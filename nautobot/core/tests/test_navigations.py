from unittest.mock import patch

from django.test import tag, TestCase
from django.urls import resolve

from nautobot.core.apps import NAV_CONTEXT_NAMES, NavContext, NavGrouping, NavItem, register_new_ui_menu_items
from nautobot.core.choices import ButtonActionColorChoices, ButtonActionIconChoices
from nautobot.core.templatetags.helpers import bettertitle
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.extras.registry import registry


@tag("unit")
class NavMenuTestCase(TestCase):
    """Verify correct construction of the nav menu."""

    def test_menu_item_attributes(self):
        """Verify that menu items and buttons have the correct text and expected permissions."""
        for tab in registry["nav_menu"]["tabs"]:
            for group in registry["nav_menu"]["tabs"][tab]["groups"]:
                for item_url, item_details in registry["nav_menu"]["tabs"][tab]["groups"][group]["items"].items():
                    with self.subTest(f"{tab} > {group} > {item_url}"):
                        view_func = resolve(item_url).func
                        try:
                            # NautobotUIViewSet
                            view_class = view_func.view_class
                        except AttributeError:
                            # ObjectListView
                            view_class = view_func.cls
                        try:
                            view_queryset = view_class.queryset
                            view_model = view_queryset.model

                            if item_details["name"] not in {
                                "Elevations",
                                "Interface Connections",
                                "Console Connections",
                                "Power Connections",
                                "Job Approval Queue",
                            }:
                                expected_name = bettertitle(view_model._meta.verbose_name_plural)
                                if expected_name == "VM Interfaces":
                                    expected_name = "Interfaces"
                                elif expected_name == "Object Changes":
                                    expected_name = "Change Log"
                                self.assertEqual(item_details["name"], expected_name)
                            if item_url == get_route_for_model(view_model, "list"):
                                # Not assertEqual as some menu items have additional permissions defined.
                                self.assertIn(get_permission_for_model(view_model, "view"), item_details["permissions"])
                        except AttributeError:
                            # Not a model view?
                            self.assertIn(item_details["name"], {"Installed Apps", "Interface Connections"})

                    for button, button_details in item_details["buttons"].items():
                        with self.subTest(f"{tab} > {group} > {item_url} > {button}"):
                            # Currently all core menu items should have just a single Add button
                            self.assertEqual(button, "Add")
                            self.assertEqual(
                                button_details["permissions"], {get_permission_for_model(view_model, "add")}
                            )
                            self.assertEqual(button_details["link"], get_route_for_model(view_model, "add"))
                            self.assertEqual(button_details["button_class"], ButtonActionColorChoices.ADD)
                            self.assertEqual(button_details["icon_class"], ButtonActionIconChoices.ADD)

    def test_permissions_rollup(self):
        menus = registry["nav_menu"]
        expected_perms = {}
        for tab_name, tab_details in menus["tabs"].items():
            expected_perms[tab_name] = set()
            for group_name, group_details in tab_details["groups"].items():
                expected_perms[f"{tab_name}:{group_name}"] = set()
                for item_details in group_details["items"].values():
                    item_perms = item_details["permissions"]
                    # If any item has no permissions restriction, then the group has no permissions restriction
                    if expected_perms[f"{tab_name}:{group_name}"] is None or not item_perms:
                        expected_perms[f"{tab_name}:{group_name}"] = None
                    else:
                        expected_perms[f"{tab_name}:{group_name}"] |= item_perms
                group_perms = group_details["permissions"]
                self.assertEqual(expected_perms[f"{tab_name}:{group_name}"], group_perms)
                # if any group has no permissions restriction, then the tab has no permissions restriction
                if expected_perms[tab_name] is None or not group_perms:
                    expected_perms[tab_name] = None
                else:
                    expected_perms[tab_name] |= group_perms
            self.assertEqual(expected_perms[tab_name], tab_details["permissions"])


class NewUINavTest(TestCase):
    @patch.dict(registry, values={"new_ui_nav_menu": {}}, clear=True)
    def test_build_new_ui_nav_menu(self):
        """Assert building and adding of new ui nav to registry

        Assert that:
        1. New UI nav is added to registry["new_ui_nav_menu"]
        2. registry["new_ui_nav_menu"] is sorted by weight
        """
        # Test App 1
        navigation_1 = (
            NavContext(
                name="Inventory",
                groups=(
                    NavGrouping(
                        name="App 1 Inventory Group 1",
                        items=(
                            NavItem(name="Menu 1", link="extras:relationshipassociation_list", weight="2000"),
                            NavItem(name="Menu 3", link="extras:relationshipassociation_list", weight="100"),
                        ),
                    ),
                    NavGrouping(
                        name="App 1 Inventory Group 2",
                        items=(
                            NavItem(name="Menu 1", link="extras:role_list", permissions=["extras.view_role"]),
                            NavItem(name="Menu 2", link="extras:tag_list"),
                        ),
                    ),
                ),
            ),
            NavContext(
                name="Security",
                groups=(
                    NavGrouping(
                        name="App 1 Security Group 1",
                        items=(
                            NavItem(name="Menu 1", link="dcim:location_list"),
                            NavItem(name="Menu 2", link="extras:relationshipassociation_list"),
                            NavItem(name="Menu 3", link="extras:tag_list"),
                        ),
                    ),
                ),
            ),
        )
        # Test App 2
        navigation_2 = (
            NavContext(
                name="Automation",
                groups=(
                    NavGrouping(
                        name="App 2 Inventory Group 1",
                        items=(
                            NavItem(name="Tags", link="extras:tag_list"),
                            NavItem(name="Location", link="dcim:location_list"),
                            NavItem(name="Roles", link="extras:role_list", permissions=["extras.view_role"]),
                        ),
                    ),
                ),
            ),
        )

        for navigation in (navigation_1, navigation_2):
            register_new_ui_menu_items(navigation)

        expected_registry = {
            "new_ui_nav_menu": {
                "Inventory": {
                    "weight": 1000,
                    "data": {
                        "App 1 Inventory Group 1": {
                            "weight": 1000,
                            "data": {
                                "Menu 3": {
                                    "name": "Menu 3",
                                    "weight": "100",
                                    "permissions": [],
                                    "data": "/extras/relationship-associations/",
                                },
                                "Menu 1": {
                                    "name": "Menu 1",
                                    "weight": "2000",
                                    "permissions": [],
                                    "data": "/extras/relationship-associations/",
                                },
                            },
                        },
                        "App 1 Inventory Group 2": {
                            "weight": 1000,
                            "data": {
                                "Menu 1": {
                                    "name": "Menu 1",
                                    "weight": 1000,
                                    "permissions": ["extras.view_role"],
                                    "data": "/extras/roles/",
                                },
                                "Menu 2": {
                                    "name": "Menu 2",
                                    "weight": 1000,
                                    "permissions": [],
                                    "data": "/extras/tags/",
                                },
                            },
                        },
                    },
                },
                "Security": {
                    "weight": 1000,
                    "data": {
                        "App 1 Security Group 1": {
                            "weight": 1000,
                            "data": {
                                "Menu 1": {
                                    "name": "Menu 1",
                                    "weight": 1000,
                                    "permissions": [],
                                    "data": "/dcim/locations/",
                                },
                                "Menu 2": {
                                    "name": "Menu 2",
                                    "weight": 1000,
                                    "permissions": [],
                                    "data": "/extras/relationship-associations/",
                                },
                                "Menu 3": {
                                    "name": "Menu 3",
                                    "weight": 1000,
                                    "permissions": [],
                                    "data": "/extras/tags/",
                                },
                            },
                        }
                    },
                },
                "Automation": {
                    "weight": 1000,
                    "data": {
                        "App 2 Inventory Group 1": {
                            "weight": 1000,
                            "data": {
                                "Tags": {"name": "Tags", "weight": 1000, "permissions": [], "data": "/extras/tags/"},
                                "Location": {
                                    "name": "Location",
                                    "weight": 1000,
                                    "permissions": [],
                                    "data": "/dcim/locations/",
                                },
                                "Roles": {
                                    "name": "Roles",
                                    "weight": 1000,
                                    "permissions": ["extras.view_role"],
                                    "data": "/extras/roles/",
                                },
                            },
                        }
                    },
                },
            }
        }
        self.assertEqual(registry, expected_registry)

    def test_validation_in_new_ui_navigation_classes(self):
        """Test Validation on each of the new ui navigation classes `NavItem`, `NavGrouping`, `NavContext`"""

        nav_item_1 = NavItem(name="Menu 1", link="extras:role_list", permissions=["extras.view_role"])
        nav_item_2 = NavItem(name="Menu 2", link="invalid_url")
        self.assertEqual(
            nav_item_1.initial_dict,
            {
                "name": nav_item_1.name,
                "weight": nav_item_1.weight,
                "permissions": nav_item_1.permissions,
                "data": nav_item_1.url(),
            },
        )
        self.assertEqual(
            nav_item_1.fixed_fields,
            (
                ("name", nav_item_1.name),
                ("permissions", nav_item_1.permissions),
            ),
        )
        self.assertEqual(
            nav_item_2.initial_dict,
            {
                "name": nav_item_2.name,
                "weight": nav_item_2.weight,
                "permissions": nav_item_2.permissions,
                "data": nav_item_2.url(),
            },
        )
        self.assertEqual(
            nav_item_2.fixed_fields,
            (
                ("name", nav_item_2.name),
                ("permissions", nav_item_2.permissions),
            ),
        )

        with self.assertRaises(TypeError) as err:
            NavGrouping(name="Test Group", items="Invalid Items")
        self.assertEqual(str(err.exception), "Items must be passed as a tuple or list.")

        with self.assertRaises(TypeError) as err:
            NavGrouping(name="Test Group", items=["Invalid Item"])
        self.assertEqual(
            str(err.exception), "All items defined in a NavGrouping must be an instance of NavItem or NavGrouping"
        )

        nav_grouping_1 = NavGrouping(name="Test Group", items=[nav_item_1], weight="200")
        nav_grouping_2 = NavGrouping(name="Test Group", items=[nav_item_2, nav_grouping_1], weight="200")
        self.assertEqual(nav_grouping_1.initial_dict, {"weight": nav_grouping_1.weight, "data": {}})
        self.assertEqual(nav_grouping_1.fixed_fields, ())
        self.assertEqual(nav_grouping_2.initial_dict, {"weight": nav_grouping_1.weight, "data": {}})
        self.assertEqual(nav_grouping_2.fixed_fields, ())

        with self.assertRaises(TypeError) as err:
            NavContext(name="Invalid Name", groups=[])
        self.assertEqual(
            str(err.exception), f"`Invalid Name` is an invalid context name, valid choices are: {NAV_CONTEXT_NAMES}"
        )

        with self.assertRaises(TypeError) as err:
            NavContext(name="Inventory", groups="Invalid Groups")
        self.assertEqual(str(err.exception), "Groups must be passed as a tuple or list.")

        with self.assertRaises(TypeError) as err:
            NavContext(name="Inventory", groups=[NavItem(name="Menu 1", link="extras:role_list")])
        self.assertEqual(str(err.exception), "All groups defined in a NavContext must be an instance of NavGrouping")

        nav_context = NavContext(name="Inventory", groups=[nav_grouping_1, nav_grouping_2], weight="200")
        self.assertEqual(nav_context.initial_dict, {"weight": nav_context.weight, "data": {}})
        self.assertEqual(nav_context.fixed_fields, ())
