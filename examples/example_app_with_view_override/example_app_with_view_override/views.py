"""Views for example_app_with_view_override."""

from django.shortcuts import HttpResponse

from nautobot.apps.views import GenericView


class ViewOverride(GenericView):
    def get(self, request, *args, **kwargs):
        return HttpResponse("Hello world! I'm an overridden view.")


override_views = {
    "plugins:example_app:view_to_be_overridden": ViewOverride.as_view(),
}
