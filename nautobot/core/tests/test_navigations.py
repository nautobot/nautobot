from django.test import TestCase
from unittest.mock import patch

from nautobot.core.apps import NAV_CONTEXT_NAMES, NavContext, NavGrouping, NavItem, register_new_ui_menu_items


# TODO(timizuo): Here might not be the best place to add this test class
class NewUINavTest(TestCase):
    @patch("nautobot.core.apps.registry", {"new_ui_nav_menu": {}})
    def test_build_new_ui_nav_menu(self):
        """Assert building and adding of new ui nav to registry

        Assert that:
        1. New UI nav is added to registry["new_ui_nav_menu"]
        2. registry["new_ui_nav_menu"] is sorted by weight
        """
        from nautobot.core.apps import registry  # Import here cause of the mock patch

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
                            NavItem(name="Menu 1", link="extras:role_list", permissions=["extras.view_status"]),
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
                            NavItem(name="Roles", link="extras:role_list", permissions=["extras.view_status"]),
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
                                    "permissions": ["extras.view_status"],
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
                                    "permissions": ["extras.view_status"],
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

        nav_item_1 = NavItem(name="Menu 1", link="extras:role_list", permissions=["extras.view_status"])
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
