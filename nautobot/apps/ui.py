"""Utilities for apps to integrate with and extend the existing Nautobot UI."""

from nautobot.core.apps import (
    HomePageBase,
    HomePageGroup,
    HomePageItem,
    HomePagePanel,
    NavContext,
    NavGrouping,
    NavItem,
    NavMenuAddButton,
    NavMenuBase,
    NavMenuButton,
    NavMenuGroup,
    NavMenuImportButton,
    NavMenuItem,
    NavMenuTab,
    PermissionsMixin,
    register_homepage_panels,
    register_menu_items,
    register_new_ui_menu_items,
)
from nautobot.core.choices import ButtonColorChoices
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import Banner
from nautobot.extras.plugins import TemplateExtension


__all__ = (
    "Banner",
    "BannerClassChoices",
    "ButtonColorChoices",
    "HomePageBase",
    "HomePageGroup",
    "HomePageItem",
    "HomePagePanel",
    "NavContext",
    "NavGrouping",
    "NavItem",
    "NavMenuAddButton",
    "NavMenuBase",
    "NavMenuButton",
    "NavMenuGroup",
    "NavMenuImportButton",
    "NavMenuItem",
    "NavMenuTab",
    "PermissionsMixin",
    "register_homepage_panels",
    "register_menu_items",
    "register_new_ui_menu_items",
    "TemplateExtension",
)
