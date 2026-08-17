"""Utilities for working with colors."""


def hex_to_rgb(hex_str):
    """
    Map a hex string like "00ff00" to individual r, g, b integer values.
    """
    return [int(hex_str[c : c + 2], 16) for c in (0, 2, 4)]


def rgb_to_hex(r, g, b):
    """
    Map r, g, b values to a hex string.
    """
    return "%02x%02x%02x" % (r, g, b)  # pylint: disable=consider-using-f-string


def relative_luminance(r, g, b):
    """
    Return the WCAG relative luminance of an sRGB color, as defined in WCAG 2.1.

    Args:
        r (int): Red channel, 0-255.
        g (int): Green channel, 0-255.
        b (int): Blue channel, 0-255.

    Returns:
        (float): Relative luminance in the range 0.0 (black) to 1.0 (white).

    See: https://www.w3.org/TR/WCAG21/#dfn-relative-luminance
    """

    def linearize(channel):
        srgb = channel / 255
        return srgb / 12.92 if srgb <= 0.03928 else ((srgb + 0.055) / 1.055) ** 2.4

    return 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)


def contrast_ratio(color_a, color_b):
    """
    Return the WCAG contrast ratio between two colors in hexadecimal RGB format.

    Args:
        color_a (str): Color in RRGGBB format, with or without a leading `#`.
        color_b (str): Color in RRGGBB format, with or without a leading `#`.

    Returns:
        (float): Contrast ratio in the range 1.0 (identical) to 21.0 (black against white).

    See: https://www.w3.org/TR/WCAG21/#dfn-contrast-ratio
    """
    luminance_a = relative_luminance(*hex_to_rgb(color_a.strip("#")))
    luminance_b = relative_luminance(*hex_to_rgb(color_b.strip("#")))
    lighter, darker = max(luminance_a, luminance_b), min(luminance_a, luminance_b)
    return (lighter + 0.05) / (darker + 0.05)


def foreground_color(bg_color):
    """
    Return the ideal foreground color (black or white) for a given background color in hexadecimal RGB format.

    Picks whichever of black or white has the greater WCAG contrast ratio against the background.
    """
    bg_color = bg_color.strip("#")
    return "000000" if contrast_ratio(bg_color, "000000") >= contrast_ratio(bg_color, "ffffff") else "ffffff"


def lighten_color(r, g, b, factor):
    """
    Make a given RGB color lighter (closer to white).
    """
    return [
        int(255 - (255 - r) * (1.0 - factor)),
        int(255 - (255 - g) * (1.0 - factor)),
        int(255 - (255 - b) * (1.0 - factor)),
    ]
