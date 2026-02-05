"""Menu items."""

from nautobot.core.apps import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab
from nautobot.core.ui.choices import NavigationIconChoices, NavigationWeightChoices

menu_items = (
    NavMenuTab(
        name="Load Balancers",
        icon=NavigationIconChoices.LOAD_BALANCERS,
        weight=NavigationWeightChoices.LOAD_BALANCERS,
        groups=(
            NavMenuGroup(
                name="Load Balancers",
                weight=100,
                items=(
                    NavMenuItem(
                        link="load_balancers:virtualserver_list",
                        name="Virtual Servers",
                        weight=100,
                        permissions=["load_balancers.view_virtualserver"],
                        buttons=(
                            NavMenuAddButton(
                                link="load_balancers:virtualserver_add",
                                permissions=["load_balancers.add_virtualserver"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="load_balancers:loadbalancerpool_list",
                        name="Load Balancer Pools",
                        weight=200,
                        permissions=["load_balancers.view_loadbalancerpool"],
                        buttons=(
                            NavMenuAddButton(
                                link="load_balancers:loadbalancerpool_add",
                                permissions=["load_balancers.add_loadbalancerpool"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="load_balancers:loadbalancerpoolmember_list",
                        name="Load Balancer Pool Members",
                        weight=300,
                        permissions=["load_balancers.view_loadbalancerpoolmember"],
                        buttons=(
                            NavMenuAddButton(
                                link="load_balancers:loadbalancerpoolmember_add",
                                permissions=["load_balancers.add_loadbalancerpoolmember"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="load_balancers:healthcheckmonitor_list",
                        name="Health Check Monitors",
                        weight=400,
                        permissions=["load_balancers.view_healthcheckmonitor"],
                        buttons=(
                            NavMenuAddButton(
                                link="load_balancers:healthcheckmonitor_add",
                                permissions=["load_balancers.add_healthcheckmonitor"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="load_balancers:certificateprofile_list",
                        name="Certificate Profiles",
                        weight=500,
                        permissions=["load_balancers.view_certificateprofile"],
                        buttons=(
                            NavMenuAddButton(
                                link="load_balancers:certificateprofile_add",
                                permissions=["load_balancers.add_certificateprofile"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
