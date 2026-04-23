"""Server-side SVG generation for breakout cable lane mapping diagrams."""

from dataclasses import dataclass

from django.utils.html import mark_safe
import svgwrite


@dataclass(frozen=True)
class MappingEntry:
    """A single row in a CableBreakoutType mapping."""

    label: str
    a_connector: int
    a_position: int
    b_connector: int
    b_position: int


class BreakoutDiagramSVG:
    """
    Generate an SVG diagram showing the lane mapping of a cable breakout type.

    Usage:
        diagram = BreakoutDiagramSVG(mapping, a_termination_labels={1: "Device1 / Eth1"})
        svg_string = diagram.render()
    """

    NODE_H_MIN = 28
    NODE_W = 60
    NODE_R = 4  # border radius
    GAP = 4
    LINE_AREA_W_MIN = 80
    LANE_PITCH = 14  # minimum vertical spacing between lane endpoints within a node
    PILL_PITCH = 22  # minimum horizontal spacing between staggered labels for parallel lanes
    PILL_W = 18
    PILL_H = 14
    FONT_SIZE = 12
    FONT_FAMILY = "var(--bs-font-sans-serif)"

    COLOR_CONNECTED = "var(--bs-success)"
    COLOR_DISCONNECTED = "var(--bs-tertiary-color)"
    COLOR_NODE_BG_CONNECTED = "var(--bs-success)"
    COLOR_NODE_BG_DEFAULT = "var(--bs-tertiary-color)"
    COLOR_NODE_TEXT = "var(--bs-body-color)"

    def __init__(
        self,
        mapping,
        show_status=True,
        a_termination_labels=None,
        b_termination_labels=None,
    ):
        """
        Args:
            mapping: list of dicts describing each lane, e.g. from `CableBreakoutType.mapping`.
                Each entry must contain keys: `label`, `a_connector`, `a_position`, `b_connector`, `b_position`.
            show_status: if True, color connected nodes green
            a_termination_labels: dict {connector_num: "Device / Interface"} for A-side tooltips
            b_termination_labels: dict {connector_num: "Device / Interface"} for B-side tooltips
        """
        self.show_status = show_status
        self.a_labels = a_termination_labels or {}
        self.b_labels = b_termination_labels or {}

        # Build connector mapping, e.g. self.a_to_b = {1: {1, 2}} and self.b_to_a = {1: {1}, 2: {1}}
        self.a_to_b = {}
        self.b_to_a = {}
        # Set of tuples of (label, a_connector, a_position, b_connector, b_position)
        self.pairs = set()
        for entry in mapping:
            self.a_to_b.setdefault(entry["a_connector"], set()).add(entry["b_connector"])
            self.b_to_a.setdefault(entry["b_connector"], set()).add(entry["a_connector"])
            self.pairs.add(MappingEntry(**entry))

        self.a_connectors = sorted(self.a_to_b.keys())
        self.b_connectors = sorted(self.b_to_a.keys())

        # Total rows = number of unique (a, b) pairs
        self.total_rows = len(self.pairs)

        # Positions-per-connector derived from the mapping: the largest position index
        # seen on each side (equivalent to total_lanes // connectors when mapping is complete).
        self.a_positions = max((entry.a_position for entry in self.pairs), default=0)
        self.b_positions = max((entry.b_position for entry in self.pairs), default=0)

        # Group lanes by (a_connector, b_connector) so parallel lanes between the
        # same pair can be staggered horizontally to keep their labels legible.
        self.pair_groups = {}
        for entry in self.pairs:
            key = (entry.a_connector, entry.b_connector)
            self.pair_groups.setdefault(key, []).append(entry)
        for group in self.pair_groups.values():
            group.sort(key=lambda e: (e.a_position, e.b_position))

        # Node heights scale with positions-per-connector so many parallel lanes
        # can spread out vertically without overlapping.
        self.a_node_h = max(self.NODE_H_MIN, self.a_positions * self.LANE_PITCH)
        self.b_node_h = max(self.NODE_H_MIN, self.b_positions * self.LANE_PITCH)

        # Line area width scales with the largest group of parallel lanes so that
        # staggered label pills within a single (a, b) pair don't overlap horizontally.
        max_parallel = max((len(g) for g in self.pair_groups.values()), default=1)
        self.line_area_w = max(self.LINE_AREA_W_MIN, (max_parallel + 1) * self.PILL_PITCH)

    def _endpoint_offset(self, position, total_positions, node_h):
        """Vertical offset within a connector node for the given 1-indexed lane position."""
        if total_positions <= 1:
            return 0
        fraction = 0.7
        span = node_h * fraction
        return -span / 2 + (position - 1) * span / (total_positions - 1)

    def _total_height(self):
        n_a = len(self.a_connectors)
        n_b = len(self.b_connectors)
        h_a = n_a * self.a_node_h + (n_a + 1) * self.GAP
        h_b = n_b * self.b_node_h + (n_b + 1) * self.GAP
        return max(h_a, h_b)

    def _total_width(self):
        return self.NODE_W + self.line_area_w + self.NODE_W + 20  # padding

    def _node_positions(self):
        """
        Return {side: {connector: y_center}} with all nodes at consistent height.

        The side with more connectors sets the total height. The side with fewer
        connectors has its nodes vertically centered within the span of their
        mapped partners.
        """
        n_a = len(self.a_connectors)
        n_b = len(self.b_connectors)
        total_h = self._total_height()

        # Position the side with more connectors evenly, tiled node_h + GAP apart
        def _even_positions(connectors, node_h):
            return {c: self.GAP + i * (node_h + self.GAP) + node_h / 2 for i, c in enumerate(connectors)}

        # Position the side with fewer connectors centered on their mapped partners
        def _centered_positions(connectors, mapping, other_positions):
            positions = {}
            for c in connectors:
                mapped = sorted(mapping.get(c, []))
                if mapped:
                    y_min = other_positions[mapped[0]]
                    y_max = other_positions[mapped[-1]]
                    positions[c] = (y_min + y_max) / 2
                else:
                    positions[c] = total_h / 2
            return positions

        if n_a >= n_b:
            a_pos = _even_positions(self.a_connectors, self.a_node_h)
            b_pos = _centered_positions(self.b_connectors, self.b_to_a, a_pos)
        else:
            b_pos = _even_positions(self.b_connectors, self.b_node_h)
            a_pos = _centered_positions(self.a_connectors, self.a_to_b, b_pos)

        return a_pos, b_pos

    def render(self):
        a_pos, b_pos = self._node_positions()

        w = self._total_width()
        h = self._total_height()

        dwg = svgwrite.Drawing(size=(f"{w}px", f"{h}px"), debug=False)
        dwg.viewbox(0, 0, w, h)

        a_x = 5
        b_x = w - self.NODE_W - 5
        a_right = a_x + self.NODE_W
        b_left = b_x

        start_x = a_right + 2
        end_x = b_left - 2

        # Draw lines first (behind nodes)
        for entry in self.pairs:
            ay = a_pos[entry.a_connector] + self._endpoint_offset(entry.a_position, self.a_positions, self.a_node_h)
            by = b_pos[entry.b_connector] + self._endpoint_offset(entry.b_position, self.b_positions, self.b_node_h)

            a_conn = self.show_status and entry.a_connector in self.a_labels
            b_conn = self.show_status and entry.b_connector in self.b_labels
            both = a_conn and b_conn

            color = self.COLOR_CONNECTED if both else self.COLOR_DISCONNECTED
            width = 2 if both or not self.show_status else 1.5
            dasharray = None if both or not self.show_status else "6,4"

            line = dwg.line(
                start=(start_x, ay),
                end=(end_x, by),
                stroke=color,
                stroke_width=width,
            )
            if dasharray:
                line["stroke-dasharray"] = dasharray
            dwg.add(line)

            # Stagger the label along the line when multiple lanes share the same
            # (a_connector, b_connector) pair, so the pills don't sit on top of each other.
            group = self.pair_groups[(entry.a_connector, entry.b_connector)]
            idx = group.index(entry)
            t = (idx + 1) / (len(group) + 1)
            mid_x = start_x + t * (end_x - start_x)
            mid_y = ay + t * (by - ay)
            label_size = self.FONT_SIZE - 1
            dwg.add(
                dwg.rect(
                    insert=(mid_x - self.PILL_W / 2, mid_y - self.PILL_H / 2),
                    size=(self.PILL_W, self.PILL_H),
                    rx=self.PILL_H / 2,
                    ry=self.PILL_H / 2,
                    fill="var(--bs-body-bg)",
                    stroke=color,
                    stroke_width=1,
                )
            )
            dwg.add(
                dwg.text(
                    entry.label,
                    insert=(mid_x, mid_y + label_size / 3),
                    text_anchor="middle",
                    fill=color,
                    font_size=f"{label_size}px",
                    font_family=self.FONT_FAMILY,
                    font_weight="bold",
                )
            )

        # Draw A-side nodes (all same height, with tooltips)
        for ac in self.a_connectors:
            y_center = a_pos[ac]
            connected = self.show_status and ac in self.a_labels
            bg = self.COLOR_NODE_BG_CONNECTED if connected else self.COLOR_NODE_BG_DEFAULT

            group = dwg.g()

            tooltip = self.a_labels.get(ac, f"A{ac} — Unconnected")
            # Tooltip — svgwrite doesn't have a Title helper, so we post-process the SVG string
            group["data-tooltip"] = tooltip

            group.add(
                dwg.rect(
                    insert=(a_x, y_center - self.a_node_h / 2),
                    size=(self.NODE_W, self.a_node_h),
                    rx=self.NODE_R,
                    ry=self.NODE_R,
                    fill=bg,
                    style="cursor: pointer;",
                )
            )

            label = f"A{ac}"
            if self.a_positions > 1:
                label += f" ({self.a_positions})"

            group.add(
                dwg.text(
                    label,
                    insert=(a_x + self.NODE_W / 2, y_center + self.FONT_SIZE / 3),
                    text_anchor="middle",
                    fill=self.COLOR_NODE_TEXT,
                    font_size=f"{self.FONT_SIZE}px",
                    font_family=self.FONT_FAMILY,
                    font_weight="bold",
                    style="pointer-events: none;",
                )
            )
            dwg.add(group)

        # Draw B-side nodes (all same height, with tooltips)
        for bc in self.b_connectors:
            y_center = b_pos[bc]
            connected = self.show_status and bc in self.b_labels
            bg = self.COLOR_NODE_BG_CONNECTED if connected else self.COLOR_NODE_BG_DEFAULT

            group = dwg.g()

            tooltip = self.b_labels.get(bc, f"B{bc} — Unconnected")
            # Tooltip — svgwrite doesn't have a Title helper, so we post-process the SVG string
            group["data-tooltip"] = tooltip

            group.add(
                dwg.rect(
                    insert=(b_x, y_center - self.b_node_h / 2),
                    size=(self.NODE_W, self.b_node_h),
                    rx=self.NODE_R,
                    ry=self.NODE_R,
                    fill=bg,
                    style="cursor: pointer;",
                )
            )

            label = f"B{bc}"
            if self.b_positions > 1:
                label += f" ({self.b_positions})"

            group.add(
                dwg.text(
                    label,
                    insert=(b_x + self.NODE_W / 2, y_center + self.FONT_SIZE / 3),
                    text_anchor="middle",
                    fill=self.COLOR_NODE_TEXT,
                    font_size=f"{self.FONT_SIZE}px",
                    font_family=self.FONT_FAMILY,
                    font_weight="bold",
                    style="pointer-events: none;",
                )
            )
            dwg.add(group)

        import re

        svg_str = dwg.tostring()

        # Post-process: convert data-tooltip="text" into <title>text</title> inside <g> elements
        svg_str = re.sub(
            r'<g([^>]*) data-tooltip="([^"]*)"([^>]*)>',
            lambda m: f"<g{m.group(1)}{m.group(3)}><title>{m.group(2)}</title>",
            svg_str,
        )

        return mark_safe(svg_str)  # noqa: S308
