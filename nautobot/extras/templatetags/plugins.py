import logging

from django import template as template_
from django.conf import settings
from django.utils.html import format_html_join
from django.utils.safestring import mark_safe

from nautobot.core.ui.choices import SectionChoices
from nautobot.extras.plugins import Banner, TemplateExtension
from nautobot.extras.registry import registry

register = template_.Library()


logger = logging.getLogger(__name__)


def _get_registered_content(obj, method, template_context, return_html=True):
    """
    Given an object, TemplateExtension method name, and template context, return all relevant extensions' content.

    Returns:
        html (str): if return_html is True, a combined, rendered HTML string
        objects (list): else, a list of dicts indexed by app name and an incrementing counter
    """
    context = {
        "object": obj,
        "request": template_context["request"],
        "settings": template_context["settings"],
        "csrf_token": template_context["csrf_token"],
        "perms": template_context["perms"],
    }

    model_name = obj._meta.label_lower
    template_extensions = registry["plugin_template_extensions"].get(model_name, [])
    objects = []
    html = ""
    for template_extension in template_extensions:
        # If the class has not overridden the specified method, we can skip it (because we know it
        # will raise NotImplementedError).
        if getattr(template_extension, method) == getattr(TemplateExtension, method):
            continue

        # Update context with plugin-specific configuration parameters
        plugin_name = template_extension.__module__.split(".")[0]
        context["config"] = settings.PLUGINS_CONFIG.get(plugin_name, {})

        # Call the method to render content
        instance = template_extension(context)
        content = getattr(instance, method)()
        if not return_html:
            for i, content in enumerate(content):
                objects.append({f"{plugin_name}:{i + 1}": content})
        else:
            html += content

    if not return_html:
        return objects

    return mark_safe(html)  # noqa: S308  # suspicious-mark-safe-usage -- we have to trust plugins to provide safe HTML


def _get_registered_ui_content(obj, attr) -> list:
    """Given an object and TemplateExtension attribute name, return all relevant extensions' content.

    Example:
        >>> _get_registered_ui_content(device, "object_detail_tabs")
        [<nautobot.core.ui.object_detail.DistinctViewTab object at 0x7f0369419ac0>]

    Returns:
        objects (list): List of Tabs, Panels, etc. depending on the given attribute, sorted by weight.
    """
    model_name = obj._meta.label_lower
    template_extensions = registry["plugin_template_extensions"].get(model_name, [])
    objects = []
    for template_extension in template_extensions:
        content = getattr(template_extension, attr)
        if content is not None:
            objects.extend(content)

    return sorted(objects, key=lambda item: item.weight)


@register.simple_tag(takes_context=True)
def plugin_buttons(context, obj, view="detail"):
    """
    Render all buttons registered by plugins
    """
    if view == "list":
        # The object_list.html template passes content_type.model_class as obj
        # This is a bit of a hack however, _get_registered_content() only really needs the model in its own logic
        return _get_registered_content(obj, "list_buttons", context)

    html = format_html_join(
        " ", "{}", ([button.render(context)] for button in _get_registered_ui_content(obj, "object_detail_buttons"))
    )
    html += _get_registered_content(obj, "buttons", context)
    return html


@register.simple_tag(takes_context=True)
def plugin_left_page(context, obj):
    """
    Render all left page content registered by plugins
    """
    panels = [
        panel
        for panel in _get_registered_ui_content(obj, "object_detail_panels")
        if panel.section == SectionChoices.LEFT_HALF
    ]
    html = format_html_join("\n", "{}", ([panel.render(context)] for panel in panels))
    html += _get_registered_content(obj, "left_page", context)
    return html


@register.simple_tag(takes_context=True)
def plugin_right_page(context, obj):
    """
    Render all right page content registered by plugins
    """
    panels = [
        panel
        for panel in _get_registered_ui_content(obj, "object_detail_panels")
        if panel.section == SectionChoices.RIGHT_HALF
    ]
    html = format_html_join("\n", "{}", ([panel.render(context)] for panel in panels))
    html += _get_registered_content(obj, "right_page", context)
    return html


@register.simple_tag(takes_context=True)
def plugin_full_width_page(context, obj):
    """
    Render all full width page content registered by plugins
    """
    panels = [
        panel
        for panel in _get_registered_ui_content(obj, "object_detail_panels")
        if panel.section == SectionChoices.FULL_WIDTH
    ]
    html = format_html_join("\n", "{}", ([panel.render(context)] for panel in panels))
    html += _get_registered_content(obj, "full_width_page", context)
    return html


@register.inclusion_tag("extras/templatetags/plugin_object_detail_tabs.html", takes_context=True)
def plugin_object_detail_tabs(context, obj):
    """
    Render all custom tabs registered by plugins for the object detail view
    """
    context["ui_component_tabs"] = _get_registered_ui_content(obj, "object_detail_tabs")
    context["plugin_object_detail_tabs"] = _get_registered_content(obj, "detail_tabs", context, return_html=False)
    return context


@register.simple_tag(takes_context=True)
def plugin_object_detail_tab_content(context, obj):
    """
    Render the contents of UI Component Framework Tabs for the object detail view.
    """
    return format_html_join(
        "\n", "{}", ([tab.render(context)] for tab in _get_registered_ui_content(obj, "object_detail_tabs"))
    )


@register.inclusion_tag("extras/templatetags/plugin_banners.html", takes_context=True)
def plugin_banners(context):
    """
    Render all banners registered by plugins.
    """
    banners = []
    for banner_function in registry["plugin_banners"]:
        try:
            banner = banner_function(context)
        except Exception as exc:
            logger.error("Plugin banner function %s raised an exception: %s", banner_function, exc)
            continue

        if banner:
            if isinstance(banner, Banner):
                banners.append(banner)
            else:
                logger.error(
                    "Plugin banner function %s should return a Banner, but instead returned %s",
                    banner_function,
                    banner,
                )

    return {"banners": banners}
