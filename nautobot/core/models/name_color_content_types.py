from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from nautobot.core.fields import AutoSlugField
from nautobot.core.models import BaseModel

# Importing CustomFieldModel, ChangeLoggedModel, RelationshipModel from  nautobot.extras.models
# caused circular import error
from nautobot.extras.models.customfields import CustomFieldModel
from nautobot.extras.models.change_logging import ChangeLoggedModel
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.models.mixins import DynamicGroupMixin, NotesMixin
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.fields import ColorField
from nautobot.utilities.querysets import RestrictedQuerySet


class ContentTypeRelatedQuerySet(RestrictedQuerySet):
    def get_for_model(self, model):
        """
        Return all `self.model` instances assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.filter(content_types=content_type)

    def get_by_natural_key(self, name):
        return self.get(name=name)


# TODO(timizuo): Inheriting from OrganizationalModel here causes partial import error
class NameColorContentTypesModel(
    BaseModel,
    ChangeLoggedModel,
    CustomFieldModel,
    RelationshipModel,
    NotesMixin,
    DynamicGroupMixin,
):
    """
    This abstract base properties model contains fields and functionality that are
    shared amongst models that requires these fields: name, color, content_types and description.
    """

    # TODO(timizuo): Tag should inherit from this model; but
    #  cant because of field conflicts: name and slug field.
    content_types = models.ManyToManyField(
        to=ContentType,
        help_text="The content type(s) to which this model applies.",
    )
    name = models.CharField(max_length=100, unique=True)
    # TODO (timizuo): Remove slug
    slug = AutoSlugField(populate_from="name", max_length=100)
    color = ColorField(default=ColorChoices.COLOR_GREY)
    description = models.CharField(
        max_length=200,
        blank=True,
    )

    objects = ContentTypeRelatedQuerySet.as_manager()

    csv_headers = ["name", "slug", "color", "content_types", "description"]
    clone_fields = ["color", "content_types"]

    class Meta:
        ordering = ["name"]
        abstract = True

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    def get_absolute_url(self):
        ct = f"{self._meta.app_label}:{self._meta.model_name}"
        # TODO(timizuo): Replace self.slug with natural key or pk
        return reverse(ct, args=[self.slug])

    def get_content_types(self):
        return ",".join(f"{ct.app_label}.{ct.model}" for ct in self.content_types.all())

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.color,
            f'"{self.get_content_types()}"',  # Wrap labels in double quotes for CSV
            self.description,
        )
