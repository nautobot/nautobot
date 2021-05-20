from nautobot.core.views import generic

from .models import DummyModel
from . import filters, forms, tables


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
