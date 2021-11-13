import inspect
from collections import OrderedDict

import django_filters
from django.db.models import Q


def extract_value_from_object_from_queryset(obj, attrs_list):

    if not attrs_list:
        raise ValueError("A list of attribute must be provided")

    print(obj, attrs_list)
    attr = attrs_list.pop(0)
    # TODO Catch exception if the attribute doesn't exist

    value = getattr(obj, attr)
    if not value:
        return None

    if attrs_list:
        return extract_value_from_object_from_queryset(value, attrs_list)

    return value


class BaseDynamicGroupMap:

    model = None
    filterset = None
    filterform = None

    field_order = []
    # field_exclude = ["model", "filterset", "field_order", "field_exclude"]

    @classmethod
    def fields(cls):
        """Return all fields in a dictionnary."""
        _fields = OrderedDict()

        filterform = cls.filterform()
        for field_name in cls.field_order:
            _fields[field_name] = filterform.fields[field_name]

        return _fields

    @classmethod
    def get_queryset(cls, filter):
        """Return a queryset matching the dynamic group filter.

        By default the queryset is generated based of the filterset but this is not mandatory
        """
        filterset = cls.filterset(cls.get_filterset_params(filter), cls.model.objects.all())
        return filterset.qs

    @classmethod
    def get_filterset_params(cls, filter):
        return filter

    @classmethod
    def get_filterset_as_string(cls, filter):
        """Get filterset as string."""
        if not filter:
            return None

        result = ""

        for key, value in cls.get_filterset_params(filter).items():
            if isinstance(value, list):
                for item in value:
                    if result != "":
                        result += "&"
                    result += f"{key}={item}"
            else:
                result += "&"
                result += f"{key}={value}"

        return result

    @classmethod
    def get_queryset_filter(cls, obj):

        queryset_filter = Q()

        for field_name in cls.field_order:
            class_name = f"get_queryset_filter_default"
            if hasattr(cls, f"get_queryset_filter_{field_name}"):
                class_name = f"get_queryset_filter_{field_name}"

            queryset_filter_item = getattr(cls, class_name)(field_name, obj)

            if queryset_filter_item:
                queryset_filter |= queryset_filter_item

        return queryset_filter

    @classmethod
    def get_queryset_filter_default(cls, field_name, obj):

        filterset = cls.filterset()
        # TODO Add check to ensure that field is present
        # TODO Add check to ensure that the field has a field_name property
        field = filterset.declared_filters[field_name]

        # ----------------------------------------------
        # Construct the query label first
        # ----------------------------------------------
        query_label = f"filter__{field_name}"

        # Identify if the field is is a list or not
        match_type = None
        if isinstance(field, django_filters.ModelMultipleChoiceFilter):
            match_type = "contains"

        if match_type:
            query_label = query_label + f"__{match_type}"

        # ----------------------------------------------
        # Construct the value of the query based on the
        # ----------------------------------------------
        query_value = extract_value_from_object_from_queryset(obj, field.field_name.split("__"))

        if query_value:
            return Q(**{query_label: query_value})
