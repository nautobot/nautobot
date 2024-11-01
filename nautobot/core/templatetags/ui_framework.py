from django import template
from django.utils.html import format_html_join

from nautobot.core.ui.object_detail import TemplateExtensionTab
from nautobot.core.views.utils import get_obj_from_context
from nautobot.extras.templatetags.plugins import get_registered_content

register = template.Library()


@register.simple_tag(takes_context=True)
def render_tabs_labels(context, object_detail_content):
    """Render the tab labels for each Tab in the given `object_detail_content` with the given `context`."""
    tabs = object_detail_content.tabs(context)
    obj = get_obj_from_context(context)
    if context["perms"]["extras"]["view_note"] and hasattr(obj, "get_notes_url"):
        tabs.append(TemplateExtensionTab(weight=0, label="Notes", tab_id="notes", url=obj.get_notes_url()))
    if context["perms"]["extras"]["view_objectchange"] and hasattr(obj, "get_changelog_url"):
        tabs.append(TemplateExtensionTab(weight=0, label="Change Log", tab_id="changelog", url=obj.get_changelog_url()))
    legacy_tabs = get_registered_content(obj, "detail_tabs", context, return_html=False)
    for tabs_list in legacy_tabs:
        for tab_id, tab in tabs_list.items():
            tabs.append(TemplateExtensionTab(weight=0, label=tab["title"], url=tab["url"], tab_id=tab_id))
    if tabs is not None:
        return format_html_join("\n", "{}", ([tab.render_label_wrapper(context)] for tab in tabs))
    return ""


@register.simple_tag(takes_context=True)
def render_tabs_content(context, object_detail_content):
    """Render the tab contents for each Tab in the given `object_detail_content` with the given `context`."""
    return render_components(context, object_detail_content.tabs(context))


@register.simple_tag(takes_context=True)
def render_components(context, components):
    """Render each component in the given `components` with the given `context`."""
    if components is not None:
        return format_html_join("\n", "{}", ([component.render(context)] for component in components))
    return ""
