"""Classes and utilities for defining an object detail view through a NautobotUIViewSet."""

import contextlib
from dataclasses import dataclass
from enum import Enum
import logging

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db import models
from django.db.models import CharField, JSONField, Q, URLField
from django.db.models.fields.related import ManyToManyField
from django.template import Context
from django.template.defaultfilters import truncatechars
from django.template.loader import render_to_string
from django.templatetags.l10n import localize
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html, format_html_join
from django_tables2 import RequestConfig

from nautobot.core.choices import ButtonColorChoices
from nautobot.core.models.tree_queries import TreeModel
from nautobot.core.templatetags.helpers import (
    badge,
    bettertitle,
    HTML_NONE,
    hyperlinked_field,
    hyperlinked_object,
    hyperlinked_object_with_color,
    placeholder,
    render_ancestor_hierarchy,
    render_boolean,
    render_content_types,
    render_json,
    render_markdown,
    slugify,
    validated_viewname,
)
from nautobot.core.ui.choices import LayoutChoices, SectionChoices
from nautobot.core.ui.utils import render_component_template
from nautobot.core.utils.lookup import get_filterset_for_model, get_route_for_model
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.utils import get_obj_from_context
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.tables import AssociatedContactsTable, DynamicGroupTable, ObjectMetadataTable
from nautobot.tenancy.models import Tenant

logger = logging.getLogger(__name__)


class ObjectDetailContent:
    """
    Base class for UI framework definition of the contents of an Object Detail (Object Retrieve) page.

    This currently defines the tabs and their panel contents, but does NOT describe the page title, breadcrumbs, etc.

    Basic usage for a `NautobotUIViewSet` looks like:

    ```py
    from nautobot.apps.ui import ObjectDetailContent, ObjectFieldsPanel, SectionChoices


    class MyModelUIViewSet(NautobotUIViewSet):
        queryset = MyModel.objects.all()
        object_detail_content = ObjectDetailContent(
            panels=[ObjectFieldsPanel(section=SectionChoices.LEFT_HALF, weight=100, fields="__all__")],
        )
    ```

    A legacy `ObjectView` can similarly define its own `object_detail_content` attribute as well.
    """

    def __init__(self, *, panels=(), layout=LayoutChoices.DEFAULT, extra_buttons=None, extra_tabs=None):
        """
        Create an ObjectDetailContent with a "main" tab and all standard "extras" tabs (advanced, contacts, etc.).

        Args:
            panels (list): List of `Panel` instances to include in this layout by default. Standard `extras` Panels
                (custom fields, relationships, etc.) do not need to be specified as they will be automatically included.
            layout (str): One of the `LayoutChoices` values, indicating the layout of the "main" tab for this view.
            extra_buttons (list): Optional list of `Button` instances. Standard detail-view "actions" dropdown
                (clone, edit, delete) does not need to be specified as it will be automatically included.
            extra_tabs (list): Optional list of `Tab` instances. Standard `extras` Tabs (advanced, contacts,
                dynamic-groups, metadata, etc.) do not need to be specified as they will be automatically included.
        """
        tabs = [
            _ObjectDetailMainTab(
                layout=layout,
                panels=panels,
            ),
            # Inject "standard" extra tabs
            _ObjectDetailAdvancedTab(),
            _ObjectDetailContactsTab(),
            _ObjectDetailGroupsTab(),
            _ObjectDetailMetadataTab(),
        ]
        if extra_tabs is not None:
            tabs.extend(extra_tabs)
        self.extra_buttons = extra_buttons or []
        self.tabs = tabs

    @property
    def extra_buttons(self):
        """The extra buttons defined for this detail view, ordered by their `weight`."""
        return sorted(self._extra_buttons, key=lambda button: button.weight)

    @extra_buttons.setter
    def extra_buttons(self, value):
        self._extra_buttons = value

    @property
    def tabs(self):
        """The tabs defined for this detail view, ordered by their `weight`."""
        return sorted(self._tabs, key=lambda tab: tab.weight)

    @tabs.setter
    def tabs(self, value):
        self._tabs = value


class Component:
    """Common base class for renderable components (tabs, panels, etc.)."""

    def __init__(self, *, weight):
        """Initialize common Component properties.

        Args:
            weight (int): A relative weighting of this Component relative to its peers. Typically lower weights will be
                rendered "first", usually towards the top left of the page.
        """
        self.weight = weight

    def should_render(self, context: dict):
        """
        Check whether this component should be rendered at all.

        This API is designed to provide "short-circuit" logic for skipping what otherwise might be expensive rendering.
        In general most Components may also return an empty string when actually rendered, which is typically also a
        means to specify that they do not need to be rendered, but may be more expensive to derive.

        Returns:
            (bool): `True` (default) if this component should be rendered.
        """
        return True

    def render(self, context: Context):
        """
        Render this component to HTML.

        Note that not all Components are fully or solely rendered by their `render()` method alone, for example,
        a Tab has a separate "label" that must be rendered by calling its `render_label_wrapper()` API instead.

        Returns:
            (str): HTML fragment, normally generated by a call(s) to `format_html()` or `format_html_join()`.
        """
        return ""

    def get_extra_context(self, context: Context):
        """
        Provide additional data to include in the rendering context, based on the configuration of this component.

        Returns:
            (dict): Additional context data.
        """
        return {}


class Button(Component):
    """Base class for UI framework definition of a single button within an Object Detail (Object Retrieve) page."""

    def __init__(
        self,
        *,
        label,
        color=ButtonColorChoices.DEFAULT,
        link_name=None,
        icon=None,
        template_path="components/button/default.html",
        required_permissions=None,
        javascript_template_path=None,
        attributes=None,
        size=None,
        link_includes_pk=True,
        context_object_key=None,
        **kwargs,
    ):
        """
        Initialize a Button component.

        Args:
            label (str): The text of this button, not including any icon.
            color (ButtonColorChoices): The color (class) of this button.
            link_name (str, optional): View name to link to, for example "dcim:locationtype_retrieve".
                This link will be reversed and will automatically include the current object's PK as a parameter to the
                `reverse()` call when the button is rendered. For more complex link construction, you can subclass this
                and override the `get_link()` method.
            context_object_key (str, optional): The key in the render context that will contain the linked object.
            icon (str, optional): Material Design Icons icon, to include on the button, for example `"mdi-plus-bold"`.
            template_path (str): Template to render for this button.
            required_permissions (list, optional): Permissions such as `["dcim.add_consoleport"]`.
                The button will only be rendered if the user has these permissions.
            javascript_template_path (str, optional): JavaScript template to render and include with this button.
                Does not need to include the wrapping `<script>...</script>` tags as those will be added automatically.
            attributes (dict, optional): Additional HTML attributes and their values to attach to the button.
            size (str, optional): The size of the button (e.g. `xs` or `sm`), used to apply a Bootstrap-style sizing.
        """
        self.label = label
        self.color = color
        self.link_name = link_name
        self.icon = icon
        self.template_path = template_path
        self.required_permissions = required_permissions or []
        self.javascript_template_path = javascript_template_path
        self.attributes = attributes
        self.size = size
        self.link_includes_pk = link_includes_pk
        self.context_object_key = context_object_key
        super().__init__(**kwargs)

    def should_render(self, context: Context):
        """Render if and only if the requesting user has appropriate permissions (if any)."""
        return context["request"].user.has_perms(self.required_permissions)

    def get_link(self, context: Context):
        """
        Get the hyperlink URL (if any) for this button.

        Defaults to reversing `self.link_name` with `pk: obj.pk` as a kwarg, but subclasses may override this for
        more advanced link construction.
        """
        if self.link_name and self.link_includes_pk:
            obj = get_obj_from_context(context, self.context_object_key)
            return reverse(self.link_name, kwargs={"pk": obj.pk})
        elif self.link_name:
            return reverse(self.link_name)
        return None

    def get_extra_context(self, context: Context):
        """Add the relevant attributes of this Button to the context."""
        return {
            "link": self.get_link(context),
            "label": self.label,
            "color": self.color,
            "icon": self.icon,
            "attributes": self.attributes,
            "size": self.size,
        }

    def render(self, context: Context):
        """Render this button to HTML, possibly including any associated JavaScript."""
        if not self.should_render(context):
            return ""

        button = render_component_template(self.template_path, context, **self.get_extra_context(context))
        if self.javascript_template_path:
            button += format_html(
                "<script>{}</script>", render_component_template(self.javascript_template_path, context)
            )
        return button


class DropdownButton(Button):
    """A Button that has one or more other buttons as `children`, which it renders into a dropdown menu."""

    def __init__(self, children: list[Button], template_path="components/button/dropdown.html", **kwargs):
        """Initialize a DropdownButton component.

        Args:
            children (list[Button]): Elements of the dropdown menu associated to this DropdownButton.
            template_path (str): Dropdown-specific template file.
        """
        self.children = children
        super().__init__(template_path=template_path, **kwargs)

    def get_extra_context(self, context: Context):
        """Add the children of this DropdownButton to the other Button context."""
        return {
            **super().get_extra_context(context),
            "children": [child.get_extra_context(context) for child in self.children if child.should_render(context)],
        }


class FormButton(Button):
    def __init__(
        self,
        form_id: str,
        link_name: str,
        template_path="components/button/formbutton.html",
        **kwargs,
    ):
        """
        Initialize a FormButton instance.

        Args:
            link_name (str, optional): View name to link to, for example "dcim:locationtype_retrieve".
                This link will be reversed and will automatically include the current object's PK as a parameter to the
                `reverse()` call when the button is rendered. For more complex link construction, you can subclass this
                and override the `get_link()` method.
        """
        self.form_id = form_id
        self.link_name = link_name

        if not self.link_name:
            raise ValueError("FormButton requires a 'link_name'.")

        if not self.form_id:
            raise ValueError("FormButton requires 'form_id' to be set in ObjectsTablePanel.")

        super().__init__(link_name=link_name, template_path=template_path, **kwargs)

    def get_extra_context(self, context: Context):
        return {
            **super().get_extra_context(context),
            "form_id": self.form_id,
        }


class Tab(Component):
    """Base class for UI framework definition of a single tabbed pane within an Object Detail (Object Retrieve) page."""

    def __init__(
        self,
        *,
        tab_id,
        label,
        panels=(),
        layout=LayoutChoices.DEFAULT,
        label_wrapper_template_path="components/tab/label_wrapper.html",
        content_wrapper_template_path="components/tab/content_wrapper.html",
        **kwargs,
    ):
        """Initialize a Tab component.

        Args:
            tab_id (str): HTML ID for the tab content element, used to link the tab label and its content together.
            label (str): User-facing label to display for this tab.
            panels (tuple): Set of `Panel` components to potentially display within this tab.
            layout (str): One of the [LayoutChoices](./ui.md#nautobot.apps.ui.LayoutChoices) values, describing the layout of panels within this tab.
            label_wrapper_template_path (str): Template path to use for rendering the tab label to HTML.
            content_wrapper_template_path (str): Template path to use for rendering the tab contents to HTML.
        """
        self.tab_id = tab_id
        self.label = label
        self.panels = panels
        self.layout = layout
        self.label_wrapper_template_path = label_wrapper_template_path
        self.content_wrapper_template_path = content_wrapper_template_path
        super().__init__(**kwargs)

    LAYOUT_TEMPLATE_PATHS = {
        LayoutChoices.TWO_OVER_ONE: "components/layout/two_over_one.html",
        LayoutChoices.ONE_OVER_TWO: "components/layout/one_over_two.html",
    }

    WEIGHT_MAIN_TAB = 100
    WEIGHT_ADVANCED_TAB = 200
    WEIGHT_CONTACTS_TAB = 300
    WEIGHT_GROUPS_TAB = 400
    WEIGHT_METADATA_TAB = 500
    WEIGHT_NOTES_TAB = 600  # reserved, not yet using this framework
    WEIGHT_CHANGELOG_TAB = 700  # reserved, not yet using this framework

    def panels_for_section(self, section):
        """
        Get the subset of this tab's panels that apply to the given layout section, ordered by their `weight`.

        Args:
            section (str): One of `SectionChoices`.

        Returns:
            (list[Panel]): Sorted list of Panel instances.
        """
        return sorted((panel for panel in self.panels if panel.section == section), key=lambda panel: panel.weight)

    def render_label_wrapper(self, context: Context):
        """
        Render the tab's label (as opposed to its contents) and wrapping HTML elements.

        In most cases you should not need to override this method; override `render_label()` instead.
        """
        if not self.should_render(context):
            return ""

        return render_component_template(
            self.label_wrapper_template_path,
            context,
            tab_id=self.tab_id,
            label=self.render_label(context),
            **self.get_extra_context(context),
        )

    def render_label(self, context: Context):
        """
        Render the tab's label text in a form suitable for display to the user.

        Defaults to just returning `self.label`, but may be overridden if context-specific formatting is needed.
        """
        return self.label

    def render(self, context: Context):
        """Render the tab's contents (layout and panels) to HTML."""
        if not self.should_render(context):
            return ""

        with context.update(
            {
                "tab_id": self.tab_id,
                "label": self.render_label(context),
                "include_plugin_content": self.tab_id == "main",
                "left_half_panels": self.panels_for_section(SectionChoices.LEFT_HALF),
                "right_half_panels": self.panels_for_section(SectionChoices.RIGHT_HALF),
                "full_width_panels": self.panels_for_section(SectionChoices.FULL_WIDTH),
                **self.get_extra_context(context),
            }
        ):
            tab_content = render_component_template(self.LAYOUT_TEMPLATE_PATHS[self.layout], context)
            return render_component_template(self.content_wrapper_template_path, context, tab_content=tab_content)


class DistinctViewTab(Tab):
    """
    A Tab that doesn't render inline on the same page, but instead links to a distinct view of its own when clicked.

    Args:
        url_name (str): The name of the URL pattern to link to, which will be reversed to generate the URL.
        label_wrapper_template_path (str, optional): Template path to render the tab label to HTML.
        related_object_attribute (str, optional): The name of the related object attribute to count for the tab label.
    """

    def __init__(
        self,
        *,
        url_name,
        label_wrapper_template_path="components/tab/label_wrapper_distinct_view.html",
        related_object_attribute="",
        **kwargs,
    ):
        self.url_name = url_name
        self.related_object_attribute = related_object_attribute
        super().__init__(label_wrapper_template_path=label_wrapper_template_path, **kwargs)

    def get_extra_context(self, context: Context):
        return {"url": reverse(self.url_name, kwargs={"pk": get_obj_from_context(context).pk})}

    def render_label(self, context: Context):
        if not self.related_object_attribute:
            return super().render_label(context)

        obj = get_obj_from_context(context)
        if not hasattr(obj, self.related_object_attribute):
            logger.warning(
                f"{obj} does not have a related attribute {self.related_object_attribute} to count for tab label."
            )
            return super().render_label(context)

        try:
            related_obj_count = getattr(obj, self.related_object_attribute).count()
            return format_html(
                "{} {}",
                self.label,
                render_to_string("utilities/templatetags/badge.html", badge(related_obj_count, True)),
            )
        except AttributeError:
            logger.warning(
                f"{obj}'s attribute {self.related_object_attribute} is not a related manager to count for tab label."
            )
            return super().render_label(context)


class Panel(Component):
    """Base class for defining an individual display panel within a Layout within a Tab."""

    WEIGHT_COMMENTS_PANEL = 200
    WEIGHT_CUSTOM_FIELDS_PANEL = 300
    WEIGHT_COMPUTED_FIELDS_PANEL = 400
    WEIGHT_RELATIONSHIPS_PANEL = 500
    WEIGHT_TAGS_PANEL = 600

    def __init__(
        self,
        *,
        label="",
        section=SectionChoices.FULL_WIDTH,
        body_id=None,
        body_content_template_path=None,
        header_extra_content_template_path=None,
        footer_content_template_path=None,
        template_path="components/panel/panel.html",
        body_wrapper_template_path="components/panel/body_wrapper_generic.html",
        **kwargs,
    ):
        """
        Initialize a Panel component that can be rendered as a self-contained HTML fragment.

        Args:
            label (str): Label to display for this panel. Optional; if an empty string, the panel will have no label.
            section (str): One of the [`SectionChoices`](./ui.md#nautobot.apps.ui.SectionChoices) values, indicating the layout section this Panel belongs to.
            body_id (str): HTML element `id` to attach to the rendered body wrapper of the panel.
            body_content_template_path (str): Template path to render the content contained *within* the panel body.
            header_extra_content_template_path (str): Template path to render extra content into the panel header,
                if any, not including its label if any.
            footer_content_template_path (str): Template path to render content into the panel footer, if any.
            template_path (str): Template path to render the Panel as a whole. Generally you won't override this.
            body_wrapper_template_path (str): Template path to render the panel body, including both its "wrapper"
                (a `div` or `table`) as well as its contents. Generally you won't override this as a user.
        """
        self.label = label
        self.section = section
        self.body_id = body_id
        self.body_content_template_path = body_content_template_path
        self.header_extra_content_template_path = header_extra_content_template_path
        self.footer_content_template_path = footer_content_template_path
        self.template_path = template_path
        self.body_wrapper_template_path = body_wrapper_template_path
        super().__init__(**kwargs)

    def render(self, context: Context):
        """
        Render the panel as a whole.

        Default implementation calls `render_label()`, `render_header_extra_content()`, `render_body()`,
        and `render_footer_extra_content()`, then wraps them all into the templated defined by `self.template_path`.

        Typically you'll override one or more of the aforementioned methods in a subclass, rather than replacing this
        entire method as a whole.
        """
        if not self.should_render(context):
            return ""
        with context.update(self.get_extra_context(context)):
            return render_component_template(
                self.template_path,
                context,
                label=self.render_label(context),
                header_extra_content=self.render_header_extra_content(context),
                body=self.render_body(context),
                footer_content=self.render_footer_content(context),
            )

    def render_label(self, context: Context):
        """Render the label of this panel, if any."""
        return self.label

    def render_header_extra_content(self, context: Context):
        """
        Render any additional (non-label) content to include in this panel's header.

        Default implementation renders the template from `self.header_extra_content_template_path` if any.
        """
        if self.header_extra_content_template_path:
            return render_component_template(self.header_extra_content_template_path, context)
        return ""

    def render_body(self, context: Context):
        """
        Render the panel body *including its HTML wrapper element(s)*.

        Default implementation calls `render_body_content()` and wraps that in the template defined at
        `self.body_wrapper_template_path`.

        Normally you won't want to override this method in a subclass, instead overriding `render_body_content()`.
        """
        return render_component_template(
            self.body_wrapper_template_path,
            context,
            body_id=self.body_id,
            body_content=self.render_body_content(context),
        )

    def render_body_content(self, context: Context):
        """
        Render the content to include in this panel's body.

        Default implementation renders the template from `self.body_content_template_path` if any.
        """
        if self.body_content_template_path:
            return render_component_template(self.body_content_template_path, context)
        return ""

    def render_footer_content(self, context: Context):
        """
        Render any non-default content to include in this panel's footer.

        Default implementation renders the template from `self.footer_content_template_path` if any.
        """
        if self.footer_content_template_path:
            return render_component_template(self.footer_content_template_path, context)
        return ""


class DataTablePanel(Panel):
    """
    A panel that renders a table generated directly from a list of dicts, without using a django_tables2 Table class.
    """

    def __init__(
        self,
        *,
        context_data_key,
        columns=None,
        context_columns_key=None,
        column_headers=None,
        context_column_headers_key=None,
        body_wrapper_template_path="components/panel/body_wrapper_table.html",
        body_content_template_path="components/panel/body_content_data_table.html",
        **kwargs,
    ):
        """
        Instantiate a DataDictTablePanel.

        Args:
            context_data_key (str): The key in the render context that stores the data used to populate the table.
            columns (list, optional): Ordered list of data keys used to order the columns of the rendered table.
                Mutually exclusive with `context_columns_key`.
                If neither are specified, the keys of the first dict in the data will be used.
            context_columns_key (str, optional): The key in the render context that stores the columns list, if any.
                Mutually exclusive with `columns`.
                If neither are specified, the keys of the first dict in the data will be used.
            column_headers (list, optional): List of column header labels, in the same order as `columns` data.
                Mutually exclusive with `context_column_headers_key`.
            context_column_headers_key (str, optional): The key in the render context that stores the column headers.
                Mutually exclusive with `column_headers`.
        """
        self.context_data_key = context_data_key
        if columns and context_columns_key:
            raise ValueError("You can only specify one of `columns` or `context_columns_key`.")
        self.columns = columns
        self.context_columns_key = context_columns_key
        if column_headers and context_column_headers_key:
            raise ValueError("You can only specify one of `column_headers` or `context_column_headers_key`.")
        self.column_headers = column_headers
        self.context_column_headers_key = context_column_headers_key

        super().__init__(
            body_wrapper_template_path=body_wrapper_template_path,
            body_content_template_path=body_content_template_path,
            **kwargs,
        )

    def get_columns(self, context: Context):
        if self.columns:
            return self.columns
        if self.context_columns_key:
            return context.get(self.context_columns_key)
        return list(context.get(self.context_data_key)[0].keys())

    def get_column_headers(self, context: Context):
        if self.column_headers:
            return self.column_headers
        if self.context_column_headers_key:
            return context.get(self.context_column_headers_key)
        return []

    def get_extra_context(self, context: Context):
        return {
            "data": context.get(self.context_data_key),
            "columns": self.get_columns(context),
            "column_headers": self.get_column_headers(context),
        }


class ObjectsTablePanel(Panel):
    """A panel that renders a Table of objects (typically related objects, rather than the "main" object of a view).
    Has built-in pagination support and "Add" button at bottom of the Table.

    It renders the django-tables2 classes with Nautobot additions. You can pass the instance of Table Class
    already configured in context and set the `context_table_key` or pass a Table Class to `__init__` via `table_class`.

    When `table_class` is set, you need to pass `table_filter` or `table_attribute` for fetching data purpose.

    Data fetching can be optimized by using `select_related_fields`, `prefetch_related_fields`.

    How Table is displayed can be changed by using `include_columns`, `exclude_columns`, `table_title`,
    `hide_hierarchy_ui`, `related_field_name` or `enable_bulk_actions`.

    Please check the Args list for further details.
    """

    def __init__(
        self,
        *,
        context_table_key=None,
        table_class=None,
        table_filter=None,
        table_attribute=None,
        select_related_fields=None,
        prefetch_related_fields=None,
        order_by_fields=None,
        table_title=None,
        max_display_count=None,
        paginate=True,
        show_table_config_button=True,
        include_columns=None,
        exclude_columns=None,
        add_button_route="default",
        add_permissions=None,
        hide_hierarchy_ui=False,
        related_field_name=None,
        enable_bulk_actions=False,
        tab_id=None,
        body_wrapper_template_path="components/panel/body_wrapper_table.html",
        body_content_template_path="components/panel/body_content_objects_table.html",
        header_extra_content_template_path="components/panel/header_extra_content_table.html",
        footer_content_template_path="components/panel/footer_content_table.html",
        footer_buttons=None,
        form_id=None,
        include_paginator=False,
        **kwargs,
    ):
        """Instantiate an ObjectsTable panel.

        Args:
            context_table_key (str): The key in the render context that will contain an already-populated-and-configured
                Table (`BaseTable`) instance. Mutually exclusive with `table_class`, `table_filter`, `table_attribute`.
            table_class (obj): The table class that will be instantiated and rendered e.g. CircuitTable, DeviceTable.
                Mutually exclusive with `context_table_key`.
            table_filter (str, list, optional): The filter(s) to apply to the queryset to initialize the table class.
                For example, in a LocationType detail view, for an ObjectsTablePanel of related Locations, this would
                be `location_type`, because `Location.objects.filter(location_type=obj)` gives the desired queryset.
                Mutually exclusive with `table_attribute`.
                For example, in ProviderNetwork detail view, for an ObjectsTablePanel of related Circuits, this would
                be `["circuit_termination_a__provider_network", "circuit_termination_z__provider_network"]` because
                `Circuit.objects.filter(Q(circuit_termination_a__provider_network=instance)
                | Q(circuit_termination_z__provider_network=instance))` gives the desired queryset.
            table_attribute (str, optional): The attribute of the detail view instance that contains the queryset to
                initialize the table class. e.g. `dynamic_groups`.
                Mutually exclusive with `table_filter`.
            select_related_fields (list, optional): list of fields to pass to table queryset's `select_related` method.
            prefetch_related_fields (list, optional): list of fields to pass to table queryset's `prefetch_related`
                method.
            order_by_fields (list, optional): list of fields to order the table queryset by.
            max_display_count (int, optional):  Maximum number of items to display in the table.
                If None, defaults to the `get_paginate_count()` (which is user's preference or a global setting).
            paginate (bool, optional): If False, do not attach a paginator to the table and render all rows
                (or up to `max_display_count` if provided). Defaults to True.
            show_table_config_button (bool, optional): If False, hide the small "Configure" button rendered in the
                panel header for this table. Defaults to True.
            table_title (str, optional): The title to display in the panel heading for the table.
                If None, defaults to the plural verbose name of the table model.
            include_columns (list, optional): A list of field names to include in the table display.
            exclude_columns (list, optional): A list of field names to exclude from the table display.
            add_button_route (str, optional): The route used to generate the "add" button URL. Defaults to "default",
                which uses the default table's model `add` route.
            add_permissions (list, optional): A list of permissions required for the "add" button to be displayed.
                If not provided, permissions are determined by default based on the model.
            hide_hierarchy_ui (bool, optional): Don't display hierarchy-based indentation of tree models in this table
            related_field_name (str, optional): The name of the filter/form field for the related model that links back
                to the base model. Defaults to the same as `table_filter` if unset. Used to populate URLs.
            enable_bulk_actions (bool, optional): Show the pk toggle columns on the table if the user has the
                appropriate permissions.
            tab_id (str, optional): The ID of the tab this panel belongs to. Used to append to a `return_url` when
                users navigate away from the tab and redirect them back to the correct one.
            footer_buttons (list, optional): A list of Button or FormButton components to render in the panel footer.
                These buttons typically perform actions like bulk delete, edit, or custom form submission.
            form_id (str, optional): A unique ID for this table's form; used to set the `data-form-id` attribute on each `FormButton`.
            include_paginator (bool, optional): If True, renders a paginator in the panel footer.
        """
        if context_table_key and any(
            [
                table_class,
                table_filter,
                table_attribute,
                select_related_fields,
                prefetch_related_fields,
                order_by_fields,
                hide_hierarchy_ui,
            ]
        ):
            raise ValueError(
                "context_table_key cannot be combined with any of the args that are used to dynamically construct the "
                "table (table_class, table_filter, table_attribute, select_related_fields, prefetch_related_fields, "
                "order_by_fields, hide_hierarchy_ui)."
            )
        self.context_table_key = context_table_key
        self.table_class = table_class
        if table_filter and table_attribute:
            raise ValueError("You can only specify either `table_filter` or `table_attribute`")
        if table_class and not (table_filter or table_attribute):
            raise ValueError("You must specify either `table_filter` or `table_attribute`")
        if table_attribute and not related_field_name:
            raise ValueError("You must provide a `related_field_name` when specifying `table_attribute`")
        self.table_filter = table_filter
        self.table_attribute = table_attribute
        self.select_related_fields = select_related_fields
        self.prefetch_related_fields = prefetch_related_fields
        self.order_by_fields = order_by_fields
        self.table_title = table_title
        self.max_display_count = max_display_count
        self.paginate = paginate
        self.show_table_config_button = show_table_config_button
        self.include_columns = include_columns
        self.exclude_columns = exclude_columns
        self.add_button_route = add_button_route
        self.add_permissions = add_permissions
        self.hide_hierarchy_ui = hide_hierarchy_ui
        self.related_field_name = related_field_name
        self.enable_bulk_actions = enable_bulk_actions
        self.tab_id = tab_id
        self.footer_buttons = footer_buttons
        self.form_id = form_id
        self.include_paginator = include_paginator

        super().__init__(
            body_wrapper_template_path=body_wrapper_template_path,
            body_content_template_path=body_content_template_path,
            header_extra_content_template_path=header_extra_content_template_path,
            footer_content_template_path=footer_content_template_path,
            **kwargs,
        )

    def _get_table_add_url(self, context: Context):
        """Generate the URL for the "Add" button in the table panel.

        This method determines the URL for adding a new object to the table. It checks if the user has
        the necessary permissions and creates the appropriate URL based on the specified add button route.
        """
        obj = get_obj_from_context(context)
        body_content_table_add_url = None
        request = context["request"]
        related_field_name = self.related_field_name or self.table_filter or obj._meta.model_name
        return_url = context.get("return_url", obj.get_absolute_url())
        if self.tab_id:
            return_url += f"?tab={self.tab_id}"

        if self.add_button_route == "default":
            body_content_table_class = self.table_class or context[self.context_table_key].__class__
            body_content_table_model = body_content_table_class.Meta.model
            permission_name = get_permission_for_model(body_content_table_model, "add")
            if request.user.has_perms([permission_name]):
                try:
                    add_route = reverse(get_route_for_model(body_content_table_model, "add"))
                    body_content_table_add_url = f"{add_route}?{related_field_name}={obj.pk}&return_url={return_url}"
                except NoReverseMatch:
                    logger.warning("add route for `body_content_table_model` not found")

        elif self.add_button_route is not None:
            if request.user.has_perms(self.add_permissions or []):
                add_route = reverse(self.add_button_route)
                body_content_table_add_url = f"{add_route}?{related_field_name}={obj.pk}&return_url={return_url}"

        return body_content_table_add_url

    def get_extra_context(self, context: Context):
        """Add additional context for rendering the table panel.

        This method processes the table data, configures pagination, and generates URLs
        for listing and adding objects. It also handles field inclusion/exclusion and
        displays the appropriate table title if provided.
        """
        request = context["request"]
        if self.context_table_key:
            body_content_table = context.get(self.context_table_key)
            body_content_table_model = body_content_table.Meta.model
        else:
            body_content_table_class = self.table_class
            body_content_table_model = body_content_table_class.Meta.model
            instance = get_obj_from_context(context)

            if self.table_attribute:
                body_content_table_queryset = getattr(instance, self.table_attribute)
            else:
                if isinstance(self.table_filter, str):
                    table_filters = [self.table_filter]
                elif isinstance(self.table_filter, list):
                    table_filters = self.table_filter
                else:
                    table_filters = []
                query = Q()
                for table_filter in table_filters:
                    query = query | Q(**{table_filter: instance})
                body_content_table_queryset = body_content_table_model.objects.filter(query)

            body_content_table_queryset = body_content_table_queryset.restrict(request.user, "view")
            if self.select_related_fields:
                body_content_table_queryset = body_content_table_queryset.select_related(*self.select_related_fields)
            if self.prefetch_related_fields:
                body_content_table_queryset = body_content_table_queryset.prefetch_related(
                    *self.prefetch_related_fields
                )
            if self.order_by_fields:
                body_content_table_queryset = body_content_table_queryset.order_by(*self.order_by_fields)
            body_content_table_queryset = body_content_table_queryset.distinct()
            body_content_table = body_content_table_class(
                body_content_table_queryset, hide_hierarchy_ui=self.hide_hierarchy_ui, user=request.user
            )
            if self.tab_id and "actions" in body_content_table.columns:
                # Use the `self.tab_id`, if it exists, to determine the correct return URL for the table
                # to redirect the user back to the correct tab after editing/deleteing an object
                body_content_table.columns["actions"].column.extra_context["return_url_extra"] = f"?tab={self.tab_id}"

        if self.exclude_columns:
            for column in body_content_table.columns:
                if column.name in self.exclude_columns:
                    body_content_table.columns.hide(column.name)

        if self.include_columns:
            for column in self.include_columns:
                if column not in body_content_table.base_columns:
                    raise ValueError(f"You are specifying a non-existent column `{column}`")
                body_content_table.columns.show(column)

        # Enable bulk action toggle if the user has appropriate permissions
        user = request.user
        if self.enable_bulk_actions and (
            user.has_perm(get_permission_for_model(body_content_table_model, "delete"))
            or user.has_perm(get_permission_for_model(body_content_table_model, "change"))
        ):
            body_content_table.columns.show("pk")

        more_queryset_count = 0
        if self.paginate:
            per_page = self.max_display_count if self.max_display_count is not None else get_paginate_count(request)
            paginate = {"paginator_class": EnhancedPaginator, "per_page": per_page}
            RequestConfig(request, paginate).configure(body_content_table)
            try:
                more_queryset_count = max(body_content_table.data.data.count() - per_page, 0)
            except TypeError:
                more_queryset_count = max(len(body_content_table.data.data) - per_page, 0)
        elif self.max_display_count is not None:
            # If not paginating but a cap is desired, slice the table's data source.
            try:
                more_queryset_count = max(body_content_table.data.data.count() - self.max_display_count, 0)
                body_content_table.data.data = body_content_table.data.data[: self.max_display_count]
            except TypeError:
                # Non-queryset iterable; fall back to list slicing
                more_queryset_count = max(len(body_content_table.data.data) - self.max_display_count, 0)
                body_content_table.data.data = list(body_content_table.data.data)[: self.max_display_count]

        obj = get_obj_from_context(context)
        body_content_table_model = body_content_table.Meta.model
        related_field_name = self.related_field_name or self.table_filter or obj._meta.model_name

        list_url = getattr(self.table_class, "list_url", None)
        if not list_url:
            list_url = get_route_for_model(body_content_table_model, "list")

        try:
            list_route = reverse(list_url)
        except NoReverseMatch:
            list_route = None

        if list_route:
            body_content_table_list_url = f"{list_route}?{related_field_name}={obj.pk}"
        else:
            body_content_table_list_url = None

        body_content_table_add_url = self._get_table_add_url(context)
        body_content_table_verbose_name_plural = self.table_title or body_content_table_model._meta.verbose_name_plural

        return {
            "body_content_table": body_content_table,
            "body_content_table_add_url": body_content_table_add_url,
            "body_content_table_list_url": body_content_table_list_url,
            "body_content_table_verbose_name": body_content_table_model._meta.verbose_name,
            "body_content_table_verbose_name_plural": body_content_table_verbose_name_plural,
            "footer_buttons": self.footer_buttons,
            "form_id": self.form_id,
            "more_queryset_count": more_queryset_count,
            "include_paginator": self.include_paginator,
            "show_table_config_button": self.show_table_config_button,
        }


class KeyValueTablePanel(Panel):
    """A panel that displays a two-column table of keys and values, as seen in most object detail views."""

    def __init__(
        self,
        *,
        data=None,
        context_data_key=None,
        hide_if_unset=(),
        value_transforms=None,
        body_wrapper_template_path="components/panel/body_wrapper_key_value_table.html",
        **kwargs,
    ):
        """
        Instantiate a KeyValueTablePanel.

        Args:
            data (dict): The dictionary of key/value data to display in this panel.
                May be `None` if it will be derived dynamically by `get_data()` or from `context_data_key` instead.
            context_data_key (str): The render context key that will contain the data, if `data` wasn't provided.
            hide_if_unset (list): Keys that should be omitted from the display entirely if they have a falsey value,
                instead of displaying the usual em-dash placeholder text.
            value_transforms (dict): Dictionary of `{key: [list of transform functions]}`, used to specify custom
                rendering of specific key values without needing to implement a new subclass for this purpose.
                Many of the `templatetags.helpers` functions are suitable for this purpose; examples:

                - `[render_markdown, placeholder]` - render the given text as Markdown, or render a placeholder if blank
                - `[humanize_speed, placeholder]` - convert the given kbps value to Mbps or Gbps for display
        """
        if data and context_data_key:
            raise ValueError("The data and context_data_key parameters are mutually exclusive")
        self.data = data
        self.context_data_key = context_data_key or "data"
        self.hide_if_unset = hide_if_unset
        self.value_transforms = value_transforms or {}
        super().__init__(body_wrapper_template_path=body_wrapper_template_path, **kwargs)

    def should_render(self, context: Context):
        return bool(self.get_data(context))

    def get_data(self, context: Context):
        """
        Get the data for this panel, by default from `self.data` or the key `"data"` in the provided context.

        Subclasses may need to override this method if the derivation of the data is more involved.

        Returns:
            (dict): Key/value dictionary to be rendered in this panel.
        """
        return self.data or context[self.context_data_key]

    def render_key(self, key, value, context: Context):
        """
        Render the provided key in human-readable form.

        The default implementation simply replaces underscores with spaces and title-cases it with `bettertitle()`.
        """
        return bettertitle(key.replace("_", " "))

    def queryset_list_url_filter(self, key, value, context: Context):
        """
        Get a filter parameter to use when hyperlinking queryset data to an object list URL to provide filtering.

        Returns:
            (str): A URL parameter string of the form `"filter=value"`, or `""` if none is known.

        The default implementation returns `""`, which means "no appropriate filter parameter is known,
        do not hyperlink the queryset text." Subclasses may wish to override this to provide appropriate intelligence.

        Examples:
            - For a queryset of VRFs in a Location detail view for instance `aaf814ef-2ef6-463e-9440-54f6514afe0e`,
              this might return the string `"locations=aaf814ef-2ef6-463e-9440-54f6514afe0e"`, resulting in the
              hyperlinked URL `/ipam/vrfs/?locations=aaf814ef-2ef6-463e-9440-54f6514afe0e`
            - For a queryset of Devices associated to Circuit Termination `4182ce87-0f90-450e-a682-9af5992b4bb7`
              by a Relationship with key `termination_to_devices`, this might return the string
              `"cr_termination_to_devices__source=4182ce87-0f90-450e-a682-9af5992b4bb7"`, resulting in the hyperlinked
              URL `/dcim/devices/?cr_termination_to_device__source=4182ce87-0f90-450e-a682-9af5992b4bb7`
        """
        return ""

    def render_value(self, key, value, context) -> str:
        """
        Render the provided value in human-readable form.

        Returns:
            (str): String or HTML representation of the given value. May return `""` to indicate that this value
                should be skipped entirely, i.e. not displayed in the table at all.
                May return `placeholder(value)` to display a consistent placeholder representation of any unset value.

        Behavior is influenced by:

        - `self.value_transforms` - if it has an entry for the given `key`, then the given functions provided there
          will be used to render the `value`, in place of any default processing and rendering for this data type.
        - `self.hide_if_unset` - any key in this list, if having a corresponding value of `None`, will be omitted from
          the display (returning `""` instead of a placeholder).

        There is a lot of "intelligence" built in to this method to handle various data types, including:
        - Instances of `TreeModel` will display the full path from root to node (using `render_ancestor_hierarchy()`)
        - Instances of `Status`, `Role` and similar models will be represented as an appropriately-colored hyperlinked
          badge (using `hyperlinked_object_with_color()`)
        - Instances of `Tenant` will be hyperlinked and will also display their hyperlinked `TenantGroup` if any
        - Instances of other models will be hyperlinked (using `hyperlinked_object()`)
        - Model QuerySets will render the first several objects in the QuerySet (as above), and if more objects are
          present, and `self.queryset_list_url_filter()` returns an appropriate filter string, will render the link to
          the filtered list view of that model.
        - Etc.
        """
        display = value
        if key in self.value_transforms:
            for transform in self.value_transforms[key]:
                display = transform(display)

        elif value is None:
            if key in self.hide_if_unset:
                display = ""
            else:
                display = placeholder(value)

        elif isinstance(value, bool):
            return render_boolean(value)

        elif isinstance(value, TreeModel):
            display = render_ancestor_hierarchy(value)

        elif isinstance(value, models.Model):
            if hasattr(value, "color"):
                display = hyperlinked_object_with_color(value)
            elif isinstance(value, Tenant) and value.tenant_group is not None:
                display = format_html("{} / {}", hyperlinked_object(value.tenant_group), hyperlinked_object(value))
            # TODO: render location hierarchy for Location objects
            else:
                display = hyperlinked_object(value)

        elif isinstance(value, models.QuerySet):
            if not value.exists():
                display = placeholder(None)
            else:
                # Link to the filtered list, and display up to 3 records individually as a list
                count = value.count()
                model = value.model

                # If we can find the list URL and the appropriate filter parameter for this listing, wrap the above
                # in an appropriate hyperlink:
                list_url = None
                list_url_filter = self.queryset_list_url_filter(key, value, context)
                list_url_name = validated_viewname(model, "list")
                if list_url_filter and list_url_name:
                    list_url = f"{reverse(list_url_name)}?{list_url_filter}"

                display = format_html_join(
                    ", ", "{}", ([self.render_value(key, record, context)] for record in value[:3])
                )
                if count > 3:
                    if list_url:
                        display += format_html(
                            ', and <a href="{}">{} other {}</a>',
                            list_url,
                            count - 3,
                            model._meta.verbose_name if count - 3 == 1 else model._meta.verbose_name_plural,
                        )
                    else:
                        display += format_html(
                            ", and {} other {}",
                            count - 3,
                            model._meta.verbose_name if count - 3 == 1 else model._meta.verbose_name_plural,
                        )
        else:
            display = placeholder(localize(value))

        # TODO: apply additional smart formatting such as JSON/Markdown rendering, etc.
        return display

    def render_body_content(self, context: Context):
        """Render key-value pairs as table rows, using `render_key()` and `render_value()` methods as applicable."""
        data = self.get_data(context)

        if not data:
            return format_html('<tr><td colspan="2">{}</td></tr>', placeholder(data))

        result = format_html("")
        panel_label = slugify(self.label or "")
        for key, value in data.items():
            key_display = self.render_key(key, value, context)

            if value_display := self.render_value(key, value, context):
                if value_display is HTML_NONE:
                    value_tag = value_display
                else:
                    value_tag = format_html(
                        """
                            <span class="hover_copy">
                                <span id="{unique_id}_value_{key}">{value}</span>
                                <button class="btn btn-inline btn-default hover_copy_button" data-clipboard-target="#{unique_id}_value_{key}">
                                    <span class="mdi mdi-content-copy"></span>
                                </button>
                            </span>
                        """,
                        # key might not be globally unique in a page, but is unique to a panel;
                        # Hence we add the panel label to make it globally unique to the page
                        unique_id=panel_label,
                        key=slugify(key),
                        value=value_display,
                    )
                result += format_html("<tr><td>{key}</td><td>{value}</td></tr>", key=key_display, value=value_tag)

        return result


class ObjectFieldsPanel(KeyValueTablePanel):
    """A panel that renders a table of object instance attributes and their values."""

    def __init__(
        self,
        *,
        fields="__all__",
        exclude_fields=(),
        context_object_key=None,
        ignore_nonexistent_fields=False,
        label=None,
        **kwargs,
    ):
        """
        Instantiate an ObjectFieldsPanel.

        Args:
            fields (str, list): The ordered list of fields to display, or `"__all__"` to display fields automatically.
                Note that ManyToMany fields and reverse relations are **not** included in `"__all__"` at this time, nor
                are any hidden fields, nor the specially handled `id`, `created`, `last_updated` fields on most models.
            exclude_fields (list): Only relevant if `fields == "__all__"`, in which case it excludes the given fields.
            context_object_key (str): The key in the render context that will contain the object to derive fields from.
            ignore_nonexistent_fields (bool): If True, `fields` is permitted to include field names that don't actually
                exist on the provided object; otherwise an exception will be raised at render time.
            label (str): If omitted, the provided object's `verbose_name` will be rendered as the label
                (see `render_label()`).
        """
        self.fields = fields
        self.exclude_fields = exclude_fields
        self.context_object_key = context_object_key
        self.ignore_nonexistent_fields = ignore_nonexistent_fields
        super().__init__(data=None, label=label, **kwargs)

    def render_label(self, context: Context):
        """Default to rendering the provided object's `verbose_name` if no more specific `label` was defined."""
        if self.label is None:
            return bettertitle(get_obj_from_context(context, self.context_object_key)._meta.verbose_name)
        return super().render_label(context)

    def render_value(self, key, value, context: Context):
        obj = get_obj_from_context(context, self.context_object_key)
        try:
            field_instance = obj._meta.get_field(key)
        except FieldDoesNotExist:
            field_instance = None

        if key in self.value_transforms:
            display = value
            for transform in self.value_transforms[key]:
                display = transform(display)
            return display

        if key == "_hierarchy":
            return render_ancestor_hierarchy(value)

        if isinstance(field_instance, URLField):
            return hyperlinked_field(value)

        if isinstance(field_instance, JSONField):
            return format_html("<pre>{}</pre>", render_json(value))

        if isinstance(field_instance, ManyToManyField) and field_instance.related_model == ContentType:
            return render_content_types(value)

        if isinstance(field_instance, CharField) and hasattr(obj, f"get_{key}_display"):
            # For example, Secret.provider -> Secret.get_provider_display()
            # Note that we *don't* want to do this for models with a StatusField and its `get_status_display()`
            return super().render_value(key, getattr(obj, f"get_{key}_display")(), context)

        return super().render_value(key, value, context)

    def get_data(self, context: Context):
        """
        Load data from the object provided in the render context based on the given set of `fields`.

        Returns:
            (dict): Key-value pairs corresponding to the object's fields, or `{}` if no object is present.
        """
        fields = self.fields
        instance = get_obj_from_context(context, self.context_object_key)

        if instance is None:
            return {}

        if fields == "__all__":
            # Derive the list of fields from the instance, skipping certain fields by default.
            fields = []
            for field in instance._meta.get_fields():
                if field.hidden or field.name.startswith("_"):
                    continue
                if field.name in ("id", "created", "last_updated", "tags", "comments"):
                    # Handled elsewhere in the detail view
                    continue
                if field.is_relation and field.one_to_many:
                    # Reverse relations should be handled by ObjectsTablePanel
                    continue
                if field.is_relation and field.many_to_many and field.related_model != ContentType:
                    # Many-to-many relations should be handled by ObjectsTablePanel, *except* for ContentTypes, where
                    # we keep the historic pattern of just rendering them as a list since there's no need for a table
                    continue
                fields.append(field.name)
            # TODO: apply a default ordering "smarter" than declaration order? Alphabetical? By field type?
            # TODO: allow model to specify an alternative field ordering?

        data = {}

        if isinstance(instance, TreeModel) and (self.fields == "__all__" or "_hierarchy" in self.fields):
            # using `_hierarchy` with the prepended `_` to try to archive a unique name, in cases where a model might have hierarchy field.
            data["_hierarchy"] = instance

        for field_name in fields:
            if field_name in self.exclude_fields:
                continue
            try:
                field_value = getattr(instance, field_name)
            except ObjectDoesNotExist:
                field_value = None
            except AttributeError:
                if self.ignore_nonexistent_fields:
                    continue
                raise

            data[field_name] = field_value

        # Ensuring the `name` field is displayed first, if present.
        if "name" in data:
            data = {"name": data["name"], **{k: v for k, v in data.items() if k != "name"}}

        return data

    def render_key(self, key, value, context: Context):
        """Render the `verbose_name` of the model field whose name corresponds to the given key, if applicable."""
        instance = get_obj_from_context(context, self.context_object_key)

        if instance is not None:
            try:
                field = instance._meta.get_field(key)
                return bettertitle(field.verbose_name)
            # Not all fields have a verbose name, ManyToOneRel for example.
            except (FieldDoesNotExist, AttributeError):
                pass

        return super().render_key(key, value, context)


class GroupedKeyValueTablePanel(KeyValueTablePanel):
    """
    A KeyValueTablePanel that displays its data within collapsible accordion groupings, such as object custom fields.

    Expects data in the form `{grouping1: {key1: value1, key2: value2, ...}, grouping2: {...}, ...}`.

    The special grouping `""` may be used to indicate top-level key/value pairs that don't belong to a group.
    """

    def __init__(self, *, body_id, **kwargs):
        super().__init__(body_id=body_id, **kwargs)

    def render_header_extra_content(self, context: Context):
        """Add a "Collapse All" button to the header."""
        return format_html(
            '<button type="button" class="btn-xs btn-primary pull-right accordion-toggle-all" data-target="#{body_id}">'
            "Collapse All</button>",
            body_id=self.body_id,
        )

    def render_body_content(self, context: Context):
        """Render groups of key-value pairs to HTML."""
        data = self.get_data(context)

        if not data:
            return format_html('<tr><td colspan="2">{}</td></tr>', placeholder(data))

        result = format_html("")
        counter = 0
        for grouping, entry in data.items():
            counter += 1
            if grouping:
                result += render_component_template(
                    "components/panel/grouping_toggle.html",
                    context,
                    grouping=grouping,
                    body_id=self.body_id,
                    counter=counter,
                )
            for key, value in entry.items():
                key_display = self.render_key(key, value, context)
                value_display = self.render_value(key, value, context)
                if value_display:
                    # TODO: add a copy button on hover to all display items
                    result += format_html(
                        '<tr class="collapseme-{body_id}-{counter} collapse in" data-parent="#{body_id}">'
                        "<td>{key}</td><td>{value}</td></tr>",
                        counter=counter,
                        body_id=self.body_id,
                        key=key_display,
                        value=value_display,
                    )

        return result


class BaseTextPanel(Panel):
    """A panel that renders a single value as text, Markdown, JSON, or YAML."""

    class RenderOptions(Enum):
        """Options available for text panels for different type of rendering a given input.

        Attributes:
            PLAINTEXT (str): Plain text format (value: "plaintext").
            JSON (str): Dict will be dumped into JSON and pretty-formatted (value: "json").
            YAML (str): Dict will be displayed as pretty-formatted yaml (value: "yaml")
            MARKDOWN (str): Markdown format (value: "markdown").
            CODE (str): Code format. Just wraps content within <pre> tags (value: "code").
        """

        PLAINTEXT = "plaintext"
        JSON = "json"
        YAML = "yaml"
        MARKDOWN = "markdown"
        CODE = "code"

    def __init__(
        self,
        *,
        render_as=RenderOptions.MARKDOWN,
        body_content_template_path="components/panel/body_content_text.html",
        render_placeholder=True,
        **kwargs,
    ):
        """
        Instantiate BaseTextPanel.

        Args:
            render_as (RenderOptions): One of BaseTextPanel.RenderOptions to define rendering function.
            render_placeholder (bool): Whether to render placeholder text if given value is "falsy".
            body_content_template_path (str): The path of the template to use for the body content.
                Can be overridden for custom use cases.
            kwargs (dict): Additional keyword arguments passed to `Panel.__init__`.
        """
        self.render_as = render_as
        self.render_placeholder = render_placeholder
        super().__init__(body_content_template_path=body_content_template_path, **kwargs)

    def render_body_content(self, context: Context):
        value = self.get_value(context)

        if not value and self.render_placeholder:
            return HTML_NONE

        if self.body_content_template_path:
            return render_component_template(
                self.body_content_template_path, context, render_as=self.render_as.value, value=value
            )
        return value

    def get_value(self, context: Context):
        raise NotImplementedError


class ObjectTextPanel(BaseTextPanel):
    """
    Panel that renders text, Markdown, JSON or YAML from the given field on the given object in the context.

    Args:
        object_field (str): The name of the object field to be rendered. None by default.
        kwargs (dict): Additional keyword arguments passed to `BaseTextPanel.__init__`.
    """

    def __init__(self, *, object_field=None, **kwargs):
        self.object_field = object_field

        super().__init__(**kwargs)

    def get_value(self, context: Context):
        obj = get_obj_from_context(context)
        if not obj:
            return ""
        return getattr(obj, self.object_field, "")


class TextPanel(BaseTextPanel):
    """Panel that renders text, Markdown, JSON or YAML from the given value in the context.

    Args:
        context_field (str): source field from context with value for `TextPanel`.
        kwargs (dict): Additional keyword arguments passed to `BaseTextPanel.__init__`.
    """

    def __init__(self, *, context_field="text", **kwargs):
        self.context_field = context_field
        super().__init__(**kwargs)

    def get_value(self, context: Context):
        return context.get(self.context_field, "")


class StatsPanel(Panel):
    def __init__(
        self,
        *,
        filter_name,
        related_models=None,
        body_content_template_path="components/panel/stats_panel_body.html",
        **kwargs,
    ):
        """
        Instantiate a `StatsPanel`.
        filter_name (str) is a valid query filter append to the anchor tag for each stat button.
        e.g. the `tenant` query parameter in the url `/circuits/circuits/?tenant=f4b48e9d-56fc-4090-afa5-dcbe69775b13`.
        related_models is a list of model classes and/or tuples of (model_class, query_string).
        e.g. [Device, Prefix, (Circuit, "circuit_terminations__location__in"), (VirtualMachine, "cluster__location__in")]
        """

        self.filter_name = filter_name
        self.related_models = related_models
        super().__init__(body_content_template_path=body_content_template_path, **kwargs)

    def should_render(self, context: Context):
        """Always should render this panel as the permission is reinforced in python with .restrict(request.user, "view")"""
        return True

    def render_body_content(self, context: Context):
        """
        Transform self.related_models to a dictionary with key, value pairs as follows:
        {
            <related_object_model_class_1>: [related_object_model_class_list_url_1, related_object_count_1, related_object_title_1],
            <related_object_model_class_2>: [related_object_model_class_list_url_2, related_object_count_2, related_object_title_2],
            <related_object_model_class_3>: [related_object_model_class_list_url_3, related_object_count_3, related_object_title_3],
            ...
        }
        """
        instance = get_obj_from_context(context)
        request = context["request"]
        if isinstance(instance, TreeModel):
            self.filter_pks = (
                instance.descendants(include_self=True).restrict(request.user, "view").values_list("pk", flat=True)
            )
        else:
            self.filter_pks = [instance.pk]

        if self.body_content_template_path:
            stats = {}
            if not self.related_models:
                return ""
            for related_field in self.related_models:
                if isinstance(related_field, tuple):
                    related_object_model_class, query = related_field
                else:
                    related_object_model_class, query = related_field, f"{self.filter_name}__in"
                filter_dict = {query: self.filter_pks}
                related_object_count = (
                    related_object_model_class.objects.restrict(request.user, "view").filter(**filter_dict).count()
                )
                related_object_model_class_meta = related_object_model_class._meta
                related_object_list_url = validated_viewname(related_object_model_class, "list")
                related_object_title = bettertitle(related_object_model_class_meta.verbose_name_plural)
                value = [related_object_list_url, related_object_count, related_object_title]
                stats[related_object_model_class] = value
                related_object_model_filterset = get_filterset_for_model(related_object_model_class)
                if self.filter_name not in related_object_model_filterset.get_filters():
                    raise FieldDoesNotExist(
                        f"{self.filter_name} is not a valid filter field for {related_object_model_class_meta.verbose_name}"
                    )

            return render_component_template(
                self.body_content_template_path, context, stats=stats, filter_name=self.filter_name
            )
        return ""


class _ObjectCustomFieldsPanel(GroupedKeyValueTablePanel):
    """A panel that renders a table of object custom fields."""

    def __init__(
        self,
        *,
        advanced_ui=False,
        weight=Panel.WEIGHT_CUSTOM_FIELDS_PANEL,
        label="Custom Fields",
        section=SectionChoices.LEFT_HALF,
        **kwargs,
    ):
        """Instantiate an `_ObjectCustomFieldsPanel`.

        Args:
            advanced_ui (bool): Whether this is on the "main" tab (False) or the "advanced" tab (True)
        """
        self.advanced_ui = advanced_ui
        super().__init__(
            data=None,
            body_id=f"custom_fields_{advanced_ui}",
            weight=weight,
            label=label,
            section=section,
            **kwargs,
        )

    def should_render(self, context: Context):
        """Render only if any custom fields are present."""
        obj = get_obj_from_context(context)
        if not hasattr(obj, "get_custom_field_groupings"):
            return False
        self.custom_field_data = obj.get_custom_field_groupings(advanced_ui=self.advanced_ui)
        return bool(self.custom_field_data)

    def get_data(self, context: Context):
        """Remap the response from `get_custom_field_groupings()` to a nested dict as expected by the parent class."""
        data = {}
        for grouping, entries in self.custom_field_data.items():
            data[grouping] = {entry[0]: entry[1] for entry in entries}
        return data

    def render_key(self, key, value, context: Context):
        """Render the custom field's description as well as its label."""
        return format_html('<span title="{}">{}</span>', key.description, key)

    def render_value(self, key, value, context: Context):
        """Render a given custom field value appropriately depending on what type of custom field it is."""
        cf = key
        if cf.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
            return render_boolean(value)
        elif cf.type == CustomFieldTypeChoices.TYPE_URL and value:
            return format_html('<a href="{}">{}</a>', value, truncatechars(value, 70))
        elif cf.type == CustomFieldTypeChoices.TYPE_MULTISELECT and value:
            return format_html_join(", ", "{}", ([v] for v in value))
        elif cf.type == CustomFieldTypeChoices.TYPE_MARKDOWN and value:
            return render_markdown(value)
        elif cf.type == CustomFieldTypeChoices.TYPE_JSON and value is not None:
            return format_html(
                """<p>
                    <button class="btn btn-xs btn-primary" type="button" data-toggle="collapse"
                            data-target="#cf_{field_key}" aria-expanded="false" aria-controls="cf_{field_key}">
                        Show/Hide
                    </button>
                </p>
                <pre class="collapse" id="cf_{field_key}">{rendered_value}</pre>""",
                field_key=cf.key,
                rendered_value=render_json(value),
            )
        elif value or value == 0:
            return format_html("{}", value)
        elif cf.required:
            return format_html('<span class="text-warning">Not defined</span>')
        return placeholder(value)


class _ObjectComputedFieldsPanel(GroupedKeyValueTablePanel):
    """A panel that renders a table of object computed field values."""

    def __init__(
        self,
        *,
        advanced_ui=False,
        weight=Panel.WEIGHT_COMPUTED_FIELDS_PANEL,
        label="Computed Fields",
        section=SectionChoices.LEFT_HALF,
        **kwargs,
    ):
        """Instantiate this panel.

        Args:
            advanced_ui (bool): Whether this is on the "main" tab (False) or the "advanced" tab (True)
        """
        self.advanced_ui = advanced_ui
        super().__init__(
            data=None,
            body_id=f"computed_fields_{advanced_ui}",
            weight=weight,
            label=label,
            section=section,
            **kwargs,
        )

    def should_render(self, context: Context):
        """Render only if any relevant computed fields are defined."""
        obj = get_obj_from_context(context)
        if not hasattr(obj, "get_computed_fields_grouping"):
            return False
        self.computed_fields_data = obj.get_computed_fields_grouping(advanced_ui=self.advanced_ui)
        return bool(self.computed_fields_data)

    def get_data(self, context: Context):
        """Remap `get_computed_fields_grouping()` to the nested dict format expected by the base class."""
        data = {}
        for grouping, entries in self.computed_fields_data.items():
            data[grouping] = {entry[0]: entry[1] for entry in entries}
        return data

    def render_key(self, key, value, context: Context):
        """Render the computed field's description as well as its label."""
        return format_html('<span title="{}">{}</span>', key.description, key)


class _ObjectRelationshipsPanel(KeyValueTablePanel):
    """A panel that renders a table of object "custom" relationships."""

    def __init__(
        self,
        *,
        advanced_ui=False,
        weight=Panel.WEIGHT_RELATIONSHIPS_PANEL,
        label="Relationships",
        section=SectionChoices.LEFT_HALF,
        **kwargs,
    ):
        """Instantiate this panel.

        Args:
            advanced_ui (bool): Whether this is on the "main" tab (False) or the "advanced" tab (True)
        """
        self.advanced_ui = advanced_ui
        super().__init__(data=None, weight=weight, label=label, section=section, **kwargs)

    def should_render(self, context: Context):
        """Render only if any relevant relationships are defined."""
        obj = get_obj_from_context(context)
        if not hasattr(obj, "get_relationships_with_related_objects"):
            return False
        self.relationships_data = obj.get_relationships_with_related_objects(
            advanced_ui=self.advanced_ui, include_hidden=False
        )
        return bool(
            self.relationships_data["source"]
            or self.relationships_data["destination"]
            or self.relationships_data["peer"]
        )

    def get_data(self, context: Context):
        """Remap `get_relationships_with_related_objects()` to the flat dict format expected by the base class."""
        data = {}
        for side, relationships in self.relationships_data.items():
            for relationship, value in relationships.items():
                key = (relationship, side)
                data[key] = value

        return data

    def render_key(self, key, value, context: Context):
        """Render the relationship's label and key as well as the related-objects label."""
        relationship, side = key
        return format_html(
            '<span title="{} ({})">{}</span>',
            relationship.label,
            relationship.key,
            bettertitle(relationship.get_label(side)),
        )

    def queryset_list_url_filter(self, key, value, context: Context):
        """Filter the list URL based on the given relationship key and side."""
        relationship, side = key
        obj = get_obj_from_context(context)
        return f"cr_{relationship.key}__{side}={obj.pk}"


class _ObjectTagsPanel(Panel):
    """Panel displaying an object's tags as a space-separated list of color-coded tag names."""

    def __init__(
        self,
        *,
        weight=Panel.WEIGHT_TAGS_PANEL,
        label="Tags",
        section=SectionChoices.LEFT_HALF,
        body_content_template_path="components/panel/body_content_tags.html",
        **kwargs,
    ):
        """Instantiate an `_ObjectTagsPanel`."""
        super().__init__(
            weight=weight,
            label=label,
            section=section,
            body_content_template_path=body_content_template_path,
            **kwargs,
        )

    def should_render(self, context: Context):
        return hasattr(get_obj_from_context(context), "tags")

    def get_extra_context(self, context: Context):
        obj = get_obj_from_context(context)
        return {
            "tags": obj.tags.all(),
            "list_url_name": validated_viewname(obj, "list"),
        }


class _ObjectCommentPanel(ObjectTextPanel):
    """Panel displaying an object's comments as a Markdown formatted panel."""

    def __init__(
        self,
        *,
        label="Comments",
        section=SectionChoices.LEFT_HALF,
        weight=Panel.WEIGHT_COMMENTS_PANEL,
        object_field="comments",
        **kwargs,
    ):
        super().__init__(
            weight=weight,
            label=label,
            section=section,
            object_field=object_field,
            **kwargs,
        )

    def should_render(self, context: Context):
        return hasattr(get_obj_from_context(context), "comments")


class _ObjectDetailMainTab(Tab):
    """Base class for a main display tab containing an overview of object fields and similar data."""

    def __init__(
        self,
        *,
        tab_id="main",
        label="",  # see render_label()
        weight=Tab.WEIGHT_MAIN_TAB,
        panels=(),
        **kwargs,
    ):
        panels = list(panels)
        # Inject standard panels (custom fields, relationships, tags, etc.) as appropriate
        panels.append(_ObjectCommentPanel())
        panels.append(_ObjectCustomFieldsPanel())
        panels.append(_ObjectComputedFieldsPanel())
        panels.append(_ObjectRelationshipsPanel())
        panels.append(_ObjectTagsPanel())

        super().__init__(tab_id=tab_id, label=label, weight=weight, panels=panels, **kwargs)

    def render_label(self, context: Context):
        """Use the `verbose_name` of the given instance's Model as the tab label by default."""
        return bettertitle(get_obj_from_context(context)._meta.verbose_name)


class _ObjectDataProvenancePanel(ObjectFieldsPanel):
    """Built-in class for a Panel displaying data provenance information on the Advanced tab."""

    def __init__(
        self,
        *,
        weight=150,
        label="Data Provenance",
        section=SectionChoices.LEFT_HALF,
        fields=("created", "last_updated", "created_by", "last_updated_by", "api_url"),
        ignore_nonexistent_fields=True,
        **kwargs,
    ):
        super().__init__(
            weight=weight,
            label=label,
            section=section,
            fields=fields,
            ignore_nonexistent_fields=ignore_nonexistent_fields,
            **kwargs,
        )

    def get_data(self, context: Context):
        data = super().get_data(context)
        # 3.0 TODO: instead of passing these around as context variables, just call
        # `get_created_and_last_updated_usernames_for_model(context[self.context_object_key])` right here?
        data["created_by"] = context["created_by"]
        data["last_updated_by"] = context["last_updated_by"]
        with contextlib.suppress(AttributeError):
            data["api_url"] = get_obj_from_context(context, self.context_object_key).get_absolute_url(api=True)
        return data

    def render_key(self, key, value, context: Context):
        if key == "api_url":
            return "View in API Browser"
        return super().render_key(key, value, context)

    def render_value(self, key, value, context: Context):
        if key == "api_url":
            return format_html('<a href="{}" target="_blank"><span class="mdi mdi-open-in-new"></span></a>', value)
        return super().render_value(key, value, context)


class _ObjectDetailAdvancedTab(Tab):
    """Built-in class for a Tab displaying "advanced" information such as PKs and data provenance."""

    def __init__(
        self,
        *,
        tab_id="advanced",
        label="Advanced",
        weight=Tab.WEIGHT_ADVANCED_TAB,
        panels=None,
        **kwargs,
    ):
        if not panels:
            panels = (
                ObjectFieldsPanel(
                    label="Object Details",
                    section=SectionChoices.LEFT_HALF,
                    weight=100,
                    fields=["id", "natural_slug", "slug"],
                    ignore_nonexistent_fields=True,
                ),
                _ObjectDataProvenancePanel(),
                _ObjectCustomFieldsPanel(advanced_ui=True),
                _ObjectComputedFieldsPanel(advanced_ui=True),
                _ObjectRelationshipsPanel(advanced_ui=True),
            )

        super().__init__(tab_id=tab_id, label=label, weight=weight, panels=panels, **kwargs)


class _ObjectDetailContactsTab(Tab):
    """Built-in class for a Tab displaying information about contact/team associations."""

    def __init__(
        self,
        *,
        tab_id="contacts",
        label="Contacts",
        weight=Tab.WEIGHT_CONTACTS_TAB,
        panels=None,
        **kwargs,
    ):
        if panels is None:
            panels = (
                ObjectsTablePanel(
                    weight=100,
                    table_class=AssociatedContactsTable,
                    table_attribute="associated_contacts",
                    related_field_name="assigned_object_id",
                    order_by_fields=["role__name"],
                    enable_bulk_actions=True,
                    max_display_count=100,  # since there isn't a separate list view for ContactAssociations!
                    # TODO: we should provide a standard reusable component template for bulk-actions in the footer
                    footer_content_template_path="components/panel/footer_contacts_table.html",
                    header_extra_content_template_path=None,
                ),
            )
        super().__init__(tab_id=tab_id, label=label, weight=weight, panels=panels, **kwargs)

    def should_render(self, context: Context):
        return getattr(get_obj_from_context(context), "is_contact_associable_model", False)

    def render_label(self, context: Context):
        return format_html(
            "{} {}",
            self.label,
            render_to_string(
                "utilities/templatetags/badge.html",
                badge(get_obj_from_context(context).associated_contacts.count(), True),
            ),
        )


@dataclass
class _ObjectDetailGroupsTab(Tab):
    """Built-in class for a Tab displaying information about associated dynamic groups."""

    def __init__(
        self,
        *,
        tab_id="dynamic_groups",
        label="Dynamic Groups",
        weight=Tab.WEIGHT_GROUPS_TAB,
        panels=None,
        **kwargs,
    ):
        if panels is None:
            panels = (
                ObjectsTablePanel(
                    weight=100,
                    table_class=DynamicGroupTable,
                    table_attribute="dynamic_groups",
                    exclude_columns=["content_type"],
                    add_button_route=None,
                    related_field_name="member_id",
                ),
            )
        super().__init__(tab_id=tab_id, label=label, weight=weight, panels=panels, **kwargs)

    def should_render(self, context: Context):
        obj = get_obj_from_context(context)
        return (
            getattr(obj, "is_dynamic_group_associable_model", False)
            and context["request"].user.has_perm("extras.view_dynamicgroup")
            and obj.dynamic_groups.exists()
        )

    def render_label(self, context: Context):
        return format_html(
            "{} {}",
            self.label,
            render_to_string(
                "utilities/templatetags/badge.html", badge(get_obj_from_context(context).dynamic_groups.count(), True)
            ),
        )


@dataclass
class _ObjectDetailMetadataTab(Tab):
    """Built-in class for a Tab displaying information about associated object metadata."""

    def __init__(
        self,
        *,
        tab_id="object_metadata",
        label="Object Metadata",
        weight=Tab.WEIGHT_METADATA_TAB,
        panels=None,
        **kwargs,
    ):
        if panels is None:
            panels = (
                ObjectsTablePanel(
                    weight=100,
                    table_class=ObjectMetadataTable,
                    table_attribute="associated_object_metadata",
                    order_by_fields=["metadata_type", "scoped_fields"],
                    exclude_columns=["assigned_object"],
                    add_button_route=None,
                    related_field_name="assigned_object_id",
                    header_extra_content_template_path=None,
                ),
            )
        super().__init__(tab_id=tab_id, label=label, weight=weight, panels=panels, **kwargs)

    def should_render(self, context: Context):
        obj = get_obj_from_context(context)
        return (
            getattr(obj, "is_metadata_associable_model", False)
            and context["request"].user.has_perm("extras.view_objectmetadata")
            and obj.associated_object_metadata.exists()
        )

    def render_label(self, context: Context):
        return format_html(
            "{} {}",
            self.label,
            render_to_string(
                "utilities/templatetags/badge.html",
                badge(get_obj_from_context(context).associated_object_metadata.count(), True),
            ),
        )
