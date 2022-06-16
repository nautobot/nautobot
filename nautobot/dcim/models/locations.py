from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

from tree_queries.models import TreeNode

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.extras.models import StatusModel
from nautobot.extras.utils import extras_features, FeatureQuery
from nautobot.utilities.fields import NaturalOrderingField
from nautobot.utilities.tree_queries import TreeManager


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

    A LocationType also specifies the content types that can be associated to a Location of this category.
    For example a "Building" LocationType might allow Prefix and VLANGroup, but not Devices,
    while a "Room" LocationType might allow Racks and Devices.
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

    As presently implemented, Location is an intermediary model between Site and RackGroup - more specific than a Site,
    less specific (and more broadly applicable) than a RackGroup:

    Region
      Region
        Site
          Location
            Location
              RackGroup
                Rack
                  Device
              Device
            Prefix
            etc.
          VLANGroup
          Prefix
          etc.

    As such, as presently implemented, every Location either has a parent Location or a "parent" Site.

    In the future, we plan to collapse Region and Site (and likely RackGroup as well) into the Location model.
    """

    # A Location's name is unique within context of its parent, not globally unique.
    name = models.CharField(max_length=100, db_index=True)
    _name = NaturalOrderingField(target_field="name", max_length=100, blank=True, db_index=True)
    # However a Location's slug *is* globally unique.
    slug = AutoSlugField(populate_from=["parent__name", "name"])
    location_type = models.ForeignKey(
        to="dcim.LocationType",
        on_delete=models.PROTECT,
        related_name="locations",
    )
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.CASCADE,
        related_name="locations",
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="locations",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)
    images = GenericRelation(to="extras.ImageAttachment")

    objects = TreeManager()

    csv_headers = [
        "name",
        "slug",
        "location_type",
        "site",
        "status",
        "parent",
        "tenant",
        "description",
    ]

    clone_fields = [
        "location_type",
        "site",
        "status",
        "parent",
        "tenant",
        "description",
    ]

    class Meta:
        ordering = ("_name",)
        constraints = [
            models.UniqueConstraint(name="unique_name_per_parent", fields=["parent", "name"]),
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
            self.site.name if self.site else None,
            self.get_status_display(),
            self.parent.name if self.parent else None,
            self.tenant.name if self.tenant else None,
            self.description,
        )

    @property
    def base_site(self):
        """The site that this Location belongs to, if any, or that its root ancestor belongs to, if any."""
        return self.site or self.ancestors().first().site

    def validate_unique(self, exclude=None):
        # Check for a duplicate name on a Location with no parent.
        # This is necessary because Django does not consider two NULL fields to be equal.
        if self.parent is None:
            if Location.objects.exclude(pk=self.pk).filter(parent__isnull=True, name=self.name).exists():
                raise ValidationError({"name": "A root-level location with this name already exists."})

        super().validate_unique(exclude=exclude)

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
