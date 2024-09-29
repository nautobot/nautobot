import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ButtonsColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)

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
    description = tables.Column()
    tags = TagColumn(url_name="wireless:radioprofile_list")
    actions = ButtonsColumn(RadioProfile)

    class Meta(BaseTable.Meta):
        model = RadioProfile
        fields = (
            "pk",
            "name",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "actions",
        )


class SupportedDataRateTable(BaseTable):
    pk = ToggleColumn()
    rate = tables.Column(linkify=True)
    standard = tables.Column()
    tags = TagColumn(url_name="wireless:supporteddatarate_list")
    actions = ButtonsColumn(SupportedDataRate)

    class Meta(BaseTable.Meta):
        model = SupportedDataRate
        fields = (
            "pk",
            "rate",
            "standard",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "rate",
            "standard",
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
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "actions",
        )
