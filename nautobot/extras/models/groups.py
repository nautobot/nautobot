"""Dynamic Groups Models."""

import logging

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel
from nautobot.extras.groups import dynamicgroup_map_factory
from nautobot.extras.querysets import DynamicGroupQuerySet
from nautobot.extras.utils import extras_features


logger = logging.getLogger(__name__)


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class DynamicGroup(OrganizationalModel):
    """Dynamic Group Model."""

    name = models.CharField(max_length=100, unique=True, help_text="Dynamic Group name")
    slug = AutoSlugField(max_length=100, unique=True, help_text="Unique slug", populate_from="name")
    description = models.CharField(max_length=200, blank=True)
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        verbose_name="Object Type",
        help_text="The type of object for this Dynamic Group.",
    )
    # TODO(jathan): Set editable=False that this field doesn't show up in forms.
    # It's a complex field only modified by the DynamicGroupForm internals at
    # this time. I am not happy with this pattern right now but due to the
    # dynamism of the form by merging in the `FooFilterForm` fields, there's not
    # currently an easy way to move this construction logic to the model.
    filter = models.JSONField(
        encoder=DjangoJSONEncoder,
        editable=False,
        default=dict,
        help_text="A JSON-encoded dictionary of filter parameters for group membership",
    )

    objects = DynamicGroupQuerySet.as_manager()

    clone_fields = ["content_type", "filter"]

    class Meta:
        ordering = ["content_type", "name"]

    def __str__(self):
        return self.name

    def get_queryset(self, **kwargs):
        """
        Define custom queryset for group model.

        Any `kwargs` are passed along to `DynamicGroupMap.get_queryset()`.
        """

        model = self.content_type.model_class()

        if not self.filter:
            return model.objects.none()

        qs = self.map.get_queryset(self.filter, **kwargs)

        # Make sure that this instance can't be a member of its own group
        if self.present_in_database and model == self.__class__:
            qs = qs.exclude(pk=self.pk)

        return qs

    @property
    def members(self):
        return self.get_queryset()

    @property
    def count(self):
        """Return the number of objects in the group."""
        return self.get_queryset().count()

    @property
    def map(self):
        """
        Accessor to automatically generated `BaseDynamicGroupMap` class.

        This class object is cached on the instance after the first time it is accessed.
        """

        if getattr(self, "_map", None) is None:
            try:
                model = self.content_type.model_class()
                dynamicgroupmap_class = dynamicgroup_map_factory(model)
            except (models.ObjectDoesNotExist, TypeError):
                dynamicgroupmap_class = None

            self._map = dynamicgroupmap_class

        return self._map

    def get_absolute_url(self):
        return reverse("extras:dynamicgroup", kwargs={"slug": self.slug})

    def get_group_members_url(self):
        """Get URL to group members."""
        if self.map is None:
            return ""

        base_url = self.map.base_url
        filter_str = self.map.urlencode(self.filter)

        if filter_str is not None:
            base_url += f"?{filter_str}"

        return base_url

    def get_filter_fields(self):
        """Return a mapping of `{field_name: filter_field}` for this group's `content_type`."""
        # Fail cleaninly until the object has been created and has a map class.
        if self.map is None:
            return {}

        if not self.present_in_database:
            return {}

        return self.map.fields()

    def set_filter(self, form_data):
        """
        Set all desired fields from `form_data` into `filter` dict.

        :param form_data:
            Dict of filter parameters, generally from a filter form's `cleaned_data`
        """
        # Get the authoritative source of filter fields we want to keep.
        filter_fields = self.get_filter_fields()

        # Populate the filterset from the incoming `form_data`. The filterset's internal form is
        # used for validation, will be used by us to extract cleaned data for final processing.
        filterset_class = self.map.filterset_class
        filterset_class.form_prefix = "filter"
        filterset = filterset_class(form_data)

        # Use the auto-generated filterset form perform creation of the filter dictionary.
        filterset_form = filterset.form

        # It's expected that the incoming data has already been cleaned by a form. This `is_valid()`
        # call is primarily to reduce the fields down to be able to work with the `cleaned_data` from the
        # filterset form, but will also catch errors in case a user-created dict is provided instead.
        if not filterset_form.is_valid():
            raise ValidationError(filterset_form.errors)

        # Perform some type coercions so that they are URL-friendly and reversible, excluding any
        # empty/null value fields.
        new_filter = {}
        for field_name in filter_fields:
            field = filterset_form.fields[field_name]
            field_value = filterset_form.cleaned_data[field_name]

            if isinstance(field, forms.ModelMultipleChoiceField):
                field_to_query = field.to_field_name or "pk"
                new_value = [getattr(item, field_to_query) for item in field_value]

            elif isinstance(field, forms.ModelChoiceField):
                field_to_query = field.to_field_name or "pk"
                new_value = getattr(field_value, field_to_query, None)

            else:
                new_value = field_value

            # Don't store empty values like `None`, [], etc.
            if new_value in (None, "", [], {}):
                logger.debug("[%s] Not storing empty value (%s) for %s", self.name, field_value, field_name)
                continue

            logger.debug("[%s] Setting filter field {%s: %s}", self.name, field_name, field_value)
            new_filter[field_name] = new_value

        self.filter = new_filter

    # FIXME(jathan): Yes, this is "something", but there is discrepancy between explicitly declared
    # fields on `DeviceFilterForm` (for example) vs. the `DeviceFilterSet` filters. For example
    # `Device.name` becomes a `MultiValueCharFilter` that emits a `MultiValueCharField` which
    # expects a list of strings as input. The inverse is not true. It's easier to munge this
    # dictionary when we go to send it to the form, than it is to dynamically coerce the form field
    # types coming and going... For now.
    def get_initial(self):
        """
        Return an form-friendly version of `self.filter` for initial form data.

        This is intended for use to populate the dynamically-generated filter form created by
        `generate_filter_form()`.
        """
        filter_fields = self.get_filter_fields()
        initial_data = self.filter.copy()

        # Brute force to capture the names of any `*CharField` fields.
        char_fields = [f for (f, ftype) in filter_fields.items() if ftype.__class__.__name__.endswith("CharField")]

        # Iterate the char fields and coerce their type to a singular value or
        # an empty string in the case of an empty list.
        for char_field in char_fields:
            if char_field not in initial_data:
                continue

            field_value = initial_data[char_field]

            if isinstance(field_value, list):
                # Either the first (and should be only) item in this list.
                if field_value:
                    new_value = field_value[0]
                # Or empty string if there isn't.
                else:
                    new_value = ""
                initial_data[char_field] = new_value

        return initial_data

    def generate_filter_form(self):
        """
        Generate a `FilterForm` class for use in `DynamicGroup` edit view.

        This form is used to popoulate and validate the filter dictionary.
        """
        filterform_class = self.map and self.map.filterform_class
        filter_fields = self.get_filter_fields()

        # FIXME(jathan): Account for field_order in the newly generated class.
        try:

            class FilterForm(filterform_class):
                prefix = "filter"

                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.fields = filter_fields

        except (AttributeError, TypeError):
            return None

        return FilterForm

    def clean_filter(self):
        """Clean for `self.filter` that uses the filterset_class to validate."""
        if not isinstance(self.filter, dict):
            raise ValidationError({"filter": "Filter must be a dict"})

        # Validate against the filterset's internal form validation.
        filterset = self.map.filterset_class(self.filter)
        if not filterset.is_valid():
            raise ValidationError(filterset.errors)

    def clean(self):
        super().clean()

        if self.present_in_database:
            # Check immutable fields
            database_object = self.__class__.objects.get(pk=self.pk)

            if self.content_type != database_object.content_type:
                raise ValidationError({"content_type": "ContentType cannot be changed once created"})

        # Validate `filter` dict
        self.clean_filter()
