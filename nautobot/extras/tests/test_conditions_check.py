"""Tests for `nautobot.extras.conditions.check`."""

from django.contrib.contenttypes.models import ContentType
from django.test import SimpleTestCase, tag

from nautobot.core.testing import TestCase as NautobotTestCase
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.conditions.check import check, check_row, RowVerdict, Verdict
from nautobot.extras.conditions.payload import build_event_payload
from nautobot.extras.conditions.presets import register_builtin_condition_presets
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import ObjectChange, Status

PAYLOAD = {
    "event": "updated",
    "timestamp": "2026-08-27T10:00:00+00:00",
    "model": "device",
    "username": "kasia",
    "request_id": "r",
    "data": {"name": "sw-01", "mtu": 9216, "status": {"id": "u2", "name": "Active"}, "tenant": None},
    "snapshots": {
        "prechange": {"name": "sw-01", "mtu": 1500, "status": {"id": "u1", "name": "Staged"}, "tenant": None},
        "postchange": {"name": "sw-01", "mtu": 9216, "status": {"id": "u2", "name": "Active"}, "tenant": None},
        "differences": {"added": {"mtu": 9216, "status": {"id": "u2", "name": "Active"}}},
    },
}


def expression(source, negate=False):
    return {"type": "expression", "source": source, "negate": negate}


def preset(key, negate=False, **values):
    return {"type": "preset", "preset": key, "values": values, "negate": negate}


class CheckTestCase(SimpleTestCase):
    def setUp(self):
        super().setUp()
        register_builtin_condition_presets()


@tag("unit")
class CheckRowTest(CheckTestCase):
    def test_truthy_result_passes(self):
        verdict = check_row(0, expression("data.mtu > 9000"), PAYLOAD)
        self.assertEqual(verdict, RowVerdict(index=0, row=expression("data.mtu > 9000"), passed=True))

    def test_falsy_results_fail(self):
        """Anything falsy fails: False, None, 0, "", [] - `bool(result)` is the contract."""
        for source in ("false", "none", "0", "''", "[]", "data.missing"):
            with self.subTest(source=source):
                self.assertFalse(check_row(0, expression(source), PAYLOAD).passed)

    def test_negate_inverts_a_verdict(self):
        self.assertFalse(check_row(0, expression("data.mtu > 9000", negate=True), PAYLOAD).passed)
        self.assertTrue(check_row(0, expression("data.mtu > 10000", negate=True), PAYLOAD).passed)

    def test_missing_nested_value_is_a_quiet_non_match(self):
        """`postchange` is None on a delete; the chain stays falsy instead of raising."""
        payload = {**PAYLOAD, "snapshots": {**PAYLOAD["snapshots"], "postchange": None}}
        verdict = check_row(0, expression("snapshots.postchange.status.name == 'Active'"), payload)
        self.assertFalse(verdict.passed)
        self.assertIsNone(verdict.error)

    def test_every_kind_of_failure_is_recorded_not_raised(self):
        cases = (
            ("not a row", "ConditionRowError"),
            ({"type": "regex"}, "ConditionRowError"),
            (preset("no_such_preset"), "ConditionRowError"),
            (preset("field_compare", field="mtu"), "ConditionPresetError"),
            (expression("data.mtu >"), "ConditionError"),
            (expression("1 / 0"), "ZeroDivisionError"),
            (preset("field_compare", field="mtu", operator="gt", value=["9000"]), "TypeError"),
            (expression("data.__init__()"), "SecurityError"),
        )
        for row, error_type in cases:
            with self.subTest(row=row):
                verdict = check_row(0, row, PAYLOAD)
                self.assertFalse(verdict.passed)
                self.assertTrue(verdict.error.startswith(f"{error_type}:"), verdict.error)

    def test_sandbox_hides_unsafe_attributes_without_an_error(self):
        """Reading an unsafe attribute yields Undefined, so the row is a quiet non-match; only calling
        one raises, and that is covered above."""
        verdict = check_row(0, expression("data.__class__.__name__ == 'dict'"), PAYLOAD)
        self.assertFalse(verdict.passed)
        self.assertIsNone(verdict.error)

    def test_negate_does_not_turn_an_error_into_a_pass(self):
        verdict = check_row(0, expression("1 / 0", negate=True), PAYLOAD)
        self.assertFalse(verdict.passed)
        self.assertIsNotNone(verdict.error)

    def test_index_and_row_are_reported_back(self):
        row = expression("true")
        verdict = check_row(7, row, PAYLOAD)
        self.assertEqual(verdict.index, 7)
        self.assertIs(verdict.row, row)


@tag("unit")
class CheckTest(CheckTestCase):
    def test_rows_are_anded(self):
        verdict = check([expression("true"), expression("false"), expression("true")], PAYLOAD)
        self.assertFalse(verdict.passed)
        self.assertEqual([row.passed for row in verdict.rows], [True, False, True])

    def test_every_row_is_checked_after_a_failure(self):
        verdict = check([expression("1 / 0"), expression("true")], PAYLOAD)
        self.assertEqual(len(verdict.rows), 2)
        self.assertTrue(verdict.rows[1].passed)

    def test_empty_conditions_pass(self):
        for conditions in ([], None):
            with self.subTest(conditions=conditions):
                verdict = check(conditions, PAYLOAD)
                self.assertEqual(verdict, Verdict(rows=(), passed=True))

    def test_as_dict_shape(self):
        as_dict = check([expression("true")], PAYLOAD).as_dict()
        self.assertEqual(set(as_dict), {"passed", "rows"})
        self.assertEqual(set(as_dict["rows"][0]), {"index", "row", "passed", "error"})


@tag("unit")
class BuiltinPresetsEndToEndTest(CheckTestCase):
    """Each shipped preset, through the real environment, on a payload shaped like production."""

    def test_field_transition(self):
        """Both ends are checked: the recorded change went Staged → Active, so a rule expecting
        Planned → Active does not match even though the destination is the same."""
        staged_to_active = preset("field_transition", field="status.name", **{"from": "Staged", "to": "Active"})
        planned_to_active = preset("field_transition", field="status.name", **{"from": "Planned", "to": "Active"})
        self.assertTrue(check([staged_to_active], PAYLOAD).passed)
        self.assertFalse(check([planned_to_active], PAYLOAD).passed)

    def test_field_transition_is_quiet_on_create_and_delete(self):
        row = preset("field_transition", field="status.name", **{"from": "Staged", "to": "Active"})
        created = {**PAYLOAD, "event": "created", "snapshots": {**PAYLOAD["snapshots"], "prechange": None}}
        deleted = {**PAYLOAD, "event": "deleted", "snapshots": {**PAYLOAD["snapshots"], "postchange": None}}
        for payload in (created, deleted):
            with self.subTest(event=payload["event"]):
                verdict = check([row], payload)
                self.assertFalse(verdict.passed)
                self.assertIsNone(verdict.rows[0].error)

    def test_field_changed(self):
        self.assertTrue(check([preset("field_changed", field="mtu")], PAYLOAD).passed)
        self.assertTrue(check([preset("field_changed", field="status.name")], PAYLOAD).passed)
        self.assertFalse(check([preset("field_changed", field="name")], PAYLOAD).passed)
        created = {**PAYLOAD, "event": "created", "snapshots": {**PAYLOAD["snapshots"], "prechange": None}}
        self.assertFalse(check([preset("field_changed", field="mtu")], created).passed)

    def test_field_compare(self):
        for row, expected in (
            (preset("field_compare", field="mtu", operator="gt", value=9000), True),
            (preset("field_compare", field="status.name", operator="=", value="Active"), True),
            (preset("field_compare", field="status.name", operator="in", value=["Active", "Planned"]), True),
            (preset("field_compare", field="status", operator="=", value="Active"), False),
        ):
            with self.subTest(values=row["values"]):
                self.assertIs(check([row], PAYLOAD).passed, expected)

    def test_user_is(self):
        self.assertTrue(check([preset("user_is", username="kasia")], PAYLOAD).passed)
        self.assertFalse(check([preset("user_is", username="sync")], PAYLOAD).passed)
        self.assertTrue(check([preset("user_is", username="sync", negate=True)], PAYLOAD).passed)

    def test_presets_and_expressions_mix(self):
        rows = [
            preset("field_transition", field="status.name", **{"from": "Staged", "to": "Active"}),
            expression("data.mtu > 9000 and username != 'sync'"),
        ]
        self.assertTrue(check(rows, PAYLOAD).passed)


class CheckAgainstRecordedChangeTest(NautobotTestCase):
    """Real change-log rows through the real payload builder, so the paths the presets assume - a
    relation is a mapping with a `name` - are checked against what the serializer actually records."""

    def setUp(self):
        super().setUp()
        register_builtin_condition_presets()
        location_ct = ContentType.objects.get_for_model(Location)
        self.staged = Status.objects.create(name="Check Staged")
        self.active = Status.objects.create(name="Check Active")
        for status in (self.staged, self.active):
            status.content_types.add(location_ct)
        location_type = LocationType.objects.create(name="Check Site")

        with web_request_context(self.user):
            location = Location.objects.create(name="Check Location", location_type=location_type, status=self.staged)
        location_pk = location.pk  # `delete()` would clear it; kept for the same reason
        with web_request_context(self.user):
            location.status = self.active
            location.save()

        changes = ObjectChange.objects.filter(changed_object_id=location_pk).select_related("changed_object_type")
        self.update = changes.get(action=ObjectChangeActionChoices.ACTION_UPDATE)
        self.payload = build_event_payload(self.update, self.update.get_snapshots())

    def test_relation_is_addressed_by_sub_field(self):
        """`status` is a mapping in `object_data_v2`; `status.name` reaches the value, `status` does not."""
        by_sub_field = preset("field_compare", field="status.name", operator="=", value="Check Active")
        by_relation = preset("field_compare", field="status", operator="=", value="Check Active")
        self.assertTrue(check([by_sub_field], self.payload).passed)
        self.assertFalse(check([by_relation], self.payload).passed)

    def test_transition_and_change_read_both_recorded_snapshots(self):
        rows = [
            preset("field_transition", field="status.name", **{"from": "Check Staged", "to": "Check Active"}),
            preset("field_changed", field="status.name"),
        ]
        verdict = check(rows, self.payload)
        self.assertTrue(verdict.passed, verdict.as_dict())

    def test_unchanged_field_did_not_change(self):
        self.assertFalse(check([preset("field_changed", field="name")], self.payload).passed)

    def test_user_is_the_recorded_user(self):
        self.assertTrue(check([preset("user_is", username=self.user.username)], self.payload).passed)

    def test_no_row_errors_on_a_real_payload(self):
        rows = [
            preset("field_compare", field="status.name", operator="in", value=["Check Active", "Other"]),
            expression("data.status.name == 'Check Active' and snapshots.prechange.status.name == 'Check Staged'"),
            expression("event == 'updated' and username == '" + self.user.username + "'"),
        ]
        verdict = check(rows, self.payload)
        self.assertTrue(verdict.passed, verdict.as_dict())
        self.assertTrue(all(row.error is None for row in verdict.rows))
