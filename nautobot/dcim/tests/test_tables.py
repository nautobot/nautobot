from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django_tables2.rows import BoundRow

from nautobot.core.templatetags import helpers
from nautobot.core.testing import AssertNoRepeatedQueries
from nautobot.dcim.choices import InterfaceDuplexChoices, InterfaceSpeedChoices, InterfaceTypeChoices, PortTypeChoices
from nautobot.dcim.models import (
    Cable,
    CableType,
    ConsolePort,
    ConsoleServerPort,
    Device,
    DeviceType,
    Interface,
    InterfaceTemplate,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleType,
    PowerFeed,
    PowerOutlet,
    PowerPanel,
    PowerPort,
    RearPort,
)
from nautobot.dcim.tables import ConsoleConnectionTable, InterfaceConnectionTable, PowerConnectionTable
from nautobot.dcim.tables.devices import DeviceModuleInterfaceTable, InterfaceTable
from nautobot.dcim.tables.devicetypes import InterfaceTemplateTable
from nautobot.dcim.views import (
    ConsoleConnectionsListView,
    InterfaceConnectionsListView,
    PowerConnectionsListView,
)
from nautobot.extras.models import Role, Status


class InterfaceTableRenderMixin:
    """Mixin for testing render_speed methods on interface tables."""

    table_class = None

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Test Device Type")
        device_role = Role.objects.get_for_model(Device).first()
        location_type = LocationType.objects.get(name="Campus")
        location = Location.objects.filter(location_type=location_type).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.interface_status = Status.objects.get_for_model(Interface).first()

        cls.device = Device.objects.create(
            name="Test Device",
            device_type=device_type,
            role=device_role,
            location=location,
            status=device_status,
        )

    def test_render_speed_duplex_with_value(self):
        """Test that the table renders humanized speed values."""
        interface = Interface.objects.create(
            device=self.device,
            name="eth0",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=self.interface_status,
            speed=InterfaceSpeedChoices.SPEED_1G,
            duplex=InterfaceDuplexChoices.DUPLEX_FULL,
        )

        queryset = Interface.objects.filter(pk=interface.pk)
        table = self.table_class(queryset)  # pylint: disable=not-callable
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")
        rendered_duplex = bound_row.get_cell("duplex")

        self.assertEqual(rendered_speed, "1 Gbps")
        self.assertEqual(rendered_duplex, "Full")

    def test_render_speed_duplex_with_none(self):
        """Test that the table handles None speed value and renders an emdash."""
        interface = Interface.objects.create(
            device=self.device,
            name="eth1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            status=self.interface_status,
            speed=None,
        )

        queryset = Interface.objects.filter(pk=interface.pk)
        table = self.table_class(queryset)  # pylint: disable=not-callable
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")
        rendered_duplex = bound_row.get_cell("duplex")

        self.assertEqual(rendered_speed, helpers.HTML_NONE)
        self.assertEqual(rendered_duplex, helpers.HTML_NONE)

    def test_render_speed_various(self):
        """Test that the table correctly humanizes various speed values."""
        # Test all speed choices defined in InterfaceSpeedChoices
        for speed_value, expected_output in InterfaceSpeedChoices.CHOICES:
            with self.subTest(speed_value=speed_value, expected=expected_output):
                interface = Interface.objects.create(
                    device=self.device,
                    name=f"eth-{speed_value}",
                    type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                    status=self.interface_status,
                    speed=speed_value,
                )

                queryset = Interface.objects.filter(pk=interface.pk)
                table = self.table_class(queryset)  # pylint: disable=not-callable
                bound_row = table.rows[0]
                rendered_speed = bound_row.get_cell("speed")

                self.assertEqual(rendered_speed, expected_output)

    def test_render_duplex_various(self):
        """Test that the table correctly renders various duplex values."""
        for duplex_value, expected_output in InterfaceDuplexChoices.CHOICES:
            with self.subTest(duplex_value=duplex_value, expected=expected_output):
                interface = Interface.objects.create(
                    device=self.device,
                    name=f"eth-{duplex_value}",
                    type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                    status=self.interface_status,
                    duplex=duplex_value,
                )

                queryset = Interface.objects.filter(pk=interface.pk)
                table = self.table_class(queryset)  # pylint: disable=not-callable
                bound_row = table.rows[0]
                rendered_duplex = bound_row.get_cell("duplex")

                self.assertEqual(rendered_duplex, expected_output)

    def test_row_attrs_color_by_cable_status(self):
        """A cabled interface's row carries a cable-status color class; an uncabled one does not.

        Runs for both the list table and the device/module tab table, guarding against the list
        table missing the `cable_status_color_css` row coloring its tab counterpart has.
        """
        uncabled = Interface.objects.create(device=self.device, name="uncabled", status=self.interface_status)
        cabled_a = Interface.objects.create(device=self.device, name="cabled-a", status=self.interface_status)
        cabled_b = Interface.objects.create(device=self.device, name="cabled-b", status=self.interface_status)
        cable_status = Status.objects.get_for_model(Cable).get(name="Connected")
        Cable.objects.create(termination_a=cabled_a, termination_b=cabled_b, status=cable_status)

        cabled_table = self.table_class(Interface.objects.filter(pk=cabled_a.pk))  # pylint: disable=not-callable
        cabled_class = str(cabled_table.rows[0].attrs.get("class", ""))
        # "Connected" cable status is green → table-success.
        self.assertIn("table-success", cabled_class)

        uncabled_table = self.table_class(Interface.objects.filter(pk=uncabled.pk))  # pylint: disable=not-callable
        self.assertNotIn("table-success", str(uncabled_table.rows[0].attrs.get("class", "")))

    def _make_breakout_trunk_with_children(self, count):
        """Create a 1xN breakout trunk with `count` far interfaces and matching child interfaces.

        Returns `(child_pks, far_by_position)` where `far_by_position[p]` is the interface cabled to
        the breakout-side connector that child interface position `p` maps to.
        """
        cable_status = Status.objects.get_for_model(Cable).first()
        breakout_type = CableType.objects.create(
            name=f"1x{count} breakout (table render)", a_connectors=1, b_connectors=count, total_lanes=count
        )
        trunk = Interface.objects.create(device=self.device, name="trunk0", status=self.interface_status)
        far_by_position = {}
        child_pks = []
        for position in range(1, count + 1):
            far = Interface.objects.create(device=self.device, name=f"lane{position}", status=self.interface_status)
            if position == 1:
                cable = Cable(termination_a=trunk, termination_b=far, cable_type=breakout_type, status=cable_status)
                cable.save()
            else:
                cable.add_termination(far, "B", connector=position)
            far_by_position[position] = far
            child = Interface.objects.create(
                device=self.device,
                name=f"trunk0.{position}",
                status=self.interface_status,
                parent_interface=trunk,
                breakout_position=position,
            )
            child_pks.append(child.pk)
        return child_pks, far_by_position

    def test_render_breakout_subinterface_connection_and_cable_peer(self):
        """A breakout child interface renders its mapped far termination in both connection columns.

        A virtual child interface has no cable termination of its own, so `connection` (n-hop) and
        `cable_peer` (one-hop) fall back to the breakout-side termination it maps to via
        `breakout_position`. Here the far termination is itself an endpoint, so the two coincide.
        """
        child_pks, far_by_position = self._make_breakout_trunk_with_children(2)

        queryset = Interface.optimize_queryset_for_cable_columns(Interface.objects.filter(pk=child_pks[0]))
        table = self.table_class(queryset)  # pylint: disable=not-callable
        bound_row = table.rows[0]
        rendered_connection = bound_row.get_cell("connection")
        rendered_cable_peer = bound_row.get_cell("cable_peer")

        self.assertIn(far_by_position[1].get_absolute_url(), rendered_connection)
        self.assertIn(far_by_position[1].get_absolute_url(), rendered_cable_peer)
        # Only the mapped lane (position 1), not the other breakout lane.
        self.assertNotIn(far_by_position[2].get_absolute_url(), rendered_cable_peer)

    def test_render_breakout_subinterface_actions_trace_button(self):
        """A breakout child interface's actions menu offers a Trace button targeting the parent
        trunk's lane (parent PK + the lane's cablepath_id), since the child has no cable of its own."""
        child_pks, _ = self._make_breakout_trunk_with_children(2)
        child = Interface.objects.get(pk=child_pks[0])
        path = child.get_breakout_lane_cable_path()
        self.assertIsNotNone(path)

        queryset = Interface.optimize_queryset_for_cable_columns(Interface.objects.filter(pk=child.pk))
        table = self.table_class(queryset)  # pylint: disable=not-callable
        rendered_actions = table.rows[0].get_cell("actions")

        expected_href = reverse("dcim:interface_trace", args=[child.parent_interface_id]) + f"?cablepath_id={path.pk}"
        self.assertIn(expected_href, rendered_actions)

    def _make_cabled_interfaces(self, count):
        """Create `count` plain interfaces each directly cabled to a peer; return the near-side pks."""
        cable_status = Status.objects.get_for_model(Cable).first()
        near_pks = []
        for i in range(count):
            near = Interface.objects.create(device=self.device, name=f"plain-a-{i}", status=self.interface_status)
            far = Interface.objects.create(device=self.device, name=f"plain-b-{i}", status=self.interface_status)
            Cable(termination_a=near, termination_b=far, status=cable_status).save()
            near_pks.append(near.pk)
        return near_pks

    def _per_row_query_cost(self, column, pks):
        """Marginal queries added per row when rendering `column`: count(all rows) - count(one row).

        A constant (non-scaling) accessor yields 0; each per-row query the accessor triggers adds 1.
        """

        def render_query_count(row_pks):
            queryset = Interface.optimize_queryset_for_cable_columns(Interface.objects.filter(pk__in=row_pks))
            table = self.table_class(queryset)  # pylint: disable=not-callable
            with CaptureQueriesContext(connection) as ctx:
                for row in table.rows:
                    row.get_cell(column)
            return len(ctx.captured_queries)

        # Warm one-time caches (notably the `ContentType` cache that `GenericPrefetch` resolves)
        # so their constant cost doesn't skew the *marginal* per-row count measured below.
        render_query_count(pks)
        return (render_query_count(pks) - render_query_count(pks[:1])) / (len(pks) - 1)

    def test_cable_column_prefetch_skipped_when_columns_hidden(self):
        """Hiding the `cable_peer` / `connection` columns skips their (conditional) prefetch queries.

        Their prefetch is applied by the table only when the column is visible, so a table that hides
        them evaluates its queryset with strictly fewer queries than one that shows them.
        """
        self._make_cabled_interfaces(4)
        queryset = Interface.optimize_queryset_for_cable_columns(Interface.objects.all())

        def prefetch_query_count(**table_kwargs):
            table = self.table_class(queryset, **table_kwargs)  # pylint: disable=not-callable
            with CaptureQueriesContext(connection) as ctx:
                list(table.data.data)  # force the prefetch_related lookups to execute
            return len(ctx.captured_queries)

        shown = prefetch_query_count(exclude=())
        hidden = prefetch_query_count(exclude=("cable_peer", "connection"))
        self.assertLess(hidden, shown)

    def test_render_breakout_subinterface_columns_no_extra_n_plus_one(self):
        """The breakout connection/cable_peer fallbacks add no per-row queries beyond normal cabling.

        Both the breakout fallbacks and the normal cabled rendering share one known residual per-row
        lookup (`termination.parent` → device/module), tracked separately for a future device-component
        FK-prefetch refactor. This guards that the breakout `parent_interface__...` prefetches keep the
        breakout path's per-row cost equal to the normal path's — i.e. no *additional* N+1 was added.
        """
        child_pks, _ = self._make_breakout_trunk_with_children(4)
        cabled_pks = self._make_cabled_interfaces(4)

        for column in ("cable_peer", "connection"):
            with self.subTest(column=column):
                self.assertLessEqual(
                    self._per_row_query_cost(column, child_pks),
                    self._per_row_query_cost(column, cabled_pks),
                )

    def test_render_breakout_leaf_connection_shows_trunk_child_interface(self):
        """A fan-out (leaf) interface's connection column annotates its trunk endpoint with the child interface."""
        child_pks, far_by_position = self._make_breakout_trunk_with_children(2)
        leaf = far_by_position[1]
        child = Interface.objects.get(pk=child_pks[0])  # breakout_position 1

        queryset = Interface.optimize_queryset_for_cable_columns(Interface.objects.filter(pk=leaf.pk))
        table = self.table_class(queryset)  # pylint: disable=not-callable
        rendered_connection = table.rows[0].get_cell("connection")
        self.assertIn(child.get_absolute_url(), rendered_connection)

    def test_render_breakout_leaf_connection_no_extra_n_plus_one(self):
        """Annotating a leaf's connection with the trunk child interface adds no per-row query.

        The trunk endpoint's `cable_paths`, breakout lanes, and `child_interfaces` are prefetched via
        the `GenericPrefetch` on `cable_paths__destination`, so the connection-column annotation stays
        constant-cost regardless of row count.
        """
        _, far_by_position = self._make_breakout_trunk_with_children(4)
        leaf_pks = [iface.pk for iface in far_by_position.values()]
        cabled_pks = self._make_cabled_interfaces(4)

        self.assertLessEqual(
            self._per_row_query_cost("connection", leaf_pks),
            self._per_row_query_cost("connection", cabled_pks),
        )


class InterfaceTableTestCase(InterfaceTableRenderMixin, TestCase):
    """Test cases for InterfaceTable."""

    table_class = InterfaceTable


class DeviceModuleInterfaceTableTestCase(InterfaceTableRenderMixin, TestCase):
    """Test cases for DeviceModuleInterfaceTable."""

    table_class = DeviceModuleInterfaceTable


class InterfaceTemplateTableTestCase(TestCase):
    """Render tests for InterfaceTemplateTable speed/duplex columns."""

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manuf Tmpl")
        cls.device_type = DeviceType.objects.create(manufacturer=manufacturer, model="DT-Tmpl")

    def test_render_speed_duplex_with_value(self):
        interface_template = InterfaceTemplate.objects.create(
            device_type=self.device_type,
            name="tmpl-eth0",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            speed=InterfaceSpeedChoices.SPEED_1G,
            duplex=InterfaceDuplexChoices.DUPLEX_FULL,
        )
        table = InterfaceTemplateTable(InterfaceTemplate.objects.filter(pk=interface_template.pk))
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")  # pylint: disable=no-member
        rendered_duplex = bound_row.get_cell("duplex")  # pylint: disable=no-member
        self.assertEqual(rendered_speed, "1 Gbps")
        self.assertEqual(rendered_duplex, "Full")

    def test_render_speed_duplex_with_none(self):
        interface_template = InterfaceTemplate.objects.create(
            device_type=self.device_type,
            name="tmpl-eth1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
        )
        table = InterfaceTemplateTable(InterfaceTemplate.objects.filter(pk=interface_template.pk))
        bound_row = table.rows[0]
        rendered_speed = bound_row.get_cell("speed")  # pylint: disable=no-member
        rendered_duplex = bound_row.get_cell("duplex")  # pylint: disable=no-member
        self.assertEqual(rendered_speed, helpers.HTML_NONE)
        self.assertEqual(rendered_duplex, helpers.HTML_NONE)


class ConnectionTableTestCase(TestCase):
    """Render tests for the Console / Power / Interface Connections tables.

    These tables render the far (B) side of each connection through accessors that walk Python
    attributes rather than ORM fields, and `BoundRow._get_and_render_with` swallows any resolution
    error and renders the column default instead. A broken accessor is therefore invisible at the
    HTTP level, which is how nautobot#9341 shipped. Assert on the rendered cells directly.
    """

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name="Test Manuf Conn")
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="DT-Conn")
        device_role = Role.objects.get_for_model(Device).first()
        location_type = LocationType.objects.get(name="Campus")
        location = Location.objects.filter(location_type=location_type).first()
        device_status = Status.objects.get_for_model(Device).first()
        interface_status = Status.objects.get_for_model(Interface).first()
        cls.connected = Status.objects.get_for_model(Cable).get(name="Connected")
        planned = Status.objects.get_for_model(Cable).get(name="Planned")

        cls.device_a = Device.objects.create(
            name="Conn Device A",
            device_type=device_type,
            role=device_role,
            location=location,
            status=device_status,
        )
        cls.device_b = Device.objects.create(
            name="Conn Device B",
            device_type=device_type,
            role=device_role,
            location=location,
            status=device_status,
        )

        # Console: a reachable connection, an unreachable one, and one dead-ending on a RearPort.
        cls.console_port = ConsolePort.objects.create(device=cls.device_a, name="cp-active")
        cls.console_server_port = ConsoleServerPort.objects.create(device=cls.device_b, name="csp-active")
        Cable.objects.create(
            termination_a=cls.console_port, termination_b=cls.console_server_port, status=cls.connected
        )

        cls.console_port_planned = ConsolePort.objects.create(device=cls.device_a, name="cp-planned")
        cls.console_server_port_planned = ConsoleServerPort.objects.create(device=cls.device_b, name="csp-planned")
        Cable.objects.create(
            termination_a=cls.console_port_planned, termination_b=cls.console_server_port_planned, status=planned
        )

        # A RearPort is a CableTermination but not a PathEndpoint, so the path has no destination.
        cls.console_port_unresolved = ConsolePort.objects.create(device=cls.device_a, name="cp-deadend")
        rear_port = RearPort.objects.create(device=cls.device_b, name="rp-deadend", type=PortTypeChoices.TYPE_8P8C)
        Cable.objects.create(termination_a=cls.console_port_unresolved, termination_b=rear_port, status=cls.connected)

        # Power: one path terminating on a PowerOutlet (parent -> device) and one on a PowerFeed
        # (parent -> power_panel), so both `pdu` column shapes are covered.
        cls.power_port_outlet = PowerPort.objects.create(device=cls.device_a, name="pp-outlet")
        cls.power_outlet = PowerOutlet.objects.create(device=cls.device_b, name="po-1")
        Cable.objects.create(termination_a=cls.power_port_outlet, termination_b=cls.power_outlet, status=cls.connected)

        cls.power_panel = PowerPanel.objects.create(location=location, name="Conn Power Panel")
        cls.power_feed = PowerFeed.objects.create(
            power_panel=cls.power_panel,
            name="Conn Power Feed",
            status=Status.objects.get_for_model(PowerFeed).first(),
        )
        cls.power_port_feed = PowerPort.objects.create(device=cls.device_a, name="pp-feed")
        Cable.objects.create(termination_a=cls.power_port_feed, termination_b=cls.power_feed, status=cls.connected)

        # Interface Connections is backed by CablePath and is NOT affected by nautobot#9341.
        cls.interface_a = Interface.objects.create(device=cls.device_a, name="conn-eth0", status=interface_status)
        cls.interface_b = Interface.objects.create(device=cls.device_b, name="conn-eth1", status=interface_status)
        Cable.objects.create(termination_a=cls.interface_a, termination_b=cls.interface_b, status=cls.connected)

    def _first_row(self, table_class, queryset) -> BoundRow:
        """First bound row of `table_class` rendered over `queryset`."""
        return table_class(queryset).rows[0]

    def _row_for(self, view_class, table_class, instance) -> BoundRow:
        """Bound row for `instance`, built from the list view's real (prefetch-carrying) queryset.

        Building from the view's own queryset rather than a bare `objects.filter()` keeps the table
        and the view in lockstep: these tests fail if either the accessors or the prefetching regress.
        """
        return self._first_row(table_class, view_class.queryset.filter(pk=instance.pk))

    def test_console_connection_table_renders_peer_columns(self):
        row = self._row_for(ConsoleConnectionsListView, ConsoleConnectionTable, self.console_port)

        console_server = row.get_cell("console_server")
        self.assertIn(self.device_b.get_absolute_url(), console_server)
        self.assertIn(self.device_b.name, console_server)

        port = row.get_cell("console_server_port")
        self.assertIn(self.console_server_port.get_absolute_url(), port)
        self.assertIn(self.console_server_port.name, port)

        self.assertEqual(row.get_cell("reachable"), helpers.render_boolean(True))

        # The near (A) side must keep working too.
        self.assertIn(self.device_a.get_absolute_url(), row.get_cell("device"))
        self.assertIn(self.console_port.get_absolute_url(), row.get_cell("name"))

    def test_power_connection_table_renders_power_outlet_peer(self):
        row = self._row_for(PowerConnectionsListView, PowerConnectionTable, self.power_port_outlet)
        self.assertIn(self.device_b.get_absolute_url(), row.get_cell("pdu"))
        self.assertIn(self.power_outlet.get_absolute_url(), row.get_cell("outlet"))
        self.assertEqual(row.get_cell("reachable"), helpers.render_boolean(True))

    def test_power_connection_table_renders_power_feed_peer(self):
        """A PowerPort cabled to a PowerFeed shows the PowerPanel as its PDU (`PowerFeed.parent`)."""
        row = self._row_for(PowerConnectionsListView, PowerConnectionTable, self.power_port_feed)
        self.assertIn(self.power_panel.get_absolute_url(), row.get_cell("pdu"))
        self.assertIn(self.power_feed.get_absolute_url(), row.get_cell("outlet"))

    def test_connection_table_renders_unreachable_path(self):
        """A path whose cable is not Connected renders reachable=False, not the placeholder."""
        row = self._row_for(ConsoleConnectionsListView, ConsoleConnectionTable, self.console_port_planned)
        self.assertIn(self.console_server_port_planned.get_absolute_url(), row.get_cell("console_server_port"))
        self.assertEqual(row.get_cell("reachable"), helpers.render_boolean(False))

    def test_connection_table_unresolved_destination_renders_placeholder(self):
        """A path dead-ending on a RearPort has no destination; the peer columns blank gracefully."""
        row = self._row_for(ConsoleConnectionsListView, ConsoleConnectionTable, self.console_port_unresolved)
        self.assertEqual(row.get_cell("console_server"), helpers.HTML_NONE)
        self.assertEqual(row.get_cell("console_server_port"), helpers.HTML_NONE)
        self.assertEqual(row.get_cell("reachable"), helpers.render_boolean(False))
        # The near side still renders, so the row isn't wholly empty.
        self.assertIn(self.console_port_unresolved.get_absolute_url(), row.get_cell("name"))

    def test_interface_connection_table_renders_peer_columns(self):
        """Interface Connections was reworked onto CablePath in 3.2 and is not affected by #9341."""
        # `interface_connections()` canonicalizes a point-to-point pair onto the single direction where
        # `origin_id < destination_id`, so which of the two interfaces lands on the A side depends on
        # randomly generated UUIDs. Assert against the row's own endpoints rather than assuming a side.
        queryset = InterfaceConnectionsListView.base_queryset().filter(
            origin_id__in=[self.interface_a.pk, self.interface_b.pk]
        )
        path = queryset.get()
        self.assertIn(path.destination, [self.interface_a, self.interface_b])

        # pylint mis-infers `BoundRows[0]` as `BoundRows` when the table class is statically known, so
        # `get_cell` reads as a missing member here but not where the class arrives as an argument.
        row = self._first_row(InterfaceConnectionTable, queryset)
        self.assertIn(path.destination.parent.get_absolute_url(), row.get_cell("device_b"))  # pylint: disable=no-member
        self.assertIn(path.destination.get_absolute_url(), row.get_cell("interface_b"))  # pylint: disable=no-member
        self.assertEqual(row.get_cell("reachable"), helpers.render_boolean(True))  # pylint: disable=no-member

    def test_interface_connection_table_renders_peer_without_device(self):
        """An interface on a Module sitting in storage has no device, so its `parent` is None."""
        location = self.device_a.location
        location.location_type.content_types.add(ContentType.objects.get_for_model(Module))
        module = Module.objects.create(
            module_type=ModuleType.objects.create(
                manufacturer=self.device_a.device_type.manufacturer, model="MT-Storage"
            ),
            location=location,
            status=Status.objects.get_for_model(Module).first(),
        )
        interface_status = Status.objects.get_for_model(Interface).first()
        stored = Interface.objects.create(module=module, name="stored-eth0", status=interface_status)
        self.assertIsNone(stored.device)  # the premise of this test

        peer = Interface.objects.create(device=self.device_a, name="peer-of-stored", status=interface_status)
        Cable.objects.create(termination_a=stored, termination_b=peer, status=self.connected)

        queryset = InterfaceConnectionsListView.base_queryset().filter(origin_id__in=[stored.pk, peer.pk])
        path = queryset.get()
        row = self._first_row(InterfaceConnectionTable, queryset)

        # Canonicalization picks the A side by UUID order, so derive which column holds which side.
        if path.origin_id == stored.pk:
            deviceless, with_device = "device_a", "device_b"
        else:
            deviceless, with_device = "device_b", "device_a"
        self.assertEqual(row.get_cell(deviceless).strip(), helpers.HTML_NONE)  # pylint: disable=no-member
        self.assertIn(self.device_a.get_absolute_url(), row.get_cell(with_device))  # pylint: disable=no-member
        # Both interfaces still render regardless of device assignment.
        both_interface_cells = row.get_cell("interface_a") + row.get_cell("interface_b")  # pylint: disable=no-member
        self.assertIn(stored.get_absolute_url(), both_interface_cells)
        self.assertIn(peer.get_absolute_url(), both_interface_cells)

    def _assert_render_has_no_n_plus_one(self, table_class, queryset):
        """Rendering every cell of `queryset` must not issue a query per row.

        Callers supply at least 12 rows: against `AssertNoRepeatedQueries`' default threshold of 10,
        *any* single per-row query then trips the assertion (12 repeats > 10), so this doesn't depend
        on estimating how many queries per row the accessors happen to cost.
        """
        table = table_class(queryset)
        with AssertNoRepeatedQueries(self):
            for row in table.rows:
                for column in table.columns:
                    row.get_cell(column.name)

    def test_console_connection_table_render_has_no_n_plus_one(self):
        pks = []
        for i in range(12):
            console_port = ConsolePort.objects.create(device=self.device_a, name=f"cp-bulk-{i}")
            peer = ConsoleServerPort.objects.create(device=self.device_b, name=f"csp-bulk-{i}")
            Cable.objects.create(termination_a=console_port, termination_b=peer, status=self.connected)
            pks.append(console_port.pk)

        self._assert_render_has_no_n_plus_one(
            ConsoleConnectionTable, ConsoleConnectionsListView.queryset.filter(pk__in=pks)
        )

    def test_power_connection_table_render_has_no_n_plus_one(self):
        """Power rows alternate PowerOutlet and PowerFeed peers, so both destination content types of
        the `GenericPrefetch` are exercised in one render."""
        pks = []
        for i in range(12):
            power_port = PowerPort.objects.create(device=self.device_a, name=f"pp-bulk-{i}")
            if i % 2:
                peer = PowerOutlet.objects.create(device=self.device_b, name=f"po-bulk-{i}")
            else:
                peer = PowerFeed.objects.create(
                    power_panel=self.power_panel,
                    name=f"pf-bulk-{i}",
                    status=Status.objects.get_for_model(PowerFeed).first(),
                )
            Cable.objects.create(termination_a=power_port, termination_b=peer, status=self.connected)
            pks.append(power_port.pk)

        self._assert_render_has_no_n_plus_one(
            PowerConnectionTable, PowerConnectionsListView.queryset.filter(pk__in=pks)
        )

    def test_interface_connection_table_render_has_no_n_plus_one(self):
        """The A and B device columns resolve `origin.parent` / `destination.parent`, i.e.
        `Interface.device`, which `interface_connections()` joins via `GenericPrefetch`."""
        interface_status = Status.objects.get_for_model(Interface).first()
        for i in range(12):
            near = Interface.objects.create(device=self.device_a, name=f"if-bulk-a-{i}", status=interface_status)
            far = Interface.objects.create(device=self.device_b, name=f"if-bulk-b-{i}", status=interface_status)
            Cable.objects.create(termination_a=near, termination_b=far, status=self.connected)

        self._assert_render_has_no_n_plus_one(InterfaceConnectionTable, InterfaceConnectionsListView.base_queryset())
