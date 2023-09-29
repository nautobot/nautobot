# Adding Links to the Installed Apps View

+++ 1.2.0

It's common for many apps to provide an "app configuration" [view](views/index.md) used for interactive configuration of aspects of the app that don't necessarily need to be managed by a system administrator via `PLUGINS_CONFIG`. The `NautobotAppConfig` setting of `config_view_name` lets you provide the URL pattern name defined for this view, which will then be accessible via a button on the **Plugins -> Installed Plugins** UI view.

For example, if the `animal_sounds` app provides a configuration view, which is set up in `urls.py` as follows:

```python
# urls.py
from django.urls import path

from . import views

urlpatterns = [
    path("/configuration/", views.AnimalSoundsConfigView.as_view(), name="config"),
]
```

then in your `AnimalSoundsConfig` you could refer to the view by name:

```python
# __init__.py
from nautobot.apps import NautobotAppConfig

class AnimalSoundsConfig(NautobotAppConfig):
    # ...
    config_view_name = "plugins:animal_sounds:config"

config = AnimalSoundsConfig
```

and now the "Configuration" button that appears in the Installed Plugins table next to "Animal Sounds" will be a link to your configuration view.

Similarly, if your app provides an "app home" or "dashboard" view, you can provide a link for the "Home" button in the Installed Plugins table by defining `home_view_name` on your `NautobotAppConfig` class. This can also be done for documentation by defining `docs_view_name` on your `NautobotAppConfig` class.
