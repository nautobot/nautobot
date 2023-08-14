# Adding Extra Tabs

+++ 1.4.0

In order for any extra tabs to work properly, the `"url"` key must reference a view which inherits from the `nautobot.apps.views.ObjectView` class and the template must extend the object's detail template such as:

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
