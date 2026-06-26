from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from nautobot.core.templatetags import helpers
from nautobot.dcim.choices import InterfaceDuplexChoices, InterfaceSpeedChoices, InterfaceTypeChoices
from nautobot.dcim.models import (
    Cable,
    CableType,
    Device,
    DeviceType,
    Interface,
    InterfaceTemplate,
    Location,
    LocationType,
    Manufacturer,
)
from nautobot.dcim.tables.devices import DeviceModuleInterfaceTable, InterfaceTable
from nautobot.dcim.tables.devicetypes import InterfaceTemplateTable
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

        return (render_query_count(pks) - render_query_count(pks[:1])) / (len(pks) - 1)

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
