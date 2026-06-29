"""Unit tests for DCIM SVG rendering helpers."""

import functools
import re

from django.test import SimpleTestCase, tag
from django.utils.safestring import SafeString

from nautobot.core.testing import TestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import (
    Cable,
    CableType,
    Device,
    DeviceType,
    FrontPort,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleType,
    RearPort,
)
from nautobot.dcim.svg import constants as svg_constants
from nautobot.dcim.svg.cable_breakout import BreakoutDiagramSVG, TerminationLabel
from nautobot.dcim.svg.path_trace import CableTraceSVG
from nautobot.dcim.svg.utils import estimate_text_width, fit_text
from nautobot.dcim.utils import generate_cable_breakout_mapping
from nautobot.extras.models import Role, Status


def _line_endpoints(svg):
    """Extract [(x1, y1, x2, y2), ...] from all <line> elements in the SVG string."""
    endpoints = []
    for match in re.finditer(r"<line\b([^/]*)/>", svg):
        attrs = match.group(1)
        coords = {}
        for name in ("x1", "y1", "x2", "y2"):
            m = re.search(rf'\b{name}="([^"]+)"', attrs)
            if m is None:
                break
            coords[name] = float(m.group(1))
        else:
            endpoints.append((coords["x1"], coords["y1"], coords["x2"], coords["y2"]))
    return endpoints


def _label_rects(svg):
    """Return [(x, y), ...] for each label rect (identified by fill="var(--bs-body-bg)")."""
    labels = []
    for match in re.finditer(r"<rect\b([^/]*)/>", svg):
        attrs = match.group(1)
        fill_match = re.search(r'(?<![-\w])fill="([^"]+)"', attrs)
        x_match = re.search(r'(?<![-\w])x="([^"]+)"', attrs)
        y_match = re.search(r'(?<![-\w])y="([^"]+)"', attrs)
        if fill_match and fill_match.group(1) == "var(--bs-body-bg)" and x_match and y_match:
            labels.append((float(x_match.group(1)), float(y_match.group(1))))
    return labels


@tag("unit")
class FitTextTest(SimpleTestCase):
    """Tests for nautobot.dcim.svg.utils.fit_text."""

    def test_empty_text_returns_empty_string(self):
        """Falsy text short-circuits to an empty string regardless of the available width."""
        self.assertEqual(fit_text("", 100, 12), "")

    def test_text_within_width_is_returned_unchanged(self):
        """Text whose estimated width fits within `max_width` is returned verbatim, no ellipsis."""
        self.assertEqual(fit_text("Short", 1000, 12), "Short")

    def test_text_exceeding_width_is_truncated_with_ellipsis(self):
        """Text wider than `max_width` is truncated to fit, reserving one slot for the ellipsis.

        At font_size=12 and ratio=0.65, `max_width=50` allows 6 chars, so a longer string keeps its
        first 5 characters plus the ellipsis glyph.
        """
        self.assertEqual(fit_text("Truncate me please", 50, 12), "Trunc…")


@tag("unit")
class BreakoutDiagramSVGTest(SimpleTestCase):
    """Tests for nautobot.dcim.svg.cable_breakout.BreakoutDiagramSVG."""

    def _render(self, **kwargs):
        mapping = generate_cable_breakout_mapping(**kwargs)
        return mapping, BreakoutDiagramSVG(mapping, show_status=False).render()

    def test_y_offset_single_position(self):
        """A connector with a single position should not offset its lane endpoints."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=1, total_lanes=1)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)
        self.assertEqual(diagram._y_offset(1, 1, diagram.a_connector_height), 0)

    def test_y_offset_multiple_positions_symmetric(self):
        """With >1 positions, offsets should straddle zero within +/- connector_height * fraction / 2."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=1, total_lanes=4)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)

        offsets = [diagram._y_offset(p, 4, diagram.a_connector_height) for p in range(1, 5)]
        # Symmetric about zero and monotonically increasing.
        self.assertAlmostEqual(offsets[0], -offsets[-1])
        self.assertAlmostEqual(offsets[1], -offsets[-2])
        self.assertEqual(sorted(offsets), offsets)
        # All offsets sit within the connector height.
        for offset in offsets:
            self.assertLess(abs(offset), diagram.a_connector_height / 2)

    def test_connector_height_scales_with_positions(self):
        """A connector's height grows with positions-per-connector."""
        small_diagram = BreakoutDiagramSVG(
            generate_cable_breakout_mapping(a_connectors=1, b_connectors=1, total_lanes=1), show_status=False
        )
        large_diagram = BreakoutDiagramSVG(
            generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=12), show_status=False
        )

        # Small: 1 position → minimum height.
        self.assertEqual(small_diagram.a_connector_height, 2 * BreakoutDiagramSVG.LANE_Y_SPACING)
        # Large: 12 A-positions → height = (12 + 1) * LANE_Y_SPACING.
        self.assertEqual(large_diagram.a_connector_height, 13 * BreakoutDiagramSVG.LANE_Y_SPACING)
        # Large: 6 B-positions per connector → height = (6 + 1) * LANE_Y_SPACING.
        self.assertEqual(large_diagram.b_connector_height, 7 * BreakoutDiagramSVG.LANE_Y_SPACING)

    def test_parallel_lanes_rendered_with_distinct_y_values(self):
        """A straight 1:1 breakout with multiple positions must render each lane separately."""
        _, svg = self._render(a_connectors=1, b_connectors=1, total_lanes=4)
        endpoints = _line_endpoints(svg)
        self.assertEqual(len(endpoints), 4, "Expected one <line> element per lane")

        y_starts = [y1 for (_, y1, _, _) in endpoints]
        y_ends = [y2 for (_, _, _, y2) in endpoints]
        # If the previous bug were still present, all four lanes would share the
        # same (y1, y2) — making the set size 1 rather than 4.
        self.assertEqual(len(set(y_starts)), 4, "A-side endpoints must be distinct per lane")
        self.assertEqual(len(set(y_ends)), 4, "B-side endpoints must be distinct per lane")

    def test_parallel_lanes_share_same_pair_of_connectors(self):
        """Distinct endpoints must still fall within the A and B connector boundaries."""
        mapping, svg = self._render(a_connectors=1, b_connectors=1, total_lanes=4)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)
        a_connector_y_centers, b_connector_y_centers = diagram._connector_y_centers()
        a_center = a_connector_y_centers[1]
        b_center = b_connector_y_centers[1]

        for _, y1, _, y2 in _line_endpoints(svg):
            self.assertLessEqual(abs(y1 - a_center), diagram.a_connector_height / 2)
            self.assertLessEqual(abs(y2 - b_center), diagram.b_connector_height / 2)

    def test_breakout_one_to_many_distinct_a_side_offsets(self):
        """A 1:N breakout must spread A-side endpoints based on a_position."""
        _, svg = self._render(a_connectors=1, b_connectors=4, total_lanes=8)
        endpoints = _line_endpoints(svg)
        self.assertEqual(len(endpoints), 8)

        # total_lanes=8, a_connectors=1 → a_positions=8. Every lane leaves the
        # single A connector at a distinct y, instead of all piling onto its center.
        y_starts = {y1 for (_, y1, _, _) in endpoints}
        self.assertEqual(len(y_starts), 8)

        # b_connectors=4, b_positions=2 → each B connector receives exactly 2 lanes
        # at 2 distinct y values. Group endpoints by their nearest b center.
        diagram = BreakoutDiagramSVG(
            generate_cable_breakout_mapping(a_connectors=1, b_connectors=4, total_lanes=8), show_status=False
        )
        _, b_connector_y_centers = diagram._connector_y_centers()
        lanes_per_b = {bc: set() for bc in b_connector_y_centers}

        def y_offset(bc, y2):
            return abs(b_connector_y_centers[bc] - y2)

        for _, _, _, y2 in endpoints:
            nearest_bc = min(b_connector_y_centers, key=functools.partial(y_offset, y2=y2))
            lanes_per_b[nearest_bc].add(round(y2, 4))
        for bc, y_values in lanes_per_b.items():
            self.assertEqual(len(y_values), 2, f"B connector {bc} should receive 2 distinct y values")

    def test_dense_breakout_one_to_two_twelve_lanes(self):
        """A 1:2 breakout with 12 lanes (6 parallel per pair) must render all 12 legibly.

        Every line endpoint must be distinct on both sides, labels must
        have distinct x coordinates within each parallel-lane group, and all
        endpoints must fit inside their connector.
        """
        mapping, svg = self._render(a_connectors=1, b_connectors=2, total_lanes=12)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)
        self.assertEqual(diagram.a_positions, 12)
        self.assertEqual(diagram.b_positions, 6)

        endpoints = _line_endpoints(svg)
        self.assertEqual(len(endpoints), 12)

        # All 12 A-side endpoints are distinct (one per a_position).
        y_starts = {y1 for (_, y1, _, _) in endpoints}
        self.assertEqual(len(y_starts), 12)

        # Each B connector gets 6 distinct endpoint y values (one per b_position).
        a_connector_y_centers, b_connector_y_centers = diagram._connector_y_centers()
        lanes_per_b = {bc: set() for bc in b_connector_y_centers}

        def y_offset(bc, y2):
            return abs(b_connector_y_centers[bc] - y2)

        for _, _, _, y2 in endpoints:
            nearest_bc = min(b_connector_y_centers, key=functools.partial(y_offset, y2=y2))
            lanes_per_b[nearest_bc].add(round(y2, 4))
        for bc, y_values in lanes_per_b.items():
            self.assertEqual(len(y_values), 6, f"B connector {bc} should receive 6 distinct y values")

        # All endpoints stay inside their connector's rect.
        for _, y1, _, y2 in endpoints:
            self.assertLessEqual(abs(y1 - a_connector_y_centers[1]), diagram.a_connector_height / 2)
            nearest_bc = min(b_connector_y_centers, key=functools.partial(y_offset, y2=y2))
            self.assertLessEqual(abs(y2 - b_connector_y_centers[nearest_bc]), diagram.b_connector_height / 2)

        # Labels: each of the 12 lanes gets its own distinct position.
        # Pills in different pairs may share an x value (they sit at different
        # y values because those two pairs' lines have different slopes).
        labels = _label_rects(svg)
        self.assertEqual(len(labels), 12)
        self.assertEqual(len(set(labels)), 12)
        # Each of the 2 parallel-lane groups places its 6 labels at 6 distinct x
        # values; each pair may reuse the same 6 x values, so the total unique x count is at least 6.
        self.assertGreaterEqual(len({x for (x, _) in labels}), 6)

    def test_lane_labels_staggered_for_parallel_lanes(self):
        """When multiple lanes share a connector pair, labels must not stack at the same x."""
        _, svg = self._render(a_connectors=1, b_connectors=1, total_lanes=4)
        label_x_values = [x for (x, _) in _label_rects(svg)]
        self.assertEqual(len(label_x_values), 4)
        self.assertEqual(len(set(label_x_values)), 4, "Parallel-lane labels should not overlap in x")

    def test_render_returns_safestring_with_matching_dimensions(self):
        """render() returns a SafeString whose svg dimensions match _total_width/_total_height."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=4)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)
        svg = diagram.render()

        self.assertIsInstance(svg, SafeString)

        total_width = diagram._total_width()
        total_height = diagram._total_height()
        self.assertIn(f'width="{total_width}px"', svg)
        self.assertIn(f'height="{total_height}px"', svg)
        self.assertIn(f'viewBox="0,0,{total_width},{total_height}"', svg)

    def test_connector_label_includes_positions_suffix_when_multiple(self):
        """Connector labels should gain a ' (N)' suffix only when positions-per-connector > 1."""
        # 1:1 with a single lane → 1 position per connector on each side, no suffix.
        single = generate_cable_breakout_mapping(a_connectors=1, b_connectors=1, total_lanes=1)
        svg = BreakoutDiagramSVG(single, show_status=False).render()
        self.assertIn(">A1</text>", svg)
        self.assertIn(">B1</text>", svg)
        self.assertNotIn("A1 (", svg)
        self.assertNotIn("B1 (", svg)

        # 1:2 with 8 lanes → A1 has 8 positions, B1/B2 have 4 each.
        multi = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=8)
        svg = BreakoutDiagramSVG(multi, show_status=False).render()
        self.assertIn(">A1 (8)</text>", svg)
        self.assertIn(">B1 (4)</text>", svg)
        self.assertIn(">B2 (4)</text>", svg)

    def test_line_area_width_scales_with_label_length(self):
        """line_area_width should hit the minimum for short labels and grow with long labels."""
        # Short default labels + few parallel lanes → clamped to MINIMUM_LINE_AREA_WIDTH.
        short = BreakoutDiagramSVG(
            generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2),
            show_status=False,
        )
        self.assertEqual(short.line_area_width, BreakoutDiagramSVG.MINIMUM_LINE_AREA_WIDTH)

        # Long custom labels should push line_area_width above the minimum.
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=1, total_lanes=2)
        for i, entry in enumerate(mapping):
            entry["label"] = f"VERY_LONG_LANE_LABEL_{i}"
        long_diagram = BreakoutDiagramSVG(mapping, show_status=False)
        self.assertGreater(long_diagram.line_area_width, BreakoutDiagramSVG.MINIMUM_LINE_AREA_WIDTH)

    def test_termination_label_renders_clickable_parent_and_termination_links(self):
        """A connected connector's label renders the parent and termination as separate hyperlinks."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2)
        svg = BreakoutDiagramSVG(
            mapping,
            show_status=True,
            a_termination_labels={
                1: TerminationLabel(
                    term_text="Eth1/1",
                    term_url="/dcim/interfaces/iface-uuid/",
                    parent_text="switch-01",
                    parent_url="/dcim/devices/device-uuid/",
                )
            },
        ).render()
        # Both objects are linked...
        self.assertIn('xlink:href="/dcim/devices/device-uuid/"', svg)
        self.assertIn('xlink:href="/dcim/interfaces/iface-uuid/"', svg)
        # ...with their respective text, separated by a non-link " / ".
        self.assertIn(">switch-01</tspan>", svg)
        self.assertIn(">Eth1/1</tspan>", svg)
        self.assertIn("> / </tspan>", svg)

    def test_termination_label_without_parent_renders_only_termination(self):
        """A label with no parent renders just the termination, with no separator."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2)
        svg = BreakoutDiagramSVG(
            mapping,
            show_status=True,
            a_termination_labels={1: TerminationLabel(term_text="Eth1/1", term_url="/dcim/interfaces/iface-uuid/")},
        ).render()
        self.assertIn('xlink:href="/dcim/interfaces/iface-uuid/"', svg)
        self.assertIn(">Eth1/1</tspan>", svg)
        self.assertNotIn("> / </tspan>", svg)

    def test_termination_label_without_url_renders_plain_text(self):
        """A label segment with no URL is rendered as plain (non-link) text rather than a hyperlink."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2)
        svg = BreakoutDiagramSVG(
            mapping,
            show_status=True,
            a_termination_labels={
                1: TerminationLabel(term_text="NoUrlIface", term_url="", parent_text="dev2", parent_url="")
            },
        ).render()
        self.assertNotIn("xlink:href", svg)
        self.assertIn(">dev2</tspan>", svg)
        self.assertIn(">NoUrlIface</tspan>", svg)

    def test_termination_label_renders_full_text_without_truncation(self):
        """Long labels are rendered in full (no ellipsis); width is handled by the scrollable card."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2)
        long_term = "GigabitEthernet" + "0" * 60
        svg = BreakoutDiagramSVG(
            mapping,
            show_status=True,
            a_termination_labels={1: TerminationLabel(term_text=long_term, parent_text="router-01")},
        ).render()
        self.assertIn(f">{long_term}</tspan>", svg)
        self.assertIn(">router-01</tspan>", svg)
        self.assertNotIn("…", svg)

    def test_termination_label_area_width_grows_to_fit_labels(self):
        """Reserving space for visible labels widens the diagram, and longer labels widen it further."""
        mapping = generate_cable_breakout_mapping(a_connectors=1, b_connectors=2, total_lanes=2)
        bare = BreakoutDiagramSVG(mapping, show_status=False)
        labeled = BreakoutDiagramSVG(
            mapping,
            show_status=True,
            a_termination_labels={1: TerminationLabel(term_text="Eth1/1", parent_text="switch-01")},
        )
        longer = BreakoutDiagramSVG(
            mapping,
            show_status=True,
            a_termination_labels={1: TerminationLabel(term_text="Eth1/1", parent_text="switch-01" * 10)},
        )
        self.assertEqual(bare.a_label_area_width, 0)
        self.assertGreater(labeled.a_label_area_width, 0)
        self.assertGreater(labeled._total_width(), bare._total_width())
        # Full labels are never truncated, so a longer label always reserves more width.
        self.assertGreater(longer.a_label_area_width, labeled.a_label_area_width)


class CableTraceSVGTestCase(TestCase):
    """Direct tests of the server-side cable-trace SVG renderer (no view layer)."""

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="SVG Trace Device Type")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            location=location,
            device_type=device_type,
            role=device_role,
            name="SVG Trace Device",
            status=device_status,
        )
        cls.interface_status = Status.objects.get_for_model(Interface).first()
        cls.connected = Status.objects.get_for_model(Cable).get(name="Connected")

    @staticmethod
    def _svg_width(svg):
        return float(re.search(r'width="([\d.]+)px"', svg).group(1))

    @staticmethod
    def _matrix_cells(diagram):
        """All matrix cells for a rendered diagram."""
        return [cell for row in diagram.build_matrix()["rows"] for cell in row]

    def test_passthrough_hops_always_fold_into_passthrough_nodes(self):
        """Front↔rear pass-through hops are always merged into `passthrough_node` device boxes; a
        standalone `passthrough` cell never reaches a row (so it has no rendering of its own)."""
        rp1 = RearPort.objects.create(device=self.device, name="PT Rear 1", positions=1)
        fp1 = FrontPort.objects.create(device=self.device, name="PT Front 1", rear_port=rp1, rear_port_position=1)
        rp2 = RearPort.objects.create(device=self.device, name="PT Rear 2", positions=1)
        fp2 = FrontPort.objects.create(device=self.device, name="PT Front 2", rear_port=rp2, rear_port_position=1)
        iface_a = Interface.objects.create(device=self.device, name="pt-a", status=self.interface_status)
        iface_b = Interface.objects.create(device=self.device, name="pt-b", status=self.interface_status)
        # iface_a -- RP1 ; FP1 -- RP2 ; FP2 -- iface_b  (two patch-panel pass-throughs)
        Cable.objects.create(termination_a=iface_a, termination_b=rp1, status=self.connected)
        Cable.objects.create(termination_a=fp1, termination_b=rp2, status=self.connected)
        Cable.objects.create(termination_a=fp2, termination_b=iface_b, status=self.connected)

        cells = self._matrix_cells(CableTraceSVG(iface_a))
        types = {cell["type"] for cell in cells}
        self.assertIn("passthrough_node", types)
        self.assertNotIn("passthrough", types)

    def test_get_parent_info_for_component_on_location_module(self):
        """A component on a Module assigned directly to a Location (no ModuleBay) has no parent
        Device — `Module.device` returns None — so `ModularComponentModel.parent` is None. In that
        case `_get_parent_info` falls back to a single self-named, unlinked line rather than
        dereferencing the absent parent.
        """
        module_location = Location.objects.get_for_model(Module).first()
        module_type = ModuleType.objects.create(
            manufacturer=Manufacturer.objects.first(), model="SVG Trace Location Module"
        )
        module = Module.objects.create(
            module_type=module_type,
            location=module_location,
            status=Status.objects.get_for_model(Module).first(),
        )
        iface = Interface.objects.create(module=module, name="mod-iface", status=self.interface_status)
        # Precondition: a location-based module's component has no parent device.
        self.assertIsNone(iface.parent)

        key, lines = CableTraceSVG(iface)._get_parent_info(iface)
        self.assertIsNone(key)
        self.assertEqual(lines, [(str(iface), "#")])

    def test_uneven_breakout_legs_pad_shorter_column_with_empty_cells(self):
        """A breakout whose legs differ in length pads the shorter leg's column with `empty` cells.

        Empty cells only ever trail a leg's content (legs are top-aligned), so they render as
        no-ops — they never carry a `continuation` marker.
        """
        breakout = CableType(name="Uneven 1x2", a_connectors=1, b_connectors=2, total_lanes=2)
        breakout.validated_save()
        trunk = Interface.objects.create(device=self.device, name="uneven-trunk", status=self.interface_status)
        # Lane 1: straight to an interface (short leg).
        lane1 = Interface.objects.create(device=self.device, name="uneven-lane1", status=self.interface_status)
        # Lane 2: through a patch panel to an interface (longer leg).
        rear = RearPort.objects.create(device=self.device, name="Uneven Rear", positions=1)
        front = FrontPort.objects.create(device=self.device, name="Uneven Front", rear_port=rear, rear_port_position=1)
        dest = Interface.objects.create(device=self.device, name="uneven-dest", status=self.interface_status)
        cable = Cable(termination_a=trunk, termination_b=lane1, cable_type=breakout, status=self.connected)
        cable.save()
        cable.add_termination(front, "B", connector=2)
        Cable.objects.create(termination_a=rear, termination_b=dest, status=self.connected)

        diagram = CableTraceSVG(trunk)
        cells = self._matrix_cells(diagram)
        empties = [cell for cell in cells if cell["type"] == "empty"]
        self.assertTrue(empties, "The shorter leg's column should be padded with empty cells")
        self.assertFalse(any(cell.get("continuation") for cell in empties))
        # Empty pad cells render as no-ops; the diagram still renders.
        self.assertIn("<svg", diagram.render())

    def test_origin_without_cable_path_renders_empty_placeholder(self):
        """An origin with no cable (hence no CablePath) yields an empty trace: `_detect_fanout`
        returns no legs and `render` falls back to the 'No cable path found' placeholder."""
        iface = Interface.objects.create(device=self.device, name="empty-origin", status=self.interface_status)

        diagram = CableTraceSVG(iface)
        self.assertEqual(diagram.traced_path, [])
        self.assertEqual(diagram.fanout_paths, [])

        svg = diagram.render()
        self.assertIn("<svg", svg)
        self.assertIn("No cable path found", svg)

    def test_complete_trace_footer(self):
        """A complete trace renders a completion summary with the segment count and total length."""
        iface_a = Interface.objects.create(device=self.device, name="iface-a", status=self.interface_status)
        iface_b = Interface.objects.create(device=self.device, name="iface-b", status=self.interface_status)
        Cable.objects.create(
            termination_a=iface_a, termination_b=iface_b, status=self.connected, length=5, length_unit="m"
        )

        svg = CableTraceSVG(iface_a).render()
        self.assertIn("Trace completed", svg)
        self.assertIn("Total segments: 1", svg)
        self.assertIn("5 Meters", svg)
        self.assertIn("Feet", svg)

    def test_non_connected_cable_renders_dashed_with_status_badge(self):
        """A path through a non-Connected cable draws the bar dashed and labels it with the cable's
        status, unlike a Connected cable (drawn solid, with no dash array)."""
        planned = Status.objects.get_for_model(Cable).get(name="Planned")
        iface_a = Interface.objects.create(device=self.device, name="planned-a", status=self.interface_status)
        iface_b = Interface.objects.create(device=self.device, name="planned-b", status=self.interface_status)
        Cable.objects.create(termination_a=iface_a, termination_b=iface_b, status=planned)

        svg = CableTraceSVG(iface_a).render()
        # A dashed bar (only emitted for non-Connected cables) plus a status badge naming the status.
        self.assertIn("stroke-dasharray", svg)
        self.assertIn("Planned", svg)

        # Contrast: a Connected cable draws a solid bar with no dash array.
        iface_c = Interface.objects.create(device=self.device, name="planned-c", status=self.interface_status)
        iface_d = Interface.objects.create(device=self.device, name="planned-d", status=self.interface_status)
        Cable.objects.create(termination_a=iface_c, termination_b=iface_d, status=self.connected)
        self.assertNotIn("stroke-dasharray", CableTraceSVG(iface_c).render())

    def test_branched_trace_footer_is_neutral_aggregate(self):
        """A branched (breakout) trace shows a neutral aggregate footer, not first-lane-only totals."""
        breakout = CableType(name="SVG 1x2", a_connectors=1, b_connectors=2, total_lanes=2)
        breakout.validated_save()  # populates `mapping` via clean()
        trunk = Interface.objects.create(device=self.device, name="branch-trunk", status=self.interface_status)
        lane1 = Interface.objects.create(device=self.device, name="branch-lane-1", status=self.interface_status)
        lane2 = Interface.objects.create(device=self.device, name="branch-lane-2", status=self.interface_status)
        cable = Cable(termination_a=trunk, termination_b=lane1, cable_type=breakout, status=self.connected)
        cable.save()
        cable.add_termination(lane2, "B", connector=2)

        svg = CableTraceSVG(trunk).render()
        self.assertIn("Breakout fan-out", svg)
        # The single-path summary (which would reflect only the first lane) is suppressed.
        self.assertNotIn("Trace completed", svg)
        self.assertNotIn("Total segments", svg)
        self.assertNotIn("Total length", svg)

    def test_one_to_one_cable_type_renders_as_linear_trace(self):
        """A cable_type that maps the origin's connector to a single far connector is not a fan-out.

        `_detect_fanout` finds `seen_far_connectors <= 1` and returns the single linear leg, so the
        trace renders like an ordinary point-to-point cable — no "Breakout fan-out" header.
        """
        one_to_one = CableType(name="SVG 1x1", a_connectors=1, b_connectors=1, total_lanes=1)
        one_to_one.validated_save()  # populates `mapping` via clean()
        trunk = Interface.objects.create(device=self.device, name="1x1-trunk", status=self.interface_status)
        dest = Interface.objects.create(device=self.device, name="1x1-dest", status=self.interface_status)
        Cable.objects.create(termination_a=trunk, termination_b=dest, cable_type=one_to_one, status=self.connected)

        diagram = CableTraceSVG(trunk)
        self.assertEqual(len(diagram.fanout_paths), 1)
        self.assertEqual(diagram.fanout_paths[0]["connector_label"], "")
        svg = diagram.render()
        self.assertIn("<svg", svg)
        self.assertNotIn("Breakout fan-out", svg)

    def test_origin_side_breakout_cable_shows_lane_detail(self):
        """A breakout cable that is the origin's first hop, traced from the single-lane side, renders
        as one linear bar (no fork) but must still show its lane mapping detail — matching how the
        same cable renders as a mid-path segment.

        [IF_lane1] --C (breakout 1:2, lane B1)-- [IF_trunk]
        """
        breakout = CableType(name="SVG lane-detail 1x2", a_connectors=1, b_connectors=2, total_lanes=2)
        breakout.validated_save()  # populates `mapping` via clean()
        trunk = Interface.objects.create(device=self.device, name="ld-trunk", status=self.interface_status)
        lane1 = Interface.objects.create(device=self.device, name="ld-lane-1", status=self.interface_status)
        lane2 = Interface.objects.create(device=self.device, name="ld-lane-2", status=self.interface_status)
        cable = Cable(termination_a=trunk, termination_b=lane1, cable_type=breakout, status=self.connected)
        cable.save()
        cable.add_termination(lane2, "B", connector=2)

        # Tracing from a single lane maps to one trunk connector, so it is a linear (non-fan-out) leg.
        diagram = CableTraceSVG(lane1)
        self.assertEqual(len(diagram.fanout_paths), 1)
        svg = diagram.render()
        self.assertNotIn("Breakout fan-out", svg)
        # The breakout cable is the only cable and sits in the header; its lane detail (absent before
        # the first hop's endpoints were threaded through) names the lane mapping.
        self.assertIn("Breakout: B1 → A1", svg)

    def test_split_trace_footer_lists_next_hops_with_cables(self):
        """A split trace renders "Path split!" and the selectable next-hop nodes with their cables."""
        iface = Interface.objects.create(device=self.device, name="split-origin", status=self.interface_status)
        rear = RearPort.objects.create(device=self.device, name="Rear Port Split", positions=4)
        front1 = FrontPort.objects.create(
            device=self.device, name="Front Port Split 1", rear_port=rear, rear_port_position=1
        )
        front2 = FrontPort.objects.create(
            device=self.device, name="Front Port Split 2", rear_port=rear, rear_port_position=2
        )
        dest1 = Interface.objects.create(device=self.device, name="split-dest-1", status=self.interface_status)
        dest2 = Interface.objects.create(device=self.device, name="split-dest-2", status=self.interface_status)

        # IF -- C1 -- RP (positions=4); the rear port fans out, so tracing from IF splits there.
        Cable.objects.create(termination_a=iface, termination_b=rear, status=self.connected)
        Cable.objects.create(termination_a=front1, termination_b=dest1, status=self.connected, label="split-cable-1")
        Cable.objects.create(termination_a=front2, termination_b=dest2, status=self.connected, label="split-cable-2")

        svg = CableTraceSVG(iface).render()
        self.assertIn("Path split!", svg)
        self.assertIn("Select a node below to continue", svg)
        self.assertIn("Front Port Split 1", svg)
        self.assertIn("Front Port Split 2", svg)
        # Each next-hop names its onward cable.
        self.assertIn("split-cable-1", svg)
        self.assertIn("split-cable-2", svg)

    def test_split_trace_footer_lists_uncabled_next_hop_as_plain_text(self):
        """A split next-hop node with no onward cable can't be traced further, so the footer lists it
        as bare text (no link, no "(Cable ...)"), unlike a cabled next-hop which links to its trace."""
        iface = Interface.objects.create(device=self.device, name="nc-origin", status=self.interface_status)
        rear = RearPort.objects.create(device=self.device, name="NC Rear", positions=4)
        cabled_front = FrontPort.objects.create(
            device=self.device, name="NC Front Cabled", rear_port=rear, rear_port_position=1
        )
        uncabled_front = FrontPort.objects.create(
            device=self.device, name="NC Front Uncabled", rear_port=rear, rear_port_position=2
        )
        dest = Interface.objects.create(device=self.device, name="nc-dest", status=self.interface_status)
        # IF -- C1 -- RP (positions=4): tracing from IF splits at the rear port.
        Cable.objects.create(termination_a=iface, termination_b=rear, status=self.connected)
        # Only one front port has an onward cable; the other is a dead end.
        Cable.objects.create(termination_a=cabled_front, termination_b=dest, status=self.connected)

        # Map each next-hop's footer text to its url (last tuple element); a None url is plain text.
        next_hops = {text: url for text, _size, _weight, _fill, url in CableTraceSVG(iface)._trace_end_lines()}
        # The cabled front port links to its trace and names the cable inline.
        cabled_line = next(text for text in next_hops if str(cabled_front) in text)
        self.assertIn("(Cable", cabled_line)
        self.assertIsNotNone(next_hops[cabled_line])
        # The uncabled front port is listed as bare text with no link (path_trace.py line 1109).
        self.assertIn(str(uncabled_front), next_hops)
        self.assertIsNone(next_hops[str(uncabled_front)])

    def test_long_cable_label_fits_within_canvas_width(self):
        """The canvas must be wide enough that a long cable label is not clipped on the right."""
        iface_a = Interface.objects.create(device=self.device, name="wide-a", status=self.interface_status)
        iface_b = Interface.objects.create(device=self.device, name="wide-b", status=self.interface_status)
        long_label = "DEMO-VERY-LONG-CABLE-LABEL-THAT-SHOULD-NOT-BE-CLIPPED-01"
        Cable.objects.create(termination_a=iface_a, termination_b=iface_b, status=self.connected, label=long_label)

        diagram = CableTraceSVG(iface_a)
        svg = diagram.render()
        width = self._svg_width(svg)

        # The label hangs to the right of the (centered) cable bar; its right edge must be inside the canvas.
        matrix = diagram.build_matrix()
        center_x = matrix["col_centers"][0]
        label_x = center_x + diagram.CABLE_BAR_W / 2 + diagram.LABEL_OFFSET_X
        label_width = estimate_text_width(long_label, svg_constants.FONT_SIZE)
        self.assertLessEqual(label_x + label_width, width, msg=f"Cable label clipped: width={width}")

    def test_trace_end_footer_centered_and_unclipped(self):
        """The trunk is centered in the canvas so the centered footer can't overflow the left edge."""
        iface = Interface.objects.create(device=self.device, name="footer-origin", status=self.interface_status)
        rear = RearPort.objects.create(device=self.device, name="Footer Rear", positions=4)
        front = FrontPort.objects.create(device=self.device, name="Footer Front", rear_port=rear, rear_port_position=1)
        dest = Interface.objects.create(device=self.device, name="footer-dest", status=self.interface_status)
        Cable.objects.create(termination_a=iface, termination_b=rear, status=self.connected)
        # A long onward-cable label makes the split footer's next-hop line the widest element.
        long_label = "DEMO-EXTREMELY-LONG-NEXT-HOP-CABLE-LABEL-FOR-FOOTER-WIDTH-CHECK-01"
        Cable.objects.create(termination_a=front, termination_b=dest, status=self.connected, label=long_label)

        diagram = CableTraceSVG(iface)
        width = self._svg_width(diagram.render())
        col_centers = diagram.build_matrix()["col_centers"]
        trunk_cx = (col_centers[0] + col_centers[-1]) / 2

        # The trunk runs down the SVG center, so the centered footer has equal room on both sides.
        self.assertAlmostEqual(trunk_cx, width / 2, places=3)
        footer_half = diagram._trace_end_width() / 2
        self.assertGreaterEqual(trunk_cx - footer_half, 0, msg="Footer overflows the left edge")
        self.assertLessEqual(trunk_cx + footer_half, width, msg="Footer overflows the right edge")

    def test_grouped_passthrough_shared_rear_port_drawn_once_among_distinct(self):
        """A rear port shared by two adjacent legs renders once even when a third leg in the same
        grouped pass-through node uses a different rear port (regression: all-or-nothing dedup)."""
        breakout = CableType(name="SVG 1x3", a_connectors=1, b_connectors=3, total_lanes=3)
        breakout.validated_save()  # populates `mapping` via clean()
        trunk = Interface.objects.create(device=self.device, name="grp-trunk", status=self.interface_status)

        shared_rear = RearPort.objects.create(device=self.device, name="Rear-Shared", positions=2)
        front1 = FrontPort.objects.create(
            device=self.device, name="Front-1", rear_port=shared_rear, rear_port_position=1
        )
        front2 = FrontPort.objects.create(
            device=self.device, name="Front-2", rear_port=shared_rear, rear_port_position=2
        )
        other_rear = RearPort.objects.create(device=self.device, name="Rear-Other", positions=1)
        front3 = FrontPort.objects.create(
            device=self.device, name="Front-3", rear_port=other_rear, rear_port_position=1
        )

        # Lanes B1/B2 → front1/front2 (both pass through to the shared rear); B3 → front3 (other rear).
        cable = Cable(termination_a=trunk, termination_b=front1, cable_type=breakout, status=self.connected)
        cable.save()
        cable.add_termination(front2, "B", connector=2)
        cable.add_termination(front3, "B", connector=3)

        # The rear ports must continue onward (here, straight to interfaces) so the front→rear
        # pass-through is mid-leg — only then are the rear ports actually rendered.
        dest1 = Interface.objects.create(device=self.device, name="grp-dest-1", status=self.interface_status)
        dest2 = Interface.objects.create(device=self.device, name="grp-dest-2", status=self.interface_status)
        Cable.objects.create(termination_a=shared_rear, termination_b=dest1, status=self.connected)
        Cable.objects.create(termination_a=other_rear, termination_b=dest2, status=self.connected)

        svg = CableTraceSVG(trunk).render()
        # The shared rear port is drawn once (consecutive run), the distinct one once.
        self.assertEqual(svg.count("Rear-Shared"), 1, "Shared rear port should render once, not per leg")
        self.assertEqual(svg.count("Rear-Other"), 1)

    def _make_breakout_trunk_terminus(self):
        """A leaf interface breakout-cabled to a trunk that has a child (sub)interface on lane 1.

        Returns `(leaf, trunk, child)`. Tracing from `leaf` ends on the breakout trunk `trunk`,
        whose child interface `child` maps to the trunk-connector position `leaf`'s lane carries.
        """
        breakout = CableType(name="SVG terminus 1x2", a_connectors=1, b_connectors=2, total_lanes=2)
        breakout.validated_save()
        trunk = Interface.objects.create(
            device=self.device,
            name="terminus-trunk",
            type=InterfaceTypeChoices.TYPE_40GE_QSFP_PLUS,
            status=self.interface_status,
        )
        child = Interface.objects.create(
            device=self.device,
            name="terminus-trunk.1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            status=self.interface_status,
            parent_interface=trunk,
            breakout_position=1,
        )
        leaf = Interface.objects.create(
            device=self.device,
            name="terminus-leaf",
            type=InterfaceTypeChoices.TYPE_10GE_SFP_PLUS,
            status=self.interface_status,
        )
        # trunk (A1) --breakout--> leaf (B1); the leaf's lane maps back to child position 1.
        Cable(termination_a=trunk, termination_b=leaf, cable_type=breakout, status=self.connected).save()
        return leaf, trunk, child

    def test_trace_ending_in_breakout_trunk_renders_subinterface_box(self):
        """A trace ending on a breakout trunk folds the trunk's mapped child interface onto the
        terminal device as a passthrough-style departing port (the trunk port on top, the child
        (sub)interface box below it)."""
        leaf, trunk, child = self._make_breakout_trunk_terminus()
        self.assertEqual(leaf.get_breakout_trunk_child_interface_for_endpoint(trunk), child)

        diagram = CableTraceSVG(leaf)
        terminal_cells = [
            cell
            for cell in self._matrix_cells(diagram)
            if cell["type"] == "passthrough_node" and cell.get("arriving") == trunk
        ]
        self.assertEqual(len(terminal_cells), 1, "Terminal trunk node should fold into a passthrough node")
        self.assertEqual(terminal_cells[0]["departing"], child)

        svg = diagram.render()
        self.assertIn(str(child), svg)

    def test_trace_from_subinterface_renders_single_lane_with_subinterface_on_top(self):
        """Tracing from a breakout child (sub)interface follows only the parent trunk's matching lane
        (a single linear leg, not the trunk's full fan-out) and draws the originating subinterface
        atop its parent trunk port — the vertical mirror of a trace ending on that trunk."""
        leaf, trunk, child = self._make_breakout_trunk_terminus()

        diagram = CableTraceSVG(child)
        # The child interface has no CablePath of its own; the renderer follows the parent trunk's lane.
        self.assertEqual(diagram.trunk_origin, trunk)
        self.assertEqual(len(diagram.fanout_paths), 1, "A subinterface trace follows one lane, not a fan-out")
        self.assertEqual(diagram.fanout_paths[0]["termination"], leaf)

        svg = diagram.render()
        # The subinterface (origin), its parent trunk, and the far endpoint all appear.
        self.assertIn(str(child), svg)
        self.assertIn(str(trunk), svg)
        self.assertIn(str(leaf), svg)
        # The origin subinterface is highlighted (active termination box: success stroke, width 3).
        self.assertIn(f'stroke="{svg_constants.COLOR_SUCCESS}"', svg)

    def test_trace_from_subinterface_with_explicit_cable_path(self):
        """Passing the parent trunk's lane `CablePath` explicitly (as the view does for a
        `?cablepath_id=` selection) renders the same single-lane, subinterface-on-top trace."""
        leaf, trunk, child = self._make_breakout_trunk_terminus()
        lane = child.get_breakout_lane()
        path = next(p for p in trunk.cable_paths.all() if p.peer_connector == lane.far_connector)

        diagram = CableTraceSVG(child, cable_path=path)
        self.assertEqual(diagram.trunk_origin, trunk)
        self.assertEqual(len(diagram.fanout_paths), 1)
        svg = diagram.render()
        self.assertIn(str(child), svg)
        self.assertIn(str(leaf), svg)

    def test_trace_from_trunk_side_does_not_render_subinterface_box(self):
        """Tracing the *other* direction — from the trunk out to its fan-out leaf — leaves the leaf
        as a plain terminal `node`: the leaf isn't a breakout trunk, so no child-interface box is
        folded onto it (the subinterface only renders when the trace *ends* on a trunk)."""
        leaf, trunk, _child = self._make_breakout_trunk_terminus()

        cells = self._matrix_cells(CableTraceSVG(trunk))
        leaf_nodes = [cell for cell in cells if cell["type"] == "node" and cell.get("termination") == leaf]
        self.assertEqual(len(leaf_nodes), 1, "Fan-out leaf should remain a plain terminal node")
        self.assertFalse(any(cell["type"] == "passthrough_node" for cell in cells))
