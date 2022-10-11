import logging

import factory
import faker

from nautobot.core.factory import OrganizationalModelFactory, PrimaryModelFactory
from nautobot.dcim.models import DeviceType, Manufacturer, Platform
from nautobot.dcim.choices import SubdeviceRoleChoices
from nautobot.utilities.factory import random_instance, UniqueFaker


logger = logging.getLogger(__name__)


class ManufacturerFactory(OrganizationalModelFactory):
    class Meta:
        model = Manufacturer
        exclude = ("has_description",)

    class Params:
        unique_name = UniqueFaker("word")

    # Slug isn't defined here since it will always inherit from name.
    name = factory.LazyAttribute(lambda o: o.unique_name.title())

    has_description = factory.Faker("pybool")
    description = factory.Maybe("has_description", factory.Faker("text", max_nb_chars=200), "")


class ManufacturerGetOrCreateFactory(ManufacturerFactory):
    class Meta:
        django_get_or_create = ("name",)


class PlatformFactory(OrganizationalModelFactory):
    class Meta:
        model = Platform
        exclude = ("has_manufacturer", "has_description", "has_napalm_driver", "has_napalm_args")

    # Slug isn't defined here since it will always inherit from name.
    name = factory.LazyFunction(
        lambda: faker.Faker().word(part_of_speech="adjective").title() + " " + faker.Faker().word().title()
    )

    has_manufacturer = factory.Faker("pybool")
    manufacturer = factory.Maybe("has_manufacturer", random_instance(Manufacturer), None)

    has_napalm_driver = factory.Faker("pybool")
    napalm_driver = factory.Maybe("has_napalm_driver", factory.Faker("locale"), "")

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

    model = factory.LazyFunction(
        lambda: faker.Faker().word(part_of_speech="adjective").title() + " " + faker.Faker().word().title()
    )

    slug = UniqueFaker("word")
    has_part_number = factory.Faker("pybool")
    part_number = factory.Maybe("has_part_number", factory.Faker("ean", length=8), "")

    # If randomly a subdevice, set u_height to 0.
    is_subdevice_child = factory.Faker("pybool")
    u_height = factory.Maybe("is_subdevice_child", 0, factory.Faker("random_int", min=1, max=4))

    is_full_depth = factory.Faker("pybool")

    # If randomly a subdevice, also set subdevice_role to "child". We might want to reconsider this.
    subdevice_role = factory.Maybe(
        "is_subdevice_child",
        SubdeviceRoleChoices.ROLE_CHILD,
        factory.Faker("random_element", elements=["", SubdeviceRoleChoices.ROLE_PARENT]),
    )

    has_comments = factory.Faker("pybool")
    comments = factory.Maybe("has_comments", factory.Faker("paragraph"), "")
