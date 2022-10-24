import factory
import pytz
from factory.django import DjangoModelFactory
from faker import Faker

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.circuits.models import CircuitTermination
from nautobot.dcim.models import Device, Location, LocationType, Region, Rack, RackGroup, PowerPanel, Site
from nautobot.extras.models import Status
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.utilities.factory import random_instance, UniqueFaker
from nautobot.virtualization.models import Cluster


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region
        exclude = (
            "has_parent",
            "has_description",
        )

    has_parent = factory.Faker("pybool")
    parent = factory.Maybe("has_parent", random_instance(Region), None)
    name = factory.Maybe("has_parent", UniqueFaker("city"), UniqueFaker("country"))

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence", nb_words=5), "")


class SiteFactory(DjangoModelFactory):
    class Meta:
        model = Site
        exclude = (
            "has_asn",
            "has_region",
            "has_tenant",
            "has_time_zone",
            "has_physical_address",
            "has_shipping_address",
            "has_latitude",
            "has_longitude",
            "has_contact_name",
            "has_contact_phone",
            "has_contact_email",
        )

    name = UniqueFaker("street_address")
    status = random_instance(lambda: Status.objects.get_for_model(Site), allow_null=False)

    has_asn = factory.Faker("pybool")
    asn = factory.Maybe("has_asn", factory.Sequence(lambda n: 65000 + n), None)

    has_region = factory.Faker("pybool")
    region = factory.Maybe("has_region", random_instance(Region), None)

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_time_zone = factory.Faker("pybool")
    time_zone = factory.Maybe("has_time_zone", factory.LazyAttribute(lambda o: pytz.timezone(Faker().timezone())), None)

    has_physical_address = factory.Faker("pybool")
    physical_address = factory.Maybe("has_physical_address", factory.Faker("address"))

    has_shipping_address = factory.Faker("pybool")
    shipping_address = factory.Maybe("has_shipping_address", factory.Faker("address"))

    has_latitude = factory.Faker("pybool")
    latitude = factory.Maybe("has_latitude", factory.Faker("latitude"))

    has_longitude = factory.Faker("pybool")
    longitude = factory.Maybe("has_longitude", factory.Faker("longitude"))

    has_contact_name = factory.Faker("pybool")
    contact_name = factory.Maybe("has_contact_name", factory.Faker("name"))

    has_contact_phone = factory.Faker("pybool")
    # Opt not to use factory.Faker("phone_number") because contact_phone has a 20 char limit
    # whereas factory.Faker("phone_number") generates more than 20 chars
    contact_phone = factory.Maybe("has_contact_phone", factory.Sequence(lambda n: f"1091-65912-{n:04d}"))

    has_contact_email = factory.Faker("pybool")
    contact_email = factory.Maybe("has_contact_email", factory.Faker("safe_email"))


class LocationTypeFactory(DjangoModelFactory):
    class Meta:
        model = LocationType
        exclude = ("has_description",)

    name = factory.Iterator(["Root", "Campus", "Building", "Floor", "Elevator", "Room", "Aisle"])

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence", nb_words=5), "")

    nestable = factory.LazyAttribute(lambda l: bool(l.name in ["Campus", "Root"]))

    @factory.lazy_attribute
    def parent(self):
        if self.name == "Building":
            return LocationType.objects.get(name="Campus")
        if self.name in ["Floor", "Elevator"]:
            return LocationType.objects.get(name="Building")
        if self.name == "Room":
            return LocationType.objects.get(name="Floor")
        if self.name == "Aisle":
            return LocationType.objects.get(name="Room")
        return None

    @factory.post_generation
    def content_types(self, create, extract, **kwargs):
        """Assign some contenttypes to a location after generation"""
        if self.name in ["Root", "Campus"]:
            self.content_types.set(ContentType.objects.filter(FeatureQuery("locations").get_query()))
        elif self.name in ["Building", "Floor"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Prefix),
                    ContentType.objects.get_for_model(Rack),
                    ContentType.objects.get_for_model(RackGroup),
                    ContentType.objects.get_for_model(VLANGroup),
                    ContentType.objects.get_for_model(VLAN),
                ]
            )
        elif self.name in ["Room"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Cluster),
                    ContentType.objects.get_for_model(PowerPanel),
                    ContentType.objects.get_for_model(Rack),
                    ContentType.objects.get_for_model(RackGroup),
                    ContentType.objects.get_for_model(VLAN),
                ]
            )
        elif self.name in ["Elevator"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Cluster),
                    ContentType.objects.get_for_model(PowerPanel),
                    ContentType.objects.get_for_model(VLAN),
                ]
            )
        elif self.name in ["Aisle"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(CircuitTermination),
                    ContentType.objects.get_for_model(Device),
                    ContentType.objects.get_for_model(PowerPanel),
                    ContentType.objects.get_for_model(Rack),
                    ContentType.objects.get_for_model(RackGroup),
                    ContentType.objects.get_for_model(VLAN),
                ]
            )


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location
        exclude = (
            "has_parent",
            "has_site",
            "has_tenant",
            "has_description",
            "_parent",
        )

    name = factory.LazyAttributeSequence(lambda l, n: f"{l.location_type.name}-{n:02d}")
    status = random_instance(lambda: Status.objects.get_for_model(Location), allow_null=False)

    @factory.iterator
    def location_type():  # pylint: disable=no-method-argument
        lts = LocationType.objects.all()
        for lt in lts:
            yield lt

    @factory.lazy_attribute
    def parent(self):
        """
        The parent attribute of all the location types other than root and campus are deterministic.
        There is a 50% chance whether a root or campus type location (both nestable) have a parent.
        """
        candidate_parents = Q()
        # LocationType that does have a parent
        if self.location_type.parent is not None:
            candidate_parents |= Q(location_type=self.location_type.parent)
            if self.location_type.nestable:
                candidate_parents |= Q(location_type=self.location_type)
        # LocationType that does not have a parent, but could be nestable
        else:
            if self.location_type.nestable:
                # 50% chance to have a parent
                if not Faker().pybool():
                    return
                candidate_parents |= Q(location_type=self.location_type)
        parents = Location.objects.filter(candidate_parents)
        if parents.exists():
            return factory.random.randgen.choice(parents)
        return None

    has_site = factory.LazyAttribute(lambda l: not bool(l.parent))
    site = factory.Maybe("has_site", random_instance(Site, allow_null=False), None)

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence", nb_words=5), "")
