import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction
from django.db.models import Prefetch, ProtectedError, Q
from django.forms.models import model_to_dict
from django.shortcuts import get_object_or_404, redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.utils.html import format_html
from django.utils.http import urlencode
from django.views.generic import View
from django_tables2 import RequestConfig
import netaddr
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.cloud.tables import CloudNetworkTable
from nautobot.core.choices import ButtonActionColorChoices
from nautobot.core.constants import MAX_PAGE_SIZE_DEFAULT
from nautobot.core.models.querysets import count_related
from nautobot.core.ui import object_detail
from nautobot.core.ui.choices import SectionChoices
from nautobot.core.utils.config import get_settings_or_config
from nautobot.core.utils.permissions import get_permission_for_model
from nautobot.core.views import generic, mixins as view_mixins
from nautobot.core.views.paginator import EnhancedPaginator, get_paginate_count
from nautobot.core.views.utils import handle_protectederror
from nautobot.core.views.viewsets import NautobotUIViewSet
from nautobot.dcim.models import Device, Interface, Location
from nautobot.extras.models import Role, SavedView, Status, Tag
from nautobot.ipam import choices, constants
from nautobot.ipam.api import serializers
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import VirtualMachine, VMInterface

from . import filters, forms, tables
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
    get_add_available_ipaddresses_callback,
    get_add_available_prefixes_callback,
    get_add_available_vlans_callback,
    handle_relationship_changes_when_merging_ips,
    retrieve_interface_or_vminterface_from_request,
)

logger = logging.getLogger(__name__)

#
# Namespaces
#


class NamespaceUIViewSet(NautobotUIViewSet):
    form_class = forms.NamespaceForm
    bulk_update_form_class = forms.NamespaceBulkEditForm
    filterset_class = filters.NamespaceFilterSet
    filterset_form_class = forms.NamespaceFilterForm
    queryset = Namespace.objects.all()
    serializer_class = serializers.NamespaceSerializer
    table_class = tables.NamespaceTable
    object_detail_content = object_detail.ObjectDetailContent(
        panels=(object_detail.ObjectFieldsPanel(section=SectionChoices.LEFT_HALF, weight=100, fields="__all__"),),
        extra_tabs=(
            object_detail.DistinctViewTab(
                weight=800,
                tab_id="vrfs",
                label="VRFs",
                url_name="ipam:namespace_vrfs",
                related_object_attribute="vrfs",
            ),
            object_detail.DistinctViewTab(
                weight=900,
                tab_id="prefixes",
                label="Prefixes",
                url_name="ipam:namespace_prefixes",
                related_object_attribute="prefixes",
            ),
            object_detail.DistinctViewTab(
                weight=1000,
                tab_id="ip_addresses",
                label="IP Addresses",
                url_name="ipam:namespace_ip_addresses",
                related_object_attribute="ip_addresses",
            ),
        ),
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        context.update({"object_detail_content": self.object_detail_content})
        return context

    @action(detail=True, url_path="vrfs")
    def vrfs(self, request, *args, **kwargs):
        instance = self.get_object()
        vrfs = instance.vrfs.restrict(request.user, "view")
        vrf_table = tables.VRFTable(
            data=vrfs,
            user=request.user,
            exclude=["namespace"],
        )
        if request.user.has_perm("ipam.change_vrf") or request.user.has_perm("ipam.delete_vrf"):
            vrf_table.columns.show("pk")

        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(vrf_table)
        return Response(
            {
                "vrf_table": vrf_table,
                "active_tab": "vrfs",
            }
        )

    @action(detail=True, url_path="prefixes")
    def prefixes(self, request, *args, **kwargs):
        instance = self.get_object()
        prefixes = instance.prefixes.restrict(request.user, "view").select_related("status")
        prefix_table = tables.PrefixTable(data=prefixes, user=request.user, exclude=["namespace"])
        if request.user.has_perm("ipam.change_prefix") or request.user.has_perm("ipam.delete_prefix"):
            prefix_table.columns.show("pk")

        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(prefix_table)
        return Response(
            {
                "prefix_table": prefix_table,
                "active_tab": "prefixes",
            }
        )

    @action(detail=True, url_path="ip-addresses", url_name="ip_addresses")
    def ip_addresses(self, request, *args, **kwargs):
        instance = self.get_object()
        ip_addresses = instance.ip_addresses.restrict(request.user, "view").select_related("role", "status", "tenant")
        ip_address_table = tables.IPAddressTable(data=ip_addresses, user=request.user, exclude=["namespace"])
        if request.user.has_perm("ipam.change_ipaddress") or request.user.has_perm("ipam.delete_ipaddress"):
            ip_address_table.columns.show("pk")

        RequestConfig(
            request, paginate={"paginator_class": EnhancedPaginator, "per_page": get_paginate_count(request)}
        ).configure(ip_address_table)
        return Response(
            {
                "ip_address_table": ip_address_table,
                "active_tab": "ip_addresses",
            }
        )


#
# VRFs
#


class VRFUIViewSet(NautobotUIViewSet):
    queryset = VRF.objects.all()
    filterset_class = filters.VRFFilterSet
    filterset_form_class = forms.VRFFilterForm
    table_class = tables.VRFTable
    form_class = forms.VRFForm
    bulk_update_form_class = forms.VRFBulkEditForm
    serializer_class = serializers.VRFSerializer

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                table_class=tables.RouteTargetTable,
                table_filter="importing_vrfs",
                table_title="Import Route Targets",
                add_button_route=None,
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                table_class=tables.RouteTargetTable,
                table_filter="exporting_vrfs",
                table_title="Export Route Targets",
                add_button_route=None,
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=100,
                table_class=tables.PrefixTable,
                table_filter="vrfs",
                table_title="Assigned Prefixes",
                hide_hierarchy_ui=True,
                exclude_columns=["namespace"],
                add_button_route=None,
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=200,
                table_class=tables.VRFDeviceAssignmentTable,
                table_filter="vrf",
                table_title="Assigned Devices",
                exclude_columns=["vrf", "namespace", "rd"],
                add_button_route=None,
            ),
        ),
    )


#
# Route targets
#


class RouteTargetUIViewSet(NautobotUIViewSet):
    queryset = RouteTarget.objects.all()
    filterset_class = filters.RouteTargetFilterSet
    filterset_form_class = forms.RouteTargetFilterForm
    table_class = tables.RouteTargetTable
    form_class = forms.RouteTargetForm
    bulk_update_form_class = forms.RouteTargetBulkEditForm
    serializer_class = serializers.RouteTargetSerializer

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=100,
                table_class=tables.VRFTable,
                table_filter="import_targets",
                table_title="Importing VRFs",
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.RIGHT_HALF,
                weight=200,
                table_class=tables.VRFTable,
                table_filter="export_targets",
                table_title="Exporting VRFs",
            ),
        ),
    )


#
# RIRs
#


class RIRUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.RIRBulkEditForm
    filterset_class = filters.RIRFilterSet
    filterset_form_class = forms.RIRFilterForm
    form_class = forms.RIRForm
    queryset = RIR.objects.all()
    serializer_class = serializers.RIRSerializer
    table_class = tables.RIRTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields="__all__",
            ),
            object_detail.ObjectsTablePanel(
                section=SectionChoices.FULL_WIDTH,
                weight=100,
                table_title="Assigned Prefixes",
                table_class=tables.PrefixTable,
                table_filter="rir",
                hide_hierarchy_ui=True,
            ),
        ),
    )


#
# Prefixes
#


class PrefixListView(generic.ObjectListView):
    filterset = filters.PrefixFilterSet
    filterset_form = forms.PrefixFilterForm
    table = tables.PrefixDetailTable
    template_name = "ipam/prefix_list.html"
    queryset = Prefix.objects.all()


class PrefixView(generic.ObjectView):
    queryset = Prefix.objects.select_related(
        "parent",
        "rir",
        "role",
        "status",
        "tenant__tenant_group",
        "vlan__vlan_group",
        "namespace",
    ).prefetch_related("locations")

    def get_extra_context(self, request, instance):
        # Parent prefixes table
        parent_prefixes = instance.ancestors().restrict(request.user, "view")
        parent_prefix_table = tables.PrefixTable(parent_prefixes, exclude=["namespace"])

        vrfs = instance.vrf_assignments.restrict(request.user, "view")
        vrf_table = tables.VRFPrefixAssignmentTable(vrfs, orderable=False)

        cloud_networks = instance.cloud_networks.restrict(request.user, "view")
        cloud_network_table = CloudNetworkTable(cloud_networks, orderable=False)
        cloud_network_table.exclude = ("actions", "assigned_prefix_count", "circuit_count", "cloud_service_count")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(parent_prefix_table)
        RequestConfig(request, paginate).configure(vrf_table)
        RequestConfig(request, paginate).configure(cloud_network_table)

        return {
            "vrf_table": vrf_table,
            "parent_prefix_table": parent_prefix_table,
            "cloud_network_table": cloud_network_table,
            **super().get_extra_context(request, instance),
        }


class PrefixPrefixesView(generic.ObjectView):
    queryset = Prefix.objects.all()
    template_name = "ipam/prefix_prefixes.html"

    def get_extra_context(self, request, instance):
        # Child prefixes table
        child_prefixes = instance.descendants().restrict(request.user, "view")

        # Add available prefixes to the table if requested
        data_transform_callback = get_add_available_prefixes_callback(
            show_available=request.GET.get("show_available", "true") == "true", parent=instance
        )

        prefix_table = tables.PrefixDetailTable(
            child_prefixes,
            exclude=["namespace"],
            data_transform_callback=data_transform_callback,
        )
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
            "base_tree_depth": instance.ancestors().count(),
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
        ipaddresses = instance.get_all_ips().restrict(request.user, "view")

        # Add available IP addresses to the table if requested
        data_transform_callback = get_add_available_ipaddresses_callback(
            show_available=request.GET.get("show_available", "true") == "true", parent=instance
        )

        ip_table = tables.IPAddressTable(
            ipaddresses, exclude=["parent__namespace"], data_transform_callback=data_transform_callback
        )
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
        warning_msg = format_html(
            '<p>This <a href="{}#prefix-hierarchy">will be considered invalid data</a> in a future release.</p>',
            static("docs/models/ipam/prefix.html"),
        )
        if obj.parent and obj.parent.type != constants.PREFIX_ALLOWED_PARENT_TYPES[obj.type]:
            parent_edit_url = reverse("ipam:prefix_edit", kwargs={"pk": obj.parent.pk})
            messages.warning(
                request,
                format_html(
                    '{} is a {} prefix but its parent <a href="{}">{}</a> is a {}. {} Consider '
                    '<a href="{}">changing the type of {}</a> and/or <a href="{}">{}</a> to resolve this issue.',
                    obj,
                    obj.type.title(),
                    obj.parent.get_absolute_url(),
                    obj.parent,
                    obj.parent.type.title(),
                    warning_msg,
                    edit_url,
                    obj,
                    parent_edit_url,
                    obj.parent,
                ),
            )

        invalid_children = obj.children.filter(
            ~Q(type__in=constants.PREFIX_ALLOWED_CHILD_TYPES[obj.type]),  # exclude valid children
        )

        if invalid_children.exists():
            children_link = format_html('<a href="{}?parent={}">its children</a>', reverse("ipam:prefix_list"), obj.pk)
            if obj.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
                messages.warning(
                    request,
                    format_html(
                        "{} is a Container prefix and should not contain child prefixes of type Pool. {} "
                        "Consider creating an intermediary Network prefix, or changing the type of {} to Network, "
                        "to resolve this issue.",
                        obj,
                        warning_msg,
                        children_link,
                    ),
                )
            elif obj.type == choices.PrefixTypeChoices.TYPE_NETWORK:
                messages.warning(
                    request,
                    format_html(
                        "{} is a Network prefix and should not contain child prefixes of types Container or Network. "
                        '{} Consider <a href="{}">changing the type of {}</a> to Container, '
                        "or changing the type of {} to Pool, to resolve this issue.",
                        obj,
                        warning_msg,
                        edit_url,
                        obj,
                        children_link,
                    ),
                )
            else:  # TYPE_POOL
                messages.warning(
                    request,
                    format_html(
                        "{} is a Pool prefix and should not contain other prefixes. {} "
                        'Consider either <a href="{}">changing the type of {}</a> to Container or Network, '
                        "or deleting {}, to resolve this issue.",
                        obj,
                        warning_msg,
                        edit_url,
                        obj,
                        children_link,
                    ),
                )

        if obj.ip_addresses.exists() and obj.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            ip_warning_msg = format_html(
                '<p>This <a href="{}#ipaddress-parenting-concrete-relationship">will be considered invalid data</a> '
                "in a future release.</p>",
                static("docs/models/ipam/ipaddress.html"),
            )
            shortest_child_mask_length = min([ip.mask_length for ip in obj.ip_addresses.all()])
            if shortest_child_mask_length > obj.prefix_length:
                ip_link = format_html(
                    '<a href="{}?parent={}">these IP addresses</a>', reverse("ipam:ipaddress_list"), obj.pk
                )
                create_url = reverse("ipam:prefix_add") + urlencode(
                    {
                        "namespace": obj.namespace.pk,
                        "type": choices.PrefixTypeChoices.TYPE_NETWORK,
                        "prefix": obj.prefix,
                    }
                )
                messages.warning(
                    request,
                    format_html(
                        "{} is a Container prefix and should not directly contain IP addresses. {} "
                        'Consider either <a href="{}">changing the type of {}</a> to Network, '
                        'or <a href="{}">creating one or more child prefix(es) of type Network</a> to contain {}, '
                        "to resolve this issue.",
                        obj,
                        ip_warning_msg,
                        edit_url,
                        obj,
                        create_url,
                        ip_link,
                    ),
                )
            else:
                messages.warning(
                    request,
                    format_html(
                        "{} is a Container prefix and should not directly contain IP addresses. {} "
                        'Consider <a href="{}">changing the type of {}</a> to Network to resolve this issue.',
                        obj,
                        ip_warning_msg,
                        edit_url,
                        obj,
                    ),
                )

        super().successful_post(request, obj, created, _logger)


class PrefixDeleteView(generic.ObjectDeleteView):
    queryset = Prefix.objects.all()
    template_name = "ipam/prefix_delete.html"


class PrefixBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = Prefix.objects.all()
    table = tables.PrefixTable


class PrefixBulkEditView(generic.BulkEditView):
    queryset = Prefix.objects.all()
    filterset = filters.PrefixFilterSet
    table = tables.PrefixTable
    form = forms.PrefixBulkEditForm


class PrefixBulkDeleteView(generic.BulkDeleteView):
    queryset = Prefix.objects.all()
    filterset = filters.PrefixFilterSet
    table = tables.PrefixTable


#
# IP addresses
#


class IPAddressListView(generic.ObjectListView):
    queryset = IPAddress.objects.all()
    filterset = filters.IPAddressFilterSet
    filterset_form = forms.IPAddressFilterForm
    table = tables.IPAddressDetailTable
    template_name = "ipam/ipaddress_list.html"

    def alter_queryset(self, request):
        queryset = super().alter_queryset(request)

        # All of the below is just to determine whether we are displaying the "assigned_count" column, and if so,
        # perform the relevant queryset annotation. Ref: nautobot/nautobot#6605
        if request.user is None or isinstance(request.user, AnonymousUser):
            table_columns = None
        else:
            table_columns = request.user.get_config("tables.IPAddressDetailTable.columns")
        current_saved_view_pk = request.GET.get("saved_view", None)
        if current_saved_view_pk:
            try:
                current_saved_view = SavedView.objects.get(view="ipam:ipaddress_list", pk=current_saved_view_pk)
                view_table_config = current_saved_view.config.get("table_config", {}).get("IPAddressDetailTable", None)
                if view_table_config is not None:
                    table_columns = view_table_config.get("columns", table_columns)
            except ObjectDoesNotExist:
                pass

        # column name is "assigned", not "assigned_count", and it's shown by default if there is no table config
        if (table_columns and "assigned" in table_columns) or not table_columns:
            queryset = queryset.annotate(
                assigned_count=count_related(Interface, "ip_addresses") + count_related(VMInterface, "ip_addresses"),
            )
        return queryset


class IPAddressView(generic.ObjectView):
    queryset = IPAddress.objects.select_related("tenant", "status", "role")

    def get_extra_context(self, request, instance):
        # Parent prefixes table
        parent_prefixes = instance.ancestors().restrict(request.user, "view")
        parent_prefixes_table = tables.PrefixTable(parent_prefixes, orderable=False)

        # Related IP table
        related_ips = (
            instance.siblings()
            .restrict(request.user, "view")
            .select_related("role", "status", "tenant")
            .annotate(
                interface_count=count_related(Interface, "ip_addresses"),
                interface_parent_count=count_related(Device, "interfaces__ip_addresses", distinct=True),
                vm_interface_count=count_related(VMInterface, "ip_addresses"),
                vm_interface_parent_count=count_related(VirtualMachine, "interfaces__ip_addresses", distinct=True),
            )
        )
        related_ips_table = tables.IPAddressTable(related_ips, orderable=False)

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(parent_prefixes_table)
        RequestConfig(request, paginate).configure(related_ips_table)

        return {
            "parent_prefixes_table": parent_prefixes_table,
            "related_ips_table": related_ips_table,
            **super().get_extra_context(request, instance),
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
                return redirect(self.get_return_url(request, default_return_url="ipam:ipaddress_add"))

        return super().dispatch(request, *args, **kwargs)

    def successful_post(self, request, obj, created, _logger):
        """Check for data that will be invalid in a future Nautobot release and warn the user if found."""
        # 3.0 TODO: remove this check after enabling strict enforcement of the equivalent logic in IPAddress.save()
        if obj.parent.type == choices.PrefixTypeChoices.TYPE_CONTAINER:
            warning_msg = format_html(
                '<p>This <a href="{}#ipaddress-parenting-concrete-relationship">will be considered invalid data</a> '
                "in a future release.</p>",
                static("docs/models/ipam/ipaddress.html"),
            )
            parent_link = format_html('<a href="{}">{}</a>', obj.parent.get_absolute_url(), obj.parent)
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
                    format_html(
                        "IP address {} currently has prefix {} as its parent, which is a Container. {} "
                        'Consider <a href="{}">creating an intermediate /{} prefix of type Network</a> '
                        "to resolve this issue.",
                        obj,
                        parent_link,
                        warning_msg,
                        create_url,
                        obj.mask_length,
                    ),
                )
            else:
                messages.warning(
                    request,
                    format_html(
                        "IP address {} currently has prefix {} as its parent, which is a Container. {} "
                        'Consider <a href="{}">changing the prefix</a> to type Network or Pool to resolve this issue.',
                        obj,
                        parent_link,
                        warning_msg,
                        reverse("ipam:prefix_edit", kwargs={"pk": obj.parent.pk}),
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
class IPAddressAssignView(view_mixins.GetReturnURLMixin, generic.ObjectView):
    """
    Search for IPAddresses to be assigned to an Interface.
    """

    queryset = IPAddress.objects.all()

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            # Redirect user if an interface has not been provided
            if "interface" not in request.GET and "vminterface" not in request.GET:
                return redirect(self.get_return_url(request, default_return_url="ipam:ipaddress_add"))

            _, error_msg = retrieve_interface_or_vminterface_from_request(request)
            if error_msg:
                messages.warning(request, error_msg)
                return redirect(self.get_return_url(request, default_return_url="ipam:ipaddress_add"))

        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        interface, _ = retrieve_interface_or_vminterface_from_request(request)
        form = forms.IPAddressAssignForm(data=request.GET)

        table = None
        if request.GET.get("q"):
            addresses = (
                self.queryset.select_related("parent__namespace", "role", "status", "tenant")
                .exclude(pk__in=interface.ip_addresses.values_list("pk"))
                .string_search(request.GET.get("q"))
            )
            table = tables.IPAddressAssignTable(addresses)
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(table)
            max_page_size = get_settings_or_config("MAX_PAGE_SIZE", fallback=MAX_PAGE_SIZE_DEFAULT)
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
                "return_url": self.get_return_url(request),
                "table": table,
            },
        )

    def post(self, request):
        interface, _ = retrieve_interface_or_vminterface_from_request(request)

        if pks := request.POST.getlist("pk"):
            ip_addresses = IPAddress.objects.restrict(request.user, "view").filter(pk__in=pks)
            interface.ip_addresses.add(*ip_addresses)
            return redirect(self.get_return_url(request))
        messages.error(request, "Please select at least one IP Address from the table.")
        return redirect(request.get_full_path())


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
            with cache.lock(
                "nautobot.ipam.views.ipaddress_merge", blocking_timeout=15, timeout=settings.REDIS_LOCK_TIMEOUT
            ):
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
                    msg = format_html(
                        'Merged {} {} into <a href="{}">{}</a>',
                        deleted_count,
                        self.queryset.model._meta.verbose_name,
                        merged_ip.get_absolute_url(),
                        merged_ip,
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
                    messages.success(request, msg)
        return self.find_duplicate_ips(request, merged_attributes)


class IPAddressDeleteView(generic.ObjectDeleteView):
    queryset = IPAddress.objects.all()


class IPAddressBulkCreateView(generic.BulkCreateView):
    queryset = IPAddress.objects.all()
    form = forms.IPAddressBulkCreateForm
    model_form = forms.IPAddressBulkAddForm
    pattern_target = "address"
    template_name = "ipam/ipaddress_bulk_add.html"


class IPAddressBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = IPAddress.objects.all()
    table = tables.IPAddressTable


class IPAddressBulkEditView(generic.BulkEditView):
    # queryset = IPAddress.objects.select_related("status", "role", "tenant", "vrf__tenant")
    queryset = IPAddress.objects.select_related("role", "status", "tenant").annotate(
        interface_count=count_related(Interface, "ip_addresses"),
        interface_parent_count=count_related(Device, "interfaces__ip_addresses", distinct=True),
        vm_interface_count=count_related(VMInterface, "ip_addresses"),
        vm_interface_parent_count=count_related(VirtualMachine, "interfaces__ip_addresses", distinct=True),
    )
    filterset = filters.IPAddressFilterSet
    table = tables.IPAddressTable
    form = forms.IPAddressBulkEditForm


class IPAddressBulkDeleteView(generic.BulkDeleteView):
    # queryset = IPAddress.objects.select_related("status", "role", "tenant", "vrf__tenant")
    queryset = IPAddress.objects.select_related("role", "status", "tenant").annotate(
        interface_count=count_related(Interface, "ip_addresses"),
        interface_parent_count=count_related(Device, "interfaces__ip_addresses", distinct=True),
        vm_interface_count=count_related(VMInterface, "ip_addresses"),
        vm_interface_parent_count=count_related(VirtualMachine, "interfaces__ip_addresses", distinct=True),
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

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(interface_table)

        return {
            "interface_table": interface_table,
            "active_tab": "interfaces",
        }


class IPAddressVMInterfacesView(generic.ObjectView):
    queryset = IPAddress.objects.all()
    template_name = "ipam/ipaddress_vm_interfaces.html"

    def get_extra_context(self, request, instance):
        vm_interfaces = instance.vm_interfaces.restrict(request.user, "view").prefetch_related(
            Prefetch("ip_addresses", queryset=IPAddress.objects.restrict(request.user)),
        )
        vm_interface_table = tables.IPAddressVMInterfaceTable(data=vm_interfaces, user=request.user, orderable=False)
        if request.user.has_perm("virtualization.change_vminterface") or request.user.has_perm(
            "virtualization.delete_vminterface"
        ):
            vm_interface_table.columns.show("pk")

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(vm_interface_table)

        return {
            "vm_interface_table": vm_interface_table,
            "active_tab": "vm_interfaces",
        }


#
# IPAddress to Interface (assignments
#


class IPAddressToInterfaceUIViewSet(view_mixins.ObjectBulkCreateViewMixin):  # 3.0 TODO: use ObjectListViewMixin instead
    """
    ViewSet for IP Address (VM)Interface assignments.

    This view intentionally only implements bulk import at this time. Accessing list view will
    redirect to the import view.
    """

    lookup_field = "pk"
    # form_class = forms.NamespaceForm
    filterset_class = filters.IPAddressToInterfaceFilterSet
    queryset = IPAddressToInterface.objects.all()
    serializer_class = serializers.IPAddressToInterfaceSerializer
    table_class = tables.IPAddressToInterfaceTable
    action_buttons = ("import", "export")

    def list(self, request, *args, **kwargs):
        """Redirect list view to import view."""
        return redirect(reverse("ipam:ipaddresstointerface_import"))


#
# VLAN groups
#


class VLANGroupUIViewSet(NautobotUIViewSet):
    bulk_update_form_class = forms.VLANGroupBulkEditForm
    filterset_class = filters.VLANGroupFilterSet
    filterset_form_class = forms.VLANGroupFilterForm
    form_class = forms.VLANGroupForm
    queryset = VLANGroup.objects.all()
    serializer_class = serializers.VLANGroupSerializer
    table_class = tables.VLANGroupTable

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
                context_table_key="vlan_table",
                related_field_name="vlan_group",
                enable_bulk_actions=True,
                add_button_route=None,
                form_id="vlan_form",
                footer_buttons=[
                    object_detail.FormButton(
                        link_name="ipam:vlan_bulk_edit",
                        link_includes_pk=False,
                        label="Edit Selected",
                        color=ButtonActionColorChoices.EDIT,
                        icon="mdi-pencil",
                        size="xs",
                        form_id="vlan_form",
                        weight=200,
                    ),
                    object_detail.FormButton(
                        link_name="ipam:vlan_bulk_delete",
                        link_includes_pk=False,
                        label="Delete Selected",
                        color=ButtonActionColorChoices.DELETE,
                        icon="mdi-trash-can-outline",
                        size="xs",
                        form_id="vlan_form",
                        weight=100,
                    ),
                ],
            ),
        )
    )

    def get_extra_context(self, request, instance):
        context = super().get_extra_context(request, instance)
        if self.action == "retrieve":
            vlans = (
                VLAN.objects.restrict(request.user, "view")
                .filter(vlan_group=instance)
                .prefetch_related(Prefetch("prefixes", queryset=Prefix.objects.restrict(request.user)))
            )
            data_transform_callback = get_add_available_vlans_callback(show_available=True, vlan_group=instance)
            vlan_table = tables.VLANDetailTable(
                vlans, exclude=["vlan_group"], data_transform_callback=data_transform_callback
            )
            paginate = {
                "paginator_class": EnhancedPaginator,
                "per_page": get_paginate_count(request),
            }
            RequestConfig(request, paginate).configure(vlan_table)
            context.update(
                {
                    "bulk_querystring": f"vlan_group={instance.pk}",
                    "vlan_table": vlan_table,
                    "badge_count_override": vlans.count(),
                }
            )
        return context


#
# VLANs
#


class VLANListView(generic.ObjectListView):
    queryset = VLAN.objects.all()
    filterset = filters.VLANFilterSet
    filterset_form = forms.VLANFilterForm
    table = tables.VLANDetailTable


class VLANView(generic.ObjectView):
    queryset = VLAN.objects.annotate(location_count=count_related(Location, "vlans")).select_related(
        "role",
        "status",
        "tenant__tenant_group",
    )

    def get_extra_context(self, request, instance):
        prefixes = (
            Prefix.objects.restrict(request.user, "view")
            .filter(vlan=instance)
            .select_related(
                "status",
                "role",
                # "vrf",
                "namespace",
            )
        )
        prefix_table = tables.PrefixTable(list(prefixes), hide_hierarchy_ui=True, exclude=["vlan"])

        paginate = {
            "paginator_class": EnhancedPaginator,
            "per_page": get_paginate_count(request),
        }
        RequestConfig(request, paginate).configure(prefix_table)

        return {"prefix_table": prefix_table, **super().get_extra_context(request, instance)}


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


class VLANBulkImportView(generic.BulkImportView):  # 3.0 TODO: remove, unused
    queryset = VLAN.objects.all()
    table = tables.VLANTable


class VLANBulkEditView(generic.BulkEditView):
    queryset = VLAN.objects.select_related(
        "vlan_group",
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
        "status",
        "tenant",
        "role",
    )
    filterset = filters.VLANFilterSet
    table = tables.VLANTable


#
# Services
#


class ServiceEditView(generic.ObjectEditView):  # This view is used to assign services to devices and VMs
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


class ServiceUIViewSet(NautobotUIViewSet):  # 3.0 TODO: remove, unused BulkImportView
    model = Service
    bulk_update_form_class = forms.ServiceBulkEditForm
    filterset_class = filters.ServiceFilterSet
    filterset_form_class = forms.ServiceFilterForm
    form_class = forms.ServiceForm
    queryset = Service.objects.select_related("device", "virtual_machine").prefetch_related("ip_addresses")
    serializer_class = serializers.ServiceSerializer
    table_class = tables.ServiceTable

    object_detail_content = object_detail.ObjectDetailContent(
        panels=(
            object_detail.ObjectFieldsPanel(
                section=SectionChoices.LEFT_HALF,
                weight=100,
                fields=["name", "parent", "protocol", "port_list", "description"],
            ),
            object_detail.ObjectsTablePanel(
                weight=200,
                section=SectionChoices.RIGHT_HALF,
                table_class=tables.IPAddressTable,
                table_filter="services",
                select_related_fields=["tenant", "status", "role"],
                add_button_route=None,
            ),
        )
    )
