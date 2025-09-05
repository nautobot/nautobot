import datetime
import logging
import math

from django.contrib.contenttypes.models import ContentType
import factory
import faker

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.factory import (
    get_random_instances,
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.models import Location, VirtualDeviceContext
from nautobot.extras.models import Role, Status
from nautobot.ipam.choices import PrefixTypeChoices
from nautobot.ipam.models import IPAddress, Namespace, Prefix, RIR, RouteTarget, VLAN, VLANGroup, VRF
from nautobot.tenancy.models import Tenant

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

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")


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
        # 16-bit ASNs 64496-64511 are reserved for documentation and sample code
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

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

    has_tenant = factory.Faker("boolean", chance_of_getting_true=75)
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class VRFFactory(PrimaryModelFactory):
    class Meta:
        model = VRF
        exclude = (
            "has_description",
            "has_status",
            "has_tenant",
        )

    # note that name is *not* globally unique
    name = factory.LazyFunction(lambda: f"{faker.Faker().color_name()}{faker.Faker().pyint()}")

    # RD needs to be globally unique, but the random route-distinguisher generation space is large enough that
    # we'll deal with collisions as and when they occur.
    # TODO Need to figure out a way to guarantee uniqueness on the VRF model, as namespace <-> rd combination composite key
    # is not guaranteed to be unique since rd is nullable.
    # Making rd not nullable on the randomly generated data to pass test_composite_key() uniqueness test here.
    rd = factory.LazyFunction(random_route_distinguisher)

    has_tenant = factory.Faker("boolean", chance_of_getting_true=75)
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

    has_status = NautobotBoolIterator()
    status = factory.Maybe(
        "has_status", random_instance(lambda: Status.objects.get_for_model(VRF), allow_null=False), None
    )

    namespace = random_instance(Namespace, allow_null=False)

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

    @factory.post_generation
    def prefixes(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.prefixes.set(extracted)
            else:
                self.prefixes.set(
                    get_random_instances(lambda: Prefix.objects.filter(namespace=self.namespace), minimum=0)
                )

    @factory.post_generation
    def virtual_device_contexts(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.virtual_device_contexts.set(extracted)
            else:
                self.virtual_device_contexts.set(get_random_instances(VirtualDeviceContext))


class VLANGroupFactory(OrganizationalModelFactory):
    class Meta:
        model = VLANGroup
        exclude = (
            "has_description",
            "has_location",
        )

    class Params:
        unique_name = UniqueFaker("word", part_of_speech="noun")

    name = factory.LazyAttribute(lambda o: o.unique_name.upper())

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

    has_location = NautobotBoolIterator()
    location = factory.Maybe(
        "has_location", random_instance(lambda: Location.objects.get_for_model(VLANGroup), allow_null=False), None
    )

    @factory.post_generation
    def children(self, create, extracted, **kwargs):
        """Creates child VLANs within the VLANGroup."""
        if create:
            return

        # 50% chance to create children
        if not faker.Faker().pybool():
            return

        # Default to maximum of 4 children unless overridden in kwargs
        max_count = int(kwargs.pop("max_count", 4))
        child_count = faker.Faker().pyint(min_value=0, max_value=max_count)
        if child_count == 0:
            return

        if extracted and self.has_location:
            VLANFactory.create_batch(size=child_count, location=self.location, vlan_group=self)


class VLANGroupGetOrCreateFactory(VLANGroupFactory):
    class Meta:
        django_get_or_create = "location"


class VLANFactory(PrimaryModelFactory):
    class Meta:
        model = VLAN
        exclude = (
            "has_description",
            "has_vlan_group",
            "has_role",
            "has_tenant",
            "has_location",
        )

    # TODO: VID and name do not need to be globally unique, but must be unique within a group (if any)
    # As with VLANGroup, with fully random names and vids, non-uniqueness is unlikely but possible,
    # and we might want to consider intentionally reusing non-unique values for test purposes?
    vid = factory.Faker("pyint", min_value=1, max_value=4094)
    # Generate names like "vlan__0001__purple__GROUP__Floor-1__242_Vasquez_Freeway" or "vlan__1234__easy",
    # depending on which of (group, location) are defined, if any.
    name = factory.LazyAttribute(
        lambda o: "__".join(
            [
                str(x)
                for x in filter(  # Filter out Nones from the tuple so name isn't "vlan__1234__easy__None__None__None"
                    None,
                    (
                        "vlan",
                        f"{o.vid:04d}",  # "0001" rather than "1", for more consistent names
                        faker.Faker().word(part_of_speech="adjective"),
                        o.vlan_group,  # may be None
                    ),
                )
            ]
        )[:255]  # truncate to max VLAN.name length just to be safe
    )
    has_location = NautobotBoolIterator()

    status = random_instance(lambda: Status.objects.get_for_model(VLAN), allow_null=False)
    has_role = NautobotBoolIterator()
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(VLAN), allow_null=False),
        None,
    )

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")

    has_vlan_group = NautobotBoolIterator()
    vlan_group = factory.Maybe("has_vlan_group", random_instance(VLANGroup, allow_null=False), None)

    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    @factory.post_generation
    def locations(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.locations.set(extracted)
            else:
                vlan_ct = ContentType.objects.get_for_model(VLAN)
                self.locations.set(
                    get_random_instances(
                        lambda: Location.objects.filter(location_type__content_types__in=[vlan_ct]), minimum=0
                    )
                )
                if self.vlan_group and self.vlan_group.location:
                    # add the parent of the vlan group location to the vlan locations
                    self.locations.add(self.vlan_group.location.ancestors(include_self=True)[0])


class VLANGetOrCreateFactory(VLANFactory):
    class Meta:
        django_get_or_create = ("vlan_group", "vid")


class VRFGetOrCreateFactory(VRFFactory):
    class Meta:
        django_get_or_create = ("tenant",)


class NamespaceFactory(PrimaryModelFactory):
    """
    Create random Namespace objects with randomized data.
    """

    class Meta:
        model = Namespace

    name = UniqueFaker("text", max_nb_chars=20)  # could be up to CHARFIELD_MAX_LENGTH but that gets unwieldy fast


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
        has_date_allocated = NautobotBoolIterator()
        has_description = NautobotBoolIterator()
        has_locations = NautobotBoolIterator()
        has_rir = NautobotBoolIterator()
        has_role = NautobotBoolIterator()
        has_tenant = NautobotBoolIterator()
        has_vlan = NautobotBoolIterator()
        is_ipv6 = NautobotBoolIterator()

    prefix = factory.Maybe(
        "is_ipv6",
        UniqueFaker("ipv6_network"),
        UniqueFaker("ipv4", network=True),
    )
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(Prefix), allow_null=False),
        None,
    )
    status = random_instance(lambda: Status.objects.get_for_model(Prefix), allow_null=False)
    type = PrefixTypeChoices.TYPE_CONTAINER  # top level prefix should be a container
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))
    vlan = factory.Maybe(
        "has_vlan",
        factory.SubFactory(
            VLANGetOrCreateFactory,
            tenant=factory.SelfAttribute("..tenant"),
        ),
        None,
    )
    namespace = random_instance(Namespace, allow_null=False)
    rir = factory.Maybe("has_rir", random_instance(RIR, allow_null=False), None)
    date_allocated = factory.Maybe("has_date_allocated", factory.Faker("date_time", tzinfo=datetime.timezone.utc), None)

    @factory.post_generation
    def locations(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.locations.set(extracted)
            else:
                prefix_ct = ContentType.objects.get_for_model(Prefix)
                self.locations.set(
                    get_random_instances(
                        lambda: Location.objects.filter(location_type__content_types__in=[prefix_ct]), minimum=0
                    )
                )

    @factory.post_generation
    def vrfs(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.vrfs.set(extracted)
            else:
                self.vrfs.set(get_random_instances(lambda: VRF.objects.filter(namespace=self.namespace), minimum=0))

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
        if factory.random.randgen.choice([True, False]):
            return

        action = "create" if create else "build"
        is_ipv6 = self.ip_version == 6

        # Create child prefixes for containers, randomly create prefixes or ip addresses for networks
        if self.type == PrefixTypeChoices.TYPE_CONTAINER:
            child_factory = PrefixFactory
        elif self.type == PrefixTypeChoices.TYPE_NETWORK:
            weights = [10, 1]  # prefer ip addresses
            child_factory = factory.random.randgen.choices([IPAddressFactory, PrefixFactory], weights)[0]
        else:
            return

        method = getattr(child_factory, action)

        # Default to maximum of 4 children unless overridden in kwargs
        max_count = int(kwargs.pop("max_count", 4))
        if max_count == 0:
            return
        child_count = faker.Faker().pyint(min_value=1, max_value=min(max_count, self.prefix.size))

        # Propagate parent tenant to children if parent tenant is set
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
                    method(address=str(address), is_ipv6=is_ipv6, namespace=self.namespace, **kwargs)
                    created += 1
        else:
            # Calculate prefix length for child prefixes to allow them to fit in the parent prefix without creating duplicate prefix
            child_cidr = self.prefix_length + max(1, math.ceil(math.log(child_count, 2)))
            # Raise exception for invalid cidr length (>128 for ipv6, >32 for ipv4)
            if child_cidr > 128 or (self.ip_version == 4 and child_cidr > 32):
                raise ValueError(f"Unable to create {child_count} child prefixes in container prefix {self.cidr_str}.")

            weights = [1, 6, 3]  # prefer network and pool prefixes
            child_type = factory.random.randgen.choices(
                [PrefixTypeChoices.TYPE_CONTAINER, PrefixTypeChoices.TYPE_NETWORK, PrefixTypeChoices.TYPE_POOL], weights
            )[0]

            # Create child prefixes, preserving is_ipv6 from parent
            for count, address in enumerate(self.prefix.subnet(child_cidr)):
                if count == child_count:
                    break
                method(
                    prefix=str(address.cidr),
                    is_ipv6=is_ipv6,
                    has_rir=False,
                    namespace=self.namespace,
                    type=child_type,
                    **kwargs,
                )


class IPAddressFactory(PrimaryModelFactory):
    """Create random IPAddress objects with randomized data.

    The fields `description`, `dns_name`, `nat_inside`, `role`, `tenant`, and `vrf` have a 50% chance
    to be populated with randomized data, otherwise they are null or blank depending on the field.
    The address has a 50% chance to be ipv4 or ipv6. Uses a self-referential SubFactory to create
    random IPAddress objects to use for the `nat_inside` reference. This can be disabled by passing
    `has_nat_inside=False` to the create/build methods.

    Examples:
        Create 20 IP addresses with 50% chance to generate IP addresses for `nat_inside`:

            >>> IPAddressFactory.create_batch(20)

        Create 20 IP Addresses with `nat_inside` forced to null:

            >>> IPAddressFactory.create_batch(20, has_nat_inside=False)
    """

    class Meta:
        model = IPAddress

    class Params:
        has_description = NautobotBoolIterator()
        has_dns_name = NautobotBoolIterator()
        has_nat_inside = NautobotBoolIterator()
        has_role = NautobotBoolIterator()
        has_tenant = NautobotBoolIterator()
        is_ipv6 = NautobotBoolIterator()

    # TODO: For some reason, this is not working as expected
    # passing in an address from the PrefixFactory.children is ignored
    # address = factory.Maybe(
    #     "is_ipv6",
    #     UniqueFaker("ipv6"),
    #     UniqueFaker("ipv4_private"),
    # )
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=CHARFIELD_MAX_LENGTH), "")
    dns_name = factory.Maybe("has_dns_name", factory.Faker("hostname"), "")
    # TODO: Needs to be made more robust because prefixes and namespaces need to exist first
    # nat_inside = factory.SubFactory(
    #     "nautobot.ipam.factory.IPAddressFactory",
    #     nat_inside=None,
    #     is_ipv6=factory.SelfAttribute("..is_ipv6"),
    # )
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(IPAddress), allow_null=False),
        None,
    )
    status = factory.Maybe(
        "is_ipv6",
        random_instance(lambda: Status.objects.get_for_model(IPAddress), allow_null=False),
        random_instance(lambda: Status.objects.get_for_model(IPAddress).exclude(name="SLAAC"), allow_null=False),
    )
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))
    # Obviously improve this
    # namespace = Namespace.objects.first()
