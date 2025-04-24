from django.test import TestCase

from nautobot.circuits.models import Circuit
from nautobot.circuits.tables import CircuitTable
from nautobot.core.models.querysets import count_related
from nautobot.dcim.models import Device, InventoryItem, Location, LocationType, Rack, RackGroup
from nautobot.dcim.tables import InventoryItemTable, LocationTable, LocationTypeTable, RackGroupTable
from nautobot.extras.models import JobLogEntry
from nautobot.extras.tables import JobLogEntryTable
from nautobot.tenancy.tables import TenantGroupTable
from nautobot.wireless.models import WirelessNetwork
from nautobot.wireless.tables import WirelessNetworkTable


class TableTestCase(TestCase):
    maxDiff = None

    def _validate_sorted_tree_queryset_same_with_table_queryset(self, queryset, table_class, field_name):
        with self.subTest(f"Assert sorting {table_class.__name__} on '{field_name}'"):
            table = table_class(queryset.with_tree_fields(), order_by=field_name)
            table_queryset_data = table.data.data.values_list("pk", flat=True)
            sorted_queryset = queryset.with_tree_fields().extra(order_by=[field_name]).values_list("pk", flat=True)
            self.assertEqual(list(table_queryset_data), list(sorted_queryset))

    def test_tree_model_table_orderable(self):
        """Assert TreeNode model table are orderable."""
        location_type = LocationType.objects.get(name="Campus")
        locations = Location.objects.filter(location_type=location_type)
        devices = Device.objects.all()

        for i in range(3):
            RackGroup.objects.create(name=f"Rack Group {i}", location=locations[i])
            InventoryItem.objects.create(
                device=devices[i], name=f"Inventory Item {i}", manufacturer=devices[i].device_type.manufacturer
            )

        RackGroup.objects.create(
            name="Rack Group 3",
            location=locations[2],
            parent=RackGroup.objects.last(),
        )
        InventoryItem.objects.create(
            name="Inventory Item 3",
            device=devices[3],
            manufacturer=devices[3].device_type.manufacturer,
            parent=InventoryItem.objects.last(),
        )

        tree_node_model_tables = [
            LocationTable,
            LocationTypeTable,
            RackGroupTable,
            InventoryItemTable,
            TenantGroupTable,
        ]

        # Each of the table has at-least two sortable field_names in the field_names
        model_field_names = ["name", "location", "parent", "location_type", "manufacturer"]
        for table_class in tree_node_model_tables:
            queryset = table_class.Meta.model.objects.all()
            table_avail_fields = set(model_field_names) & set(table_class.Meta.fields)
            for table_field_name in table_avail_fields:
                self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, table_class, table_field_name)
                self._validate_sorted_tree_queryset_same_with_table_queryset(
                    queryset, table_class, f"-{table_field_name}"
                )

        # Test for `rack_count`
        queryset = RackGroupTable.Meta.model.objects.annotate(rack_count=count_related(Rack, "rack_group")).all()
        self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, RackGroupTable, "rack_count")
        self._validate_sorted_tree_queryset_same_with_table_queryset(queryset, RackGroupTable, "-rack_count")

    def test_base_table_apis(self):
        """
        Test BaseTable APIs, specifically visible_columns and configurable_columns.
        Assert that they gave the correct results.
        """
        # Wireless Network Table
        wn_table = WirelessNetworkTable(WirelessNetwork.objects.all(), exclude=["enabled", "hidden"])
        wn_table.columns.hide("description")
        expected_visible_columns = [
            "name",
            "ssid",
            "mode",
            "authentication",
            "actions",
        ]
        expected_configurable_columns = [
            ("name", "Name"),
            ("ssid", "SSID"),
            ("mode", "Mode"),
            ("authentication", "Authentication"),
            ("secret", "Secret"),
            ("description", "Description"),
            ("tags", "Tags"),
            ("dynamic_group_count", "Dynamic Groups"),
        ]
        self.assertEqual(wn_table.visible_columns, expected_visible_columns)
        self.assertEqual(wn_table.configurable_columns, expected_configurable_columns)

        # Location Table
        location_table = LocationTable(Location.objects.all(), exclude=["parent", "tenant"])
        location_table.columns.hide("description")
        location_table.columns.hide("tags")
        expected_visible_columns = ["name", "status", "actions"]
        expected_configurable_columns = [
            ("name", "Name"),
            ("status", "Status"),
            ("location_type", "Location type"),
            ("description", "Description"),
            ("facility", "Facility"),
            ("asn", "ASN"),
            ("time_zone", "Time zone"),
            ("physical_address", "Physical address"),
            ("shipping_address", "Shipping address"),
            ("latitude", "Latitude"),
            ("longitude", "Longitude"),
            ("contact_name", "Contact name"),
            ("contact_phone", "Contact phone"),
            ("contact_email", "Contact E-mail"),
            ("tags", "Tags"),
            ("dynamic_group_count", "Dynamic Groups"),
            ("cf_example_app_auto_custom_field", "Example App Automatically Added Custom Field"),
        ]
        self.assertEqual(location_table.visible_columns, expected_visible_columns)
        self.assertEqual(location_table.configurable_columns, expected_configurable_columns)

        # Circuit Table
        circuit_table = CircuitTable(Circuit.objects.all(), exclude=["provider", "circuit_termination_a"])
        circuit_table.columns.hide("tags")
        expected_visible_columns = [
            "cid",
            "circuit_type",
            "status",
            "circuit_termination_z",
            "description",
            "example_app_provider_asn",
            "actions",
        ]
        expected_configurable_columns = [
            ("cid", "ID"),
            ("circuit_type", "Circuit type"),
            ("status", "Status"),
            ("tenant", "Tenant"),
            ("circuit_termination_z", "Side Z"),
            ("install_date", "Date installed"),
            ("commit_rate", "Commit rate (Kbps)"),
            ("description", "Description"),
            ("tags", "Tags"),
            ("example_app_provider_asn", "Provider ASN"),
            ("dynamic_group_count", "Dynamic Groups"),
        ]
        self.assertEqual(circuit_table.visible_columns, expected_visible_columns)
        self.assertEqual(circuit_table.configurable_columns, expected_configurable_columns)

        # Job Log Entry Table (Job Log Entry is not Dynamic Group associable)
        job_log_entry_table = JobLogEntryTable(JobLogEntry.objects.all(), exclude=["created", "message"])
        job_log_entry_table.columns.hide("log_level")
        expected_visible_columns = ["grouping", "log_object"]
        expected_configurable_columns = [
            ("grouping", "Grouping"),
            ("log_level", "Level"),
            ("log_object", "Object"),
        ]
        self.assertEqual(job_log_entry_table.visible_columns, expected_visible_columns)
        self.assertEqual(job_log_entry_table.configurable_columns, expected_configurable_columns)
