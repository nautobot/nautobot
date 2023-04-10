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

    filter_field = filters[field_name]

    resolved_filter["display"] = get_filter_field_label(filter_field)

    if len(values) == 0 or not hasattr(filter_field, "queryset") or not is_uuid(values[0]):
        return resolved_filter
    else:
        try:
            new_values = []
            for value in filter_field.queryset.filter(pk__in=values):
                new_values.append({"name": str(value.pk), "display": getattr(value, "display", str(value))})
            resolved_filter["values"] = new_values
        except (FieldError, AttributeError):
            pass

    return resolved_filter


def get_filter_field_label(filter_field):
    """
    Return a label for a given field name and value.

    Args:
        field (Filter): The filter to get a label for

    Returns:
        (str): The label for the given field
    """

    if filter_field.label:
        return filter_field.label
    elif hasattr(filter_field, "relationship"):
        return filter_field.relationship.get_label(side=filter_field.side)
    elif hasattr(filter_field, "custom_field"):
        return filter_field.custom_field.label
    else:
        return _field_name_to_display(filter_field.field_name)


def _field_name_to_display(field_name):
    """
    Return a more human readable version of a field name.
    """
    field_name = field_name.replace("_custom_field_data__", "")
    split_field = field_name.split("__") if "__" in field_name else field_name.split("_")
    words = " ".join(split_field)
    return words[0].upper() + words[1:]
