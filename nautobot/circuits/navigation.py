from nautobot.core.apps import NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Inventory",
        weight=100,
        groups=(
            NavMenuGroup(
                name="Circuits",
                weight=400,
                items=(
                    NavMenuItem(
                        link="circuits:circuit_list",
                        name="Circuits",
                        weight=100,
                        permissions=[
                            "circuits.view_circuit",
                        ],
                    ),
                    NavMenuItem(
                        link="circuits:circuittype_list",
                        name="Circuit Types",
                        weight=200,
                        permissions=[
                            "circuits.view_circuittype",
                        ],
                    ),
                    NavMenuItem(
                        link="circuits:provider_list",
                        name="Providers",
                        weight=300,
                        permissions=[
                            "circuits.view_provider",
                        ],
                    ),
                    NavMenuItem(
                        link="circuits:providernetwork_list",
                        name="Provider Networks",
                        weight=400,
                        permissions=[
                            "circuits.view_providernetwork",
                        ],
                    ),
                ),
            ),
        ),
    ),
)
