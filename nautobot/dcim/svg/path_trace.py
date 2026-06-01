"""Server-side SVG generation for cable path trace diagrams.

The renderer ingests a `PathEndpoint` origin and emits an SVG depicting the full trace from that
origin to its destination(s), including breakout fan-outs, pass-through ports, multi-hop paths,
and unconnected breakout lanes. See `CableTraceSVG` for the public entry point.
"""

from django.contrib.contenttypes.models import ContentType
from django.utils.html import mark_safe
import svgwrite

from nautobot.core.templatetags.helpers import fgcolor


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

    # Layout: overall dimensions
    MAX_WIDTH = 400
    # Column pitch must be >= NODE_W so adjacent device boxes in different columns don't overlap;
    # the extra ~20 px gives a visible gap between distinct devices.
    COL_WIDTH = 200
    INITIAL_HEIGHT = 800
    INITIAL_FANOUT_HEIGHT = 2000
    EMPTY_HEIGHT = 60

    # Layout: node (device/circuit/panel box)
    NODE_W = 180
    NODE_H = 50
    NODE_BORDER_RADIUS = 6

    # Layout: termination sub-box. TERM_W bumped to fit longer port / circuit termination names
    # without immediate truncation; values that still overflow get clipped to an ellipsis with
    # the full string available on hover via a `<title>` element.
    TERM_W = 160
    TERM_H = 26
    TERM_BORDER_RADIUS = 4
    # Horizontal padding inside the termination box; the usable text area is `TERM_W - 2 * TERM_TEXT_PAD`.
    TERM_TEXT_PAD = 6

    # Layout: cable segment
    CABLE_H = 120
    CABLE_BAR_W = 4

    # Layout: pass-through
    PASSTHROUGH_H = 24

    # Layout: spacing and offsets
    GAP_Y = 4
    LABEL_OFFSET_X = 8
    FORK_DROP_LENGTH = 12  # GAP_Y * 3 — vertical drop from fork bar to first row
    TEXT_LINE_SPACING = 10
    TEXT_VERTICAL_OFFSET = 4
    TRACE_END_PADDING = 6
    TRACE_END_HEIGHT = 20
    # Minimum reserve for cable labels/badges hanging off the rightmost column. Actual reserve
    # is sized to the longest cable label found in the trace; this is the floor used when no
    # cables (or only very short ones) are present.
    LABEL_RIGHT_RESERVE_MIN = 120

    # Typography
    FONT_FAMILY = "system-ui, -apple-system, sans-serif"
    FONT_SIZE = 12
    FONT_SIZE_SM = 10
    # Approximate average glyph width as a fraction of font size for sans-serif text. Used to
    # size badge backgrounds; 0.65 covers uppercase-heavy strings.
    FONT_WIDTH_RATIO = 0.65

    # Line widths
    FORK_LINE_WIDTH = 2

    # Colors
    COLOR_NODE_BG = "#f8f9fa"
    COLOR_NODE_BORDER = "#dee2e6"
    COLOR_TERM_BG = "#e9ecef"
    COLOR_TERM_BORDER = "#adb5bd"
    COLOR_ACTIVE_BORDER = "#198754"
    COLOR_TEXT = "#212529"
    COLOR_TEXT_MUTED = "#6c757d"
    COLOR_LINK = "#0d6efd"
    COLOR_CABLE_DEFAULT = "#606060"
    COLOR_SUCCESS = "#198754"
    COLOR_DANGER = "#dc3545"
    COLOR_WARNING = "#ffc107"

    def __init__(self, origin, base_url=""):
        self.origin = origin
        self.base_url = base_url.rstrip("/") if base_url else ""
        self.traced_path = origin.trace() if hasattr(origin, "trace") else []
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
                full_path_objects = [self.origin, *cable_path.get_path()]
                while (len(full_path_objects) + 1) % 3:
                    full_path_objects.append(None)
                full_path_objects.append(cable_path.destination)
                full_trace = list(zip(*[iter(full_path_objects)] * 3))
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
        """Extract parent info for a termination: grouping key, display name, detail, and URL.

        Returns (key, name, detail, url). Key groups same-device nodes; uses `termination.parent`
        which handles device, module, circuit, and power_panel.
        """
        if termination is None:
            return None, None, None, None

        parent = getattr(termination, "parent", None)
        if parent is None:
            return (None, str(termination), "", "#")

        parent_key = str(parent.pk)
        parent_name = str(parent)
        parent_url = self._url(parent)

        if hasattr(parent, "device_type"):
            # Device — show manufacturer / device type.
            detail = f"{parent.device_type.manufacturer} / {parent.device_type}"
        elif hasattr(parent, "provider"):
            # Circuit — prefix key to avoid PK collisions with devices.
            parent_key = f"c:{parent.pk}"
            parent_name = f"{parent.provider} / {parent.cid}"
            detail = "Circuit"
        else:
            # PowerPanel or other — use verbose name as detail.
            parent_key = f"{parent._meta.model_name}:{parent.pk}"
            detail = parent._meta.verbose_name.title()

        return (parent_key, parent_name, detail, parent_url)

    def _fit_text(self, text, max_width, font_size=None):
        """Truncate `text` with an ellipsis if its estimated rendered width exceeds `max_width` px.

        Width estimate uses the `font_size * FONT_WIDTH_RATIO` heuristic; callers should attach the
        un-truncated `text` as a `<title>` tooltip for full discoverability when truncation occurs.
        """
        if not text:
            return ""
        font_size = font_size or self.FONT_SIZE
        max_chars = max(int(max_width / (font_size * self.FONT_WIDTH_RATIO)), 1)
        if len(text) <= max_chars:
            return text
        # Reserve one slot for the ellipsis glyph.
        return text[: max(max_chars - 1, 1)] + "…"

    def _max_cable_label_width(self, header_cable, column_entries):
        """Estimate the widest cable label that will be drawn to the right of any column center."""
        labels = []
        if header_cable is not None:
            labels.append(str(header_cable))
        for entries in column_entries:
            for entry in entries:
                if entry.get("type") == "cable" and entry.get("cable") is not None:
                    labels.append(str(entry["cable"]))
        if not labels:
            return 0
        max_chars = max(len(label) for label in labels)
        return max_chars * self.FONT_SIZE * self.FONT_WIDTH_RATIO

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
        cable_color = f"#{cable.color}" if cable and cable.color else self.COLOR_CABLE_DEFAULT

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

        # Layout: now that we know every cable label in the trace, size the canvas to fit them
        # and center the column band horizontally within `total_width`.
        col_width = self.COL_WIDTH
        # Leftmost / rightmost overhang relative to a column center.
        left_overhang = max(self.NODE_W / 2, 0)
        right_overhang = (
            self.LABEL_OFFSET_X
            + self._max_cable_label_width(header["cable"], column_entries)
            + self.GAP_Y * 2  # safety margin: width estimation is a fraction-of-em approximation
        )
        right_overhang = max(right_overhang, self.LABEL_RIGHT_RESERVE_MIN, left_overhang)
        # `content_extent` is the actual horizontal range from leftmost node edge to rightmost label edge,
        # measured relative to the first column's center.
        content_extent = (column_count - 1) * col_width + left_overhang + right_overhang
        total_width = max(content_extent, self.MAX_WIDTH)
        # Center the content band; first column's center sits at `left_overhang + extra/2`.
        first_col_x = left_overhang + max((total_width - content_extent) / 2, 0)
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

        # Step 4: Group consecutive same-parent node cells into colspan.
        rows = []
        for raw_row in raw_rows:
            row = list(raw_row)

            col_idx = 0
            while col_idx < column_count:
                cell = row[col_idx]
                if cell["type"] == "node" and cell.get("termination") is not None:
                    parent_key = self._get_parent_info(cell["termination"])[0]
                    span_end = col_idx + 1
                    while span_end < column_count:
                        next_cell = row[span_end]
                        if next_cell["type"] == "node" and next_cell.get("termination") is not None:
                            if (
                                self._get_parent_info(next_cell["termination"])[0] == parent_key
                                and parent_key is not None
                            ):
                                span_end += 1
                                continue
                        break

                    colspan = span_end - col_idx
                    if colspan > 1:
                        terminations = [row[spanned_col]["termination"] for spanned_col in range(col_idx, span_end)]
                        row[col_idx] = {
                            "type": "grouped_node",
                            "col": col_idx,
                            "colspan": colspan,
                            "terminations": terminations,
                            "parent_key": parent_key,
                            "continuation": False,
                        }
                        for spanned_col in range(col_idx + 1, span_end):
                            row[spanned_col] = {"type": "spanned", "col": spanned_col, "continuation": False}
                        col_idx = span_end
                    else:
                        cell["colspan"] = 1
                        col_idx += 1
                else:
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
            y = self._draw_trace_end(dwg, trunk_cx, y, incomplete=True)
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
                            fill=self.COLOR_TEXT_MUTED,
                            font_size=f"{self.FONT_SIZE_SM}px",
                            font_family=self.FONT_FAMILY,
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
            elif cell["type"] == "passthrough_node":
                text_area_h = self.TEXT_LINE_SPACING * 3
                row_h = max(row_h, self.TERM_H + text_area_h)
            elif cell["type"] == "cable":
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

            elif cell["type"] == "passthrough":
                dwg.add(
                    dwg.line(
                        start=(cx, y),
                        end=(cx, y + row_h),
                        stroke=self.COLOR_NODE_BORDER,
                        stroke_width=1,
                        stroke_dasharray="4,3",
                    )
                )
                dwg.add(
                    dwg.text(
                        "pass-thru",
                        insert=(cx + self.LABEL_OFFSET_X, y + row_h / 2 + self.TEXT_VERTICAL_OFFSET),
                        fill=self.COLOR_TEXT_MUTED,
                        font_size=f"{self.FONT_SIZE_SM}px",
                        font_family=self.FONT_FAMILY,
                    )
                )

            elif cell["type"] == "empty" and cell.get("continuation"):
                dwg.add(
                    dwg.line(
                        start=(cx, y),
                        end=(cx, y + row_h),
                        stroke=self.COLOR_NODE_BORDER,
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
                            fill=self.COLOR_WARNING,
                            font_size=f"{self.FONT_SIZE_SM}px",
                            font_family=self.FONT_FAMILY,
                            font_weight="bold",
                        )
                    )
                else:
                    self._draw_node(dwg, cx, y, cell["termination"], term_position="top")

            elif cell["type"] == "grouped_node":
                self._draw_grouped_node_cell(dwg, y, cell, col_centers)

            elif cell["type"] == "passthrough_node":
                self._draw_passthrough_node(dwg, cx, y, cell["arriving"], cell["departing"])

    # ──────────────────────────────────────────────
    # Cell drawing primitives
    # ──────────────────────────────────────────────

    def _draw_device_box(self, dwg, box_x, box_y, box_w, box_h, text_cx, text_area_top, text_area_h, termination):
        """Draw a device/circuit/panel box with centered name and detail text.

        Shared primitive for all node types — callers handle termination box placement, this
        draws only the device background and text.
        """
        _parent_key, parent_name, parent_detail, parent_url = self._get_parent_info(termination)

        dwg.add(
            dwg.rect(
                insert=(box_x, box_y),
                size=(box_w, box_h),
                rx=self.NODE_BORDER_RADIUS,
                ry=self.NODE_BORDER_RADIUS,
                fill=self.COLOR_NODE_BG,
                stroke=self.COLOR_NODE_BORDER,
                stroke_width=1,
            )
        )

        text_center_y = text_area_top + text_area_h / 2
        # Usable text area inside the device box, after the NODE_BORDER_RADIUS rounded corners eat
        # a few pixels at each end. Detail line is rendered at FONT_SIZE_SM so fits a few more chars.
        text_area_w = box_w - 2 * self.NODE_BORDER_RADIUS
        if parent_name:
            display_name = self._fit_text(parent_name, text_area_w)
            link = dwg.a(href=parent_url, target="_top")
            name_el = dwg.text(
                display_name,
                insert=(text_cx, text_center_y - self.TEXT_LINE_SPACING / 2 + self.TEXT_VERTICAL_OFFSET),
                text_anchor="middle",
                fill=self.COLOR_LINK,
                font_size=f"{self.FONT_SIZE}px",
                font_family=self.FONT_FAMILY,
                font_weight="bold",
            )
            if display_name != parent_name:
                name_el.set_desc(title=parent_name)
            link.add(name_el)
            dwg.add(link)
        if parent_detail:
            display_detail = self._fit_text(parent_detail, text_area_w, font_size=self.FONT_SIZE_SM)
            detail_el = dwg.text(
                display_detail,
                insert=(text_cx, text_center_y + self.TEXT_LINE_SPACING / 2 + self.TEXT_VERTICAL_OFFSET),
                text_anchor="middle",
                fill=self.COLOR_TEXT_MUTED,
                font_size=f"{self.FONT_SIZE_SM}px",
                font_family=self.FONT_FAMILY,
            )
            if display_detail != parent_detail:
                detail_el.set_desc(title=parent_detail)
            dwg.add(detail_el)

    def _draw_node(self, dwg, cx, y, termination, term_position="top", is_last=False):
        """Draw a device node with one termination box (top or bottom)."""
        half_term_h = self.TERM_H / 2

        if term_position == "top":
            term_y = y
            box_y = y + half_term_h
            text_area_top = box_y + half_term_h
            text_area_h = self.NODE_H - self.TERM_H
            total_bottom = box_y + self.NODE_H
        else:
            box_y = y
            term_y = y + self.NODE_H - half_term_h
            text_area_top = box_y
            text_area_h = self.NODE_H - self.TERM_H
            total_bottom = term_y + self.TERM_H

        self._draw_device_box(
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

    def _draw_grouped_node_cell(self, dwg, y, cell, col_centers):
        """Draw a device box spanning multiple columns with side-by-side termination boxes at top."""
        terminations = cell["terminations"]
        start_col = cell["col"]
        colspan = cell["colspan"]
        half_term_h = self.TERM_H / 2

        first_cx = col_centers[start_col]
        last_cx = col_centers[start_col + colspan - 1]
        group_cx = (first_cx + last_cx) / 2

        box_w = (last_cx - first_cx) + self.TERM_W + self.GAP_Y * 2
        box_x = first_cx - self.TERM_W / 2 - self.GAP_Y
        box_y = y + half_term_h
        text_area_top = box_y + half_term_h
        text_area_h = self.NODE_H - self.TERM_H

        self._draw_device_box(
            dwg,
            box_x,
            box_y,
            box_w,
            self.NODE_H,
            group_cx,
            text_area_top,
            text_area_h,
            terminations[0],
        )
        for term_index, termination in enumerate(terminations):
            self._draw_termination_box(dwg, col_centers[start_col + term_index], y, termination)

        return box_y + self.NODE_H

    def _draw_cable(self, dwg, cx, y, cable, near_end=None, far_end=None):
        """Draw a cable segment with color bar, label, breakout lane info, and status badge."""
        cable_color = f"#{cable.color}" if cable.color else self.COLOR_CABLE_DEFAULT
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

        link = dwg.a(href=cable_url, target="_top")
        link.add(
            dwg.text(
                str(cable),
                insert=(label_x, label_y - self.TEXT_VERTICAL_OFFSET),
                fill=self.COLOR_LINK,
                font_size=f"{self.FONT_SIZE}px",
                font_family=self.FONT_FAMILY,
                font_weight="bold",
            )
        )
        dwg.add(link)

        # Breakout lane info (only for cables with a cable_type and both endpoints known).
        next_line_y = label_y + self.LABEL_OFFSET_X
        if cable.cable_type_id and near_end and far_end:
            near_row = self._cable_lane_info(cable, near_end)
            far_row = self._cable_lane_info(cable, far_end)
            if near_row is not None and near_row.connector is not None:
                breakout_text = f"Breakout: {near_row.cable_end}{near_row.connector}"
                if far_row is not None and far_row.connector is not None:
                    breakout_text += f" → {far_row.cable_end}{far_row.connector}"
                dwg.add(
                    dwg.text(
                        breakout_text,
                        insert=(label_x, next_line_y),
                        fill=self.COLOR_TEXT_MUTED,
                        font_size=f"{self.FONT_SIZE_SM}px",
                        font_family=self.FONT_FAMILY,
                    )
                )
                next_line_y += self.TEXT_LINE_SPACING + 2

        status = cable.status if hasattr(cable, "status") else None
        status_name = status.name if status else "Unknown"
        status_color = f"#{status.color}" if status and status.color else self.COLOR_TEXT_MUTED
        self._draw_status_badge(dwg, label_x, next_line_y, status_name, status_color)

        return y + bar_h

    def _draw_passthrough_node(self, dwg, cx, y, arriving_termination, departing_termination):
        """Draw a device node with arriving port at top and departing port at bottom."""
        half_term_h = self.TERM_H / 2
        text_area_h = self.TEXT_LINE_SPACING * 3
        box_h = half_term_h + text_area_h + half_term_h

        box_y = y + half_term_h
        departing_y = box_y + box_h - half_term_h
        text_area_top = box_y + half_term_h

        self._draw_device_box(
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

        text_width = len(status_name) * self.FONT_SIZE_SM * self.FONT_WIDTH_RATIO
        badge_w = text_width + 12
        badge_h = self.FONT_SIZE_SM + 6
        badge_r = 4

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
                font_size=f"{self.FONT_SIZE_SM}px",
                font_family=self.FONT_FAMILY,
                font_weight="bold",
            )
        )

    def _draw_termination_box(self, dwg, cx, y, termination):
        """Draw a single termination sub-box at the given position."""
        termination_x = cx - self.TERM_W / 2
        is_active = termination == self.origin
        termination_url = self._url(termination) if termination else "#"
        termination_name = str(termination)
        display_name = self._fit_text(termination_name, self.TERM_W - 2 * self.TERM_TEXT_PAD)

        border_color = self.COLOR_ACTIVE_BORDER if is_active else self.COLOR_TERM_BORDER
        border_width = 3 if is_active else 1

        dwg.add(
            dwg.rect(
                insert=(termination_x, y),
                size=(self.TERM_W, self.TERM_H),
                rx=self.TERM_BORDER_RADIUS,
                ry=self.TERM_BORDER_RADIUS,
                fill=self.COLOR_TERM_BG,
                stroke=border_color,
                stroke_width=border_width,
            )
        )
        link = dwg.a(href=termination_url, target="_top")
        text_el = dwg.text(
            display_name,
            insert=(cx, y + self.TERM_H / 2 + self.TEXT_VERTICAL_OFFSET),
            text_anchor="middle",
            fill=self.COLOR_LINK,
            font_size=f"{self.FONT_SIZE}px",
            font_family=self.FONT_FAMILY,
            font_weight="bold",
        )
        # Browser tooltip with the full name — useful when the rendered text was truncated.
        if display_name != termination_name:
            text_el.set_desc(title=termination_name)
        link.add(text_el)
        dwg.add(link)

    def _draw_trace_end(self, dwg, cx, y, incomplete=False):
        """Draw the trace completion indicator at the bottom of a finished trace."""
        text = "Trace completed" if not incomplete else "Trace incomplete"
        color = self.COLOR_SUCCESS if not incomplete else self.COLOR_DANGER

        y += self.TRACE_END_PADDING
        segment_count = len(self.traced_path)
        label = f"{text} • {segment_count} segment{'s' if segment_count != 1 else ''}"
        dwg.add(
            dwg.text(
                label,
                insert=(cx, y + self.FONT_SIZE),
                text_anchor="middle",
                fill=color,
                font_size=f"{self.FONT_SIZE}px",
                font_family=self.FONT_FAMILY,
                font_weight="bold",
            )
        )
        return y + self.TRACE_END_HEIGHT

    def _render_empty(self):
        """Render an empty/no-path SVG."""
        dwg = svgwrite.Drawing(size=(f"{self.COL_WIDTH}px", f"{self.EMPTY_HEIGHT}px"), debug=False)
        dwg.viewbox(0, 0, self.COL_WIDTH, self.EMPTY_HEIGHT)
        dwg.add(
            dwg.text(
                "No cable path found",
                insert=(self.COL_WIDTH / 2, self.EMPTY_HEIGHT / 2),
                text_anchor="middle",
                fill=self.COLOR_TEXT_MUTED,
                font_size=f"{self.FONT_SIZE}px",
                font_family=self.FONT_FAMILY,
            )
        )
        return mark_safe(dwg.tostring())  # noqa: S308
