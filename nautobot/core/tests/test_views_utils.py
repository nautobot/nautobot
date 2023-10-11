from django.test import TestCase

from nautobot.core.models.querysets import count_related
from nautobot.core.views.utils import check_filter_for_display

from nautobot.dcim.filters import DeviceFilterSet
from nautobot.dcim.models import Device, DeviceRedundancyGroup, DeviceType, InventoryItem, Location, Manufacturer
from nautobot.extras.models import Role, Status


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


class CheckCountRelatedSubquery(TestCase):
    def test_count_related(self):
        """Assert that InventoryItems with the same Manufacuturers do not cause issues in count_related subquery."""
        location = Location.objects.filter(parent__isnull=False).first()
        manufacturer = Manufacturer.objects.create(name="New Manufacturer")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        device1 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice1",
            status=device_status,
            location=location,
        )
        self.manufacturer_1 = Manufacturer.objects.create(name="Manufacturer 1")
        self.manufacturer_2 = Manufacturer.objects.create(name="Manufacturer 2")
        self.manufacturer_3 = Manufacturer.objects.create(name="Manufacturer 3")
        self.parent_inventory_item_1 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturer_1, name="Parent Inv 1"
        )
        self.child_inventory_item_1 = InventoryItem.objects.create(
            device=device1,
            manufacturer=self.manufacturer_1,
            name="Parent Inv 1",
            parent=self.parent_inventory_item_1,
        )
        self.inventory_item_2 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturer_2, name="Inv 2"
        )
        self.inventory_item_3 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturer_3, name="Inv 3"
        )
        self.inventory_item_4 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturer_3, name="Inv 4"
        )
        queryset = Manufacturer.objects.annotate(inventory_item_count=count_related(InventoryItem, "manufacturer"))
        self.assertIsNotNone(queryset.count)
