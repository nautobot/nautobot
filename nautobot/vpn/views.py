"""Views for the vpn models."""

import logging

from django.core.exceptions import ValidationError

from nautobot.apps.ui import ObjectDetailContent, ObjectFieldsPanel, ObjectsTablePanel, SectionChoices
from nautobot.apps.views import NautobotUIViewSet

from . import filters, forms, models, tables
from .api import serializers

logger = logging.getLogger(__name__)


class VPNProfileUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNProfile."""

    bulk_update_form_class = forms.VPNProfileBulkEditForm
    filterset_class = filters.VPNProfileFilterSet
    filterset_form_class = forms.VPNProfileFilterForm
    form_class = forms.VPNProfileForm
    # TODO INIT verify this is the lookup field you want
    lookup_field = "pk"
    queryset = models.VPNProfile.objects.all()
    serializer_class = serializers.VPNProfileSerializer
    table_class = tables.VPNProfileTable
    # base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            # TODO INIT ensure these are the fields you want to show
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
                    "extra_options",
                    "secrets_group",
                    "role",
                ],
            ),
            ObjectsTablePanel(
                weight=100,
                table_class=tables.VPNProfilePhase1PolicyAssignmentTable,
                table_filter="vpn_profile",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[],
            ),
            ObjectsTablePanel(
                weight=200,
                table_class=tables.VPNProfilePhase2PolicyAssignmentTable,
                table_filter="vpn_profile",
                section=SectionChoices.RIGHT_HALF,
                exclude_columns=[],
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
    # TODO INIT verify this is the lookup field you want
    lookup_field = "pk"
    queryset = models.VPNPhase1Policy.objects.all()
    serializer_class = serializers.VPNPhase1PolicySerializer
    table_class = tables.VPNPhase1PolicyTable
    # base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            # TODO INIT ensure these are the fields you want to show
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
                ],
            ),
        ],
    )


class VPNPhase2PolicyUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNPhase2Policy."""

    bulk_update_form_class = forms.VPNPhase2PolicyBulkEditForm
    filterset_class = filters.VPNPhase2PolicyFilterSet
    filterset_form_class = forms.VPNPhase2PolicyFilterForm
    form_class = forms.VPNPhase2PolicyForm
    # TODO INIT verify this is the lookup field you want
    lookup_field = "pk"
    queryset = models.VPNPhase2Policy.objects.all()
    serializer_class = serializers.VPNPhase2PolicySerializer
    table_class = tables.VPNPhase2PolicyTable
    # base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            # TODO INIT ensure these are the fields you want to show
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["name", "description", "encryption_algorithm", "integrity_algorithm", "pfs_group", "lifetime"],
            ),
        ],
    )


class VPNUIViewSet(NautobotUIViewSet):
    """ViewSet for VPN."""

    bulk_update_form_class = forms.VPNBulkEditForm
    filterset_class = filters.VPNFilterSet
    filterset_form_class = forms.VPNFilterForm
    form_class = forms.VPNForm
    # TODO INIT verify this is the lookup field you want
    lookup_field = "pk"
    queryset = models.VPN.objects.all()
    serializer_class = serializers.VPNSerializer
    table_class = tables.VPNTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            # TODO INIT ensure these are the fields you want to show
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=["vpn_profile", "name", "description", "vpn_id", "tenant", "role"],
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
    # TODO INIT verify this is the lookup field you want
    lookup_field = "pk"
    queryset = models.VPNTunnel.objects.all()
    serializer_class = serializers.VPNTunnelSerializer
    table_class = tables.VPNTunnelTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            # TODO INIT ensure these are the fields you want to show
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
                    "tenant",
                    "role",
                    "status",
                ],
            ),
            ObjectFieldsPanel(
                label="Endpoint A",
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                fields=[
                    "endpoint_a",
                ],
            ),
            ObjectFieldsPanel(
                label="Endpoint Z",
                weight=100,
                section=SectionChoices.RIGHT_HALF,
                fields=[
                    "endpoint_z",
                ],
            ),
        ],
    )


class VPNTunnelEndpointUIViewSet(NautobotUIViewSet):
    """ViewSet for VPNTunnelEndpoint."""

    bulk_update_form_class = forms.VPNTunnelEndpointBulkEditForm
    filterset_class = filters.VPNTunnelEndpointFilterSet
    filterset_form_class = forms.VPNTunnelEndpointFilterForm
    form_class = forms.VPNTunnelEndpointForm
    # TODO INIT verify this is the lookup field you want
    lookup_field = "pk"
    queryset = models.VPNTunnelEndpoint.objects.all()
    serializer_class = serializers.VPNTunnelEndpointSerializer
    table_class = tables.VPNTunnelEndpointTable
    base_template = "generic/object_retrieve.html"

    object_detail_content = ObjectDetailContent(
        panels=[
            # TODO INIT ensure these are the fields you want to show
            ObjectFieldsPanel(
                weight=100,
                section=SectionChoices.LEFT_HALF,
                fields=[
                    "vpn_profile",
                    "source_ipaddress",
                    "source_interface",
                    "destination_ipaddress",
                    "destination_fqdn",
                    "tunnel_interface",
                    "protected_prefixes_dg",
                    "protected_prefixes",
                    "role",
                ],
            ),
        ],
    )
