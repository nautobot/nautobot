from django.shortcuts import render
from django.views.generic import View

from nautobot.core.views import generic

from dummy_plugin.models import DummyModel
from dummy_plugin import filters, forms, tables


class DummyPluginHomeView(View):

    def get(self, request):
        return render(request, "dummy_plugin/home.html")


class DummyPluginConfigView(View):

    def get(self, request):
        """Render the configuration page for this plugin.

        Just an example - in reality you'd want to use real config data here as appropriate to your plugin, if any.
        """
        form = forms.DummyPluginConfigForm({"magic_word": "frobozz", "maximum_velocity": 300000})
        return render(request, "dummy_plugin/config.html", {"form": form})

    def post(self, request):
        """Handle configuration changes for this plugin.

        Not actually implemented here.
        """
        form = forms.DummyPluginConfigForm({"magic_word": "frobozz", "maximum_velocity": 300000})
        return render(request, "dummy_plugin/config.html", {"form": form})


class DummyModelListView(generic.ObjectListView):
    """List `DummyModel` objects."""

    queryset = DummyModel.objects.all()
    filterset = filters.DummyModelFilterSet
    filterset_form = forms.DummyModelFilterForm
    table = tables.DummyModelTable


class DummyModelEditView(generic.ObjectEditView):
    """Edit a single `DummyModel` object."""

    queryset = DummyModel.objects.all()
    model_form = forms.DummyModelForm


class DummyModelBulkEditView(generic.BulkEditView):
    """Edit multiple `DummyModel` objects."""

    queryset = DummyModel.objects.all()
    table = tables.DummyModelTable
    form = forms.DummyModelBulkEditForm


class DummyModelBulkDeleteView(generic.BulkDeleteView):
    """Delete multiple `DummyModek` objects."""

    queryset = DummyModel.objects.all()
    table = tables.DummyModelTable


class DummyModelDeleteView(generic.ObjectDeleteView):
    """Delete a single `Dummy` object."""

    queryset = DummyModel.objects.all()


class DummyModelBulkImportView(generic.BulkImportView):
    """Bulk CSV import of multiple `Dummy` objects."""

    queryset = DummyModel.objects.all()
    model_form = forms.DummyModelCSVForm
    table = tables.DummyModelTable


class DummyModelView(generic.ObjectView):
    """Detail view for a single `Dummy` object."""

    queryset = DummyModel.objects.all()
