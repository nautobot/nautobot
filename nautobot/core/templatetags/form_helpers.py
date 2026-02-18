import json
from urllib.parse import urlencode

from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


@register.inclusion_tag("utilities/render_field.html", takes_context=True)
def render_field(context, field, bulk_nullable=False):
    """
    Render a single form field from template
    """
    field_instance = getattr(field, "field", None)
    embedded_create = getattr(field_instance, "embedded_create", False)
    embedded_search = getattr(field_instance, "embedded_search", False)
    is_embedded = context.request.headers.get("HX-Request", False) == "true"
    has_embedded_create_permissions = context.request.user.has_perms(
        getattr(field_instance, "embedded_create_permissions", [])
    )

    embedded_create_query_params = []
    field_attributes = getattr(getattr(field_instance, "widget", None), "attrs", {})
    for attribute_name, attribute_value in field_attributes.items():
        # If field defines a specific content type(s), parse it and later use as initial value in embedded create form.
        if attribute_name in ("data-contenttype", "data-query-param-content_type", "data-query-param-content_types"):
            try:
                # Most content type field attributes are defined as JSON arrays of strings, e.g. `["dcim.location"]`.
                content_types = json.loads(attribute_value)
            except json.JSONDecodeError:
                content_types = [attribute_value]
            for content_type in content_types:
                try:
                    app_label, model = content_type.split(".")
                    # Need to map content type string to content type ID before passing it as initial form value.
                    content_type_id = ContentType.objects.get(app_label=app_label, model=model).id
                    # Note the difference between `content_type` and `content_types`.
                    query_param = (f"content_type{'s' if attribute_name.endswith('s') else ''}", content_type_id)
                    embedded_create_query_params.append(query_param)
                except (AttributeError, ObjectDoesNotExist, ValueError):
                    pass

    return {
        "field": field,
        "bulk_nullable": bulk_nullable,
        "should_render_embedded_create": embedded_create and not is_embedded and has_embedded_create_permissions,
        "should_render_embedded_search": embedded_search and not is_embedded,
        "embedded_create_query_string": urlencode(embedded_create_query_params),
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
