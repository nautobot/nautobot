"""Classes and utilities for defining an object detail view through a NautobotUIViewSet."""

from abc import ABC, abstractmethod

from django.conf import settings
from django.middleware import csrf
from django.shortcuts import render
from django.template import RequestContext, Template
from django.template.loader import render_to_string
from django.utils.html import format_html, format_html_join

from nautobot.core.templatetags.helpers import badge, bettertitle, hyperlinked_object, hyperlinked_object_with_color, placeholder
from nautobot.extras.templatetags.plugins import plugin_full_width_page, plugin_left_page, plugin_right_page
from nautobot.tenancy.models import Tenant

# ObjectDetailContent
#  Tab ("Device")
#    LayoutLeftHalf
#      -- view-specific panels --
#      Panel ("Device")
#      Panel ("Management")
#      Panel ("Comments")
#      -- always-available panels --
#      Panel ("Custom Fields")
#      Panel ("Computed Fields")
#      Panel ("Relationships")
#      Panel ("Tags")
#    LayoutRightHalf
#      -- view-specific panels --
#      Panel ("Assigned VRFs")
#      Panel ("Services")
#      Panel ("Images")
#  -- always-available tabs --
#  Tab ("Advanced")
#    LayoutLeftHalf
#      -- always-available panels --
#      Panel ("Object Details")
#      Panel ("Data Provenance")
#  Tab ("Contacts")
#    LayoutFullWidth
#      Panel ("Contact Associations")
#  Tab ("Dynamic Groups")
#    LayoutFullWidth
#      Panel ("Dynamic Groups")
#  Tab ("Object Metadata")
#    LayoutFullWidth
#      Panel ("Object Metadata")

# ObjectDetailContent
#  Tab ("IP Address")
#    LayoutLeftHalf
#      Panel ("IP Address")
#      ...
#    LayoutRightHalf
#      Panel ("Operational Details")
#      Panel ("Parent Prefixes")
#    LayoutFullWidth
#      Panel ("Related IP Addresses")
#  ...

# ObjectDetailContent
#  Tab ("Location")
#    LayoutLeftHalf
#      Panel ("Location")
#      Panel ("Geographical Info")
#      ...
#    LayoutRightHalf
#      Panel ("Stats")
#      Panel ("Rack Groups")
#      Panel ("Images")
#    LayoutFullWidth
#      Panel ("Children")
#  ...

# ObjectDetailContent
#  Tab ("Tenant")
#    LayoutLeftHalf
#      Panel ("Tenant")
#      ...
#    LayoutRightHalf
#      Panel ("Stats")
#  ...


# A default detail view consists of:
# ObjectDetailContent:
#  Tab (model._meta.verbose_name|bettertitle)
#    LayoutLeftHalf
#      ObjectDetailsPanel(fields="__all__")
#      (additional panels provided by Extras and Apps)
#      ...
#    LayoutRightHalf (empty, extensible by Apps)
#    LayoutFullWidth (empty, extensible by Apps)
#  (additional tabs provided by Core, Extras, and Apps)


class ObjectDetailContent:
    """
    Base class for UI framework definition of the contents of an Object Detail (Object Retrieve) page.

    This currently defines the tabs and their contents, but currently does NOT define the page title, breadcrumbs, etc.
    """

    def __init__(self, tabs=None, detail_fields=None, field_transforms=None):
        """
        Create an ObjectDetailContent.

        Args:
            tabs (list): Optional list of `Tab` instances; if unset, the default `ObjectDetailMainTab` will be used.
                         Standard extras Tabs (advanced, contacts, dynamic-groups, metadata, etc.) do not need to be
                         specified as they will be automatically included regardless.
            detail_fields (dict): Optional dict of {panel_name: [list of object field names], ...}.
                                  This addresses the common case where a detail view doesn't care to define custom tabs,
                                  layouts, or panels, but wants some control over how the default `ObjectDetailMainTab`
                                  presents the object's fields in an ObjectFieldsPanel(s).
            field_transforms (dict): Optional dict of {field_name: [list of transform functions], ...}.
                                     This can be used to provide custom rendering of given field(s) within the automatic
                                     `ObjectDetailMainTab` class, for example `{"commit_rate": [humanize_speed]}`.
        """
        if tabs is None:
            tabs = [ObjectDetailMainTab()]
            if detail_fields is not None:
                tabs[0].layouts[0].left_panels = [
                    ObjectFieldsPanel(label=label, fields=fields, field_transforms=field_transforms)
                    for label, fields in detail_fields.items()
                ]

        tabs = list(tabs)
        # Inject "standard" tabs
        tabs.append(ObjectDetailAdvancedTab())
        tabs.append(ObjectDetailContactsTab())
        tabs.append(ObjectDetailGroupsTab())
        tabs.append(ObjectDetailMetadataTab())
        self.tabs = tabs

    def render_tabs(self, request, instance):
        """Render the tabs (as opposed to their contents) for each of `self.tabs`."""
        return format_html_join("\n", "{}", ([tab.render_tab(request, instance)] for tab in self.tabs))

    def render_content(self, request, instance):
        """Render the tab content for each of `self.tabs`."""
        return format_html_join("\n", "{}", ([tab.render_content(request, instance)] for tab in self.tabs))


class Tab(ABC):
    """Base class for UI framework definition of a single tabbed pane within an Object Detail (Object Retrieve) page."""

    tab_id: str
    tab_label: str

    def __init__(self, layouts=None):
        """
        Create a Tab containing the given layouts of data.

        Args:
            layouts (list): List of `Layout` instances contained in this tab.
        """
        if layouts is None:
            layouts = []
        self.layouts = list(layouts)

    def render_tab(self, request, instance):
        """Render the tab (as opposed to its contents) to HTML."""
        self.request = request
        self.instance = instance

        return format_html(
            """\
<li role="presentation"{active_class}>
    <a href="{url}#{tab_id}" onclick="switch_tab(this.href)" aria-controls="{tab_id}" role="tab" data-toggle="tab">
        {tab_label}
    </a>
</li>""",
            active_class=' class="active"' if request.GET.get("tab", None) == self.tab_id else "",
            url=instance.get_absolute_url(),
            tab_id=self.tab_id,
            tab_label=self.tab_label,
        )

    def render_content(self, request, instance):
        """Render the tab contents to HTML."""
        self.request = request
        self.instance = instance

        return format_html(
            """\
<div id="{tab_id}" role="tabpanel" class="tab-pane {active_or_fade}">
    {layouts}
</div>""",
            tab_id=self.tab_id,
            active_or_fade="active" if request.GET.get("tab", None) == self.tab_id else "fade",
            layouts=format_html_join("\n", "{}", ([layout.render(request, instance)] for layout in self.layouts)),
        )


class ObjectDetailMainTab(Tab):
    """Base class for a main display tab containing an overview of object fields and similar data."""

    tab_id = "main"

    @property
    def tab_label(self):
        """Use the `verbose_name` of the given instance's Model as the tab label by default."""
        return bettertitle(self.instance._meta.verbose_name)

    def __init__(self, layouts=None):
        """Default to two-column layout at top (containing a left `ObjectFieldsPanel`) with full-width layout below."""
        if layouts is None:
            layouts = [
                LayoutTwoColumn(
                    include_template_extensions=True,
                    left_panels=(
                        ObjectFieldsPanel(),
                    ),
                ),
                LayoutFullWidth(include_template_extensions=True),
            ]
        # TODO: autoinject standard panels (custom fields, relationships, tags, etc.) even if layouts was customized
        super().__init__(layouts=layouts)


class ObjectDetailAdvancedTab(Tab):
    """Built-in class for a Tab displaying "advanced" information such as PKs and data provenance."""

    tab_id = "advanced"
    tab_label = "Advanced"

    def __init__(self):
        super().__init__(
            layouts=(
                LayoutTwoColumn(
                    left_panels=(
                        # TODO
                        TemplatePanel(label="Object Details", template_string="Object Details"),
                        TemplatePanel(label="Data Provenance", template_string="Data Provenance")
                    ),
                ),
                LayoutFullWidth(),
            )
        )


class ObjectDetailContactsTab(Tab):
    """Built-in class for a Tab displaying information about contact/team associations."""

    tab_id = "contacts"

    def __init__(self):
        super().__init__(
            layouts=(
                LayoutFullWidth(
                    panels=(
                        # TODO
                        TemplatePanel(label="Contact Associations", template_string="Contact Associations Table"),
                    ),
                ),
            ),
        )

    def render_tab(self, request, instance):
        if not instance.is_contact_associable_model:
            return ""
        return super().render_tab(request, instance)

    def render_content(self, request, instance):
        if not instance.is_contact_associable_model:
            return ""
        return super().render_content(request, instance)

    @property
    def tab_label(self):
        return format_html(
            "Contacts {}",
            render_to_string("utilities/templatetags/badge.html", badge(self.instance.associated_contacts.count())),
        )


class ObjectDetailGroupsTab(Tab):
    """Built-in class for a Tab displaying information about associated dynamic groups."""

    tab_id = "dynamic_groups"

    def __init__(self):
        super().__init__(
            layouts=(
                LayoutFullWidth(
                    panels=(
                        # TODO
                        TemplatePanel(label="Dynamic Groups", template_string="Dynamic Groups Table"),
                    ),
                ),
            ),
        )

    def render_tab(self, request, instance):
        if not (
            instance.is_dynamic_group_associable_model
            and request.user.has_perm("extras.view_dynamicgroup")
            and instance.dynamic_groups.exists()
        ):
            return ""
        return super().render_tab(request, instance)

    def render_content(self, request, instance):
        if not (
            instance.is_dynamic_group_associable_model
            and request.user.has_perm("extras.view_dynamicgroup")
            and instance.dynamic_groups.exists()
        ):
            return ""
        return super().render_content(request, instance)

    @property
    def tab_label(self):
        return format_html(
            "Dynamic Groups {}",
            render_to_string("utilities/templatetags/badge.html", badge(self.instance.dynamic_groups.count())),
        )


class ObjectDetailMetadataTab(Tab):
    """Built-in class for a Tab displaying information about associated object metadata."""

    tab_id = "object_metadata"

    def __init__(self):
        super().__init__(
            layouts=(
                LayoutFullWidth(
                    panels=(
                        # TODO
                        TemplatePanel(label="Object Metadata", template_string="Object Metadata Table"),
                    ),
                ),
            ),
        )

    def render_tab(self, request, instance):
        if not (
            instance.is_metadata_associable_model
            and request.user.has_perm("extras.view_objectmetadata")
            and instance.associated_object_metadata.exists()
        ):
            return ""
        return super().render_tab(request, instance)

    def render_content(self, request, instance):
        if not (
            instance.is_metadata_associable_model
            and request.user.has_perm("extras.view_object_metadata")
            and instance.associated_object_metadata.exists()
        ):
            return ""
        return super().render_content(request, instance)

    @property
    def tab_label(self):
        return format_html(
            "Object Metadata {}",
            render_to_string(
                "utilities/templatetags/badge.html", badge(self.instance.associated_object_metadata.count())
            ),
        )


class Layout(ABC):
    """Abstract base class for defining a layout of content panels within a `Tab`."""

    def __init__(self, *, include_template_extensions=False):
        """Instantiate a Layout.

        Args:
            include_template_extensions (bool): If True, this layout will include any App-defined TemplateExtension
                                                content as a part of its rendering.
        """
        self.include_template_extensions = include_template_extensions

    def _request_context(self, request):
        return {
            "request": request,
            "settings": settings,
            "csrf_token": csrf.get_token(request),
            "perms": [],  # TODO!
        }

    @abstractmethod
    def render(self, request, instance):
        ...


class LayoutTwoColumn(Layout):
    """Layout class for two side-by-side columns of half-width content each."""

    def __init__(self, *, left_panels=None, right_panels=None, **kwargs):
        """Define a two-column layout with the given left column and right column of panels."""
        super().__init__(**kwargs)
        if left_panels is None:
            left_panels = []
        if right_panels is None:
            right_panels = []
        self.left_panels = list(left_panels)
        self.right_panels = list(right_panels)

    def render(self, request, instance):
        return format_html(
            """\
<div class="row">
    <div class="col-md-6">
        {left_panels}
        {plugin_left_page}
    </div>
    <div class="col-md-6">
        {right_panels}
        {plugin_right_page}
    </div>
</div>""",
            left_panels=format_html_join("\n", "{}", ([panel.render(request, instance)] for panel in self.left_panels)),
            right_panels=format_html_join("\n", "{}", ([panel.render(request, instance)] for panel in self.right_panels)),
            plugin_left_page=plugin_left_page(self._request_context(request), instance) if self.include_template_extensions else "",
            plugin_right_page=plugin_right_page(self._request_context(request), instance) if self.include_template_extensions else "",
        )


class LayoutFullWidth(Layout):
    """Layout class for full-width content."""

    def __init__(self, *, panels=None, **kwargs):
        """Define a full-width layout containing the given panels."""
        super().__init__(**kwargs)
        if panels is None:
            panels = []
        self.panels = list(panels)

    def render(self, request, instance):
        return format_html(
            """\
<div class="row">
    <div class="col-md-12">
        {panels}
        {plugin_full_width_page}
    </div>
</div>""",
            panels=format_html_join("\n", "{}", ([panel.render(request, instance)] for panel in self.panels)),
            plugin_full_width_page=plugin_full_width_page(self._request_context(request), instance) if self.include_template_extensions else "",
        )

class Panel(ABC):
    """Abstract base class for defining an individual display panel within a Layout within a Tab."""

    def __init__(self, *, label=None):
        """
        Instantiate a Panel.

        Args:
            label (str): The label to display at the top of the panel.
        """
        self.label = label

    def render(self, request, instance):
        return format_html(
            """\
<div class="panel panel-default">
    <div class="panel-heading">
        <strong>{label}</strong>
    </div>
    <div class="panel-body">
        {content}
    </div>
</div>""",
            label=self.render_label(request, instance),
            content=self.render_content(request, instance),
        )

    def render_label(self, request, instance):
        return self.label

    @abstractmethod
    def render_content(self, request, instance):
        pass


class TemplatePanel(Panel):
    """A panel that renders an arbitrary HTML template, either from a string or from a template file."""

    def __init__(self, *, template_string=None, template_path=None, **kwargs):
        if template_string is None and template_path is None:
            raise ValueError("Either template_string or template_path must be provided")
        if template_string is not None and template_path is not None:
            raise ValueError("template_string and template_path are mutually exclusive")
        self.template_string = template_string
        self.template_path = template_path
        super().__init__(**kwargs)

    def render_content(self, request, instance):
        if self.template_string is not None:
            return Template(self.template_string).render(RequestContext(request, {"object": instance}))
        return render(request, self.template_path, {"object": instance})


class ObjectFieldsPanel(Panel):
    """A panel that renders a table of object instance attributes."""

    def __init__(self, *, fields="__all__", field_transforms=None, **kwargs):
        """
        Instantiate an ObjectFieldsPanel.

        Args:
            fields (str, list): The string "__all__", or an ordered list of field names to display.
            field_transforms (dict): A dict of `{field_name: [transform_functions]}` that can be used to customize the
                                     display string for any given field.
        """
        self.fields = fields
        self.field_transforms = field_transforms or {}
        super().__init__(**kwargs)

    def render(self, request, instance):
        """Override Panel.render() to render an attr-table as the panel body."""
        return format_html(
            """\
<div class="panel panel-default">
    <div class="panel-heading">
        <strong>{label}</strong>
    </div>
    <table class="table table-hover panel-body attr-table">
        {content}
    </table>
</div>""",
            label=self.render_label(request, instance),
            content=self.render_content(request, instance),
        )

    def render_label(self, request, instance):
        if self.label is None:
            return bettertitle(instance._meta.verbose_name)
        return super().render_label(request, instance)

    def render_content(self, request, instance):
        """Render the table rows corresponding to the specified fields, applying field_transforms as specified."""
        result = format_html("")
        fields = self.fields

        if fields == "__all__":
            # Derive the list of fields from the instance, skipping certain fields by default.
            fields = []
            for field in instance._meta.get_fields():
                if field.hidden or field.name.startswith("_"):
                    continue
                if field.name in ("id", "created", "last_updated"):
                    # Handled elsewhere in the detail view
                    continue
                if field.is_relation and (field.many_to_many or field.one_to_many):
                    continue
                fields.append(field.name)

        for field_name in fields:
            field = instance._meta.get_field(field_name)
            field_label = bettertitle(field.verbose_name)
            field_value = getattr(instance, field.name)

            if field_name in self.field_transforms:
                field_display = field_value
                for transform in self.field_transforms[field_name]:
                    field_display = transform(field_display)
            elif field.is_relation:
                if hasattr(field_value, "color"):
                    field_display = hyperlinked_object_with_color(field_value)
                else:
                    field_display = hyperlinked_object(field_value)

                if isinstance(field_value, Tenant) and field_value.tenant_group is not None:
                    field_display = format_html("{} / {}", hyperlinked_object(field_value.tenant_group), field_display)
            else:
                field_display = placeholder(field_value)
            # TODO: apply additional formatting such as JSON/Markdown rendering, etc.

            # TODO: add a copy button on hover to all field_display items
            result += format_html(
                """<tr>
            <td>{field_label}</td>
            <td>{field_display}</td>
        </tr>""",
                field_label=field_label,
                field_display=field_display,
            )

        return result
