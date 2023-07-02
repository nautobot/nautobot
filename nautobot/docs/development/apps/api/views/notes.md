# Note URL Endpoint

+++ 1.4.0

Models that inherit from `PrimaryModel` and `OrganizationalModel` can have notes associated. In order to utilize this new feature you will need to add the endpoint to `urls.py`. Here is an option to be able to support both 1.4+ and older versions of Nautobot:

```python

urlpatterns = [
    path('random/', views.RandomAnimalView.as_view(), name='random_animal'),
]

try:
    from nautobot.extras.views import ObjectNotesView
    urlpatterns.append(
        path(
            'random/<uuid:pk>/notes/),
            ObjectNotesView.as_view(),
            name="random_notes",
            kwargs={"model": Random},
        )
    )
except ImportError:
    pass
```
