import json

from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def to_json(value):
    """Filter to dump dict to json."""
    return mark_safe(json.dumps(value))
