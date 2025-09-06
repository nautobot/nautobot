from django.urls import reverse

from nautobot.apps.ui import (
    BaseTextPanel,
    Button,
    ButtonColorChoices,
    DistinctViewTab,
    EChartsPanel,
    EChartsTypeChoices,
    ObjectFieldsPanel,
    ObjectTextPanel,
    SectionChoices,
    Tab,
    TemplateExtension,
)

from .echarts_data import tenant_related_objects_data


class CircuitContent(TemplateExtension):
    model = "circuits.circuit"

    #
    # Nautobot 2.4 and later preferred way of extending a detail view (in this case, Circuit view)
    # is to define a TemplateExtension with `object_detail_panels` and/or `object_detail_tabs` as in the example below.
    #

    object_detail_panels = (
        ObjectTextPanel(
            weight=100,
            label="Example App Text Panel",
            section=SectionChoices.LEFT_HALF,
            render_as=ObjectTextPanel.RenderOptions.CODE,
            object_field="description",
        ),
    )

    object_detail_tabs = (
        Tab(
            weight=100,
            tab_id="example_app_inline_tab",
            label="Example App Inline Tab",
            panels=[
                ObjectFieldsPanel(weight=100, fields="__all__"),
            ],
        ),
        DistinctViewTab(
            weight=200,
            tab_id="example_app_distinct_view_tab",
            label="Example App Distinct View Tab",
            url_name="plugins:example_app:circuit_detail_tab",
        ),
    )

    #
    # Old (deprecated) way to do things follows
    # See examples above for preferred (Nautobot 2.4+) approach using `object_detail_tabs` attribute
    #

    def detail_tabs(self):
        """
        You may define extra tabs to render on a model's detail page by utilizing this method.
        Each tab is defined as a dict in a list of dicts.

        For each of the tabs defined:
        - The <title> key's value will become the tab link's title.
        - The <url> key's value is used to render the HTML link for the tab.

        Since the `model` attribute of this class is set as "circuits.circuit",
        these tabs will be added to the Circuit model's detail page.

        This example demonstrates defining one tab.
        """
        return [
            {
                "title": "Example App Tab",
                "url": reverse("plugins:example_app:circuit_detail_tab", kwargs={"pk": self.context["object"].pk}),
            },
        ]


class DeviceContent(TemplateExtension):
    model = "dcim.device"

    #
    # Nautobot 2.4 and later preferred way of extending a detail view (in this case, Circuit view)
    # is to define a TemplateExtension with `object_detail_panels` and/or `object_detail_tabs` as in the example below.
    #

    object_detail_tabs = [
        DistinctViewTab(
            weight=100,
            tab_id="example_app_device_detail_tab_1",
            label="Example App Tab 1",
            url_name="plugins:example_app:device_detail_tab_1",
        ),
    ]

    #
    # Old (deprecated) way to do things follows
    # See examples above for preferred (Nautobot 2.4+) approach using `object_detail_tabs` attribute
    #

    def detail_tabs(self):
        """
        You may define extra tabs to render on a model's detail page by utilizing this method.
        Each tab is defined as a dict in a list of dicts.

        For each of the tabs defined:
        - The <title> key's value will become the tab link's title.
        - The <url> key's value is used to render the HTML link for the tab

        Since the `model` attribute of this class is set as "dcim.device",
        these tabs will be added to the Device model's detail page.

        This example demonstrates defining two tabs. The tabs will be ordered by their position in list.
        """
        return [
            {
                "title": "Example App Tab 2",
                "url": reverse("plugins:example_app:device_detail_tab_2", kwargs={"pk": self.context["object"].pk}),
            },
        ]


class HardCodedTextPanel(BaseTextPanel):
    """
    A text panel that just displays hard-coded text.

    Not generally *useful* (hence why it's not included in Nautobot core) but handy for purpose of illustration.
    """

    def __init__(self, *, value, **kwargs):
        self.value = value
        super().__init__(**kwargs)

    def get_value(self, context):
        return self.value


class LocationContent(TemplateExtension):
    model = "dcim.location"

    object_detail_panels = (
        HardCodedTextPanel(
            weight=100,
            section=SectionChoices.LEFT_HALF,
            label="App Injected Content - Left",
            value="Hello, world!",
        ),
        HardCodedTextPanel(
            weight=100,
            section=SectionChoices.RIGHT_HALF,
            label="App Injected Content - Right",
            value="Hi, everybody!",
        ),
        HardCodedTextPanel(
            weight=100,
            section=SectionChoices.FULL_WIDTH,
            label="App Injected Content - Full Width",
            value="Greetings, everyone!",
        ),
    )

    def buttons(self):
        return "APP INJECTED LOCATION CONTENT - BUTTONS"

    def list_buttons(self):
        return "LOCATION CONTENT - BUTTONS LIST"


class TenantContent(TemplateExtension):
    model = "tenancy.tenant"

    object_detail_panels = [
        EChartsPanel(
            section=SectionChoices.FULL_WIDTH,
            weight=100,
            label="EChart - Stats",
            chart_kwargs={
                "chart_type": EChartsTypeChoices.PIE,
                "header": "Stats by Tenant",
                "description": "Example chart with using context and queryset.",
                "legend": {"orient": "vertical", "right": 10, "top": "center"},
                "data": tenant_related_objects_data,
                "additional_config": {
                    "series": [
                        {
                            "avoidLabelOverlap": False,
                            "radius": ["40%", "70%"],
                            "itemStyle": {"borderRadius": 10, "borderColor": "#fff", "borderWidth": 2},
                            "label": {"show": False, "position": "center"},
                            "emphasis": {"label": {"show": True, "fontSize": 40, "fontWeight": "bold"}},
                            "labelLine": {"show": False},
                        }
                    ]
                },
            },
        )
    ]


class ExampleModelContent(TemplateExtension):
    """
    You can also use an app to extend other apps's views, or even (in this case) its *own* views.

    Why you'd want to do this to your own views I don't know but it is possible.
    """

    model = "example_app.examplemodel"
    template_name = "example_app/panel.html"

    object_detail_buttons = (
        Button(
            weight=100,
            label="Example App Button",
            color=ButtonColorChoices.BLUE,
            icon="mdi-information",
            attributes={"onClick": 'alert("I am from the example app template_extension.")'},
        ),
    )

    #
    # Old (deprecated) way to do things follows
    # See examples above for preferred (Nautobot 2.4+) approach using `object_detail_panels` attribute
    #

    def left_page(self):
        # You can use the render() method and pass it a template file and context to populate it.
        return self.render(
            self.template_name,
            extra_context={
                "panel_title": "Example App Left Page",
                "panel_body": "Now sliiiiide to the left... I'll show up after anything defined in the detail view template",
            },
        )

    def right_page(self):
        # You can also just send raw HTML.
        return """
        <div class="panel panel-default">
            <div class="panel-heading">
                <strong>Example App Right Page</strong>
            </div>
            <div class="panel-body">
                <span>Check me out! I'll show up after anything defined in the detail view template.</span>
            </div>
        </div>
        """

    def full_width_page(self):
        return self.render(
            self.template_name,
            extra_context={
                "panel_title": "Example App Full Width Page",
                "panel_body": "I'm a full width panel that shows up following other full-width panels defined in the detail view template.",
            },
        )


# Don't forget to register your template extensions!
template_extensions = [ExampleModelContent, LocationContent, CircuitContent, DeviceContent, TenantContent]
