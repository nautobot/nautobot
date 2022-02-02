"""Dynamic Groups Models."""

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.urls import reverse

from nautobot.core.models import BaseModel
from nautobot.extras.groups import BaseDynamicGroupMap
from nautobot.extras.models import ChangeLoggedModel
from nautobot.utilities.utils import get_filterform_for_model, get_filterset_for_model
from nautobot.utilities.querysets import RestrictedQuerySet


class DynamicGroupQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroup` objects."""

    def get_for_object(self, obj):
        """
        Return all `DynamicGroup` assigned to the given object.
        """
        if not isinstance(obj, models.Model):
            raise TypeError(f"{obj} is not an instance of Django Model class")

        # Check if dynamicgroup is supported for this model
        model = obj._meta.model
        dynamicgroupmap = dynamicgroup_map_factory(model)

        # If there's not a map just return an unfiltered queryset?
        # TODO(jathan): Are we sure that's what we want?
        if not dynamicgroupmap:
            return self

        dynamicgroup_filter = dynamicgroupmap.get_queryset_filter(obj)
        return self.filter(content_type=ContentType.objects.get_for_model(obj)).filter(dynamicgroup_filter)


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


class DynamicGroup(BaseModel, ChangeLoggedModel):
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
    filter = models.JSONField(
        encoder=DjangoJSONEncoder,
        editable=False,
        blank=True,
        null=True,
        help_text="A JSON-encoded dictionary of filter parameters for group membership",
    )

    objects = DynamicGroupQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_queryset(self):
        """Define custom queryset for group model."""

        model = self.content_type.model_class()

        if not self.filter:
            return model.objects.none()

        qs = self.map.get_queryset(self.filter)

        # Make sure that this instance can't be a member of its own group
        if self.present_in_database and model == self.__class__:
            qs = qs.exclude(pk=self.pk)

        return qs

    @property
    def members(self):
        return self.get_queryset()

    def count(self):
        """Return the number of objects in the group."""
        return self.get_queryset().count()

    @property
    def map(self):
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
        """Get url to group members."""
        model = self.content_type.model_class()
        # Move this function to dgm class to simplify support for plugin
        base_url = reverse(f"{model._meta.app_label}:{model._meta.model_name}_list")

        filter_str = self.map.get_filterset_as_string(self.filter)

        if filter_str:
            return f"{base_url}?{filter_str}"

        return base_url

    def get_filter_fields(self):
        # Do not present the list of filter options until the object has been created and has a map
        # class.
        if not self.present_in_database or not self.map:
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
            field = form.fields[field_name]

            if isinstance(field, forms.ModelMultipleChoiceField):
                qs = form.cleaned_data[field_name]
                field_to_query = field.to_field_name or "pk"
                print(f"{form.cleaned_data[field_name]} - {field_to_query}")
                values = [str(item) for item in qs.values_list(field_to_query, flat=True)]
                filter[field_name] = values or []

            elif isinstance(field, forms.ModelChoiceField):
                field_to_query = field.to_field_name or "pk"
                value = getattr(form.cleaned_data[field_name], field_to_query, None)
                filter[field_name] = value or None

            elif isinstance(field, forms.NullBooleanField):
                filter[field_name] = form.cleaned_data[field_name]

            else:
                filter[field_name] = form.cleaned_data[field_name]
                print(f"{field_name}: {form.cleaned_data[field_name]}")

        self.filter = filter
        self.save()

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
