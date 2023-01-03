import logging
import sys

from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from taggit.managers import TaggableManager, _TaggableManager
from taggit.models import GenericUUIDTaggedItemBase, TagBase

from nautobot.core.choices import ColorChoices
from nautobot.core.fields import ColorField
from nautobot.core.models import (
    BaseModel,
    ChangeLoggedModel,
    CustomFieldModel,
    NotesMixin,
    PrimaryModel,
    RelationshipModel,
)
from nautobot.core.querysets import RestrictedQuerySet
from nautobot.extras.utils import TaggableClassesQuery, extras_features

logger = logging.getLogger(__name__)


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


# 2.0 TODO: remove this, force migration to the newer django-taggit API.
class _NautobotTaggableManager(_TaggableManager):
    """Extend _TaggableManager to work around a breaking API change between django-taggit 1.x and 2.x.

    This is a bit confusing, as there's also a related `TaggableManager` class as well.
    `TaggableManager` is the *model field* (subclass of `models.fields.related.RelatedField`),
    while `_TaggableManager` is the *associated manager* (subclass of `models.Manager`).

    For `TaggableManager`, we chose to monkey-patch rather than subclass to override its `formfield` method;
    replacing it with a subclass would create database migrations for every PrimaryModel with a `tags` field.
    In 2.0 we'll want to bite the bullet and make the cutover (#1633).

    For `_TaggableManager`, we can subclass rather than monkey-patching because replacing it *doesn't* require
    a database migration, and this is cleaner than a monkey-patch.
    """

    def set(self, *tags, through_defaults=None, **kwargs):
        """
        Patch model.tags.set() to be backwards-compatible with django-taggit 1.x and forward-compatible with later.

        Both of these approaches are supported:

        - tags.set("tag 1", "tag 2")  # django-taggit 1.x
        - tags.set(["tag 1", "tag 2"])  # django-taggit 2.x and later
        """
        if len(tags) == 1 and not isinstance(tags[0], (self.through.tag_model(), str)):
            # taggit 2.x+ style, i.e. `set([tag, tag, tag])`
            tags = tags[0]
        else:
            # taggit 1.x style, i.e. `set(tag, tag, tag)`
            # Note: logger.warning() only supports a `stacklevel` parameter in Python 3.8 and later
            tags_unpacked = ", ".join([repr(tag) for tag in tags])
            tags_list = list(tags)
            message = "Deprecated `tags.set(%s)` was called, please change to `tags.set(%s)` instead"
            if sys.version_info >= (3, 8):
                logger.warning(message, tags_unpacked, tags_list, stacklevel=2)
            else:  # Python 3.7
                logger.warning(message, tags_unpacked, tags_list)
        return super().set(tags, through_defaults=through_defaults, **kwargs)


class TaggedModel(PrimaryModel):
    """
    Abstract model which adds `tags` to the model
    """

    tags = TaggableManager(through=TaggedItem, manager=_NautobotTaggableManager, ordering=["name"])

    class Meta:
        abstract = True
