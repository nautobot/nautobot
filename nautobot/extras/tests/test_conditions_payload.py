"""Tests for `nautobot.extras.conditions.payload`."""

from types import SimpleNamespace
from unittest import TestCase

from django.test import tag

from nautobot.extras.conditions.payload import build_event_payload, event_value, field_value

# The payload's documented shape. Condition expressions read these names; changing this set is an
# API change, and this constant existing in the tests is what makes that change loud.
PAYLOAD_KEYS = {"event", "timestamp", "model", "username", "request_id", "data", "snapshots"}

SNAPSHOTS = {"prechange": {"status": "Staged"}, "postchange": {"status": "Active"}, "differences": {}}


def make_object_change(**overrides):
    """A minimal stand-in for ObjectChange: just the attributes the builder reads."""

    def _fail_get_snapshots():
        raise AssertionError("get_snapshots() must not be called when snapshots were provided")

    defaults = {
        "action": "update",
        "time": "2026-08-27T10:00:00+00:00",
        "changed_object_type": SimpleNamespace(model="device"),
        "user_name": "kasia",
        "request_id": "req-1",
        # `object_data` is deliberately absent: the builder reads only `object_data_v2`, so a
        # reintroduced fallback to the older field fails loudly here instead of passing quietly.
        "object_data_v2": {"name": "sw-01", "status": {"id": "u1", "name": "Active"}},
        "get_snapshots": _fail_get_snapshots,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@tag("unit")
class EventValueTest(TestCase):
    """Reduction of a serialized field to the scalar a condition compares against."""

    def test_v2_related_object_reduces_to_name(self):
        value = {"id": "b1c0", "url": "/api/...", "name": "Active", "display": "Active"}
        self.assertEqual(event_value(value), "Active")

    def test_reduction_key_priority(self):
        """`value` outranks `name` outranks `display` outranks `id` - the order is contract."""
        self.assertEqual(event_value({"value": "v", "name": "n", "display": "d", "id": "i"}), "v")
        self.assertEqual(event_value({"name": "n", "display": "d", "id": "i"}), "n")
        self.assertEqual(event_value({"display": "d", "id": "i"}), "d")
        self.assertEqual(event_value({"id": "i"}), "i")

    def test_dict_without_known_keys_passes_whole(self):
        self.assertEqual(event_value({"weird": 1}), {"weird": 1})

    def test_legacy_bare_pk_passes_untouched(self):
        """A related object recorded as a bare UUID stays a bare UUID: recovering the name would take
        a query. Reachable both from an ObjectChange predating `object_data_v2` and from any model
        without an API serializer, so this is a standing limitation rather than a legacy-only one -
        recorded here, not papered over in the reduction."""
        self.assertEqual(event_value("b1c0f4b2-53ed-4b24-8750-7c7d31613d25"), "b1c0f4b2-53ed-4b24-8750-7c7d31613d25")

    def test_lists_normalize_element_by_element(self):
        tags = [{"id": "1", "name": "core"}, {"id": "2", "name": "warsaw"}]
        self.assertEqual(event_value(tags), ["core", "warsaw"])
        self.assertEqual(event_value(("a", {"name": "b"})), ["a", "b"])

    def test_scalars_and_none_pass_untouched(self):
        for value in ("Active", 9000, True, None):
            with self.subTest(value=value):
                self.assertEqual(event_value(value), value)


@tag("unit")
class FieldValueTest(TestCase):
    """Dotted-path lookup with every failure resolving to None, never an exception."""

    DATA = {
        "status": {"id": "u1", "name": "Active"},
        "primary_ip4": {"id": "u2", "address": "10.0.0.1/24"},
        "mtu": 9000,
    }

    def test_reduction_and_descent_agree(self):
        """`status` (reduced) and `status.name` (descended) are two roads to the same value.

        This also proves intermediate segments are not reduced: if they were, `status` would become
        the string "Active" before the `name` segment had anything to descend into.
        """
        self.assertEqual(field_value(self.DATA, "status"), "Active")
        self.assertEqual(field_value(self.DATA, "status.name"), "Active")

    def test_descent_reaches_past_the_reduction_keys(self):
        self.assertEqual(field_value(self.DATA, "status.id"), "u1")
        self.assertEqual(field_value(self.DATA, "primary_ip4.address"), "10.0.0.1/24")

    def test_missing_paths_are_none(self):
        for path in ("missing", "status.missing", "mtu.deeper", ""):
            with self.subTest(path=path):
                self.assertIsNone(field_value(self.DATA, path))

    def test_none_container_is_none(self):
        """The create case: `snapshots.prechange` is None, and a transition condition must get a
        quiet None to compare against, not an exception."""
        self.assertIsNone(field_value(None, "status"))

    def test_non_string_path_does_not_raise(self):
        self.assertIsNone(field_value(self.DATA, 123))


@tag("unit")
class BuildEventPayloadTest(TestCase):
    def test_shape_is_exactly_the_documented_keys(self):
        payload = build_event_payload(make_object_change(), SNAPSHOTS)
        self.assertEqual(set(payload), PAYLOAD_KEYS)

    def test_ingredients_land_where_documented(self):
        payload = build_event_payload(make_object_change(), SNAPSHOTS)
        self.assertEqual(payload["event"], "updated")
        self.assertEqual(payload["model"], "device")
        self.assertEqual(payload["username"], "kasia")
        self.assertEqual(payload["request_id"], "req-1")
        self.assertEqual(payload["data"]["name"], "sw-01")

    def test_event_labels_for_all_actions(self):
        """The payload speaks in past-tense labels; the rule's flags speak in bare actions."""
        for action, label in (("create", "created"), ("update", "updated"), ("delete", "deleted")):
            with self.subTest(action=action):
                payload = build_event_payload(make_object_change(action=action), SNAPSHOTS)
                self.assertEqual(payload["event"], label)

    def test_provided_snapshots_are_used_verbatim_without_a_query(self):
        """The hot path passes snapshots in; the builder must neither recompute nor copy them.

        Identity (assertIs) is deliberate: isolating actions from each other via deepcopy is the
        gate's job, per action - a copy here would hide that and pay it once too few.
        """
        payload = build_event_payload(make_object_change(), SNAPSHOTS)
        self.assertIs(payload["snapshots"], SNAPSHOTS)

    def test_omitted_snapshots_are_computed_exactly_once(self):
        calls = []

        def counting_get_snapshots():
            calls.append(1)
            return SNAPSHOTS

        oc = make_object_change(get_snapshots=counting_get_snapshots)
        payload = build_event_payload(oc)
        self.assertEqual(len(calls), 1)
        self.assertIs(payload["snapshots"], SNAPSHOTS)

    def test_data_is_the_v2_serialization_itself(self):
        """`data` is the serialized object, not the ObjectChange that carries it.

        This is the one assertion pinning `data` to the right attribute; without it, passing the row
        itself type-checks fine and every condition reading `data.<field>` silently stops matching.
        """
        oc = make_object_change()
        self.assertEqual(build_event_payload(oc, SNAPSHOTS)["data"], oc.object_data_v2)
        self.assertEqual(field_value(build_event_payload(oc, SNAPSHOTS)["data"], "status"), "Active")

    def test_timestamp_and_request_id_are_strings(self):
        class Uuidish:
            def __str__(self):
                return "as-string"

        oc = make_object_change(time=Uuidish(), request_id=Uuidish())
        payload = build_event_payload(oc, SNAPSHOTS)
        self.assertEqual(payload["timestamp"], "as-string")
        self.assertEqual(payload["request_id"], "as-string")
