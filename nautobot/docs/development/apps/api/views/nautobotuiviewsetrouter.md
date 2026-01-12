# NautobotUIViewSetRouter

With `NautobotUIViewSet` as the base UI ViewSet for `YourAppModel`, it is required to register your urls with the help of `NautobotUIViewSetRouter`.

For a concrete example on how to use `NautobotUIViewSetRouter`, see `nautobot.circuits.urls`.

Below is a theoretical `urls.py` file for `YourAppModel`:

```python
from django.urls import path

from nautobot.apps.urls import NautobotUIViewSetRouter
from your_app import views


router = NautobotUIViewSetRouter()
router.register("yourappmodel", views.YourAppModelUIViewSet)

urlpatterns = [
    # Extra urls that do not follow the patterns of `NautobotUIViewSetRouter` go here.
    ...
    path(
        "yourappmodels/<uuid:pk>/ping/",
        PingView.as_view(),
        name="yourappmodel_ping",
        kwargs={"model": yourappmodel},
    ),
    path(
        "yourappmodels/<uuid:pk>/traceroute/",
        TracerouteView.as_view(),
        name="yourappmodel_traceroute",
        kwargs={"model": yourappmodel},
    ),
    ...
]
urlpatterns += router.urls
```
