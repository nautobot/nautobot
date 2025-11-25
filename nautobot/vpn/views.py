"""Views for the vpn models."""

import logging

from django.core.exceptions import ValidationError
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot.apps.ui import ObjectDetailContent, ObjectFieldsPanel, ObjectsTablePanel, SectionChoices
from nautobot.apps.views import NautobotUIViewSet
from nautobot.core.templatetags import helpers
from nautobot.core.ui import object_detail
from nautobot.extras.tables import DynamicGroupTable
from nautobot.ipam.tables import PrefixTable

from . import filters, forms, models, tables
from .api import serializers

logger = logging.getLogger(__name__)


class VPNProfileUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNProfile."""

    bulk_update_form_class = forms.VPNProfileBulkEditForm
    filterset_class = filters.VPNProfileFilterSet
    filterset_form_class = forms.VPNProfileFilterForm
    form_class = forms.VPNProfileForm
    lookup_field = "pk"
    queryset = models.VPNProfile.objects.all()
    serializer_class = serializers.VPNProfileSerializer
    table_class = tables.VPNProfileTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "description",
                    "keepalive_enabled",
                    "keepalive_interval",
                    "keepalive_retries",
                    "nat_traversal",
                    "secrets_group",
                    "role",
                    "tenant",
                    "extra_options",
                ],
            ),
            ObjectsTablePanel(
                weight=100,
                table_class=tables.VPNProfilePhase1PolicyAssignmentTable,
                table_filter="vpn_profile",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[],
                show_table_config_button=False,
                related_list_url_name="vpn:vpnphase1policy_list",
                related_field_name="vpn_profiles",
            ),
            ObjectsTablePanel(
                weight=200,
                table_class=tables.VPNProfilePhase2PolicyAssignmentTable,
                table_filter="vpn_profile",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[],
                show_table_config_button=False,
                related_list_url_name="vpn:vpnphase2policy_list",
                related_field_name="vpn_profiles",
            ),
        ],
        extra_tabs=[
            object_detail.DistinctViewTab(
                weight=object_detail.Tab.WEIGHT_CHANGELOG_TAB + 100,
                tab_id="vpn_vpns",
                label="VPNs",
                url_name="vpn:vpnprofile_vpns",
                related_object_attribute="vpns",
                hide_if_empty=True,
                panels=(
                    object_detail.ObjectsTablePanel(
                        weight=100,
                        section=SectionChoices.FULL_WIDTH,
                        table_title="VPNs",
                        table_class=tables.VPNTable,
                        table_attribute="vpns",
                        related_field_name="vpn_profile",
                        select_related_fields=["role"],
                        exclude_columns=["vpn_profile"],
                        tab_id="vpns",
                        enable_bulk_actions=True,
                        include_paginator=True,
                    ),
                ),
            ),
            object_detail.DistinctViewTab(
                weight=object_detail.Tab.WEIGHT_CHANGELOG_TAB + 200,
                tab_id="vpn_tunnels",
                label="VPN Tunnels",
                url_name="vpn:vpnprofile_vpntunnels",
                related_object_attribute="vpn_tunnels",
                hide_if_empty=True,
                panels=(
                    object_detail.ObjectsTablePanel(
                        weight=100,
                        section=SectionChoices.FULL_WIDTH,
                        table_title="VPN Tunnels",
                        table_class=tables.VPNTunnelTable,
                        table_attribute="vpn_tunnels",
                        related_field_name="vpn_profile",
                        select_related_fields=["endpoint_a", "endpoint_z", "role"],
                        exclude_columns=["vpn_profile"],
                        tab_id="vpn_tunnels",
                        enable_bulk_actions=True,
                        include_paginator=True,
                    ),
                ),
            ),
            object_detail.DistinctViewTab(
                weight=object_detail.Tab.WEIGHT_CHANGELOG_TAB + 300,
                tab_id="vpn_endpoints",
                label="VPN Endpoints",
                url_name="vpn:vpnprofile_vpnendpoints",
                related_object_attribute="vpn_tunnel_endpoints",
                hide_if_empty=True,
                panels=(
                    object_detail.ObjectsTablePanel(
                        weight=100,
                        section=SectionChoices.FULL_WIDTH,
                        table_title="VPN Endpoints",
                        table_class=tables.VPNTunnelEndpointTable,
                        table_attribute="vpn_tunnel_endpoints",
                        related_field_name="vpn_profile",
                        select_related_fields=["source_interface", "role"],
                        exclude_columns=["vpn_profile"],
                        tab_id="vpn_endpoints",
                        enable_bulk_actions=True,
                        include_paginator=True,
                    ),
                ),
            ),
        ],
    )

    def get_extra_context(self, request, instance=None):
        ctx = super().get_extra_context(request, instance)

        if self.action in ["create", "update"]:
            ctx["vpn_phase1_policies"] = forms.VPNProfilePh1FormSet(
                instance=instance,
                data=request.POST if request.method == "POST" else None,
            )
            ctx["vpn_phase2_policies"] = forms.VPNProfilePh2FormSet(
                instance=instance,
                data=request.POST if request.method == "POST" else None,
            )
        return ctx

    @action(
        detail=True,
        url_path="vpn-vpns",
        url_name="vpns",
        custom_view_base_action="view",
        custom_view_additional_permissions=["vpn.view_vpn"],
    )
    def vpn_vpns(self, request, *args, **kwargs):
        return Response({})

    @action(
        detail=True,
        url_path="vpn-tunnels",
        url_name="vpntunnels",
        custom_view_base_action="view",
        custom_view_additional_permissions=["vpn.view_vpntunnel"],
    )
    def vpn_tunnels(self, request, *args, **kwargs):
        return Response({})

    @action(
        detail=True,
        url_path="vpn-endpoints",
        url_name="vpnendpoints",
        custom_view_base_action="view",
        custom_view_additional_permissions=["vpn.view_vpntunnelendpoint"],
    )
    def vpn_endpoints(self, request, *args, **kwargs):
        return Response({})

    def form_save(self, form, **kwargs):
        obj = super().form_save(form, **kwargs)
        ctx = self.get_extra_context(self.request, obj)

        vpn_phase1_policies = ctx.get("vpn_phase1_policies")
        if vpn_phase1_policies.is_valid():
            vpn_phase1_policies.save()
        else:
            logger.debug("PH1 Policies")
            logger.error(vpn_phase1_policies.errors)
            raise ValidationError(vpn_phase1_policies.errors)

        vpn_phase2_policies = ctx.get("vpn_phase2_policies")
        if vpn_phase2_policies.is_valid():
            vpn_phase2_policies.save()
        else:
            logger.debug("PH2 Policies")
            logger.error(vpn_phase1_policies.errors)
            raise ValidationError(vpn_phase2_policies.errors)

        return obj


class VPNPhase1PolicyUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNPhase1Policy."""

    bulk_update_form_class = forms.VPNPhase1PolicyBulkEditForm
    filterset_class = filters.VPNPhase1PolicyFilterSet
    filterset_form_class = forms.VPNPhase1PolicyFilterForm
    form_class = forms.VPNPhase1PolicyForm
    lookup_field = "pk"
    queryset = models.VPNPhase1Policy.objects.all()
    serializer_class = serializers.VPNPhase1PolicySerializer
    table_class = tables.VPNPhase1PolicyTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "description",
                    "ike_version",
                    "aggressive_mode",
                    "encryption_algorithm",
                    "integrity_algorithm",
                    "dh_group",
                    "lifetime_seconds",
                    "lifetime_kb",
                    "authentication_method",
                    "tenant",
                ],
                value_transforms={
                    "encryption_algorithm": [helpers.label_list],
                    "integrity_algorithm": [helpers.label_list],
                    "dh_group": [helpers.label_list],
                },
            ),
        ],
    )


class VPNPhase2PolicyUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNPhase2Policy."""

    bulk_update_form_class = forms.VPNPhase2PolicyBulkEditForm
    filterset_class = filters.VPNPhase2PolicyFilterSet
    filterset_form_class = forms.VPNPhase2PolicyFilterForm
    form_class = forms.VPNPhase2PolicyForm
    lookup_field = "pk"
    queryset = models.VPNPhase2Policy.objects.all()
    serializer_class = serializers.VPNPhase2PolicySerializer
    table_class = tables.VPNPhase2PolicyTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "description",
                    "encryption_algorithm",
                    "integrity_algorithm",
                    "pfs_group",
                    "lifetime",
                    "tenant",
                ],
                value_transforms={
                    "encryption_algorithm": [helpers.label_list],
                    "integrity_algorithm": [helpers.label_list],
                    "pfs_group": [helpers.label_list],
                },
            ),
        ],
    )


class VPNUIViewSet(NautobotUIViewSet):
    """ViewSet for VPN."""

    bulk_update_form_class = forms.VPNBulkEditForm
    filterset_class = filters.VPNFilterSet
    filterset_form_class = forms.VPNFilterForm
    form_class = forms.VPNForm
    lookup_field = "pk"
    queryset = models.VPN.objects.all()
    serializer_class = serializers.VPNSerializer
    table_class = tables.VPNTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["vpn_profile", "name", "description", "vpn_id", "role", "tenant"],
            ),
            ObjectsTablePanel(
                weight=200,
                table_class=tables.VPNTunnelTable,
                table_filter="vpn",
                section=SectionChoices.FULL_WIDTH,
                exclude_columns=[],
            ),
        ],
    )


class VPNTunnelUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNTunnel."""

    bulk_update_form_class = forms.VPNTunnelBulkEditForm
    filterset_class = filters.VPNTunnelFilterSet
    filterset_form_class = forms.VPNTunnelFilterForm
    form_class = forms.VPNTunnelForm
    lookup_field = "pk"
    queryset = models.VPNTunnel.objects.all()
    serializer_class = serializers.VPNTunnelSerializer
    table_class = tables.VPNTunnelTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "description",
                    "vpn",
                    "vpn_profile",
                    "tunnel_id",
                    "encapsulation",
                    "role",
                    "status",
                    "tenant",
                ],
            ),
            ObjectsTablePanel(
                weight=100,
                label="A",
                table_class=tables.VPNTunnelEndpointTable,
                table_filter="endpoint_a_vpn_tunnels",
                table_title="Tunnel Endpoint",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[
                    "protected_prefixes_count",
                    "tenant",
                ],
                add_button_route=None,
            ),
            ObjectsTablePanel(
                weight=200,
                label="Z",
                table_class=tables.VPNTunnelEndpointTable,
                table_filter="endpoint_z_vpn_tunnels",
                table_title="Tunnel Endpoint",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[
                    "protected_prefixes_count",
                    "tenant",
                ],
                add_button_route=None,
            ),
        ],
    )


class VPNTunnelEndpointUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNTunnelEndpoint."""

    bulk_update_form_class = forms.VPNTunnelEndpointBulkEditForm
    filterset_class = filters.VPNTunnelEndpointFilterSet
    filterset_form_class = forms.VPNTunnelEndpointFilterForm
    form_class = forms.VPNTunnelEndpointForm
    lookup_field = "pk"
    queryset = models.VPNTunnelEndpoint.objects.all()
    serializer_class = serializers.VPNTunnelEndpointSerializer
    table_class = tables.VPNTunnelEndpointTable

    object_detail_content = ObjectDetailContent(
        panels=[
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "name",
                    "vpn_profile",
                    "device",
                    "source_interface",
                    "source_ipaddress",
                    "source_fqdn",
                    "tunnel_interface",
                    "role",
                    "tenant",
                ],
            ),
            ObjectsTablePanel(
                weight=100,
                table_class=tables.VPNTunnelTable,
                table_filter="endpoint_a",
                table_title="A Endpoint Tunnels",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[
                    "description",
                    "endpoint_a",
                    "tenant",
                    "actions",
                ],
                add_button_route=None,
            ),
            ObjectsTablePanel(
                weight=200,
                table_class=tables.VPNTunnelTable,
                table_filter="endpoint_z",
                table_title="Z Endpoint Tunnels",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[
                    "description",
                    "endpoint_z",
                    "tenant",
                    "actions",
                ],
                add_button_route=None,
            ),
        ],
        extra_tabs=[
            object_detail.DistinctViewTab(
                weight=object_detail.Tab.WEIGHT_CHANGELOG_TAB + 100,
                tab_id="protected_prefixes",
                label="Protected Prefixes",
                url_name="vpn:vpntunnelendpoint_protectedprefixes",
                related_object_attribute="protected_prefixes",
                hide_if_empty=True,
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=PrefixTable,
                        table_filter="vpn_tunnel_endpoints",
                        tab_id="protected_prefixes",
                        include_paginator=True,
                    ),
                ),
            ),
            object_detail.DistinctViewTab(
                weight=object_detail.Tab.WEIGHT_CHANGELOG_TAB + 200,
                tab_id="protected_dynamic_groups",
                label="Protected Prefixes from Dynamic Group",
                url_name="vpn:vpntunnelendpoint_protecteddynamicgroups",
                related_object_attribute="protected_prefixes_dg",
                hide_if_empty=True,
                panels=(
                    object_detail.ObjectsTablePanel(
                        section=SectionChoices.FULL_WIDTH,
                        weight=100,
                        table_class=DynamicGroupTable,
                        table_filter="vpn_tunnel_endpoints",
                        tab_id="protected_dynamic_groups",
                        include_paginator=True,
                        enable_related_link=False,
                    ),
                ),
            ),
        ],
    )

    @action(
        detail=True,
        url_path="protected-prefixes",
        url_name="protectedprefixes",
        custom_view_base_action="view",
        custom_view_additional_permissions=["ipam.view_prefix"],
    )
    def protected_prefixes(self, request, *args, **kwargs):
        return Response({})

    @action(
        detail=True,
        url_path="protected-dynamic-groups",
        url_name="protecteddynamicgroups",
        custom_view_base_action="view",
        custom_view_additional_permissions=["extras.view_dynamicgroup"],
    )
    def protected_dynamic_groups(self, request, *args, **kwargs):
        return Response({})
