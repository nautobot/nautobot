"""Dynamic Groups Models."""

import logging

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse

from nautobot.core.models.generics import OrganizationalModel
from nautobot.extras.groups import dynamicgroup_map_factory
from nautobot.extras.utils import extras_features
from nautobot.utilities.querysets import RestrictedQuerySet


logger = logging.getLogger(__name__)


class DynamicGroupQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroup` objects."""

    def get_for_object(self, obj):
        """
        Return all `DynamicGroup` assigned to the given object.
        """
        if not isinstance(obj, models.Model):
            raise TypeError(f"{obj} is not an instance of Django Model class")

        # Extract the content_type fields to optimize the query.
        model = obj._meta.model
        app_label = model._meta.app_label
        model_name = model._meta.model_name

        # Get dynamic groups for this content_type.
        # TODO(jathan): 1 query
        print(">>> GETTING ELIGIBLE GROUPS\n")
        eligible_groups = self.filter(
            content_type__app_label=app_label,
            content_type__model=model_name
        ).select_related("content_type")

        # Filter down to matching groups
        my_groups = []
        # TODO(jathan: 3 queries per DynamicGroup instance
        for dynamic_group in eligible_groups:
            print(">>> GROUP INSTANCE\n")
            if obj.pk in dynamic_group.get_queryset(flat=True):
                my_groups.append(dynamic_group.pk)

        # TODO(jathan): 1 query
        return self.filter(pk__in=my_groups)


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class DynamicGroup(OrganizationalModel):
    """Dynamic Group Model."""

    name = models.CharField(max_length=100, unique=True, help_text="Dynamic Group name")
    slug = models.SlugField(max_length=100, unique=True, help_text="Unique slug")
    description = models.CharField(max_length=200, blank=True)
    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        verbose_name="Object Type",
        help_text="The type of object for this group.",
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
        blank=True,
        null=True,
        help_text="A JSON-encoded dictionary of filter parameters for group membership",
    )

    objects = DynamicGroupQuerySet.as_manager()

    clone_fields = ["content_type", "filter"]

    class Meta:
        ordering = ["content_type", "name"]

    def __str__(self):
        return self.name

    def get_queryset(self, **kwargs):
        """Define custom queryset for group model."""

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
            except models.ObjectDoesNotExist:
                dynamicgroupmap_class = None

            self._map = dynamicgroupmap_class

        return self._map

    def get_absolute_url(self):
        return reverse("extras:dynamicgroup", kwargs={"slug": self.slug})

    def get_group_members_url(self):
        """Get URL to group members."""
        base_url = self.map.base_url
        filter_str = self.map.urlencode(self.filter)

        if filter_str is not None:
            base_url += f"?{filter_str}"

        return base_url

    def get_filter_fields(self):
        # Do not present the list of filter options until the object has been created and has a map
        # class.
        if not self.map:
            return {}

        if not self.present_in_database:
            return {}

        # Add all fields defined in the DynamicGroupMap to the form and populate the default value
        fields = {}
        for field_name, field in self.map.fields().items():
            if field_name in self.filter:
                field.initial = self.filter[field_name]

            fields[field_name] = field

        return fields

    def save_filters(self, form):
        """
        Extract all data from `form` fields into `filter` dictionary and call `save()`.

        This is called from `DynamicGroupForm.save()`.

        :param form:
            A validated instance of `DynamicGroupForm`
        """
        filter = {}
        filter_fields = self.get_filter_fields()
        for field_name in filter_fields:
            if field_name not in form.fields:
                continue

            field = form.fields[field_name]

            if isinstance(field, forms.ModelMultipleChoiceField):
                qs = form.cleaned_data[field_name]
                field_to_query = field.to_field_name or "pk"
                logger.debug("%s - %s", form.cleaned_data[field_name], field_to_query)
                values = [str(item) for item in qs.values_list(field_to_query, flat=True)]
                filter[field_name] = values or []

            elif isinstance(field, forms.ModelChoiceField):
                field_to_query = field.to_field_name or "pk"
                value = getattr(form.cleaned_data[field_name], field_to_query, None)
                filter[field_name] = value or None

            # TODO(jathan): Decide if we need this before removing this code.
            # elif isinstance(field, forms.NullBooleanField):
            #     filter[field_name] = form.cleaned_data[field_name]

            else:
                filter[field_name] = form.cleaned_data[field_name]
                logger.debug("%s: %s", field_name, form.cleaned_data[field_name])

        self.filter = filter
        # FIXME(jathan): Don't call save here. Just dynamically update `.filter`
        # and let the caller worry about save. This also aligns with the current
        # dynamic `FilterForm` pattern which may or may not persist.
        # self.save()

    def clean(self):
        super().clean()

        if self.present_in_database:
            # Check immutable fields
            database_object = self.__class__.objects.get(pk=self.pk)

            if self.content_type != database_object.content_type:
                raise ValidationError({"content_type": "ContentType cannot be changed once created"})

        if not isinstance(self.filter, dict):
            raise ValidationError({"filter": "Filter must be a dict"})

    # def clean(self):
    #     """Group Model clean method."""
    #     model = self.content_type.model_class()

    #     if self.filter:
    #         try:
    #             filterset_class = get_filterset_for_model(model)
    #         except AttributeError:
    #             raise ValidationError(  # pylint: disable=raise-missing-from
    #                 {"filter": "Unable to find a FilterSet for this model."}
    #             )

    #         filterset = filterset_class(self.filter, model.objects.all())

    #         if filterset.errors:
    #             for key in filterset.errors:
    #                 raise ValidationError({"filter": f"{key}: {filterset.errors[key]}"})
