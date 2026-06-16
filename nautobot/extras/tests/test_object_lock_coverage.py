"""Targeted unit tests for Object Lock behaviours not exercised directly by the broader suites.

Real behavioural tests — template tags, glyph/summary helpers, filter methods, the sweep Job wrapper,
manager/diff edge paths, and m2m-enforcement early returns. Purely defensive guards that are only
reachable by mocking an internal failure are intentionally left uncovered.
"""

from datetime import timedelta
import uuid

from django import forms as dj_forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings, RequestFactory
from django.utils import timezone

from nautobot.core.testing import APITestCase, create_job_result_and_run_job, TestCase, TransactionTestCase
from nautobot.dcim.filters import ManufacturerFilterSet
from nautobot.dcim.models import Location, LocationType, Manufacturer, Platform
from nautobot.extras import views
from nautobot.extras.api.object_locks import _batch_active_lock_claims
from nautobot.extras.choices import CustomFieldTypeChoices, JobResultStatusChoices
from nautobot.extras.context_managers import ORMChangeContext, web_request_context
from nautobot.extras.forms.forms import LockedFieldsFormMixin
from nautobot.extras.jobs_object_lock_sweep import purge_expired_and_orphaned_locks
from nautobot.extras.locking import (
    _prior_data_from_snapshot,
    _serialize_field_value,
    ALL_FIELDS_FROZEN,
    enforce_m2m_change,
    get_changed_fields,
    invalidate_gate_cache,
)
from nautobot.extras.models import CustomField, ObjectLock, ObjectLockBypassAudit, Status, Tag
from nautobot.extras.models.object_locks import ObjectLockGeneration, validate_locked_field_names
from nautobot.extras.object_lock_ui import (
    _glyph_token,
    LOCK_PROTECTION_BLURB,
    LockState,
    render_lock_glyph,
    summarize_modes,
)
from nautobot.extras.signals import change_context_state
from nautobot.extras.templatetags.object_lock import object_lock_blurb, object_lock_state

User = get_user_model()


class ObjectLockTemplateTagTestCase(TestCase):
    """templatetags/object_lock.py — both assignment tags (the module is otherwise only loaded by Selenium)."""

    def test_object_lock_state_tag(self):
        m = Manufacturer.objects.create(name="TplTag Locked")
        ObjectLock.objects.create(
            content_type=ContentType.objects.get_for_model(Manufacturer),
            object_id=m.pk,
            prevent_delete=True,
            source_key="tpl",
        )
        state = object_lock_state(m)
        self.assertIsNotNone(state)
        self.assertTrue(state.locked_for_delete)
        # Unlocked object, None, and a pk-less instance each resolve to None (the unlocked branch).
        self.assertIsNone(object_lock_state(Manufacturer.objects.create(name="TplTag Unlocked")))
        self.assertIsNone(object_lock_state(None))
        self.assertIsNone(object_lock_state(Manufacturer(name="TplTag NoPk")))

    def test_object_lock_blurb_tag(self):
        self.assertEqual(object_lock_blurb(), LOCK_PROTECTION_BLURB)


class ObjectLockGlyphHelperTestCase(TestCase):
    """object_lock_ui.py — glyph token, mode summary, and the metadata-rich tooltip."""

    def test_glyph_token_and_summary_per_mode(self):
        update_only = LockState(is_locked=True, locked_for_update=True, active_lock_count=1)
        self.assertEqual(_glyph_token(update_only), "update")
        self.assertEqual(summarize_modes(update_only), "Update-locked")
        unlocked = LockState()
        self.assertIsNone(_glyph_token(unlocked))
        self.assertEqual(summarize_modes(unlocked), "")

    def test_glyph_tooltip_includes_expiry_and_sources(self):
        state = LockState(
            is_locked=True,
            locked_for_delete=True,
            active_lock_count=2,
            earliest_expiry=timezone.now() + timedelta(days=1),
            source_keys=["alpha", "beta"],
        )
        html = str(render_lock_glyph(state, include_metadata=True))
        self.assertIn("earliest expiry", html)
        self.assertIn("sources:", html)


class ObjectLockBypassAuditAdminTestCase(TestCase):
    """admin.py — the bypass-audit admin is fully read-only."""

    def test_bypass_audit_admin_read_only(self):
        model_admin = admin.site._registry[ObjectLockBypassAudit]
        self.assertFalse(model_admin.has_add_permission(None))
        self.assertFalse(model_admin.has_change_permission(None))
        self.assertFalse(model_admin.has_delete_permission(None))


class ObjectLockDunderStrTestCase(TestCase):
    """models/object_locks.py — __str__ for the audit row and the generation token."""

    def test_bypass_audit_str(self):
        m = Manufacturer.objects.create(name="Audit Str Mfg")
        audit = ObjectLockBypassAudit.objects.create(
            content_type=ContentType.objects.get_for_model(Manufacturer), object_id=m.pk
        )
        self.assertIn("Bypass by", str(audit))

    def test_generation_token_str(self):
        # The migration-seeded pk=1 row is cleared by the runner's generate_test_data --flush, so create
        # one explicitly rather than rely on the seed.
        gen = ObjectLockGeneration.objects.create(token=7)
        self.assertEqual(str(gen), "7")


class ObjectLockManagerEdgeTestCase(TestCase):
    """models/object_locks.py — indefinite TTL, locked() auto source_key, empty-field validation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="ol-cov-mgr")

    @override_settings(OBJECT_LOCK_DEFAULT_TTL=None)
    def test_lock_with_ttl_none_is_indefinite(self):
        m = Manufacturer.objects.create(name="TTL None Mfg")
        lock = ObjectLock.objects.lock(m, requesting_user=self.user)
        self.assertIsNone(lock.expires)

    def test_locked_context_manager_auto_source_key(self):
        m = Manufacturer.objects.create(name="Auto Key Mfg")
        with ObjectLock.objects.locked(m, requesting_user=self.user):
            self.assertEqual(ObjectLock.objects.for_object(m).count(), 1)
        self.assertEqual(ObjectLock.objects.for_object(m).count(), 0)

    def test_validate_empty_field_names_returns_empty(self):
        self.assertEqual(validate_locked_field_names(Manufacturer, []), [])
        self.assertEqual(validate_locked_field_names(Manufacturer, None), [])


class ObjectLockDiffEdgeTestCase(TestCase):
    """locking.py — get_changed_fields / serialize / snapshot edge branches + ALL_FIELDS_FROZEN sentinel."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="ol-cov-diff")
        cls.ct = ContentType.objects.get_for_model(Manufacturer)

    def test_all_fields_frozen_sentinel(self):
        self.assertEqual(repr(ALL_FIELDS_FROZEN), "ALL_FIELDS_FROZEN")
        self.assertIn("anything", ALL_FIELDS_FROZEN)  # __contains__ is always True

    def test_empty_candidate_fields_returns_empty(self):
        m = Manufacturer.objects.create(name="Diff Empty")
        self.assertEqual(get_changed_fields(m, set()), set())

    def test_serialize_none_fk_value_returns_none(self):
        p = Platform.objects.create(name="Diff NoneFK")  # manufacturer FK is null
        self.assertIsNone(_serialize_field_value(p, "manufacturer"))

    def test_snapshot_missing_field_fails_closed(self):
        m = Manufacturer.objects.create(name="Diff SnapMiss", description="orig")
        ctx = ORMChangeContext(user=self.user)
        ctx.pre_object_data = {str(m.pk): {"name": "Diff SnapMiss"}}  # 'description' absent from snapshot
        token = change_context_state.set(ctx)
        try:
            m.description = "new"
            self.assertEqual(get_changed_fields(m, {"description"}), {"description"})
        finally:
            change_context_state.reset(token)

    def test_prior_data_none_when_snapshot_empty(self):
        m = Manufacturer.objects.create(name="Diff EmptySnap")
        ctx = ORMChangeContext(user=self.user)
        ctx.pre_object_data = {}  # context present but no snapshot rows
        token = change_context_state.set(ctx)
        try:
            self.assertIsNone(_prior_data_from_snapshot(m))
        finally:
            change_context_state.reset(token)

    def test_custom_field_changed_via_db_path(self):
        cf = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, key="cov_db_cf", label="Cov DB CF")
        cf.content_types.set([self.ct])
        m = Manufacturer.objects.create(name="Diff CfDb")
        m._custom_field_data = {"cov_db_cf": "orig"}
        m.save()
        m.refresh_from_db()
        m._custom_field_data["cov_db_cf"] = "changed"
        # No change context -> snapshot None -> custom-field prior is read from the DB row.
        self.assertEqual(get_changed_fields(m, {"cov_db_cf"}), {"cov_db_cf"})

    def test_custom_field_fail_closed_when_not_in_db(self):
        cf = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, key="cov_fc_cf", label="Cov FC CF")
        cf.content_types.set([self.ct])
        m = Manufacturer(name="Diff CfUnsaved")  # not saved
        m._custom_field_data = {"cov_fc_cf": "x"}
        # No snapshot and not in the DB -> prior unknowable -> fail closed.
        self.assertEqual(get_changed_fields(m, {"cov_fc_cf"}), {"cov_fc_cf"})


class ObjectLockFilterMethodTestCase(APITestCase):
    """filters.py — locked_for_delete / locked_for_update filters + the value-None passthrough."""

    def setUp(self):
        super().setUp()
        self.delete_locked = Manufacturer.objects.create(name="FM Delete Locked")
        self.update_locked = Manufacturer.objects.create(name="FM Update Locked")
        self.unlocked = Manufacturer.objects.create(name="FM Unlocked")
        ObjectLock.objects.lock(self.delete_locked, prevent_delete=True, requesting_user=self.user)
        ObjectLock.objects.lock(
            self.update_locked, prevent_update=True, prevent_delete=False, requesting_user=self.user
        )
        self.add_permissions("dcim.view_manufacturer")

    def test_filter_locked_for_delete(self):
        resp = self.client.get("/api/dcim/manufacturers/?locked_for_delete=true", **self.header)
        names = {row["name"] for row in resp.data["results"]}
        self.assertIn("FM Delete Locked", names)
        self.assertNotIn("FM Update Locked", names)
        self.assertNotIn("FM Unlocked", names)

    def test_filter_locked_for_update(self):
        resp = self.client.get("/api/dcim/manufacturers/?locked_for_update=true", **self.header)
        names = {row["name"] for row in resp.data["results"]}
        self.assertIn("FM Update Locked", names)
        self.assertNotIn("FM Delete Locked", names)

    def test_lock_filter_none_passthrough(self):
        filterset = ManufacturerFilterSet()
        queryset = Manufacturer.objects.all()
        self.assertEqual(list(filterset._apply_lock_filter(queryset, None)), list(queryset))


class ObjectLockApiEdgeTestCase(APITestCase):
    """api/object_locks.py — empty-batch helper + past-expiry rejection on the lock action."""

    def setUp(self):
        super().setUp()
        self.mfg = Manufacturer.objects.create(name="Api Edge Mfg")

    def test_batch_active_lock_claims_empty(self):
        self.assertEqual(_batch_active_lock_claims([]), {})

    def test_lock_action_rejects_past_expires(self):
        self.add_permissions("extras.add_objectlock", "dcim.view_manufacturer")
        url = f"/api/dcim/manufacturers/{self.mfg.pk}/lock/"
        past = (timezone.now() - timedelta(days=1)).isoformat()
        resp = self.client.post(url, {"prevent_delete": True, "expires": past}, format="json", **self.header)
        self.assertHttpStatus(resp, 400)


class ObjectLockSweepJobTestCase(TransactionTestCase):
    """jobs_object_lock_sweep.py — the Job run() wrapper and the uninstalled-model orphan purge."""

    # Running the sweep Job writes JobLogEntry rows to the separate 'job_logs' connection, which an
    # atomic TestCase can't host ("cannot open a new connection in an atomic block"); use the non-atomic
    # TransactionTestCase + job_logs db, mirroring JobTransactionTest in test_jobs.py.
    databases = ("default", "job_logs")

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(username="ol-cov-sweep", is_superuser=True)

    def test_sweep_job_run(self):
        m = Manufacturer.objects.create(name="Sweep Job Mfg")
        lock = ObjectLock.objects.lock(m, source_key="covsweep", requesting_user=self.user)
        ObjectLock.objects.filter(pk=lock.pk).update(expires=timezone.now() - timedelta(hours=1))
        job_result = create_job_result_and_run_job("nautobot.extras.jobs_object_lock_sweep", "ObjectLockSweep")
        self.assertEqual(job_result.status, JobResultStatusChoices.STATUS_SUCCESS)
        self.assertFalse(ObjectLock.objects.filter(pk=lock.pk).exists())

    def test_sweep_purges_uninstalled_model_locks(self):
        ghost_ct = ContentType.objects.create(app_label="ghostapp_cov", model="ghostmodel")
        ObjectLock.objects.create(
            content_type=ghost_ct, object_id=uuid.uuid4(), prevent_delete=True, source_key="ghost"
        )
        result = purge_expired_and_orphaned_locks()
        self.assertFalse(ObjectLock.objects.filter(content_type=ghost_ct).exists())
        self.assertGreaterEqual(result["orphaned"], 1)


class ObjectLockFormMixinUnboundTestCase(TestCase):
    """forms/forms.py — an unbound LockedFieldsFormMixin form resolves an empty frozen-field set."""

    def test_unbound_form_has_no_frozen_fields(self):
        class _SampleForm(LockedFieldsFormMixin, dj_forms.Form):
            name = dj_forms.CharField(required=False)

        form = _SampleForm()  # no frozen_fields kwarg, no instance -> _frozen_fields_for_instance() -> set()
        self.assertEqual(form._frozen_fields, set())
        self.assertFalse(form.fields["name"].disabled)


class ObjectLockBulkReturnUrlTestCase(TestCase):
    """views.py — ObjectLockBulkActionView._safe_return_url accepts a safe local URL."""

    def test_safe_return_url_accepts_local(self):
        view = views.ObjectLockBulkActionView()
        # RequestFactory (unlike the test Client) doesn't auto-allow "testserver"; use an allowed host.
        request = RequestFactory().post("/", {"return_url": "/dcim/manufacturers/"}, SERVER_NAME="nautobot.example.com")
        self.assertEqual(view._safe_return_url(request), "/dcim/manufacturers/")


class ObjectLockM2MEarlyReturnTestCase(TestCase):
    """locking.py + signals.py — m2m-enforcement early returns and the kill switch."""

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_user(username="ol-cov-m2m", is_superuser=True)
        location_type = LocationType.objects.create(name="Region-Cov")
        location_type.content_types.add(ContentType.objects.get_for_model(Location))
        cls.status = Status.objects.get_for_model(Location).first()
        cls.location = Location.objects.create(name="LocCov", location_type=location_type, status=cls.status)
        cls.tag = Tag.objects.create(name="TagCov")
        cls.tag.content_types.add(ContentType.objects.get_for_model(Location))

    def setUp(self):
        invalidate_gate_cache()

    def test_enforce_m2m_non_pre_action_returns(self):
        enforce_m2m_change(self.location, "tags", "post_add")  # non-pre action -> early return, no raise

    def test_enforce_m2m_not_in_database_returns(self):
        enforce_m2m_change(Location(name="ghost"), "tags", "pre_add")  # unsaved -> early return, no raise

    def test_enforce_m2m_gate_miss_returns(self):
        enforce_m2m_change(self.location, "tags", "pre_add")  # no lock on this type -> gate miss, no raise

    @override_settings(OBJECT_LOCK_ENFORCED=False)
    def test_m2m_kill_switch_allows_frozen(self):
        with web_request_context(self.superuser):
            ObjectLock.objects.lock(
                self.location,
                prevent_update=True,
                locked_fields=["tags"],
                requesting_user=self.superuser,
                source_key="cov-m2m-frozen",
            )
        invalidate_gate_cache()
        with web_request_context(self.superuser):
            self.location.tags.add(self.tag)  # kill switch disables enforcement
        self.assertIn(self.tag, self.location.tags.all())


class ObjectLockDefensiveGuardTestCase(TestCase):
    """Group A — reachable defensive guards covered with real tests (no mocking)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="ol-cov-guard")

    def test_find_stale_locked_fields_uninstalled_model(self):
        from nautobot.extras.locking import find_stale_locked_fields

        ghost_ct = ContentType.objects.create(app_label="ghostapp_stale", model="ghoststale")
        lock = ObjectLock.objects.create(
            content_type=ghost_ct,
            object_id=uuid.uuid4(),
            prevent_update=True,
            locked_fields=["whatever"],
            source_key="ghost-stale",
        )
        match = [entry for entry in find_stale_locked_fields() if entry["lock_id"] == lock.pk]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0]["stale_fields"], ["whatever"])  # uninstalled model -> every name stale

    def test_lock_rejects_basemodel_with_non_uuid_pk(self):
        instance = Manufacturer(name="NonUuidPk")
        instance.pk = 123  # a BaseModel instance whose pk is not a UUID
        with self.assertRaises(TypeError):
            ObjectLock.objects.lock(instance, requesting_user=self.user)

    def test_frozen_field_labels_uninstalled_model(self):
        ghost_ct = ContentType.objects.create(app_label="ghostapp_lbl", model="ghostlbl")
        lock = ObjectLock.objects.create(
            content_type=ghost_ct,
            object_id=uuid.uuid4(),
            prevent_update=True,
            locked_fields=["a", "b"],
            source_key="ghost-lbl",
        )
        self.assertEqual(lock.frozen_field_labels(), ["a", "b"])  # no model -> raw stored names

    def test_m2m_field_name_for_sender_no_match(self):
        from nautobot.extras.signals import _m2m_field_name_for_sender

        mfr = Manufacturer.objects.create(name="M2M NoMatch")
        # An unrelated through model resolves to no field name on the instance.
        self.assertIsNone(_m2m_field_name_for_sender(mfr, Tag.content_types.through))

    def test_is_field_frozen_non_iterable_returns_false(self):
        class _SampleForm(LockedFieldsFormMixin, dj_forms.Form):
            name = dj_forms.CharField(required=False)

        form = _SampleForm(frozen_fields=123)  # non-iterable -> `in` raises TypeError -> False
        self.assertFalse(form.is_field_frozen("name"))

    def test_bulk_resolve_request_uninstalled_model_404(self):
        from django.http import Http404

        ghost_ct = ContentType.objects.create(app_label="ghostapp_view", model="ghostview")
        view = views.ObjectLockBulkActionView()
        request = RequestFactory().post("/", {"content_type": str(ghost_ct.pk)}, SERVER_NAME="nautobot.example.com")
        with self.assertRaises(Http404):
            view._resolve_request(request)

    def test_glyph_wrap_is_idempotent(self):
        from nautobot.dcim.tables import ManufacturerTable

        table = ManufacturerTable(Manufacturer.objects.none())  # __init__ wraps the primary column once
        table._wrap_primary_column_with_lock_glyph()  # a second call must no-op via the idempotency guard


# Assorted Object Lock behaviours: filter combination, kill-switch surfacing, blocked-write message,
# list-view query efficiency, factory name uniqueness, and gate-rebuild fallback.


class ObjectLockFilterCombinationTestCase(APITestCase):
    """Combining two lock filters must not 500 (each filter uses a distinct annotation alias)."""

    def setUp(self):
        super().setUp()
        self.locked = Manufacturer.objects.create(name="Combo Locked")
        ObjectLock.objects.lock(self.locked, prevent_delete=True, prevent_update=True, requesting_user=self.user)
        self.add_permissions("dcim.view_manufacturer")

    def test_two_lock_filters_combined_does_not_500(self):
        resp = self.client.get("/api/dcim/manufacturers/?is_locked=true&locked_for_update=true", **self.header)
        self.assertHttpStatus(resp, 200)
        self.assertIn("Combo Locked", {row["name"] for row in resp.data["results"]})


class ObjectLockKillSwitchSurfacingTestCase(APITestCase):
    """OBJECT_LOCK_ENFORCED=False silences surfacing too (UI helper, REST fields, filters)."""

    def setUp(self):
        super().setUp()
        self.mfg = Manufacturer.objects.create(name="KS Mfg")
        ObjectLock.objects.lock(self.mfg, prevent_delete=True, requesting_user=self.user)
        self.add_permissions("dcim.view_manufacturer")

    @override_settings(OBJECT_LOCK_ENFORCED=False)
    def test_surfacing_silenced_when_disabled(self):
        from nautobot.extras.object_lock_ui import lock_state_for_objects

        self.assertEqual(lock_state_for_objects([self.mfg]), {})  # UI glyphs/panel
        detail = self.client.get(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        self.assertFalse(detail.data["is_locked"])  # REST lock-state fields
        listed = self.client.get("/api/dcim/manufacturers/?is_locked=true", **self.header)
        self.assertNotIn("KS Mfg", {row["name"] for row in listed.data["results"]})  # filters

    def test_surfacing_active_when_enabled(self):
        from nautobot.extras.object_lock_ui import lock_state_for_objects

        self.assertIn(self.mfg.pk, lock_state_for_objects([self.mfg]))
        detail = self.client.get(f"/api/dcim/manufacturers/{self.mfg.pk}/", **self.header)
        self.assertTrue(detail.data["is_locked"])


class ObjectLockBlockedMessageTestCase(TestCase):
    """The blocked-write message leads with the human reason, keeping source_key as secondary."""

    def test_message_leads_with_reason(self):
        from nautobot.extras.locking import build_locked_message, GATE_MODE_DELETE

        m = Manufacturer.objects.create(name="Msg Mfg")
        claim = ObjectLock.objects.create(
            content_type=ContentType.objects.get_for_model(Manufacturer),
            object_id=m.pk,
            prevent_delete=True,
            source_key="auto:abc-123",
            reason="ACME SSoT sync in progress",
        )
        msg = build_locked_message([claim], GATE_MODE_DELETE)
        self.assertIn("ACME SSoT sync in progress", msg)
        self.assertIn("auto:abc-123", msg)  # technical identifier retained
        self.assertLess(msg.index("reason:"), msg.index("source(s):"))  # reason leads


class ObjectLockListViewQuerysetTestCase(TestCase):
    """The ObjectLock UI list view eager-loads its FK + GFK columns (no N+1)."""

    def test_uiviewset_queryset_eager_loads(self):
        queryset = views.ObjectLockUIViewSet.queryset
        self.assertIn("content_type", queryset.query.select_related)
        self.assertIn("created_by", queryset.query.select_related)
        self.assertIn("locked_object", queryset._prefetch_related_lookups)


class ObjectLockFactoryUniquenessTestCase(TestCase):
    """ObjectLockFactory builds many instances without colliding on the unique target name."""

    def test_factory_batch_creates_distinct_targets(self):
        from nautobot.extras.factory import ObjectLockFactory

        locks = ObjectLockFactory.create_batch(5)
        self.assertEqual(len({lock.object_id for lock in locks}), 5)


class ObjectLockGateRebuildTestCase(TestCase):
    """A failed gate-rebuild lock acquisition (redis LockError) falls back to a DB build, not a 500."""

    def test_gate_rebuild_survives_lock_error(self):
        from unittest import mock

        import redis

        from nautobot.extras.locking import GATE_MODE_DELETE, GATE_MODE_UPDATE, get_gate

        invalidate_gate_cache()
        with mock.patch("nautobot.extras.locking.cache") as mock_cache:
            mock_cache.get.return_value = None  # cache miss -> rebuild path
            mock_cache.lock.side_effect = redis.exceptions.LockError("could not acquire")
            gate = get_gate()  # must fall back to an uncached DB build, not raise
        self.assertIsInstance(gate, dict)
        self.assertIn(GATE_MODE_DELETE, gate)
        self.assertIn(GATE_MODE_UPDATE, gate)


# Trust-boundary RBAC: object-scoped lock/release, round-trip gate re-arm, and bypass via ObjectPermission.


class ObjectLockRBACTestCase(APITestCase):
    """The lock/release actions honor object-level view scoping, and release re-arms the gate."""

    def setUp(self):
        super().setUp()
        self.in_scope = Manufacturer.objects.create(name="RBAC In Scope")
        self.out_scope = Manufacturer.objects.create(name="RBAC Out Scope")

    def _grant_scoped_view(self, *manufacturers):
        from nautobot.users.models import ObjectPermission

        perm = ObjectPermission.objects.create(
            name="rbac scoped view",
            actions=["view"],
            constraints={"pk__in": [str(m.pk) for m in manufacturers]},
        )
        perm.object_types.set([ContentType.objects.get_for_model(Manufacturer)])
        perm.users.add(self.user)

    def test_lock_action_respects_object_view_scope(self):
        # add_objectlock is the (unconstrained) trust boundary; view is object-scoped to in_scope only.
        self.add_permissions("extras.add_objectlock")
        self._grant_scoped_view(self.in_scope)
        in_url = f"/api/dcim/manufacturers/{self.in_scope.pk}/lock/"
        out_url = f"/api/dcim/manufacturers/{self.out_scope.pk}/lock/"
        self.assertHttpStatus(self.client.post(in_url, {"prevent_delete": True}, format="json", **self.header), 201)
        self.assertHttpStatus(self.client.post(out_url, {"prevent_delete": True}, format="json", **self.header), 404)

    def test_release_action_respects_object_view_scope(self):
        self.add_permissions("extras.add_objectlock", "extras.delete_objectlock")
        self._grant_scoped_view(self.in_scope)
        ObjectLock.objects.lock(self.out_scope, prevent_delete=True, source_key="oos", requesting_user=self.user)
        out_url = f"/api/dcim/manufacturers/{self.out_scope.pk}/release/"
        # The user can't view the out-of-scope object, so release 404s before touching the claim.
        self.assertHttpStatus(self.client.post(out_url, {"source_key": "oos"}, format="json", **self.header), 404)
        self.assertEqual(ObjectLock.objects.for_object(self.out_scope).count(), 1)

    def test_lock_block_release_roundtrip_rearms_gate(self):
        from django.urls import reverse

        self.add_permissions(
            "extras.add_objectlock",
            "extras.delete_objectlock",
            "dcim.view_manufacturer",
            "dcim.delete_manufacturer",
        )
        lock_url = f"/api/dcim/manufacturers/{self.in_scope.pk}/lock/"
        detail_url = reverse("dcim-api:manufacturer-detail", kwargs={"pk": self.in_scope.pk})
        source_key = self.client.post(lock_url, {"prevent_delete": True}, format="json", **self.header).data[
            "source_key"
        ]
        self.assertHttpStatus(self.client.delete(detail_url, **self.header), 409)  # blocked while locked
        release_url = f"/api/dcim/manufacturers/{self.in_scope.pk}/release/"
        self.assertHttpStatus(
            self.client.post(release_url, {"source_key": source_key}, format="json", **self.header), 200
        )
        self.assertHttpStatus(self.client.delete(detail_url, **self.header), 204)  # gate re-armed -> delete succeeds


class ObjectLockBypassRBACTestCase(TestCase):
    """Bypass works when bypass_objectlock is granted via an ObjectPermission (not only as superuser)."""

    def test_bypass_permission_via_object_permission(self):
        from nautobot.extras.locking import bypass_object_lock
        from nautobot.users.models import ObjectPermission

        actor = User.objects.create_user(username="ol-bypass-actor")  # NOT a superuser
        m = Manufacturer.objects.create(name="Bypass RBAC Mfg", description="keep")
        with web_request_context(actor):
            ObjectLock.objects.lock(m, prevent_update=True, requesting_user=actor, source_key="brbac")
        invalidate_gate_cache()
        perm = ObjectPermission.objects.create(name="bypass perm", actions=["bypass"])
        perm.object_types.set([ContentType.objects.get_for_model(ObjectLock)])
        perm.users.add(actor)
        actor = User.objects.get(pk=actor.pk)  # fresh instance: no stale permission cache
        with web_request_context(actor):
            with bypass_object_lock():
                m.description = "bypassed"
                m.save()  # must not raise — bypass permission satisfied via the ObjectPermission
        m.refresh_from_db()
        self.assertEqual(m.description, "bypassed")


class ObjectLockNoOpRejectionTestCase(TestCase):
    """A lock that prevents neither delete nor update is rejected at validation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="ol-noop")

    def test_manager_rejects_noop_lock(self):
        from django.core.exceptions import ValidationError

        m = Manufacturer.objects.create(name="NoOp Mgr")
        with self.assertRaises(ValidationError):
            ObjectLock.objects.lock(m, prevent_delete=False, prevent_update=False, requesting_user=self.user)

    def test_clean_rejects_noop_lock(self):
        from django.core.exceptions import ValidationError

        m = Manufacturer.objects.create(name="NoOp Clean")
        lock = ObjectLock(
            content_type=ContentType.objects.get_for_model(Manufacturer),
            object_id=m.pk,
            prevent_delete=False,
            prevent_update=False,
        )
        with self.assertRaises(ValidationError):
            lock.clean()
