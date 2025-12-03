import os

from django.apps import apps
from django.test import tag, TestCase
from django.urls import resolve

from nautobot.core.apps import NavMenuTab
from nautobot.core.choices import ButtonActionColorChoices, ButtonActionIconChoices
from nautobot.core.testing.utils import get_expected_menu_item_name
from nautobot.core.ui.choices import NavigationIconChoices, NavigationWeightChoices
from nautobot.core.utils.lookup import get_route_for_model
from nautobot.core.utils.module_loading import import_string_optional
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
                                "Wireless Controllers",
                            }:
                                expected_name = get_expected_menu_item_name(view_model)
                                self.assertEqual(item_details["name"], expected_name)
                            if item_url == get_route_for_model(view_model, "list"):
                                # Not assertEqual as some menu items have additional permissions defined.
                                self.assertIn(get_permission_for_model(view_model, "view"), item_details["permissions"])
                        except AttributeError:
                            # Not a model view?
                            self.assertIn(
                                item_details["name"],
                                {"Apps Marketplace", "Installed Apps", "Interface Connections", "Device Constraints"},
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

    def test_nav_menu_tabs_have_icon_and_weight(self):
        """Ensure each NavMenuTab in every navigation.py has an icon and weight set, and any duplicates by name match."""
        tabs_by_name = {}
        for app in apps.get_app_configs():
            if not app.name.startswith("nautobot."):
                continue
            nav_path = f"{app.name}.navigation.menu_items"
            menu_items = import_string_optional(nav_path)
            if menu_items is None:
                continue
            for tab in menu_items:
                if not isinstance(tab, NavMenuTab):
                    raise TypeError(f"Expected NavMenuTab instance in {nav_path}, got {type(tab)}")
                tab_name = tab.name
                icon = tab.icon
                weight = tab.weight
                with self.subTest(tab_name=tab_name, nav_path=nav_path):
                    self.assertIsNotNone(tab_name, f"Tab in {nav_path} missing 'name'")
                    self.assertIsNotNone(icon, f"Tab '{tab_name}' in {nav_path} missing 'icon'")
                    self.assertIsNotNone(weight, f"Tab '{tab_name}' in {nav_path} missing 'weight'")
                    if tab_name in tabs_by_name:
                        prev_icon, prev_weight, prev_path = tabs_by_name[tab_name]
                        self.assertEqual(
                            icon,
                            prev_icon,
                            f"Tab '{tab_name}' has inconsistent icons: '{icon}' in {nav_path} vs '{prev_icon}' in {prev_path}",
                        )
                        self.assertEqual(
                            weight,
                            prev_weight,
                            f"Tab '{tab_name}' has inconsistent weights: '{weight}' in {nav_path} vs '{prev_weight}' in {prev_path}",
                        )
                    else:
                        tabs_by_name[tab_name] = (icon, weight, nav_path)

    def test_icon_and_weight_class_attributes_match(self):
        """
        Ensure every class attribute in NavigationIconChoices is also in NavigationWeightChoices and vice versa.
        If not, print the missing/extra attributes for easier debugging.
        """
        icon_attrs = {attr for attr in dir(NavigationIconChoices) if attr.isupper()}
        weight_attrs = {attr for attr in dir(NavigationWeightChoices) if attr.isupper()}

        only_in_icons = sorted(icon_attrs - weight_attrs)
        only_in_weights = sorted(weight_attrs - icon_attrs)

        if only_in_icons or only_in_weights:
            msg = []
            if only_in_icons:
                msg.append(f"Class attributes only in NavigationIconChoices: {only_in_icons}")
            if only_in_weights:
                msg.append(f"Class attributes only in NavigationWeightChoices: {only_in_weights}")
            self.fail("\n".join(msg))

    def test_navigation_icons_have_svg(self):
        """Ensure every NavigationIconChoices icon has a corresponding SVG file."""
        missing = []
        svg_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "project-static", "nautobot-icons")
        )
        icon_attrs = [attr for attr in dir(NavigationIconChoices) if attr.isupper() and not attr == "CHOICES"]
        for icon_attr in icon_attrs:
            icon_name = getattr(NavigationIconChoices, icon_attr)
            svg_path = os.path.join(svg_dir, f"{icon_name}.svg")
            if not os.path.isfile(svg_path):
                missing.append(svg_path)
        self.assertFalse(missing, f"Missing SVG files for NavigationIconChoices: {missing}")
