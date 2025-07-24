"""Utilities for apps to integrate with and extend the existing Nautobot UI."""

from nautobot.core.choices import ButtonColorChoices
from nautobot.core.ui.base import PermissionsMixin
from nautobot.core.ui.breadcrumbs import (
    BaseBreadcrumbItem,
    Breadcrumbs,
    InstanceBreadcrumbItem,
    ModelBreadcrumbItem,
    ViewNameBreadcrumbItem,
)
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
    BaseTextPanel,
    Button,
    Component,
    DataTablePanel,
    DistinctViewTab,
    DropdownButton,
    GroupedKeyValueTablePanel,
    KeyValueTablePanel,
    ObjectDetailContent,
    ObjectFieldsPanel,
    ObjectsTablePanel,
    ObjectTextPanel,
    Panel,
    StatsPanel,
    Tab,
    TextPanel,
)
from nautobot.core.ui.titles import Titles
from nautobot.core.ui.utils import render_component_template
from nautobot.extras.choices import BannerClassChoices
from nautobot.extras.plugins import Banner, TemplateExtension

__all__ = (
    "Banner",
    "BannerClassChoices",
    "BaseBreadcrumbItem",
    "BaseTextPanel",
    "Breadcrumbs",
    "Button",
    "ButtonColorChoices",
    "Component",
    "DataTablePanel",
    "DistinctViewTab",
    "DropdownButton",
    "GroupedKeyValueTablePanel",
    "HomePageBase",
    "HomePageGroup",
    "HomePageItem",
    "HomePagePanel",
    "InstanceBreadcrumbItem",
    "KeyValueTablePanel",
    "LayoutChoices",
    "ModelBreadcrumbItem",
    "NavMenuAddButton",
    "NavMenuBase",
    "NavMenuButton",
    "NavMenuGroup",
    "NavMenuImportButton",
    "NavMenuItem",
    "NavMenuTab",
    "ObjectDetailContent",
    "ObjectFieldsPanel",
    "ObjectTextPanel",
    "ObjectsTablePanel",
    "Panel",
    "PermissionsMixin",
    "SectionChoices",
    "StatsPanel",
    "Tab",
    "TemplateExtension",
    "TextPanel",
    "Titles",
    "ViewNameBreadcrumbItem",
    "render_component_template",
)
