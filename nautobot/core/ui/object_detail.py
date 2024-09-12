"""Classes and utilities for defining an object detail view through a NautobotUIViewSet."""

from abc import ABC, abstractmethod

from django.core.exceptions import FieldDoesNotExist
from django.shortcuts import render
from django.template import Template
from django.template.loader import render_to_string
from django.templatetags.l10n import localize
from django.utils.html import format_html, format_html_join

from nautobot.core.templatetags.helpers import (
    badge,
    bettertitle,
    hyperlinked_object,
    hyperlinked_object_with_color,
    placeholder,
)
from nautobot.core.ui.choices import LayoutChoices, SectionChoices
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

    def __init__(self, *, panels=None, layout=LayoutChoices.DEFAULT, extra_tabs=None):
        """
        Create an ObjectDetailContent.

        Args:
            panels (list): List of `Panel` instances to include in this layout by default. Standard `extras` Panels
                (custom fields, relationships, etc.) do not need to be specified as they will be automatically included.
            layout (str): One of the LayoutChoices values from nautobot.core.ui.choices.
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
        self.tabs = tabs

    @property
    def tabs(self):
        return sorted(self._tabs, key=lambda tab: tab.weight)

    @tabs.setter
    def tabs(self, value):
        self._tabs = value

    def render_tabs(self, context):
        """Render the tabs (as opposed to their contents) for each of `self.tabs`."""
        return format_html_join("\n", "{}", ([tab.render_tab(context)] for tab in self.tabs))

    def render_content(self, context):
        """Render the tab content for each of `self.tabs`."""
        return format_html_join("\n", "{}", ([tab.render_content(context)] for tab in self.tabs))


class Tab(ABC):
    """Base class for UI framework definition of a single tabbed pane within an Object Detail (Object Retrieve) page."""

    tab_id: str
    tab_label: str

    def __init__(self, *, panels, layout=LayoutChoices.DEFAULT, weight=100):
        """
        Create a Tab containing the given panels and layout.

        Args:
            panels (list): List of `Panel` instances to include in this layout by default.
            layout (str): One of the LayoutChoices values from nautobot.core.ui.choices.
            weight (int): Influences order of the tabs within a page (lower weights appear first).
        """
        if layout not in LayoutChoices.values():
            raise RuntimeError(f"Unknown layout {layout}")
        self.layout = layout
        self.panels = panels
        self.weight = weight

    def panels_for_section(self, section):
        return sorted((panel for panel in self.panels if panel.section == section), key=lambda panel: panel.weight)

    def should_render(self, context):
        return True

    def render_tab(self, context):
        """Render the tab (as opposed to its contents) to HTML."""
        if not self.should_render(context):
            return ""

        self.context = context

        return format_html(
            """\
<li role="presentation"{active_class}>
    <a href="{url}#{tab_id}" onclick="switch_tab(this.href)" aria-controls="{tab_id}" role="tab" data-toggle="tab">
        {tab_label}
    </a>
</li>""",
            active_class=' class="active"' if context["request"].GET.get("tab", None) == self.tab_id else "",
            url=context["object"].get_absolute_url(),
            tab_id=self.tab_id,
            tab_label=self.tab_label,
        )

    def render_content(self, context):
        """Render the tab contents to HTML."""
        if not self.should_render(context):
            return ""

        self.context = context
        instance = context["object"]

        tab_content = None
        panel_data = {
            "left_half_panels": format_html_join(
                "\n", "{}", ([panel.render(context)] for panel in self.panels_for_section(SectionChoices.LEFT_HALF))
            ),
            "plugin_left_page": plugin_left_page(context, instance) if self.tab_id == "main" else "",
            "right_half_panels": format_html_join(
                "\n", "{}", ([panel.render(context)] for panel in self.panels_for_section(SectionChoices.RIGHT_HALF))
            ),
            "plugin_right_page": plugin_right_page(context, instance) if self.tab_id == "main" else "",
            "full_width_panels": format_html_join(
                "\n", "{}", ([panel.render(context)] for panel in self.panels_for_section(SectionChoices.FULL_WIDTH))
            ),
            "plugin_full_width_page": plugin_full_width_page(context, instance) if self.tab_id == "main" else "",
        }

        if self.layout == LayoutChoices.TWO_OVER_ONE:
            tab_content = format_html(
                """\
    <div class="row">
        <div class="col-md-6">
            {left_half_panels}
            {plugin_left_page}
        </div>
        <div class="col-md-6">
            {right_half_panels}
            {plugin_right_page}
        </div>
    </div>
    <div class="row">
        <div class="col-md-12">
            {full_width_panels}
            {plugin_full_width_page}
        </div>
    </div>""",
                **panel_data,
            )
        elif self.layout == LayoutChoices.ONE_OVER_TWO:
            tab_content = format_html(
                """\
    <div class="row">
        <div class="col-md-12">
            {full_width_panels}
            {plugin_full_width_page}
        </div>
    </div>
    <div class="row">
        <div class="col-md-6">
            {left_half_panels}
            {plugin_left_page}
        </div>
        <div class="col-md-6">
            {right_half_panels}
            {plugin_right_page}
        </div>
    </div>""",
                **panel_data,
            )

        return format_html(
            """\
<div id="{tab_id}" role="tabpanel" class="tab-pane {active_or_fade}">
    {tab_content}
</div>""",
            tab_id=self.tab_id,
            active_or_fade="active" if context["request"].GET.get("tab", None) == self.tab_id else "fade",
            tab_content=tab_content,
        )


class _ObjectDetailMainTab(Tab):
    """Base class for a main display tab containing an overview of object fields and similar data."""

    tab_id = "main"

    def __init__(self, **kwargs):
        """Default to two-column layout at top (containing a left `ObjectFieldsPanel`) with full-width layout below."""
        kwargs.setdefault("weight", 0)
        super().__init__(**kwargs)
        # TODO: inject standard panels (custom fields, relationships, tags, etc.) even if kwargs["panels"] is customized

    @property
    def tab_label(self):
        """Use the `verbose_name` of the given instance's Model as the tab label by default."""
        return bettertitle(self.context["object"]._meta.verbose_name)


class _ObjectDetailAdvancedTab(Tab):
    """Built-in class for a Tab displaying "advanced" information such as PKs and data provenance."""

    tab_id = "advanced"
    tab_label = "Advanced"

    def __init__(self, **kwargs):
        kwargs.setdefault("weight", 1000)
        kwargs.setdefault(
            "panels",
            [
                ObjectFieldsPanel(
                    label="Object Details",
                    section=SectionChoices.LEFT_HALF,
                    weight=100,
                    fields=["id", "natural_slug", "slug"],
                    ignore_nonexistent_fields=True,
                ),
                ObjectFieldsPanel(
                    label="Data Provenance",
                    section=SectionChoices.LEFT_HALF,
                    weight=200,
                    fields=["created", "last_updated"],
                    ignore_nonexistent_fields=True,
                    # TODO add created_by/last_updated_by derived fields and link to REST API
                ),
                # TODO add advanced_ui custom fields and relationships
            ],
        )
        super().__init__(**kwargs)


class _ObjectDetailContactsTab(Tab):
    """Built-in class for a Tab displaying information about contact/team associations."""

    tab_id = "contacts"

    def __init__(self, **kwargs):
        kwargs.setdefault("weight", 1100)
        kwargs.setdefault(
            "panels",
            [
                # TODO
                TemplatePanel(label="Contact Associations", template_string="Contact Associations Table"),
            ],
        )
        super().__init__(**kwargs)

    def should_render(self, context):
        return context["object"].is_contact_associable_model

    @property
    def tab_label(self):
        return format_html(
            "Contacts {}",
            render_to_string(
                "utilities/templatetags/badge.html", badge(self.context["object"].associated_contacts.count())
            ),
        )


class _ObjectDetailGroupsTab(Tab):
    """Built-in class for a Tab displaying information about associated dynamic groups."""

    tab_id = "dynamic_groups"

    def __init__(self, **kwargs):
        kwargs.setdefault("weight", 1200)
        kwargs.setdefault(
            "panels",
            [
                # TODO
                TemplatePanel(label="Dynamic Groups", template_string="Dynamic Groups Table"),
            ],
        )
        super().__init__(**kwargs)

    def should_render(self, context):
        return (
            context["object"].is_dynamic_group_associable_model
            and context["request"].user.has_perm("extras.view_dynamicgroup")
            and context["object"].dynamic_groups.exists()
        )

    @property
    def tab_label(self):
        return format_html(
            "Dynamic Groups {}",
            render_to_string("utilities/templatetags/badge.html", badge(self.context["object"].dynamic_groups.count())),
        )


class _ObjectDetailMetadataTab(Tab):
    """Built-in class for a Tab displaying information about associated object metadata."""

    tab_id = "object_metadata"

    def __init__(self, **kwargs):
        kwargs.setdefault("weight", 1300)
        kwargs.setdefault(
            "panels",
            [
                # TODO
                TemplatePanel(label="Object Metadata", template_string="Object Metadata Table"),
            ],
        )
        super().__init__(**kwargs)

    def should_render(self, context):
        return (
            context["object"].is_metadata_associable_model
            and context["request"].user.has_perm("extras.view_objectmetadata")
            and context["object"].associated_object_metadata.exists()
        )

    @property
    def tab_label(self):
        return format_html(
            "Object Metadata {}",
            render_to_string(
                "utilities/templatetags/badge.html", badge(self.context["object"].associated_object_metadata.count())
            ),
        )


class Panel(ABC):
    """Abstract base class for defining an individual display panel within a Layout within a Tab."""

    DEFAULT_CONTENT_WRAPPER = '<div class="panel-body">{}</div>'
    ATTR_TABLE_CONTENT_WRAPPER = '<table class="table table-hover panel-body attr-table">{}</table>'

    def __init__(self, *, label=None, weight=100, section=SectionChoices.FULL_WIDTH, content_wrapper=None):
        """
        Instantiate a Panel.

        Args:
            label (str): The label to display at the top of the panel.
            weight (int): Influences relative position of panels within a section. Lower weights are toward the top.
            section (str): One of the SectionChoices values in `nautobot.core.ui.choices`.
            content_wrapper (str): HTML format string to wrap the rendered content in.
                Defaults to `<div class="panel-body">{}</div>`.
        """
        self.label = label
        self.weight = weight
        if section not in SectionChoices.values():
            raise RuntimeError(f"Unknown section {section}")
        self.section = section
        self.content_wrapper = content_wrapper or self.DEFAULT_CONTENT_WRAPPER

    def render(self, context):
        return format_html(
            """\
<div class="panel panel-default">
    <div class="panel-heading"><strong>{label}</strong></div>
    {wrapped_content}
</div>""",
            label=self.render_label(context),
            wrapped_content=format_html(self.content_wrapper, self.render_content(context)),
        )

    def render_label(self, context):
        return self.label

    @abstractmethod
    def render_content(self, context): ...


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

    def render_content(self, context):
        if self.template_string is not None:
            return Template(self.template_string).render(context)
        return render(context["request"], self.template_path, context)


class ObjectFieldsPanel(Panel):
    """A panel that renders a table of object instance attributes."""

    def __init__(
        self,
        *,
        fields="__all__",
        exclude_fields=None,
        field_transforms=None,
        ignore_nonexistent_fields=False,
        **kwargs,
    ):
        """
        Instantiate an ObjectFieldsPanel.

        Args:
            fields (str, list): The string "__all__", or an ordered list of field names to display.
            exclude_fields (list): Optional list of field names to exclude from `__all__`.
            field_transforms (dict): A dict of `{field_name: [transform_functions]}` that can be used to customize the
                                     display string for any given field.
        """
        self.fields = fields
        self.exclude_fields = exclude_fields or []
        if self.exclude_fields and self.fields != "__all__":
            raise ValueError("exclude_fields can only be set in combination with fields='__all__'")
        self.field_transforms = field_transforms or {}
        self.ignore_nonexistent_fields = ignore_nonexistent_fields
        kwargs.setdefault("content_wrapper", self.ATTR_TABLE_CONTENT_WRAPPER)
        super().__init__(**kwargs)

    def render_label(self, context):
        if self.label is None:
            return bettertitle(context["object"]._meta.verbose_name)
        return super().render_label(context)

    def render_content(self, context):
        """Render the table rows corresponding to the specified fields, applying field_transforms as specified."""
        result = format_html("")
        fields = self.fields
        instance = context["object"]

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
            # TODO: apply a default ordering "smarter" than declaration order? Alphabetical? By field type?
            # TODO: allow model to specify an alternative field ordering?

        for field_name in fields:
            if field_name in self.exclude_fields:
                continue
            try:
                field = instance._meta.get_field(field_name)
                field_label = bettertitle(field.verbose_name)
                field_value = getattr(instance, field.name)
            except FieldDoesNotExist:
                try:
                    field_value = getattr(instance, field_name)
                except AttributeError:
                    if self.ignore_nonexistent_fields:
                        continue
                    raise
                field = None
                field_label = bettertitle(field_name.replace("_", " "))

            if field_name in self.field_transforms:
                field_display = field_value
                for transform in self.field_transforms[field_name]:
                    field_display = transform(field_display)
            elif getattr(field, "is_relation", False):
                if hasattr(field_value, "color"):
                    field_display = hyperlinked_object_with_color(field_value)
                else:
                    field_display = hyperlinked_object(field_value)

                if isinstance(field_value, Tenant) and field_value.tenant_group is not None:
                    field_display = format_html("{} / {}", hyperlinked_object(field_value.tenant_group), field_display)
            else:
                field_display = placeholder(localize(field_value))
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
