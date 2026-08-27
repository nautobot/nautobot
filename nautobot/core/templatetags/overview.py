from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def resolve_overview(context, overview):
    """Resolve the given overview against the active render context.

    An overview is either an HTML string, a template file, or key/value pairs. HTML strings and key/value pairs
    arrive here as deferred callables awaiting a context. A template file is rendered by Django and needs no resolving.
    """
    return overview(context) if overview else None
