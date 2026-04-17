"""Server-side SVG generation for breakout cable lane mapping diagrams."""

from django.utils.html import mark_safe

import svgwrite


class BreakoutDiagramSVG:
    """
    Generate an SVG diagram showing the lane mapping of a cable breakout type.

    Usage:
        diagram = BreakoutDiagramSVG(cable_breakout_type, connected_a={1}, connected_b={1,2,3})
        svg_string = diagram.render()
    """

    NODE_H = 28
    NODE_W = 60
    NODE_R = 4  # border radius
    GAP = 4
    LINE_AREA_W = 80
    FONT_SIZE = 12
    FONT_FAMILY = "system-ui, -apple-system, sans-serif"

    COLOR_CONNECTED = "#198754"
    COLOR_DISCONNECTED = "#adb5bd"
    COLOR_NODE_BG_CONNECTED = "#198754"
    COLOR_NODE_BG_DEFAULT = "#6c757d"
    COLOR_NODE_TEXT = "#ffffff"

    def __init__(
        self,
        cable_breakout_type,
        connected_a=None,
        connected_b=None,
        show_status=True,
        a_termination_labels=None,
        b_termination_labels=None,
    ):
        """
        Args:
            cable_breakout_type: CableBreakoutType instance
            connected_a: set of A connector numbers with terminations
            connected_b: set of B connector numbers with terminations
            show_status: if True, color connected nodes green
            a_termination_labels: dict {connector_num: "Device / Interface"} for A-side tooltips
            b_termination_labels: dict {connector_num: "Device / Interface"} for B-side tooltips
        """
        self.cable_breakout_type = cable_breakout_type
        self.connected_a = connected_a or set()
        self.connected_b = connected_b or set()
        self.show_status = show_status
        self.a_labels = a_termination_labels or {}
        self.b_labels = b_termination_labels or {}

        # Build connector mapping
        self.a_to_b = {}
        self.b_to_a = {}
        for entry in cable_breakout_type.mapping:
            self.a_to_b.setdefault(entry["a_connector"], set()).add(entry["b_connector"])
            self.b_to_a.setdefault(entry["b_connector"], set()).add(entry["a_connector"])

        self.a_connectors = sorted(self.a_to_b.keys())
        self.b_connectors = sorted(self.b_to_a.keys())

        # Total rows = number of unique (a, b) pairs
        self.pairs = []
        seen = set()
        for entry in cable_breakout_type.mapping:
            pair = (entry["label"], entry["a_connector"], entry["b_connector"])
            if pair not in seen:
                self.pairs.append(pair)
                seen.add(pair)

        self.total_rows = len(self.pairs)

    def _total_height(self):
        return self.total_rows * (self.NODE_H + self.GAP) + self.GAP

    def _total_width(self):
        return self.NODE_W + self.LINE_AREA_W + self.NODE_W + 20  # padding

    def _node_positions(self):
        """
        Return {side: {connector: y_center}} with all nodes at consistent height.

        The side with more connectors sets the total height. The side with fewer
        connectors has its nodes vertically centered within the span of their
        mapped partners.
        """
        n_a = len(self.a_connectors)
        n_b = len(self.b_connectors)
        max_n = max(n_a, n_b)
        total_h = max_n * (self.NODE_H + self.GAP) + self.GAP

        # Position the side with more connectors evenly
        def _even_positions(connectors):
            n = len(connectors)
            spacing = total_h / n
            return {c: self.GAP + i * spacing + spacing / 2 for i, c in enumerate(connectors)}

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
            a_pos = _even_positions(self.a_connectors)
            b_pos = _centered_positions(self.b_connectors, self.b_to_a, a_pos)
        else:
            b_pos = _even_positions(self.b_connectors)
            a_pos = _centered_positions(self.a_connectors, self.a_to_b, b_pos)

        return a_pos, b_pos, total_h

    def render(self):
        a_pos, b_pos, total_h = self._node_positions()

        w = self._total_width()
        h = total_h

        dwg = svgwrite.Drawing(size=(f"{w}px", f"{h}px"), debug=False)
        dwg.viewbox(0, 0, w, h)

        a_x = 5
        b_x = w - self.NODE_W - 5
        a_right = a_x + self.NODE_W
        b_left = b_x

        # Draw lines first (behind nodes)
        for label, ac, bc in self.pairs:
            ay = a_pos[ac]
            by = b_pos[bc]

            a_conn = self.show_status and ac in self.connected_a
            b_conn = self.show_status and bc in self.connected_b
            both = a_conn and b_conn

            color = self.COLOR_CONNECTED if both else self.COLOR_DISCONNECTED
            width = 2 if both else 1.5
            dasharray = None if both or not self.show_status else "6,4"

            line = dwg.line(
                start=(a_right + 2, ay),
                end=(b_left - 2, by),
                stroke=color,
                stroke_width=width,
            )
            if dasharray:
                line["stroke-dasharray"] = dasharray
            dwg.add(line)

            # Lane label at the midpoint of the line with white background pill
            mid_x = (a_right + 2 + b_left - 2) / 2
            mid_y = (ay + by) / 2
            label_size = self.FONT_SIZE - 1
            pill_w = 18
            pill_h = 14
            dwg.add(
                dwg.rect(
                    insert=(mid_x - pill_w / 2, mid_y - pill_h / 2),
                    size=(pill_w, pill_h),
                    rx=pill_h / 2,
                    ry=pill_h / 2,
                    fill="white",
                    stroke=color,
                    stroke_width=1,
                )
            )
            dwg.add(
                dwg.text(
                    label, 
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
            connected = self.show_status and ac in self.connected_a
            bg = self.COLOR_NODE_BG_CONNECTED if connected else self.COLOR_NODE_BG_DEFAULT

            group = dwg.g()

            tooltip = self.a_labels.get(ac, f"A{ac} — Unconnected")
            # Tooltip — svgwrite doesn't have a Title helper, so we post-process the SVG string
            group["data-tooltip"] = tooltip

            group.add(
                dwg.rect(
                    insert=(a_x, y_center - self.NODE_H / 2),
                    size=(self.NODE_W, self.NODE_H),
                    rx=self.NODE_R,
                    ry=self.NODE_R,
                    fill=bg,
                    style="cursor: pointer;",
                )
            )

            label = f"A{ac}"
            if self.cable_breakout_type.a_positions > 1:
                label += f" ({self.cable_breakout_type.a_positions})"

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
            connected = self.show_status and bc in self.connected_b
            bg = self.COLOR_NODE_BG_CONNECTED if connected else self.COLOR_NODE_BG_DEFAULT

            group = dwg.g()

            tooltip = self.b_labels.get(bc, f"B{bc} — Unconnected")
            # Tooltip — svgwrite doesn't have a Title helper, so we post-process the SVG string
            group["data-tooltip"] = tooltip

            group.add(
                dwg.rect(
                    insert=(b_x, y_center - self.NODE_H / 2),
                    size=(self.NODE_W, self.NODE_H),
                    rx=self.NODE_R,
                    ry=self.NODE_R,
                    fill=bg,
                    style="cursor: pointer;",
                )
            )

            label = f"B{bc}"
            if self.cable_breakout_type.b_positions > 1:
                label += f" ({self.cable_breakout_type.b_positions})"

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

        return mark_safe(svg_str)
