from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import mark_safe
from django.utils.http import urlencode
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.core.choices import ButtonActionColorChoices
from nautobot.core.templatetags.helpers import HTML_NONE
from nautobot.core.ui import object_detail
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.utils.requests import normalize_querydict
from nautobot.core.views import generic
from nautobot.core.views.utils import common_detail_view_context
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.models import Device
from nautobot.dcim.tables import DeviceTable
from nautobot.dcim.utils import render_software_version_and_image_files
from nautobot.extras.models import ConfigContext
from nautobot.ipam.tables import InterfaceIPAddressTable, InterfaceVLANTable, ServiceTable, VRFDeviceAssignmentTable
from nautobot.ipam.utils import render_ip_with_nat
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


class ClusterUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.ClusterBulkEditForm
    filterset_class = filters.ClusterFilterSet
    filterset_form_class = forms.ClusterFilterForm
    form_class = forms.ClusterForm
    serializer_class = serializers.ClusterSerializer
    table_class = tables.ClusterTable
    queryset = Cluster.objects.all()

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
                table_class=DeviceTable,
                table_filter="cluster",
                table_title="Host Devices",
                enable_bulk_actions=True,
                add_button_route=None,
                form_id="device_form",
                footer_buttons=[
                    object_detail.FormButton(
                        form_id="device_form",
                        link_name="virtualization:cluster_remove_devices",
                        label="Remove Devices",
                        weight=100,
                        color=ButtonActionColorChoices.DELETE,
                        icon="mdi-trash-can-outline",
                        size="xs",
                    ),
                    object_detail.Button(
                        link_name="virtualization:cluster_add_devices",
                        label="Add Devices",
                        weight=200,
                        color=ButtonActionColorChoices.ADD,
                        icon="mdi-plus",
                        size="xs",
                    ),
                ],
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.VirtualMachineTable,
                table_filter="cluster",
                add_button_route=None,
            ),
        )
    )


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


class VirtualMachineUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.VirtualMachineBulkEditForm
    filterset_class = filters.VirtualMachineFilterSet
    filterset_form_class = forms.VirtualMachineFilterForm
    form_class = forms.VirtualMachineForm
    serializer_class = serializers.VirtualMachineSerializer
    table_class = tables.VirtualMachineDetailTable
    queryset = VirtualMachine.objects.select_related("tenant__tenant_group")

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.action == "config_context":
            queryset = queryset.annotate_config_context_data()
        return queryset

    class VirtualMachineFieldsPanel(object_detail.ObjectFieldsPanel):
        def render_value(self, key, value, context):
            if key == "software_version":
                return render_software_version_and_image_files(
                    object_detail.get_obj_from_context(context, self.context_object_key), value, context
                )

            return super().render_value(key, value, context)

    class VirtualMachineAddInterfacesButton(object_detail.Button):
        def get_link(self, context):
            instance = object_detail.get_obj_from_context(context, self.context_object_key)
            return (
                super().get_link(context)
                + "?"
                + urlencode({"virtual_machine": instance.pk, "return_url": instance.get_absolute_url()})
            )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            VirtualMachineFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=(
                    "name",
                    "status",
                    "role",
                    "platform",
                    "tenant",
                    "primary_ip4",
                    "primary_ip6",
                    "software_version",
                ),
                value_transforms={
                    "primary_ip4": [render_ip_with_nat],
                    "primary_ip6": [render_ip_with_nat],
                },
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                table_title="Assigned VRFs",  # TODO: why does `label` get added to the table_title instead of overwriting
                table_class=VRFDeviceAssignmentTable,
                table_filter="virtual_machine",
                exclude_columns=["related_object_type", "related_object_name"],
            ),
            object_detail.ObjectFieldsPanel(
                weight=200,
                section=SectionChoices.RIGHT_HALF,
                label="Cluster",
                fields=("cluster", "cluster__cluster_type"),
                key_transforms={"cluster__cluster_type": "Cluster Type"},
            ),
            object_detail.ObjectFieldsPanel(
                weight=300,
                section=SectionChoices.RIGHT_HALF,
                label="Resources",
                fields=(
                    "vcpus",
                    "memory",
                    "disk",
                ),
                key_transforms={
                    "vcpus": mark_safe('<span class="mdi mdi-gauge"></span> Virtual CPUs'),
                    "memory": mark_safe('<span class="mdi mdi-chip"></span> Memory'),
                    "disk": mark_safe('<span class="mdi mdi-harddisk"></span> Disk Space'),
                },
                value_transforms={
                    "memory": [lambda value: f"{value} MB" if value else HTML_NONE],
                    "disk": [lambda value: f"{value} GB" if value else HTML_NONE],
                },
            ),
            object_detail.ObjectsTablePanel(
                weight=400,
                section=SectionChoices.RIGHT_HALF,
                table_title="Services",
                table_class=ServiceTable,
                table_filter="virtual_machine",
                exclude_columns=["parent"],
                include_columns=["ip_addresses"],
            ),
            object_detail.ObjectsTablePanel(
                weight=100,
                section=SectionChoices.FULL_WIDTH,
                table_title="Interfaces",
                table_class=tables.VirtualMachineVMInterfaceTable,
                table_filter="virtual_machine",
                header_extra_content_template_path="virtualization/inc/virtualmachine_vminterface_filter.html",
            ),
        ),
        extra_buttons=(
            VirtualMachineAddInterfacesButton(
                weight=100,
                color=ButtonActionColorChoices.ADD,
                link_name="virtualization:vminterface_add",
                label="Add Interfaces",
                icon="mdi-plus-thick",
                required_permissions=["virtualization.add_vminterface"],
                link_includes_pk=False,
            ),
        ),
        extra_tabs=(
            object_detail.DistinctViewTab(
                weight=1000,
                tab_id="config_context",
                label="Config Context",
                url_name="virtualization:virtualmachine_configcontext",
                required_permissions=["extras.view_configcontext"],
            ),
        ),
    )

    @action(
        detail=True,
        url_path="config-context",
        url_name="configcontext",
        custom_view_additional_permissions=["extras.view_configcontext"],
    )
    def config_context(self, request, pk):
        instance = self.get_object()

        # Determine user's preferred output format
        if request.GET.get("data_format") in ["json", "yaml"]:
            data_format = request.GET.get("data_format")
            if request.user.is_authenticated:
                request.user.set_config("extras.configcontext.format", data_format, commit=True)
        elif request.user.is_authenticated:
            data_format = request.user.get_config("extras.configcontext.format", "json")
        else:
            data_format = "json"

        context = {
            "object": instance,
            "content_type": ContentType.objects.get_for_model(self.queryset.model),
            "verbose_name": self.queryset.model._meta.verbose_name,
            "verbose_name_plural": self.queryset.model._meta.verbose_name_plural,
            "object_detail_content": self.object_detail_content,
            **common_detail_view_context(request, instance),
            "rendered_context": instance.get_config_context(),
            "source_contexts": ConfigContext.objects.restrict(request.user, "view").get_for_object(instance),
            "format": data_format,
            "template": "extras/object_configcontext.html",
            "base_template": "virtualization/virtualmachine.html",
        }

        return Response(context)


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
