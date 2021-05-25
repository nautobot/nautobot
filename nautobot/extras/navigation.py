from nautobot.extras.nautobot_app import NavMenuButton, NavMenuItem, NavMenuTab, NavMenuGroup
from nautobot.utilities.choices import ButtonColorChoices


menu_tabs = (
    NavMenuTab(
        name="Organization",
        weight=100,
        groups=(
            NavMenuGroup(
                name="Tags",
                weight=400,
                items=(
                    NavMenuItem(
                        link="extras:tag_list",
                        link_text="Tags",
                        permissions=[
                            "extras.view_tags",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:tag_add",
                                title="Tags",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_tag",
                                ],
                            ),
                            NavMenuButton(
                                link="extras:tag_add",
                                title="Tags",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "extras.add_tag",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Statuses",
                weight=500,
                items=(
                    NavMenuItem(
                        link="extras:status_list",
                        link_text="Statuses",
                        permissions=[
                            "extras.view_status",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:status_add",
                                title="Statuses",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_status",
                                ],
                            ),
                            NavMenuButton(
                                link="extras:status_import",
                                title="Statuses",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "extras.add_status",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Extensibility",
        weight=700,
        groups=(
            NavMenuGroup(
                name="Logging",
                weight=100,
                items=(
                    NavMenuItem(
                        link="extras:objectchange_list",
                        link_text="Change Log",
                        permissions=[
                            "extras.view_objectchange",
                        ],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="extras:jobresult_list",
                        link_text="Job Results",
                        permissions=[
                            "extras.view_jobresult",
                        ],
                        buttons=(),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Data Sources",
                weight=200,
                items=(
                    NavMenuItem(
                        link="extras:gitrepository_list",
                        link_text="Git Repositories",
                        permissions=[
                            "extras.view_gitrepository",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:gitrepository_add",
                                title="Git Repositories",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_gitrepository",
                                ],
                            ),
                            NavMenuButton(
                                link="extras:gitrepository_import",
                                title="Git Repositories",
                                icon_class="mdi mdi-database-import-outline",
                                color=ButtonColorChoices.BLUE,
                                permissions=[
                                    "extras.add_gitrepository",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Data Management",
                weight=300,
                items=(
                    NavMenuItem(
                        link="extras:relationship_list",
                        link_text="Relationships",
                        permissions=[
                            "extras.view_relationship",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:relationship_add",
                                title="Relationships",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_relationship",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Automation",
                weight=400,
                items=(
                    NavMenuItem(
                        link="extras:configcontext_list",
                        link_text="Config Context",
                        permissions=[
                            "extras.view_configcontext",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:configcontext_add",
                                title="Config Context",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_configcontext",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="extras:exporttemplate_list",
                        link_text="Export Templates",
                        permissions=[
                            "extras.view_exporttemplate",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:exporttemplate_add",
                                title="Export Templates",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_exporttemplate",
                                ],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="extras:job_list",
                        link_text="Jobs",
                        permissions=[
                            "extras.view_job",
                        ],
                        buttons=(),
                    ),
                    NavMenuItem(
                        link="extras:webhook_list",
                        link_text="Webhooks",
                        permissions=[
                            "extras.view_webhook",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:webhook_add",
                                title="Webhooks",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_webhook",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Miscellaneous",
                weight=500,
                items=(
                    NavMenuItem(
                        link="extras:customlink_list",
                        link_text="Custom Links",
                        permissions=[
                            "extras.view_customlink",
                        ],
                        buttons=(
                            NavMenuButton(
                                link="extras:customlink_add",
                                title="Custom Links",
                                icon_class="mdi mdi-plus-thick",
                                color=ButtonColorChoices.GREEN,
                                permissions=[
                                    "extras.add_customlink",
                                ],
                            ),
                        ),
                    ),
                ),
            ),
        )
    )
)
