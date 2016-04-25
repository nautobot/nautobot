from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from utilities.error_handlers import handle_protectederror
from utilities.forms import ConfirmationForm
from utilities.views import BulkImportView, BulkEditView, BulkDeleteView, ObjectListView

from .filters import CircuitFilter
from .forms import CircuitForm, CircuitImportForm, CircuitBulkEditForm, CircuitBulkDeleteForm, CircuitFilterForm, \
    ProviderForm, ProviderImportForm, ProviderBulkEditForm, ProviderBulkDeleteForm
from .models import Circuit, Provider
from .tables import CircuitTable, CircuitBulkEditTable, ProviderTable, ProviderBulkEditTable


#
# Providers
#

class ProviderListView(ObjectListView):
    queryset = Provider.objects.annotate(count_circuits=Count('circuits'))
    table = ProviderTable
    edit_table = ProviderBulkEditTable
    edit_table_permissions = ['circuits.change_provider', 'circuits.delete_provider']
    template_name = 'circuits/provider_list.html'


def provider(request, slug):

    provider = get_object_or_404(Provider, slug=slug)
    circuits = Circuit.objects.filter(provider=provider).select_related('site', 'interface__device')

    return render(request, 'circuits/provider.html', {
        'provider': provider,
        'circuits': circuits,
    })


@permission_required('circuits.add_provider')
def provider_add(request):

    if request.method == 'POST':
        form = ProviderForm(request.POST)
        if form.is_valid():
            provider = form.save()
            messages.success(request, "Added new provider: {0}".format(provider))
            if '_addanother' in request.POST:
                return redirect('circuits:provider_add')
            else:
                return redirect('circuits:provider', slug=provider.slug)

    else:
        form = ProviderForm()

    return render(request, 'circuits/provider_edit.html', {
        'form': form,
        'cancel_url': reverse('circuits:provider_list'),
    })


@permission_required('circuits.change_provider')
def provider_edit(request, slug):

    provider = get_object_or_404(Provider, slug=slug)

    if request.method == 'POST':
        form = ProviderForm(request.POST, instance=provider)
        if form.is_valid():
            provider = form.save()
            messages.success(request, "Modified provider {0}".format(provider))
            return redirect('circuits:provider', slug=provider.slug)

    else:
        form = ProviderForm(instance=provider)

    return render(request, 'circuits/provider_edit.html', {
        'provider': provider,
        'form': form,
        'cancel_url': reverse('circuits:provider', kwargs={'slug': provider.slug}),
    })


@permission_required('circuits.delete_provider')
def provider_delete(request, slug):

    provider = get_object_or_404(Provider, slug=slug)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                provider.delete()
                messages.success(request, "Provider {0} has been deleted".format(provider))
                return redirect('circuits:provider_list')
            except ProtectedError, e:
                handle_protectederror(provider, request, e)
                return redirect('circuits:provider', slug=provider.slug)

    else:
        form = ConfirmationForm()

    return render(request, 'circuits/provider_delete.html', {
        'provider': provider,
        'form': form,
        'cancel_url': reverse('circuits:provider', kwargs={'slug': provider.slug})
    })


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
    template_name = 'circuits/provider_bulk_delete.html'
    default_redirect_url = 'circuits:provider_list'


#
# Circuits
#

class CircuitListView(ObjectListView):
    queryset = Circuit.objects.select_related('provider', 'type', 'site')
    filter = CircuitFilter
    filter_form = CircuitFilterForm
    table = CircuitTable
    edit_table = CircuitBulkEditTable
    edit_table_permissions = ['circuits.change_circuit', 'circuits.delete_circuit']
    template_name = 'circuits/circuit_list.html'


def circuit(request, pk):

    circuit = get_object_or_404(Circuit, pk=pk)

    return render(request, 'circuits/circuit.html', {
        'circuit': circuit,
    })


@permission_required('circuits.add_circuit')
def circuit_add(request):

    if request.method == 'POST':
        form = CircuitForm(request.POST)
        if form.is_valid():
            circuit = form.save()
            messages.success(request, "Added new circuit: {0}".format(circuit))
            if '_addanother' in request.POST:
                return redirect('circuits:circuit_add')
            else:
                return redirect('circuits:circuit', pk=circuit.pk)

    else:
        form = CircuitForm(initial={
            'site': request.GET.get('site'),
        })

    return render(request, 'circuits/circuit_edit.html', {
        'form': form,
        'cancel_url': reverse('circuits:circuit_list'),
    })


@permission_required('circuits.change_circuit')
def circuit_edit(request, pk):

    circuit = get_object_or_404(Circuit, pk=pk)

    if request.method == 'POST':
        form = CircuitForm(request.POST, instance=circuit)
        if form.is_valid():
            circuit = form.save()
            messages.success(request, "Modified circuit {0}".format(circuit))
            return redirect('circuits:circuit', pk=circuit.pk)

    else:
        form = CircuitForm(instance=circuit)

    return render(request, 'circuits/circuit_edit.html', {
        'circuit': circuit,
        'form': form,
        'cancel_url': reverse('circuits:circuit', kwargs={'pk': circuit.pk}),
    })


@permission_required('circuits.delete_circuit')
def circuit_delete(request, pk):

    circuit = get_object_or_404(Circuit, pk=pk)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                circuit.delete()
                messages.success(request, "Circuit {0} has been deleted".format(circuit))
                return redirect('circuits:circuit_list')
            except ProtectedError, e:
                handle_protectederror(circuit, request, e)
                return redirect('circuits:circuit', pk=circuit.pk)

    else:
        form = ConfirmationForm()

    return render(request, 'circuits/circuit_delete.html', {
        'circuit': circuit,
        'form': form,
        'cancel_url': reverse('circuits:circuit', kwargs={'pk': circuit.pk})
    })


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
    template_name = 'circuits/circuit_bulk_delete.html'
    default_redirect_url = 'circuits:circuit_list'
