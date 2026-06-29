"""Server-side SVG generation for cable path trace diagrams.

The renderer ingests a `PathEndpoint` origin and emits an SVG depicting the full trace from that
origin to its destination(s), including breakout fan-outs, pass-through ports, multi-hop paths,
and unconnected breakout lanes. See `CableTraceSVG` for the public entry point.
"""

from django.contrib.contenttypes.models import ContentType
from django.urls import NoReverseMatch, reverse
from django.utils.html import mark_safe
import svgwrite

from nautobot.core.templatetags.helpers import bettertitle, fgcolor, meters_to_feet
from nautobot.dcim.svg import constants
from nautobot.dcim.svg.utils import estimate_text_width, fit_text


class CableTraceSVG:
    """
    Generate an SVG diagram of a cable trace path.

    Renders a top-to-bottom flow showing devices, terminations, cables, pass-throughs, and breakout
    fan-outs as connected SVG elements.

    The rendering is split into two phases:
      Phase 1 (`build_matrix`): Collect trace data into a row/column matrix with spatial metadata
          (e.g. colspan for grouped devices spanning fan-out columns).
      Phase 2 (`render`): Walk the matrix and draw each cell at its computed pixel position.

    Usage:
        diagram = CableTraceSVG(origin_instance, base_url="")
        svg_string = diagram.render()
    """

    # Layout: spacing and offsets
    GAP_Y = 5
    LABEL_OFFSET_X = 10
    # Baseline-to-baseline spacing for stacked detail lines; tied to the (larger) base font size so
    # consecutive lines aren't crowded.
    TEXT_LINE_SPACING = constants.FONT_SIZE
    # Downward shift from a vertical center to a text baseline (≈ half the cap height) so a line of
    # text appears vertically centered at its target y.
    TEXT_VERTICAL_OFFSET = 5
    TRACE_END_PADDING = 5
    # Minimum reserve for cable labels/badges hanging off the rightmost column. Actual reserve
    # is sized to the longest cable label found in the trace; this is the floor used when no
    # cables (or only very short ones) are present.
    LABEL_RIGHT_RESERVE_MIN = 140

    # Layout: termination sub-box. TERM_W is wide enough to fit most port / circuit termination
    # names without truncation; values that still overflow get clipped to an ellipsis with the
    # full string available on hover via a `<title>` element.
    TERM_W = 230
    # Horizontal padding inside the termination box; the usable text area is `TERM_W - 2 * TERM_TEXT_PAD`.
    TERM_TEXT_PAD = 8
    # Vertical padding above and below the termination box's stacked text block.
    TERM_TEXT_PAD_Y = 6
    # TERM_H holds two stacked lines: the bold termination name plus a "<verbose name> (<type>)"
    # detail line, with vertical padding.
    TERM_H = constants.FONT_SIZE + TEXT_LINE_SPACING + 2 * TERM_TEXT_PAD_Y

    # Layout: node (device/circuit/panel box)
    NODE_W = TERM_W + 30
    # Vertical padding above and below the stacked text block within a node box.
    NODE_TEXT_PAD_Y = 8
    # NODE_TEXT_AREA_H is the free vertical span reserved for a node's stacked text block: the bold
    # name (FONT_SIZE) plus up to three detail lines (TEXT_LINE_SPACING each — e.g. a device's
    # manufacturer/type, location, and rack), with padding so the text clears the box edges and any
    # termination sub-boxes. The height is fixed (sized for the tallest node) so rows stay aligned
    # when they mix node types; shorter nodes just center their text with extra padding. NODE_H adds
    # the half-termination overlap a single (top- or bottom-) termination box contributes beyond it.
    NODE_TEXT_AREA_H = constants.FONT_SIZE + 3 * TEXT_LINE_SPACING + 2 * NODE_TEXT_PAD_Y
    NODE_H = NODE_TEXT_AREA_H + TERM_H // 2

    # Layout: cable segment
    CABLE_H = 140
    # A breakout cable's trunk is drawn shorter than a normal cable bar so the diagonal fan-out
    # below it gets more vertical room to spread (steeper, less crowded branches).
    BREAKOUT_TRUNK_H = 90
    CABLE_BAR_W = 10
    CABLE_BORDER_W = 1
    # Dash pattern for a disconnected/planned cable (and its fork lines): the cable color rides on
    # top of a wider, longer border-color dash so each dash keeps a visible border "rung" against
    # the page background. Same period; the cable dash is offset so its rungs straddle it evenly.
    CABLE_DASH_SEGMENT_LENGTH = 20
    CABLE_DASH_GAP_LENGTH = 10
    CABLE_DASH_BORDER = f"{CABLE_DASH_SEGMENT_LENGTH},{CABLE_DASH_GAP_LENGTH}"
    CABLE_DASH = f"{CABLE_DASH_SEGMENT_LENGTH - 2 * CABLE_BORDER_W},{CABLE_DASH_GAP_LENGTH + 2 * CABLE_BORDER_W}"
    CABLE_DASH_OFFSET = -CABLE_BORDER_W

    # Layout: overall dimensions
    # Column pitch must be >= NODE_W so adjacent device boxes in different columns don't overlap;
    # the extra ~20 px gives a visible gap between distinct devices.
    COL_WIDTH = NODE_W + 20
    EMPTY_HEIGHT = 70

    def __init__(self, origin, base_url="", cable_path=None):
        self.origin = origin
        self.base_url = base_url.rstrip("/") if base_url else ""
        # A breakout child (sub)interface origin is virtual and has no `CablePath` of its own; its
        # physical path is a single lane of its parent trunk's breakout cable. Record the parent
        # trunk so the renderer traces only that lane and draws the child atop the trunk.
        get_breakout_lane = getattr(origin, "get_breakout_lane", None)
        self.trunk_origin = (
            origin.parent_interface if get_breakout_lane is not None and get_breakout_lane() is not None else None
        )
        # Render the explicitly-selected CablePath when given (e.g. a `?cablepath_id=` choice);
        # otherwise fall back to the parent trunk's lane (subinterface origin) or the origin's path.
        if cable_path is None:
            if self.trunk_origin is not None:
                cable_path = origin.get_breakout_lane_cable_path()
            elif hasattr(origin, "cable_paths"):
                cable_path = origin.cable_paths.first()
        self.cable_path = cable_path
        self.traced_path = cable_path.trace() if cable_path is not None else []
        self.fanout_paths = self._detect_fanout()

    # ──────────────────────────────────────────────
    # Data collection helpers
    # ──────────────────────────────────────────────

    def _detect_fanout(self):
        """Detect whether this trace fans out through a breakout cable.

        For a breakout origin there is one `CablePath` per `peer_connector` (the connector on
        the cable's far side that the lane bundle emerges through). Unconnected legs — i.e.,
        connectors named in `cable.cable_type.mapping` but with no `CableToCableTermination`
        row — surface as `{"termination": None, ...}` entries so the matrix can render them
        as explicit "Unconnected" placeholders.
        """
        if not self.traced_path:
            return []

        _, cable, far_end = self.traced_path[0]

        # A trace that isn't a breakout fan-out is modeled as a single linear leg (no fork), so
        # breakout and non-breakout traces flow through the same build_matrix → render pipeline.
        linear_fanout = [
            {
                "termination": far_end,
                "connector_label": "",
                "trace": self._expand_trace_segments(self.traced_path[1:]),
            }
        ]

        # A breakout child (sub)interface origin follows just one lane of its parent trunk's breakout
        # cable, so render a single linear leg rather than fanning out across every lane. (The origin
        # also isn't a termination on the cable — the trunk is — so the fan-out detection below, which
        # locates the origin's own cable row, doesn't apply.)
        if self.trunk_origin is not None:
            return linear_fanout

        if not cable or not cable.cable_type_id:
            return linear_fanout

        from nautobot.dcim.models import CablePath, CableToCableTermination

        # Locate the origin's CableToCableTermination row to learn which side we're on. This row is
        # the very linkage that placed the cable in the trace, so under consistent data it always
        # exists; a miss means inconsistent data, so fail loudly rather than render a misleading trace.
        origin_row = self._cable_lane_info(cable, self.origin)
        if origin_row is None:
            raise RuntimeError(
                f"No CableToCableTermination row links trace origin {self.origin!r} to its first "
                f"cable {cable!r}; cannot determine the breakout side."
            )
        origin_ct = ContentType.objects.get_for_model(self.origin)

        origin_side = origin_row.cable_end  # "A" or "B"
        opposite_side = "B" if origin_side == "A" else "A"
        origin_side_key = "a_connector" if origin_side == "A" else "b_connector"
        origin_position_key = "a_position" if origin_side == "A" else "b_position"
        far_side_key = "b_connector" if origin_side == "A" else "a_connector"

        # All mapping entries that originate from the origin's connector, deduplicated by the
        # far-side connector so multi-position trunks contribute one leg per peer connector. Also
        # track which origin-side positions each far connector carries, so a trunk origin's numbered
        # child interfaces can be annotated onto their corresponding legs.
        seen_far_connectors = []
        positions_by_far_connector = {}
        for entry in cable.cable_type.mapping or []:
            if entry.get(origin_side_key) != origin_row.connector:
                continue
            far_connector = entry.get(far_side_key)
            if far_connector is None:
                continue
            positions_by_far_connector.setdefault(far_connector, []).append(entry.get(origin_position_key))
            if far_connector not in seen_far_connectors:
                seen_far_connectors.append(far_connector)
        seen_far_connectors.sort()

        if len(seen_far_connectors) <= 1:
            return linear_fanout

        # Trunk-side child interfaces keyed by their breakout position, used to annotate each leg
        # with the numbered child interface it maps to (empty for non-Interface origins).
        child_interface_by_position = {}
        if hasattr(self.origin, "child_interfaces"):
            for child in self.origin.child_interfaces.all():
                if child.breakout_position is not None:
                    child_interface_by_position[child.breakout_position] = child

        # Far-side terminations indexed by connector for quick lookup; CablePaths indexed by
        # peer_connector (which corresponds to the far-side connector for the breakout leg).
        far_rows = {
            row.connector: row for row in CableToCableTermination.objects.filter(cable=cable, cable_end=opposite_side)
        }
        path_by_peer_connector = {
            cable_path.peer_connector: cable_path
            for cable_path in CablePath.objects.filter(origin_type=origin_ct, origin_id=self.origin.pk)
        }

        fanout_legs = []
        for far_connector in seen_far_connectors:
            far_row = far_rows.get(far_connector)
            termination = far_row.termination if far_row is not None else None

            leg_trace = []
            cable_path = path_by_peer_connector.get(far_connector)
            if cable_path is not None:
                # Reconstruct the trace from the CablePath, stripping the first hop (the breakout
                # cable itself) since the renderer's header already shows it.
                full_trace = cable_path.trace()
                if len(full_trace) > 1:
                    leg_trace = self._expand_trace_segments(full_trace[1:])

            # Annotate the leg with the trunk's numbered child interface(s) mapped to this connector.
            child_interfaces = [
                child_interface_by_position[position]
                for position in positions_by_far_connector.get(far_connector, [])
                if position in child_interface_by_position
            ]
            connector_label = f"{opposite_side}{far_connector}"
            if child_interfaces:
                connector_label += " (" + ", ".join(str(child) for child in child_interfaces) + ")"

            fanout_legs.append(
                {
                    "termination": termination,
                    "connector_label": connector_label,
                    "trace": leg_trace,
                }
            )

        return fanout_legs

    def _url(self, obj):
        """Build an absolute URL for an object, prefixed by `base_url` when set."""
        try:
            return self.base_url + obj.get_absolute_url()
        except (AttributeError, TypeError):
            return "#"

    def _get_parent_info(self, termination):
        """Extract a termination's grouping key and the text block to render for its parent node.

        Returns `(key, lines)`. `lines` is a list of `(text, url)` tuples drawn stacked inside the
        node box: line 0 is the bold parent name and any further lines are detail. `url` is `None`
        for plain text or an absolute URL to render the line as a link. `key` groups same-device
        nodes via the parent's globally-unique UUID; `termination.parent` handles device, module,
        circuit, and power_panel.

        `termination` must be non-None: a null-termination cell (an unconnected breakout lane) is
        rendered as an "Unconnected" placeholder and grouping skips it, so it never reaches here.
        """
        parent = termination.parent
        if parent is None:  # case of a ModularComponent belonging to a module that isn't installed in a device?
            return (None, [(str(termination), "#")])

        parent_key = str(parent.pk)
        # Line 0: the linked parent name. Detail lines are appended below per parent type.
        lines = [(str(parent), self._url(parent))]

        if hasattr(parent, "device_type"):
            # Device — manufacturer + device type, then location and rack each on their own line
            # (split onto separate lines so each centers cleanly). `location` is a required FK;
            # `rack` is optional.
            lines.append((f"{parent.device_type.manufacturer} {parent.device_type}", None))
            lines.append((str(parent.location), self._url(parent.location)))
            if parent.rack:
                lines.append((str(parent.rack), self._url(parent.rack)))
        elif hasattr(parent, "provider"):
            # Circuit — name is the cid, then "Circuit" and the linked provider.
            lines.append(("Circuit", None))
            lines.append((str(parent.provider), self._url(parent.provider)))
        else:
            # PowerPanel / Module / other — verbose name, then linked location if any.
            lines.append((parent._meta.verbose_name.title(), None))
            if parent.location is not None:
                lines.append((str(parent.location), self._url(parent.location)))

        return (parent_key, lines)

    def _cell_group_key(self, cell):
        """Return the grouping key for a `node`/`passthrough_node`/`cable` cell, else None.

        Adjacent cells of the same type sharing this key collapse across the columns they occupy.
        `node`/`passthrough_node` group by parent device (the leg terminations sit side by side in
        one box); a pass-through node uses its arriving termination's parent (its departing port is
        on the same device). A `cable` groups by identity, so a single physical cable shared by
        several legs — a breakout that fans into a common trunk and back out — renders once, centered.
        """
        if cell["type"] == "node" and cell.get("termination") is not None:
            return self._get_parent_info(cell["termination"])[0]
        if cell["type"] == "passthrough_node" and cell.get("arriving") is not None:
            return self._get_parent_info(cell["arriving"])[0]
        if cell["type"] == "cable" and cell.get("cable") is not None:
            return cell["cable"].pk
        return None

    def _max_cable_label_width(self, header_cable, column_entries):
        """Estimate the widest element drawn to the right of any column center.

        Considers everything a cable stacks beside its bar — the bold name, the muted detail lines,
        and the status badge pill — so the canvas reserves enough width to avoid clipping any of them.
        """
        widths = []

        def add(cable, near_end, far_end):
            # The bold name renders at FONT_SIZE; the detail lines below it at FONT_SIZE_SM.
            widths.append(estimate_text_width(str(cable), constants.FONT_SIZE))
            for detail in self._cable_detail_lines(cable, near_end, far_end):
                widths.append(estimate_text_width(detail, constants.FONT_SIZE_SM))
            # Status badge pill, mirroring `_draw_status_badge`: text width plus horizontal padding
            # of FONT_SIZE_SM.
            widths.append(estimate_text_width(cable.status.name, constants.FONT_SIZE_SM) + constants.FONT_SIZE_SM)

        if header_cable is not None:
            # A fan-out trunk forks to multiple far ends and draws no lane detail; a linear first hop
            # draws its lane detail from the single far end, mirroring how `render` draws the header.
            if len(self.fanout_paths) > 1:
                add(header_cable, None, None)
            else:
                near_end, _, far_end = self.traced_path[0]
                add(header_cable, near_end, far_end)
        for entries in column_entries:
            for entry in entries:
                if entry.get("type") == "cable" and entry.get("cable") is not None:
                    add(entry["cable"], entry.get("near"), entry.get("far"))
        return max(widths, default=0)

    def _cable_lane_info(self, cable, termination):
        """Return the `CableToCableTermination` row matching `termination` on `cable`, or None.

        `cable` and `termination` must be non-None; callers resolve them first.
        """
        termination_ct = ContentType.objects.get_for_model(termination)
        for row in cable.terminations.all():
            if (
                row.termination_id == termination.pk
                and row.termination_type
                and (row.termination_type.app_label, row.termination_type.model)
                == (termination_ct.app_label, termination_ct.model)
            ):
                return row
        return None

    def _cable_detail_lines(self, cable, near_end=None, far_end=None):
        """Muted detail lines drawn beneath a cable's name: type, cable type, and breakout lane info.

        The breakout lane info is only included for cables with a `cable_type` when both endpoints
        are known (i.e. when called from a rendered segment, not for the header trunk).
        """
        lines = []
        if cable.type:
            lines.append(cable.get_type_display())
        if cable.cable_type_id:
            lines.append(str(cable.cable_type))
        if cable.cable_type_id and near_end and far_end:
            near_row = self._cable_lane_info(cable, near_end)
            far_row = self._cable_lane_info(cable, far_end)
            if near_row is not None and near_row.connector is not None:
                breakout_text = f"Breakout: {near_row.cable_end}{near_row.connector}"
                if far_row is not None and far_row.connector is not None:
                    breakout_text += f" → {far_row.cable_end}{far_row.connector}"
                lines.append(breakout_text)
        return lines

    def _terminal_subinterface(self, entries):
        """Child (sub)interface of a breakout trunk this leg ends on, mapped back to the origin.

        When a leg's terminal node is a breakout-trunk `Interface` whose lane resolves back to the
        trace origin — possibly several hops away through patch-panel front/rear ports — return the
        trunk's child interface for that lane so it can be drawn as a port on the terminal device.
        Returns None when the leg doesn't end on such a trunk or no child interface claims the
        matching lane position. See `Interface.get_breakout_trunk_child_interface_for_endpoint`.
        """
        resolver = getattr(self.origin, "get_breakout_trunk_child_interface_for_endpoint", None)
        if resolver is None or not entries:
            return None
        terminal = entries[-1]
        if terminal["type"] != "node" or terminal.get("termination") is None:
            return None
        return resolver(terminal["termination"])

    # ──────────────────────────────────────────────
    # Phase 1: Build the matrix
    # ──────────────────────────────────────────────

    def build_matrix(self):
        """Build a row/column matrix from fan-out legs with spatial metadata.

        Returns:
            {
                "header": {
                    "origin": termination,
                    "cable": cable_obj,
                    "cable_color": str,
                    "connector_labels": [str, ...],
                },
                "columns": int,
                "col_centers": [float, ...],    # X center for each column
                "total_width": float,
                "rows": [
                    [cell, cell, ...],  # one cell per column
                    ...
                ],
            }

        Row cell types:
            {"type": "node", "col": int, "colspan": 1, "termination": obj}
            {"type": "grouped_node", "col": int, "colspan": int,
             "terminations": [obj, ...], "parent_key": str}
            {"type": "passthrough_node", "col": int, "arriving": obj, "departing": obj}
            {"type": "grouped_passthrough_node", "col": int, "colspan": int,
             "arriving": [obj, ...], "departing": [obj, ...], "parent_key": str}
            {"type": "cable", "col": int, "cable": obj, "near": obj, "far": obj}
            {"type": "grouped_cable", "col": int, "colspan": int, "cable": obj, "near": obj, "far": obj}
            {"type": "spanned", "col": int}  — covered by a grouped cell in a prior column
            {"type": "empty", "col": int}  — column padding where a shorter leg has ended

        A front↔rear `passthrough` is an intermediate raw entry only; Step 1 always folds the
        preceding node and the passthrough into a single `passthrough_node`, so a standalone
        `passthrough` never reaches a row.
        """
        column_count = len(self.fanout_paths)

        near_end, cable, far_end = self.traced_path[0] if self.traced_path else (None, None, None)
        cable_color = f"#{cable.color}" if cable and cable.color else constants.COLOR_SECONDARY

        header = {
            "origin": near_end,
            "cable": cable,
            "cable_color": cable_color,
            "far_end": far_end,
            "connector_labels": [leg["connector_label"] for leg in self.fanout_paths],
        }

        # Step 1: Build raw per-column entry lists, merging node+passthrough into passthrough_node.
        column_entries = []
        for leg in self.fanout_paths:
            raw_entries = []
            leg_termination = leg["termination"]
            trace_segments = leg.get("trace", [])

            raw_entries.append({"type": "node", "termination": leg_termination})

            # Implicit pass-through between leg termination and first trace near_end
            # (e.g., FrontPort → RearPort within the same device).
            if trace_segments and leg_termination:
                first_near = trace_segments[0][0]
                if first_near and first_near.pk != leg_termination.pk:
                    raw_entries.append({"type": "passthrough", "near": leg_termination, "far": first_near})

            for segment_near, segment_cable, segment_far in trace_segments:
                if segment_cable is None and segment_far is not None:
                    raw_entries.append({"type": "passthrough", "near": segment_near, "far": segment_far})
                else:
                    if segment_cable:
                        raw_entries.append(
                            {"type": "cable", "cable": segment_cable, "near": segment_near, "far": segment_far}
                        )
                    if segment_far:
                        raw_entries.append({"type": "node", "termination": segment_far})

            # Merge node-followed-by-passthrough into passthrough_node.
            entries = []
            entry_index = 0
            while entry_index < len(raw_entries):
                entry = raw_entries[entry_index]
                if (
                    entry["type"] == "node"
                    and entry_index + 1 < len(raw_entries)
                    and raw_entries[entry_index + 1]["type"] == "passthrough"
                ):
                    passthrough = raw_entries[entry_index + 1]
                    entries.append(
                        {
                            "type": "passthrough_node",
                            "arriving": entry["termination"],
                            "departing": passthrough["far"],
                        }
                    )
                    entry_index += 2
                else:
                    entries.append(entry)
                    entry_index += 1

            # When this leg terminates on a breakout-trunk interface, fold the trunk's child
            # (sub)interface for the lane leading back to the origin into the terminal device node:
            # the trunk port and the child interface render as the arriving/departing port pair of a
            # passthrough node, so the subinterface box sits on the device below its trunk port.
            subinterface = self._terminal_subinterface(entries)
            if subinterface is not None:
                trunk_termination = entries[-1]["termination"]
                entries[-1] = {
                    "type": "passthrough_node",
                    "arriving": trunk_termination,
                    "departing": subinterface,
                }

            column_entries.append(entries)

        # Layout: size the canvas to fit the trace and center the column band so the trunk (band
        # center) sits at the SVG's horizontal center. The widest overhang from a column center is
        # reserved symmetrically on both sides: cable labels hang to the right of the rightmost
        # column, the origin/trunk node and the centered trace-end footer extend to the left of the
        # trunk, so a symmetric reserve keeps the labels, the node, and the footer all unclipped.
        col_width = self.COL_WIDTH
        node_overhang = self.NODE_W / 2
        label_overhang = (
            self.CABLE_BAR_W / 2
            + self.LABEL_OFFSET_X
            + self._max_cable_label_width(header["cable"], column_entries)
            + self.GAP_Y * 2  # safety margin: width estimation is a fraction-of-em approximation
        )
        side_overhang = max(node_overhang, label_overhang, self.LABEL_RIGHT_RESERVE_MIN)
        band_width = (column_count - 1) * col_width
        # The footer is centered on the trunk, so the canvas must hold its full width as well.
        total_width = max(band_width + 2 * side_overhang, self._trace_end_width(), self.COL_WIDTH)
        # Center the band: the trunk center then coincides with the SVG center (total_width / 2).
        first_col_x = (total_width - band_width) / 2
        col_centers = [first_col_x + col_idx * col_width for col_idx in range(column_count)]

        # Step 2: Normalize into rows (pad with empty cells).
        max_depth = max((len(entries) for entries in column_entries), default=0)
        raw_rows = []
        for depth in range(max_depth):
            row = []
            for col_idx in range(column_count):
                if depth < len(column_entries[col_idx]):
                    cell = dict(column_entries[col_idx][depth])
                    cell["col"] = col_idx
                else:
                    cell = {"type": "empty", "col": col_idx}
                row.append(cell)
            raw_rows.append(row)

        # Step 3: Collapse a run of same-type cells that share a grouping key into one cell spanning
        # their columns: node/pass-through nodes into one device box, a shared cable into one bar.
        rows = []
        for raw_row in raw_rows:
            row = list(raw_row)

            col_idx = 0
            while col_idx < column_count:
                cell = row[col_idx]
                group_key = self._cell_group_key(cell)
                if group_key is None:
                    col_idx += 1
                    continue

                # Span adjacent cells of the same type sharing the grouping key.
                span_end = col_idx + 1
                while (
                    span_end < column_count
                    and row[span_end]["type"] == cell["type"]
                    and self._cell_group_key(row[span_end]) == group_key
                ):
                    span_end += 1

                colspan = span_end - col_idx
                if colspan > 1:
                    spanned = range(col_idx, span_end)
                    if cell["type"] == "node":
                        row[col_idx] = {
                            "type": "grouped_node",
                            "col": col_idx,
                            "colspan": colspan,
                            "terminations": [row[c]["termination"] for c in spanned],
                            "parent_key": group_key,
                        }
                    elif cell["type"] == "passthrough_node":
                        row[col_idx] = {
                            "type": "grouped_passthrough_node",
                            "col": col_idx,
                            "colspan": colspan,
                            "arriving": [row[c]["arriving"] for c in spanned],
                            "departing": [row[c]["departing"] for c in spanned],
                            "parent_key": group_key,
                        }
                    else:  # cable shared across legs (a fan-in/fan-out trunk)
                        row[col_idx] = {
                            "type": "grouped_cable",
                            "col": col_idx,
                            "colspan": colspan,
                            "cable": cell["cable"],
                            "near": cell.get("near"),
                            "far": cell.get("far"),
                        }
                    for spanned_col in range(col_idx + 1, span_end):
                        row[spanned_col] = {"type": "spanned", "col": spanned_col}
                    col_idx = span_end
                else:
                    cell["colspan"] = 1
                    col_idx += 1

            rows.append(row)

        return {
            "header": header,
            "columns": column_count,
            "col_centers": col_centers,
            "total_width": total_width,
            "rows": rows,
        }

    # ──────────────────────────────────────────────
    # Phase 2: Render the matrix to SVG
    # ──────────────────────────────────────────────

    def render(self):
        """Render the complete trace (breakout fan-out or single-leg linear) as an SVG string."""
        if not self.traced_path:
            return self._render_empty()

        matrix = self.build_matrix()
        header = matrix["header"]
        col_centers = matrix["col_centers"]
        total_width = matrix["total_width"]

        dwg = svgwrite.Drawing(size=(f"{total_width}px", f"{self.EMPTY_HEIGHT}px"), debug=False)

        trunk_cx = (col_centers[0] + col_centers[-1]) / 2 if col_centers else total_width / 2
        y = self.GAP_Y

        # Header: Origin node
        if header["origin"]:
            if self.trunk_origin is not None:
                # Subinterface origin: draw the originating child interface atop its parent trunk
                # port on the shared device — the mirror of a trace *ending* on a trunk, which folds
                # the child below the trunk — then trace that one lane below.
                y = self._draw_passthrough_node(dwg, trunk_cx, y, self.origin, header["origin"])
            else:
                y = self._draw_node(dwg, trunk_cx, y, header["origin"], term_position="bottom")
            y += self.GAP_Y

        # Header: Breakout cable trunk + fork
        cable = header["cable"]
        if cable:
            cable_color = header["cable_color"]
            is_connected = cable.status.name == "Connected"
            is_breakout_fanout = bool(cable.cable_type_id) and len(col_centers) > 1

            if is_breakout_fanout:
                # Breakout cable: a short vertical trunk that fans out, via one straight diagonal per
                # connector, to the far columns. The trunk segment and every branch are drawn as one
                # two-pass network (all borders first, then all colors) so the trunk's border never
                # paints over a branch and the whole fan reads as a single connected shape.
                fan_origin = (trunk_cx, y + self.BREAKOUT_TRUNK_H)
                fan_end_y = y + self.CABLE_H + self.GAP_Y + self.CABLE_DASH_SEGMENT_LENGTH
                segments = [((trunk_cx, y), fan_origin)]
                segments += [(fan_origin, (cx, fan_end_y)) for cx in col_centers]
                self._draw_cable_fan(dwg, segments, cable_color, is_connected)
                self._draw_cable_label(dwg, trunk_cx, y, self.BREAKOUT_TRUNK_H, cable)

                # Label each branch's landing column, just below the foot of its line.
                connector_labels = header["connector_labels"]
                y = fan_end_y + self.GAP_Y
                if any(connector_labels):
                    label_baseline = y + constants.FONT_SIZE_SM
                    for col_idx, cx in enumerate(col_centers):
                        label = connector_labels[col_idx]
                        if label:
                            dwg.add(
                                dwg.text(
                                    label,
                                    insert=(cx, label_baseline),
                                    text_anchor="middle",
                                    fill=constants.COLOR_SECONDARY,
                                    font_size=f"{constants.FONT_SIZE_SM}px",
                                    font_family=constants.FONT_FAMILY,
                                    font_weight="bold",
                                )
                            )
                    y = label_baseline + self.GAP_Y
            else:
                # Linear or single-leg: full-height cable bar, no fork. Pass the first hop's
                # endpoints so a breakout cable here shows its lane detail, as a mid-path segment would.
                y = self._draw_cable(dwg, trunk_cx, y, cable, header["origin"], header["far_end"])
                y += self.GAP_Y

            row_positions = []
            for row in matrix["rows"]:
                row_h = self._compute_row_height(row)
                row_positions.append((y, row, row_h))
                y += row_h + self.GAP_Y

            self._render_rows(dwg, row_positions, col_centers)

        # Footer: split next-hops, or completion summary (segment count + total length).
        y = self._draw_trace_end(dwg, trunk_cx, y)

        dwg["height"] = f"{y + self.GAP_Y}px"
        dwg["width"] = f"{total_width}px"
        dwg.viewbox(0, 0, total_width, y + self.GAP_Y)
        return mark_safe(dwg.tostring())  # noqa: S308

    def _expand_trace_segments(self, segments):
        """Expand `trace()` three-tuples into entries with explicit pass-through hops.

        When `trace()` returns consecutive segments where segment N's far_end differs from
        segment N+1's near_end, that's an implicit pass-through (e.g., FrontPort → RearPort
        within the same device). This inserts explicit `(from, None, to)` passthrough entries
        for those gaps.
        """
        entries = []
        for segment_index, (near_end, cable, far_end) in enumerate(segments):
            if segment_index > 0:
                prev_far = segments[segment_index - 1][2]
                if prev_far and near_end and near_end.pk != prev_far.pk:
                    entries.append((prev_far, None, near_end))

            if cable:
                entries.append((near_end, cable, far_end))

        return entries

    def _compute_row_height(self, row):
        row_h = 0
        for cell in row:
            if cell["type"] == "node":
                row_h = max(row_h, self.TERM_H / 2 + self.NODE_H)
            elif cell["type"] == "grouped_node":
                row_h = max(row_h, self.TERM_H / 2 + self.NODE_H)
            elif cell["type"] in ("passthrough_node", "grouped_passthrough_node"):
                # Arriving termination + free text area + departing termination.
                row_h = max(row_h, 2 * self.TERM_H + self.NODE_TEXT_AREA_H)
            elif cell["type"] in ("cable", "grouped_cable"):
                row_h = max(row_h, self.CABLE_H)
        return row_h

    def _render_rows(self, dwg, row_positions, col_centers):
        """Draw every cell of every row: cable bars, device boxes, and termination boxes.

        Rows are separated vertically by GAP_Y and the cells within a row occupy distinct columns,
        so no two cells ever share pixels — paint order doesn't affect the result.
        """
        for y, row, _row_h in row_positions:
            for cell in row:
                cx = col_centers[cell["col"]]

                if cell["type"] == "cable":
                    self._draw_cable(dwg, cx, y, cell["cable"], cell.get("near"), cell.get("far"))

                elif cell["type"] == "grouped_cable":
                    # A shared trunk spanning several legs — drawn once, centered over the span.
                    self._draw_cable(
                        dwg, self._group_cx(cell, col_centers), y, cell["cable"], cell.get("near"), cell.get("far")
                    )

                elif cell["type"] == "node":
                    if cell["termination"] is None:
                        dwg.add(
                            dwg.text(
                                "Unconnected",
                                insert=(cx, y + self.NODE_H / 2),
                                text_anchor="middle",
                                fill=constants.COLOR_WARNING,
                                font_size=f"{constants.FONT_SIZE_SM}px",
                                font_family=constants.FONT_FAMILY,
                                font_weight="bold",
                            )
                        )
                    else:
                        self._draw_node(dwg, cx, y, cell["termination"], term_position="top")

                elif cell["type"] == "grouped_node":
                    self._draw_grouped_node_cell(dwg, y, cell, col_centers)

                elif cell["type"] == "passthrough_node":
                    self._draw_passthrough_node(dwg, cx, y, cell["arriving"], cell["departing"])

                elif cell["type"] == "grouped_passthrough_node":
                    self._draw_grouped_passthrough_node(dwg, y, cell, col_centers)

    # ──────────────────────────────────────────────
    # Cell drawing primitives
    # ──────────────────────────────────────────────

    def _add_text(self, dwg, text, x, baseline_y, anchor, font_size, font_weight, url=None, title=None, fill=None):
        """Add one `<text>` element (wrapped in a link when `url` is set) and an optional tooltip.

        `fill` overrides the default color (link blue when `url` is set, else muted).
        """
        if fill is None:
            fill = constants.COLOR_LINK if url else constants.COLOR_SECONDARY
        element = dwg.text(
            text,
            insert=(x, baseline_y),
            text_anchor=anchor,
            fill=fill,
            font_size=f"{font_size}px",
            font_family=constants.FONT_FAMILY,
            font_weight=font_weight,
        )
        if title:
            element.set_desc(title=title)
        if url:
            link = dwg.a(href=url, target="_top")
            link.add(element)
            dwg.add(link)
        else:
            dwg.add(element)

    def _draw_text_line(self, dwg, cx, baseline_y, text, url, font_size, max_width, font_weight="normal"):
        """Draw a single line of text centered at `cx`, as a blue link when `url` is set.

        Text wider than `max_width` is truncated to an ellipsis with the full text preserved as a
        `<title>` tooltip.
        """
        if not text:
            return
        fitted = fit_text(text, max_width, font_size)
        title = text if fitted != text else None
        self._add_text(dwg, fitted, cx, baseline_y, "middle", font_size, font_weight, url=url, title=title)

    def _draw_text_block(self, dwg, text_cx, area_top, area_h, max_width, lines):
        """Draw `lines` stacked and vertically centered within the span [area_top, area_top+area_h].

        Each line is a `(text, url)` tuple. Line 0 is the bold name (FONT_SIZE); the remaining lines
        are smaller detail text (FONT_SIZE_SM). Centering the block within `area_h` yields the
        padding above and below.
        """
        text_center_y = area_top + area_h / 2
        line_count = len(lines)
        for line_index, (text, url) in enumerate(lines):
            baseline_y = (
                text_center_y + (line_index - (line_count - 1) / 2) * self.TEXT_LINE_SPACING + self.TEXT_VERTICAL_OFFSET
            )
            if line_index == 0:
                self._draw_text_line(
                    dwg, text_cx, baseline_y, text, url, constants.FONT_SIZE, max_width, font_weight="bold"
                )
            else:
                self._draw_text_line(dwg, text_cx, baseline_y, text, url, constants.FONT_SIZE_SM, max_width)

    def _draw_parent_box(self, dwg, box_x, box_y, box_w, box_h, text_cx, text_area_top, text_area_h, termination):
        """Draw a parent (device/circuit/panel) box with a centered, stacked text block.

        Shared primitive for all node types — callers handle termination box placement, this draws
        only the box background and the lines from `_get_parent_info` (bold linked name on top,
        detail lines below). `text_area_top`/`text_area_h` describe the free vertical span between
        any termination boxes (or box edges); the text block is centered within it, which yields
        the padding above and below.
        """
        _parent_key, lines = self._get_parent_info(termination)

        dwg.add(
            dwg.rect(
                insert=(box_x, box_y),
                size=(box_w, box_h),
                rx=constants.BORDER_RADIUS,
                ry=constants.BORDER_RADIUS,
                fill=constants.COLOR_SECONDARY_BG,
                stroke=constants.COLOR_BORDER,
                stroke_width=1,
            )
        )

        # Usable text width inside the box, inset at each end so text clears the rounded corners.
        # Detail lines render at FONT_SIZE_SM so they fit a few more chars.
        text_area_w = box_w - 2 * constants.BORDER_RADIUS
        self._draw_text_block(dwg, text_cx, text_area_top, text_area_h, text_area_w, lines)

    def _draw_node(self, dwg, cx, y, termination, term_position="top"):
        """Draw a device node with one termination box (top or bottom)."""
        half_term_h = self.TERM_H / 2

        if term_position == "top":
            term_y = y
            box_y = y + half_term_h
            # Free text span runs from the termination box's bottom edge to the box's bottom edge.
            text_area_top = box_y + half_term_h
            text_area_h = self.NODE_TEXT_AREA_H
            total_bottom = box_y + self.NODE_H
        else:
            box_y = y
            term_y = y + self.NODE_H - half_term_h
            # Free text span runs from the box's top edge to the termination box's top edge.
            text_area_top = box_y
            text_area_h = self.NODE_TEXT_AREA_H
            total_bottom = term_y + self.TERM_H

        self._draw_parent_box(
            dwg,
            cx - self.NODE_W / 2,
            box_y,
            self.NODE_W,
            self.NODE_H,
            cx,
            text_area_top,
            text_area_h,
            termination,
        )
        self._draw_termination_box(dwg, cx, term_y, termination)

        return total_bottom

    def _group_cx(self, cell, col_centers):
        """Horizontal center of a grouped cell, spanning `col` through `col + colspan - 1`."""
        first_cx = col_centers[cell["col"]]
        last_cx = col_centers[cell["col"] + cell["colspan"] - 1]
        return (first_cx + last_cx) / 2

    def _grouped_box_bounds(self, cell, col_centers):
        """Left edge and width of a grouped node's box spanning its columns.

        The box extends half a termination box (plus GAP_Y) past the outermost column centers on each
        side, so the leftmost and rightmost termination boxes sit fully inside it.
        """
        first_cx = col_centers[cell["col"]]
        last_cx = col_centers[cell["col"] + cell["colspan"] - 1]
        box_w = (last_cx - first_cx) + self.TERM_W + self.GAP_Y * 2
        box_x = first_cx - self.TERM_W / 2 - self.GAP_Y
        return box_x, box_w

    @staticmethod
    def _same_termination(first, second):
        """True if both are the same non-None termination (shared port)."""
        return first is not None and second is not None and first.pk == second.pk

    def _draw_termination_row(self, dwg, terminations, term_y, start_col, col_centers):
        """Draw a grouped cell's termination boxes at `term_y`.

        A run of consecutive columns sharing the same termination — a fan-in/fan-out trunk port
        reached by several legs — is drawn once, centered over the columns it spans, rather than
        redundantly per column. (All-or-nothing won't do: a grouped device can mix a shared trunk
        port with other, distinct ports.)
        """
        index = 0
        count = len(terminations)
        while index < count:
            termination = terminations[index]
            run_end = index + 1
            while run_end < count and self._same_termination(terminations[run_end], termination):
                run_end += 1
            first_cx = col_centers[start_col + index]
            last_cx = col_centers[start_col + run_end - 1]
            self._draw_termination_box(dwg, (first_cx + last_cx) / 2, term_y, termination)
            index = run_end

    def _draw_grouped_node_cell(self, dwg, y, cell, col_centers):
        """Draw a device box spanning multiple columns with side-by-side termination boxes at top."""
        terminations = cell["terminations"]
        start_col = cell["col"]
        half_term_h = self.TERM_H / 2
        group_cx = self._group_cx(cell, col_centers)
        box_x, box_w = self._grouped_box_bounds(cell, col_centers)
        box_y = y + half_term_h
        text_area_top = box_y + half_term_h

        self._draw_parent_box(
            dwg, box_x, box_y, box_w, self.NODE_H, group_cx, text_area_top, self.NODE_TEXT_AREA_H, terminations[0]
        )
        self._draw_termination_row(dwg, terminations, y, start_col, col_centers)

        return box_y + self.NODE_H

    def _draw_grouped_passthrough_node(self, dwg, y, cell, col_centers):
        """Draw a pass-through device box spanning multiple columns.

        Like `_draw_grouped_node_cell`, but with the arriving termination boxes side by side at the
        top and the departing termination boxes side by side at the bottom (e.g. a patch panel whose
        front ports pass through to rear ports across several breakout legs). When the legs converge
        on a single shared port (an MPO trunk feeding several lanes), that port is drawn once.
        """
        arriving = cell["arriving"]
        departing = cell["departing"]
        start_col = cell["col"]
        half_term_h = self.TERM_H / 2
        text_area_h = self.NODE_TEXT_AREA_H
        box_h = self.TERM_H + text_area_h
        group_cx = self._group_cx(cell, col_centers)
        box_x, box_w = self._grouped_box_bounds(cell, col_centers)
        box_y = y + half_term_h
        departing_y = box_y + box_h - half_term_h
        text_area_top = box_y + half_term_h

        self._draw_parent_box(dwg, box_x, box_y, box_w, box_h, group_cx, text_area_top, text_area_h, arriving[0])
        self._draw_termination_row(dwg, arriving, y, start_col, col_centers)
        self._draw_termination_row(dwg, departing, departing_y, start_col, col_centers)

        return departing_y + self.TERM_H

    def _draw_cable(self, dwg, cx, y, cable, near_end=None, far_end=None):
        """Draw a cable segment with color bar, label, breakout lane info, and status badge."""
        cable_color = f"#{cable.color}" if cable.color else constants.COLOR_SECONDARY
        is_connected = cable.status.name == "Connected"

        bar_h = self.CABLE_H
        self._draw_cable_line(dwg, (cx, y), (cx, y + bar_h), cable_color, is_connected)
        self._draw_cable_label(dwg, cx, y, bar_h, cable, near_end, far_end)

        return y + bar_h

    def _draw_cable_label(self, dwg, cx, y, bar_h, cable, near_end=None, far_end=None):
        """Draw a cable's side label — bold name, muted detail lines, then the status badge — as a
        vertical stack centered on the midpoint of a bar of height `bar_h` rooted at `(cx, y)`."""
        cable_url = self._url(cable)
        label_x = cx + self.CABLE_BAR_W / 2 + self.LABEL_OFFSET_X
        label_y = y + bar_h / 2

        detail_lines = self._cable_detail_lines(cable, near_end, far_end)
        line_step = self.TEXT_LINE_SPACING + 2
        row_count = 1 + len(detail_lines) + 1  # name + details + status badge
        # Vertical center of the first (top) row, working back from the bar midpoint.
        first_row_cy = label_y - (row_count - 1) * line_step / 2

        # Cable name (bold link).
        self._add_text(
            dwg,
            str(cable),
            label_x,
            first_row_cy + self.TEXT_VERTICAL_OFFSET,
            "start",
            constants.FONT_SIZE,
            "bold",
            url=cable_url,
        )
        # Muted detail lines (type, cable type, breakout lane info).
        for row_index, detail in enumerate(detail_lines, start=1):
            self._add_text(
                dwg,
                detail,
                label_x,
                first_row_cy + row_index * line_step + self.TEXT_VERTICAL_OFFSET,
                "start",
                constants.FONT_SIZE_SM,
                "normal",
            )

        # Status badge on the last row
        status_y = first_row_cy + (row_count - 1) * line_step
        self._draw_status_badge(dwg, label_x, status_y, cable.status.name, f"#{cable.status.color}")

    def _draw_cable_line(self, dwg, start, end, cable_color, is_connected):
        """Draw a cable line — the main trace bar or a breakout fork bar/drop.

        The cable color is drawn `CABLE_BAR_W - 2 * CABLE_BORDER_W` wide over a `CABLE_BAR_W`-wide border-color line,
        so the border shows as a CABLE_BORDER_W outline on each side and the cable stays distinct from the
        page background even when its color is near it. When the cable isn't connected the line is
        dashed, with the wider border peeking out as a "rung" at each dash.
        """
        if is_connected:
            dwg.add(dwg.line(start=start, end=end, stroke=constants.COLOR_BORDER, stroke_width=self.CABLE_BAR_W))
            dwg.add(
                dwg.line(
                    start=start, end=end, stroke=cable_color, stroke_width=self.CABLE_BAR_W - 2 * self.CABLE_BORDER_W
                )
            )
        else:
            for stroke, width, dasharray, dashoffset in (
                (constants.COLOR_BORDER, self.CABLE_BAR_W, self.CABLE_DASH_BORDER, 0),
                (cable_color, self.CABLE_BAR_W - 2 * self.CABLE_BORDER_W, self.CABLE_DASH, self.CABLE_DASH_OFFSET),
            ):
                line = dwg.line(start=start, end=end, stroke=stroke, stroke_width=width, stroke_dasharray=dasharray)
                if dashoffset:
                    line["stroke-dashoffset"] = dashoffset
                dwg.add(line)

    def _draw_cable_fan(self, dwg, segments, cable_color, is_connected):
        """Draw a breakout fan-out: straight cable lines diverging from a shared trunk point.

        Each segment is a `(start, end)` pair sharing the same trunk `start`. All border strokes are
        drawn before any color strokes (rather than border+color per line) so that where the branches
        converge at the trunk, a later branch's wider border never overpaints an earlier branch's
        fill — the fan stays a clean single junction.
        """
        if is_connected:
            strokes = (
                (constants.COLOR_BORDER, self.CABLE_BAR_W, None, 0),
                (cable_color, self.CABLE_BAR_W - 2 * self.CABLE_BORDER_W, None, 0),
            )
        else:
            strokes = (
                (constants.COLOR_BORDER, self.CABLE_BAR_W, self.CABLE_DASH_BORDER, 0),
                (cable_color, self.CABLE_BAR_W - 2 * self.CABLE_BORDER_W, self.CABLE_DASH, self.CABLE_DASH_OFFSET),
            )
        for stroke, width, dasharray, dashoffset in strokes:
            for start, end in segments:
                line = dwg.line(start=start, end=end, stroke=stroke, stroke_width=width)
                if dasharray:
                    line["stroke-dasharray"] = dasharray
                if dashoffset:
                    line["stroke-dashoffset"] = dashoffset
                dwg.add(line)

    def _draw_passthrough_node(self, dwg, cx, y, arriving_termination, departing_termination):
        """Draw a device node with arriving port at top and departing port at bottom."""
        half_term_h = self.TERM_H / 2
        text_area_h = self.NODE_TEXT_AREA_H
        box_h = self.TERM_H + text_area_h

        box_y = y + half_term_h
        departing_y = box_y + box_h - half_term_h
        text_area_top = box_y + half_term_h

        self._draw_parent_box(
            dwg,
            cx - self.NODE_W / 2,
            box_y,
            self.NODE_W,
            box_h,
            cx,
            text_area_top,
            text_area_h,
            arriving_termination,
        )
        self._draw_termination_box(dwg, cx, y, arriving_termination)
        self._draw_termination_box(dwg, cx, departing_y, departing_termination)

        return departing_y + self.TERM_H

    def _draw_status_badge(self, dwg, x, y, status_name, bg_color):
        """Draw a Bootstrap-style badge pill with colored background and contrasting text."""
        text_width = estimate_text_width(status_name, constants.FONT_SIZE_SM)
        # Pad the pill horizontally/vertically relative to the font size it wraps.
        badge_w = text_width + constants.FONT_SIZE_SM
        badge_h = constants.FONT_SIZE_SM + self.GAP_Y

        dwg.add(
            dwg.rect(
                insert=(x, y - badge_h / 2),
                size=(badge_w, badge_h),
                rx=constants.BORDER_RADIUS,
                ry=constants.BORDER_RADIUS,
                fill=bg_color,
            )
        )

        text_color = fgcolor(bg_color)
        dwg.add(
            dwg.text(
                status_name,
                insert=(x + badge_w / 2, y + self.TEXT_VERTICAL_OFFSET),
                text_anchor="middle",
                fill=text_color,
                font_size=f"{constants.FONT_SIZE_SM}px",
                font_family=constants.FONT_FAMILY,
                font_weight="bold",
            )
        )

    def _draw_termination_box(self, dwg, cx, y, termination):
        """Draw a single termination sub-box: bold linked name plus a "<verbose name> (<type>)" line."""
        termination_x = cx - self.TERM_W / 2
        is_active = termination == self.origin
        termination_url = self._url(termination) if termination else "#"

        border_color = constants.COLOR_SUCCESS if is_active else constants.COLOR_BORDER
        border_width = 3 if is_active else 1

        dwg.add(
            dwg.rect(
                insert=(termination_x, y),
                size=(self.TERM_W, self.TERM_H),
                rx=constants.BORDER_RADIUS,
                ry=constants.BORDER_RADIUS,
                fill=constants.COLOR_TERTIARY_BG,
                stroke=border_color,
                stroke_width=border_width,
            )
        )

        # Line 0: the linked name; line 1: the model verbose name plus type display, if any.
        lines = [(str(termination), termination_url)]
        if termination is not None:
            detail = bettertitle(termination._meta.verbose_name)
            type_display = getattr(termination, "get_type_display", None)
            if getattr(termination, "type", None) and callable(type_display):
                detail = f"{detail} ({type_display()})"
            lines.append((detail, None))

        self._draw_text_block(dwg, cx, y, self.TERM_H, self.TERM_W - 2 * self.TERM_TEXT_PAD, lines)

    def _trace_url(self, node):
        """Absolute URL of the trace view for a split next-hop node (FrontPort/RearPort)."""
        try:
            return self.base_url + reverse(f"dcim:{node._meta.model_name}_trace", kwargs={"pk": node.pk})
        except NoReverseMatch:
            return self._url(node)

    def _trace_end_lines(self):
        """Descriptors `(text, font_size, font_weight, fill, url)` for the trace-end footer.

        For a branched (breakout) trace, a single neutral aggregate line — there is no one end state
        to report, and each lane's outcome is already shown in its own column. For a split path
        (`CablePath.is_split`): a "Path split!" heading and the selectable next-hop nodes to continue
        through. Otherwise a completion summary with the total segment count and linear length (when
        available), mirroring the legacy `cable_trace.html` footer. Centralizing the content here
        lets both the rendered footer and the canvas width derive from one source.
        """
        cable_path = self.cable_path
        lines = []

        # A branched trace's `cable_path`/`traced_path` only describe the first lane, so a single
        # completion/split/totals summary would misrepresent the other branches.
        if len(self.fanout_paths) > 1:
            return [(f"Breakout fan-out — {len(self.fanout_paths)} branches", constants.FONT_SIZE, "bold", None, None)]

        if cable_path is not None and cable_path.is_split:
            lines.append(("Path split!", constants.FONT_SIZE, "bold", constants.COLOR_DANGER, None))
            lines.append(("Select a node below to continue:", constants.FONT_SIZE_SM, "normal", None, None))
            for next_node in cable_path.get_split_nodes():
                next_cable = getattr(next_node, "cable", None)
                # A node with an onward cable links to its trace view, naming that cable inline; a
                # node with no cable can't be continued, so it stays plain muted text.
                if next_cable is not None:
                    text = f"{next_node}  (Cable {next_cable})"
                    lines.append((text, constants.FONT_SIZE_SM, "normal", None, self._trace_url(next_node)))
                else:
                    lines.append((str(next_node), constants.FONT_SIZE_SM, "normal", None, None))
            return lines

        complete = cable_path is not None and cable_path.destination is not None
        lines.append(
            (
                "Trace completed" if complete else "Trace incomplete",
                constants.FONT_SIZE,
                "bold",
                constants.COLOR_SUCCESS if complete else constants.COLOR_DANGER,
                None,
            )
        )
        lines.append((f"Total segments: {len(self.traced_path)}", constants.FONT_SIZE_SM, "normal", None, None))
        total_length = cable_path.get_total_length() if cable_path is not None else None
        if total_length:
            length_text = (
                f"Total length: {self._format_length(total_length)} Meters"
                f" / {self._format_length(meters_to_feet(total_length))} Feet"
            )
        else:
            length_text = "Total length: N/A"
        lines.append((length_text, constants.FONT_SIZE_SM, "normal", None, None))
        return lines

    def _trace_end_width(self):
        """Estimated width of the widest footer line (centered, so half is reserved on each side)."""
        return max(
            (estimate_text_width(text, font_size) for text, font_size, *_ in self._trace_end_lines()),
            default=0,
        )

    def _draw_trace_end(self, dwg, cx, y):
        """Draw the trace-end footer (see `_trace_end_lines`), centered at `cx`."""
        line_step = self.TEXT_LINE_SPACING + self.GAP_Y
        y += self.TRACE_END_PADDING
        for index, (text, font_size, font_weight, fill, url) in enumerate(self._trace_end_lines()):
            y += font_size if index == 0 else line_step
            self._add_text(dwg, text, cx, y, "middle", font_size, font_weight, url=url, fill=fill)
        return y + self.TRACE_END_PADDING

    @staticmethod
    def _format_length(value):
        """Format a length with up to two decimal places, trailing zeros stripped (cf. floatformat:-2)."""
        return f"{float(value):.2f}".rstrip("0").rstrip(".")

    def _render_empty(self):
        """Render an empty/no-path SVG."""
        dwg = svgwrite.Drawing(size=(f"{self.COL_WIDTH}px", f"{self.EMPTY_HEIGHT}px"), debug=False)
        dwg.viewbox(0, 0, self.COL_WIDTH, self.EMPTY_HEIGHT)
        dwg.add(
            dwg.text(
                "No cable path found",
                insert=(self.COL_WIDTH / 2, self.EMPTY_HEIGHT / 2),
                text_anchor="middle",
                fill=constants.COLOR_SECONDARY,
                font_size=f"{constants.FONT_SIZE}px",
                font_family=constants.FONT_FAMILY,
            )
        )
        return mark_safe(dwg.tostring())  # noqa: S308
