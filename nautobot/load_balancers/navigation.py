"""Menu items."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Load Balancers",
        weight=450,
        groups=(
            NavMenuGroup(
                name="Load Balancers",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_load_balancer_models:virtualserver_list",
                        name="Virtual Servers",
                        weight=100,
                        permissions=["nautobot_load_balancer_models.view_virtualserver"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_load_balancer_models:virtualserver_add",
                                permissions=["nautobot_load_balancer_models.add_virtualserver"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_load_balancer_models:loadbalancerpool_list",
                        name="Pools",
                        weight=200,
                        permissions=["nautobot_load_balancer_models.view_loadbalancerpool"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_load_balancer_models:loadbalancerpool_add",
                                permissions=["nautobot_load_balancer_models.add_loadbalancerpool"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_load_balancer_models:loadbalancerpoolmember_list",
                        name="Pool Members",
                        weight=300,
                        permissions=["nautobot_load_balancer_models.view_loadbalancerpoolmember"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_load_balancer_models:loadbalancerpoolmember_add",
                                permissions=["nautobot_load_balancer_models.add_loadbalancerpoolmember"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_load_balancer_models:healthcheckmonitor_list",
                        name="Health Check Monitors",
                        weight=400,
                        permissions=["nautobot_load_balancer_models.view_healthcheckmonitor"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_load_balancer_models:healthcheckmonitor_add",
                                permissions=["nautobot_load_balancer_models.add_healthcheckmonitor"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_load_balancer_models:certificateprofile_list",
                        name="Certificate Profiles",
                        weight=500,
                        permissions=["nautobot_load_balancer_models.view_certificateprofile"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_load_balancer_models:certificateprofile_add",
                                permissions=["nautobot_load_balancer_models.add_certificateprofile"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
