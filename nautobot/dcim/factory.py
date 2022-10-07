import factory
import pytz
from factory.django import DjangoModelFactory

from django.contrib.contenttypes.models import ContentType

from nautobot.dcim.models import Location, LocationType, Region, Site, Device
from nautobot.extras.models import Status
from nautobot.ipam.models import Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.utilities.factory import random_instance, UniqueFaker


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
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")


class SiteFactory(DjangoModelFactory):
    class Meta:
        model = Site
        exclude = ("has_region", "has_tenant")

    name = UniqueFaker("street_address")
    status = random_instance(lambda: Status.objects.get_for_model(Site), allow_null=False)

    has_region = factory.Faker("pybool")
    region = factory.Maybe("has_region", random_instance(Region), None)

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))

    time_zone = pytz.timezone("US/Eastern")
    physical_address = factory.Faker("address")
    shipping_address = factory.Faker("address")
    latitude = factory.Faker("latitude")
    longitude = factory.Faker("longitude")
    contact_name = factory.Faker("name")
    contact_phone = factory.Sequence(lambda n: f"1091-65912-{n:04d}")
    contact_email = factory.Faker("company_email")


class LocationTypeFactory(DjangoModelFactory):
    class Meta:
        model = LocationType
        exclude = ("has_description",)

    name = factory.Sequence(
        lambda n: "Root"
        if n == 0
        else (
            "Building"
            if n == 1
            else ("Floor" if n == 2 else ("Elevator" if n == 3 else ("Room" if n == 4 else "Aisle")))
        )
    )
    parent = factory.LazyAttribute(
        lambda l: LocationType.objects.get(name="Building")
        if l.name in ["Floor", "Elevator"]
        else (
            LocationType.objects.get(name="Floor")
            if l.name == "Room"
            else (LocationType.objects.get(name="Room") if l.name == "Aisle" else None)
        )
    )

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")

    @factory.post_generation
    def content_types(self, create, extract, **kwargs):
        """Assign some contenttypes to a location after generation"""
        if self.name in ["Building", "Floor"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Prefix),
                    ContentType.objects.get_for_model(VLANGroup),
                    ContentType.objects.get_for_model(VLAN),
                ]
            )
        elif self.name in ["Room", "Elevator"]:
            self.content_types.set([ContentType.objects.get_for_model(VLAN)])
        elif self.name in ["Aisle"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Device),
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
        )

    location_type = factory.Sequence(
        lambda n: LocationType.objects.get(name="Building")
        if n == 0
        else (
            LocationType.objects.get(name="Floor")
            if n == 1
            else (
                LocationType.objects.get(name="Room")
                if n == 2
                else LocationType.objects.all()[n % LocationType.objects.all().count()]
            )
        )
    )
    name = factory.LazyAttributeSequence(lambda l, n: f"{l.location_type.name}-{n:02d}")
    status = random_instance(lambda: Status.objects.get_for_model(Location), allow_null=False)

    has_parent = factory.LazyAttribute(lambda l: bool(l.location_type.parent))
    parent = factory.Maybe(
        "has_parent",
        factory.LazyAttribute(
            lambda l: factory.random.randgen.choice(Location.objects.filter(location_type=l.location_type.parent))
            if Location.objects.count()
            else None
        ),
    )

    has_site = factory.LazyAttribute(lambda l: not bool(l.has_parent))
    site = factory.Maybe("has_site", random_instance(Site))

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")
