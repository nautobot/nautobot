from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import classproperty

from timezone_field import TimeZoneField

from nautobot.core.models.fields import NaturalOrderingField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.tree_queries import TreeManager, TreeModel, TreeQuerySet
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.fields import ASNField
from nautobot.extras.models import StatusField
from nautobot.extras.utils import extras_features, FeatureQuery


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class LocationType(TreeModel, OrganizationalModel):
    """
    Definition of a category of Locations, including its hierarchical relationship to other LocationTypes.

    A LocationType also specifies the content types that can be associated to a Location of this category.
    For example a "Building" LocationType might allow Prefix and VLANGroup, but not Devices,
    while a "Room" LocationType might allow Racks and Devices.
    """

    name = models.CharField(max_length=100, unique=True)
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

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

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


class LocationQuerySet(TreeQuerySet):
    def get_for_model(self, model):
        """Filter locations to only those that can accept the given model class."""
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.filter(location_type__content_types=content_type)


class LocationManager(TreeManager.from_queryset(LocationQuerySet)):
    pass


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class Location(TreeModel, PrimaryModel):
    """
    A Location represents an arbitrarily specific geographic location, such as a campus, building, floor, room, etc.

    As presently implemented, Location is a model less specific (and more broadly applicable) than a RackGroup:
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

    As such, as presently implemented, every Location, depends on its LocationType, do/don't have a parent Location.
    In the future, we plan to collapse RackGroup into the Location model.
    """

    # A Location's name is unique within context of its parent, not globally unique.
    name = models.CharField(max_length=100, db_index=True)
    _name = NaturalOrderingField(target_field="name", max_length=100, blank=True, db_index=True)
    location_type = models.ForeignKey(
        to="dcim.LocationType",
        on_delete=models.PROTECT,
        related_name="locations",
    )
    status = StatusField(blank=False, null=False)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="locations",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)
    facility = models.CharField(max_length=50, blank=True, help_text="Local facility ID or description")
    asn = ASNField(
        blank=True,
        null=True,
        verbose_name="ASN",
        help_text="32-bit autonomous system number",
    )
    time_zone = TimeZoneField(blank=True)
    physical_address = models.TextField(blank=True)
    shipping_address = models.TextField(blank=True)
    latitude = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="GPS coordinate (latitude)",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        blank=True,
        null=True,
        help_text="GPS coordinate (longitude)",
    )
    contact_name = models.CharField(max_length=100, blank=True)
    contact_phone = models.CharField(max_length=50, blank=True)
    contact_email = models.EmailField(blank=True, verbose_name="Contact E-mail")
    comments = models.TextField(blank=True)
    images = GenericRelation(to="extras.ImageAttachment")

    objects = LocationManager()

    clone_fields = [
        "location_type",
        "status",
        "parent",
        "tenant",
        "description",
        "facility",
        "asn",
        "time_zone",
        "physical_address",
        "shipping_address",
        "latitude",
        "longitude",
        "contact_name",
        "contact_phone",
        "contact_email",
    ]

    class Meta:
        ordering = ("_name",)
        unique_together = [["parent", "name"]]

    def __str__(self):
        return self.name

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def natural_key_field_lookups(cls):  # pylint: disable=no-self-argument
        """
        Due to the recursive nature of Location's natural key, we need a custom implementation of this property.

        When LOCATION_NAME_AS_NATURAL_KEY is set in settings or Constance, we use just the `name` for simplicity,
        even though it's not technically guaranteed to be globally unique.

        Otherwise, this returns a set of natural key lookups based on the current maximum depth of the Location tree.
        For example if the tree is 2 layers deep, it will return ["name", "parent__name", "parent__parent__name"].

        Without this custom implementation, the generic `natural_key_field_lookups` would recurse infinitely.
        """
        if get_settings_or_config("LOCATION_NAME_AS_NATURAL_KEY"):
            # opt-in simplified "pseudo-natural-key"
            return ["name"]

        lookups = []
        name = "name"
        for _ in range(cls.objects.max_tree_depth() + 1):
            lookups.append(name)
            name = f"parent__{name}"
        return lookups

    @classmethod
    def natural_key_args_to_kwargs(cls, args):
        """Handle the possibility that more recursive "parent" lookups were specified than we initially expected."""
        args = list(args)
        natural_key_field_lookups = list(cls.natural_key_field_lookups)
        while len(args) < len(natural_key_field_lookups):
            args.append(None)
        while len(args) > len(natural_key_field_lookups):
            natural_key_field_lookups.append(f"parent__{natural_key_field_lookups[-1]}")
        return dict(zip(natural_key_field_lookups, args))

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

        else:  # Our location type has a parent type of its own
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

    def clean_fields(self, exclude=None):
        """Explicitly convert latitude/longitude to strings to avoid floating-point precision errors."""

        if self.longitude is not None and isinstance(self.longitude, float):
            decimal_places = self._meta.get_field("longitude").decimal_places
            self.longitude = f"{self.longitude:.{decimal_places}f}"
        if self.latitude is not None and isinstance(self.latitude, float):
            decimal_places = self._meta.get_field("latitude").decimal_places
            self.latitude = f"{self.latitude:.{decimal_places}f}"
        super().clean_fields(exclude)
