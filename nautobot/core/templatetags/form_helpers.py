from urllib.parse import urlencode

from django import template
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist

register = template.Library()


@register.inclusion_tag("utilities/render_field.html", takes_context=True)
def render_field(context, field, bulk_nullable=False, container_class=None):
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
    embedded_search_query_params = []
    field_query_params = getattr(field_instance, "query_params", {})
    for query_param_name, query_param_value in field_query_params.items():
        # If field defines a specific content type(s), use it as initial value in embedded create and search forms.
        if query_param_name in ("content_type", "content_types"):
            # Some `content_types` query params are defined as lists of strings, e.g. `["dcim.location"]`, while others
            # may just be plain strings, e.g. `"dcim.location"`.
            content_types = query_param_value if isinstance(query_param_value, list) else [query_param_value]
            for content_type in content_types:
                try:
                    app_label, model = content_type.split(".")
                    # Need to map content type string to content type ID before passing it as initial form value.
                    content_type_id = ContentType.objects.get(app_label=app_label, model=model).id
                    embedded_create_query_params.append((query_param_name, content_type_id))
                    # For search form, additionally prefix content type param with `initial_` to avoid confusion with
                    # `content_type` param indicating the model of filterset form to render, not related to form values.
                    embedded_search_query_params.append((query_param_name, content_type))
                except (AttributeError, ObjectDoesNotExist, ValueError):
                    pass

    embedded_search_content_type = ""
    try:
        embedded_search_content_type = field_instance.queryset.model._meta.label_lower
    except AttributeError:
        pass

    return {
        "field": field,
        "bulk_nullable": bulk_nullable,
        "should_render_embedded_create": embedded_create and not is_embedded and has_embedded_create_permissions,
        "should_render_embedded_search": embedded_search and not is_embedded,
        "embedded_create_query_string": urlencode(embedded_create_query_params),
        "embedded_search_query_string": urlencode(embedded_search_query_params),
        "embedded_search_content_type": embedded_search_content_type,
        "container_class": container_class,
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
