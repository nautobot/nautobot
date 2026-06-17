from django import template
from django_jinja import library

from nautobot.dcim.constants import CABLE_TERMINATION_GENERIC_ICON, DEVICE_COMPONENT_ICONS

register = template.Library()


@library.filter()
@register.filter()
def termination_type_icon(termination):
    """Return an MDI icon class string for a cable termination object or modelname based on its type."""
    if termination is None:
        return "mdi-help-circle-outline"
    if isinstance(termination, str):
        model_name = termination
    else:
        model_name = termination._meta.model_name
    return DEVICE_COMPONENT_ICONS.get(model_name, CABLE_TERMINATION_GENERIC_ICON)
