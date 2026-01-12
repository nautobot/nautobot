from collections import OrderedDict

from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from nautobot.core.utils.data import render_jinja2
from nautobot.extras.models import CustomLink

register = template.Library()

LINK_BUTTON = '<a href="{}"{} class="btn btn-{}">{}</a>\n'
GROUP_BUTTON = (
    '<div class="dropdown d-inline-flex align-middle">\n'
    '<button type="button" class="btn btn-{} dropdown-toggle" data-bs-toggle="dropdown">\n'
    '{} <span class="mdi mdi-chevron-down" aria-hidden="true"></span>\n'
    "</button>\n"
    '<ul class="dropdown-menu float-end">\n'
    "{}</ul></div>\n"
)
GROUP_LINK = '<li><a class="dropdown-item" href="{}"{}>{}</a></li>\n'


@register.simple_tag(takes_context=True)
def custom_links(context, obj):
    """
    Render all applicable links for the given object.
    """
    content_type = ContentType.objects.get_for_model(obj)
    links = CustomLink.objects.filter(content_type=content_type)
    if not links:
        return ""

    # Pass select context data when rendering the CustomLink
    link_context = {
        "obj": obj,
        "debug": context.get("debug", False),  # django.template.context_processors.debug
        "request": context["request"],  # django.template.context_processors.request
        "user": context["user"],  # django.contrib.auth.context_processors.auth
        "perms": context["perms"],  # django.contrib.auth.context_processors.auth
    }
    template_code = mark_safe("")
    group_names = OrderedDict()

    for cl in links:
        # Organize custom links by group
        if cl.group_name and cl.group_name in group_names:
            group_names[cl.group_name].append(cl)
        elif cl.group_name:
            group_names[cl.group_name] = [cl]

        # Add non-grouped links
        else:
            try:
                text_rendered = render_jinja2(cl.text, link_context)
                if text_rendered:
                    link_rendered = render_jinja2(cl.target_url, link_context)
                    link_target = ' target="_blank"' if cl.new_window else ""
                    template_code += format_html(
                        LINK_BUTTON, link_rendered, link_target, cl.button_class_css_class, text_rendered
                    )
            except Exception as e:
                template_code += format_html(
                    '<a aria-disabled="true" class="btn btn-secondary disabled" title="{}">'
                    '<span class="mdi mdi-alert"></span> {}</a>\n',
                    e,
                    cl.name,
                )

    # Add grouped links to template
    for group, links in group_names.items():
        links_rendered = mark_safe("")

        for cl in links:
            try:
                text_rendered = render_jinja2(cl.text, link_context)
                if text_rendered:
                    link_target = ' target="_blank"' if cl.new_window else ""
                    link_rendered = render_jinja2(cl.target_url, link_context)
                    links_rendered += format_html(GROUP_LINK, link_rendered, link_target, text_rendered)
            except Exception as e:
                links_rendered += format_html(
                    '<li><a aria-disabled="true" class="disabled dropdown-item" title="{}"><span class="text-secondary">'
                    '<span class="mdi mdi-alert"></span> {}</span></a></li>',
                    e,
                    cl.name,
                )

        if links_rendered:
            template_code += format_html(GROUP_BUTTON, links[0].button_class_css_class, group, links_rendered)

    return template_code
