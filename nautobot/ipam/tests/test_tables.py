from nautobot.core.models.querysets import count_related
from nautobot.core.testing import AssertNoRepeatedQueries, TestCase
from nautobot.dcim.models import Device, DeviceType, Interface, Manufacturer
from nautobot.dcim.models.locations import Location, LocationType
from nautobot.extras.models import Role, Status
from nautobot.ipam.choices import IPAddressTypeChoices
from nautobot.ipam.models import IPAddress, Namespace, Prefix
from nautobot.ipam.tables import IPAddressTable, PrefixTable
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface


class PrefixTableTestCase(TestCase):
    def _validate_sorted_queryset_same_with_table_queryset(self, queryset, table_class, field_name):
        with self.subTest(f"Assert sorting {table_class.__name__} on '{field_name}'"):
            table = table_class(queryset, order_by=field_name)
            table_queryset_data = table.data.data.values_list("pk", flat=True)
            sorted_queryset = queryset.order_by(field_name).values_list("pk", flat=True)
            self.assertEqual(list(table_queryset_data), list(sorted_queryset))

    def test_prefix_table_sort(self):
        """Assert TreeNode model table are orderable."""
        # Due to MySQL's lack of support for combining 'LIMIT' and 'ORDER BY' in a single query,
        # hence this approach.
        pk_list = Prefix.objects.all().values_list("pk", flat=True)[:20]
        pk_list = [str(pk) for pk in pk_list]
        queryset = Prefix.objects.filter(pk__in=pk_list)

        # Assets model names
        table_avail_fields = ["tenant", "vlan", "namespace"]
        for table_field_name in table_avail_fields:
            self._validate_sorted_queryset_same_with_table_queryset(queryset, PrefixTable, table_field_name)
            self._validate_sorted_queryset_same_with_table_queryset(queryset, PrefixTable, f"-{table_field_name}")

        # Assert `prefix`
        table_queryset_data = PrefixTable(queryset, order_by="prefix").data.data.values_list("pk", flat=True)
        prefix_queryset = queryset.order_by("network", "prefix_length").values_list("pk", flat=True)
        self.assertEqual(list(table_queryset_data), list(prefix_queryset))
        table_queryset_data = PrefixTable(queryset, order_by="-prefix").data.data.values_list("pk", flat=True)
        prefix_queryset = queryset.order_by("-network", "-prefix_length").values_list("pk", flat=True)
        self.assertEqual(list(table_queryset_data), list(prefix_queryset))

        # Assets `location_count`
        location_count_queryset = queryset.annotate(location_count=count_related(Location, "prefixes")).all()
        self._validate_sorted_queryset_same_with_table_queryset(location_count_queryset, PrefixTable, "location_count")
        self._validate_sorted_queryset_same_with_table_queryset(location_count_queryset, PrefixTable, "-location_count")


class IPAddressTableTestCase(TestCase):
    """Assert the Devices/Interfaces/Virtual Machines/VM Interfaces columns render names vs counts (#6614)."""

    @classmethod
    def setUpTestData(cls):
        namespace = Namespace.objects.create(name="IPAddressTable Test Namespace")
        prefix_status = Status.objects.get_for_model(Prefix).first()
        ip_status = Status.objects.get_for_model(IPAddress).first()
        prefix = Prefix.objects.create(prefix="10.99.0.0/24", namespace=namespace, status=prefix_status, type="network")

        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="IPAddressTable Device Type")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device_1 = Device.objects.create(
            name="IPAddressTable Device 1",
            location=location,
            device_type=device_type,
            role=device_role,
            status=device_status,
        )
        cls.device_2 = Device.objects.create(
            name="IPAddressTable Device 2",
            location=location,
            device_type=device_type,
            role=device_role,
            status=device_status,
        )

        intf_status = Status.objects.get_for_model(Interface).first()
        cls.interface_1a = Interface.objects.create(device=cls.device_1, name="Eth1a", status=intf_status)
        cls.interface_1b = Interface.objects.create(device=cls.device_1, name="Eth1b", status=intf_status)
        cls.interface_2 = Interface.objects.create(device=cls.device_2, name="Eth2", status=intf_status)

        cluster_type = ClusterType.objects.create(name="IPAddressTable Cluster Type")
        cluster = Cluster.objects.create(name="IPAddressTable Cluster", cluster_type=cluster_type)
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        cls.virtual_machine = VirtualMachine.objects.create(
            cluster=cluster, name="IPAddressTable VM 1", status=vm_status
        )
        vm_intf_status = Status.objects.get_for_model(VMInterface).first()
        cls.vm_interface = VMInterface.objects.create(
            virtual_machine=cls.virtual_machine, name="VM Eth1", status=vm_intf_status
        )

        def _make_ip(host):
            return IPAddress.objects.create(
                parent=prefix, address=host, status=ip_status, type=IPAddressTypeChoices.TYPE_HOST
            )

        # IP on a single interface of a single device.
        cls.ip_single = _make_ip("10.99.0.1/24")
        cls.interface_1a.add_ip_addresses(cls.ip_single)

        # IP on two interfaces of the same device.
        cls.ip_same_device = _make_ip("10.99.0.2/24")
        cls.interface_1a.add_ip_addresses(cls.ip_same_device)
        cls.interface_1b.add_ip_addresses(cls.ip_same_device)

        # IP on interfaces across two different devices.
        cls.ip_multi_device = _make_ip("10.99.0.3/24")
        cls.interface_1a.add_ip_addresses(cls.ip_multi_device)
        cls.interface_2.add_ip_addresses(cls.ip_multi_device)

        # IP on a single VM interface.
        cls.ip_vm = _make_ip("10.99.0.4/24")
        cls.vm_interface.add_ip_addresses(cls.ip_vm)

    def _render_cell(self, ip_address, column_name):
        """Render a single IP address's cell for the given column, via the full BaseTable pipeline."""
        table = IPAddressTable(IPAddress.objects.filter(pk=ip_address.pk))
        bound_row = table.rows[0]
        return bound_row.get_cell(column_name)  # pylint: disable=no-member  # BoundRows[0] is a BoundRow

    def test_single_device_single_interface_shows_names(self):
        device_cell = self._render_cell(self.ip_single, "interface_parent_count")
        self.assertIn(self.device_1.name, device_cell)
        self.assertNotIn("badge", device_cell)
        interface_cell = self._render_cell(self.ip_single, "interface_count")
        self.assertIn(self.interface_1a.name, interface_cell)
        self.assertNotIn("badge", interface_cell)

    def test_single_device_multiple_interfaces_shows_device_name_and_interface_count(self):
        # One distinct device -> render the device name, not a count badge.
        device_cell = self._render_cell(self.ip_same_device, "interface_parent_count")
        self.assertIn(self.device_1.name, device_cell)
        self.assertNotIn("badge", device_cell)
        # Two interfaces -> render a count badge.
        interface_cell = self._render_cell(self.ip_same_device, "interface_count")
        self.assertIn('class="badge bg-primary">2</a>', interface_cell)

    def test_multiple_devices_shows_counts(self):
        device_cell = self._render_cell(self.ip_multi_device, "interface_parent_count")
        self.assertIn('class="badge bg-primary">2</a>', device_cell)
        interface_cell = self._render_cell(self.ip_multi_device, "interface_count")
        self.assertIn('class="badge bg-primary">2</a>', interface_cell)

    def test_single_vm_interface_shows_names(self):
        vm_cell = self._render_cell(self.ip_vm, "vm_interface_parent_count")
        self.assertIn(self.virtual_machine.name, vm_cell)
        self.assertNotIn("badge", vm_cell)
        vm_interface_cell = self._render_cell(self.ip_vm, "vm_interface_count")
        self.assertIn(self.vm_interface.name, vm_interface_cell)
        self.assertNotIn("badge", vm_interface_cell)

    def test_dual_interfaces_prefetch_does_not_collide(self):
        """Both the Interfaces and Devices columns prefetch `interfaces`; evaluating the table must not raise."""
        table = IPAddressTable(IPAddress.objects.filter(parent__namespace__name="IPAddressTable Test Namespace"))
        # Force queryset evaluation through the prefetch machinery; this raised ValueError before the
        # distinct to_attr fix ("'interfaces' lookup was already seen with a different queryset").
        self.assertEqual(len(list(table.rows)), 4)

    def test_nested_lookup_columns_avoid_n_plus_one_queries(self):
        """The Devices/Virtual Machines columns must render without per-row queries.

        The single-object display relies on a prefetch whose queryset `select_related`s the trailing
        relation (`device`/`virtual_machine`). If that select_related is ever dropped, accessing it would
        fall back to one query per row. Render enough single-device rows that such a regression would trip
        `AssertNoRepeatedQueries`.
        """
        # Add IPs (all on the same interface/device) so the table has well more rows than the N+1 threshold.
        for i in range(15):
            extra_ip = IPAddress.objects.create(
                parent=self.ip_single.parent,
                address=f"10.99.0.{100 + i}/24",
                status=self.ip_single.status,
                type=IPAddressTypeChoices.TYPE_HOST,
            )
            self.interface_1a.add_ip_addresses(extra_ip)

        nested_columns = (
            "interface_count",
            "interface_parent_count",
            "vm_interface_count",
            "vm_interface_parent_count",
        )
        with AssertNoRepeatedQueries(self):
            table = IPAddressTable(IPAddress.objects.filter(parent__namespace__name="IPAddressTable Test Namespace"))
            for row in table.rows:
                for column_name in nested_columns:
                    row.get_cell(column_name)  # pylint: disable=no-member  # BoundRow has get_cell
