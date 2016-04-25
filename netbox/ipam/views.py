from netaddr import IPSet

from django_tables2 import RequestConfig
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.core.urlresolvers import reverse
from django.db.models import ProtectedError
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import urlencode

from dcim.models import Device
from utilities.error_handlers import handle_protectederror
from utilities.forms import ConfirmationForm
from utilities.paginator import EnhancedPaginator
from utilities.views import BulkImportView, BulkEditView, BulkDeleteView, ObjectListView

from .filters import AggregateFilter, PrefixFilter, IPAddressFilter, VLANFilter, VRFFilter
from .forms import AggregateForm, AggregateImportForm, AggregateBulkEditForm, AggregateBulkDeleteForm, \
    AggregateFilterForm, PrefixForm, PrefixImportForm, PrefixBulkEditForm, PrefixBulkDeleteForm, PrefixFilterForm, \
    IPAddressForm, IPAddressImportForm, IPAddressBulkEditForm, IPAddressBulkDeleteForm, IPAddressFilterForm, VLANForm, \
    VLANImportForm, VLANBulkEditForm, VLANBulkDeleteForm, VRFForm, VRFImportForm, VRFBulkEditForm, VRFBulkDeleteForm, \
    VLANFilterForm
from .models import VRF, Aggregate, Prefix, VLAN
from .tables import AggregateTable, AggregateBulkEditTable, PrefixTable, PrefixBriefTable, PrefixBulkEditTable, \
    IPAddress, IPAddressBriefTable, IPAddressTable, IPAddressBulkEditTable, VLANTable, VLANBulkEditTable, VRFTable, \
    VRFBulkEditTable


def add_available_prefixes(parent, prefix_list):
    """
    Create fake Prefix objects for all unallocated space within a prefix.
    """

    # Find all unallocated space
    available_prefixes = IPSet(parent) ^ IPSet([p.prefix for p in prefix_list])
    available_prefixes = [Prefix(prefix=p) for p in available_prefixes.iter_cidrs()]

    # Concatenate and sort complete list of children
    prefix_list = list(prefix_list) + available_prefixes
    prefix_list.sort(key=lambda p: p.prefix)

    return prefix_list


#
# VRFs
#

class VRFListView(ObjectListView):
    queryset = VRF.objects.all()
    filter = VRFFilter
    table = VRFTable
    edit_table = VRFBulkEditTable
    edit_table_permissions = ['ipam.change_vrf', 'ipam.delete_vrf']
    template_name = 'ipam/vrf_list.html'


def vrf(request, pk):

    vrf = get_object_or_404(VRF.objects.all(), pk=pk)
    prefixes = Prefix.objects.filter(vrf=vrf)

    return render(request, 'ipam/vrf.html', {
        'vrf': vrf,
        'prefixes': prefixes,
    })


@permission_required('ipam.add_vrf')
def vrf_add(request):

    if request.method == 'POST':
        form = VRFForm(request.POST)
        if form.is_valid():
            vrf = form.save()
            messages.success(request, "Added new VRF: {0}".format(vrf))
            if '_addanother' in request.POST:
                return redirect('ipam:vrf_add')
            else:
                return redirect('ipam:vrf', pk=vrf.pk)

    else:
        form = VRFForm()

    return render(request, 'ipam/vrf_edit.html', {
        'form': form,
        'cancel_url': reverse('ipam:vrf_list'),
    })


@permission_required('ipam.change_vrf')
def vrf_edit(request, pk):

    vrf = get_object_or_404(VRF, pk=pk)

    if request.method == 'POST':
        form = VRFForm(request.POST, instance=vrf)
        if form.is_valid():
            vrf = form.save()
            messages.success(request, "Modified VRF {0}".format(vrf))
            return redirect('ipam:vrf', pk=vrf.pk)

    else:
        form = VRFForm(instance=vrf)

    return render(request, 'ipam/vrf_edit.html', {
        'vrf': vrf,
        'form': form,
        'cancel_url': reverse('ipam:vrf', kwargs={'pk': vrf.pk}),
    })


@permission_required('ipam.delete_vrf')
def vrf_delete(request, pk):

    vrf = get_object_or_404(VRF, pk=pk)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                vrf.delete()
                messages.success(request, "VRF {0} has been deleted".format(vrf))
                return redirect('ipam:vrf_list')
            except ProtectedError, e:
                handle_protectederror(vrf, request, e)
                return redirect('ipam:vrf', pk=vrf.pk)

    else:
        form = ConfirmationForm()

    return render(request, 'ipam/vrf_delete.html', {
        'vrf': vrf,
        'form': form,
        'cancel_url': reverse('ipam:vrf', kwargs={'pk': vrf.pk})
    })


class VRFBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'ipam.add_vrf'
    form = VRFImportForm
    table = VRFTable
    template_name = 'ipam/vrf_import.html'
    obj_list_url = 'ipam:vrf_list'


class VRFBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'ipam.change_vrf'
    cls = VRF
    form = VRFBulkEditForm
    template_name = 'ipam/vrf_bulk_edit.html'
    default_redirect_url = 'ipam:vrf_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        for field in ['description']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} VRFs".format(updated_count))


class VRFBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'ipam.delete_vrf'
    cls = VRF
    form = VRFBulkDeleteForm
    template_name = 'ipam/vrf_bulk_delete.html'
    default_redirect_url = 'ipam:vrf_list'


#
# Aggregates
#

class AggregateListView(ObjectListView):
    queryset = Aggregate.objects.select_related('rir').extra(select={
        'child_count': 'SELECT COUNT(*) FROM ipam_prefix WHERE ipam_prefix.prefix <<= ipam_aggregate.prefix',
    })
    filter = AggregateFilter
    filter_form = AggregateFilterForm
    table = AggregateTable
    edit_table = AggregateBulkEditTable
    edit_table_permissions = ['ipam.change_aggregate', 'ipam.delete_aggregate']
    template_name = 'ipam/aggregate_list.html'


def aggregate(request, pk):

    aggregate = get_object_or_404(Aggregate, pk=pk)

    # Find all child prefixes contained by this aggregate
    child_prefixes = Prefix.objects.filter(prefix__net_contained_or_equal=str(aggregate.prefix))\
        .select_related('site', 'status', 'role').annotate_depth(limit=0)
    child_prefixes = add_available_prefixes(aggregate.prefix, child_prefixes)

    if request.user.has_perm('ipam.change_prefix') or request.user.has_perm('ipam.delete_prefix'):
        prefix_table = PrefixBulkEditTable(child_prefixes)
    else:
        prefix_table = PrefixTable(child_prefixes)
    RequestConfig(request, paginate={'per_page': settings.PAGINATE_COUNT, 'klass': EnhancedPaginator})\
        .configure(prefix_table)

    return render(request, 'ipam/aggregate.html', {
        'aggregate': aggregate,
        'prefix_table': prefix_table,
    })


@permission_required('ipam.add_aggregate')
def aggregate_add(request):

    if request.method == 'POST':
        form = AggregateForm(request.POST)
        if form.is_valid():
            aggregate = form.save()
            messages.success(request, "Added new aggregate: {0}".format(aggregate.prefix))
            if '_addanother' in request.POST:
                return redirect('ipam:aggregate_add')
            else:
                return redirect('ipam:aggregate', pk=aggregate.pk)

    else:
        form = AggregateForm()

    return render(request, 'ipam/aggregate_edit.html', {
        'form': form,
        'cancel_url': reverse('ipam:aggregate_list'),
    })


@permission_required('ipam.change_aggregate')
def aggregate_edit(request, pk):

    aggregate = get_object_or_404(Aggregate, pk=pk)

    if request.method == 'POST':
        form = AggregateForm(request.POST, instance=aggregate)
        if form.is_valid():
            aggregate = form.save()
            messages.success(request, "Modified aggregate {0}".format(aggregate.prefix))
            return redirect('ipam:aggregate', pk=aggregate.pk)

    else:
        form = AggregateForm(instance=aggregate)

    return render(request, 'ipam/aggregate_edit.html', {
        'aggregate': aggregate,
        'form': form,
        'cancel_url': reverse('ipam:aggregate', kwargs={'pk': aggregate.pk}),
    })


@permission_required('ipam.delete_aggregate')
def aggregate_delete(request, pk):

    aggregate = get_object_or_404(Aggregate, pk=pk)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                aggregate.delete()
                messages.success(request, "Aggregate {0} has been deleted".format(aggregate))
                return redirect('ipam:aggregate_list')
            except ProtectedError, e:
                handle_protectederror(aggregate, request, e)
                return redirect('ipam:aggregate', pk=aggregate.pk)

    else:
        form = ConfirmationForm()

    return render(request, 'ipam/aggregate_delete.html', {
        'aggregate': aggregate,
        'form': form,
        'cancel_url': reverse('ipam:aggregate', kwargs={'pk': aggregate.pk})
    })


class AggregateBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'ipam.add_aggregate'
    form = AggregateImportForm
    table = AggregateTable
    template_name = 'ipam/aggregate_import.html'
    obj_list_url = 'ipam:aggregate_list'


class AggregateBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'ipam.change_aggregate'
    cls = Aggregate
    form = AggregateBulkEditForm
    template_name = 'ipam/aggregate_bulk_edit.html'
    default_redirect_url = 'ipam:aggregate_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        for field in ['rir', 'date_added', 'description']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} aggregates".format(updated_count))


class AggregateBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'ipam.delete_aggregate'
    cls = Aggregate
    form = AggregateBulkDeleteForm
    template_name = 'ipam/aggregate_bulk_delete.html'
    default_redirect_url = 'ipam:aggregate_list'


#
# Prefixes
#

class PrefixListView(ObjectListView):
    queryset = Prefix.objects.select_related('site', 'status', 'role')
    filter = PrefixFilter
    filter_form = PrefixFilterForm
    table = PrefixTable
    edit_table = PrefixBulkEditTable
    edit_table_permissions = ['ipam.change_prefix', 'ipam.delete_prefix']
    template_name = 'ipam/prefix_list.html'

    def alter_queryset(self, request):
        # Show only top-level prefixes by default (unless searching)
        limit = None if request.GET.get('expand') or request.GET.get('q') else 0
        return self.queryset.annotate_depth(limit=limit)


def prefix(request, pk):

    prefix = get_object_or_404(Prefix.objects.select_related('site', 'vlan', 'status', 'role'), pk=pk)

    try:
        aggregate = Aggregate.objects.get(prefix__net_contains_or_equals=str(prefix.prefix))
    except Aggregate.DoesNotExist:
        aggregate = None

    # Count child IP addresses
    ipaddress_count = IPAddress.objects.filter(address__net_contained_or_equal=str(prefix.prefix)).count()

    # Parent prefixes table
    parent_prefixes = Prefix.objects.filter(vrf=prefix.vrf, prefix__net_contains=str(prefix.prefix))\
        .select_related('site', 'status', 'role').annotate_depth()
    parent_prefix_table = PrefixBriefTable(parent_prefixes)

    # Duplicate prefixes table
    duplicate_prefixes = Prefix.objects.filter(vrf=prefix.vrf, prefix=str(prefix.prefix)).exclude(pk=prefix.pk)\
        .select_related('site', 'status', 'role')
    duplicate_prefix_table = PrefixBriefTable(duplicate_prefixes)

    # Child prefixes table
    child_prefixes = Prefix.objects.filter(vrf=prefix.vrf, prefix__net_contained=str(prefix.prefix))\
        .select_related('site', 'status', 'role').annotate_depth(limit=0)
    if child_prefixes:
        child_prefixes = add_available_prefixes(prefix.prefix, child_prefixes)
    if request.user.has_perm('ipam.change_prefix') or request.user.has_perm('ipam.delete_prefix'):
        child_prefix_table = PrefixBulkEditTable(child_prefixes)
    else:
        child_prefix_table = PrefixTable(child_prefixes)
    RequestConfig(request, paginate={'per_page': settings.PAGINATE_COUNT, 'klass': EnhancedPaginator})\
        .configure(child_prefix_table)

    return render(request, 'ipam/prefix.html', {
        'prefix': prefix,
        'aggregate': aggregate,
        'ipaddress_count': ipaddress_count,
        'parent_prefix_table': parent_prefix_table,
        'child_prefix_table': child_prefix_table,
        'duplicate_prefix_table': duplicate_prefix_table,
    })


@permission_required('ipam.add_prefix')
def prefix_add(request):

    if request.method == 'POST':
        form = PrefixForm(request.POST)
        if form.is_valid():
            prefix = form.save()
            messages.success(request, "Added new prefix: {0}".format(prefix.prefix))
            if '_addanother' in request.POST:
                return redirect('ipam:prefix_add')
            else:
                return redirect('ipam:prefix', pk=prefix.pk)

    else:
        form = PrefixForm(initial={
            'site': request.GET.get('site'),
            'vrf': request.GET.get('vrf'),
            'prefix': request.GET.get('prefix'),
        })

    return render(request, 'ipam/prefix_edit.html', {
        'form': form,
        'cancel_url': reverse('ipam:prefix_list'),
    })


@permission_required('ipam.change_prefix')
def prefix_edit(request, pk):

    prefix = get_object_or_404(Prefix, pk=pk)

    if request.method == 'POST':
        form = PrefixForm(request.POST, instance=prefix)
        if form.is_valid():
            prefix = form.save()
            messages.success(request, "Modified prefix {0}".format(prefix.prefix))
            return redirect('ipam:prefix', pk=prefix.pk)

    else:
        form = PrefixForm(instance=prefix)

    return render(request, 'ipam/prefix_edit.html', {
        'prefix': prefix,
        'form': form,
        'cancel_url': reverse('ipam:prefix', kwargs={'pk': prefix.pk}),
    })


@permission_required('ipam.delete_prefix')
def prefix_delete(request, pk):

    prefix = get_object_or_404(Prefix, pk=pk)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                prefix.delete()
                messages.success(request, "Prefix {0} has been deleted".format(prefix))
                return redirect('ipam:prefix_list')
            except ProtectedError, e:
                handle_protectederror(prefix, request, e)
                return redirect('ipam:prefix', pk=prefix.pk)

    else:
        form = ConfirmationForm()

    return render(request, 'ipam/prefix_delete.html', {
        'prefix': prefix,
        'form': form,
        'cancel_url': reverse('ipam:prefix', kwargs={'pk': prefix.pk})
    })


class PrefixBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'ipam.add_prefix'
    form = PrefixImportForm
    table = PrefixTable
    template_name = 'ipam/prefix_import.html'
    obj_list_url = 'ipam:prefix_list'


class PrefixBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'ipam.change_prefix'
    cls = Prefix
    form = PrefixBulkEditForm
    template_name = 'ipam/prefix_bulk_edit.html'
    default_redirect_url = 'ipam:prefix_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        if form.cleaned_data['vrf']:
            fields_to_update['vrf'] = form.cleaned_data['vrf']
        elif form.cleaned_data['vrf_global']:
            fields_to_update['vrf'] = None
        for field in ['site', 'status', 'role', 'description']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} prefixes".format(updated_count))


class PrefixBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'ipam.delete_prefix'
    cls = Prefix
    form = PrefixBulkDeleteForm
    template_name = 'ipam/prefix_bulk_delete.html'
    default_redirect_url = 'ipam:prefix_list'


def prefix_ipaddresses(request, pk):

    prefix = get_object_or_404(Prefix.objects.all(), pk=pk)

    # Find all IPAddresses belonging to this Prefix
    ipaddresses = IPAddress.objects.filter(address__net_contained_or_equal=str(prefix.prefix))\
        .select_related('vrf', 'interface__device', 'primary_for')

    if request.user.has_perm('ipam.change_ipaddress') or request.user.has_perm('ipam.delete_ipaddress'):
        ip_table = IPAddressBulkEditTable(ipaddresses)
    else:
        ip_table = IPAddressTable(ipaddresses)
    RequestConfig(request, paginate={'per_page': settings.PAGINATE_COUNT, 'klass': EnhancedPaginator})\
        .configure(ip_table)

    return render(request, 'ipam/prefix_ipaddresses.html', {
        'prefix': prefix,
        'ip_table': ip_table,
    })


#
# IP addresses
#

class IPAddressListView(ObjectListView):
    queryset = IPAddress.objects.select_related('vrf', 'interface__device', 'primary_for')
    filter = IPAddressFilter
    filter_form = IPAddressFilterForm
    table = IPAddressTable
    edit_table = IPAddressBulkEditTable
    edit_table_permissions = ['ipam.change_ipaddress', 'ipam.delete_ipaddress']
    template_name = 'ipam/ipaddress_list.html'


def ipaddress(request, pk):

    ipaddress = get_object_or_404(IPAddress.objects.select_related('interface__device'), pk=pk)

    parent_prefixes = Prefix.objects.filter(vrf=ipaddress.vrf, prefix__net_contains=str(ipaddress.address.ip))
    related_ips = IPAddress.objects.select_related('interface__device').exclude(pk=ipaddress.pk).filter(vrf=ipaddress.vrf, address__net_contained_or_equal=str(ipaddress.address))

    related_ips_table = IPAddressBriefTable(related_ips)
    RequestConfig(request, paginate={'per_page': settings.PAGINATE_COUNT, 'klass': EnhancedPaginator}).configure(related_ips_table)

    return render(request, 'ipam/ipaddress.html', {
        'ipaddress': ipaddress,
        'parent_prefixes': parent_prefixes,
        'related_ips_table': related_ips_table,
    })


@permission_required('ipam.add_ipaddress')
def ipaddress_add(request):

    if request.method == 'POST':
        form = IPAddressForm(request.POST)
        if form.is_valid():
            ipaddress = form.save()
            messages.success(request, "Created new IP Address: {0}".format(ipaddress))
            if '_addanother' in request.POST:
                return redirect('ipam:ipaddress_add')
            else:
                return redirect('ipam:ipaddress', pk=ipaddress.pk)

    else:
        form = IPAddressForm(initial={
            'ipaddress': request.GET.get('ipaddress', None),
        })

    return render(request, 'ipam/ipaddress_edit.html', {
        'form': form,
        'cancel_url': reverse('ipam:ipaddress_list'),
    })


@permission_required('ipam.change_ipaddress')
def ipaddress_edit(request, pk):

    ipaddress = get_object_or_404(IPAddress, pk=pk)

    if request.method == 'POST':
        form = IPAddressForm(request.POST, instance=ipaddress)
        if form.is_valid():
            ipaddress = form.save()
            messages.success(request, "Modified IP address {0}".format(ipaddress))
            return redirect('ipam:ipaddress', pk=ipaddress.pk)

    else:
        form = IPAddressForm(instance=ipaddress)

    return render(request, 'ipam/ipaddress_edit.html', {
        'ipaddress': ipaddress,
        'form': form,
        'cancel_url': reverse('ipam:ipaddress', kwargs={'pk': ipaddress.pk}),
    })


@permission_required('ipam.delete_ipaddress')
def ipaddress_delete(request, pk):

    ipaddress = get_object_or_404(IPAddress, pk=pk)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                ipaddress.delete()
                messages.success(request, "IP address {0} has been deleted".format(ipaddress))
                if ipaddress.interface:
                    return redirect('dcim:device', pk=ipaddress.interface.device.pk)
                else:
                    return redirect('ipam:ipaddress_list')
            except ProtectedError, e:
                handle_protectederror(ipaddress, request, e)
                return redirect('ipam:ipaddress', pk=ipaddress.pk)

    else:
        form = ConfirmationForm()

    # Upon cancellation, redirect to the assigned device if one exists
    if ipaddress.interface:
        cancel_url = reverse('dcim:device', kwargs={'pk': ipaddress.interface.device.pk})
    else:
        cancel_url = reverse('ipam:ipaddress_list')

    return render(request, 'ipam/ipaddress_delete.html', {
        'ipaddress': ipaddress,
        'form': form,
        'cancel_url': cancel_url,
    })


class IPAddressBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'ipam.add_ipaddress'
    form = IPAddressImportForm
    table = IPAddressTable
    template_name = 'ipam/ipaddress_import.html'
    obj_list_url = 'ipam:ipaddress_list'

    def save_obj(self, obj):
        obj.save()
        # Update primary IP for device if needed
        try:
            device = obj.primary_for
            device.primary_ip = obj
            device.save()
        except Device.DoesNotExist:
            pass


class IPAddressBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'ipam.change_ipaddress'
    cls = IPAddress
    form = IPAddressBulkEditForm
    template_name = 'ipam/ipaddress_bulk_edit.html'
    default_redirect_url = 'ipam:ipaddress_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        if form.cleaned_data['vrf']:
            fields_to_update['vrf'] = form.cleaned_data['vrf']
        elif form.cleaned_data['vrf_global']:
            fields_to_update['vrf'] = None
        for field in ['description']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} IP addresses".format(updated_count))


class IPAddressBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'ipam.delete_ipaddress'
    cls = IPAddress
    form = IPAddressBulkDeleteForm
    template_name = 'ipam/ipaddress_bulk_delete.html'
    default_redirect_url = 'ipam:ipaddress_list'


#
# VLANs
#

class VLANListView(ObjectListView):
    queryset = VLAN.objects.select_related('site', 'status', 'role')
    filter = VLANFilter
    filter_form = VLANFilterForm
    table = VLANTable
    edit_table = VLANBulkEditTable
    edit_table_permissions = ['ipam.change_vlan', 'ipam.delete_vlan']
    template_name = 'ipam/vlan_list.html'


def vlan(request, pk):

    vlan = get_object_or_404(VLAN.objects.select_related('site', 'status', 'role'), pk=pk)
    prefixes = Prefix.objects.filter(vlan=vlan)

    return render(request, 'ipam/vlan.html', {
        'vlan': vlan,
        'prefixes': prefixes,
    })


@permission_required('ipam.add_vlan')
def vlan_add(request):

    if request.method == 'POST':
        form = VLANForm(request.POST)
        if form.is_valid():
            vlan = form.save()
            messages.success(request, "Added new VLAN: {0}".format(vlan))
            if '_addanother' in request.POST:
                base_url = reverse('ipam:vlan_add')
                params = urlencode({
                    'site': vlan.site.pk,
                })
                return HttpResponseRedirect('{}?{}'.format(base_url, params))
            else:
                return redirect('ipam:vlan', pk=vlan.pk)

    else:
        form = VLANForm()

    return render(request, 'ipam/vlan_edit.html', {
        'form': form,
        'cancel_url': reverse('ipam:vlan_list'),
    })


@permission_required('ipam.change_vlan')
def vlan_edit(request, pk):

    vlan = get_object_or_404(VLAN, pk=pk)

    if request.method == 'POST':
        form = VLANForm(request.POST, instance=vlan)
        if form.is_valid():
            vlan = form.save()
            messages.success(request, "Modified VLAN {0}".format(vlan))
            return redirect('ipam:vlan', pk=vlan.pk)

    else:
        form = VLANForm(instance=vlan)

    return render(request, 'ipam/vlan_edit.html', {
        'vlan': vlan,
        'form': form,
        'cancel_url': reverse('ipam:vlan', kwargs={'pk': vlan.pk}),
    })


@permission_required('ipam.delete_vlan')
def vlan_delete(request, pk):

    vlan = get_object_or_404(VLAN, pk=pk)

    if request.method == 'POST':
        form = ConfirmationForm(request.POST)
        if form.is_valid():
            try:
                vlan.delete()
                messages.success(request, "VLAN {0} has been deleted".format(vlan))
                return redirect('ipam:vlan_list')
            except ProtectedError, e:
                handle_protectederror(vlan, request, e)
                return redirect('ipam:vlan', pk=vlan.pk)

    else:
        form = ConfirmationForm()

    return render(request, 'ipam/vlan_delete.html', {
        'vlan': vlan,
        'form': form,
        'cancel_url': reverse('ipam:vlan', kwargs={'pk': vlan.pk})
    })


class VLANBulkImportView(PermissionRequiredMixin, BulkImportView):
    permission_required = 'ipam.add_vlan'
    form = VLANImportForm
    table = VLANTable
    template_name = 'ipam/vlan_import.html'
    obj_list_url = 'ipam:vlan_list'


class VLANBulkEditView(PermissionRequiredMixin, BulkEditView):
    permission_required = 'ipam.change_vlan'
    cls = VLAN
    form = VLANBulkEditForm
    template_name = 'ipam/vlan_bulk_edit.html'
    default_redirect_url = 'ipam:vlan_list'

    def update_objects(self, pk_list, form):

        fields_to_update = {}
        for field in ['site', 'status', 'role']:
            if form.cleaned_data[field]:
                fields_to_update[field] = form.cleaned_data[field]

        updated_count = self.cls.objects.filter(pk__in=pk_list).update(**fields_to_update)
        messages.success(self.request, "Updated {} VLANs".format(updated_count))


class VLANBulkDeleteView(PermissionRequiredMixin, BulkDeleteView):
    permission_required = 'ipam.delete_vlan'
    cls = VLAN
    form = VLANBulkDeleteForm
    template_name = 'ipam/vlan_bulk_delete.html'
    default_redirect_url = 'ipam:vlan_list'
