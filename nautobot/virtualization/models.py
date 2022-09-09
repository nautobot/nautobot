from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from taggit.managers import TaggableManager

from nautobot.dcim.models import BaseInterface, Device
from nautobot.extras.models import (
    ConfigContextModel,
    CustomFieldModel,
    ObjectChange,
    StatusModel,
    TaggedItem,
)
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.querysets import ConfigContextModelQuerySet
from nautobot.extras.utils import extras_features
from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import BaseModel, OrganizationalModel, PrimaryModel
from nautobot.utilities.config import get_settings_or_config
from nautobot.utilities.fields import NaturalOrderingField
from nautobot.utilities.ordering import naturalize_interface
from nautobot.utilities.query_functions import CollateAsChar
from nautobot.utilities.utils import serialize_object, serialize_object_v2


__all__ = (
    "Cluster",
    "ClusterGroup",
    "ClusterType",
    "VirtualMachine",
    "VMInterface",
)


#
# Cluster types
#


@extras_features(
    "custom_fields",
    "custom_validators",
    "graphql",
    "relationships",
)
class ClusterType(OrganizationalModel):
    """
    A type of Cluster.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "description"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("virtualization:clustertype", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.description,
        )


#
# Cluster groups
#


@extras_features(
    "custom_fields",
    "custom_validators",
    "graphql",
    "relationships",
)
class ClusterGroup(OrganizationalModel):
    """
    An organizational group of Clusters.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "description"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("virtualization:clustergroup", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.description,
        )


#
# Clusters
#


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "locations",
    "relationships",
    "webhooks",
)
class Cluster(PrimaryModel):
    """
    A cluster of VirtualMachines. Each Cluster may optionally be associated with one or more Devices.
    """

    name = models.CharField(max_length=100, unique=True)
    type = models.ForeignKey(to=ClusterType, on_delete=models.PROTECT, related_name="clusters")
    group = models.ForeignKey(
        to=ClusterGroup,
        on_delete=models.PROTECT,
        related_name="clusters",
        blank=True,
        null=True,
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="clusters",
        blank=True,
        null=True,
    )
    site = models.ForeignKey(
        to="dcim.Site",
        on_delete=models.PROTECT,
        related_name="clusters",
        blank=True,
        null=True,
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="clusters",
        blank=True,
        null=True,
    )
    comments = models.TextField(blank=True)

    csv_headers = ["name", "type", "group", "site", "location", "tenant", "comments"]
    clone_fields = [
        "type",
        "group",
        "tenant",
        "site",
        "location",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("virtualization:cluster", args=[self.pk])

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:
            if self.site is not None and self.location.base_site != self.site:
                raise ValidationError(
                    {"location": f'Location "{self.location}" does not belong to site "{self.site}".'}
                )

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'Clusters may not associate to locations of type "{self.location.location_type}".'}
                )

        # If the Cluster is assigned to a Site, verify that all host Devices belong to that Site.
        if self.present_in_database and self.site:
            nonsite_devices = Device.objects.filter(cluster=self).exclude(site=self.site).count()
            if nonsite_devices:
                raise ValidationError(
                    {
                        "site": f"{nonsite_devices} devices are assigned as hosts for this cluster but are not in site {self.site}"
                    }
                )

        # Likewise, verify that host Devices match Location of this Cluster if any
        if self.present_in_database and self.location is not None:
            nonlocation_devices = (
                Device.objects.filter(cluster=self)
                .exclude(location=self.location)
                .exclude(location__isnull=True)
                .count()
            )
            if nonlocation_devices:
                raise ValidationError(
                    {
                        "location": f"{nonlocation_devices} devices are assigned as hosts for this cluster "
                        f'but belong to a location other than "{self.location}".'
                    }
                )

    def to_csv(self):
        return (
            self.name,
            self.type.name,
            self.group.name if self.group else None,
            self.site.name if self.site else None,
            self.location.name if self.location else None,
            self.tenant.name if self.tenant else None,
            self.comments,
        )


#
# Virtual machines
#


@extras_features(
    "custom_fields",
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "relationships",
    "statuses",
    "webhooks",
)
class VirtualMachine(PrimaryModel, ConfigContextModel, StatusModel):
    """
    A virtual machine which runs inside a Cluster.
    """

    cluster = models.ForeignKey(
        to="virtualization.Cluster",
        on_delete=models.PROTECT,
        related_name="virtual_machines",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="virtual_machines",
        blank=True,
        null=True,
    )
    platform = models.ForeignKey(
        to="dcim.Platform",
        on_delete=models.SET_NULL,
        related_name="virtual_machines",
        blank=True,
        null=True,
    )
    name = models.CharField(max_length=64, db_index=True)
    role = models.ForeignKey(
        to="dcim.DeviceRole",
        on_delete=models.PROTECT,
        related_name="virtual_machines",
        limit_choices_to={"vm_role": True},
        blank=True,
        null=True,
    )
    primary_ip4 = models.OneToOneField(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="Primary IPv4",
    )
    primary_ip6 = models.OneToOneField(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="Primary IPv6",
    )
    vcpus = models.PositiveSmallIntegerField(blank=True, null=True, verbose_name="vCPUs")
    memory = models.PositiveIntegerField(blank=True, null=True, verbose_name="Memory (MB)")
    disk = models.PositiveIntegerField(blank=True, null=True, verbose_name="Disk (GB)")
    comments = models.TextField(blank=True)

    objects = ConfigContextModelQuerySet.as_manager()

    csv_headers = [
        "name",
        "status",
        "role",
        "cluster",
        "tenant",
        "platform",
        "vcpus",
        "memory",
        "disk",
        "comments",
    ]
    clone_fields = [
        "cluster",
        "tenant",
        "platform",
        "status",
        "role",
        "vcpus",
        "memory",
        "disk",
    ]
    # 2.0 TODO: Make this go away when we assert filterset/filterform parity. FilterSet fields that
    # are custom on FilterForm that we don't want in DynamicGroup UI edit form because they are
    # already there.
    #
    # This mapping is in the form of:
    #   {missing_form_field_name}: {filterset_field_name_that_duplicates_it}
    dynamic_group_filter_fields = {
        "cluster": "cluster_id",
    }

    class Meta:
        ordering = ("name",)  # Name may be non-unique
        unique_together = [["cluster", "tenant", "name"]]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("virtualization:virtualmachine", args=[self.pk])

    def validate_unique(self, exclude=None):

        # Check for a duplicate name on a VM assigned to the same Cluster and no Tenant. This is necessary
        # because Django does not consider two NULL fields to be equal, and thus will not trigger a violation
        # of the uniqueness constraint without manual intervention.
        if self.tenant is None and VirtualMachine.objects.exclude(pk=self.pk).filter(
            name=self.name, cluster=self.cluster, tenant__isnull=True
        ):
            raise ValidationError({"name": "A virtual machine with this name already exists in the assigned cluster."})

        super().validate_unique(exclude)

    def clean(self):
        super().clean()

        # Validate primary IP addresses
        interfaces = self.interfaces.all()
        for field in ["primary_ip4", "primary_ip6"]:
            ip = getattr(self, field)
            if ip is not None:
                if ip.assigned_object in interfaces:
                    pass
                elif ip.nat_inside is not None and ip.nat_inside.assigned_object in interfaces:
                    pass
                else:
                    raise ValidationError(
                        {
                            field: f"The specified IP address ({ip}) is not assigned to this VM.",
                        }
                    )

    def to_csv(self):
        return (
            self.name,
            self.get_status_display(),
            self.role.name if self.role else None,
            self.cluster.name,
            self.tenant.name if self.tenant else None,
            self.platform.name if self.platform else None,
            self.vcpus,
            self.memory,
            self.disk,
            self.comments,
        )

    @property
    def primary_ip(self):
        if get_settings_or_config("PREFER_IPV4") and self.primary_ip4:
            return self.primary_ip4
        elif self.primary_ip6:
            return self.primary_ip6
        elif self.primary_ip4:
            return self.primary_ip4
        else:
            return None

    @property
    def site(self):
        return self.cluster.site

    @property
    def site_id(self):
        return self.cluster.site_id

    @property
    def location(self):
        return self.cluster.location

    @property
    def location_id(self):
        return self.cluster.location_id


#
# Interfaces
#


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
class VMInterface(BaseModel, BaseInterface, CustomFieldModel, NotesMixin):
    virtual_machine = models.ForeignKey(
        to="virtualization.VirtualMachine",
        on_delete=models.CASCADE,
        related_name="interfaces",
    )
    name = models.CharField(max_length=64, db_index=True)
    _name = NaturalOrderingField(
        target_field="name", naturalize_function=naturalize_interface, max_length=100, blank=True, db_index=True
    )
    description = models.CharField(max_length=200, blank=True)
    untagged_vlan = models.ForeignKey(
        to="ipam.VLAN",
        on_delete=models.SET_NULL,
        related_name="vminterfaces_as_untagged",
        null=True,
        blank=True,
        verbose_name="Untagged VLAN",
    )
    tagged_vlans = models.ManyToManyField(
        to="ipam.VLAN",
        related_name="vminterfaces_as_tagged",
        blank=True,
        verbose_name="Tagged VLANs",
    )
    ip_addresses = GenericRelation(
        to="ipam.IPAddress",
        content_type_field="assigned_object_type",
        object_id_field="assigned_object_id",
        related_query_name="vminterface",
    )
    tags = TaggableManager(through=TaggedItem, related_name="vminterface")

    csv_headers = [
        "virtual_machine",
        "name",
        "enabled",
        "mac_address",
        "mtu",
        "description",
        "mode",
        "status",
        "parent_interface",
        "bridge",
    ]

    class Meta:
        verbose_name = "VM interface"
        ordering = ("virtual_machine", CollateAsChar("_name"))
        unique_together = ("virtual_machine", "name")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("virtualization:vminterface", kwargs={"pk": self.pk})

    def to_csv(self):
        return (
            self.virtual_machine.name,
            self.name,
            self.enabled,
            self.mac_address,
            self.mtu,
            self.description,
            self.get_mode_display(),
            self.get_status_display(),
            self.parent_interface.name if self.parent_interface else None,
            self.bridge.name if self.bridge else None,
        )

    def to_objectchange(self, action):

        # Annotate the parent VirtualMachine
        return ObjectChange(
            changed_object=self,
            object_repr=str(self),
            action=action,
            object_data=serialize_object(self),
            object_data_v2=serialize_object_v2(self),
            related_object=self.virtual_machine,
        )

    @property
    def parent(self):
        return self.virtual_machine

    @property
    def count_ipaddresses(self):
        return self.ip_addresses.count()
