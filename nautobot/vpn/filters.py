"""Filtering for the vpn models."""

from nautobot.apps.filters import (
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    SearchFilter,
    StatusModelFilterSetMixin,
    TenancyModelFilterSetMixin,
)

from . import models


class VPNProfileFilterSet(NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNProfile."""

    # TODO INIT Validate the filter_predicates below. If the only field you want to search is `name`, you can remove the SearchFilter
    # and instead use the NameSearchFilterSet in the class inheritance.
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
        }
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNProfile
        fields = "__all__"


class VPNPhase1PolicyFilterSet(NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNPhase1Policy."""

    # TODO INIT Validate the filter_predicates below. If the only field you want to search is `name`, you can remove the SearchFilter
    # and instead use the NameSearchFilterSet in the class inheritance.
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "ike_version": "icontains",
            "encryption_algorithm": "icontains",
            "integrity_algorithm": "icontains",
            "dh_group": "icontains",
            "authentication_method": "icontains",
        }
    )
    vpn_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        to_field_name="name",
        label="VPN Profile",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNPhase1Policy
        fields = "__all__"


class VPNPhase2PolicyFilterSet(NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNPhase2Policy."""

    # TODO INIT Validate the filter_predicates below. If the only field you want to search is `name`, you can remove the SearchFilter
    # and instead use the NameSearchFilterSet in the class inheritance.
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "encryption_algorithm": "icontains",
            "integrity_algorithm": "icontains",
            "pfs_group": "icontains",
        }
    )
    vpn_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VPNProfile.objects.all(),
        to_field_name="name",
        label="VPN Profile",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNPhase2Policy
        fields = "__all__"


class VPNFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPN."""

    # TODO INIT Validate the filter_predicates below. If the only field you want to search is `name`, you can remove the SearchFilter
    # and instead use the NameSearchFilterSet in the class inheritance.
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "vpn_id": "icontains",
        }
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPN
        fields = "__all__"


class VPNTunnelFilterSet(StatusModelFilterSetMixin, TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNTunnel."""

    # TODO INIT Validate the filter_predicates below. If the only field you want to search is `name`, you can remove the SearchFilter
    # and instead use the NameSearchFilterSet in the class inheritance.
    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "description": "icontains",
            "tunnel_id": "icontains",
            "encapsulation": "icontains",
        }
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNTunnel
        fields = "__all__"


class VPNTunnelEndpointFilterSet(NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VPNTunnelEndpoint."""

    # TODO INIT Validate the filter_predicates below. If the only field you want to search is `name`, you can remove the SearchFilter
    # and instead use the NameSearchFilterSet in the class inheritance.
    q = SearchFilter(
        filter_predicates={
            "destination_fqdn": "icontains",
        }
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VPNTunnelEndpoint
        fields = "__all__"
