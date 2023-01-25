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
def render_form(form):
    """
    Render an entire form from template
    """
    return {
        "form": form,
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
