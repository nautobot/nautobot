"""Server-side SVG generation for breakout cable lane mapping diagrams."""

from dataclasses import dataclass

from django.utils.html import mark_safe
import svgwrite

from nautobot.dcim.svg import constants
from nautobot.dcim.svg.utils import estimate_text_width
from nautobot.dcim.utils import validate_cable_breakout_mapping


@dataclass(frozen=True)
class MappingEntry:
    """A single row in a CableType mapping."""

    label: str
    a_connector: int
    a_position: int
    b_connector: int
    b_position: int


@dataclass(frozen=True)
class TerminationLabel:
    """A connector's termination label, rendered as a pair of (optionally clickable) segments.

    `term_text`/`term_url` describe the CableTermination's termination object (e.g. an interface);
    `parent_text`/`parent_url` describe its parent (e.g. a device). A URL of "" renders that
    segment as plain text rather than a link, and an empty `parent_text` omits the parent entirely.
    """

    term_text: str
    term_url: str = ""
    parent_text: str = ""
    parent_url: str = ""

    @property
    def display_text(self):
        """Combined 'Parent / Termination' text, used for width estimation."""
        if self.parent_text:
            return f"{self.parent_text} / {self.term_text}"
        return self.term_text


class BreakoutDiagramSVG:
    """
    Generate an SVG diagram showing the lane mapping of a cable breakout type.

    Usage:
        diagram = BreakoutDiagramSVG(mapping, a_termination_labels={1: "Device1 / Eth1"})
        svg_string = diagram.render()
    """

    CONNECTOR_WIDTH = 80
    SPACE_BETWEEN_CONNECTORS = 4
    MINIMUM_LINE_AREA_WIDTH = 80
    LANE_X_GAP = 1  # space between the connector and the lane
    LANE_Y_SPACING = 14  # minimum vertical spacing between lane endpoints within a connector
    LANE_LABEL_HEIGHT = constants.FONT_SIZE_SM + 4
    TERMINATION_LABEL_GAP = 8  # gap between connector edge and termination label

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
            a_termination_labels: dict {connector_num: TerminationLabel} for A-side connector labels
            b_termination_labels: dict {connector_num: TerminationLabel} for B-side connector labels
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
        longest_label = max((e.label for e in self.entries), key=len, default="")
        lane_label_x_spacing = estimate_text_width(longest_label + " ", constants.FONT_SIZE_SM)
        self.line_area_width = max(self.MINIMUM_LINE_AREA_WIDTH, (max_parallel_lanes + 1) * lane_label_x_spacing)

        # Reserve outer horizontal space for visible termination labels alongside each connector.
        self.a_label_area_width = self._termination_label_area_width(self.a_labels)
        self.b_label_area_width = self._termination_label_area_width(self.b_labels)

    def _termination_label_area_width(self, labels):
        """Pixel width to reserve for the visible termination labels on one side."""
        if not labels:
            return 0
        longest = max((label.display_text for label in labels.values()), key=len, default="")
        return self.TERMINATION_LABEL_GAP + estimate_text_width(longest, constants.FONT_SIZE_SM)

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
        """Total width of the SVG - two connectors plus the line area between them, plus
        outer label areas on each side for the visible termination labels."""
        return (
            self.a_label_area_width
            + self.CONNECTOR_WIDTH
            + self.line_area_width
            + self.CONNECTOR_WIDTH
            + self.b_label_area_width
        )

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
            bg = constants.COLOR_SUCCESS if connected else constants.COLOR_TERTIARY

            group = drawing.g()

            group.add(
                drawing.rect(
                    insert=(x, y_center - connector_height / 2),
                    size=(self.CONNECTOR_WIDTH, connector_height),
                    rx=constants.BORDER_RADIUS,
                    ry=constants.BORDER_RADIUS,
                    fill=bg,
                )
            )

            label = f"{side}{connector}"
            if positions > 1:
                label += f" ({positions})"
            group.add(
                drawing.text(
                    label,
                    insert=(x + self.CONNECTOR_WIDTH / 2, y_center + constants.FONT_SIZE / 3),
                    text_anchor="middle",
                    fill=constants.COLOR_BODY,
                    font_size=f"{constants.FONT_SIZE}px",
                    font_family=constants.FONT_FAMILY,
                    font_weight="bolder",
                    style="pointer-events: none;",
                )
            )
            drawing.add(group)

            # Visible termination label outside the connector box (left for A, right for B),
            # rendered as a pair of links to the termination and its parent.
            label = labels.get(connector)
            if label:
                if side == "A":
                    text_x = x - self.TERMINATION_LABEL_GAP
                    text_anchor = "end"
                else:
                    text_x = x + self.CONNECTOR_WIDTH + self.TERMINATION_LABEL_GAP
                    text_anchor = "start"
                text = drawing.text(
                    "",
                    insert=(text_x, y_center + constants.FONT_SIZE_SM / 3),
                    text_anchor=text_anchor,
                    fill=constants.COLOR_BODY,
                    font_size=f"{constants.FONT_SIZE_SM}px",
                    font_family=constants.FONT_FAMILY,
                )
                if label.parent_text:
                    self._add_label_segment(drawing, text, label.parent_text, label.parent_url)
                    text.add(drawing.tspan(" / ", fill=constants.COLOR_SECONDARY))
                self._add_label_segment(drawing, text, label.term_text, label.term_url)
                drawing.add(text)

    def _add_label_segment(self, drawing, text, segment_text, url):
        """Append a label segment to `text`, as a same-tab hyperlink when a URL is known."""
        if url:
            link = drawing.a(href=url, target="_self")
            link.add(drawing.tspan(segment_text, fill=constants.COLOR_LINK, style="cursor: pointer;"))
            text.add(link)
        else:
            text.add(drawing.tspan(segment_text))

    def _render_lane_lines(self, drawing, a_connector_y_centers, b_connector_y_centers, total_width):
        lines = []
        line_a_x = self.a_label_area_width + self.CONNECTOR_WIDTH + self.LANE_X_GAP
        line_b_x = total_width - self.b_label_area_width - self.CONNECTOR_WIDTH - self.LANE_X_GAP
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

            color = constants.COLOR_SUCCESS if connected_both else constants.COLOR_TERTIARY
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

            label_estimated_width = constants.FONT_SIZE_SM / 2 * (1 + len(entry.label))
            drawing.add(
                drawing.rect(
                    insert=(label_mid_x - label_estimated_width / 2, label_mid_y - self.LANE_LABEL_HEIGHT / 2),
                    size=(label_estimated_width, self.LANE_LABEL_HEIGHT),
                    rx=self.LANE_LABEL_HEIGHT / 2,
                    ry=self.LANE_LABEL_HEIGHT / 2,
                    fill=constants.COLOR_BODY_BG,
                    stroke=color,
                    stroke_width=1,
                )
            )
            drawing.add(
                drawing.text(
                    entry.label,
                    insert=(label_mid_x, label_mid_y + constants.FONT_SIZE_SM / 3),
                    text_anchor="middle",
                    fill=constants.COLOR_BODY,
                    font_size=f"{constants.FONT_SIZE_SM}px",
                    font_family=constants.FONT_FAMILY,
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
            x=self.a_label_area_width,
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
            x=total_width - self.CONNECTOR_WIDTH - self.b_label_area_width,
            connector_y_centers=b_connector_y_centers,
            connector_height=self.b_connector_height,
            labels=self.b_labels,
        )

        # Draw lane lines then lane labels
        lines = self._render_lane_lines(drawing, a_connector_y_centers, b_connector_y_centers, total_width)
        self._render_lane_labels(drawing, lines)

        return mark_safe(drawing.tostring())  # noqa: S308
