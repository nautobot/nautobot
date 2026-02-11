import logging
from typing import Any, Iterable, Mapping

from django import forms
from django.core.exceptions import ValidationError
from django_filters import FilterSet

from nautobot.core.utils.lookup import get_form_for_model

logger = logging.getLogger(__name__)


def build_filter_dict_from_filterset(
    filterset_class: type[FilterSet],
    form_data: Mapping[str, Any],
    filter_fields: Iterable[str] | None = None,
    *,
    logs_prefix: object | None = None,
) -> dict[str, Any]:
    # Populate the filterset from the incoming `form_data`. The filterset's internal form is
    # used for validation, will be used by us to extract cleaned data for final processing.
    filterset = filterset_class(form_data)

    # Use the auto-generated filterset form perform creation of the filter dictionary.
    filterset_form = filterset.form

    # Get the declared form for any overloaded form field definitions.
    declared_form = get_form_for_model(filterset._meta.model, form_prefix="Filter")

    # It's expected that the incoming data has already been cleaned by a form. This `is_valid()`
    # call is primarily to reduce the fields down to be able to work with the `cleaned_data` from the
    # filterset form, but will also catch errors in case a user-created dict is provided instead.
    if not filterset_form.is_valid():
        raise ValidationError(filterset_form.errors)

    logs_prefix = logs_prefix or filterset_class.__name__

    # Perform some type coercions so that they are URL-friendly and reversible, excluding any
    # empty/null value fields.
    new_filter = {}
    allowed_fields = filter_fields or filterset_form.fields.keys()
    for field_name in allowed_fields:
        field = declared_form.declared_fields.get(field_name, filterset_form.fields[field_name])
        field_value = filterset_form.cleaned_data[field_name]

        # TODO: This could/should check for both "convenience" FilterForm fields (ex: DynamicModelMultipleChoiceField)
        # and literal FilterSet fields (ex: MultiValueCharFilter).
        if isinstance(field, forms.ModelMultipleChoiceField):
            if not field_value:
                continue
            field_to_query = field.to_field_name or "pk"
            new_value = [getattr(item, field_to_query) for item in field_value]

        elif isinstance(field, forms.ModelChoiceField):
            if not field_value:
                continue
            field_to_query = field.to_field_name or "pk"
            new_value = getattr(field_value, field_to_query, None)

        else:
            new_value = field_value

        # Don't store empty values like `None`, [], etc.
        if new_value in (None, "", [], {}, ()):
            logger.debug("[%s] Not storing empty value (%s) for %s", logs_prefix, field_value, field_name)
            continue

        logger.debug("[%s] Setting filter field {%s: %s}", logs_prefix, field_name, field_value)
        new_filter[field_name] = new_value

    return new_filter
