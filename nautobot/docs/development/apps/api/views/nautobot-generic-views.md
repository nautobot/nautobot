# Utilizing Nautobot Generic Views

+++ 1.1.0
    Via [PR #14](https://github.com/nautobot/nautobot/issues/14), some `generic` views have been exposed to help aid in plugin development. These views have some requirements that must be in place in order to work. These can be used by importing them from `from nautobot.core.views import generic`.

More documentation and examples can be found in [Generic Views](../../../core/generic-views.md) guide.

## Note URL Endpoint

+++ 1.4.0

Models that inherit from `PrimaryModel` and `OrganizationalModel` can have notes associated. In order to utilize this new feature you will need to add the endpoint to `urls.py`. Here is an option to be able to support both 1.4+ and older versions of Nautobot:

!!! tip
    This is only necessary if you are not using NautobotUIViewSet & NautobotUIViewSetRouter and wish to include Notes functionality.

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
