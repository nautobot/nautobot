from django.contrib import messages
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Count
from django.shortcuts import get_object_or_404, render

from utilities.views import BulkImportView, BulkEditView, BulkDeleteView, ObjectListView, ObjectAddView,\
    ObjectEditView, ObjectDeleteView

from .filters import CircuitFilter
from .forms import CircuitTypeForm, CircuitTypeBulkDeleteForm, CircuitForm, CircuitImportForm, CircuitBulkEditForm,\
    CircuitBulkDeleteForm, CircuitFilterForm, ProviderForm, ProviderImportForm, ProviderBulkEditForm,\
    ProviderBulkDeleteForm
from .models import Circuit, CircuitType, Provider
from .tables import CircuitTable, CircuitTypeTable, ProviderTable


#
# Providers
#

class ProviderListView(ObjectListView):
    queryset = Provider.objects.annotate(count_circuits=Count('circuits'))
    table = ProviderTable
    edit_permissions = ['circuits.change_provider', 'circuits.delete_provider']
    template_name = 'circuits/provider_list.html'


def provider(request, slug):

    provider = get_object_or_404(Provider, slug=slug)
    circuits = Circuit.objects.filter(provider=provider).select_related('site', 'interface__device')

    return render(request, 'circuits/provider.html', {
        'provider': provider,
        'circuits': circuits,
    })


class ProviderAddView(PermissionRequiredMixin, ObjectAddView):
    permission_required = 'circuits.add_provider'
    model = Provider
    form_class = ProviderForm
    template_name = 'circuits/provider_edit.html'
    cancel_url = 'circuits:provider_list'


class ProviderEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'circuits.change_provider'
    model = Provider
    form_class = ProviderForm
    template_name = 'circuits/provider_edit.html'


class ProviderDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'circuits.delete_provider'
    model = Provider
    redirect_url = 'circuits:provider_list'


class ProviderBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'circuits.add_provider'
    form = ProviderImportForm
    table = ProviderTable
    template_name = 'circuits/provider_import.html'
    obj_list_url = 'circuits:provider_list'


class ProviderBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'circuits.change_provider'
    cls = Provider
    form = ProviderBulkEditForm
    template_name = 'circuits/provider_bulk_edit.html'
    default_redirect_url = 'circuits:provider_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        for field in ['asn', 'account', 'portal_url', 'noc_contact', 'admin_contact', 'comments']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} providers".format(updated_count))


class ProviderBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'circuits.delete_provider'
    cls = Provider
    form = ProviderBulkDeleteForm
    default_redirect_url = 'circuits:provider_list'


#
# Circuit Types
#

class CircuitTypeListView(ObjectListView):
    queryset = CircuitType.objects.annotate(circuit_count=Count('circuits'))
    table = CircuitTypeTable
    edit_permissions = ['circuits.change_circuittype', 'circuits.delete_circuittype']
    template_name = 'circuits/circuittype_list.html'


class CircuitTypeAddView(PermissionRequiredMixin, ObjectAddView):
    permission_required = 'circuits.add_circuittype'
    model = CircuitType
    form_class = CircuitTypeForm
    cancel_url = 'circuits:circuittype_list'


class CircuitTypeEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'circuits.change_circuittype'
    model = CircuitType
    form_class = CircuitTypeForm
    return_url = 'circuits:circuittype_list'


class CircuitTypeBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'circuits.delete_circuittype'
    cls = CircuitType
    form = CircuitTypeBulkDeleteForm
    default_redirect_url = 'circuits:circuittype_list'


#
# Circuits
#

class CircuitListView(ObjectListView):
    queryset = Circuit.objects.select_related('provider', 'type', 'site')
    filter = CircuitFilter
    filter_form = CircuitFilterForm
    table = CircuitTable
    edit_permissions = ['circuits.change_circuit', 'circuits.delete_circuit']
    template_name = 'circuits/circuit_list.html'


def circuit(request, pk):

    circuit = get_object_or_404(Circuit, pk=pk)

    return render(request, 'circuits/circuit.html', {
        'circuit': circuit,
    })


class CircuitAddView(PermissionRequiredMixin, ObjectAddView):
    permission_required = 'circuits.add_circuit'
    model = Circuit
    form_class = CircuitForm
    template_name = 'circuits/circuit_edit.html'
    cancel_url = 'circuits:circuit_list'
    fields_initial = ['site']


class CircuitEditView(PermissionRequiredMixin, ObjectEditView):
    permission_required = 'circuits.change_circuit'
    model = Circuit
    form_class = CircuitForm
    template_name = 'circuits/circuit_edit.html'


class CircuitDeleteView(PermissionRequiredMixin, ObjectDeleteView):
    permission_required = 'circuits.delete_circuit'
    model = Circuit
    redirect_url = 'circuits:circuit_list'


class CircuitBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'circuits.add_circuit'
    form = CircuitImportForm
    table = CircuitTable
    template_name = 'circuits/circuit_import.html'
    obj_list_url = 'circuits:circuit_list'


class CircuitBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'circuits.change_circuit'
    cls = Circuit
    form = CircuitBulkEditForm
    template_name = 'circuits/circuit_bulk_edit.html'
    default_redirect_url = 'circuits:circuit_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        for field in ['type', 'provider', 'port_speed', 'commit_rate', 'comments']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} circuits".format(updated_count))


class CircuitBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'circuits.delete_circuit'
    cls = Circuit
    form = CircuitBulkDeleteForm
    default_redirect_url = 'circuits:circuit_list'
