from django.apps import AppConfig
from operator import getitem
from collections import OrderedDict

from nautobot.extras.plugins.utils import import_object
from nautobot.extras.registry import registry
from nautobot.utilities.choices import ButtonColorChoices


class NautobotConfig(AppConfig):
    menu_tabs = "navigation.menu_tabs"

    def ready(self):
        if self.__module__.endswith(".apps"):
            self.__module__ = self.__module__[:-5]
        menu_items = import_object(f"{self.__module__}.{self.menu_tabs}")
        if menu_items is not None:
            register_menu_items(menu_items)


def register_menu_items(class_list):
    for nav_tab in class_list:
        registry["nav_menu"]["tabs"][nav_tab.name] = {
            "weight": nav_tab.weight,
            "groups": registry["nav_menu"]["tabs"][nav_tab.name]["groups"]
            if registry["nav_menu"]["tabs"].get(nav_tab.name)
            else {},
            "permissions": [],
        }

        tab_perms = []
        for group in nav_tab.groups:
            registry["nav_menu"]["tabs"][nav_tab.name]["groups"][group.name] = {
                "weight": group.weight,
                "items": registry["nav_menu"]["tabs"][nav_tab.name]["groups"][group.name]["items"]
                if registry["nav_menu"]["tabs"][nav_tab.name]["groups"].get(group.name)
                else {},
                "permissions": [],
            }

            group_perms = []
            for item in group.items:
                registry["nav_menu"]["tabs"][nav_tab.name]["groups"][group.name]["items"][item.link] = item
                group_perms += item.permissions
            registry["nav_menu"]["tabs"][nav_tab.name]["groups"][group.name]["permissions"] = group_perms
            tab_perms += group_perms

        registry["nav_menu"]["tabs"][nav_tab.name]["permissions"] += tab_perms
        registry["nav_menu"]["tabs"][nav_tab.name]["groups"] = OrderedDict(
            sorted(registry["nav_menu"]["tabs"][nav_tab.name]["groups"].items(), key=lambda x: getitem(x[1], "weight"))
        )

    registry["nav_menu"]["tabs"] = OrderedDict(
        sorted(registry["nav_menu"]["tabs"].items(), key=lambda x: getitem(x[1], "weight"))
    )


class NavMenuTab:
    permissions = []
    groups = []

    def __init__(self, name, permissions=None, groups=None, weight=1000):
        self.name = name
        self.weight = weight
        if permissions is not None:
            if type(permissions) not in (list, tuple):
                raise TypeError("Permissions must be passed as a tuple or list.")
            self.permissions = permissions
        if groups is not None:
            if type(groups) not in (list, tuple):
                raise TypeError("Items must be passed as a tuple or list.")
            self.groups = groups


class NavMenuGroup:
    permissions = []
    items = []

    def __init__(self, name, items=None, weight=1000):
        self.name = name
        self.weight = weight
        self.groups = {}
        if items is not None:
            if type(items) not in (list, tuple):
                raise TypeError("Items must be passed as a tuple or list.")
            self.items = items


class NavMenuItem:
    """
    This class represents a navigation menu item. This constitutes primary link and its text, but also allows for
    specifying additional link buttons that appear to the right of the item in the van menu.

    Links are specified as Django reverse URL strings.
    Buttons are each specified as a list of NavMenuButton instances.
    """

    permissions = []
    buttons = []

    def __init__(self, link, link_text, permissions=None, buttons=None, weight=1000):
        self.link = link
        self.link_text = link_text
        self.weight = weight
        if permissions is not None:
            if type(permissions) not in (list, tuple):
                raise TypeError("Permissions must be passed as a tuple or list.")
            self.permissions = permissions
        if buttons is not None:
            if type(buttons) not in (list, tuple):
                raise TypeError("Buttons must be passed as a tuple or list.")
            self.buttons = buttons


class NavMenuButton:
    """
    This class represents a button within a PluginMenuItem. Note that button colors should come from
    ButtonColorChoices.
    """

    color = ButtonColorChoices.DEFAULT
    permissions = []

    def __init__(self, link, title, icon_class, color=None, permissions=None, weight=1000):
        self.link = link
        self.title = title
        self.icon_class = icon_class
        self.weight = weight
        if permissions is not None:
            if type(permissions) not in (list, tuple):
                raise TypeError("Permissions must be passed as a tuple or list.")
            self.permissions = permissions
        if color is not None:
            if color not in ButtonColorChoices.values():
                raise ValueError("Button color must be a choice within ButtonColorChoices.")
            self.color = color
