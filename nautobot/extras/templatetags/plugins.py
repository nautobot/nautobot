import logging

from django import template as template_
from django.conf import settings
from django.utils.safestring import mark_safe

from nautobot.extras.plugins import PluginBanner, PluginTemplateExtension
from nautobot.extras.registry import registry

register = template_.Library()


logger = logging.getLogger("nautobot.plugins")


def _get_registered_content(obj, method, template_context):
    """
    Given an object and a PluginTemplateExtension method name and the template context, return all the
    registered content for the object's model.
    """
    html = ""
    context = {
        "object": obj,
        "request": template_context["request"],
        "settings": template_context["settings"],
        "csrf_token": template_context["csrf_token"],
        "perms": template_context["perms"],
    }

    model_name = obj._meta.label_lower
    template_extensions = registry["plugin_template_extensions"].get(model_name, [])
    for template_extension in template_extensions:

        # If the class has not overridden the specified method, we can skip it (because we know it
        # will raise NotImplementedError).
        if getattr(template_extension, method) == getattr(PluginTemplateExtension, method):
            continue

        # Update context with plugin-specific configuration parameters
        plugin_name = template_extension.__module__.split(".")[0]
        context["config"] = settings.PLUGINS_CONFIG.get(plugin_name, {})

        # Call the method to render content
        instance = template_extension(context)
        content = getattr(instance, method)()
        html += content

    return mark_safe(html)


@register.simple_tag(takes_context=True)
def plugin_buttons(context, obj):
    """
    Render all buttons registered by plugins
    """
    return _get_registered_content(obj, "buttons", context)


@register.simple_tag(takes_context=True)
def plugin_left_page(context, obj):
    """
    Render all left page content registered by plugins
    """
    return _get_registered_content(obj, "left_page", context)


@register.simple_tag(takes_context=True)
def plugin_right_page(context, obj):
    """
    Render all right page content registered by plugins
    """
    return _get_registered_content(obj, "right_page", context)


@register.simple_tag(takes_context=True)
def plugin_full_width_page(context, obj):
    """
    Render all full width page content registered by plugins
    """
    return _get_registered_content(obj, "full_width_page", context)


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
            if isinstance(banner, PluginBanner):
                banners.append(banner)
            else:
                logger.error(
                    "Plugin banner function %s should return a PluginBanner, but instead returned %s",
                    banner_function,
                    banner,
                )

    return {"banners": banners}
