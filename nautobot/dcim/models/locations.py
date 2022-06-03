from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.extras.models import StatusModel
from nautobot.extras.utils import extras_features, FeatureQuery


#
# Note that although both LocationType and Location are tree-like models,
# we do NOT currently use django-mptt for these models. This is a calculated decision based on the following factors:
# 1) django-mptt is mostly unmaintained at this time and we want to get rid of it in Nautobot eventually
# 2) Unlike IPAM models, the nesting of these models is expected to be quite shallow (max depth < 20, typically < 10)
#    and so high efficiency of recursive lookups is not a tremendous concern at this time.

class TreeModel(models.Model):

    parent = models.ForeignKey(
        to="self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
        db_index=True,
    )

    class Meta:
        abstract = True

    def get_ancestors(self):
        if self.parent:
            return self.parent.get_ancestors() + [self.parent]
        return []

    def get_descendants(self):
        return {child: child.get_descendants() for child in self.children.all()}

    def get_depth(self):
        return len(self.get_ancestors())


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class LocationType(TreeModel, OrganizationalModel):
    """
    Definition of a category of Locations, including its hierarchical relationship to other LocationTypes.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(max_length=200, blank=True)
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="location_types",
        verbose_name="Permitted object types",
        limit_choices_to=FeatureQuery("locations"),
        help_text="The object type(s) that can be associated to a Location of this type.",
    )

    csv_headers = ["name", "slug", "parent", "description", "content_types"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:locationtype", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.parent.name if self.parent else None,
            self.description,
            "",  # TODO content-types string
        )


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class Location(TreeModel, StatusModel, PrimaryModel):
    """
    A Location represents an arbitrarily specific geographic location, such as a campus, building, floor, room, etc.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    location_type = models.ForeignKey(
        to="dcim.LocationType",
        on_delete=models.PROTECT,
        related_name="locations",
    )
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.CASCADE,
        related_name="sites",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)
    # TODO images = GenericRelation(to="extras.ImageAttachment")

    csv_headers = [
        "name",
        "slug",
        "location_type",
        "status",
        "parent",
        "description",
    ]

    clone_fields = [
        "location_type",
        "status",
        "parent",
        "description",
    ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:location", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.location_type.name,
            self.get_status_display(),
            self.parent.name if self.parent else None,
            self.description,
        )
