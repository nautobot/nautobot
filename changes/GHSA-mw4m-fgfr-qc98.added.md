Added `restrict_queryset()` to `nautobot.apps.models`, to restrict any queryset, including of users and groups, to the objects that a user has permission to act on.
Added `mock_wsgi_request()` to `nautobot.apps.utils`, to construct a minimal request, such as to carry a user, outside of handling an actual HTTP request.
