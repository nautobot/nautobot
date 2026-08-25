import re

from django import template
from django.template.defaultfilters import time as format_time

from nautobot.core.formats import PreferredTimeFormat

register = template.Library()


@register.filter()
def preferred_time_milliseconds(value):
    """Render a time using the user's hour-cycle preference and millisecond precision."""
    rendered = format_time(value, PreferredTimeFormat("H:i:s.u"))
    if not rendered:
        return rendered
    return re.sub(r"(\.\d{3})\d{3}", r"\1", rendered)
