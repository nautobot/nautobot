from django.contrib import messages
from django.core.exceptions import FieldError
from django.utils.html import escape
from django.utils.safestring import mark_safe

from nautobot.core.utils.utils import is_uuid


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
