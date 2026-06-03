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
          (colspan for grouped devices, continuation markers for empty cells above active content,
          etc.).
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
    FORK_DROP_LENGTH = 3 * GAP_Y  # vertical drop from fork bar to first row
    TRACE_END_PADDING = 5
    # Minimum reserve for cable labels/badges hanging off the rightmost column. Actual reserve
    # is sized to the longest cable label found in the trace; this is the floor used when no
    # cables (or only very short ones) are present.
    LABEL_RIGHT_RESERVE_MIN = 140

    # Layout: termination sub-box. TERM_W is wide enough to fit most port / circuit termination
    # names without truncation; values that still overflow get clipped to an ellipsis with the
    # full string available on hover via a `<title>` element.
    TERM_W = 230
    TERM_BORDER_RADIUS = 5
    # Horizontal padding inside the termination box; the usable text area is `TERM_W - 2 * TERM_TEXT_PAD`.
    TERM_TEXT_PAD = 8
    # Vertical padding above and below the termination box's stacked text block.
    TERM_TEXT_PAD_Y = 6
    # TERM_H holds two stacked lines: the bold termination name plus a "<verbose name> (<type>)"
    # detail line (mirroring trace/termination.html), with vertical padding.
    TERM_H = constants.FONT_SIZE + TEXT_LINE_SPACING + 2 * TERM_TEXT_PAD_Y

    # Layout: node (device/circuit/panel box)
    NODE_W = 260
    NODE_BORDER_RADIUS = 8
    # Vertical padding above and below the stacked text block within a node box.
    NODE_TEXT_PAD_Y = 8
    # NODE_TEXT_AREA_H is the free vertical span reserved for a node's stacked text block: the bold
    # name (FONT_SIZE) plus up to three detail lines (FONT_SIZE_SM each — e.g. a device's
    # manufacturer/type, location, and rack), with padding so the text clears the box edges and any
    # termination sub-boxes. The height is fixed (sized for the tallest node) so rows stay aligned
    # when they mix node types; shorter nodes just center their text with extra padding. NODE_H adds
    # the half-termination overlap a single (top- or bottom-) termination box contributes beyond it.
    NODE_TEXT_AREA_H = constants.FONT_SIZE + 3 * TEXT_LINE_SPACING + 2 * NODE_TEXT_PAD_Y
    NODE_H = NODE_TEXT_AREA_H + TERM_H // 2

    # Layout: cable segment
    CABLE_H = 140
    CABLE_BAR_W = 5

    # Layout: pass-through
    PASSTHROUGH_H = 30

    # Layout: overall dimensions
    MAX_WIDTH = 465
    # Column pitch must be >= NODE_W so adjacent device boxes in different columns don't overlap;
    # the extra ~20 px gives a visible gap between distinct devices.
    COL_WIDTH = 280
    INITIAL_HEIGHT = 900
    INITIAL_FANOUT_HEIGHT = 2350
    EMPTY_HEIGHT = 70

    # Line widths
    FORK_LINE_WIDTH = 2

    def __init__(self, origin, base_url="", cable_path=None):
        self.origin = origin
        self.base_url = base_url.rstrip("/") if base_url else ""
        # Render the explicitly-selected CablePath when given (e.g. a `?cablepath_id=` choice);
        # otherwise fall back to the origin endpoint's first path.
        if cable_path is None and hasattr(origin, "cable_paths"):
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

        _, cable, _ = self.traced_path[0]
        if not cable or not cable.cable_type_id:
            return []

        from nautobot.dcim.models import CablePath, CableToCableTermination

        # Locate the origin's CableToCableTermination row to learn which side we're on.
        origin_ct = ContentType.objects.get_for_model(self.origin)
        origin_row = next(
            (
                row
                for row in cable.terminations.all()
                if row.termination_id == self.origin.pk
                and row.termination_type
                and (row.termination_type.app_label, row.termination_type.model)
                == (origin_ct.app_label, origin_ct.model)
            ),
            None,
        )
        if origin_row is None:
            return []

        origin_side = origin_row.cable_end  # "A" or "B"
        opposite_side = "B" if origin_side == "A" else "A"
        origin_side_key = "a_connector" if origin_side == "A" else "b_connector"
        far_side_key = "b_connector" if origin_side == "A" else "a_connector"

        # All mapping entries that originate from the origin's connector, deduplicated by the
        # far-side connector so multi-position trunks contribute one leg per peer connector.
        seen_far_connectors = []
        for entry in cable.cable_type.mapping or []:
            if entry.get(origin_side_key) != origin_row.connector:
                continue
            far_connector = entry.get(far_side_key)
            if far_connector is None or far_connector in seen_far_connectors:
                continue
            seen_far_connectors.append(far_connector)
        seen_far_connectors.sort()

        if len(seen_far_connectors) <= 1:
            return []

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

            fanout_legs.append(
                {
                    "termination": termination,
                    "connector_label": f"{opposite_side}{far_connector}",
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
        node box, mirroring the multi-line `dcim/trace/*.html` partials: line 0 is the bold parent
        name and any further lines are detail. `url` is `None` for plain text or an absolute URL to
        render the line as a link. `key` groups same-device nodes via the parent's globally-unique
        UUID; `termination.parent` handles device, module, circuit, and power_panel.
        """
        if termination is None:
            return None, []

        parent = getattr(termination, "parent", None)
        if parent is None:
            return (None, [(str(termination), "#")])

        parent_key = str(parent.pk)
        # Line 0: the linked parent name. Detail lines are appended below per parent type.
        lines = [(str(parent), self._url(parent))]

        if hasattr(parent, "device_type"):
            # Device — manufacturer + device type, then location and rack each on their own line
            # (see trace/device.html; split onto separate lines so each centers cleanly).
            lines.append((f"{parent.device_type.manufacturer} {parent.device_type}", None))
            location = getattr(parent, "location", None)
            rack = getattr(parent, "rack", None)
            if location:
                lines.append((str(location), self._url(location)))
            if rack:
                lines.append((str(rack), self._url(rack)))
        elif hasattr(parent, "provider"):
            # Circuit — name is the cid, then "Circuit" and the linked provider (see trace/circuit.html).
            lines.append(("Circuit", None))
            lines.append((str(parent.provider), self._url(parent.provider)))
        else:
            # PowerPanel / Module / other — verbose name, then linked location if any (see trace/powerpanel.html).
            lines.append((parent._meta.verbose_name.title(), None))
            location = getattr(parent, "location", None)
            if location is not None:
                lines.append((str(location), self._url(location)))

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
            widths.append(self._status_badge_width(cable))

        if header_cable is not None:
            add(header_cable, None, None)
        for entries in column_entries:
            for entry in entries:
                if entry.get("type") == "cable" and entry.get("cable") is not None:
                    add(entry["cable"], entry.get("near"), entry.get("far"))
        return max(widths, default=0)

    def _status_badge_width(self, cable):
        """Estimated rendered width of the status badge pill drawn beside a cable bar."""
        status = getattr(cable, "status", None)
        status_name = status.name if status else "Unknown"
        # Mirrors `_draw_status_badge`: text width plus horizontal padding of FONT_SIZE_SM.
        return estimate_text_width(status_name, constants.FONT_SIZE_SM) + constants.FONT_SIZE_SM

    def _cable_lane_info(self, cable, termination):
        """Return the `CableToCableTermination` row matching `termination` on `cable`, or None."""
        if cable is None or termination is None:
            return None
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

        Cell types:
            {"type": "node", "col": int, "colspan": 1, "termination": obj}
            {"type": "grouped_node", "col": int, "colspan": int,
             "terminations": [obj, ...], "parent_key": str}
            {"type": "spanned"}  — covered by a grouped_node in a prior column
            {"type": "cable", "col": int, "cable": obj, "near": obj, "far": obj}
            {"type": "passthrough", "col": int, "near": obj, "far": obj}
            {"type": "empty", "col": int, "continuation": bool}
        """
        column_count = len(self.fanout_paths)

        near_end, cable, _ = self.traced_path[0] if self.traced_path else (None, None, None)
        cable_color = f"#{cable.color}" if cable and cable.color else constants.COLOR_SECONDARY

        header = {
            "origin": near_end,
            "cable": cable,
            "cable_color": cable_color,
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
        total_width = max(band_width + 2 * side_overhang, self._trace_end_width(), self.MAX_WIDTH)
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

        # Step 3: Mark continuation on empty cells (if any cell below in the same column has content).
        for col_idx in range(column_count):
            last_content_row_idx = -1
            for row_idx in range(len(raw_rows) - 1, -1, -1):
                if raw_rows[row_idx][col_idx]["type"] != "empty":
                    last_content_row_idx = row_idx
                    break
            for row_idx in range(last_content_row_idx):
                cell = raw_rows[row_idx][col_idx]
                if cell["type"] == "empty":
                    cell["continuation"] = True
                else:
                    cell.setdefault("continuation", False)
            for row_idx in range(last_content_row_idx, len(raw_rows)):
                cell = raw_rows[row_idx][col_idx]
                cell.setdefault("continuation", False)

        # Step 4: Collapse a run of same-type cells that share a grouping key into one cell spanning
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
                            "continuation": False,
                        }
                    elif cell["type"] == "passthrough_node":
                        row[col_idx] = {
                            "type": "grouped_passthrough_node",
                            "col": col_idx,
                            "colspan": colspan,
                            "arriving": [row[c]["arriving"] for c in spanned],
                            "departing": [row[c]["departing"] for c in spanned],
                            "parent_key": group_key,
                            "continuation": False,
                        }
                    else:  # cable shared across legs (a fan-in/fan-out trunk)
                        row[col_idx] = {
                            "type": "grouped_cable",
                            "col": col_idx,
                            "colspan": colspan,
                            "cable": cell["cable"],
                            "near": cell.get("near"),
                            "far": cell.get("far"),
                            "continuation": False,
                        }
                    for spanned_col in range(col_idx + 1, span_end):
                        row[spanned_col] = {"type": "spanned", "col": spanned_col, "continuation": False}
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
        """Render the complete trace as an SVG string."""
        if not self.traced_path:
            return self._render_empty()

        # Normalize: a linear trace is a single-leg fanout without the fork — ensures all paths
        # flow through the same build_matrix → render pipeline.
        if not self.fanout_paths:
            _, _, far_end = self.traced_path[0]
            self.fanout_paths = [
                {
                    "termination": far_end,
                    "connector_label": "",
                    "trace": self._expand_trace_segments(self.traced_path[1:]),
                }
            ]

        return self._render_fanout()

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

    def _render_fanout(self):
        """Render a breakout fan-out (or single-leg linear) trace from the matrix."""
        matrix = self.build_matrix()
        header = matrix["header"]
        col_centers = matrix["col_centers"]
        total_width = matrix["total_width"]

        dwg = svgwrite.Drawing(size=(f"{total_width}px", f"{self.INITIAL_FANOUT_HEIGHT}px"), debug=False)
        dwg.viewbox(0, 0, total_width, self.INITIAL_FANOUT_HEIGHT)

        trunk_cx = (col_centers[0] + col_centers[-1]) / 2 if col_centers else total_width / 2
        y = self.GAP_Y

        # Header: Origin node
        if header["origin"]:
            y = self._draw_node(dwg, trunk_cx, y, header["origin"], term_position="bottom")
            y += self.GAP_Y

        # Header: Breakout cable trunk + fork
        cable = header["cable"]
        if not cable:
            y = self._draw_trace_end(dwg, trunk_cx, y)
            dwg["height"] = f"{y + self.GAP_Y}px"
            dwg.viewbox(0, 0, total_width, y + self.GAP_Y)
            return mark_safe(dwg.tostring())  # noqa: S308

        cable_color = header["cable_color"]
        is_breakout_fanout = bool(cable.cable_type_id) and len(col_centers) > 1

        if is_breakout_fanout:
            # Breakout cable: half-height bar, then fork lines to each column.
            y = self._draw_cable(dwg, trunk_cx, y, cable)
            y += self.GAP_Y

            fork_y = y
            dwg.add(
                dwg.line(
                    start=(col_centers[0], fork_y),
                    end=(col_centers[-1], fork_y),
                    stroke=cable_color,
                    stroke_width=self.FORK_LINE_WIDTH,
                )
            )
            drop_end = fork_y + self.FORK_DROP_LENGTH
            for col_idx, cx in enumerate(col_centers):
                dwg.add(
                    dwg.line(
                        start=(cx, fork_y),
                        end=(cx, drop_end),
                        stroke=cable_color,
                        stroke_width=self.FORK_LINE_WIDTH,
                    )
                )
                label = header["connector_labels"][col_idx]
                if label:
                    dwg.add(
                        dwg.text(
                            label,
                            insert=(cx, fork_y - self.TEXT_VERTICAL_OFFSET),
                            text_anchor="middle",
                            fill=constants.COLOR_SECONDARY,
                            font_size=f"{constants.FONT_SIZE_SM}px",
                            font_family=constants.FONT_FAMILY,
                            font_weight="bold",
                        )
                    )
            y = drop_end + self.GAP_Y
        else:
            # Linear or single-leg: full-height cable bar, no fork.
            y = self._draw_cable(dwg, trunk_cx, y, cable)
            y += self.GAP_Y

        # Two-pass row rendering for z-order (background first, foreground on top).
        row_positions = []
        for row in matrix["rows"]:
            row_h = self._compute_row_height(row)
            row_positions.append((y, row, row_h))
            y += row_h + self.GAP_Y

        for row_y, row, row_h in row_positions:
            self._render_row_background(dwg, row_y, row, row_h, col_centers)

        for row_y, row, row_h in row_positions:
            self._render_row_foreground(dwg, row_y, row, col_centers)

        # Footer: split next-hops, or completion summary (segment count + total length).
        y = self._draw_trace_end(dwg, trunk_cx, y)

        dwg["height"] = f"{y + self.GAP_Y}px"
        dwg["width"] = f"{total_width}px"
        dwg.viewbox(0, 0, total_width, y + self.GAP_Y)
        return mark_safe(dwg.tostring())  # noqa: S308

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
            elif cell["type"] == "passthrough":
                row_h = max(row_h, self.PASSTHROUGH_H)
        return row_h

    def _render_row_background(self, dwg, y, row, row_h, col_centers):
        """Draw background elements for a row: cables, pass-through lines, continuation lines."""
        if row_h == 0:
            return
        for cell in row:
            cx = col_centers[cell["col"]]

            if cell["type"] == "cable":
                self._draw_cable(dwg, cx, y, cell["cable"], cell.get("near"), cell.get("far"))

            elif cell["type"] == "grouped_cable":
                # A shared trunk spanning several legs — drawn once, centered over the span.
                self._draw_cable(
                    dwg, self._group_cx(cell, col_centers), y, cell["cable"], cell.get("near"), cell.get("far")
                )

            elif cell["type"] == "passthrough":
                dwg.add(
                    dwg.line(
                        start=(cx, y),
                        end=(cx, y + row_h),
                        stroke=constants.COLOR_BORDER,
                        stroke_width=1,
                        stroke_dasharray="4,3",
                    )
                )
                dwg.add(
                    dwg.text(
                        "pass-thru",
                        insert=(cx + self.LABEL_OFFSET_X, y + row_h / 2 + self.TEXT_VERTICAL_OFFSET),
                        fill=constants.COLOR_SECONDARY,
                        font_size=f"{constants.FONT_SIZE_SM}px",
                        font_family=constants.FONT_FAMILY,
                    )
                )

            elif cell["type"] == "empty" and cell.get("continuation"):
                dwg.add(
                    dwg.line(
                        start=(cx, y),
                        end=(cx, y + row_h),
                        stroke=constants.COLOR_BORDER,
                        stroke_width=1,
                        stroke_dasharray="2,4",
                        opacity=0.3,
                    )
                )

    def _render_row_foreground(self, dwg, y, row, col_centers):
        """Draw foreground elements for a row: device boxes, termination boxes."""
        for cell in row:
            cx = col_centers[cell["col"]]

            if cell["type"] == "node":
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
                rx=self.NODE_BORDER_RADIUS,
                ry=self.NODE_BORDER_RADIUS,
                fill=constants.COLOR_SECONDARY_BG,
                stroke=constants.COLOR_BORDER,
                stroke_width=1,
            )
        )

        # Usable text width inside the box, after the NODE_BORDER_RADIUS rounded corners eat a few
        # pixels at each end. Detail lines render at FONT_SIZE_SM so they fit a few more chars.
        text_area_w = box_w - 2 * self.NODE_BORDER_RADIUS
        self._draw_text_block(dwg, text_cx, text_area_top, text_area_h, text_area_w, lines)

    def _draw_node(self, dwg, cx, y, termination, term_position="top", is_last=False):
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

        first_cx = col_centers[start_col]
        last_cx = col_centers[start_col + cell["colspan"] - 1]
        box_w = (last_cx - first_cx) + self.TERM_W + self.GAP_Y * 2
        box_x = first_cx - self.TERM_W / 2 - self.GAP_Y
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
        box_h = half_term_h + text_area_h + half_term_h
        group_cx = self._group_cx(cell, col_centers)

        first_cx = col_centers[start_col]
        last_cx = col_centers[start_col + cell["colspan"] - 1]
        box_w = (last_cx - first_cx) + self.TERM_W + self.GAP_Y * 2
        box_x = first_cx - self.TERM_W / 2 - self.GAP_Y
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
        cable_url = self._url(cable)
        is_connected = hasattr(cable, "status") and cable.status and cable.status.name == "Connected"

        bar_x = cx - self.CABLE_BAR_W / 2
        bar_h = self.CABLE_H

        if is_connected:
            dwg.add(dwg.rect(insert=(bar_x, y), size=(self.CABLE_BAR_W, bar_h), fill=cable_color))
        else:
            dwg.add(
                dwg.line(
                    start=(cx, y),
                    end=(cx, y + bar_h),
                    stroke=cable_color,
                    stroke_width=self.CABLE_BAR_W,
                    stroke_dasharray="8,4",
                )
            )

        label_x = cx + self.CABLE_BAR_W / 2 + self.LABEL_OFFSET_X
        label_y = y + bar_h / 2

        # The label is a vertical stack — bold cable name, muted detail lines, then the status badge
        # — centered on the cable bar's midpoint so it sits between the terminations above and below.
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

        # Status badge on the last row (positioned by its vertical center).
        status = cable.status if hasattr(cable, "status") else None
        status_name = status.name if status else "Unknown"
        status_color = f"#{status.color}" if status and status.color else constants.COLOR_SECONDARY
        self._draw_status_badge(dwg, label_x, first_row_cy + (row_count - 1) * line_step, status_name, status_color)

        return y + bar_h

    def _draw_passthrough_node(self, dwg, cx, y, arriving_termination, departing_termination):
        """Draw a device node with arriving port at top and departing port at bottom."""
        half_term_h = self.TERM_H / 2
        text_area_h = self.NODE_TEXT_AREA_H
        box_h = half_term_h + text_area_h + half_term_h

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
        badge_r = self.TERM_BORDER_RADIUS

        dwg.add(
            dwg.rect(
                insert=(x, y - badge_h / 2),
                size=(badge_w, badge_h),
                rx=badge_r,
                ry=badge_r,
                fill=bg_color,
            )
        )

        text_color = fgcolor(bg_color.lstrip("#")) if bg_color.startswith("#") else "#ffffff"
        dwg.add(
            dwg.text(
                status_name,
                insert=(x + badge_w / 2, y + self.TEXT_VERTICAL_OFFSET),
                text_anchor="middle",
                fill=f"#{text_color}" if not text_color.startswith("#") else text_color,
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
                rx=self.TERM_BORDER_RADIUS,
                ry=self.TERM_BORDER_RADIUS,
                fill=constants.COLOR_TERTIARY_BG,
                stroke=border_color,
                stroke_width=border_width,
            )
        )

        # Line 0: the linked name; line 1: the model verbose name plus type display, if any
        # (mirrors trace/termination.html).
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
