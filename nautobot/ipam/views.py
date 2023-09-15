import logging
import netaddr

from django.conf import settings
from django.contrib import messages
from django.core.cache import cache
from django.db import models, transaction
from django.db.models import Count, Prefetch, ProtectedError, Q
from django.forms.models import model_to_dict
from django.templatetags.static import static
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.html import escape
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.views.generic import View
from django_tables2 import RequestConfig

from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.core.models.querysets import count_related
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.views import generic, mixins as view_mixins
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.utils import handle_protectederror
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import Role, Status, Tag
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VirtualMachine, VMInterface
from . import filters, forms, tables
from nautobot.ipam.api import serializers
from nautobot.ipam import choices, constants
from .models import (
    IPAddress,
    IPAddressToInterface,
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
    handle_relationship_changes_when_merging_ips,
    retrieve_interface_or_vminterface_from_request,
)


logger = logging.getLogger(__name__)

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
    view_mixins.ObjectBulkCreateViewMixin,
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
        ip_addresses = (
            instance.ip_addresses.restrict(request.user, "view")
            .select_related("role", "status", "tenant")
            .annotate(
                interface_count=Count("interfaces"),
                interface_parent_count=(Count("interfaces__device", distinct=True)),
                vm_interface_count=Count("vm_interfaces"),
                vm_interface_parent_count=(Count("vm_interfaces__virtual_machine", distinct=True)),
            )
        )

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
    ).prefetch_related(
        "ip_addresses",
        "children",
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
            .select_related("role", "status", "tenant")
            .prefetch_related("primary_ip4_for", "primary_ip6_for")
            .annotate(
                interface_count=Count("interfaces"),
                interface_parent_count=(Count("interfaces__device", distinct=True)),
                vm_interface_count=Count("vm_interfaces"),
                vm_interface_parent_count=(Count("vm_interfaces__virtual_machine", distinct=True)),
            )
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

    def successful_post(self, request, obj, created, _logger):
        """Check for data that will be invalid in a future Nautobot release and warn the user if found."""
        # 3.0 TODO: remove these checks after enabling strict enforcement of the equivalent logic in Prefix.save()
        edit_url = reverse("ipam:prefix_edit", kwargs={"pk": obj.pk})
        warning_msg = (
            '<p>This <a href="'
            + static("docs/models/ipam/prefix.html")
            + '#prefix-hierarchy">will be considered invalid data</a> in a future release.</p>'
        )
        if obj.parent and obj.parent.type != constants.PREFIX_ALLOWED_PARENT_TYPES[obj.type]:
            parent_edit_url = reverse("ipam:prefix_edit", kwargs={"pk": obj.parent.pk})
            messages.warning(
                request,
                mark_safe(
                    f'{obj} is a {obj.type.title()} prefix but its parent <a href="{obj.parent.get_absolute_url()}">'
                    f"{obj.parent}</a> is a {obj.parent.type.title()}. {warning_msg} "
                    f'Consider <a href="{edit_url}">changing the type of {obj}</a> and/or '
                    f'<a href="{parent_edit_url}">{obj.parent}</a> to resolve this issue.'
                ),
            )

        invalid_children = obj.children.filter(
            ~Q(type__in=constants.PREFIX_ALLOWED_CHILD_TYPES[obj.type]),  # exclude valid children
        )

        if invalid_children.exists():
            children_link = '<a href="' + reverse("ipam:prefix_list") + f'?parent={obj.pk}">its children</a>'
            if obj.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
                messages.warning(
                    request,
                    mark_safe(
                        f"{obj} is a Container prefix and should not contain child prefixes of type Pool. "
                        f"{warning_msg} Consider creating an intermediary Network prefix, or changing "
                        f"the type of {children_link} to Network, to resolve this issue."
                    ),
                )
            elif obj.type == choices.PrefixTypeChoices.TYPE_NETWORK:
                messages.warning(
                    request,
                    mark_safe(
                        f"{obj} is a Network prefix and should not contain child prefixes of types Container or "
                        f'Network. {warning_msg} Consider <a href="{edit_url}">changing the type of {obj}</a> '
                        f"to Container, or changing the type of {children_link} to Pool, to resolve this issue."
                    ),
                )
            else:  # TYPE_POOL
                messages.warning(
                    request,
                    mark_safe(
                        f"{obj} is a Pool prefix and should not contain other prefixes. {warning_msg} "
                        f'Consider either <a href="{edit_url}">changing the type of {obj}</a> '
                        f"to Container or Network, or deleting {children_link}, to resolve this issue."
                    ),
                )

        if obj.ip_addresses.exists() and obj.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            ip_warning_msg = (
                '<p>This <a href="'
                + static("docs/models/ipam/ipaddress.html")
                + '#ipaddress-parenting-concrete-relationship">will be considered invalid data</a> '
                "in a future release.</p>"
            )
            shortest_child_mask_length = min([ip.mask_length for ip in obj.ip_addresses.all()])
            if shortest_child_mask_length > obj.prefix_length:
                ip_link = '<a href="' + reverse("ipam:ipaddress_list") + f'?parent={obj.pk}">these IP addresses</a>'
                create_url = reverse("ipam:prefix_add") + urlencode(
                    {
                        "namespace": obj.namespace.pk,
                        "type": choices.PrefixTypeChoices.TYPE_NETWORK,
                        "prefix": obj.prefix,
                    }
                )
                messages.warning(
                    request,
                    mark_safe(
                        f"{obj} is a Container prefix and should not directly contain IP addresses. {ip_warning_msg} "
                        f'Consider either <a href="{edit_url}">changing the type of {obj}</a> to Network, or '
                        f'<a href="{create_url}">creating one or more child prefix(es) of type Network</a> to contain '
                        f"{ip_link}, to resolve this issue."
                    ),
                )
            else:
                messages.warning(
                    request,
                    mark_safe(
                        f"{obj} is a Container prefix and should not directly contain IP addresses. {ip_warning_msg} "
                        f'Consider <a href="{edit_url}">changing the type of {obj}</a> to Network '
                        "to resolve this issue."
                    ),
                )

        super().successful_post(request, obj, created, _logger)


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
    queryset = IPAddress.objects.select_related("tenant", "status", "role").annotate(
        interface_count=Count("interfaces"),
        interface_parent_count=(Count("interfaces__device", distinct=True)),
        vm_interface_count=Count("vm_interfaces"),
        vm_interface_parent_count=(Count("vm_interfaces__virtual_machine", distinct=True)),
        assigned_count=Count("interfaces") + Count("vm_interfaces"),
    )
    filterset = filters.IPAddressFilterSet
    filterset_form = forms.IPAddressFilterForm
    table = tables.IPAddressDetailTable
    template_name = "ipam/ipaddress_list.html"
    use_new_ui = True


class IPAddressView(generic.ObjectView):
    queryset = IPAddress.objects.select_related("tenant", "status", "role")
    use_new_ui = True

    def get_extra_context(self, request, instance):
        # Parent prefixes table
        parent_prefixes = (
            instance.ancestors().restrict(request.user, "view").select_related("location", "status", "role", "tenant")
        )
        parent_prefixes_table = tables.PrefixTable(list(parent_prefixes), orderable=False)

        # Related IP table
        related_ips = (
            instance.siblings()
            .restrict(request.user, "view")
            .select_related("role", "status", "tenant")
            .annotate(
                interface_count=Count("interfaces"),
                interface_parent_count=(Count("interfaces__device", distinct=True)),
                vm_interface_count=Count("vm_interfaces"),
                vm_interface_parent_count=(Count("vm_interfaces__virtual_machine", distinct=True)),
            )
        )
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

    def dispatch(self, request, *args, **kwargs):
        if "interface" in request.GET or "vminterface" in request.GET:
            _, error_msg = retrieve_interface_or_vminterface_from_request(request)
            if error_msg:
                messages.warning(request, error_msg)
                return redirect(request.GET.get("return_url", "ipam:ipaddress_add"))

        return super().dispatch(request, *args, **kwargs)

    def successful_post(self, request, obj, created, _logger):
        """Check for data that will be invalid in a future Nautobot release and warn the user if found."""
        # 3.0 TODO: remove this check after enabling strict enforcement of the equivalent logic in IPAddress.save()
        if obj.parent.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            warning_msg = (
                '<p>This <a href="'
                + static("docs/models/ipam/ipaddress.html")
                + '#ipaddress-parenting-concrete-relationship">will be considered invalid data</a> '
                "in a future release.</p>"
            )
            parent_link = f'<a href="{obj.parent.get_absolute_url()}">{obj.parent}</a>'
            if obj.parent.prefix_length < obj.mask_length:
                create_url = (
                    reverse("ipam:prefix_add")
                    + "?"
                    + urlencode(
                        {
                            "namespace": obj.parent.namespace.pk,
                            "prefix": str(netaddr.IPNetwork(f"{obj.host}/{obj.mask_length}")),
                            "type": choices.PrefixTypeChoices.TYPE_NETWORK,
                        }
                    )
                )
                messages.warning(
                    request,
                    mark_safe(
                        f"IP address {obj} currently has prefix {parent_link} as its parent, which is a Container. "
                        f'{warning_msg} Consider <a href="{create_url}">creating an intermediate /{obj.mask_length} '
                        "prefix of type Network</a> to resolve this issue."
                    ),
                )
            else:
                messages.warning(
                    request,
                    mark_safe(
                        f"IP address {obj} currently has prefix {parent_link} as its parent, which is a Container. "
                        f'{warning_msg} Consider <a href="'
                        + reverse("ipam:prefix_edit", kwargs={"pk": obj.parent.pk})
                        + '">changing the prefix</a> to type Network or Pool to resolve this issue.'
                    ),
                )

        # Add IpAddress to interface if interface is in query_params
        if "interface" in request.GET or "vminterface" in request.GET:
            interface, _ = retrieve_interface_or_vminterface_from_request(request)
            interface.ip_addresses.add(obj)

        super().successful_post(request, obj, created, _logger)

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

        _, error_msg = retrieve_interface_or_vminterface_from_request(request)
        if error_msg:
            messages.warning(request, error_msg)
            return redirect(request.GET.get("return_url", "ipam:ipaddress_add"))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        interface, _ = retrieve_interface_or_vminterface_from_request(request)
        form = forms.IPAddressAssignForm(data=request.GET)

        table = None
        if request.GET.get("q"):
            addresses = self.queryset.select_related("tenant").exclude(pk__in=interface.ip_addresses.values_list("pk"))
            table = tables.IPAddressAssignTable(addresses)
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(table)
            max_page_size = get_settings_or_config("MAX_PAGE_SIZE")
            if max_page_size and paginate["per_page"] > max_page_size:
                messages.warning(
                    request,
                    f'Requested "per_page" is too large. No more than {max_page_size} items may be displayed at a time.',
                )

        return render(
            request,
            "ipam/ipaddress_assign.html",
            {
                "form": form,
                "return_url": request.GET.get("return_url", ""),
                "table": table,
            },
        )

    def post(self, request):
        interface, _ = retrieve_interface_or_vminterface_from_request(request)

        if pks := request.POST.getlist("pk"):
            ip_addresses = IPAddress.objects.restrict(request.user, "view").filter(pk__in=pks)
            interface.ip_addresses.add(*ip_addresses)
            return redirect(request.GET.get("return_url"))

        return render(
            request,
            "ipam/ipaddress_assign.html",
            {
                "return_url": request.GET.get("return_url"),
            },
        )


class IPAddressMergeView(view_mixins.GetReturnURLMixin, view_mixins.ObjectPermissionRequiredMixin, View):
    queryset = IPAddress.objects.all()
    template_name = "ipam/ipaddress_merge.html"

    def get_required_permission(self):
        return get_permission_for_model(self.queryset.model, "change")

    def find_duplicate_ips(self, request, merged_attributes=None):
        """
        Present IP Addresses with the same host values.
        If not found, return to IPAddressListView with a helpful message.
        """
        if merged_attributes:
            host_values = (
                self.queryset.filter(host__gt=merged_attributes.get("host"))
                .values("host")
                .order_by("host")
                .annotate(count=models.Count("host"))
                .filter(count__gt=1)
            )
        else:
            host_values = (
                self.queryset.values("host").order_by("host").annotate(count=models.Count("host")).filter(count__gt=1)
            )
        if host_values:
            item = host_values[0]
            queryset = self.queryset.filter(host__in=[item["host"]])
            return render(
                request=request,
                template_name=self.template_name,
                context={
                    "queryset": queryset,
                    "return_url": self.get_return_url(request),
                },
            )
        else:
            msg = "No additional duplicate IPs found."
            messages.info(request, msg)
            return redirect(self.get_return_url(request))

    def get(self, request):
        return self.find_duplicate_ips(request)

    def post(self, request):
        collapsed_ips = IPAddress.objects.filter(pk__in=request.POST.getlist("pk"))
        merged_attributes = request.POST
        operation_invalid = len(collapsed_ips) < 2
        # Check if there are at least two IP addresses for us to merge
        # and if the skip button is pressed instead.
        if "_skip" not in request.POST and not operation_invalid:
            with cache.lock("ipaddress_merge", blocking_timeout=15, timeout=settings.REDIS_LOCK_TIMEOUT):
                with transaction.atomic():
                    namespace = Namespace.objects.get(pk=merged_attributes.get("namespace"))
                    status = Status.objects.get(pk=merged_attributes.get("status"))
                    # Retrieve all attributes from the request.
                    if merged_attributes.get("tenant"):
                        tenant = Tenant.objects.get(pk=merged_attributes.get("tenant"))
                    else:
                        tenant = None
                    if merged_attributes.get("role"):
                        role = Role.objects.get(pk=merged_attributes.get("role"))
                    else:
                        role = None
                    if merged_attributes.get("tags"):
                        tag_pk_list = merged_attributes.get("tags").split(",")
                        tags = Tag.objects.filter(pk__in=tag_pk_list)
                    else:
                        tags = []
                    if merged_attributes.get("nat_inside"):
                        nat_inside = IPAddress.objects.get(pk=merged_attributes.get("nat_inside"))
                    else:
                        nat_inside = None
                    # use IP in the same namespace as a reference.
                    ip_in_the_same_namespace = collapsed_ips.filter(parent__namespace=namespace).first()
                    merged_ip = IPAddress(
                        host=merged_attributes.get("host"),
                        ip_version=ip_in_the_same_namespace.ip_version,
                        parent=ip_in_the_same_namespace.parent,
                        type=merged_attributes.get("type"),
                        status=status,
                        role=role,
                        dns_name=merged_attributes.get("dns_name", ""),
                        description=merged_attributes.get("description"),
                        mask_length=merged_attributes.get("mask_length"),
                        tenant=tenant,
                        nat_inside=nat_inside,
                        _custom_field_data=ip_in_the_same_namespace._custom_field_data,
                    )
                    merged_ip.tags.set(tags)
                    # Update custom_field_data
                    for key in merged_ip._custom_field_data.keys():
                        ip_pk = merged_attributes.get("cf_" + key)
                        merged_ip._custom_field_data[key] = IPAddress.objects.get(pk=ip_pk)._custom_field_data[key]
                    # Update relationship data
                    handle_relationship_changes_when_merging_ips(merged_ip, merged_attributes, collapsed_ips)
                    # Capture relevant device pk_list before updating IPAddress to Interface Assignments.
                    # since the update will unset the primary_ip[4/6] field on the device.
                    # Collapsed_ips can only be one of the two families v4/v6
                    # One of the querysets here is bound to be emtpy and one of the updates to Device's primary_ip field
                    # is going to be a no-op
                    device_ip4 = list(Device.objects.filter(primary_ip4__in=collapsed_ips).values_list("pk", flat=True))
                    device_ip6 = list(Device.objects.filter(primary_ip6__in=collapsed_ips).values_list("pk", flat=True))
                    vm_ip4 = list(
                        VirtualMachine.objects.filter(primary_ip4__in=collapsed_ips).values_list("pk", flat=True)
                    )
                    vm_ip6 = list(
                        VirtualMachine.objects.filter(primary_ip6__in=collapsed_ips).values_list("pk", flat=True)
                    )

                    ip_to_interface_assignments = []
                    # Update IPAddress to Interface Assignments
                    for assignment in IPAddressToInterface.objects.filter(ip_address__in=collapsed_ips):
                        updated_attributes = model_to_dict(assignment)
                        updated_attributes["ip_address"] = merged_ip
                        updated_attributes["interface"] = Interface.objects.filter(
                            pk=updated_attributes["interface"]
                        ).first()
                        updated_attributes["vm_interface"] = VMInterface.objects.filter(
                            pk=updated_attributes["vm_interface"]
                        ).first()
                        ip_to_interface_assignments.append(updated_attributes)
                    # Update Service m2m field with IPAddresses
                    services = list(Service.objects.filter(ip_addresses__in=collapsed_ips).values_list("pk", flat=True))
                    # Delete Collapsed IPs
                    try:
                        _, deleted_info = collapsed_ips.delete()
                        deleted_count = deleted_info[IPAddress._meta.label]
                    except ProtectedError as e:
                        logger.info("Caught ProtectedError while attempting to delete objects")
                        handle_protectederror(collapsed_ips, request, e)
                        return redirect(self.get_return_url(request))
                    msg = (
                        f"Merged {deleted_count} {self.queryset.model._meta.verbose_name} "
                        f'into <a href="{merged_ip.get_absolute_url()}">{escape(merged_ip)}</a>'
                    )
                    logger_msg = f"Merged {deleted_count} {self.queryset.model._meta.verbose_name} into {merged_ip}"
                    merged_ip.validated_save()
                    # After some testing
                    # We have to update the ForeignKey fields after merged_ip is saved to make the operation valid
                    for assignment in ip_to_interface_assignments:
                        IPAddressToInterface.objects.create(**assignment)
                    # Update Device primary_ip fields of the Collapsed IPs
                    Device.objects.filter(pk__in=device_ip4).update(primary_ip4=merged_ip)
                    Device.objects.filter(pk__in=device_ip6).update(primary_ip6=merged_ip)
                    VirtualMachine.objects.filter(pk__in=vm_ip4).update(primary_ip4=merged_ip)
                    VirtualMachine.objects.filter(pk__in=vm_ip6).update(primary_ip6=merged_ip)
                    for service in services:
                        Service.objects.get(pk=service).ip_addresses.add(merged_ip)
                    logger.info(logger_msg)
                    messages.success(request, mark_safe(msg))
        return self.find_duplicate_ips(request, merged_attributes)


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
    queryset = IPAddress.objects.select_related("role", "status", "tenant").annotate(
        interface_count=Count("interfaces"),
        interface_parent_count=(Count("interfaces__device", distinct=True)),
        vm_interface_count=Count("vm_interfaces"),
        vm_interface_parent_count=(Count("vm_interfaces__virtual_machine", distinct=True)),
    )
    filterset = filters.IPAddressFilterSet
    table = tables.IPAddressTable
    form = forms.IPAddressBulkEditForm


class IPAddressBulkDeleteView(generic.BulkDeleteView):
    # queryset = IPAddress.objects.select_related("status", "role", "tenant", "vrf__tenant")
    queryset = IPAddress.objects.select_related("role", "status", "tenant").annotate(
        interface_count=Count("interfaces"),
        interface_parent_count=(Count("interfaces__device", distinct=True)),
        vm_interface_count=Count("vm_interfaces"),
        vm_interface_parent_count=(Count("vm_interfaces__virtual_machine", distinct=True)),
    )
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
            "bulk_querystring": f"vlan_group={instance.pk}",
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
    action_buttons = ("add", "import", "export")


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
