from django import template

register = template.Library()


@register.inclusion_tag("utilities/render_field.html")
def render_field(field, bulk_nullable=False):
    """
    Render a single form field from template
    """
    return {
        "field": field,
        "bulk_nullable": bulk_nullable,
    }


@register.inclusion_tag("utilities/render_custom_fields.html")
def render_custom_fields(form):
    """
    Render all custom fields in a form
    """
    return {
        "form": form,
    }


@register.inclusion_tag("utilities/render_relationships.html")
def render_relationships(form):
    """
    Render all relationships in a form
    """
    return {
        "form": form,
    }


@register.inclusion_tag("utilities/render_form.html")
def render_form(form, excluded_fields=None):
    """
    Render an entire form from template and default to skipping over `tags` and `object_note` fields.
    Setting `excluded_fields` to [] prevents skipping over `tags` and `object_note` fields
    in case they are used as Job variables or DynamicGroup filters.
    See:
    https://github.com/nautobot/nautobot/issues/4473
    https://github.com/nautobot/nautobot/issues/4503
    """
    if excluded_fields is None:
        excluded_fields = ["tags", "dynamic_groups", "object_note"]

    return {
        "form": form,
        "excluded_fields": excluded_fields,
    }


@register.filter(name="widget_type")
def widget_type(field):
    """
    Return the widget type
    """
    if hasattr(field, "widget"):
        return field.widget.__class__.__name__.lower()
    elif hasattr(field, "field"):
        return field.field.widget.__class__.__name__.lower()
    else:
        return None
