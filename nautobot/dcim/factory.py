import factory
from factory.django import DjangoModelFactory

from nautobot.dcim.models import Location, LocationType, Region, Site
from nautobot.tenancy.models import Tenant
from nautobot.utilities.factory import random_instance, UniqueFaker


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region


class SiteFactory(DjangoModelFactory):
    class Meta:
        model = Site


class LocationTypeFactory(DjangoModelFactory):
    class Meta:
        model = LocationType
        exclude = (
            "has_parent",
            "has_description",
        )

    name = UniqueFaker(
        "random_element",
        elements=(
            "Continent",
            "Country",
            "State",
            "City",
            "Building",
            "Floor",
            "Room",
            "RackGroup",
            "Rack",
            "BabyRack",
        ),
    )
    has_parent = factory.Faker("pybool")
    parent = factory.Maybe("has_parent", random_instance(LocationType), None)
    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class LocationFactory(DjangoModelFactory):
    class Meta:
        model = Location
        exclude = (
            "has_parent",
            "has_site",
            "has_tenant",
            "has_description",
        )

    name = UniqueFaker(
        "random_element",
        elements=(
            "Africa",
            "North America",
            "Asia",
            "Australia",
            "Europe",
            "United States",
            "Russia",
            "China",
            "Building 1",
            "Building 2",
            "Building 3",
            "Building 4",
            "Building 5",
            "Building 6",
            "Floor 1",
            "Floor 2",
            "Floor 3",
            "Floor 4",
            "Floor 5",
        ),
    )
    location_type = random_instance(LocationType)

    has_parent = factory.LazyAttribute(lambda l: True if l.location_type.parent else False)
    parent = factory.Maybe(
        "has_parent",
        factory.LazyAttribute(
            lambda l: factory.random.randgen.choice(Location.objects.filter(location_type=l.location_type.parent))
            if Location.objects.count()
            else None
        ),
    )

    has_site = factory.LazyAttribute(lambda l: False if l.has_parent else True)
    site = factory.Maybe("has_site", random_instance(Site))

    has_tenant = factory.Faker("pybool")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
