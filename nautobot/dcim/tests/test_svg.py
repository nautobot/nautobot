"""Unit tests for DCIM SVG rendering helpers."""

import functools
import re

from django.test import SimpleTestCase

from nautobot.dcim.svg.cable_breakout import BreakoutDiagramSVG
from nautobot.dcim.utils import generate_cable_breakout_mapping


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
