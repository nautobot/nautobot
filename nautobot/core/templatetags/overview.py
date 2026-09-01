from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def resolve_overview(context, overview):
    """Resolve the given overview against the active render context.

    An overview is a callable, taking the render context, that returns either an HTML string or key/value pairs.
    """
    return overview(context) if overview else None
