from django.shortcuts import HttpResponse, render
from django.views.generic import View

from nautobot.core.views import generic
from nautobot.circuits.models import Circuit
from nautobot.dcim.models import Device

from example_plugin.models import AnotherExampleModel, ExampleModel
from example_plugin import filters, forms, tables


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


class ExampleModelListView(generic.ObjectListView):
    """List `ExampleModel` objects."""

    queryset = ExampleModel.objects.all()
    filterset = filters.ExampleModelFilterSet
    filterset_form = forms.ExampleModelFilterForm
    table = tables.ExampleModelTable


class ExampleModelEditView(generic.ObjectEditView):
    """Edit a single `ExampleModel` object."""

    queryset = ExampleModel.objects.all()
    model_form = forms.ExampleModelForm


class ExampleModelBulkEditView(generic.BulkEditView):
    """Edit multiple `ExampleModel` objects."""

    queryset = ExampleModel.objects.all()
    table = tables.ExampleModelTable
    form = forms.ExampleModelBulkEditForm


class ExampleModelBulkDeleteView(generic.BulkDeleteView):
    """Delete multiple `ExampleModel` objects."""

    queryset = ExampleModel.objects.all()
    table = tables.ExampleModelTable


class ExampleModelDeleteView(generic.ObjectDeleteView):
    """Delete a single `ExampleModel` object."""

    queryset = ExampleModel.objects.all()


class ExampleModelBulkImportView(generic.BulkImportView):
    """Bulk CSV import of multiple `ExampleModel` objects."""

    queryset = ExampleModel.objects.all()
    model_form = forms.ExampleModelCSVForm
    table = tables.ExampleModelTable


class ExampleModelView(generic.ObjectView):
    """Detail view for a single `ExampleModel` object."""

    queryset = ExampleModel.objects.all()


class AnotherExampleModelListView(generic.ObjectListView):
    """List `AnotherExampleModel` objects."""

    queryset = AnotherExampleModel.objects.all()
    filterset = filters.AnotherExampleModelFilterSet
    filterset_form = forms.AnotherExampleModelFilterForm
    table = tables.AnotherExampleModelTable


class AnotherExampleModelEditView(generic.ObjectEditView):
    """Edit a single `AnotherExampleModel` object."""

    queryset = AnotherExampleModel.objects.all()
    model_form = forms.AnotherExampleModelForm


class AnotherExampleModelBulkEditView(generic.BulkEditView):
    """Edit multiple `AnotherExampleModel` objects."""

    queryset = AnotherExampleModel.objects.all()
    table = tables.AnotherExampleModelTable
    form = forms.AnotherExampleModelBulkEditForm


class AnotherExampleModelBulkDeleteView(generic.BulkDeleteView):
    """Delete multiple `AnotherExampleModel` objects."""

    queryset = AnotherExampleModel.objects.all()
    table = tables.AnotherExampleModelTable


class AnotherExampleModelDeleteView(generic.ObjectDeleteView):
    """Delete a single `AnotherExampleModel` object."""

    queryset = AnotherExampleModel.objects.all()


class AnotherExampleModelView(generic.ObjectView):
    """Detail view for a single `AnotherExampleModel` object."""

    queryset = AnotherExampleModel.objects.all()


class ViewToBeOverridden(generic.View):
    def get(self, request, *args, **kwargs):
        return HttpResponse("I am a view in the example plugin which will be overridden by another plugin.")
