# Extending Object Detail Views and Tabs

## Extending Object Detail Views

Apps can inject custom content into certain areas of the detail views of applicable models. This is accomplished by subclassing `TemplateExtension`, designating a particular Nautobot model, and defining the desired methods to render custom content. Five methods are available:

* `left_page()` - Inject content on the left side of the page
* `right_page()` - Inject content on the right side of the page
* `full_width_page()` - Inject content across the entire bottom of the page
* `buttons()` - Add buttons to the top of the page
* `detail_tabs()` - Add extra tabs to the end of the list of tabs within the page tabs navigation

Additionally, a `render()` method is available for convenience. This method accepts the name of a template to render, and any additional context data you want to pass. Its use is optional, however.

When a TemplateExtension is instantiated, context data is assigned to `self.context`. Available data include:

* `object` - The object being viewed
* `request` - The current request
* `settings` - Global Nautobot settings
* `config` - App-specific configuration parameters

For example, accessing `{{ request.user }}` within a template will return the current user.

Declared subclasses should be gathered into a list or tuple for integration with Nautobot. By default, Nautobot looks for an iterable named `template_extensions` within a `template_content.py` file. (This can be overridden by setting `template_extensions` to a custom value on the app's `NautobotAppConfig`.) An example is [below](#example-adding-object-details-and-tabs).

## Adding Detail Tabs

+++ 1.4.0

The `TemplateExtension.detail_tabs()` method should return a list of dicts, each of which has the keys `"title"` and `"url"`. In addition, in order for tabs to work properly:

* The `"url"` key should typically be a URL that includes `self.context["object"].pk` in some form (so that the URL may know which object is being referenced)
* The view referenced by the `"url"` must inherit from the `nautobot.apps.views.ObjectView` class
* The template rendered by this view must extend the object's detail template

For example:

```python
class DeviceExtraTabs(TemplateExtension):
    """Template extension to add extra tabs to the Device detail view."""
    model = 'dcim.device'

    def detail_tabs(self):
        return [
            {
                "title": "App Tab 1",
                "url": reverse("plugins:example_plugin:device_detail_tab_1", kwargs={"pk": self.context["object"].pk}),
            },
        ]
```

```html
<!-- example_plugin/tab_device_detail_1.html -->
{% extends 'dcim/device.html' %}

{% block content %}
    <h2>Device App Tab 1</h2>
    <p>I am some content for the example plugin's device ({{ object.pk }}) detail tab 1.</p>
{% endblock %}
```

Here's a basic example of a tab's view

```python
# views.py
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
    template_name = "example_plugin/tab_device_detail_1.html"
```

You must also add the view to the `url_patterns` like so (make sure to read the note after this code snippet):

```python
# urls.py
from django.urls import path

from example_plugin import views

urlpatterns = [
    # ... previously defined urls
    path("devices/<uuid:pk>/example-plugin-tab-1/", views.DeviceDetailAppTabOne.as_view(), name="device_detail_tab_1"),
]
```

!!! note
    For added tab views, we recommend for consistency that you follow the URL pattern established by the base model detail view and tabs (if any). For example, `nautobot/dcim/urls.py` references Device tab views with the URL pattern `devices/<uuid:pk>/TAB-NAME/`, so above we have followed that same pattern.

## Example Adding Object Details and Tabs

```python
# template_content.py
from django.urls import reverse
from nautobot.apps.ui import TemplateExtension

from .models import Animal


class LocationAnimalCount(TemplateExtension):
    """Template extension to display animal count on the right side of the page."""

    model = 'dcim.location'

    def right_page(self):
        return self.render('nautobot_animal_sounds/inc/animal_count.html', extra_context={
            'animal_count': Animal.objects.count(),
        })


class DeviceExtraTabs(TemplateExtension):
    """Template extension to add extra tabs to the object detail tabs."""

    model = 'dcim.device'

    def detail_tabs(self):
        """
        You may define extra tabs to render on a model's detail page by utilizing this method.
        Each tab is defined as a dict in a list of dicts.

        For each of the tabs defined:
        - The <title> key's value will become the tab link's title.
        - The <url> key's value is used to render the HTML link for the tab

        These tabs will be visible (in this instance) on the Device model's detail page as
        set by the DeviceContent.model attribute "dcim.device"

        This example demonstrates defining two tabs. The tabs will be ordered by their position in list.
        """
        return [
            {
                "title": "App Tab 1",
                "url": reverse("plugins:example_plugin:device_detail_tab_1", kwargs={"pk": self.context["object"].pk}),
            },
            {
                "title": "App Tab 2",
                "url": reverse("plugins:example_plugin:device_detail_tab_2", kwargs={"pk": self.context["object"].pk}),
            },
        ]

template_extensions = [DeviceExtraTabs, LocationAnimalCount]
```
