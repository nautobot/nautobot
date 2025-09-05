import django_tables2 as tables

from nautobot.core.tables import (
    BaseTable,
    ChoiceFieldColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.dcim.models import PowerFeed, PowerPanel
from nautobot.extras.tables import StatusTableMixin

from .devices import CableTerminationTable

__all__ = (
    "PowerFeedTable",
    "PowerPanelTable",
)


#
# Power panels
#


class PowerPanelTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    location = tables.Column(linkify=True)
    panel_type = tables.Column()
    power_path = tables.Column()
    breaker_position_count = tables.Column(verbose_name="Total Breaker Positions")
    power_feed_count = LinkedCountColumn(
        viewname="dcim:powerfeed_list",
        url_params={"power_panel": "pk"},
        verbose_name="Feeds",
    )
    tags = TagColumn(url_name="dcim:powerpanel_list")

    class Meta(BaseTable.Meta):
        model = PowerPanel
        fields = (
            "pk",
            "name",
            "location",
            "rack_group",
            "panel_type",
            "power_path",
            "breaker_position_count",
            "power_feed_count",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "location",
            "rack_group",
            "panel_type",
            "power_path",
            "power_feed_count",
        )


#
# Power feeds
#


# We're not using PathEndpointTable for PowerFeed because power connections
# cannot traverse pass-through ports.
class PowerFeedTable(StatusTableMixin, CableTerminationTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    power_panel = tables.Column(linkify=True)
    destination_panel = tables.Column(linkify=True)
    rack = tables.Column(linkify=True)
    type = ChoiceFieldColumn()
    power_path = tables.Column()
    occupied_positions = tables.Column(accessor="occupied_positions", verbose_name="Position")
    phase_designation = tables.Column(accessor="phase_designation", verbose_name="Phase Designation")
    max_utilization = tables.TemplateColumn(template_code="{{ value }}%")
    available_power = tables.Column(verbose_name="Available power (VA)")
    tags = TagColumn(url_name="dcim:powerfeed_list")

    class Meta(BaseTable.Meta):
        model = PowerFeed
        fields = (
            "pk",
            "name",
            "power_panel",
            "destination_panel",
            "rack",
            "status",
            "type",
            "power_path",
            "supply",
            "voltage",
            "amperage",
            "phase",
            "max_utilization",
            "cable",
            "cable_peer",
            "connection",
            "available_power",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "power_panel",
            "rack",
            "status",
            "type",
            "power_path",
            "supply",
            "voltage",
            "amperage",
            "phase",
            "cable",
            "cable_peer",
        )
