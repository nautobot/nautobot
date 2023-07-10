# Registering URL Patterns

Finally, to make the view accessible to users, we need to register a URL for it. We do this in `urls.py` by defining a `urlpatterns` variable containing a list of paths.

```python
# urls.py
from django.urls import path

from . import views


urlpatterns = [
    path('random/', views.RandomAnimalView.as_view(), name='random_animal'),
]
```

A URL pattern has three components:

* `route` - The unique portion of the URL dedicated to this view
* `view` - The view itself
* `name` - A short name used to identify the URL path internally

This makes our view accessible at the URL `/plugins/animal-sounds/random/`. (Remember, our `AnimalSoundsConfig` class sets our app's base URL to `animal-sounds`.) Viewing this URL should show the base Nautobot template with our custom content inside it.

!!! tip
    As a next step, you would typically want to add links from the Nautobot UI to this view, either from the [navigation menu](../ui-extensions/navigation.md), the [Nautobot home page](../ui-extensions/home-page.md), and/or the [Installed Plugins view](../configuration-view.md).
