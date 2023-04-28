from nautobot.core.apps import NavMenuGroup, NavMenuItem, NavMenuTab


menu_items = (
    NavMenuTab(
        name="Inventory",
        groups=(
            NavMenuGroup(
                name="Devices",
                weight=100,
                items=(
                    NavMenuItem(
                        name="Dynamic Groups",
                        weight=900,
                        link="extras:dynamicgroup_list",
                        permissions=["extras.view_dynamicgroup"],
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Networks",
        groups=(
            NavMenuGroup(
                name="Config Contexts",
                weight=500,
                items=(
                    NavMenuItem(
                        name="Config Contexts",
                        weight=100,
                        link="extras:configcontext_list",
                        permissions=["extras.view_configcontext"],
                    ),
                    NavMenuItem(
                        name="Config Context Schemas",
                        weight=100,
                        link="extras:configcontextschema_list",
                        permissions=["extras.view_configcontextschema"],
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Automation",
        groups=(
            NavMenuGroup(
                name="Jobs",
                weight=100,
                items=(
                    NavMenuItem(
                        link="extras:job_list",
                        name="Jobs",
                        weight=100,
                        permissions=[
                            "extras.view_job",
                        ],
                    ),
                    NavMenuItem(
                        link="extras:scheduledjob_approval_queue_list",
                        name="Job Approval Queue",
                        weight=200,
                        permissions=[
                            "extras.view_job",
                        ],
                    ),
                    NavMenuItem(
                        link="extras:scheduledjob_list",
                        name="Scheduled Jobs",
                        weight=300,
                        permissions=[
                            "extras.view_job",
                            "extras.view_scheduledjob",
                        ],
                    ),
                    NavMenuItem(
                        link="extras:jobresult_list",
                        name="Job Results",
                        weight=400,
                        permissions=[
                            "extras.view_jobresult",
                        ],
                    ),
                    NavMenuItem(
                        link="extras:jobhook_list",
                        name="Job Hooks",
                        weight=500,
                        permissions=[
                            "extras.view_jobhook",
                        ],
                    ),
                    NavMenuItem(
                        link="extras:jobbutton_list",
                        name="Job Buttons",
                        weight=600,
                        permissions=[
                            "extras.view_jobbutton",
                        ],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Extensibility",
                weight=9999,  # always last
                items=(
                    NavMenuItem(
                        link="extras:webhook_list",
                        name="Webhooks",
                        weight=100,
                        permissions=["extras.view_webhook"],
                    ),
                    NavMenuItem(
                        name="GraphQL Queries",
                        weight=200,
                        link="extras:graphqlquery_list",
                        permissions=["extras.view_graphqlquery"],
                    ),
                    NavMenuItem(
                        name="Export Templates",
                        weight=300,
                        link="extras:exporttemplate_list",
                        permissions=["extras.view_exporttemplate"],
                    ),
                ),
            ),
        ),
    ),
    NavMenuTab(
        name="Platform",
        groups=(
            NavMenuGroup(
                name="Platform",
                weight=100,
                items=(
                    NavMenuItem(
                        name="Installed Apps",
                        weight=100,
                        link="plugins:plugins_list",
                        permissions=["is_staff"],
                    ),
                    NavMenuItem(
                        name="Git Repositories",
                        weight=200,
                        link="extras:gitrepository_list",
                        permissions=["extras.view_gitrepository"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Governance",
                weight=200,
                items=(
                    NavMenuItem(
                        name="Change Log",
                        weight=100,
                        link="extras:objectchange_list",
                        permissions=["extras.view_objectchange"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Reference Data",
                weight=300,
                items=(
                    NavMenuItem(
                        name="Tags",
                        weight=100,
                        link="extras:tag_list",
                        permissions=["extras.view_tag"],
                    ),
                    NavMenuItem(
                        name="Statuses",
                        weight=200,
                        link="extras:status_list",
                        permissions=["extras.view_status"],
                    ),
                    NavMenuItem(
                        name="Roles",
                        weight=300,
                        link="extras:role_list",
                        permissions=["extras.view_role"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Data Management",
                weight=400,
                items=(
                    NavMenuItem(
                        name="Relationships",
                        weight=100,
                        link="extras:relationship_list",
                        permissions=["extras.view_relationship"],
                    ),
                    NavMenuItem(
                        name="Computed Fields",
                        weight=200,
                        link="extras:computedfield_list",
                        permissions=["extras.view_computedfield"],
                    ),
                    NavMenuItem(
                        name="Custom Fields",
                        weight=300,
                        link="extras:customfield_list",
                        permissions=["extras.view_customfield"],
                    ),
                    NavMenuItem(
                        name="Custom Links",
                        weight=400,
                        link="extras:customlink_list",
                        permissions=["extras.view_customlink"],
                    ),
                ),
            ),
            NavMenuGroup(
                name="Secrets",
                weight=500,
                items=(
                    NavMenuItem(
                        name="Secrets",
                        weight=100,
                        link="extras:secret_list",
                        permissions=["extras.view_secret"],
                    ),
                    NavMenuItem(
                        name="Secret Groups",
                        weight=200,
                        link="extras:secretsgroup_list",
                        permissions=["extras.view_secretsgroup"],
                    ),
                ),
            ),
        ),
    ),
)
