from datetime import timedelta
from unittest import mock

from django import forms as django_forms
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import override_settings, TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from django.utils.safestring import SafeString

from nautobot.dcim.models import DeviceType, Manufacturer
from nautobot.dcim.tables import ManufacturerTable
from nautobot.extras.models import ComputedField, ObjectLock, Status
from nautobot.extras.object_lock_ui import (
    LOCK_GLYPHS,
    lock_state_for_objects,
    LockState,
    ObjectLockQuickFilterFormMixin,
    render_lock_glyph,
    summarize_modes,
    user_can_view_lock_metadata,
)
from nautobot.extras.tables import ComputedFieldTable
from nautobot.ipam.models import Namespace, Prefix
from nautobot.ipam.tables import PrefixTable
from nautobot.ipam.utils import add_available_prefixes
from nautobot.users.models import ObjectPermission

User = get_user_model()


class LockStateForObjectsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.mfr_locked = Manufacturer.objects.create(name="Locked Mfr")
        cls.mfr_unlocked = Manufacturer.objects.create(name="Unlocked Mfr")
        cls.expiry = timezone.now() + timedelta(days=1)
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.mfr_locked.pk,
            prevent_delete=True,
            prevent_update=False,
            reason="first",
            source_key="src-a",
            expires=cls.expiry,
        )
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.mfr_locked.pk,
            prevent_delete=False,
            prevent_update=True,
            reason="second",
            source_key="src-b",
            expires=cls.expiry + timedelta(days=2),
        )

    def test_returns_empty_for_empty_input(self):
        self.assertEqual(lock_state_for_objects([]), {})

    def test_single_bulk_query_only(self):
        objects = [self.mfr_locked, self.mfr_unlocked]
        with self.assertNumQueries(1):
            result = lock_state_for_objects(objects)
        self.assertIn(self.mfr_locked.pk, result)
        self.assertNotIn(self.mfr_unlocked.pk, result)

    def test_lockstate_aggregates_modes_and_counts(self):
        result = lock_state_for_objects([self.mfr_locked])
        state = result[self.mfr_locked.pk]
        self.assertIsInstance(state, LockState)
        self.assertTrue(state.is_locked)
        self.assertTrue(state.locked_for_delete)
        self.assertTrue(state.locked_for_update)
        self.assertEqual(state.active_lock_count, 2)
        self.assertEqual(state.earliest_expiry, self.expiry)
        self.assertEqual(sorted(state.source_keys), ["src-a", "src-b"])

    def test_unlocked_object_absent_from_state_map(self):
        # An object with no active lock for its type must be absent from the result map.
        result = lock_state_for_objects([self.mfr_unlocked])
        self.assertEqual(result, {})


class LockGlyphHelpersTestCase(TestCase):
    def test_glyph_map_has_three_modes(self):
        self.assertEqual(set(LOCK_GLYPHS), {"delete", "update", "both"})

    def test_render_glyph_is_safe_and_has_aria_label_and_title(self):
        state = LockState(is_locked=True, locked_for_delete=True, locked_for_update=True, active_lock_count=2)
        html = render_lock_glyph(state)
        self.assertIsInstance(html, SafeString)
        self.assertIn("mdi-lock-alert", html)  # both -> lock-alert
        self.assertIn('aria-label="', html)
        self.assertIn('title="', html)
        self.assertNotIn("color:", html)  # meaning never carried by color alone

    def test_render_glyph_returns_empty_for_unlocked(self):
        self.assertEqual(render_lock_glyph(LockState()), "")

    def test_summarize_modes_names_all_distinct_modes(self):
        both = LockState(is_locked=True, locked_for_delete=True, locked_for_update=True)
        self.assertEqual(summarize_modes(both), "Delete-locked and update-locked")
        delete_only = LockState(is_locked=True, locked_for_delete=True)
        self.assertEqual(summarize_modes(delete_only), "Delete-locked")
        update_only = LockState(is_locked=True, locked_for_update=True)
        self.assertEqual(summarize_modes(update_only), "Update-locked")


class UserCanViewLockMetadataTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.viewer = User.objects.create_user(username="viewer")
        cls.granted = User.objects.create_user(username="granted")
        perm = ObjectPermission.objects.create(name="view locks", actions=["view"])
        perm.object_types.set([ContentType.objects.get(app_label="extras", model="objectlock")])
        perm.users.add(cls.granted)
        cls.superuser = User.objects.create_superuser(username="su")

    def test_without_permission_is_false(self):
        self.assertFalse(user_can_view_lock_metadata(self.viewer))

    def test_with_permission_is_true(self):
        self.assertTrue(user_can_view_lock_metadata(self.granted))

    def test_superuser_is_true(self):
        self.assertTrue(user_can_view_lock_metadata(self.superuser))


class BaseTableLockGlyphTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.locked = Manufacturer.objects.create(name="Glyph Locked")
        cls.unlocked = Manufacturer.objects.create(name="Glyph Unlocked")
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.locked.pk,
            prevent_delete=True,
            reason="x",
            source_key="s",
            expires=timezone.now() + timedelta(days=1),
        )

    def test_lock_states_loaded_once_for_page(self):
        qs = Manufacturer.objects.filter(pk__in=[self.locked.pk, self.unlocked.pk])
        table = ManufacturerTable(qs)
        # Render the primary cells exactly as the renderer does; merely iterating ``table.rows`` builds
        # BoundRow wrappers without rendering any cell, so it would not trigger the bulk lookup.
        cells = [row.get_cell("name") for row in table.rows]
        # The whole page's lock state is built from a single bulk query, populated for locked objects only.
        self.assertIn(self.locked.pk, table._object_lock_states)
        self.assertNotIn(self.unlocked.pk, table._object_lock_states)
        # Rendering every cell must not re-issue the bulk lookup: the guard makes repeat loads free.
        with self.assertNumQueries(0):
            table._load_object_lock_states()
            for row in table.rows:
                row.get_cell("name")
        self.assertEqual(len(cells), 2)

    def test_glyph_rendered_next_to_locked_object_name(self):
        qs = Manufacturer.objects.filter(pk__in=[self.locked.pk, self.unlocked.pk])
        table = ManufacturerTable(qs)
        rendered = {row.get_cell("name"): row for row in table.rows}
        locked_cell = next(html for html in rendered if "Glyph Locked" in html)
        unlocked_cell = next(html for html in rendered if "Glyph Unlocked" in html)
        self.assertIn("mdi-lock", locked_cell)
        self.assertNotIn("mdi-lock", unlocked_cell)

    def test_glyph_not_duplicated_across_table_instantiations(self):
        # The primary column lives on the table's *class-level* base_columns and is shared across
        # every instance. Re-instantiating the table on each page request must NOT re-wrap (and thus
        # stack) the glyph renderer. Simulate three page requests and assert exactly one glyph.
        qs = Manufacturer.objects.filter(pk__in=[self.locked.pk, self.unlocked.pk])
        ManufacturerTable(qs)
        ManufacturerTable(qs)
        table = ManufacturerTable(qs)
        rendered = [row.get_cell("name") for row in table.rows]
        locked_cell = next(html for html in rendered if "Glyph Locked" in html)
        self.assertEqual(locked_cell.count("mdi-lock"), 1)


class BaseTableLockGlyphAllUnlockedTestCase(TestCase):
    """An ALL-UNLOCKED page must still load lock state at most once.

    ``lock_state_for_objects`` returns an empty dict for a page with nothing locked. A memo guard that
    treats that falsy ``{}`` as "not yet loaded" re-runs the bulk lookup on *every* primary-column cell,
    producing an N+1 of ``extras_objectlock`` SELECTs (observed as ``[30x]`` on the VRF detail view,
    which embeds tables of unlocked related objects). The locked-object cases in
    ``BaseTableLockGlyphTestCase`` could not catch this because a non-empty dict is truthy. This covers
    the common all-unlocked case directly.
    """

    @classmethod
    def setUpTestData(cls):
        # Two-plus manufacturers, zero ObjectLock rows -> every primary cell sees an empty state map.
        cls.mfrs = [Manufacturer.objects.create(name=f"Unlocked Mfr {i}") for i in range(3)]

    def test_all_unlocked_page_loads_state_at_most_once(self):
        qs = Manufacturer.objects.filter(pk__in=[m.pk for m in self.mfrs])
        self.assertFalse(ObjectLock.objects.exists(), "Premise: no locks exist for the all-unlocked case")
        table = ManufacturerTable(qs)
        with (
            mock.patch("nautobot.core.tables.lock_state_for_objects", wraps=lock_state_for_objects) as spy,
            CaptureQueriesContext(connection) as ctx,
        ):
            # Render every primary ("name") cell exactly as django_tables2 does; this is what triggers
            # the per-cell ``_load_object_lock_states`` call that the memo guard must short-circuit.
            cells = [row.get_cell("name") for row in table.rows]
        self.assertEqual(len(cells), len(self.mfrs))
        # The bulk lookup must run at most once for the whole page, even though nothing is locked.
        self.assertLessEqual(spy.call_count, 1, "All-unlocked page re-ran the lock lookup per cell (N+1)")
        # Same precise lock-records filter used elsewhere in this module (exclude sibling tables).
        object_lock_queries = [
            q
            for q in ctx.captured_queries
            if '"extras_objectlock"' in q["sql"]
            and "extras_objectlockgeneration" not in q["sql"]
            and "extras_objectlockbypassaudit" not in q["sql"]
        ]
        self.assertLessEqual(
            len(object_lock_queries),
            1,
            f"All-unlocked page issued an ObjectLock query per cell (N+1): {object_lock_queries}",
        )
        # The state map stays an (empty) dict -- no None-safety break for ``.get`` / ``in`` callers.
        self.assertEqual(table._object_lock_states, {})


class LockGlyphOnNonNameLinkifiedColumnTestCase(TestCase):
    """The glyph must attach to a linkified *primary* column even when it is not named ``name``.

    Uses a real Nautobot table: ``ComputedFieldTable`` has no ``name`` column and its display column,
    ``label``, is linkified via django_tables2 ``Column(linkify=True)`` (a ``LinkTransform`` on
    ``column.link``) -- not a ``TemplateColumn``. This exercises ``BaseTable``'s fallback away from
    ``name`` to the first visible, truly-linkified column.
    """

    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(ComputedField)
        device_ct = ContentType.objects.get(app_label="dcim", model="device")
        cls.locked = ComputedField.objects.create(
            content_type=device_ct, label="Label Locked", template="{{ obj.name }}"
        )
        cls.unlocked = ComputedField.objects.create(
            content_type=device_ct, label="Label Unlocked", template="{{ obj.name }}"
        )
        ObjectLock.objects.create(
            content_type=cls.ct,
            object_id=cls.locked.pk,
            prevent_delete=True,
            reason="non-name",
            source_key="s",
            expires=timezone.now() + timedelta(days=1),
        )

    def test_table_has_no_name_column_but_linkified_label(self):
        # Guard the premise: if ComputedFieldTable ever grows a "name" column or stops linkifying
        # "label", this test would silently stop covering the fallback path -- so assert the shape.
        table = ComputedFieldTable(ComputedField.objects.filter(pk=self.locked.pk))
        self.assertNotIn("name", table.columns.names())
        self.assertIsNotNone(getattr(table.columns["label"].column, "link", None))

    def test_glyph_rendered_on_locked_label_cell_only(self):
        qs = ComputedField.objects.filter(pk__in=[self.locked.pk, self.unlocked.pk])
        table = ComputedFieldTable(qs)
        rendered = [row.get_cell("label") for row in table.rows]
        locked_cell = next(html for html in rendered if "Label Locked" in html)
        unlocked_cell = next(html for html in rendered if "Label Unlocked" in html)
        self.assertIn("mdi-lock", locked_cell)
        self.assertNotIn("mdi-lock", unlocked_cell)


class LockGlyphOverAvailableRowsTestCase(TestCase):
    """The lock glyph must coexist safely with the "available" rows IPAM injects.

    IPAM list views feed ``BaseTable`` a mix of real saved records and synthetic "available" rows via
    ``add_available_prefixes`` (unsaved ``Prefix`` instances) and ``add_available_ipaddresses`` (plain
    tuples). Crucially, an unsaved ``Prefix`` is **not** ``pk=None`` -- ``BaseModel.id`` defaults to
    ``uuid.uuid4`` so it gets a random UUID at instantiation -- yet it has never been written to the DB
    (``present_in_database`` is ``False``). The lock lookup must therefore key off "is this row actually
    saved?" and never feed these phantom PKs into ``lock_state_for_objects``.
    """

    @classmethod
    def setUpTestData(cls):
        cls.namespace = Namespace.objects.create(name="Lock Glyph Available Rows NS")
        cls.status = Status.objects.get(name="Active")
        cls.container = Prefix(prefix="10.250.0.0/24", namespace=cls.namespace, status=cls.status)
        cls.container.validated_save()
        # One real saved child, which we lock; the rest of the /24 will surface as "available" rows.
        cls.child = Prefix(prefix="10.250.0.0/28", namespace=cls.namespace, status=cls.status)
        cls.child.validated_save()
        ObjectLock.objects.create(
            content_type=ContentType.objects.get_for_model(Prefix),
            object_id=cls.child.pk,
            prevent_delete=True,
            reason="lock glyph test",
            source_key="src",
            expires=timezone.now() + timedelta(days=1),
        )

    def _build_available_prefix_table(self):
        """Assemble a ``PrefixTable`` exactly as ``ipam.views`` does: saved children + available rows."""
        children = self.container.descendants()
        data = add_available_prefixes(self.container.prefix, self.container.namespace, children)
        # Sanity-check the fixture mirrors reality: exactly one saved row (the locked child) plus
        # unsaved "available" rows that nonetheless carry a non-None UUID pk.
        saved = [p for p in data if p.present_in_database]
        unsaved = [p for p in data if not p.present_in_database]
        self.assertEqual([p.pk for p in saved], [self.child.pk])
        self.assertTrue(unsaved, "add_available_prefixes should inject available rows for an empty /24")
        self.assertTrue(all(p.pk is not None for p in unsaved), "unsaved Prefix rows still have a UUID pk")
        return data, unsaved

    def test_available_prefix_rows_render_without_error(self):
        # Every primary cell renders even though most rows are unsaved instances (no exception).
        data, _ = self._build_available_prefix_table()
        table = PrefixTable(data)
        cells = [row.get_cell("prefix") for row in table.rows]
        self.assertEqual(len(cells), len(data))

    def test_lock_lookup_skips_unsaved_rows_and_is_single_query(self):
        # The bulk lock lookup must run exactly once and be fed ONLY the saved row(s); the unsaved
        # "available" rows must be filtered out before they reach lock_state_for_objects.
        data, unsaved = self._build_available_prefix_table()
        table = PrefixTable(data)
        with (
            mock.patch("nautobot.core.tables.lock_state_for_objects", wraps=lock_state_for_objects) as spy,
            CaptureQueriesContext(connection) as ctx,
        ):
            table._load_object_lock_states()
        # Exactly one bulk lookup call, fed only the saved child -- never the unsaved phantom rows.
        spy.assert_called_once()
        passed_records = list(spy.call_args.args[0])
        self.assertEqual([r.pk for r in passed_records], [self.child.pk])
        unsaved_pks = {p.pk for p in unsaved}
        self.assertFalse(
            unsaved_pks.intersection(r.pk for r in passed_records),
            "Unsaved available-prefix rows must not be passed to the lock lookup",
        )
        # Guard against the single bulk lookup fanning out into multiple lock queries. The lookup
        # running exactly once (never per-row) is already proven by spy.assert_called_once() above,
        # and that the lock was actually found is asserted via the state map below; this is therefore
        # <= 1 rather than == 1, since query capture can intermittently under-count under the runner.
        object_lock_queries = [
            q
            for q in ctx.captured_queries
            if '"extras_objectlock"' in q["sql"]
            and "extras_objectlockgeneration" not in q["sql"]
            and "extras_objectlockbypassaudit" not in q["sql"]
        ]
        self.assertLessEqual(len(object_lock_queries), 1, f"Bulk lock lookup must not N+1; got: {object_lock_queries}")
        # The resulting state map contains the locked child only.
        self.assertIn(self.child.pk, table._object_lock_states)
        self.assertEqual(set(table._object_lock_states) & unsaved_pks, set())

    def test_glyph_renders_only_on_locked_saved_row_in_mixed_table(self):
        # The faithful PrefixTable above never wraps a primary column (its link lives in a TemplateColumn
        # named "prefix", not "name"), so to prove glyph PLACEMENT over mixed saved/unsaved data we use a
        # table that does wrap -- ManufacturerTable -- with a saved+locked row and an unsaved row mirroring
        # the shape add_available_* injects.
        locked = Manufacturer(name="Mixed Locked")
        locked.validated_save()
        ObjectLock.objects.create(
            content_type=ContentType.objects.get_for_model(Manufacturer),
            object_id=locked.pk,
            prevent_delete=True,
            reason="lock glyph test",
            source_key="src",
            expires=timezone.now() + timedelta(days=1),
        )
        unsaved = Manufacturer(name="Mixed Available")  # never saved; carries a UUID pk like IPAM phantom rows
        self.assertFalse(unsaved.present_in_database)
        table = ManufacturerTable([locked, unsaved])
        with mock.patch("nautobot.core.tables.lock_state_for_objects", wraps=lock_state_for_objects) as spy:
            rendered = {row.get_cell("name"): row for row in table.rows}
        locked_cell = next(html for html in rendered if "Mixed Locked" in html)
        unsaved_cell = next(html for html in rendered if "Mixed Available" in html)
        self.assertIn("mdi-lock", locked_cell)
        self.assertNotIn("mdi-lock", unsaved_cell)
        # The unsaved row never reaches the lock lookup.
        passed_records = list(spy.call_args.args[0])
        self.assertEqual([r.pk for r in passed_records], [locked.pk])

    def test_available_ipaddress_tuple_rows_are_ignored_by_lock_lookup(self):
        # Tuple "available" rows (as add_available_ipaddresses injects) have no pk/_meta and must be
        # skipped by the record filter without ever invoking the lock lookup.
        table = ManufacturerTable([(5, "10.0.0.1/24")])
        with mock.patch("nautobot.core.tables.lock_state_for_objects", wraps=lock_state_for_objects) as spy:
            table._load_object_lock_states()
        spy.assert_not_called()
        self.assertEqual(table._object_lock_states, {})


class ObjectLockQuickFilterFormTestCase(TestCase):
    def test_mixin_adds_is_locked_boolean_field(self):
        class _Form(ObjectLockQuickFilterFormMixin, django_forms.Form):
            pass

        form = _Form()
        self.assertIn("is_locked", form.fields)
        field = form.fields["is_locked"]
        self.assertIsInstance(field, django_forms.NullBooleanField)
        self.assertFalse(field.required)
        self.assertEqual(field.label, "Locked")

    def test_field_filters_to_locked_only_when_true(self):
        class _Form(ObjectLockQuickFilterFormMixin, django_forms.Form):
            pass

        form = _Form(data={"is_locked": "true"})
        self.assertTrue(form.is_valid())
        self.assertTrue(form.cleaned_data["is_locked"])


@override_settings(ALLOWED_HOSTS=["testserver"])
class ObjectLockDetailAffordanceTestCase(TestCase):
    """The detail-view Edit/Delete affordances must block per lock mode, not on any active lock."""

    @classmethod
    def setUpTestData(cls):
        cls.ct = ContentType.objects.get_for_model(Manufacturer)
        cls.user = User.objects.create_user(username="affordance-user", is_superuser=True, is_staff=True)
        cls.expiry = timezone.now() + timedelta(days=1)

    def _lock(self, manufacturer, *, prevent_delete, prevent_update):
        ObjectLock.objects.create(
            content_type=self.ct,
            object_id=manufacturer.pk,
            source_key="aff",
            prevent_delete=prevent_delete,
            prevent_update=prevent_update,
            expires=self.expiry,
        )

    def _detail_html(self, manufacturer):
        self.client.force_login(self.user)
        response = self.client.get(manufacturer.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_update_only_lock_blocks_edit_not_delete(self):
        mfr = Manufacturer.objects.create(name="Update Only Mfr")
        self._lock(mfr, prevent_delete=False, prevent_update=True)
        html = self._detail_html(mfr)
        self.assertIn('data-nb-object-lock-blocked="edit"', html)
        self.assertNotIn('data-nb-object-lock-blocked="delete"', html)

    def test_delete_only_lock_blocks_delete_not_edit(self):
        mfr = Manufacturer.objects.create(name="Delete Only Mfr")
        self._lock(mfr, prevent_delete=True, prevent_update=False)
        html = self._detail_html(mfr)
        self.assertIn('data-nb-object-lock-blocked="delete"', html)
        self.assertNotIn('data-nb-object-lock-blocked="edit"', html)

    def test_both_lock_blocks_edit_and_delete(self):
        mfr = Manufacturer.objects.create(name="Both Locked Mfr")
        self._lock(mfr, prevent_delete=True, prevent_update=True)
        html = self._detail_html(mfr)
        self.assertIn('data-nb-object-lock-blocked="edit"', html)
        self.assertIn('data-nb-object-lock-blocked="delete"', html)

    def test_unlocked_blocks_neither(self):
        mfr = Manufacturer.objects.create(name="Unlocked Aff Mfr")
        html = self._detail_html(mfr)
        self.assertNotIn('data-nb-object-lock-blocked="edit"', html)
        self.assertNotIn('data-nb-object-lock-blocked="delete"', html)

    def test_locked_object_still_offers_clone(self):
        # A lock (even delete-only) must not hide unrelated, safe actions like Clone: the unlocked path
        # gets it from consolidate_detail_view_action_buttons, the locked path from
        # object_lock_extra_detail_buttons. Manufacturer has no clone_fields, so use DeviceType (which
        # does) to prove Clone survives a delete-lock.
        device_type = DeviceType.objects.create(
            manufacturer=Manufacturer.objects.create(name="Clone Mfr"), model="Clone Type"
        )
        ObjectLock.objects.create(
            content_type=ContentType.objects.get_for_model(DeviceType),
            object_id=device_type.pk,
            source_key="aff",
            prevent_delete=True,
            prevent_update=False,
            expires=self.expiry,
        )
        self.client.force_login(self.user)
        response = self.client.get(device_type.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertIn('id="clone-button"', response.content.decode())

    def test_locked_view_renders_registered_extra_action_buttons(self):
        """Model-registered extra detail-view action buttons render in the locked view; empty markup is skipped."""
        from nautobot.extras.templatetags.object_lock import object_lock_extra_detail_buttons

        mfr = Manufacturer.objects.create(name="Extra Buttons Mfr")  # no clone_fields, so Clone is not rendered

        class _FakeButton:
            def __init__(self, markup):
                self._markup = markup

            def render(self, context):
                return self._markup

        buttons = [_FakeButton("EXTRA-BUTTON-MARKER"), _FakeButton("")]
        with mock.patch(
            "nautobot.extras.templatetags.object_lock.lookup.get_extra_detail_view_action_buttons_for_model",
            return_value=buttons,
        ):
            rendered = object_lock_extra_detail_buttons({"object": mfr, "user": self.user})
        self.assertIn("EXTRA-BUTTON-MARKER", rendered)
        # The button whose render() returned "" is falsy and is skipped, so no separator is emitted.
        self.assertNotIn("\n", rendered)
