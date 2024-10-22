from django import template
from django.utils.html import format_html_join

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
