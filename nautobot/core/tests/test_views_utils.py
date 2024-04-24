from django.db import ProgrammingError
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

        # TODO(glenn): We need some filters that *aren't* getting updated to the new pattern - maybe in example_app?
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
        """Assert that InventoryItems with the same Manufacturers do not cause issues in count_related subquery."""
        location = Location.objects.filter(parent__isnull=False).first()
        self.manufacturers = Manufacturer.objects.all()[:3]
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        device1 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            status=device_status,
            location=location,
        )
        self.parent_inventory_item_1 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[0], name="Parent Inv 1"
        )
        self.child_inventory_item_1 = InventoryItem.objects.create(
            device=device1,
            manufacturer=self.manufacturers[0],
            name="Child Inv 1",
            parent=self.parent_inventory_item_1,
        )
        self.inventory_item_2 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[1], name="Inv 2"
        )
        self.inventory_item_3 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[2], name="Inv 3"
        )
        self.inventory_item_4 = InventoryItem.objects.create(
            device=device1, manufacturer=self.manufacturers[2], name="Inv 4"
        )
        try:
            qs = Manufacturer.objects.annotate(inventory_item_count=count_related(InventoryItem, "manufacturer"))
            list(qs)
            self.assertEqual(qs.get(pk=self.manufacturers[0].pk).inventory_item_count, 2)
            self.assertEqual(qs.get(pk=self.manufacturers[1].pk).inventory_item_count, 1)
            self.assertEqual(qs.get(pk=self.manufacturers[2].pk).inventory_item_count, 2)
        except ProgrammingError:
            self.fail("count_related subquery failed with ProgrammingError")

        qs = Device.objects.annotate(
            manufacturer_count=count_related(Manufacturer, "inventory_items__device", distinct=True)
        )
        self.assertEqual(qs.get(pk=device1.pk).manufacturer_count, 3)
