"""Unit tests for DCIM SVG rendering helpers."""

import re

from django.test import SimpleTestCase

from nautobot.dcim.models import CableBreakoutType
from nautobot.dcim.svg.cable_breakout import BreakoutDiagramSVG


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


def _pill_rects(svg):
    """Return [(x, y), ...] for each label pill rect (identified by width=18)."""
    pills = []
    for match in re.finditer(r"<rect\b([^/]*)/>", svg):
        attrs = match.group(1)
        # Use lookbehind to avoid matching `stroke-width=` when searching for `width=`.
        width_match = re.search(r'(?<![-\w])width="([^"]+)"', attrs)
        x_match = re.search(r'(?<![-\w])x="([^"]+)"', attrs)
        y_match = re.search(r'(?<![-\w])y="([^"]+)"', attrs)
        if width_match and x_match and y_match and float(width_match.group(1)) == 18:
            pills.append((float(x_match.group(1)), float(y_match.group(1))))
    return pills


class BreakoutDiagramSVGTest(SimpleTestCase):
    """Tests for nautobot.dcim.svg.cable_breakout.BreakoutDiagramSVG."""

    def _render(self, **kwargs):
        mapping = CableBreakoutType.autogenerate_mapping(**kwargs)
        return mapping, BreakoutDiagramSVG(mapping, show_status=False).render()

    def test_endpoint_offset_single_position(self):
        """A connector with a single position should not offset its lane endpoints."""
        mapping = CableBreakoutType.autogenerate_mapping(a_connectors=1, b_connectors=1, total_lanes=1)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)
        self.assertEqual(diagram._endpoint_offset(1, 1, diagram.a_node_h), 0)

    def test_endpoint_offset_multiple_positions_symmetric(self):
        """With >1 positions, offsets should straddle zero within +/- node_h * fraction / 2."""
        mapping = CableBreakoutType.autogenerate_mapping(a_connectors=1, b_connectors=1, total_lanes=4)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)

        offsets = [diagram._endpoint_offset(p, 4, diagram.a_node_h) for p in range(1, 5)]
        # Symmetric about zero and monotonically increasing.
        self.assertAlmostEqual(offsets[0], -offsets[-1])
        self.assertAlmostEqual(offsets[1], -offsets[-2])
        self.assertEqual(sorted(offsets), offsets)
        # All offsets sit within the node height.
        for offset in offsets:
            self.assertLess(abs(offset), diagram.a_node_h / 2)

    def test_node_height_scales_with_positions(self):
        """A connector's node height grows with positions-per-connector."""
        small_diagram = BreakoutDiagramSVG(
            CableBreakoutType.autogenerate_mapping(a_connectors=1, b_connectors=1, total_lanes=1), show_status=False
        )
        large_diagram = BreakoutDiagramSVG(
            CableBreakoutType.autogenerate_mapping(a_connectors=1, b_connectors=2, total_lanes=12), show_status=False
        )

        # Small: 1 position → minimum height.
        self.assertEqual(small_diagram.a_node_h, BreakoutDiagramSVG.NODE_H_MIN)
        # Large: 12 A-positions → height = 12 * LANE_PITCH.
        self.assertEqual(large_diagram.a_node_h, 12 * BreakoutDiagramSVG.LANE_PITCH)
        # Large: 6 B-positions per connector → height = 6 * LANE_PITCH.
        self.assertEqual(large_diagram.b_node_h, 6 * BreakoutDiagramSVG.LANE_PITCH)

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
        """Distinct endpoints must still fall within the A and B node boundaries."""
        mapping, svg = self._render(a_connectors=1, b_connectors=1, total_lanes=4)
        diagram = BreakoutDiagramSVG(mapping, show_status=False)
        a_pos, b_pos = diagram._node_positions()
        a_center = a_pos[1]
        b_center = b_pos[1]

        for _, y1, _, y2 in _line_endpoints(svg):
            self.assertLessEqual(abs(y1 - a_center), diagram.a_node_h / 2)
            self.assertLessEqual(abs(y2 - b_center), diagram.b_node_h / 2)

    def test_breakout_one_to_many_distinct_a_side_offsets(self):
        """A 1:N breakout must spread A-side endpoints based on a_position."""
        _, svg = self._render(a_connectors=1, b_connectors=4, total_lanes=8)
        endpoints = _line_endpoints(svg)
        self.assertEqual(len(endpoints), 8)

        # total_lanes=8, a_connectors=1 → a_positions=8. Every lane leaves the
        # single A node at a distinct y, instead of all piling onto its center.
        y_starts = {y1 for (_, y1, _, _) in endpoints}
        self.assertEqual(len(y_starts), 8)

        # b_connectors=4, b_positions=2 → each B node receives exactly 2 lanes
        # at 2 distinct y values. Group endpoints by their nearest b center.
        diagram = BreakoutDiagramSVG(
            CableBreakoutType.autogenerate_mapping(a_connectors=1, b_connectors=4, total_lanes=8), show_status=False
        )
        _, b_pos = diagram._node_positions()
        lanes_per_b = {bc: set() for bc in b_pos}
        for _, _, _, y2 in endpoints:
            nearest_bc = min(b_pos, key=lambda bc: abs(b_pos[bc] - y2))
            lanes_per_b[nearest_bc].add(round(y2, 4))
        for bc, y_values in lanes_per_b.items():
            self.assertEqual(len(y_values), 2, f"B connector {bc} should receive 2 distinct y values")

    def test_dense_breakout_one_to_two_twelve_lanes(self):
        """A 1:2 breakout with 12 lanes (6 parallel per pair) must render all 12 legibly.

        Every line endpoint must be distinct on both sides, label pills must
        have distinct x coordinates within each parallel-lane group, and all
        endpoints must fit inside their connector nodes.
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
        a_pos, b_pos = diagram._node_positions()
        lanes_per_b = {bc: set() for bc in b_pos}
        for _, _, _, y2 in endpoints:
            nearest_bc = min(b_pos, key=lambda bc: abs(b_pos[bc] - y2))
            lanes_per_b[nearest_bc].add(round(y2, 4))
        for bc, y_values in lanes_per_b.items():
            self.assertEqual(len(y_values), 6, f"B connector {bc} should receive 6 distinct y values")

        # All endpoints stay inside their connector's node rect.
        for _, y1, _, y2 in endpoints:
            self.assertLessEqual(abs(y1 - a_pos[1]), diagram.a_node_h / 2)
            nearest_bc = min(b_pos, key=lambda bc: abs(b_pos[bc] - y2))
            self.assertLessEqual(abs(y2 - b_pos[nearest_bc]), diagram.b_node_h / 2)

        # Label pills: each of the 12 lanes gets its own distinct pill position.
        # Pills in different pairs may share an x value (they sit at different
        # y values because those two pairs' lines have different slopes).
        pills = _pill_rects(svg)
        self.assertEqual(len(pills), 12)
        self.assertEqual(len(set(pills)), 12)
        # Each of the 2 parallel-lane groups places its 6 pills at 6 distinct x
        # values; each pair reuses the same 6 x values, so the total unique x count is 6.
        self.assertEqual(len({x for (x, _) in pills}), 6)

    def test_lane_labels_staggered_for_parallel_lanes(self):
        """When multiple lanes share a connector pair, label pills must not stack at the same x."""
        _, svg = self._render(a_connectors=1, b_connectors=1, total_lanes=4)
        pill_x_values = [x for (x, _) in _pill_rects(svg)]
        self.assertEqual(len(pill_x_values), 4)
        self.assertEqual(len(set(pill_x_values)), 4, "Parallel-lane labels should not overlap in x")
