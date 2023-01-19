from nautobot.core.apps import NautobotConfig


class VirtualizationConfig(NautobotConfig):
    name = "nautobot.virtualization"

    def ready(self):
        super().ready()
        import nautobot.virtualization.signals  # noqa: F401

    def get_search_types(self):
        from nautobot.core.utils.utils import count_related
        from nautobot.dcim.models import Device
        from nautobot.virtualization.filters import ClusterFilterSet, VirtualMachineFilterSet
        from nautobot.virtualization.models import Cluster, VirtualMachine
        from nautobot.virtualization.tables import ClusterTable, VirtualMachineDetailTable

        return {
            "cluster": {
                "queryset": Cluster.objects.select_related("cluster_type", "cluster_group").annotate(
                    device_count=count_related(Device, "cluster"),
                    vm_count=count_related(VirtualMachine, "cluster"),
                ),
                "filterset": ClusterFilterSet,
                "table": ClusterTable,
                "url": "virtualization:cluster_list",
            },
            "virtualmachine": {
                "queryset": VirtualMachine.objects.select_related(
                    "cluster",
                    "tenant",
                    "platform",
                    "primary_ip4",
                    "primary_ip6",
                ),
                "filterset": VirtualMachineFilterSet,
                "table": VirtualMachineDetailTable,
                "url": "virtualization:virtualmachine_list",
            },
        }
