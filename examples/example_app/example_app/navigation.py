from nautobot.apps.ui import (
    NavMenuAddButton,
    NavMenuButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)

menu_items = (
    NavMenuTab(
        name="Apps",
        groups=(
            NavMenuGroup(
                name="Example Nautobot App",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:example_app:examplemodel_list",
                        name="Example Models",
                        permissions=["example_app.view_examplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_app:examplemodel_add",
                                permissions=[
                                    "example_app.add_examplemodel",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:example_app:examplemodel_list",
                        name="Example Models filtered",
                        permissions=["example_app.view_examplemodel"],
                        query_params={"number": "100"},
                    ),
                    NavMenuItem(
                        link="plugins:example_app:anotherexamplemodel_list",
                        name="Another Example Models",
                        permissions=["example_app.view_anotherexamplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_app:anotherexamplemodel_add",
                                permissions=[
                                    "example_app.add_anotherexamplemodel",
                                ],
                            ),
                            NavMenuButton(
                                title="Run Example Job",
                                icon_class="mdi mdi-robot-industrial",
                                link="extras:job_run_by_class_path",
                                args=["example_app.jobs.ExampleEverythingJob"],
                                permissions=[
                                    "example_app.add_anotherexamplemodel",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Example Menu",
        weight=150,
        groups=(
            NavMenuGroup(
                name="Example Group 1",
                weight=100,
                items=(
                    NavMenuItem(
                        link="plugins:example_app:examplemodel_list",
                        name="Example Models",
                        permissions=["example_app.view_examplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_app:examplemodel_add",
                                permissions=[
                                    "example_app.add_examplemodel",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Circuits",
        groups=(
            NavMenuGroup(
                name="Example Circuit Group",
                weight=150,
                items=(
                    NavMenuItem(
                        link="plugins:example_app:examplemodel_list",
                        name="Example Models",
                        permissions=["example_app.view_examplemodel"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:example_app:examplemodel_add",
                                permissions=[
                                    "example_app.add_examplemodel",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
