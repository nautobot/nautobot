from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Circuits",
        weight=500,
        groups=(
            NavMenuGroup(
                name="Circuits",
                weight=100,
                items=(
                    NavMenuItem(
                        link="circuits:circuit_list",
                        link_text="Circuits",
                        permissions=[
                            "circuits.view_circuit",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="circuits:circuit_add",
                                title="Circuits",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "circuits.add_circuit",
                                ],
                            ),
                            NavMenuButton(
                                link="circuits:circuit_import",
                                title="Circuits",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "circuits.add_circuit",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="circuits:circuittype_list",
                        link_text="Circuit Types",
                        permissions=[
                            "circuits.view_circuittypes",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="circuits:circuittype_add",
                                title="Circuit Types",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "circuits.add_circuittype",
                                ],
                            ),
                            NavMenuButton(
                                link="circuits:circuittype_import",
                                title="Circuit Types",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "circuits.add_circuittype",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Providers",
                weight=200,
                items=(
                    NavMenuItem(
                        link="circuits:provider_list",
                        link_text="Providers",
                        permissions=[
                            "circuits.view_providers",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="circuits:provider_add",
                                title="Providers",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "circuits.add_provider",
                                ],
                            ),
                            NavMenuButton(
                                link="circuits:provider_import",
                                title="Providers",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "circuits.add_provider",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
