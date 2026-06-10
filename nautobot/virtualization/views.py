from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import mark_safe
from django.utils.http import urlencode
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.core.choices import ButtonActionColorChoices
from nautobot.core.templatetags.helpers import HTML_NONE
from nautobot.core.ui import object_detail
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.views import generic
from nautobot.core.views.mixins import (
    ObjectBulkDestroyViewMixin,
    ObjectBulkRenameViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectChangeLogViewMixin,
    ObjectDestroyViewMixin,
    ObjectDetailViewMixin,
    ObjectEditViewMixin,
    ObjectListViewMixin,
    ObjectNotesViewMixin,
)
from nautobot.core.views.utils import common_detail_view_context
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.tables import DeviceTable
from nautobot.dcim.utils import render_software_version_and_image_files
from nautobot.dcim.views import ComponentCreateViewMixin
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
                section=SectionChoices.FULL_WIDTH,
                table_class=DeviceTable,
                table_filter="clusters",
                table_title="Host Devices",
                enable_bulk_actions=True,
                exclude_columns=["cluster_count"],
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                section=SectionChoices.FULL_WIDTH,
                table_class=tables.VirtualMachineTable,
                table_filter="cluster",
                exclude_columns=["cluster"],
            ),
        )
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
                related_list_url_name="ipam:vrf_list",
                related_field_name="virtual_machines",
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
        custom_view_base_action="view",
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
            "base_template": "generic/object_retrieve.html",
        }

        return Response(context)


#
# VM interfaces
#


class VMInterfaceUIViewSet(
    ComponentCreateViewMixin,
    ObjectListViewMixin,
    ObjectDetailViewMixin,
    ObjectEditViewMixin,
    ObjectDestroyViewMixin,
    ObjectBulkDestroyViewMixin,
    ObjectBulkUpdateViewMixin,
    ObjectBulkRenameViewMixin,
    ObjectChangeLogViewMixin,
    ObjectNotesViewMixin,
):
    queryset = VMInterface.objects.all()
    filterset_class = filters.VMInterfaceFilterSet
    filterset_form_class = forms.VMInterfaceFilterForm
    table_class = tables.VMInterfaceTable
    serializer_class = serializers.VMInterfaceSerializer
    form_class = forms.VMInterfaceForm
    create_form_class = forms.VMInterfaceCreateForm
    bulk_update_form_class = forms.VMInterfaceBulkEditForm
    action_buttons = ("export",)

    def get_extra_context(self, request, instance=None):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve" and instance is not None:
            # Get assigned IP addresses
            context["ipaddress_table"] = InterfaceIPAddressTable(
                data=instance.ip_addresses.restrict(request.user, "view").select_related("role", "status", "tenant"),
                orderable=False,
            )
            # Get child interfaces
            context["child_interfaces_table"] = tables.VMInterfaceTable(
                instance.child_interfaces.restrict(request.user, "view"),
                orderable=False,
            )
            # Equivalent to exclude=("virtual_machine",):
            context["child_interfaces_table"].columns.hide("virtual_machine")
            # Get assigned VLANs and annotate whether each is tagged or untagged
            vlans = []
            if instance.untagged_vlan is not None:
                vlans.append(instance.untagged_vlan)
                vlans[0].tagged = False
            for vlan in instance.tagged_vlans.restrict(request.user).select_related("vlan_group", "tenant", "role"):
                vlan.tagged = True
                vlans.append(vlan)
            context["vlan_table"] = InterfaceVLANTable(interface=instance, data=vlans, orderable=False)
        return context

    class ChildInterfacesTablePanel(object_detail.ObjectsTablePanel):
        """Table panel whose right-aligned "Add" button targets the VM interface create form with the
        parent VM and parent interface pre-filled.

        The default add button can only pass a single `{field}={obj.pk}` param, but a child interface
        needs both `virtual_machine` (from the parent VM) and `parent_interface` (the interface being
        viewed). Overriding `_get_table_add_url` lets the native (right-side) add button carry both.
        """

        def _get_table_add_url(self, context):
            request = context["request"]
            if not request.user.has_perm("virtualization.add_vminterface"):
                return None
            instance = object_detail.get_obj_from_context(context)
            return_url = context.get("return_url", instance.get_absolute_url())
            return (
                reverse("virtualization:vminterface_add")
                + "?"
                + urlencode(
                    {
                        "virtual_machine": instance.virtual_machine.pk,
                        "parent_interface": instance.pk,
                        "return_url": return_url,
                    }
                )
            )

    class IPAddressesTablePanel(object_detail.ObjectsTablePanel):
        """Table panel whose right-aligned "Add" button opens the IP address create form pre-assigned to
        this VM interface.

        Uses the `?vminterface=<pk>` param the IP address edit view expects (singular, and distinct from
        the `vm_interfaces` list filter used for the "view all" link).
        """

        def _get_table_add_url(self, context):
            request = context["request"]
            if not request.user.has_perm("ipam.add_ipaddress"):
                return None
            instance = object_detail.get_obj_from_context(context)
            return_url = context.get("return_url", instance.get_absolute_url())
            return (
                reverse("ipam:ipaddress_add") + "?" + urlencode({"vminterface": instance.pk, "return_url": return_url})
            )

    object_detail_content = object_detail.ObjectDetailContent(
        panels=[
            object_detail.ObjectFieldsPanel(
                label="Interface",
                section=SectionChoices.LEFT_HALF,
                weight=100,
                key_transforms={
                    "mode": "802.1Q Mode",
                    "vrf": "VRF",
                },
                exclude_fields=["untagged_vlan"],
            ),
            # IP addresses
            IPAddressesTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=300,
                context_table_key="ipaddress_table",
                # The right-aligned Add button is built by the overridden `_get_table_add_url` (uses the
                # singular `vminterface` param); `related_field_name` below is only for the "view all" link.
                related_list_url_name="ipam:ipaddress_list",
                related_field_name="vm_interfaces",
            ),
            # Tagged + untagged VLANs
            # No "Add": a VLAN isn't created from an interface. You assign VLANs by editing the
            # interface's `untagged_vlan` / `tagged_vlans` fields -- the same fields used when the
            # interface is first created. So this panel links to the interface edit form instead.
            object_detail.ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=400,
                context_table_key="vlan_table",               
                # Custom footer template right-aligns the footer button (the default footer floats it left).
                footer_content_template_path="virtualization/inc/vminterface_vlan_panel_footer.html",
                footer_buttons=(
                    object_detail.Button(
                        weight=100,
                        color=ButtonActionColorChoices.EDIT,
                        link_name="virtualization:vminterface_edit",
                        label="Edit VLAN Assignments",
                        icon="mdi-pencil",
                        required_permissions=["virtualization.change_vminterface"],
                        link_includes_pk=True,
                    ),
                ),
                # "View all" links to the VLAN list filtered by this VM interface (tagged or untagged),
                # using the `vm_interfaces` filter added to VLANFilterSet.
                related_list_url_name="ipam:vlan_list",
                related_field_name="vm_interfaces",
            ),
            ChildInterfacesTablePanel(
                table_title="Child Interfaces",
                section=SectionChoices.FULL_WIDTH,
                weight=500,
                context_table_key="child_interfaces_table",
                # The right-aligned Add button is built by the overridden `_get_table_add_url`, so it
                # carries both `virtual_machine` and `parent_interface`.
                related_list_url_name="virtualization:vminterface_list",
                related_field_name="parent_interface",
            ),
        ]
    )


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
