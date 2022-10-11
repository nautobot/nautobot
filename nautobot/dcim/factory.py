import logging
import random

import factory
import factory.fuzzy

from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory
from nautobot.dcim.models import DeviceType, Manufacturer, Platform
from nautobot.dcim.choices import SubdeviceRoleChoices
from nautobot.utilities.factory import random_instance, UniqueFaker


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


class ManufacturerFactory(OrganizationalModelFactory):
    class Meta:
        model = Manufacturer
        exclude = ("has_description",)

    # Slug isn't defined here since it will always inherit from name.
    name = UniqueFaker("word", ext_word_list=MANUFACTURER_NAMES)

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")


class PlatformFactory(OrganizationalModelFactory):
    class Meta:
        model = Platform
        exclude = ("has_manufacturer", "manufacturer_slug", "has_description", "has_napalm_args")

    # This dictates `name` and `napalm_driver`.
    has_manufacturer = factory.Faker("pybool")

    # Slug isn't defined here since it will always inherit from name.
    name = factory.Maybe(
        "has_manufacturer",
        factory.LazyAttributeSequence(lambda o, n: "%s Platform %d" % (o.manufacturer.name, n + 1)),
        factory.Sequence(lambda n: "Platform %d" % n),
    )

    manufacturer = factory.Maybe("has_manufacturer", random_instance(Manufacturer), None)

    # If it has a manufacturer, it *might* have a naplam_driver.
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
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")


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
    model = factory.LazyAttributeSequence(lambda o, n: "%s DeviceType %d" % (o.manufacturer.name, n + 1))

    has_part_number = factory.Faker("pybool")
    part_number = factory.Maybe("has_part_number", factory.Faker("ean", length=8), "")

    # If randomly a subdevice, set u_height to 0.
    is_subdevice_child = factory.Faker("boolean", chance_of_getting_true=33)
    u_height = factory.Maybe("is_subdevice_child", 0, factory.fuzzy.FuzzyInteger(1, 4))

    is_full_depth = factory.Faker("pybool")

    # If randomly a subdevice, also set subdevice_role to "child". We might want to reconsider this.
    subdevice_role = factory.Maybe(
        "is_subdevice_child",
        SubdeviceRoleChoices.ROLE_CHILD,
        factory.Faker("random_element", elements=["", SubdeviceRoleChoices.ROLE_PARENT]),
    )

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")
