from collections import OrderedDict

from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.safestring import mark_safe

from nautobot.extras.models import CustomLink, ComputedField


register = template.Library()

LINK_BUTTON = '<a href="{}"{} class="btn btn-sm btn-{}">{}</a>\n'
GROUP_BUTTON = (
    '<div class="btn-group">\n'
    '<button type="button" class="btn btn-sm btn-{} dropdown-toggle" data-toggle="dropdown">\n'
    '{} <span class="caret"></span>\n'
    "</button>\n"
    '<ul class="dropdown-menu pull-right">\n'
    "{}</ul></div>\n"
)
GROUP_LINK = '<li><a href="{}"{}>{}</a></li>\n'


@register.simple_tag(takes_context=True)
def has_computed_fields(context, obj):
    """
    Return a boolean value indicating if an object's content type has associated computed fields.
    """
    content_type = ContentType.objects.get_for_model(obj)
    return bool(ComputedField.objects.filter(content_type=content_type))


@register.simple_tag(takes_context=True)
def computed_fields(context, obj):
    """
    Render all applicable links for the given object.
    """
    computed_fields = obj.get_computed_fields(label_as_key=True)
    if not computed_fields:
        return ""

    template_code = ""

    for label, value in computed_fields.items():
        template_code += f"""
        <tr>
            <td><span title="{label}">{label}</span></td>
            <td>{value}</td>
        <tr>
        """
    return mark_safe(template_code)
