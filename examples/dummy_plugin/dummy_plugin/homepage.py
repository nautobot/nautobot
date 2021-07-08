from nautobot.core.apps import HomePageColumn, HomePageItem, HomePagePanel


layout = (
    HomePageColumn(
        name="first",
        weight=100,
        panels=(
            HomePagePanel(
                name="Organization",
                items=(
                    HomePageItem(
                        name="Dummy Models",
                        weight=150,
                        link="plugins:dummy_plugin:dummymodel_list",
                        description="List dummy plugin models.",
                        permissions=["dummy_plugin.view_dummymodel"],
                    ),
                ),
            ),
        ),
    ),
    HomePageColumn(
        name="third",
        weight=300,
        panels=(
            HomePagePanel(
                name="Dummy Plugin",
                weight=300,
                items=(
                    HomePageItem(
                        name="Dummy Models",
                        link="plugins:dummy_plugin:dummymodel_list",
                        description="List dummy plugin models.",
                        permissions=["dummy_plugin.view_dummymodel"],
                        weight=100,
                    ),
                ),
            ),
        ),
    ),
)
