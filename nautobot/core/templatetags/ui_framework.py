from django import template
from django.utils.html import format_html_join

from nautobot.core.utils.lookup import get_view_for_model
from nautobot.core.views.utils import get_obj_from_context

register = template.Library()


@register.simple_tag(takes_context=True)
def render_tabs_labels(context, tabs):
    """Render the tab labels for each Tab in the given `tabs` with the given `context`."""
    if tabs is not None:
        return format_html_join("\n", "{}", ([tab.render_label_wrapper(context)] for tab in tabs))
    return ""


@register.simple_tag(takes_context=True)
def render_components(context, components):
    """Render each component in the given `components` with the given `context`."""
    if components is not None:
        return format_html_join("\n", "{}", ([component.render(context)] for component in components))
    return ""


@register.simple_tag(takes_context=True)
def render_detail_view_extra_buttons(context):
    """
    Render the "extra_buttons" if any from the base detail view associated with the context object.

    This makes it possible for "extra" tabs (such as Changelog and Notes, and any added by App TemplateExtensions)
    to automatically still render any `extra_buttons` defined by the base detail view, without the tab-specific views
    needing to explicitly inherit from the base view.
    """
    obj = get_obj_from_context(context)
    base_detail_view = get_view_for_model(obj)
    object_detail_content = getattr(base_detail_view, "object_detail_content", None)
    if object_detail_content is not None and object_detail_content.extra_buttons:
        return render_components(context, object_detail_content.extra_buttons)
    return ""
