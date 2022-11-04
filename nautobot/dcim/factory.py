import factory
import logging
import pytz
import random
from faker import Faker

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q

from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory
from nautobot.circuits.models import CircuitTermination
from nautobot.dcim.choices import DeviceRedundancyGroupFailoverStrategyChoices, SubdeviceRoleChoices
from nautobot.dcim.models import (
    Device,
    DeviceRedundancyGroup,
    DeviceRole,
    DeviceType,
    Manufacturer,
    Platform,
    Location,
    LocationType,
    Region,
    Rack,
    RackGroup,
    PowerPanel,
    Site,
)
from nautobot.extras.models import Status
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.utilities.choices import ColorChoices
from nautobot.utilities.factory import random_instance, UniqueFaker
from nautobot.virtualization.models import Cluster


logger = logging.getLogger(__name__)

# For a randomly deterministic set of vendor names. Must be a tuple.
MANUFACTURER_NAMES = (
    "A10",
    "Arista",
    "Aruba",
    "Brocade",
    "Cisco",
    "Citrix",
    "Dell",
    "F5",
    "Force10",
    "Fortinet",
    "Huawei",
    "Juniper",
    "HP",
    "Palo Alto",
)

# For `Platform.napalm_driver`, either randomly choose based on Manufacturer slug.
NAPALM_DRIVERS = {
    "arista": ["eos"],
    "cisco": ["ios", "iosxr", "iosxr_netconf", "nxos", "nxos_ssh"],
    "juniper": ["junos"],
    "palo-alto": ["panos"],
}


class DeviceTypeFactory(PrimaryModelFactory):
    class Meta:
        model = DeviceType
        exclude = (
            "has_part_number",
            "is_subdevice_child",
            "has_comments",
        )

    manufacturer = random_instance(Manufacturer)

    # Slug isn't defined here since it will always inherit from model.
    model = factory.LazyAttributeSequence(lambda o, n: f"{o.manufacturer.name} DeviceType {n + 1}")

    has_part_number = factory.Faker("pybool")
    part_number = factory.Maybe("has_part_number", factory.Faker("ean", length=8), "")

    # If randomly a subdevice, set u_height to 0.
    is_subdevice_child = factory.Faker("boolean", chance_of_getting_true=33)
    u_height = factory.Maybe("is_subdevice_child", 0, factory.Faker("pyint", min_value=1, max_value=2))

    is_full_depth = factory.Faker("pybool")

    # If randomly a subdevice, also set subdevice_role to "child". We might want to reconsider this.
    subdevice_role = factory.Maybe(
        "is_subdevice_child",
        SubdeviceRoleChoices.ROLE_CHILD,
        factory.Faker("random_element", elements=["", SubdeviceRoleChoices.ROLE_PARENT]),
    )

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class DeviceRedundancyGroupFactory(PrimaryModelFactory):
    class Meta:
        model = DeviceRedundancyGroup
        exclude = ("has_description", "has_comments")

    class Params:
        unique_name = UniqueFaker("word", part_of_speech="adjective")

    # Slug isn't defined here since it will always inherit from name.
    name = factory.LazyAttribute(lambda o: o.unique_name.title())

    status = random_instance(lambda: Status.objects.get_for_model(DeviceRedundancyGroup), allow_null=False)

    failover_strategy = factory.Iterator(
        DeviceRedundancyGroupFailoverStrategyChoices.CHOICES, getter=lambda choice: choice[0]
    )

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class DeviceRoleFactory(OrganizationalModelFactory):
    class Meta:
        model = DeviceRole
        exclude = ("has_description",)

    # Slug isn't defined here since it will always inherit from name.
    name = factory.Sequence(lambda n: f"Fake Device Role {n}")
    color = factory.Iterator(ColorChoices.CHOICES, getter=lambda choice: choice[0])
    vm_role = factory.Faker("pybool")

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class ManufacturerFactory(OrganizationalModelFactory):
    class Meta:
        model = Manufacturer
        exclude = ("has_description",)

    # Slug isn't defined here since it will always inherit from name.
    name = UniqueFaker("word", ext_word_list=MANUFACTURER_NAMES)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class PlatformFactory(OrganizationalModelFactory):
    class Meta:
        model = Platform
        exclude = ("has_manufacturer", "manufacturer_slug", "has_description", "has_napalm_args")

    # This dictates `name` and `napalm_driver`.
    has_manufacturer = factory.Faker("pybool")

    # Slug isn't defined here since it will always inherit from name.
    name = factory.Maybe(
        "has_manufacturer",
        factory.LazyAttributeSequence(lambda o, n: f"{o.manufacturer.name} Platform {n + 1}"),
        factory.Sequence(lambda n: f"Fake Platform {n}"),
    )

    manufacturer = factory.Maybe("has_manufacturer", random_instance(Manufacturer), None)

    # If it has a manufacturer, it *might* have a napalm_driver.
    napalm_driver = factory.Maybe(
        "has_manufacturer",
        factory.LazyAttribute(lambda o: random.choice(NAPALM_DRIVERS.get(o.manufacturer.slug, [""]))),
        "",
    )

    has_napalm_args = factory.Faker("pybool")
    napalm_args = factory.Maybe(
        "has_napalm_args", factory.Faker("pydict", nb_elements=2, value_types=[str, bool, int]), None
    )

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class RegionFactory(OrganizationalModelFactory):
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


class SiteFactory(PrimaryModelFactory):
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
    time_zone = factory.Maybe("has_time_zone", factory.LazyFunction(lambda: pytz.timezone(Faker().timezone())), None)

    has_physical_address = factory.Faker("pybool")
    physical_address = factory.Maybe("has_physical_address", factory.Faker("address"))

    has_shipping_address = factory.Faker("pybool")
    shipping_address = factory.Maybe("has_shipping_address", factory.Faker("address"))

    # Faker().latitude()/longitude() sometimes will generate a decimal number with more than 8 digits.
    # Which will make validations for those fields fail.
    # This is a way to formulate the number to make sure it generates no more than 5 digits.
    has_latitude = factory.Faker("pybool")
    latitude = factory.Maybe("has_latitude", factory.LazyFunction(lambda: f"{Faker().latitude():.2f}"), None)

    has_longitude = factory.Faker("pybool")
    longitude = factory.Maybe("has_longitude", factory.LazyFunction(lambda: f"{Faker().longitude():.2f}"), None)

    has_contact_name = factory.Faker("pybool")
    contact_name = factory.Maybe("has_contact_name", factory.Faker("name"))

    has_contact_phone = factory.Faker("pybool")
    # Opt not to use factory.Faker("phone_number") because contact_phone has a 20 char limit
    # whereas factory.Faker("phone_number") generates more than 20 chars
    contact_phone = factory.Maybe("has_contact_phone", factory.Sequence(lambda n: f"1091-65912-{n:04d}"))

    has_contact_email = factory.Faker("pybool")
    contact_email = factory.Maybe("has_contact_email", factory.Faker("safe_email"))


class LocationTypeFactory(OrganizationalModelFactory):
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


class LocationFactory(PrimaryModelFactory):
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
        candidate_parents = Q(pk=None)
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
                    return None
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
