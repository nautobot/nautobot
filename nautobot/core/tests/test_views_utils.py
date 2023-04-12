from django.test import TestCase

from nautobot.core.views.utils import check_filter_for_display

from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.models import DeviceRedundancyGroup


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
                "display": "Device Redundancy Groups (name or ID)",
                "values": [{"name": str(example_obj.pk), "display": str(example_obj)}],
            }

            self.assertEqual(
                check_filter_for_display(device_filter_set_filters, "device_redundancy_group", [str(example_obj.pk)]),
                expected_output,
            )

        # TODO(glenn): We need some filters that *aren't* getting updated to the new pattern - maybe in example_plugin?
        # with self.subTest("Test get value display (also legacy filter ModelMultipleChoiceFilter)"):
        #     example_obj = DeviceType.objects.first()
        #     expected_output = {
        #         "name": "device_type_id",
        #         "display": "Device type (ID)",
        #         "values": [{"name": str(example_obj.pk), "display": example_obj.display}],
        #     }

        #     self.assertEqual(
        #         check_filter_for_display(device_filter_set_filters, "device_type_id", [str(example_obj.pk)]),
        #         expected_output,
        #     )

        # with self.subTest("Test skip non-UUID value display (legacy, ex: ModelMultipleChoiceFilter)"):
        #     expected_output = {
        #         "name": "manufacturer",
        #         "display": "Manufacturer (slug)",
        #         "values": [{"name": "fake_slug", "display": "fake_slug"}],
        #     }

        # with self.assertEqual(
        #     check_filter_for_display(device_filter_set_filters, "manufacturer", ["fake_slug"]), expected_output
        # )
