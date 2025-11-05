"""Filtering for the vpn models."""

from nautobot.apps.filters import (
    BaseFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    SearchFilter,
    StatusModelFilterSetMixin,
    TenancyModelFilterSetMixin,
)
from nautobot.dcim.models import Device, Interface
from nautobot.ipam.models import IPAddress

from . import models


class VPNProfileFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNProfile."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        }
    )
    vpn_phase1_policies = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNPhase1Policy.objects.all(),
        to_field_name="name",
        label="Phase 1 Policy (name or ID)",
    )
    vpn_phase2_policies = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNPhase2Policy.objects.all(),
        to_field_name="name",
        label="Phase 2 Policy (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNProfile
        fields = "__all__"


class VPNPhase1PolicyFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNPhase1Policy."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
        }
    )
    vpn_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        to_field_name="name",
        label="VPN Profile (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNPhase1Policy
        fields = "__all__"


class VPNPhase2PolicyFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNPhase2Policy."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        }
    )
    vpn_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        to_field_name="name",
        label="VPN Profile (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNPhase2Policy
        fields = "__all__"


class VPNProfilePhase1PolicyAssignmentFilterSet(BaseFilterSet):
    """Filterset for the VPNProfilePhase1PolicyAssignment through model."""

    q = SearchFilter(
        filter_predicates={
            "vpn_profile__name": "icontains",
            "vpn_phase1_policy__name": "icontains",
        },
    )

    vpn_profile = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        label="VPN Profile (name or ID)",
        to_field_name="name",
    )
    vpn_phase1_policy = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNPhase1Policy.objects.all(),
        label="Phase 1 Policy (name or ID)",
        to_field_name="name",
    )

    class Meta:
        model = models.VPNProfilePhase1PolicyAssignment
        fields = "__all__"


class VPNProfilePhase2PolicyAssignmentFilterSet(BaseFilterSet):
    """Filterset for the VPNProfilePhase2PolicyAssignment through model."""

    q = SearchFilter(
        filter_predicates={
            "vpn_profile__name": "icontains",
            "vpn_phase2_policy__name": "icontains",
        },
    )

    vpn_profile = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        label="VPN Profile (name or ID)",
        to_field_name="name",
    )
    vpn_phase2_policy = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNPhase2Policy.objects.all(),
        label="Phase 2 Policy (name or ID)",
        to_field_name="name",
    )

    class Meta:
        model = models.VPNProfilePhase2PolicyAssignment
        fields = "__all__"


class VPNFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPN."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "vpn_id": "icontains",
        }
    )
    vpn_profile = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        label="VPN Profile (name or ID)",
        to_field_name="name",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPN
        fields = "__all__"


class VPNTunnelFilterSet(StatusModelFilterSetMixin, TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNTunnel."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "tunnel_id": "icontains",
        }
    )
    vpn_profile = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        label="VPN Profile (name or ID)",
        to_field_name="name",
    )
    vpn = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPN.objects.all(),
        label="VPN (name or ID)",
        to_field_name="name",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNTunnel
        fields = "__all__"


class VPNTunnelEndpointFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNTunnelEndpoint."""

    q = SearchFilter(
        filter_predicates={
            "source_fqdn": "icontains",
            "device__name": "icontains",
        }
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        to_field_name="name",
        label="Device (ID or name)",
    )
    source_interface = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.all(),
        to_field_name="name",
        label="Source Interface (ID or name)",
    )
    source_ipaddress = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=IPAddress.objects.all(),
        to_field_name="name",
        label="Source IPAddress (ID or name)",
    )
    tunnel_interface = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Interface.objects.filter(type="tunnel"),
        to_field_name="name",
        label="Tunnel Interface (ID or name)",
    )
    endpoint_a_vpn_tunnels = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNTunnel.objects.all(),
        to_field_name="name",
        label="Endpoint A",
    )
    endpoint_z_vpn_tunnels = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNTunnel.objects.all(),
        to_field_name="name",
        label="Endpoint Z",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNTunnelEndpoint
        fields = "__all__"
