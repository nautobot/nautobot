from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from taggit.models import TagBase, GenericUUIDTaggedItemBase

from nautobot.extras.models import ChangeLoggedModel, CustomFieldModel
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.utils import extras_features, TaggableClassesQuery
from nautobot.core.models import BaseModel
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.fields import ColorField
from nautobot.utilities.querysets import RestrictedQuerySet


#
# Tags
#


class TagQuerySet(RestrictedQuerySet):
    """Queryset for `Tags` objects."""

    def get_for_model(self, model):
        """
        Return all `Tags` assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.filter(content_types=content_type)

    def get_by_natural_key(self, name):
        return self.get(name=name)


@extras_features(
    "custom_fields",
    "custom_validators",
    "relationships",
)
class Tag(TagBase, BaseModel, ChangeLoggedModel, CustomFieldModel, RelationshipModel, NotesMixin):
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="tags",
        limit_choices_to=TaggableClassesQuery(),
    )
    color = ColorField(default=ColorChoices.COLOR_GREY)
    description = models.CharField(
        max_length=200,
        blank=True,
    )

    csv_headers = ["name", "slug", "color", "description"]

    objects = TagQuerySet.as_manager()

    class Meta:
        ordering = ["name"]

    def natural_key(self):
        return (self.name,)

    def get_absolute_url(self):
        return reverse("extras:tag", args=[self.slug])

    def to_csv(self):
        return (self.name, self.slug, self.color, self.description)

    def validate_content_types_removal(self, content_types_id):
        """Validate content_types to be removed are not tagged to a model"""
        errors = {}

        removed_content_types = self.content_types.exclude(id__in=content_types_id)

        # check if tag is assigned to any of the removed content_types
        for content_type in removed_content_types:
            model = content_type.model_class()
            if model.objects.filter(tags=self).exists():
                errors.setdefault("content_types", []).append(
                    f"Unable to remove {model._meta.label_lower}. Dependent objects were found."
                )

        return errors


class TaggedItem(BaseModel, GenericUUIDTaggedItemBase):
    tag = models.ForeignKey(to=Tag, related_name="%(app_label)s_%(class)s_items", on_delete=models.CASCADE)
    object_id = models.UUIDField()

    class Meta:
        index_together = ("content_type", "object_id")
