from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.urls import reverse

from tree_queries.models import TreeNode

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.extras.models import StatusModel
from nautobot.extras.utils import extras_features, FeatureQuery
from nautobot.utilities.fields import NaturalOrderingField
from nautobot.utilities.tree_queries import TreeManager, TreeQuerySet


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
    nestable = models.BooleanField(
        default=False,
        help_text="Allow Locations of this type to be parents/children of other Locations of this same type",
    )

    objects = TreeManager()

    csv_headers = ["name", "slug", "parent", "description", "nestable", "content_types"]

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
            self.nestable,
            ",".join(f"{ct.app_label}.{ct.model}" for ct in self.content_types.order_by("app_label", "model")),
        )

    def clean(self):
        """
        Check changes to the nestable flag for validity.

        Also, disallow LocationTypes whose name conflicts with existing location-related models, to avoid confusion.

        In the longer term we will collapse these other models into special cases of LocationType.

        Also, disallow re-parenting a LocationType if there are Locations already using this LocationType.
        """
        super().clean()

        if self.present_in_database:
            prior_nestable = LocationType.objects.get(pk=self.pk).nestable
            if (
                prior_nestable
                and not self.nestable
                and Location.objects.filter(location_type=self, parent__location_type=self).exists()
            ):
                raise ValidationError(
                    {
                        "nestable": "There are existing nested Locations of this type, "
                        "so changing this Location Type to be non-nestable is not permitted."
                    }
                )

        if self.name.lower() in [
            "region",
            "regions",
            "site",
            "sites",
            "rackgroup",
            "rackgroups",
            "rack group",
            "rack groups",
        ]:
            raise ValidationError({"name": "This name is reserved for future use."})

        if (
            self.present_in_database
            and self.parent != LocationType.objects.get(pk=self.pk).parent
            and self.locations.exists()
        ):
            raise ValidationError(
                {
                    "parent": "This LocationType currently has Locations using it, "
                    "therefore its parent cannot be changed at this time."
                }
            )

    @property
    def display(self):
        """
        Include the parent type names as well in order to provide UI clarity.
        `self.ancestors()` returns all the preceding nodes from the top down.
        So if we are looking at node C and its node structure is the following:
            A
           /
          B
         /
        C
        This method will return "A → B → C".
        Note that `self.ancestors()` may throw an `ObjectDoesNotExist` during bulk-delete operations.
        """
        display_str = ""
        try:
            for ancestor in self.ancestors():
                display_str += ancestor.name + " → "
        except ObjectDoesNotExist:
            pass
        finally:
            display_str += self.name
            return display_str  # pylint: disable=lost-exception


class LocationQuerySet(TreeQuerySet):
    def get_for_model(self, model):
        """Filter locations to only those that can accept the given model class."""
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.filter(location_type__content_types=content_type)


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
          Location (location_type="Building")
            Location (location_type="Room")
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
    slug = AutoSlugField(populate_from=["parent__slug", "name"])
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

    objects = LocationQuerySet.as_manager(with_tree_fields=True)

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
        unique_together = [["parent", "name"]]

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

    @property
    def display(self):
        """
        Location name is unique per parent but not globally unique, so include parent information as context.
        `self.ancestors()` returns all the preceding nodes from the top down.
        So if we are looking at node C and its node structure is the following:
            A
           /
          B
         /
        C
        This method will return "A → B → C".

        Note that `self.ancestors()` may throw an `ObjectDoesNotExist` during bulk-delete operations.
        """
        display_str = ""
        try:
            for ancestor in self.ancestors():
                display_str += ancestor.name + " → "
        except ObjectDoesNotExist:
            pass
        finally:
            display_str += self.name
            return display_str  # pylint: disable=lost-exception

    def validate_unique(self, exclude=None):
        # Check for a duplicate name on a Location with no parent.
        # This is necessary because Django does not consider two NULL fields to be equal.
        if self.parent is None:
            if Location.objects.exclude(pk=self.pk).filter(parent__isnull=True, name=self.name).exists():
                raise ValidationError({"name": "A root-level location with this name already exists."})

        super().validate_unique(exclude=exclude)

    def clean(self):
        super().clean()

        # Prevent changing location type as that would require a whole bunch of cascading logic checks,
        # e.g. what if the new type doesn't allow all of the associated objects that the old type did?
        if self.present_in_database:
            prior_location_type = Location.objects.get(pk=self.pk).location_type
            if self.location_type != prior_location_type:
                raise ValidationError(
                    {
                        "location_type": f"Changing the type of an existing Location (from {prior_location_type} to "
                        f"{self.location_type} in this case) is not permitted."
                    }
                )

        if self.location_type.parent is None:
            # We shouldn't have a parent, *unless* our own location type is permitted to be nested.
            if self.parent is not None:
                if self.location_type.nestable:
                    if self.parent.location_type != self.location_type:
                        raise ValidationError(
                            {
                                "parent": f"A Location of type {self.location_type} may only have "
                                "a Location of the same type as its parent."
                            }
                        )
                else:  # No parent type, and not nestable, therefore should never have a parent.
                    raise ValidationError(
                        {"parent": f"A Location of type {self.location_type} must not have a parent Location."}
                    )

                # In a future release, Site will become a kind of Location, and the resulting data migration will be
                # much cleaner if it doesn't have to deal with Locations that have two "parents".
                if self.site is not None:
                    raise ValidationError(
                        {"site": "A Location cannot have both a parent Location and an associated Site."}
                    )

            else:  # No parent, which is good, but then we must have a site.
                if self.site is None:
                    # Remove this in the future once Site and Region become special cases of Location;
                    # at that point a "root" LocationType will correctly have no site associated.
                    raise ValidationError(
                        {"site": f"A Location of type {self.location_type} must have an associated Site."}
                    )

        else:  # Our location type has a parent type of its own
            # We must *not* have a site.
            # In a future release, Site will become a kind of Location, and the resulting data migration will be
            # much cleaner if it doesn't have to deal with Locations that have two "parents".
            if self.site is not None:
                raise ValidationError(
                    {"site": f"A location of type {self.location_type} must not have an associated Site."}
                )

            # We *must* have a parent location.
            if self.parent is None:
                raise ValidationError(
                    {"parent": f"A Location of type {self.location_type} must have a parent Location."}
                )

            # Is the parent location of a correct type?
            if self.location_type.nestable:
                if self.parent.location_type not in (self.location_type, self.location_type.parent):
                    raise ValidationError(
                        {
                            "parent": f"A Location of type {self.location_type} can only have a Location "
                            f"of the same type or of type {self.location_type.parent} as its parent."
                        }
                    )
            else:
                if self.parent.location_type != self.location_type.parent:
                    raise ValidationError(
                        {
                            "parent": f"A Location of type {self.location_type} can only have a Location "
                            f"of type {self.location_type.parent} as its parent."
                        }
                    )
