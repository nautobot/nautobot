import factory
import faker

from nautobot.core.factory import (
    BaseModelFactory,
    get_random_instances,
    NautobotBoolIterator,
    PrimaryModelFactory,
    random_instance,
    UniqueFaker,
)
from nautobot.dcim.factory import ControllerManagedDeviceGroupFactory, DeviceFactory
from nautobot.ipam.models import VLAN
from nautobot.tenancy.models import Tenant
from nautobot.wireless import models
from nautobot.wireless.choices import (
    RadioProfileChannelWidthChoices,
    RadioProfileFrequencyChoices,
    RadioProfileRegulatoryDomainChoices,
    SupportedDataRateStandardChoices,
    WirelessNetworkAuthenticationChoices,
    WirelessNetworkModeChoices,
)


class SupportedDataRateFactory(PrimaryModelFactory):
    class Meta:
        model = models.SupportedDataRate

    standard = factory.Faker("random_element", elements=SupportedDataRateStandardChoices.values())
    rate = UniqueFaker("pyint", min_value=1000, max_value=164000, step=1000)
    mcs_index = factory.Faker("pyint", min_value=0, max_value=9)


class RadioProfileFactory(PrimaryModelFactory):
    class Meta:
        model = models.RadioProfile

    name = UniqueFaker("word")
    frequency = factory.Faker("random_element", elements=RadioProfileFrequencyChoices.values())
    channel_width = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements(RadioProfileChannelWidthChoices.values(), unique=True))
    )
    regulatory_domain = factory.Faker("random_element", elements=RadioProfileRegulatoryDomainChoices.values())
    tx_power_min = factory.Faker("pyint", min_value=1, max_value=5)
    tx_power_max = factory.Faker("pyint", min_value=6, max_value=30)
    rx_power_min = factory.Faker("pyint", min_value=1, max_value=10)
    allowed_channel_list = factory.LazyFunction(
        lambda: sorted(faker.Faker().random_elements([1, 6, 11, 36, 161, 165], unique=True))
    )

    @factory.post_generation
    def supported_data_rates(self, create, extracted, **kwargs):
        if create:
            if extracted:
                self.supported_data_rates.set(extracted)
            else:
                self.supported_data_rates.set(get_random_instances(models.SupportedDataRate, minimum=0))


class WirelessNetworkFactory(PrimaryModelFactory):
    class Meta:
        model = models.WirelessNetwork
        exclude = ("has_description", "has_tenant")

    name = UniqueFaker("word")
    has_description = NautobotBoolIterator()
    description = factory.Maybe("has_description", factory.Faker("sentence"), "")
    ssid = factory.Faker("word")
    mode = factory.Faker("random_element", elements=WirelessNetworkModeChoices.values())
    enabled = NautobotBoolIterator()
    authentication = factory.Faker("random_element", elements=WirelessNetworkAuthenticationChoices.values())
    # TODO: once SecretsGroupFactory is implemented:
    # has_secrets_group = NautobotBoolIterator()
    # secrets_group = factory.Maybe(
    #     "has_secrets_group",
    #     random_instance(SecretsGroup),
    # )
    hidden = NautobotBoolIterator()
    has_tenant = NautobotBoolIterator()
    tenant = factory.Maybe("has_tenant", random_instance(Tenant), None)


class ControllerManagedDeviceGroupWirelessNetworkAssignmentFactory(BaseModelFactory):
    class Meta:
        model = models.ControllerManagedDeviceGroupWirelessNetworkAssignment

    controller_managed_device_group = factory.SubFactory(ControllerManagedDeviceGroupFactory, capabilities=["wireless"])
    wireless_network = factory.SubFactory(WirelessNetworkFactory)
    vlan = random_instance(VLAN, allow_null=True)


class ControllerManagedDeviceGroupRadioProfileAssignmentFactory(BaseModelFactory):
    class Meta:
        model = models.ControllerManagedDeviceGroupRadioProfileAssignment

    controller_managed_device_group = factory.SubFactory(ControllerManagedDeviceGroupFactory, capabilities=["wireless"])
    radio_profile = factory.SubFactory(RadioProfileFactory)


class ControllerManagedDeviceGroupWithMembersFactory(ControllerManagedDeviceGroupFactory):
    capabilities = ["wireless"]
    wireless1 = factory.RelatedFactory(
        ControllerManagedDeviceGroupWirelessNetworkAssignmentFactory,
        factory_related_name="controller_managed_device_group",
    )
    wireless2 = factory.RelatedFactory(
        ControllerManagedDeviceGroupWirelessNetworkAssignmentFactory,
        factory_related_name="controller_managed_device_group",
    )
    radio1 = factory.RelatedFactory(
        ControllerManagedDeviceGroupRadioProfileAssignmentFactory,
        factory_related_name="controller_managed_device_group",
    )
    radio2 = factory.RelatedFactory(
        ControllerManagedDeviceGroupRadioProfileAssignmentFactory,
        factory_related_name="controller_managed_device_group",
    )
    device1 = factory.RelatedFactory(DeviceFactory, factory_related_name="controller_managed_device_group")
    device2 = factory.RelatedFactory(DeviceFactory, factory_related_name="controller_managed_device_group")


class RadioProfilesWithMembersFactory(RadioProfileFactory):
    controller_managed_device_group1 = factory.RelatedFactory(
        ControllerManagedDeviceGroupRadioProfileAssignmentFactory, factory_related_name="radio_profile"
    )
    controller_managed_device_group2 = factory.RelatedFactory(
        ControllerManagedDeviceGroupRadioProfileAssignmentFactory, factory_related_name="radio_profile"
    )


class WirelessNetworksWithMembersFactory(WirelessNetworkFactory):
    controller_managed_device_group1 = factory.RelatedFactory(
        ControllerManagedDeviceGroupWirelessNetworkAssignmentFactory, factory_related_name="wireless_network"
    )
    controller_managed_device_group2 = factory.RelatedFactory(
        ControllerManagedDeviceGroupWirelessNetworkAssignmentFactory, factory_related_name="wireless_network"
    )
