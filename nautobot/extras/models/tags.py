from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from taggit.models import TagBase, GenericUUIDTaggedItemBase

from nautobot.core.choices import ColorChoices
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import ColorField
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.extras.models import ChangeLoggedModel, CustomFieldModel
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.utils import extras_features, TaggableClassesQuery


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
    "custom_validators",
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

    objects = BaseManager.from_queryset(TagQuerySet)()

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


class TaggedItemManager(BaseManager.from_queryset(RestrictedQuerySet)):
    def get_by_natural_key(self, *args):
        return self.get(
            tag__name=args[0],
            content_type__app_label=args[1],
            content_type__model=args[2],
            object_id=args[3],
        )


class TaggedItem(BaseModel, GenericUUIDTaggedItemBase):
    tag = models.ForeignKey(to=Tag, related_name="%(app_label)s_%(class)s_items", on_delete=models.CASCADE)
    object_id = models.UUIDField()

    objects = TaggedItemManager()

    class Meta:
        index_together = ("content_type", "object_id")

    @classmethod
    def get_natural_key_fields(cls):
        return ["tag__name", "content_type__app_label", "content_type__model", "object_id"]

    def natural_key(self):
        return [self.tag.name, self.content_type.app_label, self.content_type.model, self.object_id]
