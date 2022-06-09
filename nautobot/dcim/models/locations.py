from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.urls import reverse

from tree_queries.models import TreeNode
from tree_queries.query import TreeManager as TreeManager_, TreeQuerySet as TreeQuerySet_

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.extras.models import StatusModel
from nautobot.extras.utils import extras_features, FeatureQuery
from nautobot.utilities.querysets import RestrictedQuerySet


class TreeQuerySet(TreeQuerySet_, RestrictedQuerySet):
    pass

class TreeManager(models.Manager.from_queryset(TreeQuerySet), TreeManager_):
    _with_tree_fields = True


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class LocationType(TreeNode, OrganizationalModel):
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

    objects = TreeManager()

    csv_headers = ["name", "slug", "parent", "description", "content_types"]

    class Meta:
        ordering = ("name",)

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
class Location(TreeNode, StatusModel, PrimaryModel):
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

    objects = TreeManager()

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

    class Meta:
        ordering = ("name",)

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
