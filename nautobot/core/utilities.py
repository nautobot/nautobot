from django.core.exceptions import FieldError

from nautobot.utilities.utils import is_uuid


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
