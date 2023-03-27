import logging

import netaddr
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError, MultipleObjectsReturned
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q
from django.urls import reverse
from django.utils.functional import classproperty

from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import AutoSlugField, JSONArrayField
from nautobot.core.models.generics import OrganizationalModel, PrimaryModel
from nautobot.core.models.utils import array_to_string
from nautobot.core.utils.data import UtilizationData
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import RoleModelMixin, Status, StatusModel
from nautobot.extras.utils import extras_features
from nautobot.ipam import choices
from nautobot.virtualization.models import VirtualMachine, VMInterface
from .constants import (
    IPADDRESS_ROLES_NONUNIQUE,
    SERVICE_PORT_MAX,
    SERVICE_PORT_MIN,
    VRF_RD_MAX_LENGTH,
)
from .fields import VarbinaryIPField
from .querysets import IPAddressQuerySet, PrefixQuerySet, RIRQuerySet
from .validators import DNSValidator


__all__ = (
    "IPAddress",
    "Prefix",
    "RIR",
    "RouteTarget",
    "Service",
    "VLAN",
    "VLANGroup",
    "VRF",
)


logger = logging.getLogger(__name__)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class VRF(PrimaryModel):
    """
    A virtual routing and forwarding (VRF) table represents a discrete layer three forwarding domain (e.g. a routing
    table). Prefixes and IPAddresses can optionally be assigned to VRFs. (Prefixes and IPAddresses not assigned to a VRF
    are said to exist in the "global" table.)
    """

    name = models.CharField(max_length=100, db_index=True)
    rd = models.CharField(
        max_length=VRF_RD_MAX_LENGTH,
        unique=True,
        blank=True,
        null=True,
        verbose_name="Route distinguisher",
        help_text="Unique route distinguisher (as defined in RFC 4364)",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="vrfs",
        blank=True,
        null=True,
    )
    enforce_unique = models.BooleanField(
        default=True,
        verbose_name="Enforce unique space",
        help_text="Prevent duplicate prefixes/IP addresses within this VRF",
    )
    description = models.CharField(max_length=200, blank=True)
    import_targets = models.ManyToManyField(to="ipam.RouteTarget", related_name="importing_vrfs", blank=True)
    export_targets = models.ManyToManyField(to="ipam.RouteTarget", related_name="exporting_vrfs", blank=True)

    csv_headers = ["name", "rd", "tenant", "enforce_unique", "description"]
    clone_fields = [
        "tenant",
        "enforce_unique",
        "description",
    ]

    class Meta:
        ordering = ("name", "rd")  # (name, rd) may be non-unique
        verbose_name = "VRF"
        verbose_name_plural = "VRFs"

    def __str__(self):
        return self.display or super().__str__()

    def get_absolute_url(self):
        return reverse("ipam:vrf", args=[self.pk])

    def to_csv(self):
        return (
            self.name,
            self.rd,
            self.tenant.name if self.tenant else None,
            str(self.enforce_unique),
            self.description,
        )

    @property
    def display(self):
        if self.rd:
            return f"{self.name} ({self.rd})"
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class RouteTarget(PrimaryModel):
    """
    A BGP extended community used to control the redistribution of routes among VRFs, as defined in RFC 4364.
    """

    name = models.CharField(
        max_length=VRF_RD_MAX_LENGTH,  # Same format options as VRF RD (RFC 4360 section 4)
        unique=True,
        help_text="Route target value (formatted in accordance with RFC 4360)",
    )
    description = models.CharField(max_length=200, blank=True)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="route_targets",
        blank=True,
        null=True,
    )

    csv_headers = ["name", "description", "tenant"]

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("ipam:routetarget", args=[self.pk])

    def to_csv(self):
        return (
            self.name,
            self.description,
            self.tenant.name if self.tenant else None,
        )


@extras_features(
    "custom_validators",
    "graphql",
)
class RIR(OrganizationalModel):
    """
    A Regional Internet Registry (RIR) is responsible for the allocation of a large portion of the global IP address
    space. This can be an organization like ARIN or RIPE, or a governing standard such as RFC 1918.
    """

    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from="name")
    is_private = models.BooleanField(
        default=False,
        verbose_name="Private",
        help_text="IP space managed by this RIR is considered private",
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "is_private", "description"]

    objects = BaseManager.from_queryset(RIRQuerySet)()

    class Meta:
        ordering = ["name"]
        verbose_name = "RIR"
        verbose_name_plural = "RIRs"

    def __str__(self):
        return self.name

    def natural_key(self):
        return (self.name,)

    def get_absolute_url(self):
        return reverse("ipam:rir", args=[self.slug])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            str(self.is_private),
            self.description,
        )


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class Prefix(PrimaryModel, StatusModel, RoleModelMixin):
    """
    A Prefix represents an IPv4 or IPv6 network, including mask length.
    Prefixes can optionally be assigned to Locations and VRFs.
    A Prefix must be assigned a status and may optionally be assigned a user-defined Role.
    A Prefix can also be assigned to a VLAN where appropriate.
    """

    network = VarbinaryIPField(
        null=False,
        db_index=True,
        help_text="IPv4 or IPv6 network address",
    )
    broadcast = VarbinaryIPField(null=False, db_index=True, help_text="IPv4 or IPv6 broadcast address")
    prefix_length = models.IntegerField(null=False, db_index=True, help_text="Length of the Network prefix, in bits.")
    type = models.CharField(
        max_length=50,
        choices=choices.PrefixTypeChoices,
        default=choices.PrefixTypeChoices.TYPE_NETWORK,
    )
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
    )
    vrf = models.ForeignKey(
        to="ipam.VRF",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
        verbose_name="VRF",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
    )
    vlan = models.ForeignKey(
        to="ipam.VLAN",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
        verbose_name="VLAN",
    )
    rir = models.ForeignKey(
        to="ipam.RIR",
        on_delete=models.PROTECT,
        related_name="prefixes",
        blank=True,
        null=True,
        verbose_name="RIR",
        help_text="Regional Internet Registry responsible for this prefix",
    )
    date_allocated = models.DateTimeField(
        blank=True,
        null=True,
        help_text="Date this prefix was allocated to an RIR, reserved in IPAM, etc.",
    )
    description = models.CharField(max_length=200, blank=True)

    objects = BaseManager.from_queryset(PrefixQuerySet)()

    # TODO: The current Prefix model has no appropriate natural key available yet.
    #       However, by default all BaseModel subclasses now have a `natural_key` property;
    #       but for this model, accessing the natural_key will raise an exception.
    #       The below is a hacky way to "remove" the natural_key property from this model class for the time being.
    class AttributeRemover:
        def __get__(self, instance, owner):
            raise AttributeError("Prefix doesn't yet have a natural key!")

    natural_key = AttributeRemover()

    csv_headers = [
        "prefix",
        "type",
        "vrf",
        "tenant",
        "location",
        "vlan_group",
        "vlan",
        "status",
        "role",
        "rir",
        "date_allocated",
        "description",
    ]
    clone_fields = [
        "date_allocated",
        "description",
        "location",
        "rir",
        "role",
        "status",
        "tenant",
        "type",
        "vlan",
        "vrf",
    ]
    dynamic_group_filter_fields = {
        "vrf": "vrf_id",  # Duplicate filter fields that will be collapsed in 2.0
    }

    class Meta:
        ordering = (
            F("vrf__name").asc(nulls_first=True),
            "network",
            "prefix_length",
        )  # (vrf, prefix) may be non-unique
        verbose_name_plural = "prefixes"

    def __init__(self, *args, **kwargs):
        prefix = kwargs.pop("prefix", None)
        super(Prefix, self).__init__(*args, **kwargs)
        self._deconstruct_prefix(prefix)

    def __str__(self):
        return str(self.prefix)

    def _deconstruct_prefix(self, pre):
        if pre:
            if isinstance(pre, str):
                pre = netaddr.IPNetwork(pre)
            # Note that our "broadcast" field is actually the last IP address in this prefix.
            # This is different from the more accurate technical meaning of a network's broadcast address in 2 cases:
            # 1. For a point-to-point prefix (IPv4 /31 or IPv6 /127), there are two addresses in the prefix,
            #    and neither one is considered a broadcast address. We store the second address as our "broadcast".
            # 2. For a host prefix (IPv6 /32 or IPv6 /128) there's only one address in the prefix.
            #    We store this address as both the network and the "broadcast".
            # This variance is intentional in both cases as we use the "broadcast" primarily for filtering and grouping
            # of addresses and prefixes, not for packet forwarding. :-)
            broadcast = pre.broadcast if pre.broadcast else pre[-1]
            self.network = str(pre.network)
            self.broadcast = str(broadcast)
            self.prefix_length = pre.prefixlen

    def get_absolute_url(self):
        return reverse("ipam:prefix", args=[self.pk])

    def clean(self):
        super().clean()

        if self.prefix:

            # /0 masks are not acceptable
            if self.prefix.prefixlen == 0:
                raise ValidationError({"prefix": "Cannot create prefix with /0 mask."})

            # Enforce unique IP space (if applicable)
            if (self.vrf is None and settings.ENFORCE_GLOBAL_UNIQUE) or (self.vrf and self.vrf.enforce_unique):
                duplicate_prefixes = self.get_duplicates()
                if duplicate_prefixes:
                    vrf = f"VRF {self.vrf}" if self.vrf else "global table"
                    raise ValidationError({"prefix": f"Duplicate prefix found in {vrf}: {duplicate_prefixes.first()}"})

        # Validate location
        if self.location is not None:

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'Prefixes may not associate to locations of type "{self.location.location_type}".'}
                )

    def save(self, *args, **kwargs):

        if isinstance(self.prefix, netaddr.IPNetwork):

            # Clear host bits from prefix
            self.prefix = self.prefix.cidr

        super().save(*args, **kwargs)

    def to_csv(self):
        return (
            self.prefix,
            self.get_type_display(),
            self.vrf.name if self.vrf else None,
            self.tenant.name if self.tenant else None,
            self.location.name if self.location else None,
            self.vlan.vlan_group.name if self.vlan and self.vlan.vlan_group else None,
            self.vlan.vid if self.vlan else None,
            self.get_status_display(),
            self.role.name if self.role else None,
            self.rir.name if self.rir else None,
            str(self.date_allocated),
            self.description,
        )

    @property
    def cidr_str(self):
        if self.network is not None and self.prefix_length is not None:
            return f"{self.network}/{self.prefix_length}"
        return None

    @property
    def prefix(self):
        if self.cidr_str:
            return netaddr.IPNetwork(self.cidr_str)
        return None

    @prefix.setter
    def prefix(self, prefix):
        self._deconstruct_prefix(prefix)

    @property
    def family(self):
        if self.prefix:
            return self.prefix.version
        return None

    def get_duplicates(self):
        return Prefix.objects.net_equals(self.prefix).filter(vrf=self.vrf).exclude(pk=self.pk)

    def get_child_prefixes(self):
        """
        Return all Prefixes within this Prefix and VRF. If this Prefix is a container in the global table, return child
        Prefixes belonging to any VRF.
        """
        if self.vrf is None and self.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            return Prefix.objects.net_contained(self.prefix)
        else:
            return Prefix.objects.net_contained(self.prefix).filter(vrf=self.vrf)

    def get_child_ips(self):
        """
        Return all IPAddresses within this Prefix and VRF. If this Prefix is a container in the global table, return
        child IPAddresses belonging to any VRF.
        """
        if self.vrf is None and self.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            return IPAddress.objects.net_host_contained(self.prefix)
        else:
            return IPAddress.objects.net_host_contained(self.prefix).filter(vrf=self.vrf)

    def get_available_prefixes(self):
        """
        Return all available Prefixes within this prefix as an IPSet.
        """
        prefix = netaddr.IPSet(self.prefix)
        child_prefixes = netaddr.IPSet([child.prefix for child in self.get_child_prefixes()])
        available_prefixes = prefix - child_prefixes

        return available_prefixes

    def get_available_ips(self):
        """
        Return all available IPs within this prefix as an IPSet.
        """
        prefix = netaddr.IPSet(self.prefix)
        child_ips = netaddr.IPSet([ip.address.ip for ip in self.get_child_ips()])
        available_ips = prefix - child_ips

        # IPv6, pool, or IPv4 /31-32 sets are fully usable
        if any(
            [
                self.family == 6,
                self.type == choices.PrefixTypeChoices.TYPE_POOL,
                self.family == 4 and self.prefix.prefixlen >= 31,
            ]
        ):
            return available_ips

        # Omit first and last IP address from the available set
        # For "normal" IPv4 prefixes, omit first and last addresses
        available_ips -= netaddr.IPSet(
            [
                netaddr.IPAddress(self.prefix.first),
                netaddr.IPAddress(self.prefix.last),
            ]
        )
        return available_ips

    def get_first_available_prefix(self):
        """
        Return the first available child prefix within the prefix (or None).
        """
        available_prefixes = self.get_available_prefixes()
        if not available_prefixes:
            return None
        return available_prefixes.iter_cidrs()[0]

    def get_first_available_ip(self):
        """
        Return the first available IP within the prefix (or None).
        """
        available_ips = self.get_available_ips()
        if not available_ips:
            return None
        return f"{next(available_ips.__iter__())}/{self.prefix.prefixlen}"

    def get_utilization(self):
        """Get the child prefix size and parent size.

        For Prefixes with a type of "container", get the number child prefixes. For all others, count child IP addresses.

        Returns:
            UtilizationData (namedtuple): (numerator, denominator)
        """
        if self.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            queryset = Prefix.objects.net_contained(self.prefix).filter(vrf=self.vrf)
            child_prefixes = netaddr.IPSet([p.prefix for p in queryset])
            return UtilizationData(numerator=child_prefixes.size, denominator=self.prefix.size)

        else:
            prefix_size = self.prefix.size
            if all(
                [
                    self.prefix.version == 4,
                    self.prefix.prefixlen < 31,
                    self.type != choices.PrefixTypeChoices.TYPE_POOL,
                ]
            ):
                prefix_size -= 2
            child_count = prefix_size - self.get_available_ips().size
            return UtilizationData(numerator=child_count, denominator=prefix_size)


@extras_features(
    "custom_links",
    "custom_validators",
    "dynamic_groups",
    "export_templates",
    "graphql",
    "statuses",
    "webhooks",
)
class IPAddress(PrimaryModel, StatusModel, RoleModelMixin):
    """
    An IPAddress represents an individual IPv4 or IPv6 address and its mask. The mask length should match what is
    configured in the real world. (Typically, only loopback interfaces are configured with /32 or /128 masks.) Like
    Prefixes, IPAddresses can optionally be assigned to a VRF. An IPAddress can optionally be assigned to an Interface.
    Interfaces can have zero or more IPAddresses assigned to them.

    An IPAddress can also optionally point to a NAT inside IP, designating itself as a NAT outside IP. This is useful,
    for example, when mapping public addresses to private addresses. When an Interface has been assigned an IPAddress
    which has a NAT outside IP, that Interface's Device can use either the inside or outside IP as its primary IP.
    """

    host = VarbinaryIPField(
        null=False,
        db_index=True,
        help_text="IPv4 or IPv6 host address",
    )
    broadcast = VarbinaryIPField(null=False, db_index=True, help_text="IPv4 or IPv6 broadcast address")
    prefix_length = models.IntegerField(null=False, db_index=True, help_text="Length of the Network prefix, in bits.")
    vrf = models.ForeignKey(
        to="ipam.VRF",
        on_delete=models.PROTECT,
        related_name="ip_addresses",
        blank=True,
        null=True,
        verbose_name="VRF",
    )
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="ip_addresses",
        blank=True,
        null=True,
    )
    nat_inside = models.ForeignKey(
        to="self",
        on_delete=models.SET_NULL,
        related_name="nat_outside_list",
        blank=True,
        null=True,
        verbose_name="NAT (Inside)",
        help_text='The IP Addresses for which this address is the "outside" IP',
    )
    dns_name = models.CharField(
        max_length=255,
        blank=True,
        validators=[DNSValidator],
        verbose_name="DNS Name",
        help_text="Hostname or FQDN (not case-sensitive)",
        db_index=True,
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = [
        "address",
        "vrf",
        "tenant",
        "status",
        "role",
        "is_primary",
        "dns_name",
        "description",
    ]
    clone_fields = [
        "vrf",
        "tenant",
        "status",
        "role",
        "description",
    ]
    dynamic_group_skip_missing_fields = True  # Problematic form labels for `vminterface` and `interface`

    objects = BaseManager.from_queryset(IPAddressQuerySet)()

    class Meta:
        ordering = ("host", "prefix_length")  # address may be non-unique
        verbose_name = "IP address"
        verbose_name_plural = "IP addresses"

    def __init__(self, *args, **kwargs):
        address = kwargs.pop("address", None)
        super(IPAddress, self).__init__(*args, **kwargs)
        self._deconstruct_address(address)

    def __str__(self):
        return str(self.address)

    def _deconstruct_address(self, address):
        if address:
            if isinstance(address, str):
                address = netaddr.IPNetwork(address)
            # Note that our "broadcast" field is actually the last IP address in this network.
            # This is different from the more accurate technical meaning of a network's broadcast address in 2 cases:
            # 1. For a point-to-point address (IPv4 /31 or IPv6 /127), there are two addresses in the network,
            #    and neither one is considered a broadcast address. We store the second address as our "broadcast".
            # 2. For a host prefix (IPv6 /32 or IPv6 /128) there's only one address in the network.
            #    We store this address as both the host and the "broadcast".
            # This variance is intentional in both cases as we use the "broadcast" primarily for filtering and grouping
            # of addresses and prefixes, not for packet forwarding. :-)
            broadcast = address.broadcast if address.broadcast else address[-1]
            self.host = str(address.ip)
            self.broadcast = str(broadcast)
            self.prefix_length = address.prefixlen

    def get_absolute_url(self):
        return reverse("ipam:ipaddress", args=[self.pk])

    def get_duplicates(self):
        return IPAddress.objects.filter(vrf=self.vrf, host=self.host).exclude(pk=self.pk)

    # TODO: The current IPAddress model has no appropriate natural key available yet.
    #       However, by default all BaseModel subclasses now have a `natural_key` property;
    #       but for this model, accessing the natural_key will raise an exception.
    #       The below is a hacky way to "remove" the natural_key property from this model class for the time being.
    class AttributeRemover:
        def __get__(self, instance, owner):
            raise AttributeError("IPAddress doesn't yet have a natural key!")

    natural_key = AttributeRemover()

    @classproperty  # https://github.com/PyCQA/pylint-django/issues/240
    def STATUS_SLAAC(cls):  # pylint: disable=no-self-argument
        """Return a cached "slaac" `Status` object for later reference."""
        cls.__status_slaac = getattr(cls, "__status_slaac", None)
        if cls.__status_slaac is None:
            try:
                cls.__status_slaac = Status.objects.get_for_model(IPAddress).get(slug="slaac")
            except Status.DoesNotExist:
                logger.error("SLAAC Status not found")
        return cls.__status_slaac

    def clean(self):
        super().clean()

        if self.address:

            # /0 masks are not acceptable
            if self.address.prefixlen == 0:
                raise ValidationError({"address": "Cannot create IP address with /0 mask."})

            # Enforce unique IP space (if applicable)
            if self.role not in IPADDRESS_ROLES_NONUNIQUE and (
                (self.vrf is None and settings.ENFORCE_GLOBAL_UNIQUE) or (self.vrf and self.vrf.enforce_unique)
            ):
                duplicate_ips = self.get_duplicates()
                if duplicate_ips:
                    vrf = f"VRF {self.vrf}" if self.vrf else "global table"
                    raise ValidationError({"address": f"Duplicate IP address found in {vrf}: {duplicate_ips.first()}"})

        # TODO: update to work with interface M2M
        # This attribute will have been set by `IPAddressForm.clean()` to indicate that the
        # `primary_ip{version}` field on `self.assigned_object.parent` has been nullified but not yet saved.
        primary_ip_unset_by_form = getattr(self, "_primary_ip_unset_by_form", False)

        # Check for primary IP assignment that doesn't match the assigned device/VM if and only if
        # "_primary_ip_unset" has not been set by the caller.
        if self.present_in_database and not primary_ip_unset_by_form:
            device = Device.objects.filter(Q(primary_ip4=self) | Q(primary_ip6=self)).first()
            if device:
                if getattr(self.assigned_object, "device", None) != device:
                    raise ValidationError(
                        {"interface": f"IP address is primary for device {device} but not assigned to it!"}
                    )
            vm = VirtualMachine.objects.filter(Q(primary_ip4=self) | Q(primary_ip6=self)).first()
            if vm:
                if getattr(self.assigned_object, "virtual_machine", None) != vm:
                    raise ValidationError(
                        {"vminterface": f"IP address is primary for virtual machine {vm} but not assigned to it!"}
                    )

        # Validate IP status selection
        if self.status == IPAddress.STATUS_SLAAC and self.family != 6:
            raise ValidationError({"status": "Only IPv6 addresses can be assigned SLAAC status"})

        # Force dns_name to lowercase
        self.dns_name = self.dns_name.lower()

    def to_csv(self):

        # Determine if this IP is primary for a Device
        is_primary = False
        if self.address.version == 4 and getattr(self, "primary_ip4_for", False):
            is_primary = True
        elif self.address.version == 6 and getattr(self, "primary_ip6_for", False):
            is_primary = True

        return (
            self.address,
            self.vrf.name if self.vrf else None,
            self.tenant.name if self.tenant else None,
            self.get_status_display(),
            self.role.name if self.role else None,
            str(is_primary),
            self.dns_name,
            self.description,
        )

    @property
    def address(self):
        if self.host is not None and self.prefix_length is not None:
            cidr = f"{self.host}/{self.prefix_length}"
            return netaddr.IPNetwork(cidr)
        return None

    @address.setter
    def address(self, address):
        self._deconstruct_address(address)

    @property
    def family(self):
        if self.address:
            return self.address.version
        return None

    # 2.0 TODO: Remove exception, getter, setter below when we can safely deprecate previous properties
    class NATOutsideMultipleObjectsReturned(MultipleObjectsReturned):
        """
        An exception class is used to expose in API the object that cannot safely support the legacy getter, setter methods.
        """

        def __init__(self, obj):
            self.obj = obj

        def __str__(self):
            return f"Multiple IPAddress objects specify this object (pk: {self.obj.pk}) as nat_inside. Please refer to nat_outside_list."

    @property
    def nat_outside(self):
        if self.nat_outside_list.count() > 1:
            raise self.NATOutsideMultipleObjectsReturned(self)
        return self.nat_outside_list.first()

    @nat_outside.setter
    def nat_outside(self, value):
        if self.nat_outside_list.count() > 1:
            raise self.NATOutsideMultipleObjectsReturned(self)
        return self.nat_outside_list.set([value])

    def _set_mask_length(self, value):
        """
        Expose the IPNetwork object's prefixlen attribute on the parent model so that it can be manipulated directly,
        e.g. for bulk editing.
        """
        if self.address is not None:
            self.prefix_length = value

    mask_length = property(fset=_set_mask_length)


class IPAddressToInterface(BaseModel):
    ip_address = models.ForeignKey("ipam.IPAddress", on_delete=models.CASCADE, related_name="+")
    interface = models.ForeignKey(
        "dcim.Interface", blank=True, null=True, on_delete=models.CASCADE, related_name="ip_address_assignments"
    )
    vm_interface = models.ForeignKey(
        "virtualization.VMInterface",
        blank=True,
        null=True,
        on_delete=models.CASCADE,
        related_name="ip_address_assignments",
    )
    is_source = models.BooleanField(default=False, help_text="Is source address on interface")
    is_destination = models.BooleanField(default=False, help_text="Is destination address on interface")
    is_default = models.BooleanField(default=False, help_text="Is default address on interface")
    is_preferred = models.BooleanField(default=False, help_text="Is preferred address on interface")
    is_primary = models.BooleanField(default=False, help_text="Is primary address on interface")
    is_secondary = models.BooleanField(default=False, help_text="Is secondary address on interface")
    is_standby = models.BooleanField(default=False, help_text="Is standby address on interface")

    def validate_unique(self, exclude=None):
        """
        Check uniqueness on combination of `ip_address`, `interface` and `vm_interface` fields
        and raise ValidationError if check failed.
        """
        if IPAddressToInterface.objects.filter(
            ip_address=self.ip_address,
            interface=self.interface,
            vm_interface=self.vm_interface,
        ).exists():
            raise ValidationError(
                "IPAddressToInterface with this ip_address, interface and vm_interface already exists."
            )

    def clean(self):
        super().clean()

        if self.interface is not None and self.vm_interface is not None:
            raise ValidationError(
                {"interface": "Cannot use a single instance to associate to both an Interface and a VMInterface."}
            )

        if self.interface is None and self.vm_interface is None:
            raise ValidationError({"interface": "Must associate to either an Interface or a VMInterface."})

    def __str__(self):
        if self.interface:
            return f"{self.ip_address!s} {self.interface.device.name} {self.interface.name}"
        else:
            return f"{self.ip_address!s} {self.vm_interface.virtual_machine.name} {self.vm_interface.name}"


@extras_features(
    "custom_validators",
    "graphql",
    "locations",
)
class VLANGroup(OrganizationalModel):
    """
    A VLAN group is an arbitrary collection of VLANs within which VLAN IDs and names must be unique.
    """

    name = models.CharField(max_length=100, db_index=True)
    # 2.0 TODO: Remove unique=None to make slug globally unique. This would be a breaking change.
    slug = AutoSlugField(populate_from="name", unique=None, db_index=True)
    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="vlan_groups",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = ["name", "slug", "location", "description"]

    class Meta:
        ordering = (
            "location",
            "name",
        )  # (location, name) may be non-unique
        unique_together = [
            # 2.0 TODO: since location is nullable, and NULL != NULL, this means that we can have multiple non-Location VLANGroups
            # with the same name. This should probably be fixed with a custom validate_unique() function!
            ["location", "name"],
            # 2.0 TODO: Remove unique_together to make slug globally unique. This would be a breaking change.
            ["location", "slug"],
        ]
        verbose_name = "VLAN group"
        verbose_name_plural = "VLAN groups"

    natural_key_field_names = ["name", "location"]  # location needs to be last since it's a variadic natural key

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'VLAN groups may not associate to locations of type "{self.location.location_type}".'}
                )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("ipam:vlangroup", args=[self.pk])

    def to_csv(self):
        return (
            self.name,
            self.slug,
            self.location.name if self.location else None,
            self.description,
        )

    def get_next_available_vid(self):
        """
        Return the first available VLAN ID (1-4094) in the group.
        """
        vlan_ids = VLAN.objects.filter(vlan_group=self).values_list("vid", flat=True)
        for i in range(1, 4095):
            if i not in vlan_ids:
                return i
        return None


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "locations",
    "statuses",
    "webhooks",
)
class VLAN(PrimaryModel, StatusModel, RoleModelMixin):
    """
    A VLAN is a distinct layer two forwarding domain identified by a 12-bit integer (1-4094).
    Each VLAN must be assigned to a Location, however VLAN IDs need not be unique within a Location.
    A VLAN may optionally be assigned to a VLANGroup, within which all VLAN IDs and names but be unique.

    Like Prefixes, each VLAN is assigned an operational status and optionally a user-defined Role. A VLAN can have zero
    or more Prefixes assigned to it.
    """

    location = models.ForeignKey(
        to="dcim.Location",
        on_delete=models.PROTECT,
        related_name="vlans",
        blank=True,
        null=True,
    )
    vlan_group = models.ForeignKey(
        to="ipam.VLANGroup",
        on_delete=models.PROTECT,
        related_name="vlans",
        blank=True,
        null=True,
    )
    vid = models.PositiveSmallIntegerField(
        verbose_name="ID", validators=[MinValueValidator(1), MaxValueValidator(4094)]
    )
    name = models.CharField(max_length=255, db_index=True)
    tenant = models.ForeignKey(
        to="tenancy.Tenant",
        on_delete=models.PROTECT,
        related_name="vlans",
        blank=True,
        null=True,
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = [
        "location",
        "vlan_group",
        "vid",
        "name",
        "tenant",
        "status",
        "role",
        "description",
    ]
    clone_fields = [
        "location",
        "vlan_group",
        "tenant",
        "status",
        "role",
        "description",
    ]

    class Meta:
        ordering = (
            "location",
            "vlan_group",
            "vid",
        )  # (location, group, vid) may be non-unique
        unique_together = [
            # 2.0 TODO: since group is nullable and NULL != NULL, we can have multiple non-group VLANs with
            # the same vid and name. We should probably fix this with a custom validate_unique() function.
            ["vlan_group", "vid"],
            ["vlan_group", "name"],
        ]
        verbose_name = "VLAN"
        verbose_name_plural = "VLANs"

    def __str__(self):
        return self.display or super().__str__()

    def get_absolute_url(self):
        return reverse("ipam:vlan", args=[self.pk])

    def clean(self):
        super().clean()

        # Validate location
        if self.location is not None:

            if ContentType.objects.get_for_model(self) not in self.location.location_type.content_types.all():
                raise ValidationError(
                    {"location": f'VLANs may not associate to locations of type "{self.location.location_type}".'}
                )

        # Validate VLAN group
        if (
            self.vlan_group is not None
            and self.location is not None
            and self.vlan_group.location is not None
            and self.vlan_group.location not in self.location.ancestors(include_self=True)
        ):
            raise ValidationError(
                {
                    "vlan_group": f'The assigned group belongs to a location that does not include location "{self.location}".'
                }
            )

    def to_csv(self):
        return (
            self.location.name if self.location else None,
            self.vlan_group.name if self.vlan_group else None,
            self.vid,
            self.name,
            self.tenant.name if self.tenant else None,
            self.get_status_display(),
            self.role.name if self.role else None,
            self.description,
        )

    @property
    def display(self):
        return f"{self.name} ({self.vid})"

    def get_interfaces(self):
        # Return all device interfaces assigned to this VLAN
        return Interface.objects.filter(Q(untagged_vlan_id=self.pk) | Q(tagged_vlans=self.pk)).distinct()

    def get_vminterfaces(self):
        # Return all VM interfaces assigned to this VLAN
        return VMInterface.objects.filter(Q(untagged_vlan_id=self.pk) | Q(tagged_vlans=self.pk)).distinct()


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class Service(PrimaryModel):
    """
    A Service represents a layer-four service (e.g. HTTP or SSH) running on a Device or VirtualMachine. A Service may
    optionally be tied to one or more specific IPAddresses belonging to its parent.
    """

    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="services",
        verbose_name="device",
        null=True,
        blank=True,
    )
    virtual_machine = models.ForeignKey(
        to="virtualization.VirtualMachine",
        on_delete=models.CASCADE,
        related_name="services",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100, db_index=True)
    protocol = models.CharField(max_length=50, choices=choices.ServiceProtocolChoices)
    ports = JSONArrayField(
        base_field=models.PositiveIntegerField(
            validators=[
                MinValueValidator(SERVICE_PORT_MIN),
                MaxValueValidator(SERVICE_PORT_MAX),
            ]
        ),
        verbose_name="Port numbers",
    )
    ip_addresses = models.ManyToManyField(
        to="ipam.IPAddress",
        related_name="services",
        blank=True,
        verbose_name="IP addresses",
    )
    description = models.CharField(max_length=200, blank=True)

    csv_headers = [
        "device",
        "virtual_machine",
        "name",
        "protocol",
        "ports",
        "description",
    ]

    class Meta:
        ordering = (
            "protocol",
            "ports",
        )  # (protocol, port) may be non-unique

    def __str__(self):
        return f"{self.name} ({self.get_protocol_display()}/{self.port_list})"

    def get_absolute_url(self):
        return reverse("ipam:service", args=[self.pk])

    @property
    def parent(self):
        return self.device or self.virtual_machine

    def clean(self):
        super().clean()

        # A Service must belong to a Device *or* to a VirtualMachine
        if self.device and self.virtual_machine:
            raise ValidationError("A service cannot be associated with both a device and a virtual machine.")
        if not self.device and not self.virtual_machine:
            raise ValidationError("A service must be associated with either a device or a virtual machine.")

    def to_csv(self):
        return (
            self.device.name if self.device else None,
            self.virtual_machine.name if self.virtual_machine else None,
            self.name,
            self.get_protocol_display(),
            self.ports,
            self.description,
        )

    @property
    def port_list(self):
        return array_to_string(self.ports)
