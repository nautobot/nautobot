import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.core.templatetags.helpers import render_boolean

from .models import AccessPointGroup, RadioProfile, SupportedDataRate, WirelessNetwork


class AccessPointGroupTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    description = tables.Column()
    controller = tables.Column(linkify=True)
    tenant = tables.Column(linkify=True)
    # devices = LinkedCountColumn()
    # radio_profiles = LinkedCountColumn()
    # wireless_networks = LinkedCountColumn()
    tags = TagColumn(url_name="wireless:accesspointgroup_list")
    actions = ButtonsColumn(AccessPointGroup)

    class Meta(BaseTable.Meta):
        model = AccessPointGroup
        fields = (
            "pk",
            "name",
            "description",
            "controller",
            "tenant",
            # "devices",
            # "radio_profiles",
            # "wireless_networks",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "controller",
            "tenant",
            "actions",
        )


class RadioProfileTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    tags = TagColumn(url_name="wireless:radioprofile_list")
    actions = ButtonsColumn(RadioProfile)

    class Meta(BaseTable.Meta):
        model = RadioProfile
        fields = (
            "pk",
            "name",
            "frequency",
            "channel_width",
            "allowed_channel_list",
            "tx_power_min",
            "tx_power_max",
            "rx_power_min",
            "regulatory_domain",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "frequency",
            "channel_width",
            "allowed_channel_list",
            "actions",
        )

    def render_channel_width(self, value):
        return ", ".join(f"{v}MHz" for v in value)

    def render_allowed_channel_list(self, value):
        return ", ".join(f"{v}" for v in value)


class SupportedDataRateTable(BaseTable):
    pk = ToggleColumn()
    rate = tables.Column(linkify=True)
    standard = tables.Column()
    mcs_index = tables.Column()
    tags = TagColumn(url_name="wireless:supporteddatarate_list")
    actions = ButtonsColumn(SupportedDataRate)

    class Meta(BaseTable.Meta):
        model = SupportedDataRate
        fields = (
            "pk",
            "rate",
            "standard",
            "mcs_index",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "rate",
            "standard",
            "mcs_index",
            "actions",
        )


class WirelessNetworkTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    description = tables.Column()
    tags = TagColumn(url_name="wireless:wirelessnetwork_list")
    actions = ButtonsColumn(WirelessNetwork)

    class Meta(BaseTable.Meta):
        model = WirelessNetwork
        fields = (
            "pk",
            "name",
            "ssid",
            "mode",
            "authentication",
            "enabled",
            "hidden",
            "secret",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "ssid",
            "mode",
            "authentication",
            "enabled",
            "hidden",
            "description",
            "actions",
        )

    def render_enabled(self, value):
        return render_boolean(value)

    def render_hidden(self, value):
        return render_boolean(value)


class AccessPointGroupWirelessNetworkAssignmentTable(BaseTable):
    access_point_group = tables.Column(linkify=True)
    wireless_network = tables.Column(linkify=True)
    vlan = tables.Column(linkify=True)
    ssid = tables.Column(accessor="wireless_network.ssid")
    mode = tables.Column(accessor="wireless_network.mode")
    authentication = tables.Column(accessor="wireless_network.authentication")
    enabled = tables.Column(accessor="wireless_network.enabled")
    hidden = tables.Column(accessor="wireless_network.hidden")
    secrets_group = tables.Column(accessor="wireless_network.secrets_group", linkify=True)
    controller = tables.Column(accessor="access_point_group.controller", linkify=True)
    prefix_count = LinkedCountColumn(
        viewname="ipam:prefix_list",
        url_params={"vlan_id": "vlan_id"},
        verbose_name="Prefixes",
        reverse_lookup="vlan__access_point_group_wireless_network_assignments",
    )

    class Meta(BaseTable.Meta):
        model = AccessPointGroup
        fields = (
            "wireless_network",
            "access_point_group",
            "ssid",
            "mode",
            "authentication",
            "vlan",
            "prefix_count",
            "enabled",
            "hidden",
            "secrets_group",
            "controller",
        )
        default_columns = (
            "wireless_network",
            "access_point_group",
            "vlan",
            "ssid",
            "prefix_count",
            "mode",
            "authentication",
            "controller",
        )


class ControllerAccessPointGroupWirelessNetworkAssignmentTable(AccessPointGroupWirelessNetworkAssignmentTable):
    class Meta(AccessPointGroupWirelessNetworkAssignmentTable.Meta):
        default_columns = (
            "wireless_network",
            "access_point_group",
            "vlan",
            "ssid",
            "prefix_count",
            "mode",
            "authentication",
        )


class AccessPointGroupRadioProfileAssignmentTable(BaseTable):
    access_point_group = tables.Column(linkify=True)
    radio_profile = tables.Column(linkify=True)
    frequency = tables.Column(accessor="radio_profile.frequency")
    channel_width = tables.Column(accessor="radio_profile.channel_width")
    allowed_channel_list = tables.Column(accessor="radio_profile.allowed_channel_list")
    tx_power_min = tables.Column(accessor="radio_profile.tx_power_min")
    tx_power_max = tables.Column(accessor="radio_profile.tx_power_max")
    rx_power_min = tables.Column(accessor="radio_profile.rx_power_min")
    regulatory_domain = tables.Column(accessor="radio_profile.regulatory_domain")

    class Meta(BaseTable.Meta):
        model = AccessPointGroup
        fields = (
            "radio_profile",
            "access_point_group",
            "frequency",
            "channel_width",
            "allowed_channel_list",
            "tx_power_min",
            "tx_power_max",
            "rx_power_min",
            "regulatory_domain",
        )
        default_columns = (
            "radio_profile",
            "access_point_group",
            "frequency",
            "channel_width",
            "allowed_channel_list",
            "tx_power_min",
            "tx_power_max",
            "rx_power_min",
            "regulatory_domain",
        )

    def render_channel_width(self, value):
        return ", ".join(f"{v}MHz" for v in value)

    def render_allowed_channel_list(self, value):
        return ", ".join(f"{v}" for v in value)
