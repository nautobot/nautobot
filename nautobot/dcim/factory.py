import logging

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import factory
from faker import Faker
import pytz

from nautobot.circuits.models import CircuitTermination
from nautobot.core.factory import (
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.choices import (
    DeviceRedundancyGroupFailoverStrategyChoices,
    RackDimensionUnitChoices,
    RackTypeChoices,
    RackWidthChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.models import (
    Device,
    DeviceRedundancyGroup,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    PowerPanel,
    Rack,
    RackGroup,
    RackReservation,
)
from nautobot.extras.models import Role, Status
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster

logger = logging.getLogger(__name__)

User = get_user_model()

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
    "HP",
    "Huawei",
    "Juniper",
    "Palo Alto",
)

# For `Platform.napalm_driver` and `Platform.network_driver`, either randomly choose based on Manufacturer name.
NAPALM_DRIVERS = {
    "Arista": ["eos"],
    "Cisco": ["ios", "iosxr", "iosxr_netconf", "nxos", "nxos_ssh"],
    "Juniper": ["junos"],
    "Palo Alto": ["panos"],
}


NETWORK_DRIVERS = {
    "A10": ["a10"],
    "Arista": ["arista_eos"],
    "Aruba": ["aruba_os", "aruba_procurve"],
    "Cisco": ["cisco_ios", "cisco_xr", "cisco_nxos", "cisco_xe"],
    "Dell": ["dell_force10", "dell_os10"],
    "F5": ["f5_ltm", "f5_tmsh", "f5_linux"],
    "Fortinet": ["fortinet"],
    "HP": ["hp_comware", "hp_procurve"],
    "Huawei": ["huawei"],
    "Juniper": ["juniper_junos"],
    "Palo Alto": ["paloalto_panos"],
}


# Retrieve correct rack reservation units
def get_rack_reservation_units(obj):
    available_units = obj.rack.units
    unavailable_units = []
    for rack in obj.rack.rack_reservations.exclude(id=obj.id):
        unavailable_units += rack.units
    return [unit for unit in available_units if unit not in unavailable_units][:1]


def get_random_platform_for_manufacturer(manufacturer):
    qs = Platform.objects.filter(manufacturer=manufacturer)
    return factory.random.randgen.choice(qs) if qs.exists() else None


class DeviceFactory(PrimaryModelFactory):
    class Meta:
        model = Device
        exclude = (
            "has_tenant",
            "has_platform",
            "has_serial",
            "has_asset_tag",
            "has_device_redundancy_group",
            "has_comments",
        )

    device_type = random_instance(DeviceType, allow_null=False)
    status = random_instance(
        lambda: Status.objects.get_for_model(Device),
        allow_null=False,
    )
    role = random_instance(
        lambda: Role.objects.get_for_model(Device),
        allow_null=False,
    )
    location = random_instance(
        lambda: Location.objects.filter(location_type__content_types=ContentType.objects.get_for_model(Device)),
        allow_null=False,
    )
    name = factory.LazyAttributeSequence(lambda o, n: f"{o.device_type.model} Device - {o.location} - {n + 1}")

    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant))
    has_platform = NautobotBoolIterator()
    platform = factory.Maybe(
        "has_platform",
        factory.LazyAttribute(lambda o: get_random_platform_for_manufacturer(o.device_type.manufacturer)),
        None,
    )

    has_serial = NautobotBoolIterator()
    serial = factory.Maybe("has_serial", factory.Faker("ean", length=8), "")

    has_asset_tag = NautobotBoolIterator()
    asset_tag = factory.Maybe("has_asset_tag", UniqueFaker("uuid4"), None)

    has_device_redundancy_group = NautobotBoolIterator()
    device_redundancy_group = factory.Maybe(
        "has_device_redundancy_group",
        random_instance(DeviceRedundancyGroup),
    )
    device_redundancy_group_priority = factory.Maybe(
        "has_device_redundancy_group",
        factory.Faker("pyint", min_value=1, max_value=500),
    )

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("bs"))

    # TODO to be done after these model factories are done.
    # has_cluster = NautobotBoolIterator()
    # cluster = factory.Maybe(
    #     "has_cluster",
    #     random_instance(Cluster),
    # )

    # has_virtual_chassis = NautobotBoolIterator()
    # virtual_chassis = factory.Maybe(
    #     "has_virtual_chassis",
    #     random_instance(VirtualChassis),
    # )
    # has_vc_position = NautobotBoolIterator()
    # vc_position = factory.Maybe(
    #     "has_vc_position",
    #     factory.Faker("pyint", min_value=1, max_value=256),
    # )
    # has_vc_priority = NautobotBoolIterator()
    # vc_priority = factory.Maybe(
    #     "has_vc_priority",
    #     factory.Faker("pyint", min_value=1, max_value=256),
    # )

    # has_secrets_group = NautobotBoolIterator()
    # secrets_group = factory.Maybe(
    #     "has_secrets_group",
    #     random_instance(SecretsGroup),
    # )

    # has_rack = NautobotBoolIterator()
    # rack = factory.Maybe(
    #     "has_rack",
    #     random_instance(Rack),
    # )
    # has_position = NautobotBoolIterator()
    # position = factory.Maybe("has_position", factory.Faker("pyint", min_value=1, max_value=256))
    # has_face = NautobotBoolIterator()
    # face = factory.Maybe(
    #     "has_face",
    #     factory.Iterator(DeviceFaceChoices.CHOICES, getter=lambda choice: choice[0]),
    #     None,
    # )
    # has_primary_ip4 = NautobotBoolIterator()
    # primary_ip4 = factory.Maybe(
    #     "has_primary_ip4",
    #     random_instance(lambda: IPAddress.objects.filter(ip_version=4), allow_null=False),
    # )

    # has_primary_ip6 = NautobotBoolIterator()
    # primary_ip6 = factory.Maybe(
    #     "has_primary_ip6",
    #     random_instance(lambda: IPAddress.objects.filter(ip_version=6), allow_null=False),
    # )


class DeviceTypeFactory(PrimaryModelFactory):
    class Meta:
        model = DeviceType
        exclude = (
            "has_part_number",
            "is_subdevice_child",
            "has_comments",
        )

    manufacturer = random_instance(Manufacturer)

    model = factory.LazyAttributeSequence(lambda o, n: f"{o.manufacturer.name} DeviceType {n + 1}")

    has_part_number = NautobotBoolIterator()
    part_number = factory.Maybe("has_part_number", factory.Faker("ean", length=8), "")

    # If randomly a subdevice, set u_height to 0.
    is_subdevice_child = factory.Faker("boolean", chance_of_getting_true=33)
    u_height = factory.Maybe("is_subdevice_child", 0, factory.Faker("pyint", min_value=1, max_value=2))

    is_full_depth = NautobotBoolIterator()

    # If randomly a subdevice, also set subdevice_role to "child". We might want to reconsider this.
    subdevice_role = factory.Maybe(
        "is_subdevice_child",
        SubdeviceRoleChoices.ROLE_CHILD,
        factory.Faker("random_element", elements=["", SubdeviceRoleChoices.ROLE_PARENT]),
    )

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class DeviceRedundancyGroupFactory(PrimaryModelFactory):
    class Meta:
        model = DeviceRedundancyGroup
        exclude = ("has_description", "has_comments")

    name = factory.LazyFunction(
        lambda: "".join(word.title() for word in Faker().words(nb=2, part_of_speech="adjective", unique=True))
    )
    status = random_instance(lambda: Status.objects.get_for_model(DeviceRedundancyGroup), allow_null=False)

    failover_strategy = factory.Iterator(
        DeviceRedundancyGroupFailoverStrategyChoices.CHOICES, getter=lambda choice: choice[0]
    )

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class ManufacturerFactory(OrganizationalModelFactory):
    class Meta:
        model = Manufacturer
        exclude = ("has_description",)

    name = UniqueFaker("word", ext_word_list=MANUFACTURER_NAMES)

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class PlatformFactory(OrganizationalModelFactory):
    class Meta:
        model = Platform
        exclude = ("has_manufacturer", "has_description", "has_napalm_args")

    # This dictates `name` and `napalm_driver`.
    has_manufacturer = NautobotBoolIterator()

    name = factory.Maybe(
        "has_manufacturer",
        factory.LazyAttributeSequence(lambda o, n: f"{o.manufacturer.name} Platform {n + 1}"),
        factory.Sequence(lambda n: f"Fake Platform {n}"),
    )

    manufacturer = factory.Maybe("has_manufacturer", random_instance(Manufacturer), None)

    # If it has a manufacturer, it *might* have a napalm_driver.
    napalm_driver = factory.Maybe(
        "has_manufacturer",
        factory.LazyAttribute(lambda o: factory.random.randgen.choice(NAPALM_DRIVERS.get(o.manufacturer.name, [""]))),
        "",
    )

    has_napalm_args = NautobotBoolIterator()
    napalm_args = factory.Maybe(
        "has_napalm_args", factory.Faker("pydict", nb_elements=2, value_types=[str, bool, int]), None
    )

    has_description = NautobotBoolIterator()
    network_driver = factory.Maybe(
        "has_manufacturer",
        factory.LazyAttribute(lambda o: factory.random.randgen.choice(NETWORK_DRIVERS.get(o.manufacturer.name, [""]))),
        "",
    )

    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


class LocationTypeFactory(OrganizationalModelFactory):
    class Meta:
        model = LocationType
        exclude = ("has_description",)

    name = factory.Iterator(["Root", "Campus", "Building", "Floor", "Elevator", "Room", "Aisle"])

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence", nb_words=5), "")

    nestable = factory.LazyAttribute(lambda loc_type: bool(loc_type.name in ["Campus", "Root"]))

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
            "has_asn",
            "has_comments",
            "has_facility",
            "has_tenant",
            "has_time_zone",
            "has_physical_address",
            "has_shipping_address",
            "has_latitude",
            "has_longitude",
            "has_contact_name",
            "has_contact_phone",
            "has_contact_email",
            "has_tenant",
            "has_description",
            "_parent",
        )

    name = factory.LazyAttributeSequence(lambda loc, num: f"{loc.location_type.name}-{num:02d}")
    status = random_instance(lambda: Status.objects.get_for_model(Location), allow_null=False)

    has_asn = NautobotBoolIterator()
    asn = factory.Maybe("has_asn", factory.Sequence(lambda n: 65000 + n), None)

    has_facility = NautobotBoolIterator()
    facility = factory.Maybe("has_facility", factory.Faker("building_number"), "")

    has_time_zone = NautobotBoolIterator()
    time_zone = factory.Maybe("has_time_zone", factory.Faker("random_element", elements=pytz.common_timezones))

    has_physical_address = NautobotBoolIterator()
    physical_address = factory.Maybe("has_physical_address", factory.Faker("address"))

    has_shipping_address = NautobotBoolIterator()
    shipping_address = factory.Maybe("has_shipping_address", factory.Faker("address"))

    # Faker().latitude()/longitude() sometimes will generate a decimal number with more than 8 digits.
    # Which will make validations for those fields fail.
    # This is a way to formulate the number to make sure it generates no more than 5 digits.
    has_latitude = NautobotBoolIterator()
    latitude = factory.Maybe("has_latitude", factory.LazyFunction(lambda: f"{Faker().latitude():.2f}"), None)

    has_longitude = NautobotBoolIterator()
    longitude = factory.Maybe("has_longitude", factory.LazyFunction(lambda: f"{Faker().longitude():.2f}"), None)

    has_contact_name = NautobotBoolIterator()
    contact_name = factory.Maybe("has_contact_name", factory.Faker("name"))

    has_contact_phone = NautobotBoolIterator()
    contact_phone = factory.Maybe("has_contact_phone", factory.Faker("phone_number"))

    has_contact_email = NautobotBoolIterator()
    contact_email = factory.Maybe("has_contact_email", factory.Faker("safe_email"))

    has_parent = NautobotBoolIterator()

    @factory.lazy_attribute_sequence
    def location_type(self, n):
        if not self.has_parent:
            lts = ["Root", "Campus"]
        else:
            lts = ["Root", "Campus", "Building", "Floor", "Elevator", "Room", "Aisle"]
        count = len(lts)
        name = lts[n % count]
        return LocationType.objects.get(name=name)

    @factory.lazy_attribute
    def parent(self):
        """
        Select a valid parent for this location based on the location type parent and nestable fields.
        """
        if not self.has_parent:
            return None
        candidate_parents = Q(pk=None)
        # LocationType that does have a parent
        if self.location_type.parent is not None:
            candidate_parents |= Q(location_type=self.location_type.parent)
            if self.location_type.nestable:
                candidate_parents |= Q(location_type=self.location_type)
        # LocationType that does not have a parent, but could be nestable
        else:
            if self.location_type.nestable:
                candidate_parents |= Q(location_type=self.location_type)
        parents = Location.objects.filter(candidate_parents)
        if parents.exists():
            return factory.random.randgen.choice(parents)
        return None

    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence", nb_words=5), "")

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("sentence", nb_words=5), "")


class RackFactory(PrimaryModelFactory):
    class Meta:
        model = Rack
        exclude = (
            "has_asset_tag",
            "has_comments",
            "has_facility_id",
            "has_rack_group",
            "has_outer_depth",
            "has_outer_width",
            "has_role",
            "has_serial",
            "has_tenant",
            "has_type",
        )

    name = factory.Sequence(lambda n: f"Rack {n}")
    status = random_instance(lambda: Status.objects.get_for_model(Rack), allow_null=False)

    has_role = NautobotBoolIterator()
    role = factory.Maybe("has_role", random_instance(lambda: Role.objects.get_for_model(Rack)), None)

    location = random_instance(lambda: Location.objects.get_for_model(VLANGroup), allow_null=False)

    has_rack_group = NautobotBoolIterator()  # TODO there's no RackGroupFactory yet...
    rack_group = factory.Maybe("has_rack_group", random_instance(RackGroup), None)

    has_tenant = factory.Faker("boolean")
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    has_serial = NautobotBoolIterator()
    serial = factory.Maybe("has_serial", factory.Faker("uuid4"), "")

    has_asset_tag = NautobotBoolIterator()
    asset_tag = factory.Maybe("has_asset_tag", UniqueFaker("uuid4"), None)

    has_type = NautobotBoolIterator()
    type = factory.Maybe("has_type", factory.Faker("random_element", elements=RackTypeChoices.values()), "")

    width = factory.Faker("random_element", elements=RackWidthChoices.values())
    u_height = factory.Faker("pyint", min_value=10, max_value=100)
    desc_units = NautobotBoolIterator()

    has_outer_width = NautobotBoolIterator()
    outer_width = factory.Maybe("has_outer_width", factory.Faker("pyint"), None)

    has_outer_depth = NautobotBoolIterator()
    outer_depth = factory.Maybe("has_outer_depth", factory.Faker("pyint"), None)

    outer_unit = factory.Maybe(
        "has_outer_width",
        factory.Faker("random_element", elements=RackDimensionUnitChoices.values()),
        factory.Maybe(
            "has_outer_depth", factory.Faker("random_element", elements=RackDimensionUnitChoices.values()), ""
        ),
    )

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")


class RackReservationFactory(PrimaryModelFactory):
    class Meta:
        model = RackReservation
        exclude = ("has_tenant",)

    rack = random_instance(Rack, allow_null=False)
    units = factory.LazyAttribute(get_rack_reservation_units)

    has_tenant = factory.Faker("boolean", chance_of_getting_true=75)
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    user = random_instance(User, allow_null=False)

    # Note no "has_description" here, RackReservation.description is mandatory.
    description = factory.Faker("sentence")
