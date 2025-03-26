from django.contrib import messages
from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.functional import cached_property

from nautobot.core.ui import object_detail
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.utils.requests import normalize_querydict
from nautobot.core.views import generic
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.models import Device
from nautobot.dcim.tables import DeviceTable
from nautobot.extras.views import ObjectConfigContextView
from nautobot.ipam.models import IPAddress, Service
from nautobot.ipam.tables import InterfaceIPAddressTable, InterfaceVLANTable, VRFDeviceAssignmentTable
from nautobot.virtualization.api import serializers

from . import filters, forms, tables
from .models import Cluster, ClusterGroup, ClusterType, VirtualMachine, VMInterface

#
# Cluster types
#


class ClusterTypeUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ClusterTypeBulkEditForm
    filterset_class = filters.ClusterTypeFilterSet
    filterset_form_class = forms.ClusterTypeFilterForm
    form_class = forms.ClusterTypeForm
    serializer_class = serializers.ClusterTypeSerializer
    table_class = tables.ClusterTypeTable
    queryset = ClusterType.objects.all()

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_class=tables.ClusterTable,
                table_filter="cluster_type",
                exclude_columns=["cluster_type"],
            ),
        )
    )


#
# Cluster groups
#


class ClusterGroupUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ClusterGroupBulkEditForm
    filterset_class = filters.ClusterGroupFilterSet
    filterset_form_class = forms.ClusterGroupFilterForm
    form_class = forms.ClusterGroupForm
    serializer_class = serializers.ClusterGroupSerializer
    table_class = tables.ClusterGroupTable
    queryset = ClusterGroup.objects.all()

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_class=tables.ClusterTable,
                table_filter="cluster_group",
                exclude_columns=["cluster_group"],
            ),
        )
    )


#
# Clusters
#


class ClusterListView(generic.ObjectListView):
    permission_required = "virtualization.view_cluster"
    queryset = Cluster.objects.all()
    table = tables.ClusterTable
    filterset = filters.ClusterFilterSet
    filterset_form = forms.ClusterFilterForm


class ClusterView(generic.ObjectView):
    queryset = Cluster.objects.all()

    def get_extra_context(self, request, instance):
        devices = Device.objects.restrict(request.user, "view").filter(cluster=instance)
        device_table = DeviceTable(list(devices), orderable=False)
        if request.user.has_perm("virtualization.change_cluster"):
            device_table.columns.show("pk")

        return {"device_table": device_table, **super().get_extra_context(request, instance)}


class ClusterEditView(generic.ObjectEditView):
    template_name = "virtualization/cluster_edit.html"
    queryset = Cluster.objects.all()
    model_form = forms.ClusterForm


class ClusterDeleteView(generic.ObjectDeleteView):
    queryset = Cluster.objects.all()


class ClusterBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = Cluster.objects.all()
    table = tables.ClusterTable


class ClusterBulkEditView(generic.BulkEditView):
    queryset = Cluster.objects.all()
    filterset = filters.ClusterFilterSet
    table = tables.ClusterTable
    form = forms.ClusterBulkEditForm


class ClusterBulkDeleteView(generic.BulkDeleteView):
    queryset = Cluster.objects.all()
    filterset = filters.ClusterFilterSet
    table = tables.ClusterTable


class ClusterAddDevicesView(generic.ObjectEditView):
    queryset = Cluster.objects.all()
    form = forms.ClusterAddDevicesForm
    template_name = "virtualization/cluster_add_devices.html"

    def get(self, request, *args, **kwargs):
        cluster = get_object_or_404(self.queryset, pk=kwargs["pk"])
        form = self.form(cluster, initial=normalize_querydict(request.GET, form_class=self.form))

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
    queryset = VirtualMachine.objects.select_related("software_version", "tenant__tenant_group")

    def get_extra_context(self, request, instance):
        # Interfaces
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
        services = (
            Service.objects.restrict(request.user, "view")
            .filter(virtual_machine=instance)
            .prefetch_related(Prefetch("ip_addresses", queryset=IPAddress.objects.restrict(request.user)))
        )

        # VRF assignments
        vrf_assignments = instance.vrf_assignments.restrict(request.user, "view")
        vrf_table = VRFDeviceAssignmentTable(vrf_assignments)

        # Software images
        if instance.software_version is not None:
            software_version_images = instance.software_version.software_image_files.restrict(request.user, "view")
        else:
            software_version_images = []

        return {
            "vminterface_table": vminterface_table,
            "services": services,
            "software_version_images": software_version_images,
            "vrf_table": vrf_table,
            **super().get_extra_context(request, instance),
        }


class VirtualMachineConfigContextView(ObjectConfigContextView):
    base_template = "virtualization/virtualmachine.html"

    @cached_property
    def queryset(self):  # pylint: disable=method-hidden
        """
        A cached_property rather than a class attribute because annotate_config_context_data() is unsafe at import time.
        """
        return VirtualMachine.objects.annotate_config_context_data()


class VirtualMachineEditView(generic.ObjectEditView):
    queryset = VirtualMachine.objects.all()
    model_form = forms.VirtualMachineForm
    template_name = "virtualization/virtualmachine_edit.html"


class VirtualMachineDeleteView(generic.ObjectDeleteView):
    queryset = VirtualMachine.objects.all()


class VirtualMachineBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = VirtualMachine.objects.all()
    table = tables.VirtualMachineTable


class VirtualMachineBulkEditView(generic.BulkEditView):
    queryset = VirtualMachine.objects.select_related("cluster", "role", "status", "tenant")
    filterset = filters.VirtualMachineFilterSet
    table = tables.VirtualMachineTable
    form = forms.VirtualMachineBulkEditForm


class VirtualMachineBulkDeleteView(generic.BulkDeleteView):
    queryset = VirtualMachine.objects.select_related("cluster", "role", "status", "tenant")
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
        ipaddress_table = InterfaceIPAddressTable(
            data=instance.ip_addresses.restrict(request.user, "view").select_related("role", "status", "tenant"),
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

        for vlan in instance.tagged_vlans.restrict(request.user).select_related("vlan_group", "tenant", "role"):
            vlan.tagged = True
            vlans.append(vlan)
        vlan_table = InterfaceVLANTable(interface=instance, data=vlans, orderable=False)

        return {
            "ipaddress_table": ipaddress_table,
            "child_interfaces_table": child_interfaces_tables,
            "vlan_table": vlan_table,
            **super().get_extra_context(request, instance),
        }


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


class VMInterfaceBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = VMInterface.objects.all()
    table = tables.VMInterfaceTable


class VMInterfaceBulkEditView(generic.BulkEditView):
    queryset = VMInterface.objects.all()
    table = tables.VMInterfaceTable
    form = forms.VMInterfaceBulkEditForm
    filterset = filters.VMInterfaceFilterSet


class VMInterfaceBulkRenameView(generic.BulkRenameView):
    queryset = VMInterface.objects.all()
    form = forms.VMInterfaceBulkRenameForm

    def get_selected_objects_parents_name(self, selected_objects):
        selected_object = selected_objects.first()
        if selected_object:
            return selected_object.virtual_machine.name
        return ""


class VMInterfaceBulkDeleteView(generic.BulkDeleteView):
    queryset = VMInterface.objects.all()
    table = tables.VMInterfaceTable
    template_name = "virtualization/vminterface_bulk_delete.html"
    filterset = filters.VMInterfaceFilterSet


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
