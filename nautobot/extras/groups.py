import logging
import urllib

from django import forms
from django.urls import reverse
from django.utils.functional import classproperty

from nautobot.utilities.utils import get_filterset_for_model, get_form_for_model, get_route_for_model


logger = logging.getLogger(__name__)


def dynamicgroup_map_factory(model):
    """
    Generate a `FooDynamicGroupMap` class for a given `model`.

    Any exceptions from underlying calls will bubble up.
    """

    filterset_class = get_filterset_for_model(model)
    filterform_class = get_form_for_model(model, form_prefix="Filter")
    form_class = get_form_for_model(model)

    group_map = type(
        str("%sDynamicGroupMap" % model._meta.object_name),
        (BaseDynamicGroupMap,),
        {
            "model": model,
            "filterset_class": filterset_class,
            "filterform_class": filterform_class,
            "form_class": form_class,
        },
    )

    return group_map


class BaseDynamicGroupMap:
    """
    Dynamic Group mapping used to generate mappings for each model class.

    This class itself should not be invoked directly as the class variables will
    not be populated and most class methods will fail.
    """

    model = None
    form_class = None
    filterform_class = None
    filterset_class = None

    # This is used as a `startswith` check on field names, so these can be
    # explicit fields or just substrings.
    #
    # Currently this means skipping "search", custom fields, and custom relationships.
    #
    # FIXME(jathan): As one example, `DeviceFilterSet.q` filter searches in `comments`. The issue
    # really being that this field renders as a textarea and it's not cute in the UI. Might be able
    # to dynamically change the widget if we decide we do want to support this field.
    #
    # Type: tuple
    exclude_filter_fields = ("q", "cr", "cf", "comments")  # Must be a tuple

    @classproperty
    def base_url(cls):
        if cls.model is None:
            return ""
        route_name = get_route_for_model(cls.model, "list")
        return reverse(route_name)

    @classmethod
    def fields(cls):
        """Return all FilterForm fields in a dictionary."""

        # Get model form and fields
        modelform = cls.form_class()
        modelform_fields = modelform.fields

        # Get filter form and fields
        filterform = cls.filterform_class()
        filterform_fields = filterform.fields

        # Get filterset and fields
        filterset = cls.filterset_class()
        filterset_fields = filterset.filters

        # Get dynamic group filter field mappings (if any)
        dynamic_group_filter_fields = getattr(cls.model, "dynamic_group_filter_fields", {})

        # Model form fields that aren't on the filter form
        missing_fields = set(modelform_fields).difference(filterform_fields)

        # Try a few ways to see if a missing field can be added to the filter fields.
        for missing_field in missing_fields:
            # Skip excluded fields
            if missing_field.startswith(cls.exclude_filter_fields):
                logger.debug("Skipping excluded form field: %s", missing_field)
                continue

            # In some cases, fields exist in the model form AND by another name # in the filter form
            # (e.g. model form: `cluster` -> filterset: `cluster_id`) yet are omitted from the
            # filter form (e.g. filter form has "cluster_id" but not "cluster"). We only want to add
            # them if-and-only-if they aren't already in `filterform_fields`.
            if missing_field in dynamic_group_filter_fields:
                mapped_field = dynamic_group_filter_fields[missing_field]
                if mapped_field in filterform_fields:
                    logger.debug(
                        "Skipping missing form field %s; mapped to %s filter field", missing_field, mapped_field
                    )
                    continue

            # If the missing field isn't even in the filterset, move on.
            try:
                filterset_field = filterset_fields[missing_field]
            except KeyError:
                logger.debug("Skipping %s: doesn't have a filterset field", missing_field)
                continue

            # Get the missing model form field so we can use it to add to the filterform_fields.
            modelform_field = modelform_fields[missing_field]

            # Replace the modelform_field with the correct type for the UI. At this time this is
            # only being done for CharField since in the filterset form this ends up being a
            # `MultVarCharField` (dynamically generated from from `MultiValueCharFilter`) which is
            # not correct for char fields.
            if isinstance(modelform_field, forms.CharField):
                # Get ready to replace the form field w/ correct widget.
                new_modelform_field = filterset_field.field
                new_modelform_field.widget = modelform_field.widget

                # If `required=True` was set on the model field, pop "required" from the widget
                # attributes. Filter fields should never be required!
                if modelform_field.required:
                    new_modelform_field.widget.attrs.pop("required")

                modelform_field = new_modelform_field

            # Carry over the `to_field_name` to the modelform_field.
            to_field_name = filterset_field.extra.get("to_field_name")
            if to_field_name is not None:
                modelform_field.to_field_name = to_field_name

            logger.debug("Added %s (%s) to filter fields", missing_field, modelform_field.__class__.__name__)
            filterform_fields[missing_field] = modelform_field

        # Reduce down to a final dict of desired fields.
        return_fields = {}
        for field_name, filter_field in filterform_fields.items():
            # Skip excluded fields
            if field_name.startswith(cls.exclude_filter_fields):
                logger.debug("Skipping excluded filter field: %s", field_name)
                continue

            return_fields[field_name] = filter_field

        return return_fields

    @classmethod
    def get_queryset(cls, filter_params, flat=False):
        """
        Return a queryset matching the dynamic group `filter_params`.

        The queryset is generated based of the FilterSet for this map.
        """
        filterset = cls.filterset_class(filter_params, cls.model.objects.all())

        if flat:
            return filterset.qs.values_list("pk", flat=True)
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
