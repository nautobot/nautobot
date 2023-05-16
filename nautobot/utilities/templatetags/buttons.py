from django import template
from django.urls import reverse, NoReverseMatch

from nautobot.extras.models import ExportTemplate
from nautobot.utilities.utils import prepare_cloned_fields, get_route_for_model

register = template.Library()


#
# Instance buttons
#


@register.inclusion_tag("buttons/clone.html")
def clone_button(instance):
    try:
        url = reverse(get_route_for_model(instance, "add"))
    except NoReverseMatch:
        return {"url": None}

    # Populate cloned field values
    param_string = prepare_cloned_fields(instance)
    if param_string:
        url = f"{url}?{param_string}"

    return {
        "url": url,
    }


@register.inclusion_tag("buttons/edit.html")
def edit_button(instance, use_pk=False, key="slug"):
    """
    Render a button to edit a model instance.

    Args:
        instance: Model record.
        use_pk: Used for backwards compatibility, no-op in this function.
        key: Used for backwards compatibility, no-op in this function.
    """
    viewname = get_route_for_model(instance, "edit")

    # We try different lookups to get a valid reverse url
    lookups = ["pk", "slug", "key"]

    for lookup in lookups:
        if hasattr(instance, lookup):
            kwargs = {lookup: getattr(instance, lookup)}
            try:
                url = reverse(viewname, kwargs=kwargs)
                return {"url": url}
            except NoReverseMatch:
                continue

    return {"url": None}


@register.inclusion_tag("buttons/delete.html")
def delete_button(instance, use_pk=False, key="slug"):
    """
    Render a button to delete a model instance.

    Args:
        instance: Model record.
        use_pk: Used for backwards compatibility, no-op in this function.
        key: Used for backwards compatibility, no-op in this function.
    """
    viewname = get_route_for_model(instance, "delete")

    # We try different lookups to get a valid reverse url
    lookups = ["pk", "slug", "key"]

    for lookup in lookups:
        if hasattr(instance, lookup):
            kwargs = {lookup: getattr(instance, lookup)}
            try:
                url = reverse(viewname, kwargs=kwargs)
                return {"url": url}
            except NoReverseMatch:
                continue

    return {"url": None}


#
# List buttons
#


@register.inclusion_tag("buttons/add.html")
def add_button(url):
    try:
        url = reverse(url)
    except NoReverseMatch:
        return {"add_url": None}

    return {
        "add_url": url,
    }


@register.inclusion_tag("buttons/import.html")
def import_button(url):
    return {
        "import_url": url,
    }


@register.inclusion_tag("buttons/export.html", takes_context=True)
def export_button(context, content_type=None):
    if content_type is not None:
        user = context["request"].user
        export_templates = ExportTemplate.objects.restrict(user, "view").filter(content_type=content_type)
    else:
        export_templates = []

    return {
        "url_params": context["request"].GET,
        "export_templates": export_templates,
    }
