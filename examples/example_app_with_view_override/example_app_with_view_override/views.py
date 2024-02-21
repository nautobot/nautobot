"""Views for example_app_with_view_override."""

from django.shortcuts import HttpResponse
from django.views import generic


class ViewOverride(generic.View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("Hello world! I'm an overridden view.")


override_views = {
    "plugins:example_app:view_to_be_overridden": ViewOverride.as_view(),
}
