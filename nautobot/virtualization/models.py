from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, transaction

from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.models import BaseManager
from nautobot.core.models.fields import NaturalOrderingField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.ordering import naturalize_interface
from nautobot.core.models.query_functions import CollateAsChar
from nautobot.dcim.models import BaseInterface, Device
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
    "VirtualMachine",
    "VMInterface",
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

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)

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

    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)

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
    "dynamic_groups",
    "export_templates",
    "graphql",
    "locations",
    "webhooks",
)
class Cluster(PrimaryModel):
    """
    A cluster of VirtualMachines. Each Cluster may optionally be associated with one or more Devices.
    """

    name = models.CharField(max_length=100, unique=True)
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

        # Likewise, verify that host Devices match Location of this Cluster if any
        # TODO: after Location model replaced Site, which was not a hierarchical model, should we allow users to create a Cluster with
        # the parent Location or the child location of host Device?
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


#
# Virtual machines
#


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
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
    name = models.CharField(max_length=64, db_index=True)
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

    def add_ip_addresses(
        self,
        ip_addresses,
        is_source=False,
        is_destination=False,
        is_default=False,
        is_preferred=False,
        is_primary=False,
        is_secondary=False,
        is_standby=False,
    ):
        """Add one or more IPAddress instances to this interface's `ip_addresses` many-to-many relationship.

        Args:
            ip_addresses (:obj:`list` or `IPAddress`): Instance of `nautobot.ipam.models.IPAddress` or list of `IPAddress` instances.
            is_source (bool, optional): Is source address. Defaults to False.
            is_destination (bool, optional): Is destination address. Defaults to False.
            is_default (bool, optional): Is default address. Defaults to False.
            is_preferred (bool, optional): Is preferred address. Defaults to False.
            is_primary (bool, optional): Is primary address. Defaults to False.
            is_secondary (bool, optional): Is secondary address. Defaults to False.
            is_standby (bool, optional): Is standby address. Defaults to False.

        Returns:
            Number of instances added.
        """
        if not isinstance(ip_addresses, (tuple, list)):
            ip_addresses = [ip_addresses]
        with transaction.atomic():
            for ip in ip_addresses:
                instance = self.ip_addresses.through(
                    ip_address=ip,
                    vm_interface=self,
                    is_source=is_source,
                    is_destination=is_destination,
                    is_default=is_default,
                    is_preferred=is_preferred,
                    is_primary=is_primary,
                    is_secondary=is_secondary,
                    is_standby=is_standby,
                )
                instance.validated_save()
        return len(ip_addresses)

    def remove_ip_addresses(self, ip_addresses):
        """Remove one or more IPAddress instances from this interface's `ip_addresses` many-to-many relationship.

        Args:
            ip_addresses (:obj:`list` or `IPAddress`): Instance of `nautobot.ipam.models.IPAddress` or list of `IPAddress` instances.

        Returns:
            Number of instances removed.
        """
        count = 0
        if not isinstance(ip_addresses, (tuple, list)):
            ip_addresses = [ip_addresses]
        with transaction.atomic():
            for ip in ip_addresses:
                qs = self.ip_addresses.through.objects.filter(ip_address=ip, vm_interface=self)
                deleted_count, _ = qs.delete()
                count += deleted_count
        return count

    @property
    def parent(self):
        return self.virtual_machine

    @property
    def ip_address_count(self):
        return self.ip_addresses.count()
