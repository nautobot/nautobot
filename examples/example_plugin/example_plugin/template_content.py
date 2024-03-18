from django.urls import reverse

from nautobot.apps.ui import TemplateExtension


class CircuitContent(TemplateExtension):
    model = "circuits.circuit"

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
                "url": reverse("plugins:example_plugin:circuit_detail_tab", kwargs={"pk": self.context["object"].pk}),
            },
        ]


class DeviceContent(TemplateExtension):
    model = "dcim.device"

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
                "title": "Example App Tab 1",
                "url": reverse("plugins:example_plugin:device_detail_tab_1", kwargs={"pk": self.context["object"].pk}),
            },
            {
                "title": "Example App Tab 2",
                "url": reverse("plugins:example_plugin:device_detail_tab_2", kwargs={"pk": self.context["object"].pk}),
            },
        ]

    def full_width_page(self):
        return """
            <div class="card card-default">
                <div class="card-header">
                    <strong>Plugin Full Width Page</strong>
                </div>
                <div class="card-body">
                    I am a teapot short and stout.
                </div>
            </div>
        """


class LocationContent(TemplateExtension):
    model = "dcim.location"

    def left_page(self):
        return "LOCATION CONTENT - LEFT PAGE"

    def right_page(self):
        return "LOCATION CONTENT - RIGHT PAGE"

    def full_width_page(self):
        return "LOCATION CONTENT - FULL WIDTH PAGE"

    def buttons(self):
        return "LOCATION CONTENT - BUTTONS"

    def list_buttons(self):
        return "LOCATION CONTENT - BUTTONS LIST"


class ExampleModelContent(TemplateExtension):
    model = "example_plugin.examplemodel"
    template_name = "example_plugin/panel.html"

    def left_page(self):
        # You can use the render() method and pass it a template file and
        # context to populate it.
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

    def buttons(self):
        return """
        <a href="#" onClick="alert('I am from the example app template_extension.')" class="btn btn-primary">
            <span class="mdi mdi-plus-thick" aria-hidden="true"></span>
            Example App Button
        </a>
        """


# Don't forget to register your template extensions!
template_extensions = [ExampleModelContent, LocationContent, CircuitContent, DeviceContent]
