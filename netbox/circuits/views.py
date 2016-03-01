from django_tables2 import RequestConfig

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse
from django.db.models import Count, ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from extras.models import ExportTemplate
from utilities.error_handlers import handle_protectederror
from utilities.forms import ConfirmationForm
from utilities.paginator import EnhancedPaginator
from utilities.views import BulkImportView, BulkEditView, BulkDeleteView

from .filters import CircuitFilter
from .forms import CircuitForm, CircuitImportForm, CircuitBulkEditForm, CircuitBulkDeleteForm, CircuitFilterForm, \
    ProviderForm, ProviderImportForm, ProviderBulkEditForm, ProviderBulkDeleteForm
from .models import Circuit, Provider
from .tables import CircuitTable, CircuitBulkEditTable, ProviderTable, ProviderBulkEditTable


#
# Providers
#

def provider_list(request):

    queryset = Provider.objects.annotate(count_circuits=Count('circuits'))

    # Export
    if 'export' in request.GET:
        et = get_object_or_404(ExportTemplate, content_type__model='provider', name=request.GET.get('export'))
        response = et.to_response(context_dict={'queryset': queryset}, filename='netbox_providers')
        return response

    if request.user.has_perm('circuits.change_provider') or request.user.has_perm('circuits.delete_provider'):
        provider_table = ProviderBulkEditTable(queryset)
    else:
        provider_table = ProviderTable(queryset)
    RequestConfig(request, paginate={'per_page': settings.PAGINATE_COUNT, 'klass': EnhancedPaginator}).configure(provider_table)

    export_templates = ExportTemplate.objects.filter(content_type__model='provider')

    return render(request, 'circuits/provider_list.html', {
        'provider_table': provider_table,
        'export_templates': export_templates,
    })


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
    redirect_url = 'circuits:provider_list'

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
    redirect_url = 'circuits:provider_list'


#
# Circuits
#

def circuit_list(request):

    queryset = Circuit.objects.select_related('provider', 'type', 'site')
    queryset = CircuitFilter(request.GET, queryset).qs

    # Export
    if 'export' in request.GET:
        et = get_object_or_404(ExportTemplate, content_type__model='circuit', name=request.GET.get('export'))
        response = et.to_response(context_dict={'queryset': queryset}, filename='netbox_circuits')
        return response

    if request.user.has_perm('circuits.change_circuit') or request.user.has_perm('circuits.delete_circuit'):
        circuit_table = CircuitBulkEditTable(queryset)
    else:
        circuit_table = CircuitTable(queryset)
    RequestConfig(request, paginate={'per_page': settings.PAGINATE_COUNT, 'klass': EnhancedPaginator}).configure(circuit_table)

    export_templates = ExportTemplate.objects.filter(content_type__model='circuit')

    return render(request, 'circuits/circuit_list.html', {
        'circuit_table': circuit_table,
        'export_templates': export_templates,
        'filter_form': CircuitFilterForm(request.GET, label_suffix=''),
    })


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
    redirect_url = 'circuits:circuit_list'

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
    redirect_url = 'circuits:circuit_list'
