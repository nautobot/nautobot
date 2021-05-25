from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Virtualization",
        weight=400,
        groups=(
            NavMenuGroup(
                name="Virtual Machines",
                weight=100,
                items=(
                    NavMenuItem(
                        link="virtualization:virtualmachine_list",
                        link_text="Virtual Machines",
                        permissions=[
                            "virtualization.view_virtualmachine",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="virtualization:virtualmachine_add",
                                title="Virtual Machines",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "virtualization.add_virtualmachine",
                                ],
                            ),
                            NavMenuButton(
                                link="virtualization:virtualmachine_import",
                                title="Virtual Machines",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "virtualization.add_virtualmachine",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="virtualization:vminterface_list",
                        link_text="Interfaces",
                        permissions=[
                            "virtualization.view_interface",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="virtualization:vminterface_import",
                                title="Interfaces",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "virtualization.add_vminterface",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Clusters",
                weight=200,
                items=(
                    NavMenuItem(
                        link="virtualization:cluster_list",
                        link_text="Clusters",
                        permissions=[
                            "virtualization.view_cluster",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="virtualization:cluster_add",
                                title="Clusters",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "virtualization.add_cluster",
                                ],
                            ),
                            NavMenuButton(
                                link="virtualization:cluster_import",
                                title="Clusters",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "virtualization.add_cluster",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="virtualization:clustertype_list",
                        link_text="Cluster Types",
                        permissions=[
                            "virtualization.view_clustertype",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="virtualization:clustertype_add",
                                title="Cluster Types",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "virtualization.add_clustertype",
                                ],
                            ),
                            NavMenuButton(
                                link="virtualization:clustertype_import",
                                title="Cluster Types",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "virtualization.add_clustertype",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="virtualization:clustergroup_list",
                        link_text="Cluster Groups",
                        permissions=[
                            "virtualization.view_clustergroup",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="virtualization:clustergroup_add",
                                title="Cluster Groups",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "virtualization.add_clustergroup",
                                ],
                            ),
                            NavMenuButton(
                                link="virtualization:clustergroup_import",
                                title="Cluster Groups",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "virtualization.add_clustergroup",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)