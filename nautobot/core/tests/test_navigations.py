from django.test import tag, TestCase
from django.urls import resolve

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
                        view_func = resolve(item_url.split("?")[0]).func
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
                                "Example Models filtered",
                                "Interface Connections",
                                "Console Connections",
                                "Power Connections",
                                "Job Approval Queue",
                                "Wireless Controllers",
                            }:
                                expected_name = bettertitle(view_model._meta.verbose_name_plural)
                                if expected_name == "VM Interfaces":
                                    expected_name = "Interfaces"
                                elif expected_name == "Object Changes":
                                    expected_name = "Change Log"
                                elif expected_name == "Controller Managed Device Groups":
                                    expected_name = "Device Groups"
                                self.assertEqual(item_details["name"], expected_name)
                            if item_url == get_route_for_model(view_model, "list"):
                                # Not assertEqual as some menu items have additional permissions defined.
                                self.assertIn(get_permission_for_model(view_model, "view"), item_details["permissions"])
                        except AttributeError:
                            # Not a model view?
                            self.assertIn(
                                item_details["name"], {"Apps Marketplace", "Installed Apps", "Interface Connections"}
                            )

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
