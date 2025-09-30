"""Utilities for apps to integrate with and extend the existing Nautobot UI."""

from nautobot.core.choices import ButtonColorChoices
from nautobot.core.ui.base import PermissionsMixin
from nautobot.core.ui.breadcrumbs import (
    AncestorsBreadcrumbs,
    BaseBreadcrumbItem,
    Breadcrumbs,
    context_object_attr,
    InstanceBreadcrumbItem,
    InstanceParentBreadcrumbItem,
    ModelBreadcrumbItem,
    ViewNameBreadcrumbItem,
)
from nautobot.core.ui.choices import EChartsTypeChoices, LayoutChoices, SectionChoices
from nautobot.core.ui.echarts import (
    EChartsBase,
    queryset_to_nested_dict_keys_as_series,
    queryset_to_nested_dict_records_as_series,
)
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
    EChartsPanel,
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
    "AncestorsBreadcrumbs",
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
    "EChartsBase",
    "EChartsPanel",
    "EChartsTypeChoices",
    "GroupedKeyValueTablePanel",
    "HomePageBase",
    "HomePageGroup",
    "HomePageItem",
    "HomePagePanel",
    "InstanceBreadcrumbItem",
    "InstanceParentBreadcrumbItem",
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
    "context_object_attr",
    "queryset_to_nested_dict_keys_as_series",
    "queryset_to_nested_dict_records_as_series",
    "render_component_template",
)
