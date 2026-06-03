"""Unit tests for DCIM SVG rendering helpers."""

import functools
import re

from django.test import SimpleTestCase

from nautobot.core.testing import TestCase
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
    RearPort,
)
from nautobot.dcim.svg.cable_breakout import BreakoutDiagramSVG
from nautobot.dcim.svg.path_trace import CableTraceSVG
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
        from django.utils.safestring import SafeString

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
        label_width = len(long_label) * diagram.FONT_SIZE * diagram.FONT_WIDTH_RATIO
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
