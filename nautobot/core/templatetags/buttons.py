from django import template
from django.urls import NoReverseMatch, reverse

from nautobot.core.utils import lookup
from nautobot.core.views import utils as views_utils
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
        instance (BaseModel): Model record.
        use_pk (bool): Used for backwards compatibility, no-op in this function.
        key (str): Used for backwards compatibility, no-op in this function.
    """
    viewname = lookup.get_route_for_model(instance, "edit")

    # We try different lookups to get a valid reverse url
    lookup_keys = ["pk", "slug", "key"]

    for lookup_key in lookup_keys:
        if hasattr(instance, lookup_key):
            kwargs = {lookup_key: getattr(instance, lookup_key)}
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
        instance (BaseModel): Model record.
        use_pk (bool): Used for backwards compatibility, no-op in this function.
        key (str): Used for backwards compatibility, no-op in this function.
    """
    viewname = lookup.get_route_for_model(instance, "delete")

    # We try different lookups to get a valid reverse url
    lookup_keys = ["pk", "slug", "key"]

    for lookup_key in lookup_keys:
        if hasattr(instance, lookup_key):
            kwargs = {lookup_key: getattr(instance, lookup_key)}
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
def add_button(url, verbose_name=None, list_element=False):
    """Display an Add Button/List Element on the page.

    This allows an Add Button to either be displayed on a page or within a Button Group.
    Args:
        url (str): URL for the object's create page.
        verbose_name (str, optional): Append the verbose_name to the button text.
        list_element (bool, optional): Render as a <li> element instead of a button. Defaults to False.
    """
    try:
        url = reverse(url)
    except NoReverseMatch:
        return {"add_url": None, "list_element": list_element, "verbose_name": verbose_name}

    return {
        "add_url": url,
        "list_element": list_element,
        "verbose_name": verbose_name,
    }


@register.inclusion_tag("buttons/import.html")
def import_button(url):  # 3.0 TODO: remove, unused
    """Deprecated - use job_import_button instead."""
    return {
        "import_url": url,
    }


@register.simple_tag
def job_import_url(content_type):
    """
    URL to the run view for the CSV Import system job, prefilled with the given content-type.

    Helper to `job_import_button` tag, but can be used separately if needed.
    """
    try:
        import_url = reverse("extras:job_run_by_class_path", kwargs={"class_path": "nautobot.core.jobs.ImportObjects"})
        import_url += f"?content_type={content_type.id}"
    except NoReverseMatch:
        import_url = None
    return import_url


@register.inclusion_tag("buttons/job_import.html")
def job_import_button(content_type, list_element=False):
    """Display an Import Button/List Element on the page.

    This allows an Import Button to either be displayed on a page or within a Button Group.
    Args:
        content_type (str): Django.contrib.ContentType for the model.
        list_element (bool, optional): Render as a <li> element instead of a button. Defaults to False.
    """
    return {"import_url": job_import_url(content_type), "list_element": list_element}


@register.simple_tag
def job_export_url():
    """
    URL to the run view for the Export Object List system job.

    Helper to `export_button` tag, but can be used separately if needed.
    """
    try:
        export_url = reverse(
            "extras:job_run_by_class_path", kwargs={"class_path": "nautobot.core.jobs.ExportObjectList"}
        )
    except NoReverseMatch:
        export_url = None
    return export_url


@register.inclusion_tag("buttons/export.html", takes_context=True)
def export_button(context, content_type=None, list_element=False):
    """Display an Export Button/List Element on the page.

    Args:
        context (dict): current Django Template context
        content_type (content_type, optional): Django Content Type for the model. Defaults to None.
        list_element (bool, optional): Render as a <li> element instead of a button. Defaults to False.
    """
    if content_type is not None:
        user = context["request"].user
        export_templates = models.ExportTemplate.objects.restrict(user, "view").filter(content_type=content_type)
        export_url = job_export_url()
        include_yaml_option = hasattr(content_type.model_class(), "to_yaml")
    else:
        export_templates = []
        export_url = None
        include_yaml_option = False

    return {
        "export_url": export_url,
        "query_string": context["request"].GET.urlencode(),
        "content_type": content_type,
        "export_templates": export_templates,
        "include_yaml_option": include_yaml_option,
        "list_element": list_element,
    }
