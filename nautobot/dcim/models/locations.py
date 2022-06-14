from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
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
    _with_tree_fields = False


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
        "site",
        "status",
        "parent",
        "description",
    ]

    clone_fields = [
        "location_type",
        "site",
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
            self.site.name if self.site else None,
            self.get_status_display(),
            self.parent.name if self.parent else None,
            self.description,
        )

    @property
    def base_site(self):
        """The site that this Location belongs to, if any, or that its ancestor belongs to, if any."""
        for location in self.ancestors(include_self=True).reverse():
            if location.site is not None:
                return location.site
        return None

    def clean(self):
        super().clean()

        if self.location_type.parent is not None:
            # We must have a parent and it must match the parent location_type.
            if self.parent is None or self.parent.location_type != self.location_type.parent:
                raise ValidationError(
                    {
                        "parent": f"A Location of type {self.location_type} must have "
                        f"a parent Location of type {self.location_type.parent}"
                    }
                )
            # We must *not* have a site.
            # In a future release, Site will become a kind of Location, and the resulting data migration will be
            # much cleaner if it doesn't have to deal with Locations that have two "parents".
            if self.site is not None:
                raise ValidationError(
                    {"site": f"A location of type {self.location_type} must not have an associated Site."}
                )

        # If this location_type does *not* have a parent type,
        # this location must have an associated Site.
        # This check will be removed in the future once Site and Region become special cases of Location;
        # at that point a "root" LocationType will correctly have no parent (or site) associated.
        if self.location_type.parent is None and self.site is None:
            raise ValidationError(
                {"site": f"A Location of type {self.location_type} has no parent Location, but must have a Site."}
            )
