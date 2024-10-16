"""Utilities for apps to integrate with and extend the existing Nautobot UI."""

from nautobot.core.choices import ButtonColorChoices
from nautobot.core.ui.base import PermissionsMixin
from nautobot.core.ui.choices import LayoutChoices, SectionChoices
from nautobot.core.ui.homepage import (
    HomePageBase,
    HomePageGroup,
    HomePageItem,
    HomePagePanel,
)
from nautobot.core.ui.nav import (
    NavMenuAddButton,
    NavMenuBase,
    NavMenuButton,
    NavMenuGroup,
    NavMenuImportButton,
    NavMenuItem,
    NavMenuTab,
)
from nautobot.core.ui.object_detail import (
    Component,
    GroupedKeyValueTablePanel,
    KeyValueTablePanel,
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectsTablePanel,
    Panel,
    StatsPanel,
    Tab,
)
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import Banner, TemplateExtension

__all__ = (
    "Banner",
    "BannerClassChoices",
    "ButtonColorChoices",
    "Component",
    "GroupedKeyValueTablePanel",
    "HomePageBase",
    "HomePageGroup",
    "HomePageItem",
    "HomePagePanel",
    "KeyValueTablePanel",
    "LayoutChoices",
    "NavMenuAddButton",
    "NavMenuBase",
    "NavMenuButton",
    "NavMenuGroup",
    "NavMenuImportButton",
    "NavMenuItem",
    "NavMenuTab",
    "ObjectDetailContent",
    "ObjectFieldsPanel",
    "ObjectsTablePanel",
    "Panel",
    "PermissionsMixin",
    "SectionChoices",
    "StatsPanel",
    "Tab",
    "TemplateExtension",
)
