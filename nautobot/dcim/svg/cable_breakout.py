"""Server-side SVG generation for breakout cable lane mapping diagrams."""

from dataclasses import dataclass

from django.utils.html import mark_safe
import svgwrite

from nautobot.dcim.utils import validate_cable_breakout_mapping


@dataclass(frozen=True)
class MappingEntry:
    """A single row in a CableType mapping."""

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

    CONNECTOR_WIDTH = 80
    CONNECTOR_CORNER_RADIUS = 4
    SPACE_BETWEEN_CONNECTORS = 4
    MINIMUM_LINE_AREA_WIDTH = 80
    LANE_X_GAP = 1  # space between the connector and the lane
    LANE_Y_SPACING = 14  # minimum vertical spacing between lane endpoints within a connector
    CONNECTOR_FONT_SIZE = 14
    LANE_LABEL_FONT_SIZE = 12
    LANE_LABEL_HEIGHT = LANE_LABEL_FONT_SIZE + 4
    FONT_FAMILY = "var(--bs-font-sans-serif)"

    COLOR_LANE_CONNECTED = "var(--bs-success)"
    COLOR_LANE_DISCONNECTED = "var(--bs-tertiary-color)"
    COLOR_CONNECTOR_FILL_CONNECTED = "var(--bs-success)"
    COLOR_CONNECTOR_FILL_DEFAULT = "var(--bs-tertiary-color)"
    COLOR_TEXT = "var(--bs-body-color)"
    COLOR_BACKGROUND = "var(--bs-body-bg)"

    def __init__(
        self,
        mapping,
        show_status=True,
        a_termination_labels=None,
        b_termination_labels=None,
    ):
        """
        Args:
            mapping: list of dicts describing each lane, e.g. from `CableType.mapping`.
                Each entry must contain keys: `label`, `a_connector`, `a_position`, `b_connector`, `b_position`.
            show_status: if True, color connected lanes/connectors as green
            a_termination_labels: dict {connector_num: "Device / Interface"} for A-side tooltips
            b_termination_labels: dict {connector_num: "Device / Interface"} for B-side tooltips
        """
        mapping, self.a_connectors, self.b_connectors, self.total_lanes = validate_cable_breakout_mapping(mapping)
        self.a_positions = self.total_lanes // self.a_connectors
        self.b_positions = self.total_lanes // self.b_connectors

        self.show_status = show_status
        self.a_labels = a_termination_labels or {}
        self.b_labels = b_termination_labels or {}

        self.entries = {MappingEntry(**entry) for entry in mapping}

        # Group lanes by (a_connector, b_connector) so parallel lanes between the
        # same pair can be staggered horizontally to keep their labels legible.
        self.lane_groups = {}
        for entry in self.entries:
            key = (entry.a_connector, entry.b_connector)
            self.lane_groups.setdefault(key, []).append(entry)
        for group in self.lane_groups.values():
            group.sort(key=lambda e: (e.a_position, e.b_position))

        # Node heights scale with positions-per-connector so many parallel lanes
        # can spread out vertically without overlapping.
        self.a_connector_height = (self.a_positions + 1) * self.LANE_Y_SPACING
        self.b_connector_height = (self.b_positions + 1) * self.LANE_Y_SPACING

        # Line area width scales with the largest group of parallel lanes so that
        # staggered labels within a single (a, b) pair don't overlap horizontally.
        max_parallel_lanes = max((len(g) for g in self.lane_groups.values()), default=1)
        lane_label_x_spacing = max(len(e.label) + 1 for e in self.entries) * self.LANE_LABEL_FONT_SIZE / 2
        self.line_area_width = max(self.MINIMUM_LINE_AREA_WIDTH, (max_parallel_lanes + 1) * lane_label_x_spacing)

    def _y_offset(self, position, total_positions, connector_height):
        """Vertical offset relative to a connector's center for the given 1-indexed lane position."""
        if total_positions == 1:  # single position, avoid dividing by zero
            return 0  # centered
        span = connector_height - (2 * self.LANE_Y_SPACING)
        return ((position - 1) * span / (total_positions - 1)) - (span / 2)

    def _total_height(self):
        """Total height of the SVG - whichever connector side is taller, usually the B side."""
        h_a = (self.a_connectors * self.a_connector_height) + ((self.a_connectors - 1) * self.SPACE_BETWEEN_CONNECTORS)
        h_b = (self.b_connectors * self.b_connector_height) + ((self.b_connectors - 1) * self.SPACE_BETWEEN_CONNECTORS)
        return max(h_a, h_b)

    def _total_width(self):
        """Total width of the SVG - two connectors plus the line area between them."""
        return self.CONNECTOR_WIDTH + self.line_area_width + self.CONNECTOR_WIDTH

    def _connector_y_centers(self):
        """Calculate the Y centers for centered, evenly spaced connectors on each side of the diagram."""
        # Position B side (more connectors) evenly, spaced b_connector_height + SPACE_BETWEEN_CONNECTORS apart
        b_connector_y_centers = {
            i: self.b_connector_height / 2 + (i - 1) * (self.b_connector_height + self.SPACE_BETWEEN_CONNECTORS)
            for i in range(1, self.b_connectors + 1)
        }

        # Position A side (same or fewer connectors) centered overall and similarly spaced by a_connector_height
        a_connector_y_offset = (
            (self.b_connector_height + self.SPACE_BETWEEN_CONNECTORS) * self.b_connectors
            - (self.a_connector_height + self.SPACE_BETWEEN_CONNECTORS) * self.a_connectors
        ) / 2
        a_connector_y_centers = {
            i: (
                a_connector_y_offset
                + self.a_connector_height / 2
                + (i - 1) * (self.a_connector_height + self.SPACE_BETWEEN_CONNECTORS)
            )
            for i in range(1, self.a_connectors + 1)
        }

        return a_connector_y_centers, b_connector_y_centers

    def _render_connectors(
        self, drawing, side, positions, connectors, x, connector_y_centers, connector_height, labels
    ):
        for connector in range(1, connectors + 1):
            y_center = connector_y_centers[connector]
            connected = self.show_status and connector in labels
            bg = self.COLOR_CONNECTOR_FILL_CONNECTED if connected else self.COLOR_CONNECTOR_FILL_DEFAULT

            group = drawing.g()

            tooltip = labels.get(connector, f"{side}{connector} - Unconnected")
            group.set_desc(tooltip)

            group.add(
                drawing.rect(
                    insert=(x, y_center - connector_height / 2),
                    size=(self.CONNECTOR_WIDTH, connector_height),
                    rx=self.CONNECTOR_CORNER_RADIUS,
                    ry=self.CONNECTOR_CORNER_RADIUS,
                    fill=bg,
                    style="cursor: pointer;",
                )
            )

            label = f"{side}{connector}"
            if positions > 1:
                label += f" ({positions})"
            group.add(
                drawing.text(
                    label,
                    insert=(x + self.CONNECTOR_WIDTH / 2, y_center + self.CONNECTOR_FONT_SIZE / 3),
                    text_anchor="middle",
                    fill=self.COLOR_TEXT,
                    font_size=f"{self.CONNECTOR_FONT_SIZE}px",
                    font_family=self.FONT_FAMILY,
                    font_weight="bolder",
                    style="pointer-events: none;",
                )
            )
            drawing.add(group)

    def _render_lane_lines(self, drawing, a_connector_y_centers, b_connector_y_centers, total_width):
        lines = []
        line_a_x = self.CONNECTOR_WIDTH + self.LANE_X_GAP
        line_b_x = total_width - self.CONNECTOR_WIDTH - self.LANE_X_GAP
        for entry in self.entries:
            line_a_y = a_connector_y_centers[entry.a_connector] + self._y_offset(
                entry.a_position, self.a_positions, self.a_connector_height
            )
            line_b_y = b_connector_y_centers[entry.b_connector] + self._y_offset(
                entry.b_position, self.b_positions, self.b_connector_height
            )

            connected_a = self.show_status and entry.a_connector in self.a_labels
            connected_b = self.show_status and entry.b_connector in self.b_labels
            connected_both = connected_a and connected_b

            color = self.COLOR_LANE_CONNECTED if connected_both else self.COLOR_LANE_DISCONNECTED
            stroke_width = 2 if connected_both or not self.show_status else 1.5
            dasharray = None if connected_both or not self.show_status else "6,4"

            line = drawing.line(
                start=(line_a_x, line_a_y),
                end=(line_b_x, line_b_y),
                stroke=color,
                stroke_width=stroke_width,
            )
            if dasharray:
                line["stroke-dasharray"] = dasharray
            drawing.add(line)
            lines.append([line_a_x, line_a_y, line_b_x, line_b_y, color])

        return lines

    def _render_lane_labels(self, drawing, lines):
        for line, entry in zip(lines, self.entries):
            line_a_x, line_a_y, line_b_x, line_b_y, color = line

            # Offset the label along the line when multiple lanes share the same
            # (a_connector, b_connector) pair, so the labels don't sit on top of each other.
            group = self.lane_groups[(entry.a_connector, entry.b_connector)]
            idx = group.index(entry)
            offset_fraction = (idx + 1) / (len(group) + 1)

            label_mid_x = line_a_x + offset_fraction * (line_b_x - line_a_x)
            label_mid_y = line_a_y + offset_fraction * (line_b_y - line_a_y)

            label_estimated_width = self.LANE_LABEL_FONT_SIZE / 2 * (1 + len(entry.label))
            drawing.add(
                drawing.rect(
                    insert=(label_mid_x - label_estimated_width / 2, label_mid_y - self.LANE_LABEL_HEIGHT / 2),
                    size=(label_estimated_width, self.LANE_LABEL_HEIGHT),
                    rx=self.LANE_LABEL_HEIGHT / 2,
                    ry=self.LANE_LABEL_HEIGHT / 2,
                    fill=self.COLOR_BACKGROUND,
                    stroke=color,
                    stroke_width=1,
                )
            )
            drawing.add(
                drawing.text(
                    entry.label,
                    insert=(label_mid_x, label_mid_y + self.LANE_LABEL_FONT_SIZE / 3),
                    text_anchor="middle",
                    fill=self.COLOR_TEXT,
                    font_size=f"{self.LANE_LABEL_FONT_SIZE}px",
                    font_family=self.FONT_FAMILY,
                    font_weight="bolder",
                )
            )

    def render(self):
        total_width = self._total_width()
        total_height = self._total_height()

        drawing = svgwrite.Drawing(size=(f"{total_width}px", f"{total_height}px"), debug=False)
        drawing.viewbox(0, 0, total_width, total_height)

        a_connector_y_centers, b_connector_y_centers = self._connector_y_centers()

        # Draw A-side connectors
        self._render_connectors(
            drawing,
            side="A",
            positions=self.a_positions,
            connectors=self.a_connectors,
            x=0,
            connector_y_centers=a_connector_y_centers,
            connector_height=self.a_connector_height,
            labels=self.a_labels,
        )

        # Draw B-side connectors
        self._render_connectors(
            drawing,
            side="B",
            positions=self.b_positions,
            connectors=self.b_connectors,
            x=total_width - self.CONNECTOR_WIDTH,
            connector_y_centers=b_connector_y_centers,
            connector_height=self.b_connector_height,
            labels=self.b_labels,
        )

        # Draw lane lines then lane labels
        lines = self._render_lane_lines(drawing, a_connector_y_centers, b_connector_y_centers, total_width)
        self._render_lane_labels(drawing, lines)

        return mark_safe(drawing.tostring())  # noqa: S308
