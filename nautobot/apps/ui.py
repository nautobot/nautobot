"""Utilities for apps to integrate with and extend the existing Nautobot UI."""

from nautobot.core.apps import (
    HomePageItem,
    HomePagePanel,
    NavMenuAddButton,
    NavMenuButton,
    NavMenuGroup,
    NavMenuImportButton,
    NavMenuItem,
    NavMenuTab,
)
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import Banner
from nautobot.extras.plugins import TemplateExtension
from nautobot.utilities.choices import ButtonColorChoices

__all__ = (
    "Banner",
    "BannerClassChoices",
    "ButtonColorChoices",
    "HomePageItem",
    "HomePagePanel",
    "NavMenuAddButton",
    "NavMenuButton",
    "NavMenuGroup",
    "NavMenuImportButton",
    "NavMenuItem",
    "NavMenuTab",
    "TemplateExtension",
)
