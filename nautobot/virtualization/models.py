from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager
from nautobot.core.models.fields import NaturalOrderingField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.ordering import naturalize_interface
from nautobot.core.models.query_functions import CollateAsChar
from nautobot.core.utils.config import get_settings_or_config
from nautobot.dcim.models import BaseInterface
from nautobot.extras.models import (
    ConfigContextModel,
    RoleField,
    StatusField,
)
from nautobot.extras.querysets import ConfigContextModelQuerySet
from nautobot.extras.utils import extras_features

__all__ = (
    "Cluster",
    "ClusterGroup",
    "ClusterType",
    "VMInterface",
    "VirtualMachine",
)


#
# Cluster types
#


@extras_features(
    "custom_validators",
    "graphql",
)
class ClusterType(OrganizationalModel):
    """
    A type of Cluster.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


#
# Cluster groups
#


@extras_features(
    "custom_validators",
    "graphql",
)
class ClusterGroup(OrganizationalModel):
    """
    An organizational group of Clusters.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


#
# Clusters
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "webhooks",
)
class Cluster(PrimaryModel):
    """
    A cluster of VirtualMachines. Each Cluster may optionally be associated with one or more Devices.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    cluster_type = models.ForeignKey(to=ClusterType, on_delete=models.PROTECT, related_name="clusters")
    cluster_group = models.ForeignKey(
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
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="clusters",
        blank=True,
        null=True,
    )
    comments = models.TextField(blank=True)

    clone_fields = [
        "cluster_type",
        "cluster_group",
        "tenant",
        "location",
    ]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:
            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'Clusters may not associate to locations of type "{self.location.location_type}".'}
                )


#
# Virtual machines
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class VirtualMachine(PrimaryModel, ConfigContextModel):
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
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    status = StatusField(blank=False, null=False)
    role = RoleField(blank=True, null=True)
    primary_ip4 = models.ForeignKey(
        to="ipam.IPAddress",
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
        verbose_name="Primary IPv4",
    )
    primary_ip6 = models.ForeignKey(
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
    software_version = models.ForeignKey(
        to="dcim.SoftwareVersion",
        on_delete=models.PROTECT,
        related_name="virtual_machines",
        blank=True,
        null=True,
        help_text="The software version installed on this virtual machine",
    )
    software_image_files = models.ManyToManyField(
        to="dcim.SoftwareImageFile",
        related_name="virtual_machines",
        blank=True,
        verbose_name="Software Image Files",
        help_text="Override the software image files associated with the software version for this virtual machine",
    )

    objects = BaseManager.from_queryset(ConfigContextModelQuerySet)()

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
        from nautobot.ipam.models import IPAddressToInterface

        # Validate primary IP addresses
        vm_interfaces = VMInterface.objects.filter(virtual_machine=self)
        for field in ["primary_ip4", "primary_ip6"]:
            ip = getattr(self, field)
            if ip is not None:
                if field == "primary_ip4":
                    if ip.ip_version != 4:
                        raise ValidationError({f"{field}": f"{ip} is not an IPv4 address."})
                else:
                    if ip.ip_version != 6:
                        raise ValidationError({f"{field}": f"{ip} is not an IPv6 address."})
                if IPAddressToInterface.objects.filter(ip_address=ip, vm_interface__in=vm_interfaces).exists():
                    pass
                elif (
                    ip.nat_inside is not None
                    and IPAddressToInterface.objects.filter(
                        ip_address=ip.nat_inside, vm_interface__in=vm_interfaces
                    ).exists()
                ):
                    pass
                else:
                    raise ValidationError(
                        {f"{field}": f"The specified IP address ({ip}) is not assigned to this virtual machine."}
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
    def location(self):
        return self.cluster.location

    @property
    def location_id(self):
        return self.cluster.location_id


#
# Interfaces
#


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class VMInterface(PrimaryModel, BaseInterface):
    virtual_machine = models.ForeignKey(
        to="virtualization.VirtualMachine",
        on_delete=models.CASCADE,
        related_name="interfaces",
    )
    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, db_index=True)
    _name = NaturalOrderingField(
        target_field="name",
        naturalize_function=naturalize_interface,
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        db_index=True,
    )
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
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
    vrf = models.ForeignKey(
        to="ipam.VRF",
        related_name="vm_interfaces",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    ip_addresses = models.ManyToManyField(
        to="ipam.IPAddress",
        through="ipam.IPAddressToInterface",
        related_name="vm_interfaces",
        blank=True,
        verbose_name="IP Addresses",
    )

    class Meta:
        verbose_name = "VM interface"
        ordering = ("virtual_machine", CollateAsChar("_name"))
        unique_together = ("virtual_machine", "name")

    def __str__(self):
        return self.name

    def to_objectchange(self, action, **kwargs):
        # Annotate the parent VirtualMachine
        try:
            virtual_machine = self.virtual_machine
        except VirtualMachine.DoesNotExist:
            # The parent VirtualMachine has already been deleted
            virtual_machine = None

        return super().to_objectchange(action, related_object=virtual_machine, **kwargs)

    @property
    def parent(self):
        return self.virtual_machine

    @property
    def ip_address_count(self):
        return self.ip_addresses.count()
