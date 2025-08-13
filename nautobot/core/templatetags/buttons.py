from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join

from nautobot.core.templatetags.helpers import bettertitle
from nautobot.core.templatetags.perms import can_add, can_change, can_delete
from nautobot.core.utils import lookup
from nautobot.core.views import utils as views_utils
from nautobot.extras import models

register = template.Library()


#
# Instance buttons
#


@register.simple_tag()
def action_url(instance, action):
    """
    URL to the <action> view for the instance.

    Helper to `edit_button`, `delete_button` and `consolidated_detail_view_action_buttons` tags,
    but can be used separately if needed.

    Args:
        instance (BaseModel): Model record.
        action (str): Action (add/edit/delete) to link to.
    """
    viewname = lookup.get_route_for_model(instance, action)
    if action == "add":
        try:
            return reverse(viewname)
        except NoReverseMatch:
            return None

    # We try different lookups to get a valid reverse url
    lookup_keys = ["pk", "slug", "key"]

    for lookup_key in lookup_keys:
        if hasattr(instance, lookup_key):
            kwargs = {lookup_key: getattr(instance, lookup_key)}
            try:
                return reverse(viewname, kwargs=kwargs)
            except NoReverseMatch:
                continue

    return None


@register.inclusion_tag("buttons/clone.html")
def clone_button(instance):
    url = action_url(instance, "add")
    if not url:
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
    return {"url": action_url(instance, "edit")}


@register.inclusion_tag("buttons/delete.html")
def delete_button(instance, use_pk=False, key="slug"):
    """
    Render a button to delete a model instance.

    Args:
        instance (BaseModel): Model record.
        use_pk (bool): Used for backwards compatibility, no-op in this function.
        key (str): Used for backwards compatibility, no-op in this function.
    """
    return {"url": action_url(instance, "delete")}


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


def render_tag_attrs(attrs_dict):
    """Converts tag attributes from a dictionary to a string format suitable for HTML rendering."""
    return format_html_join(" ", '{}="{}"', list(attrs_dict.items()))


@register.inclusion_tag("buttons/consolidated_bulk_action_buttons.html", takes_context=True)
def consolidate_bulk_action_buttons(context):
    """
    Generates a list of action buttons for bulk operations (edit, update group assignment, delete) based on the
    model capabilities and user permissions.

    Context must include the following keys:
        request (HttpRequest): The HTTP request object.
        model (Model): The model class for the list view.
        user (User): The current user.
        bulk_edit_url (str): The URL for the bulk edit action.
        bulk_delete_url (str): The URL for the bulk delete action.
        permissions (dict): A dictionary of specific permissions for the view.
    """

    bulk_action_buttons = []

    render_edit_button = bool(context["bulk_edit_url"] and context["permissions"]["change"])
    render_static_group_assign_button = bool(
        getattr(context["model"], "is_dynamic_group_associable_model", False)
        and context["user"].has_perms(["extras.add_staticgroupassociation"])
    )
    render_delete_button = bool(context["bulk_delete_url"] and context["permissions"]["delete"])
    bulk_action_button_count = sum([render_edit_button, render_static_group_assign_button, render_delete_button])

    if bulk_action_button_count == 0:
        return {
            "bulk_action_buttons": bulk_action_buttons,
        }

    primary_button_fragment = child_button_fragment = """
        <button {attrs}>
            <span class="{icon}" aria-hidden="true"></span> {label}
        </button>
    """

    edit_button_classes = "btn btn-sm btn-warning"
    delete_button_classes = "btn btn-sm btn-danger"
    static_group_button_classes = "btn btn-sm btn-primary"
    static_group_icon = "mdi mdi-group"

    if bulk_action_button_count > 1:
        child_button_fragment = f"<li>{primary_button_fragment}</li>"
        delete_button_classes = "text-danger"
        static_group_button_classes = "text"
        static_group_icon += " text-muted"

    if render_edit_button:
        bulk_action_buttons.append(
            format_html(
                primary_button_fragment,
                label="Edit Selected",
                attrs=render_tag_attrs(
                    {
                        "class": edit_button_classes,
                        "formaction": reverse(context["bulk_edit_url"]),
                        "type": "submit",
                    }
                ),
                icon="mdi mdi-pencil",
            ),
        )
        if bulk_action_button_count > 1:
            bulk_action_buttons[0] += format_html(
                f"""
                <button type="button" data-toggle="dropdown" class="{edit_button_classes} dropdown-toggle" aria-haspopup="true">
                    <span class="caret"></span>
                    <span class="sr-only">Toggle Dropdown</span>
                </button>
                """
            )

    # Render a generic "Bulk Actions" dropup button if the edit button is not present
    elif bulk_action_button_count > 1:
        bulk_action_buttons.append(
            format_html(
                """
                <button type="button" class="btn btn-sm btn-primary dropdown-toggle" data-toggle="dropdown" aria-haspopup="true">
                    Bulk Actions <span class="caret"></span>
                </button>
                """
            )
        )

    if render_delete_button:
        bulk_action_buttons.append(
            format_html(
                child_button_fragment,
                label="Delete Selected",
                attrs=render_tag_attrs(
                    {
                        "class": delete_button_classes,
                        "type": "submit",
                        "name": "_delete",
                        "formaction": reverse(context["bulk_delete_url"]),
                    }
                ),
                icon="mdi mdi-trash-can-outline",
            )
        )

    if render_delete_button and render_static_group_assign_button:
        bulk_action_buttons.append(format_html('<li role="separator" class="divider"></li>'))

    if render_static_group_assign_button:
        bulk_action_buttons.append(
            format_html(
                child_button_fragment,
                label="Update Group Assignment",
                attrs=render_tag_attrs(
                    {
                        "class": static_group_button_classes,
                        "id": "update_dynamic_groups_for_selected",
                        "data-toggle": "modal",
                        "data-target": "#dynamic_group_assignment_modal",
                        "data-objects": "selected",
                        "type": "button",
                    }
                ),
                icon=static_group_icon,
            )
        )

    return {
        "bulk_action_buttons": bulk_action_buttons,
    }


@register.inclusion_tag("buttons/consolidated_detail_view_action_buttons.html", takes_context=True)
def consolidate_detail_view_action_buttons(context):
    """
    Generates a list of action buttons for detail view operations (edit, clone, delete) based on the
    model capabilities and user permissions.

    Context must include the following keys:
        request (HttpRequest): The HTTP request object.
        object (Model): The object in the detail view.
        user (User): The current user.
    """
    instance = context["object"]
    detail_view_action_buttons = []
    object_edit_url = action_url(instance, "edit")
    object_delete_url = action_url(instance, "delete")
    object_clone_url = action_url(instance, "add")
    render_edit_button = bool(object_edit_url and can_change(context["user"], instance))
    render_delete_button = bool(object_delete_url and can_delete(context["user"], instance))
    render_clone_button = bool(
        hasattr(instance, "clone_fields") and object_clone_url and can_add(context["user"], instance)
    )

    detail_view_action_button_count = sum([render_edit_button, render_delete_button, render_clone_button])

    if detail_view_action_button_count == 0:
        return {
            "detail_view_action_buttons": detail_view_action_buttons,
        }

    child_button_fragment = primary_button_fragment = """
        <a {attrs}>
            <span class="{icon}" aria-hidden="true"></span> {label}
        </a>
    """

    delete_button_fragment = """
        <button class="{button_class}">
            <a {attrs}>
                <span class="{icon}" aria-hidden="true"></span> {label}
            </a>
        </button>
    """

    edit_button_classes = "btn btn-warning"
    delete_button_classes = "text-danger"
    clone_button_classes = "text"
    clone_icon = "mdi mdi-plus-thick text-muted"
    child_button_fragment = f"<li>{primary_button_fragment}</li>"
    delete_button_fragment = f"<li>{delete_button_fragment}</li>"

    if render_edit_button:
        detail_view_action_buttons.append(
            format_html(
                primary_button_fragment,
                label=f"Edit {bettertitle(context['verbose_name'])}",
                attrs=render_tag_attrs(
                    {
                        "id": "edit-button",
                        "class": edit_button_classes,
                        "href": object_edit_url,
                    }
                ),
                button_class=edit_button_classes,
                icon="mdi mdi-pencil",
            ),
        )
        if detail_view_action_button_count > 1:
            detail_view_action_buttons[0] += format_html(
                f"""
                <button type="button" id="actions-dropdown" data-toggle="dropdown" class="{edit_button_classes} dropdown-toggle">
                    <span class="caret"></span>
                    <span class="sr-only">Toggle Dropdown</span>
                </button>
                """
            )

    # Render a generic "Actions" dropdown button if the edit button is not present
    elif detail_view_action_button_count >= 1:
        detail_view_action_buttons.append(
            format_html(
                """
                <button type="button" id="actions-dropdown" class="btn btn-warning dropdown-toggle" data-toggle="dropdown">
                    Actions <span class="caret"></span>
                </button>
                """
            )
        )
    if render_clone_button:
        param_string = views_utils.prepare_cloned_fields(instance)
        if param_string:
            object_clone_url = f"{object_clone_url}?{param_string}"
        detail_view_action_buttons.append(
            format_html(
                child_button_fragment,
                label=f"Clone {bettertitle(context['verbose_name'])}",
                attrs=render_tag_attrs(
                    {
                        "id": "clone-button",
                        "class": clone_button_classes,
                        "href": object_clone_url,
                    }
                ),
                icon=clone_icon,
                button_class=clone_button_classes,
            )
        )
    if render_delete_button:
        if render_clone_button:
            detail_view_action_buttons.append(format_html('<li role="separator" class="divider"></li>'))
        detail_view_action_buttons.append(
            format_html(
                delete_button_fragment,
                label=f"Delete {bettertitle(context['verbose_name'])}",
                attrs=render_tag_attrs(
                    {
                        "id": "delete-button",
                        "class": delete_button_classes,
                        "href": object_delete_url,
                    }
                ),
                icon="mdi mdi-trash-can-outline",
                button_class=delete_button_classes,
            )
        )

    return {
        "detail_view_action_buttons": detail_view_action_buttons,
    }


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
