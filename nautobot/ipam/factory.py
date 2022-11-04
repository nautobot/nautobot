import logging

import factory
import faker
import math

from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory
from nautobot.dcim.models import Location, Site
from nautobot.extras.models import Status
from nautobot.ipam.choices import IPAddressRoleChoices
from nautobot.ipam.models import Aggregate, RIR, IPAddress, Prefix, Role, RouteTarget, VLAN, VLANGroup, VRF
from nautobot.tenancy.models import Tenant
from nautobot.utilities.factory import get_random_instances, random_instance, UniqueFaker


logger = logging.getLogger(__name__)


class RIRFactory(OrganizationalModelFactory):
    class Meta:
        model = RIR
        exclude = ("has_description",)

    # 9 RIRs should be enough for anybody
    name = UniqueFaker(
        "random_element",
        elements=("AFRINIC", "APNIC", "ARIN", "LACNIC", "RIPE NCC", "RFC 1918", "RFC 3849", "RFC 4193", "RFC 6598"),
    )
    is_private = factory.LazyAttribute(lambda rir: rir.name.startswith("RFC"))

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")


class AggregateFactory(PrimaryModelFactory):
    """Create random aggregates and 50% of the time generate prefixes within the aggregate IP space.

    Child prefixes create nested child prefixes and ip addresses within the prefix IP space. Defaults
    to creating 0-8 child prefixes which generate 0-4 grandchildren. Set `child_prefixes__max_count` to
    an integer when calling the factory creation methods (`create()`, `create_batch()`, etc) to override
    the maximum number of child prefixes generated. Set `child_prefixes__children__max_count` to an
    integer when calling the factory creation methods (`create()`, `batch_create()`, etc) to override
    the maximum number of grandchildren generated.

    Examples:
        Create 20 aggregates, approximately half will generate 0-8 child prefixes which will create child prefixes and ip addresses:

            >>> AggregateFactory.create_batch(20)

        Create 20 aggregates with no child prefixes:

            >>> AggregateFactory.create_batch(20, child_prefixes__max_count=0)

        Create 20 aggregates, approximately half will generate 0-8 child prefixes that will not create any children:

            >>> AggregateFactory.create_batch(20, child_prefixes__children__max_count=0)
    """

    class Meta:
        model = Aggregate
        exclude = (
            "has_date_added",
            "has_description",
            "has_tenant",
            "has_tenant_group",
            "is_ipv6",
        )

    rir = random_instance(RIR, allow_null=False)

    has_tenant = factory.Faker("pybool")
    has_tenant_group = factory.Faker("pybool")
    tenant = factory.Maybe(
        "has_tenant_group",
        random_instance(Tenant.objects.filter(group__isnull=False), allow_null=False),
        factory.Maybe("has_tenant", random_instance(Tenant.objects.filter(group__isnull=True)), None),
    )

    has_date_added = factory.Faker("pybool")
    date_added = factory.Maybe("has_date_added", factory.Faker("date"), None)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    is_ipv6 = factory.Faker("pybool")

    @factory.post_generation
    def child_prefixes(self, create, extracted, **kwargs):
        """Create child prefixes within the aggregate IP space.

        Defaults to generating 0-8 child prefixes for 50% of aggregates. Set
        `child_prefixes__max_count` to an integer when calling the factory
        creation methods (`create()`, `create_batch()`, etc) to override the
        maximum number of children generated.

        Args:
            create: True if `create` strategy was used.
            extracted: None unless a value was passed in for the PostGeneration declaration at Factory declaration time
            kwargs: Any extra parameters passed as attr__key=value when calling the Factory
        """
        if extracted:
            # Objects have already been created, do nothing
            return

        # 50% chance to create child prefixes
        if not faker.Faker().pybool():
            return

        action = "create" if create else "build"
        method = getattr(PrefixFactory, action)
        is_ipv6 = self.family == 6

        # Default to maximum of 8 children unless overridden in kwargs
        max_count = int(kwargs.pop("max_count", 8))
        prefix_count = faker.Faker().pyint(min_value=0, max_value=min(max_count, self.prefix.size))
        if prefix_count == 0:
            return

        # Calculate prefix length for child prefixes to allow them to fit in the aggregate
        prefix_cidr = self.prefix_length + math.ceil(math.log(prefix_count, 2))

        # Raise exception for invalid cidr length (>128 for ipv6, >32 for ipv4)
        if prefix_cidr > 128 or self.family == 4 and prefix_cidr > 32:
            raise ValueError(f"Unable to create {prefix_count} prefixes in aggregate {self.cidr_str}")

        # Set prefix tenant to aggregate tenant if one is present
        if self.tenant is not None:
            kwargs.setdefault("tenant", self.tenant)

        # Create child prefixes, preserving tenant and is_ipv6 from aggregate
        for count, subnet in enumerate(self.prefix.subnet(prefix_cidr)):
            if count == max_count:
                break
            method(prefix=str(subnet.cidr), is_ipv6=is_ipv6, **kwargs)

    @factory.lazy_attribute_sequence
    def prefix(self, n):
        """
        Yes, this is probably over-complicated - but it's realistic!

        Not guaranteed to work properly for n >> 100; there's only so many IPv4 aggregates to go around.
        """
        if self.rir.name == "RFC 1918":
            if n < 16:
                return f"10.{16 * n}.0.0/12"
            if n < 32:
                return f"172.{n}.0/16"
            return f"192.168.{n - 32}.0/24"
        if self.rir.name == "RFC 3849":
            return f"2001:DB8:{n:x}::/48"
        if self.rir.name == "RFC 4193":
            unique_id = faker.Faker().pyint(0, 2**32 - 1)
            hextets = (unique_id // (2**16), unique_id % (2**16))
            return f"FD{n:02X}:{hextets[0]:X}:{hextets[1]:X}::/48"
        if self.rir.name == "RFC 6598":
            return f"100.{n + 64}.0.0/16"
        if self.rir.name == "AFRINIC":
            if not self.is_ipv6:
                # 196/8 thru 197/8
                return f"{196 + (n % 2)}.{n // 2}.0.0/16"
            # 2001:4200::/23
            return f"2001:42{n:02X}::/32"
        if self.rir.name == "APNIC":
            if not self.is_ipv6:
                # 110/8 thru 126/8
                return f"{110 + (n % 16)}.{16 * (n // 16)}.0.0/12"
            # 2001:0200::/23
            return f"2001:02{n:02X}::/32"
        if self.rir.name == "ARIN":
            if not self.is_ipv6:
                # 63/8 thru 76/8
                return f"{63 + (n % 14)}.{16 * (n // 14)}.0.0/12"
            # 2600::/12
            return f"2600:{n:X}00::/24"
        if self.rir.name == "LACNIC":
            if not self.is_ipv6:
                # 186/8 thru 187/8
                return f"{186 + (n % 2)}.{n // 2}.0.0/16"
            # 2800::/12
            return f"2800:{n:X}00::/24"
        if self.rir.name == "RIPE NCC":
            if not self.is_ipv6:
                # 77/8 thru 95/8
                return f"{77 + (n % 18)}.{16 * (n // 18)}.0.0/12"
            # 2003:0000::/18
            return f"2003:0{n:X}::/32"

        raise RuntimeError(f"Don't know how to pick an address for RIR {self.rir.name}")


def random_route_distinguisher():
    """
    The RD is an arbitrary unique string up to VRF_RD_MAX_LENGTH (21) characters with no explicit validation.

    However by convention it will be one of:
    - "<2-byte ASN>:<4-byte integer>"
    - "<IPv4 address>:<2-byte integer>"
    - "<4-byte ASN>:<2-byte integer>"
    """
    fake = faker.Faker()
    branch = fake.pyint(0, 2)
    if branch == 0:
        # 16-bit ASNs 64496–64511 are reserved for documentation and sample code
        return f"{fake.pyint(64496, 64511)}:{fake.pyint(0, 2**32 - 1)}"
    if branch == 1:
        return f"{fake.ipv4_private()}:{fake.pyint(0, 2**16 - 1)}"
    # 32-bit ASNs 4200000000-4294967294 are reserved for private use
    return f"{fake.pyint(4200000000, 4294967294)}:{fake.pyint(0, 2**16 - 1)}"


class RouteTargetFactory(PrimaryModelFactory):
    class Meta:
        model = RouteTarget
        exclude = (
            "has_description",
            "has_tenant",
        )

    # Name needs to be globally unique, but the random route-distinguisher generation space is large enough that
    # we'll deal with collisions as and when they occur.
    name = factory.LazyFunction(random_route_distinguisher)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_tenant = factory.Faker("boolean", chance_of_getting_true=75)
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VRFFactory(PrimaryModelFactory):
    class Meta:
        model = VRF
        exclude = (
            "has_description",
            "has_rd",
            "has_tenant",
        )

    # note that name is *not* globally unique
    name = factory.LazyFunction(lambda: f"{faker.Faker().color_name()}{faker.Faker().pyint()}")

    # RD needs to be globally unique, but the random route-distinguisher generation space is large enough that
    # we'll deal with collisions as and when they occur.
    has_rd = factory.Faker("pybool")
    rd = factory.Maybe("has_rd", factory.LazyFunction(random_route_distinguisher), None)

    has_tenant = factory.Faker("boolean", chance_of_getting_true=75)
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    enforce_unique = factory.Faker("pybool")

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    @factory.post_generation
    def import_targets(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.import_targets.set(extracted)
            else:
                self.import_targets.set(get_random_instances(RouteTarget))

    @factory.post_generation
    def export_targets(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.export_targets.set(extracted)
            else:
                self.export_targets.set(get_random_instances(RouteTarget))


class RoleFactory(OrganizationalModelFactory):
    class Meta:
        model = Role
        exclude = ("has_description",)

    class Params:
        unique_name = UniqueFaker("word", part_of_speech="adjective")

    name = factory.LazyAttribute(lambda o: o.unique_name.title())

    weight = factory.Faker("pyint", min_value=100, step=100)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")


class VLANGroupFactory(OrganizationalModelFactory):
    class Meta:
        model = VLANGroup
        exclude = (
            "has_description",
            "has_location",
            "has_site",
        )

    class Params:
        unique_name = UniqueFaker("word", part_of_speech="noun")

    # TODO: name is not globally unique, but (site, name) tuple must be.
    # The likelihood of collision with random names is pretty low, but non-zero.
    # We might want to consider *intentionally* using non-globally-unique names for testing purposes?
    name = factory.LazyAttribute(lambda o: o.unique_name.upper())

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_location = factory.Faker("pybool")
    location = factory.Maybe(
        "has_location", random_instance(lambda: Location.objects.get_for_model(VLANGroup), allow_null=False), None
    )

    has_site = factory.Faker("pybool")

    site = factory.Maybe(
        "has_location",
        factory.LazyAttribute(lambda l: l.location.site or l.location.base_site),
        factory.Maybe(
            "has_site",
            random_instance(Site),
            None,
        ),
    )


class VLANFactory(PrimaryModelFactory):
    class Meta:
        model = VLAN
        exclude = (
            "has_description",
            "has_group",
            "has_location",
            "has_role",
            "has_site",
            "has_tenant",
        )

    # TODO: VID and name do not need to be globally unique, but must be unique within a group (if any)
    # As with VLANGroup, with fully random names and vids, non-uniqueness is unlikely but possible,
    # and we might want to consider intentionally reusing non-unique values for test purposes?
    vid = factory.Faker("pyint", min_value=1, max_value=4094)
    name = factory.LazyFunction(
        lambda: (
            faker.Faker().word(part_of_speech="adjective").capitalize()
            + faker.Faker().word(part_of_speech="noun").capitalize()
        )
    )

    status = random_instance(lambda: Status.objects.get_for_model(VLAN), allow_null=False)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_group = factory.Faker("pybool")
    group = factory.Maybe("has_group", random_instance(VLANGroup, allow_null=False), None)

    has_location = factory.Faker("pybool")
    location = factory.Maybe(
        "has_group",
        factory.LazyAttribute(lambda l: l.group.location),
        factory.Maybe("has_location", random_instance(Location, allow_null=False), None),
    )

    has_role = factory.Faker("pybool")
    role = factory.Maybe("has_role", random_instance(Role), None)

    has_site = factory.Faker("pybool")
    site = factory.Maybe(
        "has_group",
        factory.LazyAttribute(lambda l: l.group.site),
        factory.Maybe(
            "has_location",
            factory.LazyAttribute(lambda l: l.location.site),
            factory.Maybe("has_site", random_instance(Site, allow_null=False), None),
        ),
    )

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VLANGetOrCreateFactory(VLANFactory):
    class Meta:
        django_get_or_create = ("group", "location", "site", "tenant")


class VRFGetOrCreateFactory(VRFFactory):
    class Meta:
        django_get_or_create = ("tenant",)


class PrefixFactory(PrimaryModelFactory):
    """Create random Prefix objects with randomized data.

    Generate child prefixes and ip addresses within the prefix IP space for 50% of prefixes generated.
    Containers will create child prefixes while prefixes that are not containers will create ip addresses
    in the prefix's address space. Defaults to creating 0-4 children. Set `children__max_count` to an
    integer when calling the factory creation methods (`create()`, `create_batch()`, etc) to override
    the maximum number of children generated.

    Examples:

        Create 20 prefixes, approximately half will generate 0-4 children:

            >>> PrefixFactory.create_batch(20)

        Create 20 prefixes with no children:

            >>> PrefixFactory.create_batch(20, children__max_count=0)
    """

    class Meta:
        model = Prefix

    class Params:
        has_description = factory.Faker("pybool")
        has_location = factory.Faker("pybool")
        has_role = factory.Faker("pybool")
        has_site = factory.Faker("pybool")
        has_tenant = factory.Faker("pybool")
        has_vlan = factory.Faker("pybool")
        has_vrf = factory.Faker("pybool")
        is_container = factory.Faker("pybool")
        is_ipv6 = factory.Faker("pybool")
        ipv6_cidr = factory.Faker("ipv6", network=True)
        # faker ipv6 provider generates networks with /0 cidr, change to anything but /0
        ipv6_fixed = factory.LazyAttribute(
            lambda o: o.ipv6_cidr.replace("/0", f"/{UniqueFaker('pyint', min_length=1, max_length=128)!s}")
        )

    prefix = factory.Maybe(
        "is_ipv6",
        factory.SelfAttribute("ipv6_fixed"),
        UniqueFaker("ipv4", network=True, private=True),
    )
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")
    is_pool = factory.Faker("pybool")
    # TODO: create a LocationGetOrCreateFactory to get or create a location with matching site
    location = factory.Maybe(
        "has_location", random_instance(lambda: Location.objects.get_for_model(Prefix), allow_null=False), None
    )
    role = factory.Maybe("has_role", random_instance(Role), None)
    # TODO: create a SiteGetOrCreateFactory to get or create a site with matching tenant
    site = factory.Maybe(
        "has_location",
        factory.LazyAttribute(lambda l: l.location.site or l.location.base_site),
        factory.Maybe("has_site", random_instance(Site, allow_null=False), None),
    )
    status = factory.Maybe(
        "is_container",
        factory.LazyFunction(lambda: Prefix.STATUS_CONTAINER),
        random_instance(
            lambda: Status.objects.get_for_model(Prefix).exclude(pk=Prefix.STATUS_CONTAINER.pk), allow_null=False
        ),
    )
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))
    vlan = factory.Maybe(
        "has_vlan",
        factory.SubFactory(
            VLANGetOrCreateFactory,
            group=None,
            location=factory.SelfAttribute("..location"),
            site=factory.SelfAttribute("..site"),
            tenant=factory.SelfAttribute("..tenant"),
        ),
        None,
    )
    vrf = factory.Maybe(
        "has_vrf",
        factory.SubFactory(VRFGetOrCreateFactory, tenant=factory.SelfAttribute("..tenant")),
        None,
    )

    @factory.post_generation
    def children(self, create, extracted, **kwargs):
        """Creates child prefixes and ip addresses within the prefix IP space.

        Defaults to generating 0-4 child prefixes for parents that are containers,
        or generating 0-4 ip addresses within the prefix's IP space for non-container
        prefixes. Only creates children on 50% of prefixes. Set `children__max_count`
        to an integer when calling the factory creation methods (`create()`,
        `create_batch()`, etc) to override the maximum number of children generated.

        Args:
            create: True if `create` strategy was used.
            extracted: None unless a value was passed in for the PostGeneration declaration at Factory declaration time
            kwargs: Any extra parameters passed as attr__key=value when calling the Factory
        """
        if extracted:
            # Objects have already been created, do nothing
            return

        # Leaf prefixes are of size 1 but can't have children
        if self.prefix.size == 1:
            return

        # 50% chance to create children
        if not faker.Faker().pybool():
            return

        action = "create" if create else "build"
        is_ipv6 = self.family == 6

        # Create child prefixes for containers, otherwise create child ip addresses
        child_factory = PrefixFactory if self.status == Prefix.STATUS_CONTAINER else IPAddressFactory
        method = getattr(child_factory, action)

        # Default to maximum of 4 children unless overridden in kwargs
        max_count = int(kwargs.pop("max_count", 4))
        child_count = faker.Faker().pyint(min_value=0, max_value=min(max_count, self.prefix.size))
        if child_count == 0:
            return

        # Propogate parent tenant to children if parent tenant is set
        if self.tenant is not None:
            kwargs.setdefault("tenant", self.tenant)

        if child_factory == IPAddressFactory:
            # Create child ip addresses, preserving vrf and is_ipv6 from parent
            created = 0
            for address in self.prefix.iter_hosts():
                if created == child_count:
                    break
                addresses_available = self.prefix.size - child_count
                children_remaining = child_count - created
                # Randomly skip addresses if there's enough space left in the prefix
                if faker.Faker().pybool() or addresses_available <= children_remaining:
                    method(address=str(address), vrf=self.vrf, is_ipv6=is_ipv6, **kwargs)
                    created += 1
        else:
            # Calculate prefix length for child prefixes to allow them to fit in the parent prefix without creating duplicate prefix
            child_cidr = self.prefix_length + max(1, math.ceil(math.log(child_count, 2)))
            # Raise exception for invalid cidr length (>128 for ipv6, >32 for ipv4)
            if child_cidr > 128 or self.family == 4 and child_cidr > 32:
                raise ValueError(f"Unable to create {child_count} child prefixes in container prefix {self.cidr_str}.")

            # Create child prefixes, preserving site, location, vrf and is_ipv6 from parent
            for count, address in enumerate(self.prefix.subnet(child_cidr)):
                if count == child_count:
                    break
                method(
                    prefix=str(address.cidr),
                    site=self.site,
                    location=self.location,
                    children__max_count=4,
                    is_ipv6=is_ipv6,
                    vrf=self.vrf,
                    **kwargs,
                )


class IPAddressFactory(PrimaryModelFactory):
    """Create random IPAddress objects with randomized data.

    The fields `assigned_object`, `description`, `dns_name`, `nat_inside`, `role`, `tenant`, and `vrf`
    have a 50% chance to be populated with randomized data, otherwise they are null or blank depending
    on the field. The address has a 50% chance to be ipv4 or ipv6. Uses a self-referential SubFactory
    to create random IPAddress objects to use for the `nat_inside` reference. This can be disabled by
    passing `has_nat_inside=False` to the create/build methods.

    Examples:
        Create 20 IP addresses with 50% chance to generate IP addresses for `nat_inside`:

            >>> IPAddressFactory.create_batch(20)

        Create 20 IP Addresses with `nat_inside` forced to null:

            >>> IPAddressFactory.create_batch(20, has_nat_inside=False)
    """

    class Meta:
        model = IPAddress

    class Params:
        has_assigned_object = factory.Faker("pybool")
        has_description = factory.Faker("pybool")
        has_dns_name = factory.Faker("pybool")
        has_nat_inside = factory.Faker("pybool")
        has_role = factory.Faker("pybool")
        role_choice = factory.Faker("random_element", elements=IPAddressRoleChoices)
        has_tenant = factory.Faker("pybool")
        has_vrf = factory.Faker("pybool")
        is_ipv6 = factory.Faker("pybool")

    address = factory.Maybe(
        "is_ipv6",
        UniqueFaker("ipv6"),
        UniqueFaker("ipv4_private"),
    )
    # TODO: add objects for assigned_object when factories for dcim.interface and virtualization.vminterface are ready
    assigned_object = factory.Maybe("has_assigned_object", None, None)
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")
    dns_name = factory.Maybe("has_dns_name", factory.Faker("hostname"), "")
    nat_inside = factory.SubFactory(
        "nautobot.ipam.factory.IPAddressFactory",
        nat_inside=None,
        is_ipv6=factory.SelfAttribute("..is_ipv6"),
    )
    role = factory.Maybe("has_role", factory.LazyAttribute(lambda obj: obj.role_choice[0]), "")
    status = factory.Maybe(
        "is_ipv6",
        random_instance(lambda: Status.objects.get_for_model(IPAddress), allow_null=False),
        random_instance(lambda: Status.objects.get_for_model(IPAddress).exclude(name="SLAAC"), allow_null=False),
    )
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))
    vrf = factory.Maybe(
        "has_vrf",
        factory.SubFactory(VRFGetOrCreateFactory, tenant=factory.SelfAttribute("..tenant")),
        None,
    )
