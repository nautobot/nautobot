from django.apps import AppConfig
from django.urls import reverse
from operator import getitem
from collections import OrderedDict

from nautobot.extras.plugins.utils import import_object
from nautobot.extras.registry import registry
from nautobot.utilities.choices import ButtonActionColorChoices, ButtonActionIconChoices


registry["nav_menu"] = {"tabs": {}}


class NautobotConfig(AppConfig):
    """
    Custom AppConfig for Nautobot application.

    Adds functionality to generate the HTML navigation menu using `navigation.py` files from nautbot
    applications.
    """

    menu_tabs = "navigation.menu_tabs"

    def ready(self):
        """
        Ready function initiates the import application.
        """
        menu_items = import_object(f"{self.name}.{self.menu_tabs}")
        if menu_items is not None:
            register_menu_items(menu_items)


def register_menu_items(tab_list):
    """
    Using the imported object a dictionary is either created or updated with objects to create
    the navbar.

    The dictionary is built from four key objects, NavMenuTab, NavMenuGroup, NavMenuItem and
    NavMenuButton. The Django template then uses this dictionary to generate the navbar HTML.
    """
    for nav_tab in tab_list:
        if nav_tab.name not in registry["nav_menu"]["tabs"]:
            registry["nav_menu"]["tabs"][nav_tab.name] = {
                "weight": nav_tab.weight,
                "groups": {},
                "permissions": [],
            }

        tab_perms = []
        registry_groups = registry["nav_menu"]["tabs"][nav_tab.name]["groups"]
        for group in nav_tab.groups:
            if group.name not in registry_groups:
                registry_groups[group.name] = {
                    "weight": group.weight,
                    "items": {},
                    "permissions": [],
                }

            group_perms = []
            for item in group.items:
                if item.link not in registry_groups[group.name]["items"]:
                    registry_groups[group.name]["items"][item.link] = {
                        "link_text": item.link_text,
                        "weight": item.weight,
                        "buttons": {},
                        "permissions": item.permissions,
                    }

                registry_buttons = registry_groups[group.name]["items"][item.link]["buttons"]
                for button in item.buttons:
                    if button.title not in registry_buttons:
                        registry_buttons[button.title] = {
                            "button_class": button.button_class,
                            "icon_class": button.icon_class,
                            "link": button.link,
                            "permissions": button.permissions,
                            "weight": button.weight,
                        }

                    # Add sorted buttons to group registry dict
                    registry_groups[group.name]["items"][item.link]["buttons"] = OrderedDict(
                        sorted(registry_buttons.items(), key=lambda kv_pair: kv_pair[1]["weight"])
                    )

                group_perms += item.permissions

            # Add sorted items to group registry dict
            registry_groups[group.name]["items"] = OrderedDict(
                sorted(registry_groups[group.name]["items"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
            )
            # Add collected permissions to group
            registry_groups[group.name]["permissions"] = group_perms
            # Add collected permissions to tab
            tab_perms += group_perms

        # Add sorted groups to tab dict
        registry["nav_menu"]["tabs"][nav_tab.name]["groups"] = OrderedDict(
            sorted(registry_groups.items(), key=lambda kv_pair: kv_pair[1]["weight"])
        )
        # Add collected permissions to tab dict
        registry["nav_menu"]["tabs"][nav_tab.name]["permissions"] += tab_perms

    # Order all tabs in dict
    registry["nav_menu"]["tabs"] = OrderedDict(
        sorted(registry["nav_menu"]["tabs"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
    )


class PermissionsMixin:
    """Ensure permissions through init."""

    def __init__(self, permissions=None):
        """Ensure permissions."""
        if permissions is not None and not isinstance(permissions, (list, tuple)):
            raise TypeError("Permissions must be passed as a tuple or list.")
        self.permissions = permissions


class NavMenuTab(PermissionsMixin):
    """
    Ths class represents a navigation menu tab. This is built up from a name and a weight value. The name is
    the display text and the weight defines its position in the navbar.

    Groups are each specified as a list of NavMenuGroup instances.
    """

    permissions = []
    groups = []

    def __init__(self, name, permissions=None, groups=None, weight=1000):
        """Ensure tab properties."""
        super().__init__(permissions)
        self.name = name
        self.weight = weight
        if groups is not None:
            if not isinstance(groups, (list, tuple)):
                raise TypeError("Groups must be passed as a tuple or list.")
            elif not all(isinstance(group, NavMenuGroup) for group in groups):
                raise TypeError("All groups defined in a tab must be an instance of NavMenuGroup")
            self.groups = groups


class NavMenuGroup(PermissionsMixin):
    """
    Ths class represents a navigation menu group. This is built up from a name and a weight value. The name is
    the display text and the weight defines its position in the navbar.

    Items are each specified as a list of NavMenuItem instances.
    """

    permissions = []
    items = []

    def __init__(self, name, items=None, weight=1000):
        """Ensure group properties."""
        self.name = name
        self.weight = weight

        if items is not None and not isinstance(items, (list, tuple)):
            raise TypeError("Items must be passed as a tuple or list.")
        elif not all(isinstance(item, NavMenuItem) for item in items):
            raise TypeError("All items defined in a group must be an instance of NavMenuItem")
        self.items = items


class NavMenuItem(PermissionsMixin):
    """
    This class represents a navigation menu item. This constitutes primary link and its text, but also allows for
    specifying additional link buttons that appear to the right of the item in the nav menu.

    Links are specified as Django reverse URL strings.
    Buttons are each specified as a list of NavMenuButton instances.
    """

    def __init__(self, link, link_text, permissions=None, buttons=None, weight=1000):
        """Ensure item properties."""
        super().__init__(permissions)
        # Reverse lookup sanity check
        reverse(link)
        self.link = link
        self.link_text = link_text
        self.weight = weight

        if buttons is not None and not isinstance(buttons, (list, tuple)):
            raise TypeError("Buttons must be passed as a tuple or list.")
        elif not all(isinstance(button, NavMenuButton) for button in buttons):
            raise TypeError("All buttons defined in an item must be an instance or subclass of NavMenuButton")
        self.buttons = buttons


class NavMenuButton(PermissionsMixin):
    """
    This class represents a button within a PluginMenuItem. Note that button colors should come from
    ButtonColorChoices.
    """

    def __init__(
        self,
        link,
        title,
        icon_class,
        button_class=ButtonActionColorChoices.DEFAULT,
        permissions=None,
        weight=1000,
    ):
        """Ensure button properties."""
        super().__init__(permissions)
        # Reverse lookup sanity check
        reverse(link)
        self.link = link
        self.title = title
        self.icon_class = icon_class
        self.weight = weight
        self.button_class = button_class


class NavMenuAddButton(NavMenuButton):
    """Add button subclass."""

    def __init__(self, *args, **kwargs):
        """Ensure button properties."""
        if "title" not in kwargs:
            kwargs["title"] = "Add"
        if "icon_class" not in kwargs:
            kwargs["icon_class"] = ButtonActionIconChoices.ADD
        if "button_class" not in kwargs:
            kwargs["button_class"] = ButtonActionColorChoices.ADD
        if "weight" not in kwargs:
            kwargs["weight"] = 100
        super().__init__(*args, **kwargs)


class NavMenuImportButton(NavMenuButton):
    """Import button subclass."""

    def __init__(self, *args, **kwargs):
        """Ensure button properties."""
        if "title" not in kwargs:
            kwargs["title"] = "Import"
        if "icon_class" not in kwargs:
            kwargs["icon_class"] = ButtonActionIconChoices.IMPORT
        if "button_class" not in kwargs:
            kwargs["button_class"] = ButtonActionColorChoices.IMPORT
        if "weight" not in kwargs:
            kwargs["weight"] = 200
        super().__init__(*args, **kwargs)
