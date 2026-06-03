"""Shared constants for server-side DCIM SVG rendering (cable path trace, cable breakout, ...).

Colors are Bootstrap CSS theme variables rather than hard-coded hex, so an inline SVG embedded in a
page follows light/dark mode via `data-bs-theme` (the variables resolve against the document).
"""

# Typography
FONT_FAMILY = "var(--bs-font-sans-serif)"
FONT_SIZE = 14
FONT_SIZE_SM = 12
# Approximate average glyph width as a fraction of font size for sans-serif text. Used to estimate
# rendered text widths (no real font metrics are available server-side) for truncation and for
# reserving horizontal space; 0.65 covers uppercase-heavy strings.
FONT_WIDTH_RATIO = 0.65

# Bootstrap theme colors.
COLOR_BODY = "var(--bs-body-color)"
COLOR_BODY_BG = "var(--bs-body-bg)"
COLOR_SECONDARY = "var(--bs-secondary-color)"
COLOR_SECONDARY_BG = "var(--bs-secondary-bg)"
COLOR_TERTIARY = "var(--bs-tertiary-color)"
COLOR_TERTIARY_BG = "var(--bs-tertiary-bg)"
COLOR_BORDER = "var(--bs-border-color)"
COLOR_LINK = "var(--bs-link-color)"
COLOR_SUCCESS = "var(--bs-success)"
COLOR_DANGER = "var(--bs-danger)"
COLOR_WARNING = "var(--bs-warning)"
