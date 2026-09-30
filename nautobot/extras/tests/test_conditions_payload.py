"""Tests for `nautobot.extras.conditions.payload`."""

from unittest import mock, TestCase

from django.test import tag

from nautobot.core.testing import TestCase as NautobotTestCase
from nautobot.extras.choices import ObjectChangeActionChoices
from nautobot.extras.conditions.payload import build_event_payload, field_value
from nautobot.extras.context_managers import web_request_context
from nautobot.extras.models import ObjectChange, Status

# The keys condition expressions read.
PAYLOAD_KEYS = {"event", "timestamp", "model", "username", "request_id", "data", "snapshots"}


@tag("unit")
class FieldValueTest(TestCase):
    DATA = {
        "name": "sw-01",
        "mtu": 9216,
        "status": {"id": "u1", "name": "Active", "color": "4caf50"},
        "tenant": None,
        "primary_ip4": {"id": "u2", "address": "10.0.0.1/24"},
        "tags": [{"id": "1", "name": "core"}, {"id": "2", "name": "warsaw"}],
        "_custom_field_data": {"priority": 5},
    }

    def test_plain_fields(self):
        self.assertEqual(field_value(self.DATA, "name"), "sw-01")
        self.assertEqual(field_value(self.DATA, "mtu"), 9216)

    def test_relation_by_sub_field(self):
        self.assertEqual(field_value(self.DATA, "status.name"), "Active")
        self.assertEqual(field_value(self.DATA, "status.color"), "4caf50")
        self.assertEqual(field_value(self.DATA, "primary_ip4.address"), "10.0.0.1/24")

    def test_relation_without_sub_field_returns_the_mapping(self):
        self.assertEqual(field_value(self.DATA, "status"), self.DATA["status"])

    def test_list_returns_as_is_and_is_not_walked_into(self):
        self.assertEqual(field_value(self.DATA, "tags"), self.DATA["tags"])
        self.assertIsNone(field_value(self.DATA, "tags.name"))

    def test_nested_mapping_that_is_not_a_relation(self):
        self.assertEqual(field_value(self.DATA, "_custom_field_data.priority"), 5)

    def test_empty_containers(self):
        """An empty mapping or list at the path comes back as-is; walking into either yields None."""
        data = {"tags": [], "_custom_field_data": {}}
        self.assertEqual(field_value(data, "tags"), [])
        self.assertEqual(field_value(data, "_custom_field_data"), {})
        self.assertIsNone(field_value(data, "_custom_field_data.priority"))
        self.assertIsNone(field_value(data, "tags.name"))
        self.assertIsNone(field_value({}, "name"))

    def test_missing_paths_are_none(self):
        for path in ("missing", "status.missing", "mtu.deeper", "tenant.name", ""):
            with self.subTest(path=path):
                self.assertIsNone(field_value(self.DATA, path))

    def test_none_container_is_none(self):
        """`snapshots.prechange` is None on a create."""
        self.assertIsNone(field_value(None, "status.name"))

    def test_non_string_path_does_not_raise(self):
        self.assertIsNone(field_value(self.DATA, 123))


class BuildEventPayloadTest(NautobotTestCase):
    """The builder against real change-log rows: one create, one update, one delete of the same object."""

    def setUp(self):
        super().setUp()
        # One request per action: changes to the same object within a single request are merged
        # into one ObjectChange.
        with web_request_context(self.user):
            status = Status.objects.create(name="Payload Test Status")
        status_pk = status.pk  # `delete()` clears the instance's pk
        with web_request_context(self.user):
            status.description = "changed"
            status.save()
        with web_request_context(self.user):
            status.delete()
        changes = ObjectChange.objects.filter(changed_object_id=status_pk).select_related("changed_object_type")
        self.create_change = changes.get(action=ObjectChangeActionChoices.ACTION_CREATE)
        self.update_change = changes.get(action=ObjectChangeActionChoices.ACTION_UPDATE)
        self.delete_change = changes.get(action=ObjectChangeActionChoices.ACTION_DELETE)
        self.snapshots = self.update_change.get_snapshots()

    def test_shape_is_exactly_payload_keys(self):
        payload = build_event_payload(self.update_change, self.snapshots)
        self.assertEqual(set(payload), PAYLOAD_KEYS)

    def test_ingredients_land_under_their_keys(self):
        payload = build_event_payload(self.update_change, self.snapshots)
        self.assertEqual(payload["event"], "updated")
        self.assertEqual(payload["model"], "status")
        self.assertEqual(payload["username"], self.user.username)
        self.assertEqual(payload["request_id"], str(self.update_change.request_id))
        self.assertEqual(payload["timestamp"], str(self.update_change.time))
        self.assertEqual(field_value(payload["data"], "name"), "Payload Test Status")
        self.assertEqual(field_value(payload["data"], "description"), "changed")

    def test_event_labels_for_all_actions(self):
        for object_change, label in (
            (self.create_change, "created"),
            (self.update_change, "updated"),
            (self.delete_change, "deleted"),
        ):
            with self.subTest(action=object_change.action):
                payload = build_event_payload(object_change, object_change.get_snapshots())
                self.assertEqual(payload["event"], label)

    def test_timestamp_and_request_id_are_strings(self):
        payload = build_event_payload(self.update_change, self.snapshots)
        self.assertIsInstance(payload["timestamp"], str)
        self.assertIsInstance(payload["request_id"], str)

    def test_data_is_object_data_v2(self):
        payload = build_event_payload(self.update_change, self.snapshots)
        self.assertEqual(payload["data"], self.update_change.object_data_v2)

    def test_provided_snapshots_are_used_as_is_without_a_query(self):
        """Same object, not a copy, and nothing hits the database."""
        with self.assertNumQueries(0):
            payload = build_event_payload(self.update_change, self.snapshots)
        self.assertIs(payload["snapshots"], self.snapshots)

    def test_omitted_snapshots_are_computed_exactly_once(self):
        with mock.patch.object(ObjectChange, "get_snapshots", return_value=self.snapshots) as get_snapshots:
            payload = build_event_payload(self.update_change)
        get_snapshots.assert_called_once()
        self.assertIs(payload["snapshots"], self.snapshots)

    def test_snapshots_of_a_create_have_no_prechange(self):
        payload = build_event_payload(self.create_change, self.create_change.get_snapshots())
        self.assertIsNone(payload["snapshots"]["prechange"])
        self.assertEqual(field_value(payload["snapshots"]["postchange"], "name"), "Payload Test Status")
