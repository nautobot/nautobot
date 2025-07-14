from nautobot.core.apps import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)

menu_items = (
    NavMenuTab(
        name="Wireless",
        weight=250,
        groups=(
            NavMenuGroup(
                name="Wireless",
                weight=100,
                items=(
                    NavMenuItem(
                        link="wireless:wirelessnetwork_list",
                        name="Wireless Networks",
                        weight=100,
                        permissions=[
                            "wireless.view_wirelessnetwork",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="wireless:wirelessnetwork_add",
                                permissions=[
                                    "wireless.add_wirelessnetwork",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:controller_list",
                        name="Wireless Controllers",
                        query_params={"capabilities": "wireless"},
                        weight=200,
                        permissions=[
                            "dcim.view_controller",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="dcim:controller_add",
                                query_params={"capabilities": "wireless"},
                                permissions=[
                                    "dcim.add_controller",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="dcim:controllermanageddevicegroup_list",
                        name="Device Groups",
                        query_params={"capabilities": "wireless"},
                        weight=300,
                        permissions=[
                            "dcim.view_controllermanageddevicegroup",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="dcim:controllermanageddevicegroup_add",
                                query_params={"capabilities": "wireless"},
                                permissions=[
                                    "dcim.add_controllermanageddevicegroup",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="wireless:radioprofile_list",
                        name="Radio Profiles",
                        weight=500,
                        permissions=[
                            "wireless.view_radioprofile",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="wireless:radioprofile_add",
                                permissions=[
                                    "wireless.add_radioprofile",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="wireless:supporteddatarate_list",
                        name="Supported Data Rates",
                        weight=600,
                        permissions=[
                            "wireless.view_supporteddatarate",
                        ],
                        buttons=(
                            NavMenuAddButton(
                                link="wireless:supporteddatarate_add",
                                permissions=[
                                    "wireless.add_supporteddatarate",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
