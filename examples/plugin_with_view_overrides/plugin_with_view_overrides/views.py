"""Views for plugin_with_view_overrides."""

from django.shortcuts import HttpResponse
from nautobot.core.views import generic


class CircuitViewOverride(generic.View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("Hello world! I'm a view provided by a plugin to override the `circuits:circuit` view.")


class DeviceViewOverride(generic.View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("Hello world! I'm a view provided by a plugin to override the `dcim:device` view.")


override_views = {
    "dcim:device": DeviceViewOverride.as_view(),
    "circuits:circuit": CircuitViewOverride.as_view(),
}
