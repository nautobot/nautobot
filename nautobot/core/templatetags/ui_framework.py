
from django import template

register = template.Library()

@register.simple_tag(takes_context=True)
def object_detail_tabs(context):
    return context["object_detail_content"].render_tabs(request=context["request"], instance=context["object"])


@register.simple_tag(takes_context=True)
def object_detail_tabs_content(context):
    return context["object_detail_content"].render_content(request=context["request"], instance=context["object"])
