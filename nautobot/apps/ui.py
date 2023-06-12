"""Utilities for apps to integrate with and extend the existing Nautobot UI."""

from nautobot.core.apps import (
    HomePageItem,
    HomePagePanel,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import Banner
from nautobot.extras.plugins import TemplateExtension

__all__ = (
    "Banner",
    "BannerClassChoices",
    "HomePageItem",
    "HomePagePanel",
    "NavMenuGroup",
    "NavMenuItem",
    "NavMenuTab",
    "TemplateExtension",
)
