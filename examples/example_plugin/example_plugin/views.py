from django.shortcuts import HttpResponse, render
from django.views.generic import View

from nautobot.core.views import generic, mixins as view_mixins
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.circuits.models import Circuit
from nautobot.dcim.models import Device

from example_plugin.models import AnotherExampleModel, ExampleModel
from example_plugin import filters, forms, tables
from example_plugin.api import serializers


class CircuitDetailPluginTabView(generic.ObjectView):
    """
    This view's template extends the circuit detail template,
    making it suitable to show as a tab on the circuit detail page.

    Views that are intended to be for an object detail tab's content rendering must
    always inherit from nautobot.core.views.generic.ObjectView.
    """

    queryset = Circuit.objects.all()
    template_name = "example_plugin/tab_circuit_detail.html"


class DeviceDetailPluginTabOneView(generic.ObjectView):
    """
    This view's template extends the device detail template,
    making it suitable to show as a tab on the device detail page.

    Views that are intended to be for an object detail tab's content rendering must
    always inherit from nautobot.core.views.generic.ObjectView.
    """

    queryset = Device.objects.all()
    template_name = "example_plugin/tab_device_detail_1.html"


class DeviceDetailPluginTabTwoView(generic.ObjectView):
    """
    Same as DeviceDetailPluginTabOneView view above but using a different template.
    """

    queryset = Device.objects.all()
    template_name = "example_plugin/tab_device_detail_2.html"


class ExamplePluginHomeView(View):
    def get(self, request):
        return render(request, "example_plugin/home.html")


class ExamplePluginConfigView(View):
    def get(self, request):
        """Render the configuration page for this plugin.

        Just an example - in reality you'd want to use real config data here as appropriate to your plugin, if any.
        """
        form = forms.ExamplePluginConfigForm({"magic_word": "frobozz", "maximum_velocity": 300000})
        return render(request, "example_plugin/config.html", {"form": form})

    def post(self, request):
        """Handle configuration changes for this plugin.

        Not actually implemented here.
        """
        form = forms.ExamplePluginConfigForm({"magic_word": "frobozz", "maximum_velocity": 300000})
        return render(request, "example_plugin/config.html", {"form": form})


class ExampleModelUIViewSet(NautobotUIViewSet):
    bulk_create_form_class = forms.ExampleModelCSVForm
    bulk_update_form_class = forms.ExampleModelBulkEditForm
    filterset_class = filters.ExampleModelFilterSet
    filterset_form_class = forms.ExampleModelFilterForm
    form_class = forms.ExampleModelForm
    lookup_field = "pk"
    queryset = ExampleModel.objects.all()
    serializer_class = serializers.ExampleModelSerializer
    table_class = tables.ExampleModelTable


# Example excluding the BulkUpdateViewSet
class AnotherExampleModelUIViewSet(
    view_mixins.ObjectBulkDestroyViewMixin,
    view_mixins.ObjectBulkUpdateViewMixin,
    view_mixins.ObjectChangeLogViewMixin,
    view_mixins.ObjectNotesViewMixin,
    view_mixins.ObjectDestroyViewMixin,
    view_mixins.ObjectDetailViewMixin,
    view_mixins.ObjectEditViewMixin,
    view_mixins.ObjectListViewMixin,
):
    action_buttons = ["add", "export"]
    bulk_update_form_class = forms.AnotherExampleModelBulkEditForm
    filterset_class = filters.AnotherExampleModelFilterSet
    filterset_form_class = forms.AnotherExampleModelFilterForm
    form_class = forms.AnotherExampleModelForm
    lookup_field = "pk"
    queryset = AnotherExampleModel.objects.all()
    serializer_class = serializers.AnotherExampleModelSerializer
    table_class = tables.AnotherExampleModelTable


class ViewToBeOverridden(generic.View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("I am a view in the example plugin which will be overridden by another plugin.")
