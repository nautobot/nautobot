import logging

from django import template
from django.utils.html import format_html_join

from nautobot.core.ui.breadcrumbs import Breadcrumbs
from nautobot.core.ui.titles import Titles
from nautobot.core.utils.lookup import get_view_for_model
from nautobot.core.views.utils import get_obj_from_context

logger = logging.getLogger(__name__)

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
def render_title(context, mode="plain"):
    title_obj = context.get("view_titles")
    if title_obj is not None and isinstance(title_obj, Titles):
        return title_obj.render(context, mode=mode)

    if fallback_title := context.get("title"):
        return fallback_title
    return ""


@register.simple_tag(takes_context=True)
def render_breadcrumbs(context):
    breadcrumbs_obj = context.get("breadcrumbs")
    if breadcrumbs_obj is not None and isinstance(breadcrumbs_obj, Breadcrumbs):
        return breadcrumbs_obj.render(context)
    return ""


@register.simple_tag(takes_context=True)
def render_detail_view_extra_buttons(context):
    """
    Render the "extra_buttons" from the context's object_detail_content, or as fallback, from the base detail view.

    This makes it possible for "extra" tabs (such as Changelog and Notes, and any added by App TemplateExtensions)
    to automatically still render any `extra_buttons` defined by the base detail view, without the tab-specific views
    needing to explicitly inherit from the base view.
    """
    object_detail_content = context.get("object_detail_content")
    if object_detail_content is None:
        obj = get_obj_from_context(context)
        if obj is None:
            logger.error("No 'obj' or 'object' found in the render context!")
            return ""
        base_detail_view = get_view_for_model(obj)
        if base_detail_view is None:
            logger.warning(
                "Unable to identify the base detail view - check that it has a valid name, i.e. %sUIViewSet or %sView",
                type(obj).__name__,
                type(obj).__name__,
            )
            return ""
        object_detail_content = getattr(base_detail_view, "object_detail_content", None)
    if object_detail_content is not None and object_detail_content.extra_buttons:
        return render_components(context, object_detail_content.extra_buttons)
    return ""
