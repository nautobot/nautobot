from typing import Optional

from django.db.models import Model
from django.template import Context
from django.template.loader import get_template


def flatten_context(context) -> dict:
    """
    If the given context is already a dict, return it unmodified; if it is a Context, flatten it to a dict.

    This is working around a bug (not sure if in Django or in our code) where, if a `Context`'s `dicts` contain
    a `RequestContext`, calling `Context.flatten()` throws an exception.
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


def render_component_template(template_path: str, context: Context, **kwargs) -> str:
    """
    Render the template located at the given path with the given context, possibly augmented via additional kwargs.

    Args:
        template_path (str): Path to the template to render, for example `"components/tab/label_wrapper.html"`.
        context (Context): Rendering context for the template
        **kwargs (dict): Additional key/value pairs to extend the context with for this specific template.

    Examples:
        >>> render_component_template(self.label_wrapper_template_path, context, tab_id=self.tab_id, label="Hello")
    """
    with context.update(kwargs):
        return get_template(template_path).render(flatten_context(context))


def get_absolute_url(value: Optional[Model]) -> str:
    """
    Function to retrieve just absolute url to the given model instance.

    Args:
        value (Optional[django.db.models.Model]): Instance of a Django model or None.

    Returns:
        (str): url to the object if it defines get_absolute_url(), empty string otherwise.
    """
    if value is None:
        return ""

    if hasattr(value, "get_absolute_url"):
        try:
            return value.get_absolute_url()
        except AttributeError:
            return ""

    return ""
