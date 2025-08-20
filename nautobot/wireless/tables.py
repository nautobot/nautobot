import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)

from .models import (
    ControllerManagedDeviceGroupRadioProfileAssignment,
    ControllerManagedDeviceGroupWirelessNetworkAssignment,
    RadioProfile,
    SupportedDataRate,
    WirelessNetwork,
)


class RadioProfileTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    tags = TagColumn(url_name="wireless:radioprofile_list")
    actions = ButtonsColumn(RadioProfile)
    supported_data_rates_count = LinkedCountColumn(
        viewname="wireless:supporteddatarate_list",
        url_params={"radio_profiles": "pk"},
        verbose_name="Supported Data Rates",
        reverse_lookup="radio_profiles",
    )

    class Meta(BaseTable.Meta):
        model = RadioProfile
        fields = (
            "pk",
            "name",
            "frequency",
            "channel_width",
            "allowed_channel_list",
            "supported_data_rates_count",
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
            "regulatory_domain",
            "allowed_channel_list",
            "supported_data_rates_count",
            "actions",
        )

    def render_channel_width(self, value):
        return ", ".join(f"{v}MHz" for v in value)

    def render_allowed_channel_list(self, value):
        return ", ".join(f"{v}" for v in value)

    def render_tx_power_min(self, value):
        return f"{value} dBm"

    def render_tx_power_max(self, value):
        return f"{value} dBm"

    def render_rx_power_min(self, value):
        return f"{value} dBm"


class SupportedDataRateTable(BaseTable):
    pk = ToggleColumn()
    rate = tables.Column(linkify=True)
    standard = tables.Column()
    mcs_index = tables.Column(verbose_name="MCS Index")
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
    enabled = BooleanColumn()
    hidden = BooleanColumn()

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


class BaseControllerManagedDeviceGroupWirelessNetworkAssignmentTable(BaseTable):
    controller_managed_device_group = tables.Column(linkify=True, verbose_name="Device Group")
    wireless_network = tables.Column(linkify=True, verbose_name="Wireless Network")
    vlan = tables.Column(linkify=True)
    ssid = tables.Column(accessor="wireless_network.ssid")
    mode = tables.Column(accessor="wireless_network.mode")
    authentication = tables.Column(accessor="wireless_network.authentication")
    enabled = BooleanColumn(accessor="wireless_network.enabled")
    hidden = BooleanColumn(accessor="wireless_network.hidden")
    secrets_group = tables.Column(accessor="wireless_network.secrets_group", linkify=True, verbose_name="Secrets Group")
    controller = tables.Column(accessor="controller_managed_device_group.controller", linkify=True)
    prefix_count = LinkedCountColumn(
        viewname="ipam:prefix_list",
        url_params={"vlan_id": "vlan_id"},
        verbose_name="Prefixes",
        reverse_lookup="vlan__controller_managed_device_group_wireless_network_assignments",
    )

    class Meta(BaseTable.Meta):
        model = ControllerManagedDeviceGroupWirelessNetworkAssignment
        fields = (
            "wireless_network",
            "controller_managed_device_group",
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
            "controller_managed_device_group",
            "vlan",
            "ssid",
            "prefix_count",
            "mode",
            "authentication",
            "controller",
        )


class ControllerManagedDeviceGroupWirelessNetworkAssignmentTable(
    BaseControllerManagedDeviceGroupWirelessNetworkAssignmentTable
):
    list_url = "dcim:controllermanageddevicegroup_list"

    class Meta(BaseControllerManagedDeviceGroupWirelessNetworkAssignmentTable.Meta):
        pass


class DeviceGroupWirelessNetworkTable(BaseControllerManagedDeviceGroupWirelessNetworkAssignmentTable):
    list_url = "wireless:wirelessnetwork_list"

    class Meta(BaseControllerManagedDeviceGroupWirelessNetworkAssignmentTable.Meta):
        pass


class ControllerControllerManagedDeviceGroupWirelessNetworkAssignmentTable(
    BaseControllerManagedDeviceGroupWirelessNetworkAssignmentTable
):
    class Meta(ControllerManagedDeviceGroupWirelessNetworkAssignmentTable.Meta):
        default_columns = (
            "wireless_network",
            "controller_managed_device_group",
            "vlan",
            "ssid",
            "prefix_count",
            "mode",
            "authentication",
        )


class ControllerManagedDeviceGroupRadioProfileAssignmentTable(BaseTable):
    controller_managed_device_group = tables.Column(linkify=True, verbose_name="Device Group")
    radio_profile = tables.Column(linkify=True, verbose_name="Radio Profile")
    frequency = tables.Column(accessor="radio_profile.frequency")
    channel_width = tables.Column(accessor="radio_profile.channel_width", verbose_name="Channel Width")
    allowed_channel_list = tables.Column(accessor="radio_profile.allowed_channel_list", verbose_name="Allowed Channels")
    tx_power_min = tables.Column(accessor="radio_profile.tx_power_min")
    tx_power_max = tables.Column(accessor="radio_profile.tx_power_max")
    rx_power_min = tables.Column(accessor="radio_profile.rx_power_min")
    regulatory_domain = tables.Column(accessor="radio_profile.regulatory_domain", verbose_name="Regulatory Domain")

    class Meta(BaseTable.Meta):
        model = ControllerManagedDeviceGroupRadioProfileAssignment
        fields = (
            "radio_profile",
            "controller_managed_device_group",
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
            "controller_managed_device_group",
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

    def render_tx_power_min(self, value):
        return f"{value} dBm"

    def render_tx_power_max(self, value):
        return f"{value} dBm"

    def render_rx_power_min(self, value):
        return f"{value} dBm"
