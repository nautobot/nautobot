from django.template.loader import get_template


def flatten_context(context) -> dict:
    """
    If the given context is already a dict, return it unmodified; if it is a Context, flatten it to a dict.

    This is working around a bug (not sure if in Django or in our code) where, if the Context layers of `dicts` contain
    a RequestContext, calling `Context.flatten()` throws an exception.
    """
    if isinstance(context, dict):
        return context
    flat = {}
    for d in context.dicts:
        if isinstance(d, dict):
            flat.update(d)
        else:
            flat.update(flatten_context(d))
    return flat


def render_component_template(template_path: str, context, **kwargs):
    """
    Render the template located at the given path with the given context, possibly augmented via additional kwargs.
    """
    with context.update(kwargs):
        return get_template(template_path).render(flatten_context(context))
