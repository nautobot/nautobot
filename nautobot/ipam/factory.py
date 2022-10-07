import logging

import factory
import faker

from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory
from nautobot.dcim.models import Location, Site
from nautobot.extras.models import Status
from nautobot.ipam.models import Aggregate, RIR, Role, RouteTarget, VLAN, VLANGroup, VRF
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
    class Meta:
        model = Aggregate
        exclude = (
            "has_date_added",
            "has_description",
            "has_tenant",
            "is_ipv6",
        )

    rir = random_instance(RIR)

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_date_added = factory.Faker("pybool")
    date_added = factory.Maybe("has_date_added", factory.Faker("date"), None)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    is_ipv6 = factory.Faker("pybool")

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

    has_tenant = factory.Faker("pybool")
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
    name = factory.Faker("color_name")

    # RD needs to be globally unique, but the random route-distinguisher generation space is large enough that
    # we'll deal with collisions as and when they occur.
    has_rd = factory.Faker("pybool")
    rd = factory.Maybe("has_rd", factory.LazyFunction(random_route_distinguisher), None)

    has_tenant = factory.Faker("pybool")
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

    name = factory.LazyFunction(lambda: faker.Faker().word(part_of_speech="adjective").title())

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

    # TODO: name is not globally unique, but (site, name) tuple must be.
    # The likelihood of collision with random names is pretty low, but non-zero.
    # We might want to consider *intentionally* using non-globally-unique names for testing purposes?
    name = factory.LazyFunction(lambda: faker.Faker().word(part_of_speech="noun").upper())

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_location = factory.Faker("pybool")
    location = factory.Maybe("has_location", random_instance(lambda: Location.objects.get_for_model(VLANGroup)), None)

    has_site = factory.Faker("pybool")
    site = factory.Maybe(
        "has_location",
        factory.LazyAttribute(lambda l: l.location.site or l.location.base_site),
        factory.Maybe("has_site", random_instance(Site), None),
    )

    # @classmethod
    # def _adjust_kwargs(cls, **kwargs):
    #     """Fine-tune the randomly generated kwargs to ensure validity."""
    #     if (
    #         kwargs["site"] is not None
    #         and kwargs["location"] is not None
    #         and kwargs["location"].base_site != kwargs["site"]
    #     ):
    #         logger.debug("Fixing mismatch between `site` and `location.base_site` by overriding `site`")
    #         kwargs["site"] = kwargs["location"].base_site

    #     return kwargs


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
    name = factory.LazyFunction(lambda: faker.Faker().word(part_of_speech="noun").capitalize())

    status = random_instance(lambda: Status.objects.get_for_model(VLAN), allow_null=False)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    has_group = factory.Faker("pybool")
    group = factory.Maybe("has_group", random_instance(VLANGroup), None)

    has_location = factory.Faker("pybool")
    location = factory.Maybe(
        "has_group",
        factory.LazyAttribute(lambda l: l.group.location),
        factory.Maybe("has_location", random_instance(Location), None),
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
            factory.Maybe("has_site", random_instance(Site), None),
        ),
    )

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    # @classmethod
    # def _adjust_kwargs(cls, **kwargs):
    #     """Fine-tune the randomly generated kwargs to ensure validity."""
    #     if (
    #         kwargs["group"] is not None
    #         and kwargs["location"] is not None
    #         and kwargs["group"].location is not None
    #         and kwargs["group"].location not in kwargs["location"].ancestors(include_self=True)
    #     ):
    #         logger.debug("Fixing mismatch between `group.location` and `location` by overriding `location`")
    #         kwargs["location"] = randgen.choice(kwargs["group"].location.descendants(include_self=True))

    #     if (
    #         kwargs["site"] is not None
    #         and kwargs["location"] is not None
    #         and kwargs["location"].base_site != kwargs["site"]
    #     ):
    #         logger.debug("Fixing mismatch between `site` and `location.base_site` by overriding `site`")
    #         kwargs["site"] = kwargs["location"].base_site

    #     if kwargs["group"] is not None and kwargs["group"].site != kwargs["site"]:
    #         logger.debug("Fixing mismatch between `group.site` and `site` by overriding `site`")
    #         # TODO: can this conflict with the fixup for site / location.base_site? Time will tell.
    #         kwargs["site"] = kwargs["group"].site

    #     return kwargs
