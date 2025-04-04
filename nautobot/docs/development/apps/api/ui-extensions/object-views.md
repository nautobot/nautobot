# Extending Object Detail Views and Tabs

## Extending Object Detail Views

Apps can inject custom content into certain areas of the detail and list views of applicable models. This is accomplished by subclassing `TemplateExtension`, designating a particular Nautobot model, and defining the desired attributes and/or methods to provide custom content. Several attributes and methods are available:

* `object_detail_tabs` - List of `Tab` instances to add to the detail view as additional tabs.
* `object_detail_buttons` - List of `Button` instances to add to the detail view.
* `object_detail_panels` - List of `Panel` instances to add to the main tab of the detail view.
* `left_page()` - Inject content on the left side of the object detail page (deprecated since Nautobot 2.4.0; `object_detail_panels` is preferred)
* `right_page()` - Inject content on the right side of the object detail page (deprecated since Nautobot 2.4.0; `object_detail_panels` is preferred)
* `full_width_page()` - Inject content across the entire bottom of the object detail page (deprecated since Nautobot 2.4.0; `object_detail_panels` is preferred)
* `buttons()` - Add buttons to the top of the object detail page (deprecated since Nautobot 2.4.0; `object_detail_buttons` is preferred)
* `list_buttons()` - Add buttons to the object list page. This works in the same way as `buttons()` for the object detail page.
* `detail_tabs()` - Add extra tabs to the end of the list of tabs within the object detail page tabs navigation (deprecated since Nautobot 2.4.0; `object_detail_tabs` is preferred)

+++ 2.1.8 "`list_buttons()` support"
    Support for the `list_buttons()` method was added.

+/- 2.4.0 "`object_detail_tabs`, `object_detail_buttons`, `object_detail_panels` support, deprecation of some patterns"
    Support for the `object_detail_tabs`, `object_detail_buttons`, and `object_detail_panels` attributes was added. The `detail_tabs()`, `buttons()`, `left_page()`, `right_page()`, and `full_width_page()` methods were deprecated.

For details about the `Tab`, `Button`, and `Panel` classes and their subclasses, refer to the [relevant section of documentation](../../../../code-reference/nautobot/apps/ui.md) for full details. You may also find the [UI Component Framework documentation](../../../core/ui-component-framework.md) a useful reference as most of the concepts described therein apply to template extensions as well.

Declared subclasses should be gathered into a list or tuple for integration with Nautobot. By default, Nautobot looks for an iterable named `template_extensions` within a `template_content.py` file. (This can be overridden by setting `template_extensions` to a custom value on the app's `NautobotAppConfig`.)

### Additional Methods and the Render Context

In support of the method APIs described above, a `render()` method is available for convenience. This method accepts the name of a template to render, and any additional context data you want to pass. Its use is optional, however.

When a TemplateExtension is instantiated, context data is assigned to `self.context` for the method APIs to access as needed. Available data include:

* `object` - The object being viewed (note that this will be the model class when accessed in the context of `list_buttons()`)
* `request` - The current request
* `settings` - Global Nautobot settings
* `config` - App-specific configuration parameters

For example, accessing `{{ request.user }}` within a template will return the current user.

## Adding Detail Panels

### Via `object_detail_panels`

+++ 2.4.0

The `TemplateExtension.object_detail_panels` should be a list or tuple of Panel objects (as provided by the `nautobot.apps.ui` module). A variety of base classes are available; refer to the [relevant section of documentation](../../../../code-reference/nautobot/apps/ui.md) for full details. You may also find the [UI Component Framework documentation](../../../core/ui-component-framework.md) a useful reference as most of the concepts described therein apply to template extensions as well.

For example:

```python title="example_app/template_content.py"
from nautobot.apps.ui import ObjectTextPanel, SectionChoices, TemplateExtension


class CircuitContent(TemplateExtension):
    model = "circuits.circuit"

    object_detail_panels = (
        ObjectTextPanel(
            weight=100,
            label="Example App Text Panel",
            section=SectionChoices.LEFT_HALF,
            render_as=ObjectTextPanel.RenderOptions.CODE,
            object_field="description",
        ),
    )

template_extensions = [CircuitContent]
```

### Via the `*_page()` Methods (Deprecated)

The `left_page()`, `right_page()`, and `full_width_page()` methods each simply return a fragment of HTML. You are responsible for ensuring that the returned HTML is properly constructed and doesn't break the page layout and rendering.

## Adding Detail Tabs

### Via `object_detail_tabs`

+++ 2.4.0

The `TemplateExtension.object_detail_tabs` should be a list or tuple of Tab objects (as provided by the `nautobot.apps.ui` module). Two base classes are available:

* `Tab` - add a tab and its contents to the main object detail page, rendered inline with the rest of that page. Best used for quick-rendering content.
* `DistinctViewTab` - add a tab to the main object detail page that links to a distinct view of its own when clicked. Best used for more involved content.

For example:

```python title="example_app/template_content.py"
from nautobot.apps.ui import DistinctViewTab, Tab, TemplateExtension


class DeviceExtraTabs(TemplateExtension):
    model = "dcim.device"

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
            url_name="plugins:example_app:device_detail_tab_1",
        ),
    )


template_extensions = [DeviceExtraTabs]
```

Note that a `Tab` defines its contents directly (as `panels`) while the `DistinctViewTab` instead provides a `url_name` to the related URL that it should link against.

### Via `detail_tabs()` (Deprecated)

The `TemplateExtension.detail_tabs()` method should return a list of dicts, each of which has the keys `"title"` and `"url"`. In addition, in order for tabs to work properly:

* The `"url"` key should typically be a URL that includes `self.context["object"].pk` in some form (so that the URL may know which object is being referenced)
* The view referenced by the `"url"` must inherit from the `nautobot.apps.views.ObjectView` class
* The template rendered by this view must extend the object's detail template

For example:

```python title="example_app/template_content.py"
class DeviceExtraTabs(TemplateExtension):
    """Template extension to add extra tabs to the Device detail view."""
    model = "dcim.device"

    def detail_tabs(self):
        return [
            {
                "title": "App Tab 1",
                "url": reverse("plugins:example_app:device_detail_tab_1", kwargs={"pk": self.context["object"].pk}),
            },
        ]


template_extensions = [DeviceExtraTabs]
```

### Defining Distinct Tab Views

In either of the above cases, you would need to define a new view for the `device_detail_tab_1` tab to display, following a pattern similar to the below.

```html title="example_app/tab_device_detail_1.html"
{% extends 'dcim/device.html' %}

{% block content %}
    <h2>Device App Tab 1</h2>
    <p>I am some content for the Example App's device ({{ object.pk }}) detail tab 1.</p>
{% endblock %}
```

Here's a basic example of a tab's view

```python title="example_app/views.py"
from nautobot.apps.views import ObjectView
from nautobot.dcim.models import Device

class DeviceDetailAppTabOne(ObjectView):
    """
    This view's template extends the device detail template,
    making it suitable to show as a tab on the device detail page.

    Views that are intended to be for an object detail tab's content rendering must
    always inherit from nautobot.apps.views.ObjectView.
    """

    queryset = Device.objects.all()
    template_name = "example_app/tab_device_detail_1.html"
```

You must also add the view to the `url_patterns` like so (make sure to read the note after this code snippet):

```python title="example_app/urls.py"
from django.urls import path

from example_app import views

urlpatterns = [
    # ... previously defined urls
    path("devices/<uuid:pk>/example-app-tab-1/", views.DeviceDetailAppTabOne.as_view(), name="device_detail_tab_1"),
]
```

!!! note
    For added tab views, we recommend for consistency that you follow the URL pattern established by the base model detail view and tabs (if any). For example, `nautobot/dcim/urls.py` references Device tab views with the URL pattern `devices/<uuid:pk>/TAB-NAME/`, so above we have followed that same pattern.
