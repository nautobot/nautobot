# Replacing Views

+++ 1.4.0

You may override any of the core or app views by providing an `override_views` `dict` in an app's `views.py` file.

To override a view, you must specify the view's fully qualified name as the `dict` key which consists of the app name followed by the view's name separated by a colon, for instance `dcim:device`. The `dict` value should be the overriding view function.

A simple example to override the device detail view:

```python
# views.py
from django.shortcuts import HttpResponse
from django.views import generic


class DeviceViewOverride(generic.View):
    def get(self, request, *args, **kwargs):
        return HttpResponse(("Hello world! I'm a view which "
                             "overrides the device object detail view."))


override_views = {
    "dcim:device": DeviceViewOverride.as_view(),
}
```
