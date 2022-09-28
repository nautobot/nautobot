import factory
from factory.django import DjangoModelFactory

from nautobot.extras.factory import get_random_tags_for_model
from nautobot.ipam.models import Aggregate, RIR
from nautobot.tenancy.models import Tenant
from nautobot.utilities.factory import random_instance, UniqueFaker


class RIRFactory(DjangoModelFactory):
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
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    # TODO custom field data?


class AggregateFactory(DjangoModelFactory):
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
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    is_ipv6 = factory.Faker("pybool")

    # TODO custom field data?

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.tags.set(extracted)
            else:
                self.tags.set(get_random_tags_for_model(self._meta.model))

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
            unique_id = factory.random.randgen.randint(0, 2**32 - 1)
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
