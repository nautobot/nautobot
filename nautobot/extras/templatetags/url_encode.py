from django import template

from urllib.parse import urlencode

register = template.Library()


@register.simple_tag
def url_encode(val=None):
    return urlencode(val)
