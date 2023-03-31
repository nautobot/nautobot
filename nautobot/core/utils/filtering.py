import re

from django import forms
from django_filters import (
    ChoiceFilter,
    ModelMultipleChoiceFilter,
    MultipleChoiceFilter,
    NumberFilter,
)
from django_filters.utils import verbose_lookup_expr

from nautobot.core import exceptions
from nautobot.core.utils.lookup import get_filterset_for_model


# Check if field name contains a lookup expr
# e.g `name__ic` has lookup expr `ic (icontains)` while `name` has no lookup expr
CONTAINS_LOOKUP_EXPR_RE = re.compile(r"(?<=__)\w+")


def build_lookup_label(field_name, _verbose_name):
    """
    Return lookup expr with its verbose name

    Args:
        field_name (str): Field name e.g slug__iew
        _verbose_name (str): The verbose name for the lookup expr which is suffixed to the field name e.g iew -> iendswith

    Examples:
        >>> build_lookup_label("slug__iew", "iendswith")
        >>> "ends-with (iew)"
    """
    verbose_name = verbose_lookup_expr(_verbose_name) or "exact"
    label = ""
    search = CONTAINS_LOOKUP_EXPR_RE.search(field_name)
    if search:
        label = f" ({search.group()})"

    verbose_name = "not " + verbose_name if label.startswith(" (n") else verbose_name

    return verbose_name + label


def get_all_lookup_expr_for_field(model, field_name):
    """
    Return all lookup expressions for `field_name` in `model` filterset
    """
    filterset = get_filterset_for_model(model)().filters

    if not filterset.get(field_name):
        raise exceptions.FilterSetFieldNotFound("field_name not found")

    if field_name.startswith("has_"):
        return [{"id": field_name, "name": "exact"}]

    lookup_expr_choices = []

    for name, field in filterset.items():
        # remove the lookup_expr from field_name e.g name__iew -> name
        if re.sub(r"__\w+", "", name) == field_name and not name.startswith("has_"):
            lookup_expr_choices.append(
                {
                    "id": name,
                    "name": build_lookup_label(name, field.lookup_expr),
                }
            )

    return lookup_expr_choices


def get_filterset_field(filterset_class, field_name):
    field = filterset_class().filters.get(field_name)
    if field is None:
        raise exceptions.FilterSetFieldNotFound(f"{field_name} is not a valid {filterset_class.__name__} field")
    return field


def get_filterset_parameter_form_field(model, parameter):
    """
    Return the relevant form field instance for a filterset parameter e.g DynamicModelMultipleChoiceField, forms.IntegerField e.t.c
    """
    # Avoid circular import
    from nautobot.dcim.models import Device
    from nautobot.extras.filters import ContentTypeMultipleChoiceFilter, StatusFilter
    from nautobot.extras.models import ConfigContext, Role, Status, Tag
    from nautobot.extras.utils import ChangeLoggedModelsQuery, RoleModelsQuery, TaggableClassesQuery
    from nautobot.core.filters import MultiValueDecimalFilter, MultiValueFloatFilter
    from nautobot.core.forms import (
        DynamicModelMultipleChoiceField,
        MultipleContentTypeField,
        StaticSelect2Multiple,
    )
    from nautobot.virtualization.models import VirtualMachine

    filterset_class = get_filterset_for_model(model)
    field = get_filterset_field(filterset_class, parameter)
    form_field = field.field

    # TODO(Culver): We are having to replace some widgets here because multivalue_field_factory that generates these isn't smart enough
    if isinstance(field, (MultiValueDecimalFilter, MultiValueFloatFilter)):
        form_field = forms.DecimalField()
    elif isinstance(field, NumberFilter):
        form_field = forms.IntegerField()
    elif isinstance(field, ModelMultipleChoiceFilter):
        related_model = Status if isinstance(field, StatusFilter) else field.extra["queryset"].model
        form_attr = {
            "queryset": related_model.objects.all(),
            "to_field_name": field.extra.get("to_field_name", "id"),
        }
        # ConfigContext requires content_type set to Device and VirtualMachine
        if model == ConfigContext:
            form_attr["query_params"] = {"content_types": [Device._meta.label_lower, VirtualMachine._meta.label_lower]}
        # Status and Tag api requires content_type, to limit result to only related content_types
        elif related_model in [Role, Status, Tag]:
            form_attr["query_params"] = {"content_types": model._meta.label_lower}

        form_field = DynamicModelMultipleChoiceField(**form_attr)
    elif isinstance(field, ContentTypeMultipleChoiceFilter):
        plural_name = model._meta.verbose_name_plural
        try:
            form_field = MultipleContentTypeField(choices_as_strings=True, feature=plural_name)
        except KeyError:
            # `MultipleContentTypeField` employs `registry["model features"][feature]`, which may
            # result in an error if `feature` is not found in the `registry["model features"]` dict.
            # In this case use queryset
            queryset_map = {
                "tags": TaggableClassesQuery,
                "job hooks": ChangeLoggedModelsQuery,
                "roles": RoleModelsQuery,
            }
            form_field = MultipleContentTypeField(
                choices_as_strings=True, queryset=queryset_map[plural_name]().as_queryset()
            )
    elif isinstance(field, (MultipleChoiceFilter, ChoiceFilter)) and "choices" in field.extra:
        form_field_class = forms.ChoiceField
        form_field_class.widget = StaticSelect2Multiple()
        form_attr = {"choices": field.extra.get("choices")}

        form_field = form_field_class(**form_attr)

    form_field.required = False
    form_field.initial = None
    form_field.widget.attrs.pop("required", None)

    css_classes = form_field.widget.attrs.get("class", "")
    form_field.widget.attrs["class"] = "form-control " + css_classes
    return form_field
