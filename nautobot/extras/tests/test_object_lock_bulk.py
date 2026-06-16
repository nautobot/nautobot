from datetime import timedelta
import logging
from types import SimpleNamespace
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.template import Context, Template
from django.test import Client, override_settings, RequestFactory, TestCase
from django.urls import reverse as dj_reverse
from django.utils import timezone

from nautobot.core.jobs.object_lock_bulk import _mode_flags, BulkLockObjects, BulkReleaseObjects
from nautobot.dcim.models import Manufacturer
from nautobot.extras.choices import ObjectLockModeChoices
from nautobot.extras.forms.object_lock_bulk import ObjectLockBulkLockForm, ObjectLockBulkReleaseForm
from nautobot.extras.models import ObjectLock
from nautobot.extras.models.object_locks import ObjectLockManager
from nautobot.users.models import ObjectPermission

User = get_user_model()


class ObjectLockBulkLockFormTestCase(TestCase):
    def test_expiry_is_required(self):
        form = ObjectLockBulkLockForm(data={"mode": ObjectLockModeChoices.DELETE, "reason": "r", "source_key": "k"})
        self.assertFalse(form.is_valid())
        self.assertIn("expires", form.errors)

    def test_valid_with_all_fields(self):
        form = ObjectLockBulkLockForm(
            data={
                "mode": ObjectLockModeChoices.BOTH,
                "reason": "maintenance window",
                "source_key": "change-1234",
                "expires": (timezone.now() + timedelta(days=1)).isoformat(),
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_mode_choices_cover_three_modes(self):
        form = ObjectLockBulkLockForm()
        values = {c[0] for c in form.fields["mode"].choices if c[0]}
        self.assertEqual(
            values, {ObjectLockModeChoices.DELETE, ObjectLockModeChoices.UPDATE, ObjectLockModeChoices.BOTH}
        )


class ObjectLockBulkReleaseFormTestCase(TestCase):
    def test_release_form_optional_reason(self):
        form = ObjectLockBulkReleaseForm(data={})
        self.assertTrue(form.is_valid(), form.errors)


class BulkLockObjectsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.a = Manufacturer.objects.create(name="Bulk A")
        cls.b = Manufacturer.objects.create(name="Bulk B")
        cls.user = User.objects.create_superuser(username="bulk-su")

    def _run(self, job_cls, **kwargs):
        job = job_cls()
        # Job.user is a read-only property backed by job_result.user; populate the cached_property's
        # backing slot with a lightweight stub so job.user resolves without a real JobResult/Celery run.
        job.__dict__["job_result"] = SimpleNamespace(user=self.user)
        job.logger = logging.getLogger("test.objectlock")
        return job.run(**kwargs)

    def test_locks_each_selected_object(self):
        expiry = timezone.now() + timedelta(days=1)
        summary = self._run(
            BulkLockObjects,
            content_type=self.ct,
            pk_list=[str(self.a.pk), str(self.b.pk)],
            mode=ObjectLockModeChoices.DELETE,
            reason="bulk test",
            source_key="batch-1",
            expires=expiry.isoformat(),
        )
        self.assertEqual(ObjectLock.objects.active().filter(content_type=self.ct).count(), 2)
        self.assertIn("2 locked", summary)
        self.assertIn("0 failed", summary)

    def test_one_bad_target_does_not_abort_batch(self):
        """A per-object error is counted as failed; the rest of the batch still locks."""
        expiry = timezone.now() + timedelta(days=1)
        real_lock = ObjectLock.objects.lock

        def flaky_lock(obj, **kwargs):
            if obj.pk == self.b.pk:
                raise ValidationError("simulated per-object failure")
            return real_lock(obj, **kwargs)

        with mock.patch.object(ObjectLockManager, "lock", side_effect=flaky_lock):
            summary = self._run(
                BulkLockObjects,
                content_type=self.ct,
                pk_list=[str(self.a.pk), str(self.b.pk)],
                mode=ObjectLockModeChoices.DELETE,
                reason="bulk test",
                source_key="batch-resilient",
                expires=expiry.isoformat(),
            )
        self.assertIn("1 locked", summary)
        self.assertIn("1 failed", summary)
        self.assertTrue(ObjectLock.objects.active().filter(object_id=self.a.pk).exists())
        self.assertFalse(ObjectLock.objects.active().filter(object_id=self.b.pk).exists())

    def test_manager_rejects_past_expiry(self):
        """A past expiry is rejected at the manager, so programmatic/bulk locks can't be born expired."""
        past = timezone.now() - timedelta(days=1)
        with self.assertRaises(ValidationError):
            ObjectLock.objects.lock(self.a, prevent_delete=True, expires=past, requesting_user=self.user)

    def test_mode_flags_covers_all_choices(self):
        """Exhaustiveness: every ObjectLockModeChoices value maps to a (prevent_delete, prevent_update) tuple."""
        for value, _label in ObjectLockModeChoices.CHOICES:
            flags = _mode_flags(value)
            self.assertEqual(len(flags), 2)
            self.assertTrue(any(flags), f"{value} should set at least one prevent_* flag")

    def test_release_reports_skips_for_other_source(self):
        expiry = timezone.now() + timedelta(days=1)
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.a.pk,
            prevent_delete=True,
            reason="x",
            source_key="batch-1",
            created_by=self.user,
            expires=expiry,
        )
        # b's lock has a different source_key, so the source_key="batch-1" filter excludes it and it
        # is reported as skipped (the superuser would otherwise be able to release it).
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.b.pk,
            prevent_delete=True,
            reason="y",
            source_key="someone-else",
            expires=expiry,
        )
        summary = self._run(
            BulkReleaseObjects,
            content_type=self.ct,
            pk_list=[str(self.a.pk), str(self.b.pk)],
            source_key="batch-1",
        )
        self.assertIn("1 released", summary)
        self.assertIn("1 skipped", summary)
        self.assertTrue(ObjectLock.objects.active().filter(object_id=self.b.pk).exists())


class ObjectLockBulkViewTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.locked = Manufacturer.objects.create(name="View Locked")
        cls.unlocked = Manufacturer.objects.create(name="View Unlocked")
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.locked.pk,
            prevent_delete=True,
            reason="z",
            source_key="other",
            expires=timezone.now() + timedelta(days=1),
        )
        cls.user = User.objects.create_user(username="bulk-locker")
        # Lock requires add_objectlock; release requires delete_objectlock.
        perm = ObjectPermission.objects.create(name="add locks v", actions=["add", "delete"])
        perm.object_types.set([ContentType.objects.get(app_label="extras", model="objectlock")])
        perm.users.add(cls.user)
        view_perm = ObjectPermission.objects.create(name="view mfr v", actions=["view"])
        view_perm.object_types.set([cls.ct])
        view_perm.users.add(cls.user)

    def setUp(self):
        # The test config restricts ALLOWED_HOSTS to nautobot.example.com, so the client must use it.
        self.client = Client(SERVER_NAME="nautobot.example.com")
        self.client.force_login(self.user)

    def test_confirmation_lists_locked_members_of_mixed_selection(self):
        url = dj_reverse("extras:objectlock_bulk_lock")
        resp = self.client.post(
            url,
            data={"pk": [str(self.locked.pk), str(self.unlocked.pk)], "content_type": self.ct.pk},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "View Locked")  # locked member is surfaced
        self.assertContains(resp, "already locked")

    def test_release_confirmation_renders(self):
        url = dj_reverse("extras:objectlock_bulk_release")
        resp = self.client.post(
            url,
            data={"pk": [str(self.locked.pk), str(self.unlocked.pk)], "content_type": self.ct.pk},
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "View Locked")

    def test_content_type_accepted_via_get_query_string(self):
        """Real button clicks POST only pk checkboxes; content_type arrives via the formaction query string."""
        url = dj_reverse("extras:objectlock_bulk_lock") + f"?content_type={self.ct.pk}"
        resp = self.client.post(url, data={"pk": [str(self.locked.pk), str(self.unlocked.pk)]})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "already locked")

    def test_garbage_content_type_returns_404(self):
        """A tampered non-numeric content_type must 404 gracefully, not raise a raw 500 ValueError."""
        url = dj_reverse("extras:objectlock_bulk_lock")
        resp = self.client.post(url, data={"content_type": "abc", "pk": [str(self.unlocked.pk)]})
        self.assertEqual(resp.status_code, 404)

    def test_select_all_resolves_full_filtered_set(self):
        """`_all` resolves the matching set from the filter (request.GET), not just the posted pks."""
        # The list filter rides along on the button's formaction query string; post `_all` with only
        # ONE pk and assert the OTHER matching manufacturer is resolved too (rendered as a hidden pk).
        url = dj_reverse("extras:objectlock_bulk_lock") + f"?content_type={self.ct.pk}&name__ic=View"
        resp = self.client.post(url, data={"_all": "on", "pk": [str(self.locked.pk)]})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, f'value="{self.locked.pk}"')
        self.assertContains(resp, f'value="{self.unlocked.pk}"')  # not posted; resolved via _all + filter

    def test_unsupported_content_type_returns_404(self):
        """A content_type whose model is not a lockable BaseModel (no RestrictedQuerySet) 404s, not 500s."""
        nonlockable = ContentType.objects.get_for_model(ContentType)
        url = dj_reverse("extras:objectlock_bulk_lock") + f"?content_type={nonlockable.pk}"
        resp = self.client.post(url, data={"pk": [str(self.unlocked.pk)]})
        self.assertEqual(resp.status_code, 404)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_confirm_lock_creates_locks(self):
        """The _confirm path enqueues BulkLockObjects, which (eager) actually creates the lock."""
        url = dj_reverse("extras:objectlock_bulk_lock")
        expires = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        # The view enqueues via transaction.on_commit; capture+execute the callback so the
        # (eager) Job actually runs within this TestCase's never-committed transaction.
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                url,
                data={
                    "_confirm": "all",
                    "content_type": self.ct.pk,
                    "pk": [str(self.unlocked.pk)],
                    "mode": ObjectLockModeChoices.DELETE,
                    "reason": "x",
                    "source_key": "batch1",
                    "expires": expires,
                },
            )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(ObjectLock.objects.active().filter(object_id=self.unlocked.pk).exists())

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_confirm_unlocked_only_skips_locked(self):
        """_confirm=unlocked_only locks the unlocked member and leaves the already-locked one untouched."""
        before = ObjectLock.objects.active().for_object(self.locked).count()
        url = dj_reverse("extras:objectlock_bulk_lock")
        expires = (timezone.now() + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                url,
                data={
                    "_confirm": "unlocked_only",
                    "content_type": self.ct.pk,
                    "pk": [str(self.locked.pk), str(self.unlocked.pk)],
                    "mode": ObjectLockModeChoices.DELETE,
                    "reason": "x",
                    "source_key": "batch1",
                    "expires": expires,
                },
            )
        self.assertEqual(resp.status_code, 302)
        # The previously-unlocked object is now locked.
        self.assertTrue(ObjectLock.objects.active().filter(object_id=self.unlocked.pk).exists())
        # The already-locked object's active claim count is unchanged (job only targeted the unlocked pks).
        self.assertEqual(ObjectLock.objects.active().for_object(self.locked).count(), before)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True, CELERY_TASK_EAGER_PROPAGATES=True)
    def test_confirm_release_removes_claim(self):
        """_confirm release enqueues BulkReleaseObjects, which (eager) removes the user's own claim."""
        # The fixture claim on self.locked has no created_by (source_key="other"), so a plain
        # delete_objectlock user can't release it. Replace it with a claim owned by self.user so the
        # release job's "is_own" branch (which only needs delete_objectlock) applies.
        ObjectLock.objects.for_object(self.locked).delete()
        ObjectLock.objects.lock(
            self.locked,
            prevent_delete=True,
            reason="z",
            source_key="mine",
            requesting_user=self.user,
            expires=timezone.now() + timedelta(days=1),
        )
        self.assertTrue(ObjectLock.objects.active().for_object(self.locked).exists())
        url = dj_reverse("extras:objectlock_bulk_release")
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(
                url,
                data={"_confirm": "all", "content_type": self.ct.pk, "pk": [str(self.locked.pk)]},
            )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(ObjectLock.objects.active().for_object(self.locked).exists())


class BulkLockButtonRegistrationTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.objectlock_ct = ContentType.objects.get(app_label="extras", model="objectlock")
        cls.user = User.objects.create_user(username="locker")
        # Lock is gated on add_objectlock, release on delete_objectlock, so grant both.
        perm = ObjectPermission.objects.create(name="lock locks", actions=["add", "delete"])
        perm.object_types.set([cls.objectlock_ct])
        perm.users.add(cls.user)

    def _render(self, user):
        request = RequestFactory().get("/dcim/manufacturers/")
        request.user = user
        context = Context(
            {
                "request": request,
                "model": Manufacturer,
                "user": user,
                "bulk_edit_url": "dcim:manufacturer_bulk_edit",
                "bulk_delete_url": "dcim:manufacturer_bulk_delete",
                "permissions": {"change": True, "delete": True},
            }
        )
        template = Template("{% load buttons %}{% consolidate_bulk_action_buttons %}")
        return template.render(context)

    def _grant(self, username, actions):
        user = User.objects.create_user(username=username)
        perm = ObjectPermission.objects.create(name=f"{username} perm", actions=actions)
        perm.object_types.set([self.objectlock_ct])
        perm.users.add(user)
        return user

    def test_lock_button_present_with_permission(self):
        html = self._render(self.user)
        self.assertIn("Lock Selected", html)
        self.assertIn("Release Selected", html)
        # The lock button's formaction must carry the target content_type for a real click to work.
        self.assertIn(f"content_type={ContentType.objects.get_for_model(Manufacturer).pk}", html)

    def test_lock_button_absent_without_permission(self):
        no_perm_user = User.objects.create_user(username="no-lock")
        html = self._render(no_perm_user)
        self.assertNotIn("Lock Selected", html)
        self.assertNotIn("Release Selected", html)

    def test_buttons_are_independently_gated(self):
        # add-only -> Lock visible, Release hidden.
        add_only = self._grant("add-only", ["add"])
        add_html = self._render(add_only)
        self.assertIn("Lock Selected", add_html)
        self.assertNotIn("Release Selected", add_html)
        # delete-only -> Release visible, Lock hidden.
        delete_only = self._grant("delete-only", ["delete"])
        del_html = self._render(delete_only)
        self.assertIn("Release Selected", del_html)
        self.assertNotIn("Lock Selected", del_html)


class BulkJobCoverageTestCase(TestCase):
    """Guard branches of the bulk lock/release Jobs: permission, uninstalled CT, unreleasable claim."""

    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.mfr = Manufacturer.objects.create(name="Bulk Cov Mfr")
        cls.superuser = User.objects.create_superuser(username="bulk-cov-su")

    def _run(self, user, job_cls, **kwargs):
        job = job_cls()
        job.__dict__["job_result"] = SimpleNamespace(user=user)
        job.logger = logging.getLogger("test.objectlock")
        return job.run(**kwargs)

    def test_lock_without_add_permission_is_denied(self):
        user = User.objects.create_user(username="bulk-cov-noperm")
        with self.assertRaises(PermissionDenied):
            self._run(
                user,
                BulkLockObjects,
                content_type=self.ct,
                pk_list=[self.mfr.pk],
                mode=ObjectLockModeChoices.DELETE,
                reason="r",
                source_key="k",
                expires=(timezone.now() + timedelta(days=1)).isoformat(),
            )

    def test_lock_uninstalled_content_type_raises(self):
        ghost = ContentType.objects.create(app_label="ghost_bulk_lock_cov", model="ghost")
        with self.assertRaises(ValidationError):
            self._run(
                self.superuser,
                BulkLockObjects,
                content_type=ghost,
                pk_list=[],
                mode=ObjectLockModeChoices.DELETE,
                reason="r",
                source_key="k",
                expires=(timezone.now() + timedelta(days=1)).isoformat(),
            )

    def test_release_uninstalled_content_type_raises(self):
        ghost = ContentType.objects.create(app_label="ghost_bulk_rel_cov", model="ghost")
        with self.assertRaises(ValidationError):
            self._run(self.superuser, BulkReleaseObjects, content_type=ghost, pk_list=[])

    def test_release_skips_claim_user_cannot_release(self):
        # Another owner's claim, run by a user with view but NOT force_release_objectlock: the claim is
        # skipped (not released) and the object is counted as skipped.
        owner = User.objects.create_user(username="bulk-cov-owner")
        actor = User.objects.create_user(username="bulk-cov-actor")
        view_perm = ObjectPermission.objects.create(name="bulk-cov-view", actions=["view"])
        view_perm.object_types.set([self.ct])
        view_perm.users.add(actor)
        lock = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.mfr.pk,
            prevent_delete=True,
            source_key="other-owner",
            created_by=owner,
        )
        summary = self._run(actor, BulkReleaseObjects, content_type=self.ct, pk_list=[self.mfr.pk])
        self.assertTrue(ObjectLock.objects.filter(pk=lock.pk).exists())  # not released
        self.assertIn("1 skipped", summary)
