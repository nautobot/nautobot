import logging

from abc import ABC, abstractproperty
from django.apps import AppConfig
from operator import getitem
from collections import OrderedDict

from nautobot.extras.plugins.utils import import_object
from nautobot.extras.registry import registry
from nautobot.utilities.choices import ButtonActionColorChoices, ButtonActionIconChoices


logger = logging.getLogger("nautobot.core.apps")
registry["nav_menu"] = {"tabs": {}}


class NautobotConfig(AppConfig):
    """
    Custom AppConfig for Nautobot application.

    Adds functionality to generate the HTML navigation menu using `navigation.py` files from nautbot
    applications.
    """

    menu_tabs = "navigation.menu_items"

    def ready(self):
        """
        Ready function initiates the import application.
        """
        menu_items = import_object(f"{self.name}.{self.menu_tabs}")
        if menu_items is not None:
            register_menu_items(menu_items)


def create_or_check_entry(grouping, record, key, path):
    if key not in grouping:
        grouping[key] = record.initial_dict
    else:
        for attr, value in record.fixed_fields:
            if grouping[key][attr]:
                logger.error("Unable to redefine %s on %s from %s to %s", attr, path, grouping[key][attr], value)


def register_menu_items(tab_list):
    """
    Using the imported object a dictionary is either created or updated with objects to create
    the navbar.

    The dictionary is built from four key objects, NavMenuTab, NavMenuGroup, NavMenuItem and
    NavMenuButton. The Django template then uses this dictionary to generate the navbar HTML.
    """
    for nav_tab in tab_list:
        if isinstance(nav_tab, NavMenuTab):
            create_or_check_entry(registry["nav_menu"]["tabs"], nav_tab, nav_tab.name, f"{nav_tab.name}")

            tab_perms = set()
            registry_groups = registry["nav_menu"]["tabs"][nav_tab.name]["groups"]
            for group in nav_tab.groups:
                create_or_check_entry(registry_groups, group, group.name, f"{nav_tab.name} -> {group.name}")

                group_perms = set()
                for item in group.items:
                    create_or_check_entry(
                        registry_groups[group.name]["items"],
                        item,
                        item.link,
                        f"{nav_tab.name} -> {group.name} -> {item.link}",
                    )

                    registry_buttons = registry_groups[group.name]["items"][item.link]["buttons"]
                    for button in item.buttons:
                        create_or_check_entry(
                            registry_buttons,
                            button,
                            button.title,
                            f"{nav_tab.name} -> {group.name} -> {item.link} -> {button.title}",
                        )

                    # Add sorted buttons to group registry dict
                    registry_groups[group.name]["items"][item.link]["buttons"] = OrderedDict(
                        sorted(registry_buttons.items(), key=lambda kv_pair: kv_pair[1]["weight"])
                    )

                    group_perms |= set(perms for perms in item.permissions)

                # Add sorted items to group registry dict
                registry_groups[group.name]["items"] = OrderedDict(
                    sorted(registry_groups[group.name]["items"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
                )
                # Add collected permissions to group
                registry_groups[group.name]["permissions"] = group_perms
                # Add collected permissions to tab
                tab_perms |= group_perms

            # Add sorted groups to tab dict
            registry["nav_menu"]["tabs"][nav_tab.name]["groups"] = OrderedDict(
                sorted(registry_groups.items(), key=lambda kv_pair: kv_pair[1]["weight"])
            )
            # Add collected permissions to tab dict
            registry["nav_menu"]["tabs"][nav_tab.name]["permissions"] |= tab_perms
        else:
            raise TypeError(f"Top level objects need to be an instance of NavMenuTab: {nav_tab}")

        # Order all tabs in dict
        registry["nav_menu"]["tabs"] = OrderedDict(
            sorted(registry["nav_menu"]["tabs"].items(), key=lambda kv_pair: kv_pair[1]["weight"])
        )


class NavMenuBase(ABC):  # replaces PermissionsMixin
    """Base class for navigation classes."""

    @abstractproperty
    def initial_dict(self):  # to be implemented by each subclass
        return {}

    @abstractproperty
    def fixed_fields(self):  # to be implemented by subclass
        return ()


class PermissionsMixin:
    """Ensure permissions through init."""

    def __init__(self, permissions=None):
        """Ensure permissions."""
        if permissions is not None and not isinstance(permissions, (list, tuple)):
            raise TypeError("Permissions must be passed as a tuple or list.")
        self.permissions = permissions


class NavMenuTab(NavMenuBase, PermissionsMixin):
    """
    Ths class represents a navigation menu tab. This is built up from a name and a weight value. The name is
    the display text and the weight defines its position in the navbar.

    Groups are each specified as a list of NavMenuGroup instances.
    """

    permissions = []
    groups = []

    @property
    def initial_dict(self):
        return {
            "weight": self.weight,
            "groups": {},
            "permissions": set(),
        }

    @property
    def fixed_fields(self):
        return ()

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


class NavMenuGroup(NavMenuBase, PermissionsMixin):
    """
    Ths class represents a navigation menu group. This is built up from a name and a weight value. The name is
    the display text and the weight defines its position in the navbar.

    Items are each specified as a list of NavMenuItem instances.
    """

    permissions = []
    items = []

    @property
    def initial_dict(self):
        return {
            "weight": self.weight,
            "items": {},
        }

    @property
    def fixed_fields(self):
        return ()

    def __init__(self, name, items=None, weight=1000):
        """Ensure group properties."""
        self.name = name
        self.weight = weight

        if items is not None and not isinstance(items, (list, tuple)):
            raise TypeError("Items must be passed as a tuple or list.")
        elif not all(isinstance(item, NavMenuItem) for item in items):
            raise TypeError("All items defined in a group must be an instance of NavMenuItem")
        self.items = items


class NavMenuItem(NavMenuBase, PermissionsMixin):
    """
    This class represents a navigation menu item. This constitutes primary link and its text, but also allows for
    specifying additional link buttons that appear to the right of the item in the nav menu.

    Links are specified as Django reverse URL strings.
    Buttons are each specified as a list of NavMenuButton instances.
    """

    @property
    def initial_dict(self):
        return {
            "name": self.name,
            "weight": self.weight,
            "buttons": {},
            "permissions": self.permissions,
        }

    @property
    def fixed_fields(self):
        return (
            ("name", self.name),
            ("permissions", self.permissions),
        )

    permissions = []
    buttons = []

    def __init__(self, link, name, permissions=None, buttons=(), weight=1000):
        """Ensure item properties."""
        super().__init__(permissions)
        self.link = link
        self.name = name
        self.weight = weight

        if not isinstance(buttons, (list, tuple)):
            raise TypeError("Buttons must be passed as a tuple or list.")
        elif not all(isinstance(button, NavMenuButton) for button in buttons):
            raise TypeError("All buttons defined in an item must be an instance or subclass of NavMenuButton")
        self.buttons = buttons


class NavMenuButton(NavMenuBase, PermissionsMixin):
    """
    This class represents a button within a PluginMenuItem. Note that button colors should come from
    ButtonColorChoices.
    """

    @property
    def initial_dict(self):
        return {
            "link": self.link,
            "icon_class": self.icon_class,
            "button_class": self.button_class,
            "weight": self.weight,
            "buttons": {},
            "permissions": self.permissions,
        }

    @property
    def fixed_fields(self):
        return (
            ("button_class", self.button_class),
            ("icon_class", self.icon_class),
            ("link", self.link),
            ("permissions", self.permissions),
        )

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
