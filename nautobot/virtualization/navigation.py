from nautobot.core.apps import NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Inventory",
        groups=(
            NavMenuGroup(
                name="Virtualization",
                weight=600,
                items=(
                    NavMenuItem(
                        name="Virtual Machines",
                        weight=100,
                        link="virtualization:virtualmachine_list",
                        permissions=["virtualization.view_virtualmachine"],
                    ),
                    NavMenuItem(
                        name="VM Interfaces",
                        weight=200,
                        link="virtualization:vminterface_list",
                        permissions=["virtualization.view_vminterface"],
                    ),
                    NavMenuItem(
                        name="Clusters",
                        weight=300,
                        link="virtualization:cluster_list",
                        permissions=["virtualization.view_cluster"],
                    ),
                    NavMenuItem(
                        name="Cluster Types",
                        weight=400,
                        link="virtualization:clustertype_list",
                        permissions=["virtualization.view_clustertype"],
                    ),
                    NavMenuItem(
                        name="Cluster Groups",
                        weight=500,
                        link="virtualization:clustergroup_list",
                        permissions=["virtualization.view_clustergroup"],
                    ),
                ),
            ),
        ),
    ),
)
