from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.html import format_html
from taggit.models import GenericUUIDTaggedItemBase

from nautobot.core.choices import ColorChoices
from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import ColorField
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.extras.models.mixins import SavedViewMixin
from nautobot.extras.utils import extras_features, TaggableClassesQuery

# These imports are in this particular order because of circular import problems
from .change_logging import ChangeLoggedModel
from .customfields import CustomFieldModel
from .mixins import ContactMixin, DynamicGroupsModelMixin, NotesMixin
from .relationships import RelationshipModel

#
# Tags
#


class TagQuerySet(RestrictedQuerySet):
    """Queryset for `Tags` objects."""

    def get_for_model(self, model):
        """
        Return all `Tags` assigned to the given model.
        """
        return self.filter(content_types__model=model._meta.model_name, content_types__app_label=model._meta.app_label)


# Tag *should* be a `NameColorContentTypesModel` but that way lies circular import purgatory. Sigh.
@extras_features(
    "custom_validators",
)
class Tag(
    ChangeLoggedModel,
    ContactMixin,
    CustomFieldModel,
    DynamicGroupsModelMixin,
    NotesMixin,
    RelationshipModel,
    SavedViewMixin,
    BaseModel,
):
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="tags",
        limit_choices_to=TaggableClassesQuery(),
    )
    color = ColorField(default=ColorChoices.COLOR_GREY)
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
    )

    objects = BaseManager.from_queryset(TagQuerySet)()

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]

    def get_color_display(self):
        return format_html('<span class="label color-block" style="background-color: #{}">&nbsp;</span>', self.color)

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

    documentation_static_path = "docs/user-guide/platform-functionality/tag.html"
    is_metadata_associable_model = False

    natural_key_field_names = ["pk"]

    class Meta:
        index_together = ("content_type", "object_id")
        unique_together = [["content_type", "object_id", "tag"]]
