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


def foreground_color(bg_color):
    """
    Return the ideal foreground color (black or white) for a given background color in hexadecimal RGB format.
    """
    bg_color = bg_color.strip("#")
    r, g, b = hex_to_rgb(bg_color)
    if r * 0.299 + g * 0.587 + b * 0.114 > 186:
        return "000000"
    else:
        return "ffffff"


def lighten_color(r, g, b, factor):
    """
    Make a given RGB color lighter (closer to white).
    """
    return [
        int(255 - (255 - r) * (1.0 - factor)),
        int(255 - (255 - g) * (1.0 - factor)),
        int(255 - (255 - b) * (1.0 - factor)),
    ]
