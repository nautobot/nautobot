import logging

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
import factory
from faker import Faker
from timezone_field import TimeZoneFormField

from nautobot.circuits.models import CircuitTermination
from nautobot.core.factory import (
    BaseModelFactory,
    get_random_instances,
    NautobotBoolIterator,
    OrganizationalModelFactory,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.choices import (
    ConsolePortTypeChoices,
    ControllerCapabilitiesChoices,
    DeviceRedundancyGroupFailoverStrategyChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    RackDimensionUnitChoices,
    RackTypeChoices,
    RackWidthChoices,
    SoftwareImageFileHashingAlgorithmChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.models import (
    ConsolePortTemplate,
    ConsoleServerPortTemplate,
    Controller,
    ControllerManagedDeviceGroup,
    Device,
    DeviceFamily,
    DeviceRedundancyGroup,
    DeviceType,
    FrontPortTemplate,
    Interface,
    InterfaceTemplate,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleBayTemplate,
    ModuleFamily,
    ModuleType,
    Platform,
    PowerOutletTemplate,
    PowerPanel,
    PowerPortTemplate,
    Rack,
    RackGroup,
    RackReservation,
    RearPortTemplate,
    SoftwareImageFile,
    SoftwareVersion,
    VirtualDeviceContext,
)
from nautobot.extras.models import ExternalIntegration, Role, Status
from nautobot.extras.utils import FeatureQuery
from nautobot.ipam.models import Prefix, VLAN, VLANGroup, VRF
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

TIME_ZONES = sorted(timezone for timezone, _ in TimeZoneFormField().choices)


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


def get_random_software_version_for_device_type(device_type):
    qs = SoftwareVersion.objects.filter(software_image_files__device_types=device_type)
    return factory.random.randgen.choice(qs) if qs.exists() else None


class DeviceFactory(PrimaryModelFactory):
    class Meta:
        model = Device
        exclude = (
            "has_asset_tag",
            "has_comments",
            "has_device_redundancy_group",
            "has_platform",
            "has_serial",
            "has_tenant",
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
    name = factory.LazyAttributeSequence(lambda o, n: f"{o.device_type.model}-{n + 1}")

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

    controller_managed_device_group = random_instance(ControllerManagedDeviceGroup)

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("bs"))

    software_version = factory.LazyAttribute(lambda o: get_random_software_version_for_device_type(o.device_type))

    @factory.post_generation
    def software_image_files(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.software_image_files.set(extracted)
        else:
            self.software_image_files.set(
                get_random_instances(
                    SoftwareImageFile.objects.filter(default_image=True)
                    | SoftwareImageFile.objects.filter(device_types=self.device_type)
                )
            )

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


device_types = (
    "Router",
    "Switch",
    "Firewall",
    "Load Balancer",
    "WLAN Controller",
    "Access Point",
    "SAN Fabric",
    "Console Server",
)


class DeviceTypeFactory(PrimaryModelFactory):
    class Meta:
        model = DeviceType
        exclude = (
            "has_comments",
            "has_device_family",
            "has_part_number",
            "is_subdevice_child",
        )

    has_device_family = NautobotBoolIterator()
    device_family = factory.Maybe("has_device_family", random_instance(DeviceFamily), None)

    manufacturer = random_instance(Manufacturer)

    @factory.lazy_attribute
    def model(self):
        """
        Use a random unused-for-this-manufacturer element from `device_types` if any.

        If all are already used, append " 2" to all device-type strings and try again, and so forth.
        """
        possible_device_types = set(device_types)
        count = 2
        current_models = set(DeviceType.objects.filter(manufacturer=self.manufacturer).values_list("model", flat=True))
        unused_models = possible_device_types.difference(current_models)
        while not unused_models:
            unused_models = {f"{device_type} {count}" for device_type in device_types}.difference(current_models)
            count += 1
        return factory.random.randgen.choice(sorted(unused_models))

    has_part_number = NautobotBoolIterator()
    part_number = factory.Maybe("has_part_number", factory.Faker("ean", length=8), "")

    # If randomly a subdevice, set u_height to 0.
    is_subdevice_child = NautobotBoolIterator(chance_of_getting_true=33)
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

    @factory.post_generation
    def software_image_files(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            self.software_image_files.set(extracted)
        else:
            self.software_image_files.set(get_random_instances(SoftwareImageFile))


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


class DeviceFamilyFactory(PrimaryModelFactory):
    class Meta:
        model = DeviceFamily
        exclude = ("has_description",)

    name = UniqueFaker("word")

    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")


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
        if self.name in ["Root", "Campus", "Building"]:
            # All appropriate content-types
            self.content_types.set(ContentType.objects.filter(FeatureQuery("locations").get_query()))
        elif self.name in ["Floor"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Controller),
                    ContentType.objects.get_for_model(Prefix),
                    ContentType.objects.get_for_model(Rack),
                    ContentType.objects.get_for_model(RackGroup),
                    ContentType.objects.get_for_model(VLANGroup),
                ]
            )
        elif self.name in ["Room"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Controller),
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
                    ContentType.objects.get_for_model(Controller),
                    ContentType.objects.get_for_model(Cluster),
                    ContentType.objects.get_for_model(PowerPanel),
                    ContentType.objects.get_for_model(VLAN),
                ]
            )
        elif self.name in ["Aisle"]:
            self.content_types.set(
                [
                    ContentType.objects.get_for_model(Controller),
                    ContentType.objects.get_for_model(CircuitTermination),
                    ContentType.objects.get_for_model(Device),
                    ContentType.objects.get_for_model(Module),
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
    time_zone = factory.Maybe("has_time_zone", factory.Faker("random_element", elements=TIME_ZONES))

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

    location = random_instance(lambda: Location.objects.get_for_model(Rack), allow_null=False)

    has_rack_group = NautobotBoolIterator()  # TODO there's no RackGroupFactory yet...
    rack_group = factory.Maybe("has_rack_group", random_instance(RackGroup), None)

    has_tenant = NautobotBoolIterator()
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

    has_tenant = NautobotBoolIterator(chance_of_getting_true=75)
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)

    user = random_instance(User, allow_null=False)

    # Note no "has_description" here, RackReservation.description is mandatory.
    description = factory.Faker("sentence")


class SoftwareImageFileFactory(PrimaryModelFactory):
    class Meta:
        model = SoftwareImageFile

    class Params:
        has_image_file_checksum = NautobotBoolIterator()
        has_hashing_algorithm = NautobotBoolIterator()
        has_image_file_size = NautobotBoolIterator()
        has_download_url = NautobotBoolIterator()
        has_external_integration = NautobotBoolIterator()

    status = random_instance(
        lambda: Status.objects.get_for_model(SoftwareImageFile),
        allow_null=False,
    )
    software_version = random_instance(SoftwareVersion, allow_null=False)
    image_file_name = UniqueFaker("file_name", extension="bin")
    image_file_checksum = factory.Maybe("has_image_file_checksum", factory.Faker("md5"), "")
    hashing_algorithm = factory.Maybe(
        "has_hashing_algorithm",
        factory.Faker("random_element", elements=SoftwareImageFileHashingAlgorithmChoices.values()),
        "",
    )
    image_file_size = factory.Maybe("has_image_file_size", factory.Faker("pyint"), None)
    download_url = factory.Maybe("has_download_url", factory.Faker("uri"), "")
    default_image = factory.LazyAttribute(
        lambda o: not o.software_version.software_image_files.filter(default_image=True).exists()
    )
    external_integration = factory.Maybe("has_external_integration", random_instance(ExternalIntegration))


class SoftwareVersionFactory(PrimaryModelFactory):
    class Meta:
        model = SoftwareVersion

    class Params:
        has_alias = NautobotBoolIterator()
        has_release_date = NautobotBoolIterator()
        has_end_of_support_date = NautobotBoolIterator()
        has_documentation_url = NautobotBoolIterator()

    status = random_instance(
        lambda: Status.objects.get_for_model(SoftwareVersion),
        allow_null=False,
    )
    platform = random_instance(Platform, allow_null=False)
    version = factory.Faker("numerify", text="%!.%!.%!")
    alias = factory.Maybe("has_alias", factory.Faker("word"), "")
    release_date = factory.Maybe("has_release_date", factory.Faker("date_object"), None)
    end_of_support_date = factory.Maybe("has_end_of_support_date", factory.Faker("date_object"), None)
    documentation_url = factory.Maybe("has_documentation_url", factory.Faker("uri"), "")
    long_term_support = NautobotBoolIterator()
    pre_release = NautobotBoolIterator()


class ControllerFactory(PrimaryModelFactory):
    class Meta:
        model = Controller
        exclude = ("has_capabilities",)

    class Params:
        has_device = NautobotBoolIterator()

    name = UniqueFaker("word")
    description = factory.Faker("sentence")
    status = random_instance(lambda: Status.objects.get_for_model(Controller), allow_null=False)
    role = random_instance(lambda: Role.objects.get_for_model(Controller))
    has_capabilities = NautobotBoolIterator()
    capabilities = factory.Maybe(
        "has_capabilities",
        factory.Faker("random_elements", elements=ControllerCapabilitiesChoices.values(), unique=True),
        [],
    )
    platform = random_instance(Platform)
    location = random_instance(lambda: Location.objects.get_for_model(Controller), allow_null=False)
    tenant = random_instance(Tenant)
    external_integration = random_instance(ExternalIntegration)
    controller_device = factory.Maybe("has_device", random_instance(Device), None)
    controller_device_redundancy_group = factory.Maybe("has_device", None, random_instance(DeviceRedundancyGroup))


class ControllerManagedDeviceGroupFactory(PrimaryModelFactory):
    class Meta:
        model = ControllerManagedDeviceGroup
        exclude = ("has_capabilities",)

    class Params:
        has_parent = NautobotBoolIterator()

    name = UniqueFaker("word")
    parent = factory.Maybe("has_parent", random_instance(ControllerManagedDeviceGroup), None)
    controller = factory.LazyAttribute(
        lambda o: o.parent.controller if o.parent else factory.random.randgen.choice(Controller.objects.all())
    )
    has_capabilities = NautobotBoolIterator()
    capabilities = factory.Maybe(
        "has_capabilities",
        factory.Faker("random_elements", elements=ControllerCapabilitiesChoices.values(), unique=True),
        [],
    )
    weight = factory.Faker("pyint", min_value=1, max_value=1000)


module_types = (
    "Supervisor",
    "Line Card",
    "Fabric",
)


class ModuleTypeFactory(PrimaryModelFactory):
    class Meta:
        model = ModuleType
        exclude = ("has_part_number", "has_comments")

    manufacturer = random_instance(Manufacturer, allow_null=False)
    module_family = random_instance(ModuleFamily, allow_null=True)

    has_part_number = NautobotBoolIterator()
    part_number = factory.Maybe("has_part_number", factory.Faker("ean", length=8), "")

    has_comments = NautobotBoolIterator()
    comments = factory.Maybe("has_comments", factory.Faker("bs"))

    @factory.lazy_attribute
    def model(self):
        """
        Use a random unused-for-this-manufacturer element from `module_types` if any.

        If all are already used, append " 2" to all module-type strings and try again, and so forth.
        """
        possible_module_types = set(module_types)
        count = 2
        current_models = set(ModuleType.objects.filter(manufacturer=self.manufacturer).values_list("model", flat=True))
        unused_models = possible_module_types.difference(current_models)
        while not unused_models:
            unused_models = {f"{module_type} {count}" for module_type in module_types}.difference(current_models)
            count += 1
        return factory.random.randgen.choice(sorted(unused_models))


class ModuleFactory(PrimaryModelFactory):
    class Meta:
        model = Module
        exclude = (
            "has_asset_tag",
            "has_parent_module_bay",
            "has_role",
            "has_serial",
            "has_tenant",
        )

    module_type = random_instance(ModuleType, allow_null=False)
    status = random_instance(
        lambda: Status.objects.get_for_model(Module),
        allow_null=False,
    )
    has_parent_module_bay = NautobotBoolIterator()
    parent_module_bay = factory.Maybe(
        "has_parent_module_bay",
        random_instance(lambda: ModuleBay.objects.filter(installed_module__isnull=True), allow_null=False),
        None,
    )
    location = factory.Maybe(
        "has_parent_module_bay",
        None,
        random_instance(
            lambda: Location.objects.filter(location_type__content_types=ContentType.objects.get_for_model(Module)),
            allow_null=False,
        ),
    )
    has_role = NautobotBoolIterator()
    role = factory.Maybe(
        "has_role",
        random_instance(lambda: Role.objects.get_for_model(Module)),
        None,
    )
    has_asset_tag = NautobotBoolIterator()
    asset_tag = factory.Maybe("has_asset_tag", UniqueFaker("uuid4"), None)
    has_serial = NautobotBoolIterator()
    serial = factory.Maybe("has_serial", factory.Faker("ean", length=8), "")
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant, allow_null=False), None)


class DeviceComponentTemplateFactory(BaseModelFactory):
    class Params:
        has_label = NautobotBoolIterator()
        has_description = NautobotBoolIterator()

    device_type = random_instance(DeviceType.objects.all(), allow_null=False)
    label = factory.Maybe(
        "has_label",
        factory.Faker("word"),
        "",
    )
    description = factory.Maybe(
        "has_description",
        factory.Faker("sentence"),
        "",
    )


class ModularDeviceComponentTemplateFactory(DeviceComponentTemplateFactory):
    class Params:
        has_device_type = NautobotBoolIterator()

    device_type = factory.Maybe("has_device_type", random_instance(DeviceType, allow_null=False), None)
    module_type = factory.Maybe("has_device_type", None, random_instance(ModuleType, allow_null=False))


class ConsolePortTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = ConsolePortTemplate

    type = factory.Faker("random_element", elements=ConsolePortTypeChoices.values())
    name = factory.Sequence(lambda n: f"ConsolePort {n}")


class ConsoleServerPortTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = ConsoleServerPortTemplate

    type = factory.Faker("random_element", elements=ConsolePortTypeChoices.values())
    name = factory.Sequence(lambda n: f"ConsoleServerPort {n}")


class PowerPortTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = PowerPortTemplate

    type = factory.Faker("random_element", elements=PowerPortTypeChoices.values())
    name = factory.Sequence(lambda n: f"PowerPort {n}")


class PowerOutletTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = PowerOutletTemplate

    type = factory.Faker("random_element", elements=PowerOutletTypeChoices.values())
    name = factory.Sequence(lambda n: f"PowerOutlet {n}")


class InterfaceTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = InterfaceTemplate

    type = factory.Faker("random_element", elements=InterfaceTypeChoices.values())
    name = factory.Sequence(lambda n: f"Interface {n}")


class FrontPortTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = FrontPortTemplate

    device_type = factory.Maybe(
        "has_device_type",
        random_instance(DeviceType.objects.filter(rear_port_templates__isnull=False), allow_null=False),
        None,
    )
    module_type = factory.Maybe(
        "has_device_type",
        None,
        random_instance(ModuleType.objects.filter(rear_port_templates__isnull=False), allow_null=False),
    )
    type = factory.Faker("random_element", elements=PortTypeChoices.values())
    name = factory.Sequence(lambda n: f"FrontPort {n}")

    @factory.lazy_attribute
    def rear_port_template(self):
        if self.module_type:
            return factory.random.randgen.choice(self.module_type.rear_port_templates.all())
        else:
            return factory.random.randgen.choice(self.device_type.rear_port_templates.all())

    @factory.lazy_attribute
    def rear_port_position(self):
        return self.rear_port_template.front_port_templates.count() + 1


class RearPortTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = RearPortTemplate

    type = factory.Faker("random_element", elements=PortTypeChoices.values())
    name = factory.Sequence(lambda n: f"RearPort {n}")
    positions = factory.Sequence(lambda n: n + 100)


class ModuleBayTemplateFactory(ModularDeviceComponentTemplateFactory):
    class Meta:
        model = ModuleBayTemplate

    name = factory.Sequence(lambda n: f"ModuleBay {n}")
    position = factory.Maybe(
        "has_device_type",
        factory.LazyAttribute(lambda o: o.device_type.module_bay_templates.count() + 1),
        factory.LazyAttribute(lambda o: o.module_type.module_bay_templates.count() + 1),
    )

    class Params:
        has_module_family = NautobotBoolIterator()

    module_family = factory.Maybe(
        "has_module_family",
        random_instance(ModuleFamily),
        None,
    )


class VirtualDeviceContextFactory(PrimaryModelFactory):
    class Meta:
        model = VirtualDeviceContext
        exclude = ("has_role", "has_tenant", "has_description")

    status = random_instance(
        lambda: Status.objects.get_for_model(VirtualDeviceContext),
        allow_null=False,
    )
    has_role = NautobotBoolIterator()
    role = factory.Maybe(
        "has_role",
        random_instance(
            lambda: Role.objects.get_for_model(VirtualDeviceContext),
            allow_null=False,
        ),
        None,
    )
    identifier = factory.Sequence(
        lambda n: n + 101
    )  # Start at 101 to avoid conflicts VirtualDeviceContexts API test cases.
    name = factory.Sequence(lambda n: f"VirtualDeviceContext {n}")
    device = random_instance(Device, allow_null=False)
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe(
        "has_tenant",
        random_instance(Tenant, allow_null=False),
        None,
    )
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")

    @factory.post_generation
    def interfaces(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.interfaces.set(extracted)
            else:
                self.interfaces.set(get_random_instances(Interface.objects.filter(device=self.device)))

    @factory.post_generation
    def vrfs(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.vrfs.set(extracted)
            else:
                self.vrfs.set(get_random_instances(VRF.objects.all()))
