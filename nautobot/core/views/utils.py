import datetime

from django.contrib import messages
from django.core.exceptions import FieldError
from django.db.models import ForeignKey
from django.utils.html import escape
from django.utils.safestring import mark_safe

from nautobot.core.models.utils import is_taggable
from nautobot.core.utils.data import is_uuid
from nautobot.core.utils.lookup import get_form_for_model


def check_filter_for_display(filters, field_name, values):
    """
    Return any additional context data for the template.

    Args:
        filters (OrderedDict): The output of `.get_filters()` of a desired FilterSet
        field_name (str): The name of the filter to get a label for and lookup values
        values (list[str]): List of strings that may be PKs to look up

    Returns:
        (dict): A dict containing:
            - name: (str) Field name
            - display: (str) Resolved field name, whether that's a field label or fallback to inputted `field_name` if label unavailable
            - values: (list) List of dictionaries with the same `name` and `display` keys
    """
    values = values if isinstance(values, (list, tuple)) else [values]

    resolved_filter = {
        "name": field_name,
        "display": field_name,
        "values": [{"name": value, "display": value} for value in values],
    }

    if field_name not in filters.keys():
        return resolved_filter

    resolved_filter["display"] = filters[field_name].label or field_name
    if len(values) == 0 or not hasattr(filters[field_name], "queryset") or not is_uuid(values[0]):
        return resolved_filter
    else:
        try:
            new_values = []
            for value in filters[field_name].queryset.filter(pk__in=values):
                new_values.append({"name": str(value.pk), "display": getattr(value, "display", str(value))})
            resolved_filter["values"] = new_values
        except (FieldError, AttributeError):
            pass

    return resolved_filter


def csv_format(data):
    """
    Encapsulate any data which contains a comma within double quotes.
    """
    csv = []
    for value in data:

        # Represent None or False with empty string
        if value is None or value is False:
            csv.append("")
            continue

        # Convert dates to ISO format
        if isinstance(value, (datetime.date, datetime.datetime)):
            value = value.isoformat()

        # Force conversion to string first so we can check for any commas
        if not isinstance(value, str):
            value = f"{value}"

        # Double-quote the value if it contains a comma or line break
        if "," in value or "\n" in value:
            value = value.replace('"', '""')  # Escape double-quotes
            csv.append(f'"{value}"')
        else:
            csv.append(f"{value}")

    return ",".join(csv)


def handle_protectederror(obj_list, request, e):
    """
    Generate a user-friendly error message in response to a ProtectedError exception.
    """
    protected_objects = list(e.protected_objects)
    protected_count = len(protected_objects) if len(protected_objects) <= 50 else "More than 50"
    err_message = (
        f"Unable to delete <strong>{', '.join(str(obj) for obj in obj_list)}</strong>. "
        f"{protected_count} dependent objects were found: "
    )

    # Append dependent objects to error message
    dependent_objects = []
    for dependent in protected_objects[:50]:
        if hasattr(dependent, "get_absolute_url"):
            dependent_objects.append(f'<a href="{dependent.get_absolute_url()}">{escape(dependent)}</a>')
        else:
            dependent_objects.append(str(dependent))
    err_message += ", ".join(dependent_objects)

    messages.error(request, mark_safe(err_message))


def prepare_cloned_fields(instance):
    """
    Compile an object's `clone_fields` list into a string of URL query parameters. Tags are automatically cloned where
    applicable.
    """
    form_class = get_form_for_model(instance)
    form = form_class() if form_class is not None else None
    params = []
    for field_name in getattr(instance, "clone_fields", []):
        field = instance._meta.get_field(field_name)
        field_value = field.value_from_object(instance)

        # For foreign-key fields, if the ModelForm's field has a defined `to_field_name`,
        # use that field from the related object instead of its PK.
        # Example: Location.parent, LocationForm().fields["parent"].to_field_name = "slug", so use slug rather than PK.
        if isinstance(field, ForeignKey):
            related_object = getattr(instance, field_name)
            if (
                related_object is not None
                and form is not None
                and field_name in form.fields
                and hasattr(form.fields[field_name], "to_field_name")
                and form.fields[field_name].to_field_name is not None
            ):
                field_value = getattr(related_object, form.fields[field_name].to_field_name)

        # Swap out False with URL-friendly value
        if field_value is False:
            field_value = ""

        # This is likely an m2m field
        if isinstance(field_value, list):
            for fv in field_value:
                item_value = getattr(fv, "pk", str(fv))  # pk or str()
                params.append((field_name, item_value))

        # Omit empty values
        elif field_value not in (None, ""):
            params.append((field_name, field_value))

    # Copy tags
    if is_taggable(instance):
        for tag in instance.tags.all():
            params.append(("tags", tag.pk))

    # Concatenate parameters into a URL query string
    param_string = "&".join([f"{k}={v}" for k, v in params])

    return param_string
