from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django_tables2 import RequestConfig

from nautobot.core.models.querysets import count_related
from nautobot.core.views import generic, mixins as view_mixins
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.dcim.models import Device, Interface
from nautobot.virtualization.models import VirtualMachine, VMInterface
from . import filters, forms, tables
from nautobot.ipam.api import serializers
from nautobot.ipam import choices
from .models import (
    IPAddress,
    Namespace,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from .utils import (
    add_available_ipaddresses,
    add_available_prefixes,
    add_available_vlans,
)


#
# Namespaces
#


def get_namespace_related_counts(instance, request):
    """Return counts of all IPAM objects related to the given Namespace."""
    return {
        "vrf_count": instance.vrfs.restrict(request.user, "view").count(),
        "prefix_count": instance.prefixes.restrict(request.user, "view").count(),
        "ip_address_count": instance.ip_addresses.restrict(request.user, "view").count(),
    }


class NamespaceUIViewSet(
    view_mixins.ObjectDetailViewMixin,
    view_mixins.ObjectListViewMixin,
    view_mixins.ObjectEditViewMixin,
    view_mixins.ObjectDestroyViewMixin,
    view_mixins.ObjectChangeLogViewMixin,
    view_mixins.ObjectNotesViewMixin,
):
    lookup_field = "pk"
    form_class = forms.NamespaceForm
    filterset_class = filters.NamespaceFilterSet
    queryset = Namespace.objects.all()
    serializer_class = serializers.NamespaceSerializer
    table_class = tables.NamespaceTable

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        if self.action == "retrieve":
            context.update(get_namespace_related_counts(instance, request))

        return context


class NamespaceIPAddressesView(generic.ObjectView):
    queryset = Namespace.objects.all()
    template_name = "ipam/namespace_ipaddresses.html"

    def get_extra_context(self, request, instance):
        # Find all IPAddresses belonging to this Namespace
        ip_addresses = instance.ip_addresses.restrict(request.user, "view").select_related("status")

        ip_address_table = tables.IPAddressTable(ip_addresses)
        if request.user.has_perm("ipam.change_ipaddress") or request.user.has_perm("ipam.delete_ipaddress"):
            ip_address_table.columns.show("pk")

        ip_address_table.exclude = ("namespace",)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(ip_address_table)

        # Compile permissions list for rendering the object table
        permissions = {
            "add": request.user.has_perm("ipam.add_ipaddress"),
            "change": request.user.has_perm("ipam.change_ipaddress"),
            "delete": request.user.has_perm("ipam.delete_ipaddress"),
        }
        bulk_querystring = f"namespace={instance.id}"

        context = super().get_extra_context(request, instance)
        context.update(
            {
                "ip_address_table": ip_address_table,
                "permissions": permissions,
                "bulk_querystring": bulk_querystring,
                "active_tab": "ip-addresses",
            }
        )
        context.update(get_namespace_related_counts(instance, request))

        return context


class NamespacePrefixesView(generic.ObjectView):
    queryset = Namespace.objects.all()
    template_name = "ipam/namespace_prefixes.html"

    def get_extra_context(self, request, instance):
        # Find all Prefixes belonging to this Namespace
        prefixes = instance.prefixes.restrict(request.user, "view").select_related("status")

        prefix_table = tables.PrefixTable(prefixes)
        if request.user.has_perm("ipam.change_prefix") or request.user.has_perm("ipam.delete_prefix"):
            prefix_table.columns.show("pk")

        prefix_table.exclude = ("namespace",)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(prefix_table)

        # Compile permissions list for rendering the object table
        permissions = {
            "add": request.user.has_perm("ipam.add_prefix"),
            "change": request.user.has_perm("ipam.change_prefix"),
            "delete": request.user.has_perm("ipam.delete_prefix"),
        }
        bulk_querystring = f"namespace={instance.id}"

        context = super().get_extra_context(request, instance)
        context.update(
            {
                "prefix_table": prefix_table,
                "permissions": permissions,
                "bulk_querystring": bulk_querystring,
                "active_tab": "prefixes",
            }
        )
        context.update(get_namespace_related_counts(instance, request))

        return context


class NamespaceVRFsView(generic.ObjectView):
    queryset = Namespace.objects.all()
    template_name = "ipam/namespace_vrfs.html"

    def get_extra_context(self, request, instance):
        # Find all VRFs belonging to this Namespace
        vrfs = instance.vrfs.restrict(request.user, "view")

        vrf_table = tables.VRFTable(vrfs)
        if request.user.has_perm("ipam.change_vrf") or request.user.has_perm("ipam.delete_vrf"):
            vrf_table.columns.show("pk")

        vrf_table.exclude = ("namespace",)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(vrf_table)

        # Compile permissions list for rendering the object table
        permissions = {
            "add": request.user.has_perm("ipam.add_vrf"),
            "change": request.user.has_perm("ipam.change_vrf"),
            "delete": request.user.has_perm("ipam.delete_vrf"),
        }
        bulk_querystring = f"namespace={instance.id}"

        context = super().get_extra_context(request, instance)
        context.update(
            {
                "vrf_table": vrf_table,
                "permissions": permissions,
                "bulk_querystring": bulk_querystring,
                "active_tab": "vrfs",
            }
        )
        context.update(get_namespace_related_counts(instance, request))

        return context


#
# VRFs
#


class VRFListView(generic.ObjectListView):
    queryset = VRF.objects.all()
    filterset = filters.VRFFilterSet
    filterset_form = forms.VRFFilterForm
    table = tables.VRFTable


class VRFView(generic.ObjectView):
    queryset = VRF.objects.all()

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)

        prefixes = instance.prefixes.restrict(request.user, "view")
        prefix_count = prefixes.count()
        prefix_table = tables.PrefixTable(prefixes.select_related("namespace"))

        # devices = instance.devices.restrict(request.user, "view")
        # device_count = devices.count()
        # device_table = DeviceTable(devices.all(), orderable=False)

        import_targets_table = tables.RouteTargetTable(
            instance.import_targets.select_related("tenant"), orderable=False
        )
        export_targets_table = tables.RouteTargetTable(
            instance.export_targets.select_related("tenant"), orderable=False
        )

        # TODO(jathan): This table might need to live on Device and on VRFs
        # (possibly replacing `device_table` above.
        vrfs = instance.device_assignments.restrict(request.user, "view")
        vrf_table = tables.VRFDeviceAssignmentTable(vrfs)
        vrf_table.exclude = ("vrf",)
        # context["vrf_table"] = vrf_table

        context.update(
            {
                "device_table": vrf_table,
                # "device_table": device_table,
                "prefix_count": prefix_count,
                "prefix_table": prefix_table,
                "import_targets_table": import_targets_table,
                "export_targets_table": export_targets_table,
            }
        )

        return context


class VRFEditView(generic.ObjectEditView):
    queryset = VRF.objects.all()
    model_form = forms.VRFForm
    template_name = "ipam/vrf_edit.html"


class VRFDeleteView(generic.ObjectDeleteView):
    queryset = VRF.objects.all()


class VRFBulkImportView(generic.BulkImportView):
    queryset = VRF.objects.all()
    table = tables.VRFTable


class VRFBulkEditView(generic.BulkEditView):
    queryset = VRF.objects.select_related("tenant")
    filterset = filters.VRFFilterSet
    table = tables.VRFTable
    form = forms.VRFBulkEditForm


class VRFBulkDeleteView(generic.BulkDeleteView):
    queryset = VRF.objects.select_related("tenant")
    filterset = filters.VRFFilterSet
    table = tables.VRFTable


#
# Route targets
#


class RouteTargetListView(generic.ObjectListView):
    queryset = RouteTarget.objects.all()
    filterset = filters.RouteTargetFilterSet
    filterset_form = forms.RouteTargetFilterForm
    table = tables.RouteTargetTable


class RouteTargetView(generic.ObjectView):
    queryset = RouteTarget.objects.all()

    def get_extra_context(self, request, instance):
        importing_vrfs_table = tables.VRFTable(instance.importing_vrfs.select_related("tenant"), orderable=False)
        exporting_vrfs_table = tables.VRFTable(instance.exporting_vrfs.select_related("tenant"), orderable=False)

        return {
            "importing_vrfs_table": importing_vrfs_table,
            "exporting_vrfs_table": exporting_vrfs_table,
        }


class RouteTargetEditView(generic.ObjectEditView):
    queryset = RouteTarget.objects.all()
    model_form = forms.RouteTargetForm


class RouteTargetDeleteView(generic.ObjectDeleteView):
    queryset = RouteTarget.objects.all()


class RouteTargetBulkImportView(generic.BulkImportView):
    queryset = RouteTarget.objects.all()
    table = tables.RouteTargetTable


class RouteTargetBulkEditView(generic.BulkEditView):
    queryset = RouteTarget.objects.select_related("tenant")
    filterset = filters.RouteTargetFilterSet
    table = tables.RouteTargetTable
    form = forms.RouteTargetBulkEditForm


class RouteTargetBulkDeleteView(generic.BulkDeleteView):
    queryset = RouteTarget.objects.select_related("tenant")
    filterset = filters.RouteTargetFilterSet
    table = tables.RouteTargetTable


#
# RIRs
#


class RIRListView(generic.ObjectListView):
    queryset = RIR.objects.annotate(assigned_prefix_count=count_related(Prefix, "rir"))
    filterset = filters.RIRFilterSet
    filterset_form = forms.RIRFilterForm
    table = tables.RIRTable


class RIRView(generic.ObjectView):
    queryset = RIR.objects.all()

    def get_extra_context(self, request, instance):
        # Prefixes
        assigned_prefixes = Prefix.objects.restrict(request.user, "view").filter(rir=instance).select_related("tenant")

        assigned_prefix_table = tables.PrefixTable(assigned_prefixes)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(assigned_prefix_table)

        return {
            "assigned_prefix_table": assigned_prefix_table,
        }


class RIREditView(generic.ObjectEditView):
    queryset = RIR.objects.all()
    model_form = forms.RIRForm


class RIRDeleteView(generic.ObjectDeleteView):
    queryset = RIR.objects.all()


class RIRBulkImportView(generic.BulkImportView):
    queryset = RIR.objects.all()
    table = tables.RIRTable


class RIRBulkDeleteView(generic.BulkDeleteView):
    queryset = RIR.objects.annotate(assigned_prefix_count=count_related(Prefix, "rir"))
    filterset = filters.RIRFilterSet
    table = tables.RIRTable


#
# Prefixes
#


class PrefixListView(generic.ObjectListView):
    filterset = filters.PrefixFilterSet
    filterset_form = forms.PrefixFilterForm
    table = tables.PrefixDetailTable
    template_name = "ipam/prefix_list.html"
    queryset = Prefix.objects.select_related(
        "parent",
        "location",
        "namespace",
        "tenant",
        "vlan",
        "rir",
        "role",
        "status",
    )


class PrefixView(generic.ObjectView):
    queryset = Prefix.objects.select_related(
        "parent",
        "rir",
        "role",
        "location",
        "status",
        "tenant__tenant_group",
        "vlan__vlan_group",
        "namespace",
    )

    def get_extra_context(self, request, instance):
        # Parent prefixes table
        parent_prefixes = instance.ancestors().restrict(request.user, "view").select_related("parent", "namespace")
        parent_prefix_table = tables.PrefixTable(list(parent_prefixes))
        parent_prefix_table.exclude = ("namespace",)

        vrfs = instance.vrf_assignments.restrict(request.user, "view")
        vrf_table = tables.VRFPrefixAssignmentTable(vrfs, orderable=False)

        return {
            "vrf_table": vrf_table,
            "parent_prefix_table": parent_prefix_table,
        }


class PrefixPrefixesView(generic.ObjectView):
    queryset = Prefix.objects.all()
    template_name = "ipam/prefix_prefixes.html"

    def get_extra_context(self, request, instance):
        # Child prefixes table
        child_prefixes = (
            instance.descendants()
            .restrict(request.user, "view")
            .select_related("parent", "location", "status", "role", "vlan", "namespace")
        )

        # Add available prefixes to the table if requested
        if child_prefixes and request.GET.get("show_available", "true") == "true":
            child_prefixes = add_available_prefixes(instance.prefix, child_prefixes)

        prefix_table = tables.PrefixDetailTable(child_prefixes)
        prefix_table.exclude = ("namespace",)
        if request.user.has_perm("ipam.change_prefix") or request.user.has_perm("ipam.delete_prefix"):
            prefix_table.columns.show("pk")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(prefix_table)

        # Compile permissions list for rendering the object table
        permissions = {
            "add": request.user.has_perm("ipam.add_prefix"),
            "change": request.user.has_perm("ipam.change_prefix"),
            "delete": request.user.has_perm("ipam.delete_prefix"),
        }
        namespace_id = instance.namespace_id
        bulk_querystring = f"namespace={namespace_id}&within={instance.prefix}"

        return {
            "first_available_prefix": instance.get_first_available_prefix(),
            "prefix_table": prefix_table,
            "permissions": permissions,
            "bulk_querystring": bulk_querystring,
            "active_tab": "prefixes",
            "show_available": request.GET.get("show_available", "true") == "true",
        }


class PrefixIPAddressesView(generic.ObjectView):
    queryset = Prefix.objects.all()
    template_name = "ipam/prefix_ipaddresses.html"

    def get_extra_context(self, request, instance):
        # Find all IPAddresses belonging to this Prefix
        ipaddresses = (
            instance.ip_addresses.all()
            .restrict(request.user, "view")
            .select_related("status")
            .prefetch_related("primary_ip4_for", "primary_ip6_for")
        )

        # Add available IP addresses to the table if requested
        if request.GET.get("show_available", "true") == "true":
            ipaddresses = add_available_ipaddresses(
                instance.prefix, ipaddresses, instance.type == choices.PrefixTypeChoices.TYPE_POOL
            )

        ip_table = tables.IPAddressTable(ipaddresses)
        if request.user.has_perm("ipam.change_ipaddress") or request.user.has_perm("ipam.delete_ipaddress"):
            ip_table.columns.show("pk")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(ip_table)

        # Compile permissions list for rendering the object table
        permissions = {
            "add": request.user.has_perm("ipam.add_ipaddress"),
            "change": request.user.has_perm("ipam.change_ipaddress"),
            "delete": request.user.has_perm("ipam.delete_ipaddress"),
        }
        namespace_id = instance.namespace_id
        bulk_querystring = f"namespace={namespace_id}&parent={instance.prefix}"

        return {
            "first_available_ip": instance.get_first_available_ip(),
            "ip_table": ip_table,
            "permissions": permissions,
            "bulk_querystring": bulk_querystring,
            "active_tab": "ip-addresses",
            "show_available": request.GET.get("show_available", "true") == "true",
        }


class PrefixEditView(generic.ObjectEditView):
    queryset = Prefix.objects.all()
    model_form = forms.PrefixForm
    template_name = "ipam/prefix_edit.html"


class PrefixDeleteView(generic.ObjectDeleteView):
    queryset = Prefix.objects.all()
    template_name = "ipam/prefix_delete.html"


class PrefixBulkImportView(generic.BulkImportView):
    queryset = Prefix.objects.all()
    table = tables.PrefixTable


class PrefixBulkEditView(generic.BulkEditView):
    queryset = Prefix.objects.select_related("location", "status", "namespace", "tenant", "vlan", "role")
    filterset = filters.PrefixFilterSet
    table = tables.PrefixTable
    form = forms.PrefixBulkEditForm


class PrefixBulkDeleteView(generic.BulkDeleteView):
    queryset = Prefix.objects.select_related("location", "status", "namespace", "tenant", "vlan", "role")
    filterset = filters.PrefixFilterSet
    table = tables.PrefixTable


#
# IP addresses
#


class IPAddressListView(generic.ObjectListView):
    queryset = IPAddress.objects.select_related("tenant", "status", "role")
    filterset = filters.IPAddressFilterSet
    filterset_form = forms.IPAddressFilterForm
    table = tables.IPAddressDetailTable


class IPAddressView(generic.ObjectView):
    queryset = IPAddress.objects.select_related("tenant", "status", "role")

    def get_extra_context(self, request, instance):
        # Parent prefixes table
        parent_prefixes = (
            instance.ancestors().restrict(request.user, "view").select_related("location", "status", "role", "tenant")
        )
        parent_prefixes_table = tables.PrefixTable(list(parent_prefixes), orderable=False)

        # Related IP table
        related_ips = instance.siblings().restrict(request.user, "view").select_related("status", "role", "tenant")
        related_ips_table = tables.IPAddressTable(related_ips, orderable=False)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(related_ips_table)

        return {
            "parent_prefixes_table": parent_prefixes_table,
            "related_ips_table": related_ips_table,
        }


class IPAddressEditView(generic.ObjectEditView):
    queryset = IPAddress.objects.all()
    model_form = forms.IPAddressForm
    template_name = "ipam/ipaddress_edit.html"

    def alter_obj(self, obj, request, url_args, url_kwargs):
        # TODO: update to work with interface M2M
        if "interface" in request.GET:
            try:
                obj.assigned_object = Interface.objects.get(pk=request.GET["interface"])
            except (ValueError, Interface.DoesNotExist):
                pass

        elif "vminterface" in request.GET:
            try:
                obj.assigned_object = VMInterface.objects.get(pk=request.GET["vminterface"])
            except (ValueError, VMInterface.DoesNotExist):
                pass

        return obj


# 2.0 TODO: Standardize or remove this view in exchange for a `NautobotViewSet` method
class IPAddressAssignView(generic.ObjectView):
    """
    Search for IPAddresses to be assigned to an Interface.
    """

    queryset = IPAddress.objects.all()

    def dispatch(self, request, *args, **kwargs):
        # Redirect user if an interface has not been provided
        if "interface" not in request.GET and "vminterface" not in request.GET:
            return redirect("ipam:ipaddress_add")

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        form = forms.IPAddressAssignForm()

        return render(
            request,
            "ipam/ipaddress_assign.html",
            {
                "form": form,
                "return_url": request.GET.get("return_url", ""),
            },
        )

    def post(self, request):
        form = forms.IPAddressAssignForm(request.POST)
        table = None

        if form.is_valid():
            addresses = self.queryset.select_related("tenant")
            # Limit to 100 results
            addresses = filters.IPAddressFilterSet(request.POST, addresses).qs[:100]
            table = tables.IPAddressAssignTable(addresses)

        return render(
            request,
            "ipam/ipaddress_assign.html",
            {
                "form": form,
                "table": table,
                "return_url": request.GET.get("return_url"),
            },
        )


class IPAddressDeleteView(generic.ObjectDeleteView):
    queryset = IPAddress.objects.all()


class IPAddressBulkCreateView(generic.BulkCreateView):
    queryset = IPAddress.objects.all()
    form = forms.IPAddressBulkCreateForm
    model_form = forms.IPAddressBulkAddForm
    pattern_target = "address"
    template_name = "ipam/ipaddress_bulk_add.html"


class IPAddressBulkImportView(generic.BulkImportView):
    queryset = IPAddress.objects.all()
    table = tables.IPAddressTable


class IPAddressBulkEditView(generic.BulkEditView):
    # queryset = IPAddress.objects.select_related("status", "role", "tenant", "vrf__tenant")
    queryset = IPAddress.objects.select_related("status", "role", "tenant")
    filterset = filters.IPAddressFilterSet
    table = tables.IPAddressTable
    form = forms.IPAddressBulkEditForm


class IPAddressBulkDeleteView(generic.BulkDeleteView):
    # queryset = IPAddress.objects.select_related("status", "role", "tenant", "vrf__tenant")
    queryset = IPAddress.objects.select_related("status", "role", "tenant")
    filterset = filters.IPAddressFilterSet
    table = tables.IPAddressTable


class IPAddressInterfacesView(generic.ObjectView):
    queryset = IPAddress.objects.all()
    template_name = "ipam/ipaddress_interfaces.html"

    def get_extra_context(self, request, instance):
        interfaces = (
            instance.interfaces.restrict(request.user, "view")
            .prefetch_related(
                Prefetch("ip_addresses", queryset=IPAddress.objects.restrict(request.user)),
                Prefetch("member_interfaces", queryset=Interface.objects.restrict(request.user)),
                "_path__destination",
                "tags",
            )
            .select_related("lag", "cable")
        )
        interface_table = tables.IPAddressInterfaceTable(data=interfaces, user=request.user, orderable=False)
        if request.user.has_perm("dcim.change_interface") or request.user.has_perm("dcim.delete_interface"):
            interface_table.columns.show("pk")

        return {
            "interface_table": interface_table,
            "active_tab": "interfaces",
        }


#
# VLAN groups
#


class VLANGroupListView(generic.ObjectListView):
    queryset = VLANGroup.objects.select_related("location").annotate(vlan_count=count_related(VLAN, "vlan_group"))
    filterset = filters.VLANGroupFilterSet
    filterset_form = forms.VLANGroupFilterForm
    table = tables.VLANGroupTable


class VLANGroupView(generic.ObjectView):
    queryset = VLANGroup.objects.all()

    def get_extra_context(self, request, instance):
        vlans = (
            VLAN.objects.restrict(request.user, "view")
            .filter(vlan_group=instance)
            .prefetch_related(Prefetch("prefixes", queryset=Prefix.objects.restrict(request.user)))
        )
        vlans_count = vlans.count()
        vlans = add_available_vlans(instance, vlans)

        vlan_table = tables.VLANDetailTable(vlans)
        if request.user.has_perm("ipam.change_vlan") or request.user.has_perm("ipam.delete_vlan"):
            vlan_table.columns.show("pk")
        vlan_table.columns.hide("location")
        vlan_table.columns.hide("vlan_group")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(vlan_table)

        # Compile permissions list for rendering the object table
        permissions = {
            "add": request.user.has_perm("ipam.add_vlan"),
            "change": request.user.has_perm("ipam.change_vlan"),
            "delete": request.user.has_perm("ipam.delete_vlan"),
        }

        return {
            "first_available_vlan": instance.get_next_available_vid(),
            "bulk_querystring": f"vlan_group_id={instance.pk}",
            "vlan_table": vlan_table,
            "permissions": permissions,
            "vlans_count": vlans_count,
        }


class VLANGroupEditView(generic.ObjectEditView):
    queryset = VLANGroup.objects.all()
    model_form = forms.VLANGroupForm


class VLANGroupDeleteView(generic.ObjectDeleteView):
    queryset = VLANGroup.objects.all()


class VLANGroupBulkImportView(generic.BulkImportView):
    queryset = VLANGroup.objects.all()
    table = tables.VLANGroupTable


class VLANGroupBulkDeleteView(generic.BulkDeleteView):
    queryset = VLANGroup.objects.select_related("location").annotate(vlan_count=count_related(VLAN, "vlan_group"))
    filterset = filters.VLANGroupFilterSet
    table = tables.VLANGroupTable


#
# VLANs
#


class VLANListView(generic.ObjectListView):
    queryset = VLAN.objects.select_related("location", "vlan_group", "tenant", "role", "status")
    filterset = filters.VLANFilterSet
    filterset_form = forms.VLANFilterForm
    table = tables.VLANDetailTable


class VLANView(generic.ObjectView):
    queryset = VLAN.objects.select_related(
        "role",
        "location",
        "status",
        "tenant__tenant_group",
    )

    def get_extra_context(self, request, instance):
        prefixes = (
            Prefix.objects.restrict(request.user, "view")
            .filter(vlan=instance)
            .select_related(
                "location",
                "status",
                "role",
                # "vrf",
                "namespace",
            )
        )
        prefix_table = tables.PrefixTable(list(prefixes))
        prefix_table.exclude = ("vlan",)

        return {
            "prefix_table": prefix_table,
        }


class VLANInterfacesView(generic.ObjectView):
    queryset = VLAN.objects.all()
    template_name = "ipam/vlan_interfaces.html"

    def get_extra_context(self, request, instance):
        interfaces = instance.get_interfaces().select_related("device")
        members_table = tables.VLANDevicesTable(interfaces)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(members_table)

        return {
            "members_table": members_table,
            "active_tab": "interfaces",
        }


class VLANVMInterfacesView(generic.ObjectView):
    queryset = VLAN.objects.all()
    template_name = "ipam/vlan_vminterfaces.html"

    def get_extra_context(self, request, instance):
        interfaces = instance.get_vminterfaces().select_related("virtual_machine")
        members_table = tables.VLANVirtualMachinesTable(interfaces)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(members_table)

        return {
            "members_table": members_table,
            "active_tab": "vminterfaces",
        }


class VLANEditView(generic.ObjectEditView):
    queryset = VLAN.objects.all()
    model_form = forms.VLANForm
    template_name = "ipam/vlan_edit.html"


class VLANDeleteView(generic.ObjectDeleteView):
    queryset = VLAN.objects.all()


class VLANBulkImportView(generic.BulkImportView):
    queryset = VLAN.objects.all()
    table = tables.VLANTable


class VLANBulkEditView(generic.BulkEditView):
    queryset = VLAN.objects.select_related(
        "vlan_group",
        "location",
        "status",
        "tenant",
        "role",
    )
    filterset = filters.VLANFilterSet
    table = tables.VLANTable
    form = forms.VLANBulkEditForm


class VLANBulkDeleteView(generic.BulkDeleteView):
    queryset = VLAN.objects.select_related(
        "vlan_group",
        "location",
        "status",
        "tenant",
        "role",
    )
    filterset = filters.VLANFilterSet
    table = tables.VLANTable


#
# Services
#


class ServiceListView(generic.ObjectListView):
    queryset = Service.objects.all()
    filterset = filters.ServiceFilterSet
    filterset_form = forms.ServiceFilterForm
    table = tables.ServiceTable
    action_buttons = ("import", "export")


class ServiceView(generic.ObjectView):
    queryset = Service.objects.prefetch_related("ip_addresses")


class ServiceEditView(generic.ObjectEditView):
    queryset = Service.objects.prefetch_related("ip_addresses")
    model_form = forms.ServiceForm
    template_name = "ipam/service_edit.html"

    def alter_obj(self, obj, request, url_args, url_kwargs):
        if "device" in url_kwargs:
            obj.device = get_object_or_404(Device.objects.restrict(request.user), pk=url_kwargs["device"])
        elif "virtualmachine" in url_kwargs:
            obj.virtual_machine = get_object_or_404(
                VirtualMachine.objects.restrict(request.user),
                pk=url_kwargs["virtualmachine"],
            )
        return obj


class ServiceBulkImportView(generic.BulkImportView):
    queryset = Service.objects.all()
    table = tables.ServiceTable


class ServiceDeleteView(generic.ObjectDeleteView):
    queryset = Service.objects.all()


class ServiceBulkEditView(generic.BulkEditView):
    queryset = Service.objects.select_related("device", "virtual_machine")
    filterset = filters.ServiceFilterSet
    table = tables.ServiceTable
    form = forms.ServiceBulkEditForm


class ServiceBulkDeleteView(generic.BulkDeleteView):
    queryset = Service.objects.select_related("device", "virtual_machine")
    filterset = filters.ServiceFilterSet
    table = tables.ServiceTable
