from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html_join

from nautobot.extras.models import ComputedField

register = template.Library()


@register.simple_tag(takes_context=True)
def has_computed_fields(context, obj):
    """
    Return a boolean value indicating if an object's content type has associated computed fields.
    """
    content_type = ContentType.objects.get_for_model(obj)
    return ComputedField.objects.filter(content_type=content_type).exists()


@register.simple_tag(takes_context=True)
def computed_fields(context, obj, advanced_ui=None):
    """
    Render all applicable links for the given object.
    This can also check whether the advanced_ui attribute is True or False for UI display purposes.
    """
    fields = obj.get_computed_fields(label_as_key=True, advanced_ui=advanced_ui)
    if not computed_fields:
        return ""

    return format_html_join(
        "\n",
        '<tr><td><span title="{}">{}</span></td><td>{}</td></tr>',
        ((label, label, value) for label, value in fields.items()),
    )
