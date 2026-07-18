"""UI view tests for the minimal Object Lock management view."""

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.core.testing import ViewTestCases
from nautobot.core.testing.utils import post_data
from nautobot.dcim.models import Manufacturer
from nautobot.extras.choices import ObjectChangeEventContextChoices
from nautobot.extras.models import JobResult, ObjectLock


class ObjectLockUIViewTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    model = ObjectLock

    @classmethod
    def setUpTestData(cls):
        ct = ContentType.objects.get_for_model(Manufacturer)
        for i in range(3):
            mfg = Manufacturer.objects.create(name=f"UI Lock Mfg {i}")
            ObjectLock.objects.create(
                content_type=ct,
                object_id=mfg.pk,
                source_context=ObjectChangeEventContextChoices.CONTEXT_ORM,
                source_key=f"ui-{i}",
            )

    def _create_lock(self, suffix, created_by=None):
        """Create an ObjectLock against a fresh Manufacturer, optionally owned by a user."""
        ct = ContentType.objects.get_for_model(Manufacturer)
        mfg = Manufacturer.objects.create(name=f"Lock Owner Mfg {suffix}")
        return ObjectLock.objects.create(
            content_type=ct,
            object_id=mfg.pk,
            source_context=ObjectChangeEventContextChoices.CONTEXT_ORM,
            source_key=f"owner-{suffix}",
            created_by=created_by,
        )

    # --- single release: own-claim vs force-release gates ---

    def test_release_own_claim_with_delete_perm(self):
        lock = self._create_lock("own", created_by=self.user)
        self.add_permissions("extras.delete_objectlock")

        response = self.client.post(self._get_url("delete", lock), data=post_data({"confirm": True}))

        self.assertHttpStatus(response, 302)
        self.assertFalse(ObjectLock.objects.filter(pk=lock.pk).exists())

    def test_release_other_claim_without_force_denied(self):
        lock = self._create_lock("other", created_by=None)
        self.add_permissions("extras.delete_objectlock")

        response = self.client.post(self._get_url("delete", lock), data=post_data({"confirm": True}))

        self.assertHttpStatus(response, 403)
        self.assertTrue(ObjectLock.objects.filter(pk=lock.pk).exists())

    def test_release_other_claim_with_force_perm(self):
        lock = self._create_lock("force", created_by=None)
        self.add_permissions("extras.delete_objectlock", "extras.force_release_objectlock")

        with self.assertLogs("nautobot.extras.views", "WARNING"):
            response = self.client.post(self._get_url("delete", lock), data=post_data({"confirm": True}))

        self.assertHttpStatus(response, 302)
        self.assertFalse(ObjectLock.objects.filter(pk=lock.pk).exists())

    # --- bulk release: permission + per-claim ownership gate (delete_objectlock; force-release for other-owned; no staff gate) ---

    def test_bulk_release_without_delete_perm_denied(self):
        """Bulk release requires the delete object-lock permission."""
        locks = [self._create_lock(f"bulk-noperm-{i}", created_by=self.user) for i in range(2)]
        # No permissions granted.

        data = {"pk": [lock.pk for lock in locks], "confirm": True, "_confirm": True}
        response = self.client.post(self._get_url("bulk_delete"), data)

        self.assertHttpStatus(response, 403)
        self.assertEqual(ObjectLock.objects.filter(pk__in=[lock.pk for lock in locks]).count(), 2)

    def test_bulk_release_own_claims_allowed(self):
        """A delete_objectlock holder may bulk-release their own claims (no staff/elevated gate)."""
        locks = [self._create_lock(f"bulk-own-{i}", created_by=self.user) for i in range(2)]
        self.add_permissions("extras.delete_objectlock", "extras.view_jobresult")

        data = {"pk": [lock.pk for lock in locks], "confirm": True, "_confirm": True}
        response = self.client.post(self._get_url("bulk_delete"), data)

        # Dispatches the generic "Bulk Delete Objects" system job and redirects to its result.
        job_result = JobResult.objects.filter(name="Bulk Delete Objects").first()
        self.assertIsNotNone(job_result)
        self.assertRedirects(
            response,
            reverse("extras:jobresult", args=[job_result.pk]),
            status_code=302,
            target_status_code=200,
        )

    def test_bulk_release_other_claim_without_force_denied(self):
        """delete_objectlock alone cannot bulk-release another source's claims (force-release required)."""
        locks = [self._create_lock(f"bulk-other-deny-{i}", created_by=None) for i in range(2)]
        self.add_permissions("extras.delete_objectlock")

        data = {"pk": [lock.pk for lock in locks], "confirm": True, "_confirm": True}
        response = self.client.post(self._get_url("bulk_delete"), data)

        self.assertHttpStatus(response, 403)
        self.assertEqual(ObjectLock.objects.filter(pk__in=[lock.pk for lock in locks]).count(), 2)

    def test_bulk_release_other_claim_with_force_allowed(self):
        """force_release_objectlock lets a user bulk-release another source's claims."""
        locks = [self._create_lock(f"bulk-other-ok-{i}", created_by=None) for i in range(2)]
        self.add_permissions("extras.delete_objectlock", "extras.force_release_objectlock", "extras.view_jobresult")

        data = {"pk": [lock.pk for lock in locks], "confirm": True, "_confirm": True}
        response = self.client.post(self._get_url("bulk_delete"), data)

        # Ownership gate passed -> dispatches the generic Bulk Delete Objects job.
        job_result = JobResult.objects.filter(name="Bulk Delete Objects").first()
        self.assertIsNotNone(job_result)
        self.assertRedirects(
            response,
            reverse("extras:jobresult", args=[job_result.pk]),
            status_code=302,
            target_status_code=200,
        )
