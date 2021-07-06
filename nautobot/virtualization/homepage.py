from nautobot.core.apps import HomePageColumn, HomePageItem, HomePagePanel
from nautobot.virtualization.models import Cluster, VirtualMachine

layout = (
    HomePageColumn(
        name="second",
        weight=200,
        panels=(
            HomePagePanel(
                name="Virtualization",
                weight=300,
                items=(
                    HomePageItem(
                        name="Clusters",
                        link="virtualization:cluster_list",
                        model=Cluster,
                        description="Clusters of physical hosts in which VMs reside",
                        permissions=["virtualization.view_cluster"],
                        weight=100,
                    ),
                    HomePageItem(
                        name="Virtual Machines",
                        link="virtualization:virtualmachine_list",
                        model=VirtualMachine,
                        description="Virtual compute instances running inside clusters",
                        permissions=["virtualization.view_virtualmachine"],
                        weight=200,
                    ),
                ),
            ),
        ),
    ),
)
