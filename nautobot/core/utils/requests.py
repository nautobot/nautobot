import re

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.http import QueryDict
import django_filters

from nautobot.core import exceptions
from nautobot.core.utils.filtering import get_filterset_field


def convert_querydict_to_factory_formset_acceptable_querydict(request_querydict, filterset):
    """
    Convert request QueryDict/GET into an acceptable factory formset QueryDict
    while discarding `querydict` params which are not part of `filterset_class` params

    Args:
        request_querydict (QueryDict): QueryDict to convert
        filterset_class: Filterset class

    Examples:
        >>> convert_querydict_to_factory_formset_acceptable_querydict({"status": ["active", "decommissioning"], "name__ic": ["location"]},)
        >>> {
        ...     'form-TOTAL_FORMS': [3],
        ...     'form-INITIAL_FORMS': ['0'],
        ...     'form-MIN_NUM_FORMS': [''],
        ...     'form-MAX_NUM_FORMS': [''],
        ...     'form-0-lookup_field': ['status'],
        ...     'form-0-lookup_type': ['status'],
        ...     'form-0-value': ['active', 'decommissioning'],
        ...     'form-1-lookup_field': ['name'],
        ...     'form-1-lookup_type': ['name__ic'],
        ...     'form-1-value': ['location']
        ... }
    """
    query_dict = QueryDict(mutable=True)
    filterset_class_fields = filterset.filters.keys()

    query_dict.setdefault("form-INITIAL_FORMS", 0)
    query_dict.setdefault("form-MIN_NUM_FORMS", 0)
    query_dict.setdefault("form-MAX_NUM_FORMS", 100)

    lookup_field_placeholder = "form-%d-lookup_field"
    lookup_type_placeholder = "form-%d-lookup_type"
    lookup_value_placeholder = "form-%d-lookup_value"

    num = 0
    request_querydict = request_querydict.copy()
    request_querydict.pop("q", None)
    for filter_field_name, value in request_querydict.items():
        # Discard fields without values
        if value:
            if filter_field_name in filterset_class_fields:
                if hasattr(filterset.filters[filter_field_name], "relationship"):
                    lookup_field = filter_field_name
                else:
                    # convert_querydict_to_factory_formset_acceptable_querydict expects to have a QueryDict as input
                    # which means we may not have the exact field name as defined in the filterset class
                    # it may contain a lookup expression (e.g. `name__ic`), so we need to strip it
                    # this is so we can select the correct field in the formset for the "field" column
                    # TODO: Since we likely need to instantiate the filterset class early in the request anyway
                    # the filterset can handle the QueryDict conversion and we can just pass the QueryDict to the filterset
                    # then use the FilterSet to de-dupe the field names
                    lookup_field = re.sub(r"__\w+", "", filter_field_name)
                lookup_value = request_querydict.getlist(filter_field_name)

                query_dict.setlistdefault(lookup_field_placeholder % num, [lookup_field])
                query_dict.setlistdefault(lookup_type_placeholder % num, [filter_field_name])
                query_dict.setlistdefault(lookup_value_placeholder % num, lookup_value)
                num += 1

    query_dict.setdefault("form-TOTAL_FORMS", max(num, 3))
    return query_dict


def ensure_content_type_and_field_name_in_query_params(query_params):
    """Ensure `query_params` includes `content_type` and `field_name` and `content_type` is a valid ContentType.

    Return the 'ContentTypes' model and 'field_name' if validation was successful.
    """
    if "content_type" not in query_params or "field_name" not in query_params:
        raise ValidationError("content_type and field_name are required parameters", code=400)
    contenttype = query_params.get("content_type")
    app_label, model_name = contenttype.split(".")
    try:
        model_contenttype = ContentType.objects.get(app_label=app_label, model=model_name)
        model = model_contenttype.model_class()
        if model is None:
            raise ValidationError(f"model for content_type: <{model_contenttype}> not found", code=500)
    except ContentType.DoesNotExist:
        raise ValidationError("content_type not found", code=404)
    field_name = query_params.get("field_name")

    return field_name, model


def is_single_choice_field(filterset, field_name):
    # Some filter parameters do not accept multiple values, e.g DateTime, Boolean, Int fields and the q field, etc.
    field = get_filterset_field(filterset, field_name)
    return not isinstance(field, django_filters.MultipleChoiceFilter)


def get_filterable_params_from_filter_params(filter_params, non_filter_params, filterset):
    """
    Remove any `non_filter_params` and fields that are not a part of the filterset from  `filter_params`
    to return only queryset filterable parameters.

    Args:
        filter_params(QueryDict): Filter param querydict
        non_filter_params(list): Non queryset filterable params
        filterset: The FilterSet class
    """
    for non_filter_param in non_filter_params:
        filter_params.pop(non_filter_param, None)

    # Some FilterSet field only accept single choice not multiple choices
    # e.g datetime field, bool fields etc.
    final_filter_params = {}
    for field in filter_params.keys():
        if filter_params.get(field):
            # `is_single_choice_field` implements `get_filterset_field`, which throws an exception if a field is not found.
            # If an exception is thrown, instead of throwing an exception, set `_is_single_choice_field` to 'False'
            # because the fields that were not discovered are still necessary.
            try:
                _is_single_choice_field = is_single_choice_field(filterset, field)
            except exceptions.FilterSetFieldNotFound:
                _is_single_choice_field = False

            final_filter_params[field] = (
                filter_params.get(field) if _is_single_choice_field else filter_params.getlist(field)
            )

    return final_filter_params


def normalize_querydict(querydict, form_class=None):
    """
    Convert a QueryDict to a normal, mutable dictionary, preserving list values. For example,

        QueryDict('foo=1&bar=2&bar=3&baz=')

    becomes:

        {'foo': '1', 'bar': ['2', '3'], 'baz': ''}

    This function is necessary because QueryDict does not provide any built-in mechanism which preserves multiple
    values.

    A `form_class` can be provided as a way to hint which query parameters should be treated as lists.
    """
    result = {}
    if querydict:
        for key, value_list in querydict.lists():
            if len(value_list) > 1:
                # More than one value in the querydict for this key, so keep it as a list
                # TODO: we could check here and de-listify value_list if the form_class field is a single-value one?
                result[key] = value_list
            elif (
                form_class is not None
                and key in form_class.base_fields
                # ModelMultipleChoiceField is *not* itself a subclass of MultipleChoiceField, thanks Django!
                and isinstance(form_class.base_fields[key], (forms.MultipleChoiceField, forms.ModelMultipleChoiceField))
            ):
                # Even though there's only a single value in the querydict for this key, the form wants it as a list
                result[key] = value_list
            else:
                # Only a single value in the querydict for this key, and no guidance otherwise, so make it single
                result[key] = value_list[0]
    return result
