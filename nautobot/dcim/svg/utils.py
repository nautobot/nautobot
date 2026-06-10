"""Shared helpers for server-side DCIM SVG rendering."""

from nautobot.dcim.svg.constants import FONT_WIDTH_RATIO


def estimate_text_width(text, font_size, ratio=FONT_WIDTH_RATIO):
    """Estimate the rendered width (px) of `text` at `font_size` using a fraction-of-em heuristic.

    No real font metrics are available server-side, so this is an approximation; callers reserving
    space from it should leave a small safety margin.
    """
    return len(text) * font_size * ratio


def fit_text(text, max_width, font_size, ratio=FONT_WIDTH_RATIO):
    """Truncate `text` with an ellipsis if its estimated width exceeds `max_width` px.

    Returns the (possibly truncated) string. When truncation occurs, callers should attach the full
    text as a `<title>` tooltip so the complete value stays discoverable.
    """
    if not text:
        return ""
    max_chars = max(int(max_width / (font_size * ratio)), 1)
    if len(text) <= max_chars:
        return text
    # Reserve one slot for the ellipsis glyph.
    return text[: max(max_chars - 1, 1)] + "…"
