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


@library.filter()
@register.filter()
def breakout_trunk_child_interface(endpoint, near_termination):
    """The breakout-trunk child (sub)interface mapping a connected `endpoint` back to `near_termination`.

    Template-friendly wrapper for `CableTermination.get_breakout_trunk_child_interface_for_endpoint`
    (templates can't call model methods with arguments). Used to annotate a connection endpoint with
    the remote trunk's child interface even when the breakout cable is reached through patch-panel
    front/rear ports. Returns `None` when there is no such mapping.
    """
    if endpoint is None or near_termination is None:
        return None
    return near_termination.get_breakout_trunk_child_interface_for_endpoint(endpoint)


@library.filter()
@register.filter()
def breakout_subinterface_for_path(cable_path):
    """The breakout-trunk child (sub)interface mapped to a `CablePath`'s lane, or None.

    Labels each row of the cable-trace view's "Related Paths" table with the specific subinterface
    when the path originates on a breakout trunk (one path per fan-out lane). Returns None for paths
    that don't originate on a breakout-trunk interface.
    """
    origin = getattr(cable_path, "origin", None)
    if origin is None or not hasattr(origin, "get_breakout_child_interface_for_connector"):
        return None
    return origin.get_breakout_child_interface_for_connector(cable_path.peer_connector)
