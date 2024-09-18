"""Classes and utilities for defining an object detail view through a NautobotUIViewSet."""

from dataclasses import dataclass

from django.core.exceptions import FieldDoesNotExist
from django.db import models
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


class Component:
    def __init__(self, *, weight, **kwargs):
        self.weight = weight

    def should_render(self, context):
        return True


class Tab(Component):
    """Base class for UI framework definition of a single tabbed pane within an Object Detail (Object Retrieve) page."""

    def __init__(
        self,
        *,
        tab_id,
        tab_label,
        panels=(),
        layout=LayoutChoices.DEFAULT,
        tab_template_path="components/tab/tab.html",
        content_template_path="components/tab/content.html",
        **kwargs,
    ):
        self.tab_id = tab_id
        self.tab_label = tab_label
        self.panels = panels
        self.layout = layout
        self.tab_template_path = tab_template_path
        self.content_template_path = content_template_path
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
        return sorted((panel for panel in self.panels if panel.section == section), key=lambda panel: panel.weight)

    def render_tab(self, context):
        """Render the tab (as opposed to its contents) to HTML."""
        if not self.should_render(context):
            return ""

        # Two steps here because self.tab_label may be dependent on context being defined
        context = context.flatten()
        context.update(
            {
                "tab_id": self.tab_id,
                "tab_label": self.render_tab_label(context),
            }
        )

        return get_template(self.tab_template_path).render(context)

    def render_tab_label(self, context):
        return self.tab_label

    def render_content(self, context):
        """Render the tab contents to HTML."""
        if not self.should_render(context):
            return ""

        # Two steps here because self.tab_label may be dependent on context being defined
        context = context.flatten()
        context.update(
            {
                "tab_id": self.tab_id,
                "tab_label": self.render_tab_label(context),
                "include_plugin_content": self.tab_id == "main",
                "left_half_panels": self.panels_for_section(SectionChoices.LEFT_HALF),
                "right_half_panels": self.panels_for_section(SectionChoices.RIGHT_HALF),
                "full_width_panels": self.panels_for_section(SectionChoices.FULL_WIDTH),
            }
        )

        tab_content = get_template(self.LAYOUT_TEMPLATE_PATHS[self.layout]).render(context)

        return get_template(self.content_template_path).render({**context, "tab_content": tab_content})


class _ObjectDetailMainTab(Tab):
    """Base class for a main display tab containing an overview of object fields and similar data."""

    def __init__(
        self,
        *,
        tab_id="main",
        tab_label="",  # see render_tab_label()
        weight=Tab.WEIGHT_MAIN_TAB,
        **kwargs,
    ):
        # TODO: inject standard panels (custom fields, relationships, tags, etc.) even if kwargs["panels"] is customized
        super().__init__(tab_id=tab_id, tab_label=tab_label, weight=weight, **kwargs)

    def render_tab_label(self, context):
        """Use the `verbose_name` of the given instance's Model as the tab label by default."""
        return bettertitle(context["object"]._meta.verbose_name)


class Panel(Component):
    """Base class for defining an individual display panel within a Layout within a Tab."""

    def __init__(
        self,
        *,
        label="",
        section=SectionChoices.FULL_WIDTH,
        template_path="components/panel/panel.html",
        header_template_path="components/panel/header.html",
        body_template_path="components/panel/body_generic.html",
        content_template_path=None,
        footer_template_path="components/panel/footer.html",
        footer_template_string=None,
        **kwargs,
    ):
        self.label = label
        self.section = section
        self.template_path = template_path
        self.header_template_path = header_template_path
        self.body_template_path = body_template_path
        self.content_template_path = content_template_path
        self.footer_template_path = footer_template_path
        self.footer_template_string = footer_template_string
        super().__init__(**kwargs)

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


class ObjectsTablePanel(Panel):
    """A panel that renders a table of objects (typically related objects, rather than the main context object)."""

    def __init__(
        self,
        *,
        table_name,
        body_template_path="components/panel/body_table.html",
        content_template_path="components/panel/content_table.html",
        **kwargs,
    ):
        self.table_name = table_name
        super().__init__(body_template_path=body_template_path, content_template_path=content_template_path, **kwargs)

    def get_extra_context(self, context):
        return {"content_table": context[self.table_name]}


class KeyValueTablePanel(Panel):
    """A panel that displays a two-column table of keys and values."""

    body_template_path: str = "components/panel/body_key_value_table.html"
    hide_if_unset: tuple = ()
    value_transforms: dict = {}

    def __init__(
        self,
        *,
        data,
        hide_if_unset=(),
        value_transforms=None,
        body_template_path="components/panel/body_key_value_table.html",
        **kwargs,
    ):
        self.data = data
        self.hide_if_unset = hide_if_unset
        self.value_transforms = value_transforms or {}
        super().__init__(body_template_path=body_template_path, **kwargs)

    def get_data(self, context):
        return self.data

    def render_key(self, key, value, context):
        return bettertitle(key.replace("_", " "))

    def render_value(self, key, value, context):
        display = value
        if key in self.value_transforms:
            for transform in self.value_transforms[key]:
                display = transform(display)
        elif value is None:
            if key in self.hide_if_unset:
                display = ""
            else:
                display = placeholder(value)
        elif isinstance(value, models.Model):
            if hasattr(value, "color"):
                display = hyperlinked_object_with_color(value)
            else:
                display = hyperlinked_object(value)
            # TODO: render location hierarchy for Location objects

            if isinstance(value, Tenant) and value.tenant_group is not None:
                display = format_html("{} / {}", hyperlinked_object(value.tenant_group), display)
        elif isinstance(value, models.QuerySet):
            if not value.exists():
                display = placeholder(None)
            else:
                # Display up to 3 records as a list
                display = format_html("<ul>")
                for record in value[:3]:
                    display += format_html("<li>{}</li>", self.render_value(key, record, context))
                if value.count() > 3:
                    display += format_html("<li>...and {} more (total {})</li>", value.count() - 3, value.count())
                display += format_html("</ul>")
        else:
            display = placeholder(localize(value))
        # TODO: apply additional formatting such as JSON/Markdown rendering, etc.
        return display

    def render_content(self, context):
        data = self.get_data(context)

        if not data:
            return format_html('<tr><td colspan="2">{}</td></tr>', placeholder(data))

        result = format_html("")
        for key, value in data.items():
            key_display = self.render_key(key, value, context)
            value_display = self.render_value(key, value, context)
            if value_display:
                # TODO: add a copy button on hover to all display items
                result += format_html("<tr><td>{key}</td><td>{value}</td></tr>", key=key_display, value=value_display)

        return result


class ObjectFieldsPanel(KeyValueTablePanel):
    """A panel that renders a table of object instance attributes."""

    def __init__(
        self,
        *,
        fields="__all__",
        exclude_fields=(),
        context_object_key="object",
        ignore_nonexistent_fields=False,
        label=None,
        **kwargs,
    ):
        self.fields = fields
        self.exclude_fields = exclude_fields
        self.context_object_key = context_object_key
        self.ignore_nonexistent_fields = ignore_nonexistent_fields
        super().__init__(data=None, label=label, **kwargs)

    def render_label(self, context):
        if self.label is None:
            return bettertitle(context["object"]._meta.verbose_name)
        return super().render_label(context)

    def get_data(self, context):
        fields = self.fields
        instance = context.get(self.context_object_key, None)

        if instance is None:
            return {}

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

        data = {}
        for field_name in fields:
            if field_name in self.exclude_fields:
                continue
            try:
                field_value = getattr(instance, field_name)
            except AttributeError:
                if self.ignore_nonexistent_fields:
                    continue
                raise

            data[field_name] = field_value

        return data

    def render_key(self, key, value, context):
        instance = context.get(self.context_object_key, None)

        if instance is not None:
            try:
                field = instance._meta.get_field(key)
                return bettertitle(field.verbose_name)
            except FieldDoesNotExist:
                pass

        return super().render_key(key, value, context)


class _ObjectDetailAdvancedTab(Tab):
    """Built-in class for a Tab displaying "advanced" information such as PKs and data provenance."""

    def __init__(
        self,
        *,
        tab_id="advanced",
        tab_label="Advanced",
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
                ObjectFieldsPanel(
                    label="Data Provenance",
                    section=SectionChoices.LEFT_HALF,
                    weight=200,
                    fields=["created", "last_updated"],
                    ignore_nonexistent_fields=True,
                    # TODO add created_by/last_updated_by derived fields and link to REST API
                ),
                # TODO add advanced_ui custom fields and relationships
            )

        super().__init__(tab_id=tab_id, tab_label=tab_label, weight=weight, panels=panels, **kwargs)


class _ObjectDetailContactsTab(Tab):
    """Built-in class for a Tab displaying information about contact/team associations."""

    def __init__(
        self,
        *,
        tab_id="contacts",
        tab_label="Contacts",
        weight=Tab.WEIGHT_CONTACTS_TAB,
        panels=None,
        **kwargs,
    ):
        if panels is None:
            panels = (
                ObjectsTablePanel(
                    weight=100,
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
            )
        super().__init__(tab_id=tab_id, tab_label=tab_label, weight=weight, panels=panels, **kwargs)

    def should_render(self, context):
        return context["object"].is_contact_associable_model

    def render_tab_label(self, context):
        return format_html(
            "{} {}",
            self.tab_label,
            render_to_string("utilities/templatetags/badge.html", badge(context["object"].associated_contacts.count())),
        )


@dataclass
class _ObjectDetailGroupsTab(Tab):
    """Built-in class for a Tab displaying information about associated dynamic groups."""

    def __init__(
        self,
        *,
        tab_id="dynamic_groups",
        tab_label="Dynamic Groups",
        weight=Tab.WEIGHT_GROUPS_TAB,
        panels=None,
        **kwargs,
    ):
        if panels is None:
            panels = (ObjectsTablePanel(weight=100, table_name="associated_dynamic_groups_table"),)
        super().__init__(tab_id=tab_id, tab_label=tab_label, weight=weight, panels=panels, **kwargs)

    def should_render(self, context):
        return (
            context["object"].is_dynamic_group_associable_model
            and context["request"].user.has_perm("extras.view_dynamicgroup")
            and context["object"].dynamic_groups.exists()
        )

    def render_tab_label(self, context):
        return format_html(
            "{} {}",
            self.tab_label,
            render_to_string("utilities/templatetags/badge.html", badge(context["object"].dynamic_groups.count())),
        )


@dataclass
class _ObjectDetailMetadataTab(Tab):
    """Built-in class for a Tab displaying information about associated object metadata."""

    tab_id: str = "object_metadata"
    tab_label: str = "Object Metadata"
    weight: int = Tab.WEIGHT_METADATA_TAB
    panels: tuple = (ObjectsTablePanel(weight=100, table_name="associated_object_metadata_table"),)

    def should_render(self, context):
        return (
            context["object"].is_metadata_associable_model
            and context["request"].user.has_perm("extras.view_objectmetadata")
            and context["object"].associated_object_metadata.exists()
        )

    def render_tab_label(self, context):
        return format_html(
            "{} {}",
            self.tab_label,
            render_to_string(
                "utilities/templatetags/badge.html", badge(context["object"].associated_object_metadata.count())
            ),
        )
