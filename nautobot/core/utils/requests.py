import re
from urllib.parse import parse_qs, urlencode, urlparse

from django import forms
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.http import QueryDict
import django_filters

from nautobot.core import exceptions
from nautobot.core.utils.filtering import get_filterset_field

NON_FILTER_PARAMS = (
    "all_filters_removed",  # indicator for if all filters have been removed from the saved view
    "clear_view",  # indicator for if the clear view button is clicked or not
    "export",  # trigger for CSV/export-template/YAML export # 3.0 TODO: remove, irrelevant after #4746
    "page",  # used by django-tables2.RequestConfig
    "per_page",  # used by get_paginate_count
    "saved_view",  # saved_view indicator pk or composite keys
    "sort",  # table sorting
    "table_changes_pending",  # indicator for if there is any table changes not applied to the saved view
)
"""The query parameters a list view uses for something other than filtering its queryset.

Every list view starts from these (as `ObjectListView.non_filter_params` /
`ObjectListViewMixin.non_filter_params`) and a view that reads additional parameters of its own extends
them, e.g. `non_filter_params = (*NautobotUIViewSet.non_filter_params, "expanded_subtree")`. Anything
left over is handed to the view's filterset, so a parameter missing from a view's list is treated as a
filter -- which is why `ExportObjectList` unions a view's list into these rather than assuming these
alone; see `ExportObjectList._get_non_filter_params()`.
"""


def convert_querydict_to_factory_formset_acceptable_querydict(request_querydict, filterset):
    """
    Convert request QueryDict/GET into an acceptable factory formset QueryDict
    while discarding `querydict` params which are not part of `filterset_class` params

    Args:
        request_querydict (QueryDict): QueryDict to convert
        filterset (FilterSet): Filterset class

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
                if isinstance(request_querydict, QueryDict):
                    lookup_value = request_querydict.getlist(filter_field_name)
                else:
                    lookup_value = request_querydict.get(filter_field_name)
                if not isinstance(lookup_value, list):
                    lookup_value = [lookup_value]

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
        filter_params (QueryDict): Filter param querydict
        non_filter_params (list): Non queryset filterable params
        filterset (FilterSet): FilterSet class instance

    Returns:
        (QueryDict): Filter param querydict with only queryset filterable params
    """
    # Some FilterSet field only accept single choice not multiple choices
    # e.g datetime field, bool fields etc.
    final_filter_params = {}
    for field in filter_params.keys():
        if field in non_filter_params:
            continue
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


def resolve_filter_params(query_params, non_filter_params, filterset, get_saved_view_filter_params=None):
    """
    The filters a list view has applied, given its request's query parameters.

    A saved view contributes the filters it has stored only when the query string carries none of its
    own: any filter in the query string means the user changed the view's filters, and *replaces* the
    saved view's set rather than merging with it -- which is what lets a user widen a saved view as well
    as narrow it. `all_filters_removed` says the user cleared them outright.

    Shared by everything that has to answer this question the way a list view answers it: the list views
    themselves (`ObjectListView.get_filter_params()`, `NautobotViewSetMixin.get_filter_params()`) and the
    `ExportObjectList` Job, so that exporting a view covers the records that view is showing.

    Args:
        query_params (QueryDict): The request's query parameters.
        non_filter_params (iterable): Parameters this view uses for something other than filtering the
            queryset; see `NON_FILTER_PARAMS`.
        filterset (FilterSet): An instance of the view's filterset, used to tell single-valued filters
            from multi-valued ones.
        get_saved_view_filter_params (Optional[callable]): Zero-argument callable returning the filters
            stored on the saved view named by the `saved_view` query parameter. Called only if those
            filters are actually needed, so that a caller which would have to query for them does not
            pay for them on every request.

    Returns:
        (dict): The filter parameters to instantiate the filterset with.
    """
    filter_params = get_filterable_params_from_filter_params(query_params, non_filter_params, filterset)
    if filter_params or query_params.get("all_filters_removed") or not query_params.get("saved_view"):
        return filter_params
    if get_saved_view_filter_params is None:
        return filter_params
    return get_saved_view_filter_params()


def normalize_querydict(querydict, form_class=None, filterset=None):
    """
    Converts a QueryDict into a standard, mutable dictionary while preserving multiple values as lists.

    Example:
        A QueryDict like:
            QueryDict('foo=1&bar=2&bar=3&baz=')

        Converts to:
            {'foo': '1', 'bar': ['2', '3'], 'baz': ''}

    This function ensures that fields with multiple values are handled correctly, as QueryDict
    does not inherently preserve multiple values as lists.

    Args:
        querydict (QueryDict): The QueryDict or dictionary as produced by `convert_querydict_to_dict` to be normalized.
        form_class (forms.Form, optional): A form class to identify fields that should be treated as
            lists (e.g., `MultipleChoiceField` or `ModelMultipleChoiceField`).
        filterset (django_filters.FilterSet, optional): A FilterSet instance to identify filters that
            should preserve multiple values as lists (e.g., non-single-choice fields).

    Raises:
        AttributeError: If both `form_class` and `filterset` are provided.
    """
    if form_class and filterset:
        raise AttributeError("Either form_class or filterset_class is to be provided not both")

    result = {}

    if querydict:
        # check if true QueryDict or standard dict in format of querydict, e.g. from `convert_querydict_to_dict`
        if hasattr(querydict, "lists"):
            items = querydict.lists()
        else:
            items = querydict.items()

        for key, value_list in items:
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
            elif filterset is not None and filterset.filters.get(key) and not is_single_choice_field(filterset, key):
                result[key] = value_list
            else:
                # Only a single value in the querydict for this key, and no guidance otherwise, so make it single
                result[key] = value_list[0]
    return result


def add_nautobot_version_query_param_to_url(url):
    parsed_url = urlparse(url)
    params = parse_qs(parsed_url.query)
    params["version"] = settings.VERSION
    updated_query = urlencode(params, doseq=True)
    return parsed_url._replace(query=updated_query).geturl()


def convert_querydict_to_dict(request_querydict):
    """
    Convert QueryDict to standard json serializable dictionary.

    This is useful when you want to serialize a QueryDict to JSON format such as
    when sending to a Job form or sending it over an API. This is not the same as
    `normalize_querydict` which preserves single values as singletons and multi-values
    as lists. This function preserves all values as lists.

    Args:
        request_querydict (QueryDict): QueryDict to convert.

    Examples:
        >>> convert_querydict_to_dict(QueryDict('foo=1&bar=2&bar=3&baz='))
        >>> {'foo': ['1'], 'bar': ['2', '3'], 'baz': ['']}
    """
    return {key: value for key, value in request_querydict.lists()}  # pylint: disable=unnecessary-comprehension
