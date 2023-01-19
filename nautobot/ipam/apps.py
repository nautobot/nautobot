from nautobot.core.apps import NautobotConfig


class IPAMConfig(NautobotConfig):
    name = "nautobot.ipam"
    verbose_name = "IPAM"

    def ready(self):
        super().ready()

        from graphene_django.converter import convert_django_field, convert_field_to_string
        from nautobot.ipam.fields import VarbinaryIPField

        # Register VarbinaryIPField to be converted to a string type
        convert_django_field.register(VarbinaryIPField)(convert_field_to_string)

    def get_search_types(self):
        from nautobot.ipam.filters import (
            AggregateFilterSet,
            IPAddressFilterSet,
            PrefixFilterSet,
            VLANFilterSet,
            VRFFilterSet,
        )
        from nautobot.ipam.models import Aggregate, IPAddress, Prefix, VLAN, VRF
        from nautobot.ipam.tables import (
            AggregateTable,
            IPAddressTable,
            PrefixTable,
            VLANTable,
            VRFTable,
        )

        return {
            "vrf": {
                "queryset": VRF.objects.select_related("tenant"),
                "filterset": VRFFilterSet,
                "table": VRFTable,
                "url": "ipam:vrf_list",
            },
            "aggregate": {
                "queryset": Aggregate.objects.select_related("rir"),
                "filterset": AggregateFilterSet,
                "table": AggregateTable,
                "url": "ipam:aggregate_list",
            },
            "prefix": {
                "queryset": Prefix.objects.select_related("site", "vrf__tenant", "tenant", "vlan", "role"),
                "filterset": PrefixFilterSet,
                "table": PrefixTable,
                "url": "ipam:prefix_list",
            },
            "ipaddress": {
                "queryset": IPAddress.objects.select_related("vrf__tenant", "tenant"),
                "filterset": IPAddressFilterSet,
                "table": IPAddressTable,
                "url": "ipam:ipaddress_list",
            },
            "vlan": {
                "queryset": VLAN.objects.select_related("site", "group", "tenant", "role"),
                "filterset": VLANFilterSet,
                "table": VLANTable,
                "url": "ipam:vlan_list",
            },
        }
