from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from taggit.models import TagBase, GenericUUIDTaggedItemBase

from nautobot.extras.models import ChangeLoggedModel, CustomFieldModel
from nautobot.extras.models.relationships import RelationshipModel
from nautobot.extras.utils import extras_features, ModelSubclassesQuery
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


@extras_features(
    "custom_fields",
    "custom_validators",
    "relationships",
)
class Tag(TagBase, BaseModel, ChangeLoggedModel, CustomFieldModel, RelationshipModel):
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="tags",
        limit_choices_to=ModelSubclassesQuery(),
        blank=True,
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

    def get_absolute_url(self):
        return reverse("extras:tag", args=[self.slug])

    def slugify(self, tag, i=None):
        # Allow Unicode in Tag slugs (avoids empty slugs for Tags with all-Unicode names)
        slug = slugify(tag, allow_unicode=True)
        if i is not None:
            slug += "_%d" % i
        return slug

    def to_csv(self):
        return (self.name, self.slug, self.color, self.description)


class TaggedItem(BaseModel, GenericUUIDTaggedItemBase):
    tag = models.ForeignKey(to=Tag, related_name="%(app_label)s_%(class)s_items", on_delete=models.CASCADE)
    object_id = models.UUIDField()

    class Meta:
        index_together = ("content_type", "object_id")
