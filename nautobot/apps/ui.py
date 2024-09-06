"""Utilities for apps to integrate with and extend the existing Nautobot UI."""

from nautobot.core.choices import ButtonColorChoices
from nautobot.core.ui.base import PermissionsMixin
from nautobot.core.ui.homepage import (
    HomePageBase,
    HomePageGroup,
    HomePageItem,
    HomePagePanel,
)
from nautobot.core.ui.nav import (
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
)
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import Banner, TemplateExtension

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
    "TemplateExtension",
)
