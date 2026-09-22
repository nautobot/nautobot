from django import template
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from django.utils.safestring import mark_safe

from nautobot.core.utils.data import render_jinja2
from nautobot.extras.choices import ButtonClassChoices
from nautobot.extras.models import CustomLink

register = template.Library()

DISABLED_DROPDOWN_LINK = '<li><a aria-disabled="true" class="disabled dropdown-item{css_class}" title="{title}"><span class="text-secondary"><span aria-hidden="true" class="mdi mdi-alert me-4"></span>{text}</span></a></li>\n'
DISABLED_LINK_BUTTON = '<a aria-disabled="true" class="btn btn-secondary disabled{css_class}" title="{title}"><span aria-hidden="true" class="mdi mdi-alert me-4"></span>{text}</a>\n'
DROPDOWN_DIVIDER = '<li><hr class="dropdown-divider"></li>\n'
DROPDOWN_GROUP = '<li><h6 class="dropdown-header"><span aria-hidden="true" class="mdi mdi-folder-outline me-4"></span>{text}</h6></li>\n{links}\n'
DROPDOWN_LINK = '<li><a class="dropdown-item{css_class}" href="{href}"{target}>{text}</a></li>\n'
DROPDOWN_TRIGGER = """
    <button type="button" class="btn btn-{css_class} dropdown-toggle" data-bs-toggle="dropdown">
        <span aria-hidden="true" class="mdi mdi-link-variant me-4"></span>{text}<span aria-hidden="true" class="mdi mdi-chevron-down ms-4"></span>
    </button>
"""
DROPDOWN = f"""
    <div class="dropdown d-inline-flex align-middle">
        {DROPDOWN_TRIGGER}
        <ul class="dropdown-menu float-end">
            {{links}}
        </ul>
    </div>
"""
LINK_BUTTON = '<a href="{href}"{target} class="btn{css_class}"><span aria-hidden="true" class="mdi mdi-link-variant me-4"></span>{text}</a>\n'


@register.simple_tag(takes_context=True)
def custom_links(context, obj):
    """
    Render all applicable links for the given object.
    """
    content_type = ContentType.objects.get_for_model(obj)
    links = CustomLink.objects.filter(content_type=content_type)

    # Pass select context data when rendering the CustomLink
    link_context = {
        "obj": obj,
        "debug": context.get("debug", False),  # django.template.context_processors.debug
        "request": context["request"],  # django.template.context_processors.request
        "user": context["user"],  # django.contrib.auth.context_processors.auth
        "perms": context["perms"],  # django.contrib.auth.context_processors.auth
    }

    resolved_links = []
    for cl in links:
        try:
            text_rendered = render_jinja2(cl.text, link_context)
            if text_rendered:
                resolved_links.append((cl, text_rendered, render_jinja2(cl.target_url, link_context), None))
        except Exception as e:
            resolved_links.append((cl, cl.name, None, e))

    if not resolved_links:
        return ""

    first_link = resolved_links[0][0]
    is_single_link_or_group = len(resolved_links) == 1 or (
        bool(first_link.group_name) and all(cl.group_name == first_link.group_name for cl, *_ in resolved_links)
    )

    def render_custom_link(resolved_link, grouped=False):
        cl, text, href, error = resolved_link
        if error is None:
            css_class = ""
            if is_single_link_or_group and not grouped:
                css_class += f" btn-{cl.button_class_css_class}"
            if not is_single_link_or_group and grouped:
                # Links grouped within a unified dropdown are subject to additional indentation.
                css_class += " ps-24"
            if not is_single_link_or_group and cl.button_class not in (
                ButtonClassChoices.CLASS_DEFAULT,
                ButtonClassChoices.CLASS_LINK,
            ):
                # `CLASS_DEFAULT` (`secondary`) is the default case in which it is better to use standard black instead
                # of gray text, and `text-link` class, interpolated from `CLASS_LINK`, simply does not exist.
                css_class += f" text-{cl.button_class_css_class}"
            format_kwargs = {
                "css_class": css_class,
                "href": href,
                "target": mark_safe(' target="_blank"') if cl.new_window else "",
                "text": text,
            }
            format_template = LINK_BUTTON if is_single_link_or_group and not grouped else DROPDOWN_LINK
        else:
            format_kwargs = {
                "css_class": " ps-24" if not is_single_link_or_group and grouped else "",
                "title": error,
                "text": text,
            }
            if is_single_link_or_group and not grouped:
                format_template = DISABLED_LINK_BUTTON
            else:
                format_template = DISABLED_DROPDOWN_LINK

        return format_html(format_template, **format_kwargs)

    template_code = mark_safe("")
    group_names = {}

    for resolved_link in resolved_links:
        cl = resolved_link[0]

        # Organize custom links by group
        if cl.group_name and cl.group_name in group_names:
            group_names[cl.group_name].append(resolved_link)
        elif cl.group_name:
            group_names[cl.group_name] = [resolved_link]

        # Add non-grouped links
        else:
            template_code += render_custom_link(resolved_link)

    # Add grouped links to template
    for group, group_links in group_names.items():
        links_rendered = mark_safe("")

        for resolved_link in group_links:
            links_rendered += render_custom_link(resolved_link, grouped=True)

        format_template = DROPDOWN if is_single_link_or_group else DROPDOWN_GROUP
        format_kwargs = {
            "css_class": group_links[0][0].button_class_css_class,
            "links": links_rendered,
            "text": group,
        }
        # Put a line separator between the group and whatever was rendered before it.
        if template_code:
            format_template = DROPDOWN_DIVIDER + format_template
        template_code += format_html(format_template, **format_kwargs)

    if not is_single_link_or_group:
        format_kwargs = {"css_class": "secondary", "links": template_code, "text": "Links"}
        format_template = DROPDOWN
        template_code = format_html(format_template, **format_kwargs)

    return template_code
