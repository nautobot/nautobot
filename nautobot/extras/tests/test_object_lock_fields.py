"""Tests for Object Lock field-level locking."""

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework import status

from nautobot.core.testing import APITestCase, TestCase
from nautobot.dcim.forms import ManufacturerForm
from nautobot.dcim.models import Location, LocationType, Manufacturer, Platform
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.context_managers import ORMChangeContext, web_request_context
from nautobot.extras.forms.forms import LockedFieldsFormMixin
from nautobot.extras.locking import (
    ALL_FIELDS_FROZEN,
    bypass_object_lock,
    find_stale_locked_fields,
    get_changed_fields,
    get_frozen_fields_for_object,
    ObjectLockedError,
)
from nautobot.extras.models import CustomField, ObjectLock, ObjectLockBypassAudit, Status, Tag
from nautobot.extras.signals import change_context_state

User = get_user_model()


class ObjectLockFieldValidationTestCase(TestCase):
    """Validation of locked_fields names against the target model."""

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="ACME")
        cls.ct = ContentType.objects.get_for_model(Manufacturer)

    def _build(self, locked_fields):
        return ObjectLock(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_update=True,
            locked_fields=locked_fields,
        )

    def test_valid_concrete_field_passes(self):
        lock = self._build(["description"])
        lock.clean()  # must not raise

    def test_unknown_field_rejected(self):
        lock = self._build(["not_a_real_field"])
        with self.assertRaises(ValidationError) as ctx:
            lock.clean()
        self.assertIn("not_a_real_field", str(ctx.exception))

    def test_empty_locked_fields_allowed_means_whole_object(self):
        # Empty / None means "all fields" (whole-object), which is valid.
        self._build([]).clean()
        self._build(None).clean()


class ObjectLockManagerFieldValidationTestCase(TestCase):
    """Manager-layer validation of locked_fields."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(username="lockadmin")
        cls.manufacturer = Manufacturer.objects.create(name="ManufBob")

    def test_manager_rejects_unknown_field(self):
        with web_request_context(self.user):
            with self.assertRaises(ValidationError) as ctx:
                ObjectLock.objects.lock(
                    self.manufacturer,
                    prevent_update=True,
                    locked_fields=["bogus_field"],
                    reason="test",
                    requesting_user=self.user,
                )
        self.assertIn("bogus_field", str(ctx.exception))

    def test_manager_accepts_valid_field(self):
        with web_request_context(self.user):
            lock = ObjectLock.objects.lock(
                self.manufacturer,
                prevent_update=True,
                locked_fields=["description"],
                reason="test",
                requesting_user=self.user,
            )
        self.assertEqual(lock.locked_fields, ["description"])

    def test_manager_rejects_reverse_relation(self):
        """A reverse relation is unenforceable; field-lock validation must reject it."""
        reverse_names = sorted(
            f.name for f in Manufacturer._meta.get_fields() if f.is_relation and f.auto_created and not f.concrete
        )
        self.assertTrue(reverse_names, "Manufacturer should expose a reverse relation to test")
        with web_request_context(self.user):
            with self.assertRaises(ValidationError):
                ObjectLock.objects.lock(
                    self.manufacturer,
                    prevent_update=True,
                    locked_fields=[reverse_names[0]],
                    requesting_user=self.user,
                )


class ObjectLockSerializerFieldValidationTestCase(APITestCase):
    """REST validation of locked_fields names.

    The ObjectLock REST endpoint disables POST/PATCH, so locked_fields are validated through the
    per-object lock action (which delegates to the manager's validate_locked_field_names).
    """

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="ManufRest")

    def _lock_url(self):
        return f"/api/dcim/manufacturers/{self.manufacturer.pk}/lock/"

    def test_lock_action_rejects_unknown_field(self):
        self.add_permissions("extras.add_objectlock", "dcim.view_manufacturer")
        response = self.client.post(
            self._lock_url(),
            {"prevent_update": True, "locked_fields": ["nope_field"]},
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_lock_action_accepts_valid_field(self):
        self.add_permissions("extras.add_objectlock", "dcim.view_manufacturer")
        response = self.client.post(
            self._lock_url(),
            {"prevent_update": True, "locked_fields": ["name"]},
            format="json",
            **self.header,
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        lock = ObjectLock.objects.for_object(self.manufacturer).get()
        self.assertEqual(lock.locked_fields, ["name"])


class ObjectLockCompositionTestCase(TestCase):
    """Composition of locked_fields across multiple active claims."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(username="compadmin")
        cls.manufacturer = Manufacturer.objects.create(name="ManufComp")
        cls.ct = ContentType.objects.get_for_model(Manufacturer)

    def _lock(self, locked_fields, source_key):
        with web_request_context(self.user):
            return ObjectLock.objects.lock(
                self.manufacturer,
                prevent_update=True,
                locked_fields=locked_fields,
                reason="test",
                requesting_user=self.user,
                source_key=source_key,
            )

    def test_single_field_scoped_claim(self):
        self._lock(["description"], "src-a")
        frozen = get_frozen_fields_for_object(self.ct.pk, self.manufacturer.pk)
        self.assertEqual(frozen, {"description"})

    def test_union_of_two_field_scoped_claims(self):
        self._lock(["description"], "src-a")
        self._lock(["name"], "src-b")
        frozen = get_frozen_fields_for_object(self.ct.pk, self.manufacturer.pk)
        self.assertEqual(frozen, {"description", "name"})

    def test_whole_object_claim_freezes_everything(self):
        self._lock(["description"], "src-a")
        self._lock(None, "src-whole")  # whole-object claim
        frozen = get_frozen_fields_for_object(self.ct.pk, self.manufacturer.pk)
        self.assertIs(frozen, ALL_FIELDS_FROZEN)

    def test_no_active_claims_returns_empty(self):
        frozen = get_frozen_fields_for_object(self.ct.pk, self.manufacturer.pk)
        self.assertEqual(frozen, set())


class ObjectLockChangedFieldsTestCase(TestCase):
    """get_changed_fields: snapshot-present and snapshot-absent (DB) paths, fail-closed."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(username="diffadmin")

    def test_db_path_detects_changed_concrete_field(self):
        # No snapshot in context -> DB fetch path. Object has no history yet, but we
        # call get_changed_fields directly (not via signal), so it reads the DB row.
        m = Manufacturer.objects.create(name="DiffA", description="old")
        m.description = "new"
        changed = get_changed_fields(m, {"description", "name"})
        self.assertEqual(changed, {"description"})

    def test_db_path_unchanged_field_not_reported(self):
        m = Manufacturer.objects.create(name="DiffB", description="same")
        m.description = "same"
        changed = get_changed_fields(m, {"description"})
        self.assertEqual(changed, set())

    def test_snapshot_path_detects_changed_field(self):
        m = Manufacturer.objects.create(name="DiffC", description="orig")
        # Simulate a present pre-save snapshot keyed by str(pk).
        ctx = ORMChangeContext(user=self.user)
        ctx.pre_object_data = {str(m.pk): {"name": "DiffC", "description": "orig"}}
        token = change_context_state.set(ctx)
        try:
            m.description = "edited"
            changed = get_changed_fields(m, {"description", "name"})
        finally:
            change_context_state.reset(token)
        self.assertEqual(changed, {"description"})

    def test_fail_closed_when_no_prior_value_available(self):
        # Unsaved instance, no snapshot -> cannot prove unchanged -> report as changed.
        m = Manufacturer(name="DiffD", description="x")
        changed = get_changed_fields(m, {"description"})
        self.assertEqual(changed, {"description"})

    def test_snapshot_path_fk_field_diffs_on_pk_not_false_positive(self):
        """A frozen FK is compared by pk: an unchanged FK is not reported; a reassigned FK is.

        Snapshots store an FK as its pk string and the live diff serializes the
        instance's FK ``_id`` the same way, so an unchanged FK must NOT false-positive (which would
        block legitimate edits to other fields), while a genuine reassignment must be caught.
        """
        mfg_a = Manufacturer.objects.create(name="FKa")
        mfg_b = Manufacturer.objects.create(name="FKb")
        platform = Platform.objects.create(name="FKplat", manufacturer=mfg_a)
        ctx = ORMChangeContext(user=self.user)
        ctx.pre_object_data = {str(platform.pk): {"manufacturer": str(mfg_a.pk)}}
        token = change_context_state.set(ctx)
        try:
            self.assertEqual(get_changed_fields(platform, {"manufacturer"}), set())  # unchanged FK
            platform.manufacturer = mfg_b
            self.assertEqual(get_changed_fields(platform, {"manufacturer"}), {"manufacturer"})  # reassigned
        finally:
            change_context_state.reset(token)


class ObjectLockFieldEnforcementTestCase(TestCase):
    """End-to-end: editing a frozen field raises; editing an unfrozen field succeeds."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(username="enforceadmin")

    def _lock_description(self, manufacturer):
        with web_request_context(self.user):
            ObjectLock.objects.lock(
                manufacturer,
                prevent_update=True,
                locked_fields=["description"],
                reason="freeze description",
                requesting_user=self.user,
                source_key="src-enforce",
            )

    def test_editing_frozen_field_raises(self):
        m = Manufacturer.objects.create(name="EnfA", description="keep")
        self._lock_description(m)
        with web_request_context(self.user):
            m.description = "changed"
            with self.assertRaises(ObjectLockedError):
                m.save()

    def test_editing_unfrozen_field_succeeds(self):
        m = Manufacturer.objects.create(name="EnfB", description="keep")
        self._lock_description(m)
        with web_request_context(self.user):
            m.name = "EnfB-renamed"  # name is NOT frozen
            m.save()
        m.refresh_from_db()
        self.assertEqual(m.name, "EnfB-renamed")

    def test_whole_object_claim_blocks_any_field(self):
        m = Manufacturer.objects.create(name="EnfC", description="keep")
        with web_request_context(self.user):
            ObjectLock.objects.lock(
                m,
                prevent_update=True,
                locked_fields=None,
                reason="whole",
                requesting_user=self.user,
                source_key="src-whole",
            )
        with web_request_context(self.user):
            m.name = "EnfC-renamed"
            with self.assertRaises(ObjectLockedError):
                m.save()


class ObjectLockFieldClassificationTestCase(TestCase):
    """Locking a relation name or custom-field key must classify safely (no crash) and still freeze.

    The field-diff classifier skips relation names (m2m/reverse) here (m2m
    freezing is the m2m_changed receiver's job), and custom-field keys are identified from the model's
    CustomFields rather than the (empty-by-default) instance ``_custom_field_data`` dict.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_superuser(username="classadmin")

    def _lock(self, manufacturer, locked_fields, source_key):
        with web_request_context(self.user):
            ObjectLock.objects.lock(
                manufacturer,
                prevent_update=True,
                locked_fields=locked_fields,
                reason="t",
                requesting_user=self.user,
                source_key=source_key,
            )

    def test_reverse_relation_lock_does_not_crash_unfrozen_edit(self):
        # A reverse-relation name is now rejected by validation (see ObjectLockManagerFieldValidationTestCase),
        # but the field-diff classifier must stay defensive if one is persisted out-of-band (legacy data, or a
        # field that became reverse after a migration): skip it, don't crash an unfrozen edit. Create the claim
        # directly to bypass validate_locked_field_names and exercise the classifier in isolation.
        m = Manufacturer.objects.create(name="RelA", description="keep")
        ObjectLock.objects.create(
            content_type=ContentType.objects.get_for_model(Manufacturer),
            object_id=m.pk,
            prevent_update=True,
            locked_fields=["device_types"],  # reverse relation persisted out-of-band, past validation
            reason="t",
            source_key="src-rel",
            created_by=self.user,
        )
        with web_request_context(self.user):
            m.description = "edited"  # not frozen -> permitted, no AttributeError on the reverse name
            m.save()
        m.refresh_from_db()
        self.assertEqual(m.description, "edited")

    def test_custom_field_lock_does_not_crash_and_freezes(self):
        cf = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, key="lock_test_cf", label="Lock Test CF")
        cf.content_types.set([ContentType.objects.get_for_model(Manufacturer)])
        m = Manufacturer.objects.create(name="CfA", description="keep")
        m._custom_field_data = {"lock_test_cf": "orig"}
        m.save()
        self._lock(m, ["lock_test_cf"], "src-cf")
        # Editing an unfrozen concrete field is permitted (CF key must NOT crash via .values()).
        with web_request_context(self.user):
            m.description = "edited"
            m.save()
        # Changing the FROZEN custom-field value is blocked.
        with web_request_context(self.user):
            m._custom_field_data["lock_test_cf"] = "changed"
            with self.assertRaises(ObjectLockedError):
                m.save()


class ObjectLockBypassFieldAuditTestCase(TestCase):
    """Bypass suspends field-scoped checks and records suspended other-source frozen fields."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(username="bypassadmin", is_superuser=True)

    def test_bypass_allows_editing_frozen_field(self):
        m = Manufacturer.objects.create(name="ByA", description="keep")
        with web_request_context(self.superuser):
            ObjectLock.objects.lock(
                m,
                prevent_update=True,
                locked_fields=["description"],
                reason="freeze",
                requesting_user=self.superuser,
                source_key="other-source",
            )
        with web_request_context(self.superuser):
            with bypass_object_lock():
                m.description = "bypassed"
                m.save()  # must NOT raise
        m.refresh_from_db()
        self.assertEqual(m.description, "bypassed")

    def test_bypass_audit_notes_suspended_fields(self):
        other = User.objects.create_user(username="other-locker")
        m = Manufacturer.objects.create(name="ByB", description="keep")
        with web_request_context(other):
            ObjectLock.objects.lock(
                m,
                prevent_update=True,
                locked_fields=["description", "name"],
                reason="freeze",
                requesting_user=other,
                source_key="other-source",
            )
        with web_request_context(self.superuser):
            with bypass_object_lock():
                m.description = "bypassed"
                m.save()
        audit = ObjectLockBypassAudit.objects.filter(object_id=m.pk).latest("time")
        self.assertTrue(audit.suspended_other_source)
        self.assertIn("description", audit.suspended_fields)


class ObjectLockM2MEnforcementTestCase(TestCase):
    """Freezing an M2M field blocks add/remove via the m2m_changed handler."""

    @classmethod
    def setUpTestData(cls):
        # NOTE: the base TestCase.setUp() creates an instance attribute ``self.user``
        # (the non-superuser "nautobotuser"), which would shadow a class-level ``cls.user``.
        # Name our superuser ``superuser`` so it survives into the test methods.
        cls.superuser = User.objects.create_superuser(username="m2madmin")
        lt = LocationType.objects.create(name="Region-S3")
        lt.content_types.add(ContentType.objects.get_for_model(Location))
        cls.status = Status.objects.get_for_model(Location).first()
        cls.location = Location.objects.create(name="LocS3", location_type=lt, status=cls.status)
        cls.tag = Tag.objects.create(name="TagS3")
        cls.tag.content_types.add(ContentType.objects.get_for_model(Location))

    def _freeze_tags(self):
        with web_request_context(self.superuser):
            ObjectLock.objects.lock(
                self.location,
                prevent_update=True,
                locked_fields=["tags"],
                reason="freeze tags",
                requesting_user=self.superuser,
                source_key="src-m2m",
            )

    def test_adding_frozen_m2m_raises(self):
        self._freeze_tags()
        with web_request_context(self.superuser):
            with self.assertRaises(ObjectLockedError):
                self.location.tags.add(self.tag)

    def test_unfrozen_m2m_field_allowed(self):
        # Freeze "description" only; tags M2M must remain editable.
        with web_request_context(self.superuser):
            ObjectLock.objects.lock(
                self.location,
                prevent_update=True,
                locked_fields=["description"],
                reason="freeze description",
                requesting_user=self.superuser,
                source_key="src-desc",
            )
        with web_request_context(self.superuser):
            self.location.tags.add(self.tag)  # must NOT raise
        self.assertIn(self.tag, self.location.tags.all())

    def test_bypass_allows_frozen_m2m(self):
        self._freeze_tags()
        with web_request_context(self.superuser):
            with bypass_object_lock():
                self.location.tags.add(self.tag)  # must NOT raise
        self.assertIn(self.tag, self.location.tags.all())


class ObjectLockCustomFieldEnforcementTestCase(TestCase):
    """Freezing a custom-field key blocks edits to that key only (end-to-end)."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(username="cfadmin", is_superuser=True)
        ct = ContentType.objects.get_for_model(Manufacturer)
        cls.cf_frozen = CustomField.objects.create(
            type=CustomFieldTypeChoices.TYPE_TEXT, key="frozen_cf", label="Frozen CF"
        )
        cls.cf_frozen.content_types.add(ct)
        cls.cf_open = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, key="open_cf", label="Open CF")
        cls.cf_open.content_types.add(ct)

    def _make(self, name):
        m = Manufacturer.objects.create(name=name)
        m._custom_field_data = {"frozen_cf": "orig", "open_cf": "orig"}
        m.save()
        return m

    def _freeze_cf(self, m):
        with web_request_context(self.superuser):
            ObjectLock.objects.lock(
                m,
                prevent_update=True,
                locked_fields=["frozen_cf"],
                reason="freeze cf",
                requesting_user=self.superuser,
                source_key="src-cf-e2e",
            )

    def test_editing_frozen_custom_field_raises(self):
        m = self._make("CFa")
        self._freeze_cf(m)
        with web_request_context(self.superuser):
            m._custom_field_data["frozen_cf"] = "changed"
            with self.assertRaises(ObjectLockedError):
                m.save()

    def test_editing_open_custom_field_succeeds(self):
        m = self._make("CFb")
        self._freeze_cf(m)
        with web_request_context(self.superuser):
            m._custom_field_data["open_cf"] = "changed"
            m.save()
        m.refresh_from_db()
        self.assertEqual(m._custom_field_data["open_cf"], "changed")


class ObjectLockDriftHygieneTestCase(TestCase):
    """Detect and fail-closed on stale locked_fields names (field renamed/removed post-creation)."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(username="driftadmin", is_superuser=True)
        cls.manufacturer = Manufacturer.objects.create(name="DriftM", description="x")
        cls.ct = ContentType.objects.get_for_model(Manufacturer)

    def test_find_stale_locked_fields_reports_unknown_name(self):
        # Create a claim, then simulate drift by writing a now-invalid name directly (bypass clean()).
        lock = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_update=True,
            locked_fields=["description"],
        )
        ObjectLock.objects.filter(pk=lock.pk).update(locked_fields=["description", "removed_field"])
        stale = find_stale_locked_fields()
        match = [entry for entry in stale if entry["lock_id"] == lock.pk]
        self.assertEqual(len(match), 1)
        self.assertIn("removed_field", match[0]["stale_fields"])

    def test_no_stale_fields_when_all_valid(self):
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_update=True,
            locked_fields=["description"],
        )
        stale = find_stale_locked_fields()
        self.assertEqual([e for e in stale if e["content_type_id"] == self.ct.pk], [])

    def test_drifted_frozen_name_fails_closed_on_save(self):
        # A frozen name that no longer resolves to a field must block saves (can't prove unchanged).
        m = Manufacturer.objects.create(name="DriftS", description="x")
        lock = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=m.pk,
            prevent_update=True,
            locked_fields=["description"],
            source_key="src-drift",
        )
        ObjectLock.objects.filter(pk=lock.pk).update(locked_fields=["removed_field"])
        with web_request_context(self.superuser):
            m.description = "y"  # only an UNfrozen field changed, but the drifted name fails closed
            with self.assertRaises(ObjectLockedError):
                m.save()


class ObjectLock409FieldExposureTestCase(APITestCase):
    """The 409 body lists offending frozen fields only for callers with view_objectlock."""

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="ConflM", description="keep")

    def _lock_description(self):
        with web_request_context(self.user):
            ObjectLock.objects.lock(
                self.manufacturer,
                prevent_update=True,
                locked_fields=["description"],
                reason="freeze",
                requesting_user=self.user,
                source_key="src-409",
            )

    def _patch_description(self):
        url = reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.manufacturer.pk})
        return self.client.patch(url, {"description": "new"}, format="json", **self.header)

    def test_409_with_view_permission_lists_fields(self):
        self.add_permissions("dcim.change_manufacturer", "extras.view_objectlock")
        self._lock_description()
        response = self._patch_description()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("description", str(response.data))

    def test_409_without_view_permission_is_generic(self):
        self.add_permissions("dcim.change_manufacturer")  # no extras.view_objectlock
        self._lock_description()
        response = self._patch_description()
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertNotIn("description", str(response.data))


class LockedFieldsFormMixinTestCase(TestCase):
    """The form mixin renders frozen fields statically and keeps them out of POST changes."""

    @classmethod
    def setUpTestData(cls):
        class _SampleForm(LockedFieldsFormMixin, forms.Form):
            name = forms.CharField(required=False)
            description = forms.CharField(required=False)

        cls.form_class = _SampleForm

    def test_frozen_field_marked_readonly(self):
        form = self.form_class(frozen_fields={"description"})
        self.assertTrue(form.fields["description"].disabled)  # Django keeps disabled fields out of changes
        self.assertFalse(form.fields["name"].disabled)

    def test_frozen_field_dropped_from_changed_data(self):
        form = self.form_class(
            data={"name": "keep", "description": "attempted-change"},
            frozen_fields={"description"},
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("description", form.changed_data)

    def test_is_field_frozen_helper(self):
        form = self.form_class(frozen_fields={"description"})
        self.assertTrue(form.is_field_frozen("description"))
        self.assertFalse(form.is_field_frozen("name"))

    def test_manufacturer_form_auto_disables_frozen_field_from_lock(self):
        """A real edit form auto-resolves frozen fields from the bound instance's update lock."""
        user = User.objects.create_user(username="frozen-form-user")
        mfg = Manufacturer.objects.create(name="Frozen Form Mfg", description="orig")
        ObjectLock.objects.lock(
            mfg, prevent_update=True, locked_fields=["description"], requesting_user=user, source_key="freeze-desc"
        )
        form = ManufacturerForm(instance=mfg)
        self.assertTrue(form.fields["description"].disabled)  # auto-detected from the lock
        self.assertFalse(form.fields["name"].disabled)  # an unfrozen field stays editable
        self.assertIn("Object Lock", form.fields["description"].help_text)


class ObjectLockFrozenFieldLabelsTestCase(TestCase):
    """frozen_field_labels() returns human-friendly labels for the detail Locks panel."""

    @classmethod
    def setUpTestData(cls):
        cls.manufacturer = Manufacturer.objects.create(name="LblM")
        cls.ct = ContentType.objects.get_for_model(Manufacturer)

    def test_labels_for_concrete_fields(self):
        lock = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_update=True,
            locked_fields=["description"],
        )
        self.assertEqual(lock.frozen_field_labels(), ["Description"])

    def test_labels_whole_object(self):
        lock = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_update=True,
            locked_fields=None,
        )
        self.assertEqual(lock.frozen_field_labels(), ["All fields"])

    def test_labels_unknown_field_falls_back_to_name(self):
        lock = ObjectLock.objects.create(
            content_type=self.ct,
            object_id=self.manufacturer.pk,
            prevent_update=True,
            locked_fields=["description"],
        )
        ObjectLock.objects.filter(pk=lock.pk).update(locked_fields=["mystery"])
        lock.refresh_from_db()
        self.assertEqual(lock.frozen_field_labels(), ["mystery"])
