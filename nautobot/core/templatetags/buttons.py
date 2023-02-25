from django import template
from django.urls import NoReverseMatch, reverse

from nautobot.core.views import utils as views_utils
from nautobot.core.utils import lookup
from nautobot.extras import models

register = template.Library()


#
# Instance buttons
#


@register.inclusion_tag("buttons/clone.html")
def clone_button(instance):
    try:
        url = reverse(lookup.get_route_for_model(instance, "add"))
    except NoReverseMatch:
        return {"url": None}

    # Populate cloned field values
    param_string = views_utils.prepare_cloned_fields(instance)
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
        use_pk: If True, use the primary key instead of any specified "key" field. (Deprecated, use `key="pk"` instead)
        key: The attribute on the model to use for reverse URL lookup.
    """
    viewname = lookup.get_route_for_model(instance, "edit")

    # Assign kwargs
    if hasattr(instance, key) and not use_pk:
        kwargs = {key: getattr(instance, key)}
    else:
        kwargs = {"pk": instance.pk}

    try:
        url = reverse(viewname, kwargs=kwargs)
    except NoReverseMatch:
        return {"url": None}

    return {
        "url": url,
    }


@register.inclusion_tag("buttons/delete.html")
def delete_button(instance, use_pk=False, key="slug"):
    """
    Render a button to delete a model instance.

    Args:
        instance: Model record.
        use_pk: If True, use the primary key instead of any specified "key" field. (Deprecated, use `key="pk"` instead)
        key: The attribute on the model to use for reverse URL lookup.
    """
    viewname = lookup.get_route_for_model(instance, "delete")

    # Assign kwargs
    if hasattr(instance, key) and not use_pk:
        kwargs = {key: getattr(instance, key)}
    else:
        kwargs = {"pk": instance.pk}

    try:
        url = reverse(viewname, kwargs=kwargs)
    except NoReverseMatch:
        return {"url": None}

    return {
        "url": url,
    }


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
        export_templates = models.ExportTemplate.objects.restrict(user, "view").filter(content_type=content_type)
    else:
        export_templates = []

    return {
        "url_params": context["request"].GET,
        "export_templates": export_templates,
    }
