from django.contrib.contenttypes.fields import GenericRelation
from django.db import models
from django.db.models import Q
from django.urls import reverse
from mptt.models import MPTTModel, TreeForeignKey
from timezone_field import TimeZoneField

from nautobot.dcim.fields import ASNField
from nautobot.extras.models import StatusModel
from nautobot.extras.utils import extras_features
from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.utilities.fields import NaturalOrderingField
from nautobot.utilities.mptt import TreeManager

__all__ = (
    "Region",
    "Site",
)


#
# Regions
#


@extras_features(
    "custom_fields",
    "custom_validators",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class Region(MPTTModel, OrganizationalModel):
    """
    Sites can be grouped within geographic Regions.
    """

    parent = TreeForeignKey(
        to="self",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
        db_index=True,
    )
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(max_length=200, blank=True)

    objects = TreeManager()

    csv_headers = ["name", "slug", "parent", "description"]

    class MPTTMeta:
        order_insertion_by = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:region", args=[self.pk])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.parent.name if self.parent else None,
            self.description,
        )

    def get_site_count(self):
        return Site.objects.filter(Q(region=self) | Q(region__in=self.get_descendants())).count()

    def to_objectchange(self, action, object_data_exclude=None, **kwargs):
        if object_data_exclude is None:
            object_data_exclude = []
        # Remove MPTT-internal fields
        object_data_exclude += ["level", "lft", "rght", "tree_id"]
        return super().to_objectchange(action, object_data_exclude=object_data_exclude, **kwargs)


#
# Sites
#


@extras_features(
    "custom_fields",
    "custom_links",
    "export_templates",
    "custom_validators",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class Site(PrimaryModel, StatusModel):
    """
    A Site represents a geographic location within a network; typically a building or campus. The optional facility
    field can be used to include an external designation, such as a data center name (e.g. Equinix SV6).
    """

    name = models.CharField(max_length=100, unique=True)
    _name = NaturalOrderingField(target_field="name", max_length=100, blank=True, db_index=True)
    slug = AutoSlugField(populate_from="name")
    region = models.ForeignKey(
        to="dcim.Region",
        on_delete=models.SET_NULL,
        related_name="sites",
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="sites",
        blank=True,
        null=True,
    )
    facility = models.CharField(max_length=50, blank=True, help_text="Local facility ID or description")
    asn = ASNField(
        blank=True,
        null=True,
        verbose_name="ASN",
        help_text="32-bit autonomous system number",
    )
    time_zone = TimeZoneField(blank=True)
    description = models.CharField(max_length=200, blank=True)
    physical_address = models.CharField(max_length=200, blank=True)
    shipping_address = models.CharField(max_length=200, blank=True)
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
    contact_name = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True, verbose_name="Contact E-mail")
    comments = models.TextField(blank=True)
    images = GenericRelation(to="extras.ImageAttachment")

    csv_headers = [
        "name",
        "slug",
        "status",
        "region",
        "tenant",
        "facility",
        "asn",
        "time_zone",
        "description",
        "physical_address",
        "shipping_address",
        "latitude",
        "longitude",
        "contact_name",
        "contact_phone",
        "contact_email",
        "comments",
    ]
    clone_fields = [
        "status",
        "region",
        "tenant",
        "facility",
        "asn",
        "time_zone",
        "description",
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

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("dcim:site", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.get_status_display(),
            self.region.name if self.region else None,
            self.tenant.name if self.tenant else None,
            self.facility,
            self.asn,
            self.time_zone,
            self.description,
            self.physical_address,
            self.shipping_address,
            self.latitude,
            self.longitude,
            self.contact_name,
            self.contact_phone,
            self.contact_email,
            self.comments,
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
