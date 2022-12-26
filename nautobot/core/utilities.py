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
        (list): A two item list containing:
            - [0]: (str) Resolved field name, whether that's a field label of fallback to inputted `field_name` if label unavailable
            - [1]: (list) Resolved field values, the return of `.display` property of the object, or the original inputted value
    """
    values = values if isinstance(values, (list, tuple)) else [values]

    if field_name not in filters.keys():
        return [field_name, values]

    label = filters[field_name].label if filters[field_name].label else field_name
    if len(values) == 0 or not hasattr(filters[field_name], "queryset") or not is_uuid(values[0]):
        return [label, values]
    else:
        try:
            filtered_results = filters[field_name].queryset.filter(pk__in=values)
            new_values = [result.display if hasattr(result, "display") else str(result) for result in filtered_results]
            return [label, new_values]
        except (FieldError, AttributeError):
            return [label, values]
