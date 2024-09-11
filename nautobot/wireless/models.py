from django.core.validators import MinValueValidator
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseModel
from nautobot.core.models.fields import ChoiceArrayField, JSONArrayField
from nautobot.core.models.generics import PrimaryModel
from nautobot.extras.utils import extras_features
from nautobot.wireless.choices import (
    ChannelWidthChoices,
    RadioFrequencyChoices,
    RadioStandardChoices,
    RegulatoryDomainChoices,
    WirelessAuthTypeChoices,
    WirelessDeploymentModeChoices,
)


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class AccessPointGroup(PrimaryModel):
    """
    An AccessPointGroup is a collection of access points. It is used to apply common configuration to multiple
    access points at once.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    controller = models.ForeignKey(
        to="dcim.Controller",
        on_delete=models.PROTECT,
        related_name="access_point_groups",
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["name"]
        unique_together = ["name", "controller"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class SupportedDataRate(PrimaryModel):
    """
    A SupportedDataRate represents a data rate that can be used by an access point radio.
    """

    standard = models.CharField(max_length=CHARFIELD_MAX_LENGTH, choices=RadioStandardChoices)
    rate = models.FloatField(
        validators=[MinValueValidator(1)],
        help_text="Enter rate in Mbps.",
    )
    mcs_index = models.IntegerField(
        blank=True,
        null=True,
        help_text="The Modulation and Coding Scheme (MCS) index is a value used in wireless communications to define the modulation type, coding rate, and number of spatial streams used in a transmission.",
    )

    class Meta:
        ordering = ["standard", "rate"]
        unique_together = ["standard", "rate"]

    def __str__(self):
        return f"{self.standard}: {self.rate} Mbps"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class RadioProfile(PrimaryModel):
    """
    A RadioProfile is a collection of settings that can be applied to an access point radio.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    frequency = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=RadioFrequencyChoices,
    )
    tx_power_min = models.IntegerField()
    tx_power_max = models.IntegerField()
    channel_width = ChoiceArrayField(base_field=models.IntegerField(), default=list, choices=ChannelWidthChoices)
    allowed_channel_list = JSONArrayField(base_field=models.IntegerField(), default=list)
    supported_data_rates = models.ManyToManyField(
        to="wireless.SupportedDataRate",
        related_name="radio_profiles",
        blank=True,
    )
    regulatory_domain = models.CharField(max_length=CHARFIELD_MAX_LENGTH, choices=RegulatoryDomainChoices)
    rx_power_min = models.IntegerField()

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
    "webhooks",
)
class WirelessNetwork(PrimaryModel):
    """
    A WirelessNetwork represents a wireless network that can be broadcast by an access point.
    """

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    ssid = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    mode = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=WirelessDeploymentModeChoices,
    )
    enabled = models.BooleanField(default=True)
    authentication = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        choices=WirelessAuthTypeChoices,
    )
    secrets_group = models.ForeignKey(
        to="extras.SecretsGroup",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
    )
    hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class AccessPointGroupWirelessNetworkAssignment(BaseModel):
    """
    An AccessPointGroupWirelessNetworkAssignment represents the assignment of a WirelessNetwork to an AccessPointGroup.
    """

    access_point_group = models.ForeignKey(
        to="wireless.AccessPointGroup",
        on_delete=models.CASCADE,
        related_name="wireless_network_assignments",
    )
    wireless_network = models.ForeignKey(
        to="wireless.WirelessNetwork",
        on_delete=models.CASCADE,
        related_name="access_point_group_assignments",
    )
    vlan = models.ForeignKey(
        to="ipam.VLAN",
        on_delete=models.PROTECT,
        related_name="access_point_group_wireless_network_assignments",
        blank=True,
        null=True,
    )
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["access_point_group", "wireless_network"]
        ordering = ["access_point_group", "wireless_network"]

    def __str__(self):
        return f"{self.access_point_group}: {self.wireless_network}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class AccessPointGroupRadioProfile(BaseModel):
    """
    An AccessPointGroupRadioProfile represents the assignment of a RadioProfile to an AccessPointGroup.
    """

    access_point_group = models.ForeignKey(
        to="wireless.AccessPointGroup",
        on_delete=models.CASCADE,
        related_name="radio_profile_assignments",
    )
    radio_profile = models.ForeignKey(
        to="wireless.RadioProfile",
        on_delete=models.CASCADE,
        related_name="access_point_group_assignments",
    )
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["access_point_group", "radio_profile"]
        ordering = ["access_point_group", "radio_profile"]

    def __str__(self):
        return f"{self.access_point_group}: {self.radio_profile}"


@extras_features(
    "custom_links",
    "custom_validators",
    "export_templates",
    "graphql",
)
class AccessPointGroupDevicesAssignment(BaseModel):
    """
    An AccessPointGroupDevicesAssignment represents the assignment of a Device to an AccessPointGroup.
    """

    access_point_group = models.ForeignKey(
        to="wireless.AccessPointGroup",
        on_delete=models.CASCADE,
        related_name="access_points",
    )
    device = models.ForeignKey(
        to="dcim.Device",
        on_delete=models.CASCADE,
        related_name="access_point_groups",
    )
    is_metadata_associable_model = False

    class Meta:
        unique_together = ["access_point_group", "device"]
        ordering = ["access_point_group", "device"]

    def __str__(self):
        return f"{self.access_point_group}: {self.device}"
