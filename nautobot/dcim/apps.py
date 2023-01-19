from nautobot.core.apps import NautobotConfig


class DCIMConfig(NautobotConfig):
    name = "nautobot.dcim"
    verbose_name = "DCIM"

    def ready(self):
        super().ready()
        import nautobot.dcim.signals  # noqa: F401

    def get_search_types(self):
        from nautobot.core.utils.utils import count_related
        from nautobot.dcim.filters import (
            CableFilterSet,
            DeviceFilterSet,
            DeviceTypeFilterSet,
            PowerFeedFilterSet,
            RackFilterSet,
            RackGroupFilterSet,
            SiteFilterSet,
            VirtualChassisFilterSet,
        )
        from nautobot.dcim.models import (
            Cable,
            Device,
            DeviceType,
            PowerFeed,
            Rack,
            RackGroup,
            Site,
            VirtualChassis,
        )
        from nautobot.dcim.tables import (
            CableTable,
            DeviceTable,
            DeviceTypeTable,
            PowerFeedTable,
            RackTable,
            RackGroupTable,
            SiteTable,
            VirtualChassisTable,
        )

        return {
            "site": {
                "queryset": Site.objects.select_related("region", "tenant"),
                "filterset": SiteFilterSet,
                "table": SiteTable,
                "url": "dcim:site_list",
            },
            "rack": {
                "queryset": Rack.objects.select_related("site", "group", "tenant", "role"),
                "filterset": RackFilterSet,
                "table": RackTable,
                "url": "dcim:rack_list",
            },
            "rackgroup": {
                "queryset": RackGroup.objects.annotate(rack_count=count_related(Rack, "group")).select_related("site"),
                "filterset": RackGroupFilterSet,
                "table": RackGroupTable,
                "url": "dcim:rackgroup_list",
            },
            "devicetype": {
                "queryset": DeviceType.objects.select_related("manufacturer").annotate(
                    instance_count=count_related(Device, "device_type")
                ),
                "filterset": DeviceTypeFilterSet,
                "table": DeviceTypeTable,
                "url": "dcim:devicetype_list",
            },
            "device": {
                "queryset": Device.objects.select_related(
                    "device_type__manufacturer",
                    "role",
                    "tenant",
                    "site",
                    "rack",
                    "primary_ip4",
                    "primary_ip6",
                ),
                "filterset": DeviceFilterSet,
                "table": DeviceTable,
                "url": "dcim:device_list",
            },
            "virtualchassis": {
                "queryset": VirtualChassis.objects.select_related("master").annotate(
                    member_count=count_related(Device, "virtual_chassis")
                ),
                "filterset": VirtualChassisFilterSet,
                "table": VirtualChassisTable,
                "url": "dcim:virtualchassis_list",
            },
            "cable": {
                "queryset": Cable.objects.all(),
                "filterset": CableFilterSet,
                "table": CableTable,
                "url": "dcim:cable_list",
            },
            "powerfeed": {
                "queryset": PowerFeed.objects.all(),
                "filterset": PowerFeedFilterSet,
                "table": PowerFeedTable,
                "url": "dcim:powerfeed_list",
            },
        }
