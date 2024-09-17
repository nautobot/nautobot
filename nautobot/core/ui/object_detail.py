"""Classes and utilities for defining an object detail view through a NautobotUIViewSet."""

from django.core.exceptions import FieldDoesNotExist
from django.shortcuts import render
from django.template import Context, Template
from django.template.loader import get_template, render_to_string
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


class Tab:
    """Base class for UI framework definition of a single tabbed pane within an Object Detail (Object Retrieve) page."""

    tab_id: str
    tab_label: str

    # Overridable by subclasses if desired, hence not defined as CONSTANT
    tab_template_path = "components/tab/tab.html"
    content_template_path = "components/tab/content.html"
    layout_template_paths = {
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

    def __init__(self, *, panels, weight, layout=LayoutChoices.DEFAULT):
        """
        Create a Tab containing the given panels and layout.

        Args:
            panels (list): List of `Panel` instances to include in this layout by default.
            weight (int): Influences order of the tabs within a page (lower weights appear first).
            layout (str): One of the LayoutChoices values from nautobot.core.ui.choices.
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

        # Two steps here because self.tab_label may be dependent on self.context being defined
        self.context = context.flatten()
        self.context.update(
            {
                "tab_id": self.tab_id,
                "tab_label": self.tab_label,
            }
        )

        return get_template(self.tab_template_path).render(self.context)

    def render_content(self, context):
        """Render the tab contents to HTML."""
        if not self.should_render(context):
            return ""

        # Two steps here because self.tab_label may be dependent on self.context being defined
        self.context = context.flatten()
        self.context.update(
            {
                "tab_id": self.tab_id,
                "tab_label": self.tab_label,
                "include_plugin_content": self.tab_id == "main",
                "left_half_panels": self.panels_for_section(SectionChoices.LEFT_HALF),
                "right_half_panels": self.panels_for_section(SectionChoices.RIGHT_HALF),
                "full_width_panels": self.panels_for_section(SectionChoices.FULL_WIDTH),
            }
        )

        tab_content = get_template(self.layout_template_paths[self.layout]).render(self.context)

        return get_template(self.content_template_path).render({**self.context, "tab_content": tab_content})


class _ObjectDetailMainTab(Tab):
    """Base class for a main display tab containing an overview of object fields and similar data."""

    tab_id = "main"

    def __init__(self, **kwargs):
        """Default to two-column layout at top (containing a left `ObjectFieldsPanel`) with full-width layout below."""
        kwargs.setdefault("weight", self.WEIGHT_MAIN_TAB)
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
        kwargs.setdefault("weight", self.WEIGHT_ADVANCED_TAB)
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
        kwargs.setdefault("weight", self.WEIGHT_CONTACTS_TAB)
        kwargs.setdefault(
            "panels",
            [
                ObjectsTablePanel(
                    table_name="associated_contacts_table",
                    # TODO: this is ugly - we should abstract this away and provide a standard way of including
                    # bulk actions and other buttons in the footer
                    footer_template_string="""\
{% load perms %}
{% with request.path|add:"?tab=contacts"|urlencode as return_url %}
    {% if perms.extras.change_contactassociation %}
        <button type="submit" name="_edit" formaction="{% url 'extras:contactassociation_bulk_edit' %}?return_url={{return_url}}" class="btn btn-warning btn-xs">
            <span class="mdi mdi-pencil" aria-hidden="true"></span> Edit
        </button>
    {% endif %}
    {% if perms.extras.delete_contactassociation %}
        <button type="submit" formaction="{% url 'extras:contactassociation_bulk_delete' %}?return_url={{return_url}}" class="btn btn-danger btn-xs">
            <span class="mdi mdi-trash-can-outline" aria-hidden="true"></span> Delete
        </button>
    {% endif %}
    {% if perms.extras.add_contactassociation %}
        <div class="pull-right">
            <a href="{% url 'extras:object_contact_team_assign' %}?return_url={{return_url}}&associated_object_id={{object.id}}&associated_object_type={{content_type.id}}" class="btn btn-primary btn-xs">
                <span class="mdi mdi-plus-thick" aria-hidden="true"></span> Add Contact
            </a>
        </div>
    {% endif %}
    <div class="clearfix"></div>
{% endwith %}
""",
                ),
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
        kwargs.setdefault("weight", self.WEIGHT_GROUPS_TAB)
        kwargs.setdefault("panels", [ObjectsTablePanel(table_name="associated_dynamic_groups_table")])
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
        kwargs.setdefault("weight", self.WEIGHT_METADATA_TAB)
        kwargs.setdefault("panels", [ObjectsTablePanel(table_name="associated_object_metadata_table")])
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


class Panel:
    """Abstract base class for defining an individual display panel within a Layout within a Tab."""

    # Overridable by subclasses if desired, hence not defined as CONSTANT
    template_path = "components/panel/panel.html"
    header_template_path = "components/panel/header.html"
    body_template_path = "components/panel/body_generic.html"
    content_template_path = None
    footer_template_path = "components/panel/footer.html"

    def __init__(
        self,
        *,
        label=None,
        weight=100,
        section=SectionChoices.FULL_WIDTH,
        content_template_path=None,
        footer_template_string=None,
    ):
        """
        Instantiate a Panel.

        Args:
            label (str): The label to display at the top of the panel.
            weight (int): Influences relative position of panels within a section. Lower weights are toward the top.
            section (str): One of the SectionChoices values in `nautobot.core.ui.choices`.
            content_template_path (str): Path to an HTML template to use to render the content within the panel body.
            footer_template_string (str): HTML template string to render into the panel footer.
        """
        self.label = label
        self.weight = weight
        if section not in SectionChoices.values():
            raise RuntimeError(f"Unknown section {section}")
        self.section = section
        if content_template_path:
            self.content_template_path = content_template_path
        self.footer_template_string = footer_template_string

    def should_render(self, context):
        return True

    def get_extra_context(self, context):
        return {}

    def render(self, context):
        if not self.should_render(context):
            return ""
        context = {**context.flatten(), **self.get_extra_context(context)}
        return get_template(self.template_path).render(
            {
                **context,
                "header": self.render_header(context),
                "body": self.render_body(context),
                "footer": self.render_footer(context),
            }
        )

    def render_label(self, context):
        return self.label

    def render_header(self, context):
        return get_template(self.header_template_path).render(
            {
                **context,
                "label": self.render_label(context),
                "extra_content": self.render_header_extra_content(context),
            }
        )

    def render_header_extra_content(self, context):
        return ""

    def render_body(self, context):
        return get_template(self.body_template_path).render(
            {
                **context,
                "content": self.render_content(context),
            }
        )

    def render_content(self, context):
        if self.content_template_path:
            return get_template(self.content_template_path).render(context)
        return ""

    def render_footer(self, context):
        return get_template(self.footer_template_path).render(
            {
                **context,
                "extra_content": self.render_footer_extra_content(context),
            }
        )

    def render_footer_extra_content(self, context):
        if self.footer_template_string:
            return Template(self.footer_template_string).render(Context(context))
        return ""


class TemplatePanel(Panel):
    """A panel that renders an arbitrary HTML template, either from a string or from a template file."""

    def __init__(self, *, template_string=None, template_path=None, **kwargs):
        if template_string is None and template_path is None:
            raise ValueError("Either template_string or template_path must be provided")
        if template_string is not None and template_path is not None:
            raise ValueError("template_string and template_path are mutually exclusive")
        self.template_string = template_string
        # TODO conflict with Panel.template_path: self.template_path = template_path
        super().__init__(**kwargs)

    def render_content(self, context):
        if self.template_string is not None:
            return Template(self.template_string).render(Context(context))
        return render(context["request"], self.template_path, context)


class ObjectsTablePanel(Panel):
    """A panel that renders a table of objects (typically related objects, rather than the main context object)."""

    body_template_path = "components/panel/body_table.html"

    def __init__(
        self,
        *,
        table_name,
        **kwargs,
    ):
        """
        Instantiate an ObjectsTablePanel.

        Args:
            table_name (str): The render context key under which the table in question will be found.
        """
        self.table_name = table_name
        kwargs.setdefault("content_template_path", "components/panel/content_table.html")
        super().__init__(**kwargs)

    def get_extra_context(self, context):
        return {"content_table": context[self.table_name]}


class KeyValueTablePanel(Panel):
    """A panel that displays a two-column table of keys and values."""

    body_template_path = "components/panel/body_key_value_table.html"


class ObjectFieldsPanel(KeyValueTablePanel):
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
