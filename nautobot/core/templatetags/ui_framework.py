from django import template
from django.utils.html import format_html_join

register = template.Library()


@register.simple_tag(takes_context=True)
def object_detail_tabs(context):
    return context["object_detail_content"].render_tabs(context)


@register.simple_tag(takes_context=True)
def object_detail_tabs_content(context):
    return context["object_detail_content"].render_content(context)


@register.simple_tag(takes_context=True)
def render_components(context, components):
    return format_html_join("\n", "{}", ([component.render(context)] for component in components))
