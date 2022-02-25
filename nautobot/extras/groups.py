from collections import OrderedDict
import logging
import urllib

import django_filters
from django_filters.utils import get_model_field
from django.db.models import Q
from django.db import models
from django.urls import reverse
from django.utils.functional import classproperty

from nautobot.utilities.utils import get_filterform_for_model, get_filterset_for_model, get_route_for_model


logger = logging.getLogger(__name__)


def extract_value_from_object_from_queryset(obj, field_parts):
    # FIXME(jathan): Document this and fix the variable names for readability.

    if not field_parts:
        raise ValueError("A list of attribute must be provided")

    field_name = field_parts.pop(0)
    value = getattr(obj, field_name, None)

    # Only proceed if the field is found.
    if value is None:
        return None

    if field_parts:
        return extract_value_from_object_from_queryset(value, field_parts)

    if isinstance(value, models.Model):
        value = str(value)

    return value


def dynamicgroup_map_factory(model):
    """Generate a `FooDynamicGroupMap` class for a given `model`."""

    filterset = get_filterset_for_model(model)
    filterform = get_filterform_for_model(model)

    group_map = type(
        str("%sDynamicGroupMap" % model._meta.object_name),
        (BaseDynamicGroupMap,),
        {"model": model, "filterset": filterset, "filterform": filterform},
    )

    return group_map


class BaseDynamicGroupMap:
    """
    Dynamic Group mapping used to generate mappings for each model class.

    This class itself should not be invoked directly as the class variables will
    not be populated and most class methods will fail.
    """

    model = None
    filterset = None
    filterform = None

    @classproperty
    def base_url(cls):
        if cls.model is None:
            return
        route_name = get_route_for_model(cls.model, "list")
        return reverse(route_name)

    @classmethod
    def fields(cls):
        """Return all fields in a dictionnary."""
        _fields = OrderedDict()
        filterform = cls.filterform()
        for field_name in filterform.fields:
            _fields[field_name] = filterform.fields[field_name]

        return _fields

    @classmethod
    def get_queryset(cls, filter_params):
        """
        Return a queryset matching the dynamic group `filter_params`.

        By default the queryset is generated based of the filterset but this is not mandatory
        """
        filterset = cls.filterset(filter_params, cls.model.objects.all())
        return filterset.qs

    @classmethod
    def urlencode(cls, filter_params):
        """
        Given a `filter_params` dict, return a URL-encoded HTTP query string.

        For example:
            >>> dg = DynamicGroup.objects.first()
            >>> filter_params = {"site": ["ams01", "bkk01"], "has_primary_ip": True}
            >>> dg.map.urlencode(filter_params)
            site=ams01&site=bkk01&has_primary_ip=True'

        """
        return urllib.parse.urlencode(filter_params, doseq=True)

    @classmethod
    def get_queryset_filter(cls, obj):

        queryset_filter = Q()
        filterset = cls.filterset()

        for field_name in cls.fields():
            method_name = "get_queryset_filter_default"
            if hasattr(cls, f"get_queryset_filter_{field_name}"):
                method_name = f"get_queryset_filter_{field_name}"

            queryset_filter_item = getattr(cls, method_name)(field_name, obj, filterset)

            if queryset_filter_item:
                queryset_filter &= queryset_filter_item

        return queryset_filter

    @classmethod
    def get_queryset_filter_default(cls, field_name, obj, filterset=None):
        """Return a queryset filter for a specific field.

        Args:
            filterset (FilterSet): instance of a filterset
            field_name (str): name of the field in the DynamicGroupMap
            obj (): instance of the object

        Returns:
            queryset filter
        """

        # Fallback to a class-defined FilterSet object if not provided.
        if filterset is None:
            filterset = cls.filterset()

        # FIXME(jathan): Add check to ensure that the field has a field_name property
        field = filterset.declared_filters[field_name]

        # Ensure that the field is present on the model, or bomb out.
        model_field = get_model_field(obj._meta.model, field_name)
        if model_field is None:
            logger.debug("Declared filter field %s is not a model field", field_name)
            return None

        derived_field = filterset.filter_for_field(model_field, field_name)

        # If the declared field type (e.g. `BooleanFilter`) doesn't match the model's derived field
        # type (e.g. `ModelMultipleChoiceFilter`), this means the declared field shadows the model
        # field and should be skipped.
        if type(field) != type(derived_field):
            logger.debug("Declared and derived filter field mismatch for %s", field_name)
            return None

        # Construct the value of the query based on the object and filter field attributes.
        field_parts = field.field_name.split("__")
        query_value = extract_value_from_object_from_queryset(obj, field_parts)

        # Construct the query label first
        query_label = f"filter__{field_name}"

        # Field of type list (multichoice)
        #  if query_value is not null, search for value in list or empty list
        #  if query_value is None, list must be empty
        if isinstance(field, django_filters.ModelMultipleChoiceFilter):
            if query_value:
                return Q(**{f"{query_label}__contains": query_value}) | Q(**{f"{query_label}__exact": []})

            return Q(**{f"{query_label}__exact": []})

        return Q(**{f"{query_label}__exact": query_value})

    @classmethod
    def get_queryset_filter_tag(cls, field_name, obj, filterset=None):
        """Return a queryset filter for the tag field.

        Args:
            filterset (FilterSet): instance of a filterset
            field_name (str]): name of the field in the DynamicGroupMap
            obj (): instance of the object

        Returns:
            queryset filter
        """
        # TODO only 1 tag is supported, but enforce that.
        tag_slugs = [tag for tag in obj.tags.slugs()]

        if tag_slugs:
            query_filter = Q(filter__tag__exact=[])
            for tag in tag_slugs:
                query_filter |= Q(filter__tag__contains=tag)

            return query_filter

        return Q(filter__tag__exact=[])
