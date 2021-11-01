"""Dynamic Groups Models."""

from django.conf import settings
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.db.models import Model

from nautobot.extras.models import ChangeLoggedModel
from nautobot.core.models import BaseModel
from nautobot.utilities.utils import get_filterset_for_model, get_dynamicgroupmap_for_model
from nautobot.utilities.querysets import RestrictedQuerySet


class DynamicGroupQuerySet(RestrictedQuerySet):
    """Queryset for `DynamicGroup` objects."""

    def get_for_object(self, obj):
        """
        Return all `DynamicGroup` assigned to the given object.
        """
        if not isinstance(obj, Model):
            raise TypeError(f"{obj} is not an instance of Django Model class")

        # Check if dynamicgroup is supported for this model
        model = obj._meta.model
        dynamicgroupmap = get_dynamicgroupmap_for_model(model)

        if not dynamicgroupmap:
            return self

        dynamicgroup_filter = dynamicgroupmap.get_group_queryset_filter(obj)
        return self.filter(content_type=ContentType.objects.get_for_model(obj)).filter(dynamicgroup_filter)


class DynamicGroup(BaseModel, ChangeLoggedModel):
    """Dynamic Group Model."""

    name = models.CharField(max_length=100, unique=True, help_text="Internal Dynamic Group name")
    slug = models.SlugField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)

    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        verbose_name="Object Type",
        help_text="The type of object for this group.",
    )

    filter = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        help_text="",
    )

    objects = DynamicGroupQuerySet.as_manager()

    def __str__(self):
        """Group Model string return."""
        return self.name.capitalize()

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

    def get_queryset(self):
        """Define custom queryset for group model."""

        model = self.content_type.model_class()

        if not self.filter:
            return model.objects.all()

        dynamicgroupmap_class = get_dynamicgroupmap_for_model(model)
        return dynamicgroupmap_class.get_queryset(self.filter)

    def count(self):
        """Return the number of objects in the group."""
        return self.get_queryset().count()

    def get_url_to_group_members(self):
        """Get url to group members."""
        model = self.content_type.model_class()
        # Move this function to dgm class to simplify support for plugin
        base_url = reverse(f"{model._meta.app_label}:{model._meta.model_name}_list")

        dynamicgroupmap_class = get_dynamicgroupmap_for_model(model)

        filter_str = dynamicgroupmap_class.get_filterset_as_string(self.filter)

        if filter_str:
            return f"{base_url}?{filter_str}"

        return base_url
