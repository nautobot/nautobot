"""Classes and utilities for defining an object detail view through a NautobotUIViewSet."""

from abc import ABC, abstractmethod

from django.conf import settings
from django.middleware import csrf
from django.shortcuts import render
from django.template import RequestContext, Template
from django.utils.html import format_html, format_html_join

from nautobot.core.templatetags.helpers import bettertitle, hyperlinked_object, hyperlinked_object_with_color, placeholder
from nautobot.extras.templatetags.plugins import plugin_full_width_page, plugin_left_page, plugin_right_page

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

    def __init__(self, tabs=None):
        if tabs is None:
            tabs = (ObjectDetailMainTab(),)
        tabs = list(tabs)
        # Inject "standard" tabs
        tabs.append(ObjectDetailAdvancedTab())
        # TODO: contacts, groups, object-metadata tabs
        self.tabs = tabs

    def render_tabs(self, request, instance):
        return format_html_join("\n", "{}", ([tab.render_tab(request, instance)] for tab in self.tabs))

    def render_content(self, request, instance):
        return format_html_join("\n", "{}", ([tab.render_content(request, instance)] for tab in self.tabs))


class Tab(ABC):

    tab_id: str
    tab_label: str

    def __init__(self, layouts=None):
        if layouts is None:
            layouts = []
        self.layouts = list(layouts)

    def render_tab(self, request, instance):
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

    tab_id = "main"

    @property
    def tab_label(self):
        return bettertitle(self.instance._meta.verbose_name)

    def __init__(self, layouts=None):
        if layouts is None:
            layouts = [
                LayoutTwoColumn(
                    left_panels=(
                        ObjectFieldsPanel(),
                    ),
                ),
                LayoutFullWidth(),
            ]
        # TODO: autoinject standard panels (custom fields, relationships, tags, etc.) even if layouts was customized
        super().__init__(layouts=layouts)


class ObjectDetailAdvancedTab(Tab):

    tab_id = "advanced"
    tab_label = "Advanced"

    def __init__(self):
        super().__init__(
            layouts=(
                LayoutTwoColumn(
                    include_template_extensions=False,
                    left_panels=(
                        TemplatePanel(label="Object Details", template_string="Object Details"),
                        TemplatePanel(label="Data Provenance", template_string="Data Provenance")
                    ),
                ),
                LayoutFullWidth(include_template_extensions=False),
            )
        )


class Layout(ABC):

    def __init__(self, *, include_template_extensions=True):
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

    def __init__(self, *, label=None):
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

    def __init__(self, *, fields="__all__", **kwargs):
        self.fields = fields
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
        result = format_html("")
        for field in instance._meta.get_fields():
            if not (self.fields == "__all__" or field.name in self.fields):
                continue
            if field.hidden or field.name.startswith("_"):
                continue
            if field.name in ("id", "created", "last_updated"):
                # Handled elsewhere in the detail view
                continue
            if field.is_relation and (field.many_to_many or field.one_to_many):
                continue

            field_name = bettertitle(field.verbose_name)
            field_value = getattr(instance, field.name)
            if field.is_relation:
                if hasattr(field_value, "color"):
                    field_value = hyperlinked_object_with_color(field_value)
                else:
                    field_value = hyperlinked_object(field_value)
            else:
                field_value = placeholder(field_value)
            # TODO: apply additional formatting such as JSON/Markdown rendering, etc.

            result += format_html(
                """<tr>
            <td>{field_name}</td>
            <td>{field_value}</td>
        </tr>""",
                field_name=field_name,
                field_value=field_value,
            )

        return result
