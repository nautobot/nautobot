from django.test import TestCase
from django.contrib.contenttypes.models import ContentType

from nautobot.core.utilities import check_filter_for_display, get_filter_field_label, _field_name_to_display

from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.models import Device, DeviceType, DeviceRedundancyGroup
from nautobot.extras.choices import RelationshipTypeChoices
from nautobot.extras.models import Relationship, CustomField


class CheckFilterForDisplayTest(TestCase):
    def test_check_filter_for_display(self):
        """Validate the operation of check_filter_for_display()."""

        device_filter_set_filters = DeviceFilterSet().get_filters()

        with self.subTest("Test invalid filter case (field_name not found)"):
            expected_output = {
                "name": "fake_field_name",
                "display": "fake_field_name",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "fake_field_name", ["example_field_value"]),
                expected_output,
            )

        with self.subTest("Test values are converted to list"):
            expected_output = {
                "name": "fake_field_name",
                "display": "fake_field_name",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "fake_field_name", "example_field_value"),
                expected_output,
            )

        with self.subTest("Test get field label, none exists (fallback)"):
            expected_output = {
                "name": "id",
                "display": "Id",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "id", ["example_field_value"]), expected_output
            )

        with self.subTest("Test get field label, exists"):
            expected_output = {
                "name": "has_interfaces",
                "display": "Has interfaces",
                "values": [{"name": "example_field_value", "display": "example_field_value"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "has_interfaces", ["example_field_value"]),
                expected_output,
            )

        with self.subTest(
            "Test get value display, falls back to string representation (also NaturalKeyOrPKMultipleChoiceFilter)"
        ):
            example_obj = DeviceRedundancyGroup.objects.first()
            expected_output = {
                "name": "device_redundancy_group",
                "display": "Device Redundancy Groups (slug or ID)",
                "values": [{"name": str(example_obj.pk), "display": str(example_obj)}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "device_redundancy_group", [str(example_obj.pk)]),
                expected_output,
            )

        with self.subTest("Test get value display (also legacy filter ModelMultipleChoiceFilter)"):
            example_obj = DeviceType.objects.first()
            expected_output = {
                "name": "device_type_id",
                "display": "Device type (ID)",
                "values": [{"name": str(example_obj.pk), "display": example_obj.display}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "device_type_id", [str(example_obj.pk)]),
                expected_output,
            )

        with self.subTest("Test skip non-UUID value display (legacy, ex: ModelMultipleChoiceFilter)"):
            expected_output = {
                "name": "manufacturer",
                "display": "Manufacturer (slug)",
                "values": [{"name": "fake_slug", "display": "fake_slug"}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "manufacturer", ["fake_slug"]), expected_output
            )


class GetFilterFieldLabelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        device_ct = ContentType.objects.get_for_model(Device)
        cls.peer_relationship = Relationship(
            name="HA Device Peer",
            slug="ha_device_peer",
            source_type=device_ct,
            destination_type=device_ct,
            source_label="Peer",
            destination_label="Peer",
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )
        cls.peer_relationship.validated_save()

        cls.custom_field = CustomField(slug="labeled_custom_field", label="Moo!", type="text")
        cls.custom_field.validated_save()
        cls.custom_field.content_types.add(device_ct)

    def test_get_filter_field_label(self):
        """Validate the operation of get_filter_field_label()."""

        device_filter_set_filters = DeviceFilterSet().filters

        with self.subTest("Simple field name"):
            self.assertEqual(get_filter_field_label(device_filter_set_filters["id"]), "Id")

        with self.subTest("Semi-complex field name"):
            self.assertEqual(get_filter_field_label(device_filter_set_filters["has_interfaces"]), "Has interfaces")

        with self.subTest("Relationship field name"):
            self.assertEqual(
                get_filter_field_label(device_filter_set_filters[f"cr_{self.peer_relationship.slug}__peer"]),
                self.peer_relationship.source_label,
            )

        with self.subTest("Custom field with label"):
            self.assertEqual(
                get_filter_field_label(device_filter_set_filters[f"cf_{self.custom_field.slug}"]),
                "Moo!",
            )


class FieldNameToDisplayTest(TestCase):
    def test__field_name_to_display(self):
        """Validate the operation of _field_name_to_display()."""

        with self.subTest("id => Id"):
            self.assertEqual(_field_name_to_display("id"), "Id")

        with self.subTest("device_type => Device Type"):
            self.assertEqual(_field_name_to_display("device_type"), "Device type")

        with self.subTest("_custom_field_data__site_type => Site Type"):
            self.assertEqual(_field_name_to_display("_custom_field_data__site_type"), "Site type")

        with self.subTest("cr_sister_sites__peer => Peer"):
            # This shouldn't ever be an input because get_filter_field_label
            # will use the label from the custom field instead of the field name
            self.assertEqual(_field_name_to_display("cr_sister_sites__peer"), "Cr_sister_sites peer")
