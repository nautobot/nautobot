from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django_tables2 import RequestConfig

from nautobot.core.views import generic
from nautobot.dcim.models import Device
from nautobot.dcim.tables import DeviceTable
from nautobot.extras.views import ObjectConfigContextView
from nautobot.ipam.models import IPAddress, Service
from nautobot.ipam.tables import InterfaceIPAddressTable, InterfaceVLANTable
from nautobot.utilities.paginator import EnhancedPaginator, get_paginate_count
from nautobot.utilities.utils import count_related
from nautobot.utilities.utils import normalize_querydict
from . import filters, forms, tables
from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine, VMInterface


#
# Cluster types
#


class ClusterTypeListView(generic.ObjectListView):
    queryset = ClusterType.objects.annotate(cluster_count=count_related(Cluster, "type"))
    filterset = filters.ClusterTypeFilterSet
    table = tables.ClusterTypeTable


class ClusterTypeView(generic.ObjectView):
    queryset = ClusterType.objects.all()

    def get_extra_context(self, request, instance):

        # Clusters
        # v2 TODO(jathan): Replace prefetch_related with select_related
        clusters = (
            Cluster.objects.restrict(request.user, "view")
            .filter(type=instance)
            .prefetch_related("group", "site", "tenant")
        ).annotate(
            device_count=count_related(Device, "cluster"),
            vm_count=count_related(VirtualMachine, "cluster"),
        )

        cluster_table = tables.ClusterTable(clusters)
        cluster_table.columns.hide("type")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(cluster_table)

        return {
            "cluster_table": cluster_table,
        }


class ClusterTypeEditView(generic.ObjectEditView):
    queryset = ClusterType.objects.all()
    model_form = forms.ClusterTypeForm


class ClusterTypeDeleteView(generic.ObjectDeleteView):
    queryset = ClusterType.objects.all()


class ClusterTypeBulkImportView(generic.BulkImportView):
    queryset = ClusterType.objects.all()
    model_form = forms.ClusterTypeCSVForm
    table = tables.ClusterTypeTable


class ClusterTypeBulkDeleteView(generic.BulkDeleteView):
    queryset = ClusterType.objects.annotate(cluster_count=count_related(Cluster, "type"))
    table = tables.ClusterTypeTable


#
# Cluster groups
#


class ClusterGroupListView(generic.ObjectListView):
    queryset = ClusterGroup.objects.annotate(cluster_count=count_related(Cluster, "group"))
    filterset = filters.ClusterGroupFilterSet
    table = tables.ClusterGroupTable


class ClusterGroupView(generic.ObjectView):
    queryset = ClusterGroup.objects.all()

    def get_extra_context(self, request, instance):

        # Clusters
        # v2 TODO(jathan): Replace prefetch_related with select_related
        clusters = (
            Cluster.objects.restrict(request.user, "view")
            .filter(group=instance)
            .prefetch_related("type", "site", "tenant")
        ).annotate(
            device_count=count_related(Device, "cluster"),
            vm_count=count_related(VirtualMachine, "cluster"),
        )

        cluster_table = tables.ClusterTable(clusters)
        cluster_table.columns.hide("group")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(cluster_table)

        return {
            "cluster_table": cluster_table,
        }


class ClusterGroupEditView(generic.ObjectEditView):
    queryset = ClusterGroup.objects.all()
    model_form = forms.ClusterGroupForm


class ClusterGroupDeleteView(generic.ObjectDeleteView):
    queryset = ClusterGroup.objects.all()


class ClusterGroupBulkImportView(generic.BulkImportView):
    queryset = ClusterGroup.objects.all()
    model_form = forms.ClusterGroupCSVForm
    table = tables.ClusterGroupTable


class ClusterGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = ClusterGroup.objects.annotate(cluster_count=count_related(Cluster, "group"))
    table = tables.ClusterGroupTable


#
# Clusters
#


class ClusterListView(generic.ObjectListView):
    permission_required = "virtualization.view_cluster"
    queryset = Cluster.objects.annotate(
        device_count=count_related(Device, "cluster"),
        vm_count=count_related(VirtualMachine, "cluster"),
    )
    table = tables.ClusterTable
    filterset = filters.ClusterFilterSet
    filterset_form = forms.ClusterFilterForm


class ClusterView(generic.ObjectView):
    queryset = Cluster.objects.all()

    def get_extra_context(self, request, instance):
        # v2 TODO(jathan): Replace prefetch_related with select_related
        devices = (
            Device.objects.restrict(request.user, "view")
            .filter(cluster=instance)
            .prefetch_related("site", "rack", "tenant", "device_type__manufacturer")
        )
        device_table = DeviceTable(list(devices), orderable=False)
        if request.user.has_perm("virtualization.change_cluster"):
            device_table.columns.show("pk")

        return {
            "device_table": device_table,
        }


class ClusterEditView(generic.ObjectEditView):
    template_name = "virtualization/cluster_edit.html"
    queryset = Cluster.objects.all()
    model_form = forms.ClusterForm


class ClusterDeleteView(generic.ObjectDeleteView):
    queryset = Cluster.objects.all()


class ClusterBulkImportView(generic.BulkImportView):
    queryset = Cluster.objects.all()
    model_form = forms.ClusterCSVForm
    table = tables.ClusterTable


class ClusterBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Cluster.objects.prefetch_related("type", "group", "site")
    filterset = filters.ClusterFilterSet
    table = tables.ClusterTable
    form = forms.ClusterBulkEditForm


class ClusterBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = Cluster.objects.prefetch_related("type", "group", "site")
    filterset = filters.ClusterFilterSet
    table = tables.ClusterTable


class ClusterAddDevicesView(generic.ObjectEditView):
    queryset = Cluster.objects.all()
    form = forms.ClusterAddDevicesForm
    template_name = "virtualization/cluster_add_devices.html"

    def get(self, request, *args, **kwargs):
        cluster = get_object_or_404(self.queryset, pk=kwargs["pk"])
        form = self.form(cluster, initial=normalize_querydict(request.GET))

        return render(
            request,
            self.template_name,
            {
                "cluster": cluster,
                "form": form,
                "return_url": reverse("virtualization:cluster", kwargs={"pk": kwargs["pk"]}),
            },
        )

    def post(self, request, *args, **kwargs):
        cluster = get_object_or_404(self.queryset, pk=kwargs["pk"])
        form = self.form(cluster, request.POST)

        if form.is_valid():

            device_pks = form.cleaned_data["devices"]
            with transaction.atomic():

                # Assign the selected Devices to the Cluster
                for device in Device.objects.filter(pk__in=device_pks):
                    device.cluster = cluster
                    device.save()

            messages.success(
                request,
                f"Added {len(device_pks)} devices to cluster {cluster}",
            )
            return redirect(cluster.get_absolute_url())

        return render(
            request,
            self.template_name,
            {
                "cluster": cluster,
                "form": form,
                "return_url": cluster.get_absolute_url(),
            },
        )


class ClusterRemoveDevicesView(generic.ObjectEditView):
    queryset = Cluster.objects.all()
    form = forms.ClusterRemoveDevicesForm
    template_name = "generic/object_bulk_remove.html"

    def post(self, request, *args, **kwargs):

        cluster = get_object_or_404(self.queryset, pk=kwargs["pk"])

        if "_confirm" in request.POST:
            form = self.form(request.POST)
            if form.is_valid():

                device_pks = form.cleaned_data["pk"]
                with transaction.atomic():

                    # Remove the selected Devices from the Cluster
                    for device in Device.objects.filter(pk__in=device_pks):
                        device.cluster = None
                        device.save()

                messages.success(
                    request,
                    f"Removed {len(device_pks)} devices from cluster {cluster}",
                )
                return redirect(cluster.get_absolute_url())

        else:
            form = self.form(initial={"pk": request.POST.getlist("pk")})

        selected_objects = Device.objects.filter(pk__in=form.initial["pk"])
        device_table = DeviceTable(list(selected_objects), orderable=False)

        return render(
            request,
            self.template_name,
            {
                "form": form,
                "parent_obj": cluster,
                "table": device_table,
                "obj_type_plural": "devices",
                "return_url": cluster.get_absolute_url(),
            },
        )


#
# Virtual machines
#


class VirtualMachineListView(generic.ObjectListView):
    queryset = VirtualMachine.objects.all()
    filterset = filters.VirtualMachineFilterSet
    filterset_form = forms.VirtualMachineFilterForm
    table = tables.VirtualMachineDetailTable
    template_name = "virtualization/virtualmachine_list.html"


class VirtualMachineView(generic.ObjectView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = VirtualMachine.objects.prefetch_related("tenant__group")

    def get_extra_context(self, request, instance):
        # Interfaces
        # v2 TODO(jathan): Replace prefetch_related with select_related although this one may be
        # valid since `ip_addresses` is m2m.
        vminterfaces = (
            VMInterface.objects.restrict(request.user, "view")
            .filter(virtual_machine=instance)
            .prefetch_related(Prefetch("ip_addresses", queryset=IPAddress.objects.restrict(request.user)))
        )
        vminterface_table = tables.VirtualMachineVMInterfaceTable(vminterfaces, user=request.user, orderable=False)
        if request.user.has_perm("virtualization.change_vminterface") or request.user.has_perm(
            "virtualization.delete_vminterface"
        ):
            vminterface_table.columns.show("pk")

        # Services
        # v2 TODO(jathan): Replace prefetch_related with select_related
        services = (
            Service.objects.restrict(request.user, "view")
            .filter(virtual_machine=instance)
            .prefetch_related(Prefetch("ipaddresses", queryset=IPAddress.objects.restrict(request.user)))
        )

        return {
            "vminterface_table": vminterface_table,
            "services": services,
        }


class VirtualMachineConfigContextView(ObjectConfigContextView):
    queryset = VirtualMachine.objects.annotate_config_context_data()
    base_template = "virtualization/virtualmachine.html"


class VirtualMachineEditView(generic.ObjectEditView):
    queryset = VirtualMachine.objects.all()
    model_form = forms.VirtualMachineForm
    template_name = "virtualization/virtualmachine_edit.html"


class VirtualMachineDeleteView(generic.ObjectDeleteView):
    queryset = VirtualMachine.objects.all()


class VirtualMachineBulkImportView(generic.BulkImportView):
    queryset = VirtualMachine.objects.all()
    model_form = forms.VirtualMachineCSVForm
    table = tables.VirtualMachineTable


class VirtualMachineBulkEditView(generic.BulkEditView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = VirtualMachine.objects.prefetch_related("cluster", "role", "status", "tenant")
    filterset = filters.VirtualMachineFilterSet
    table = tables.VirtualMachineTable
    form = forms.VirtualMachineBulkEditForm


class VirtualMachineBulkDeleteView(generic.BulkDeleteView):
    # v2 TODO(jathan): Replace prefetch_related with select_related
    queryset = VirtualMachine.objects.prefetch_related("cluster", "role", "status", "tenant")
    filterset = filters.VirtualMachineFilterSet
    table = tables.VirtualMachineTable


#
# VM interfaces
#


class VMInterfaceListView(generic.ObjectListView):
    queryset = VMInterface.objects.all()
    filterset = filters.VMInterfaceFilterSet
    filterset_form = forms.VMInterfaceFilterForm
    table = tables.VMInterfaceTable
    action_buttons = ("export",)


class VMInterfaceView(generic.ObjectView):
    queryset = VMInterface.objects.all()

    def get_extra_context(self, request, instance):
        # Get assigned IP addresses
        # v2 TODO(jathan): Replace prefetch_related with select_related
        ipaddress_table = InterfaceIPAddressTable(
            data=instance.ip_addresses.restrict(request.user, "view").prefetch_related("vrf", "tenant"),
            orderable=False,
        )

        # Get child interfaces
        child_interfaces = instance.child_interfaces.restrict(request.user, "view")
        child_interfaces_tables = tables.VMInterfaceTable(
            child_interfaces, orderable=False, exclude=("virtual_machine",)
        )

        # Get assigned VLANs and annotate whether each is tagged or untagged
        vlans = []
        if instance.untagged_vlan is not None:
            vlans.append(instance.untagged_vlan)
            vlans[0].tagged = False

        # v2 TODO(jathan): Replace prefetch_related with select_related
        for vlan in instance.tagged_vlans.restrict(request.user).prefetch_related("site", "group", "tenant", "role"):
            vlan.tagged = True
            vlans.append(vlan)
        vlan_table = InterfaceVLANTable(interface=instance, data=vlans, orderable=False)

        return {
            "ipaddress_table": ipaddress_table,
            "child_interfaces_table": child_interfaces_tables,
            "vlan_table": vlan_table,
        }


# 2.0 TODO: This will be collapsed into `InterfaceCreateView` and will go away.
class VMInterfaceCreateView(generic.ComponentCreateView):
    queryset = VMInterface.objects.all()
    form = forms.VMInterfaceCreateForm
    model_form = forms.VMInterfaceForm
    template_name = "virtualization/virtualmachine_component_add.html"


class VMInterfaceEditView(generic.ObjectEditView):
    queryset = VMInterface.objects.all()
    model_form = forms.VMInterfaceForm
    template_name = "virtualization/vminterface_edit.html"


class VMInterfaceDeleteView(generic.ObjectDeleteView):
    queryset = VMInterface.objects.all()
    template_name = "virtualization/virtual_machine_vminterface_delete.html"


class VMInterfaceBulkImportView(generic.BulkImportView):
    queryset = VMInterface.objects.all()
    model_form = forms.VMInterfaceCSVForm
    table = tables.VMInterfaceTable


class VMInterfaceBulkEditView(generic.BulkEditView):
    queryset = VMInterface.objects.all()
    table = tables.VMInterfaceTable
    form = forms.VMInterfaceBulkEditForm


class VMInterfaceBulkRenameView(generic.BulkRenameView):
    queryset = VMInterface.objects.all()
    form = forms.VMInterfaceBulkRenameForm


class VMInterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = VMInterface.objects.all()
    table = tables.VMInterfaceTable
    template_name = "virtualization/virtual_machine_vminterface_delete.html"


#
# Bulk Device component creation
#


class VirtualMachineBulkAddInterfaceView(generic.BulkComponentCreateView):
    parent_model = VirtualMachine
    parent_field = "virtual_machine"
    form = forms.VMInterfaceBulkCreateForm
    queryset = VMInterface.objects.all()
    model_form = forms.VMInterfaceForm
    filterset = filters.VirtualMachineFilterSet
    table = tables.VirtualMachineTable

    def get_required_permission(self):
        return "virtualization.add_vminterface"
