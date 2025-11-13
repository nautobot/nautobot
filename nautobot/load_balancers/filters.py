"""Filtering for nautobot_load_balancer_models."""

import django_filters

from nautobot.cloud.models import CloudService
from nautobot.core.filters import (
    BaseFilterSet,
    MultiValueDateTimeFilter,
    NameSearchFilterSet,
    NaturalKeyOrPKMultipleChoiceFilter,
    SearchFilter,
)
from nautobot.dcim.models import Device, DeviceRedundancyGroup, VirtualChassis
from nautobot.extras.filters import NautobotFilterSet, StatusModelFilterSetMixin
from nautobot.ipam.models import IPAddress, Prefix
from nautobot.load_balancers import models
from nautobot.tenancy.filter_mixins import TenancyModelFilterSetMixin


class VirtualServerFilterSet(NameSearchFilterSet, TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VirtualServer."""

    vip = django_filters.ModelMultipleChoiceFilter(
        queryset=IPAddress.objects.all(),
        label="VIP (ID)",
    )
    source_nat_pool = django_filters.ModelMultipleChoiceFilter(
        queryset=Prefix.objects.all(),
        label="Source NAT Pool (ID)",
    )
    load_balancer_pool = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.LoadBalancerPool.objects.all(),
        label="Load Balancer Pool (name or ID)",
    )
    device = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="Device (name or ID)",
    )
    device_redundancy_group = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=DeviceRedundancyGroup.objects.all(),
        label="Device Redundancy Group (name or ID)",
    )
    cloud_service = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=CloudService.objects.all(),
        label="Cloud Service (name or ID)",
    )
    virtual_chassis = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=VirtualChassis.objects.all(),
        label="Virtual Chassis (name or ID)",
    )
    health_check_monitor = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.HealthCheckMonitor.objects.all(),
        label="Health Check Monitor (name or ID)",
    )
    certificate_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=models.CertificateProfile.objects.all(),
        label="Certificate Profile (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VirtualServer

        fields = "__all__"


class LoadBalancerPoolFilterSet(NameSearchFilterSet, NautobotFilterSet, TenancyModelFilterSetMixin):  # pylint: disable=too-many-ancestors
    """Filter for LoadBalancerPool."""

    health_check_monitor = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.HealthCheckMonitor.objects.all(),
        label="Health Check Monitor (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.LoadBalancerPool

        fields = "__all__"


class LoadBalancerPoolMemberFilterSet(StatusModelFilterSetMixin, TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for LoadBalancerPoolMember."""

    q = SearchFilter(
        filter_predicates={
            "ip_address__host": "icontains",
            "label": "icontains",
            "load_balancer_pool__name": "icontains",
            "port": "icontains",
        }
    )
    ip_address = django_filters.ModelMultipleChoiceFilter(
        queryset=IPAddress.objects.all(),
        label="IP Address (ID)",
    )
    load_balancer_pool = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=models.LoadBalancerPool.objects.all(),
        label="Load Balancer Pool (name or ID)",
    )
    health_check_monitor = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.HealthCheckMonitor.objects.all(),
        label="Health Check Monitor (name or ID)",
    )
    certificate_profiles = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=models.CertificateProfile.objects.all(),
        label="Certificate Profile (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.LoadBalancerPoolMember
        fields = "__all__"


class HealthCheckMonitorFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for HealthCheckMonitor."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "interval": {
                "lookup_expr": "exact",
                "preprocessor": int,
            },
            "retry": {
                "lookup_expr": "exact",
                "preprocessor": int,
            },
            "timeout": {
                "lookup_expr": "exact",
                "preprocessor": int,
            },
            "port": {
                "lookup_expr": "exact",
                "preprocessor": int,
            },
            "health_check_type": "icontains",
        }
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.HealthCheckMonitor
        fields = "__all__"


class CertificateProfileFilterSet(TenancyModelFilterSetMixin, NautobotFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for CertificateProfile."""

    q = SearchFilter(
        filter_predicates={
            "name": "icontains",
            "certificate_type": "icontains",
            "cipher": "icontains",
            "certificate_file_path": "icontains",
            "chain_file_path": "icontains",
            "key_file_path": "icontains",
        }
    )
    expiration_date = MultiValueDateTimeFilter()
    load_balancer_pool_members = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="ip_address__host",
        queryset=models.LoadBalancerPoolMember.objects.all(),
        label="Load Balancer Pool Members (ID or host string)",
    )
    virtual_servers = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=models.VirtualServer.objects.all(),
        label="Virtual Servers",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.CertificateProfile
        fields = "__all__"


class VirtualServerCertificateProfileAssignmentFilterSet(BaseFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for VirtualServerCertificateProfileAssignment."""

    virtual_server = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=models.VirtualServer.objects.all(),
        label="Virtual Server (name or ID)",
    )
    certificate_profile = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=models.CertificateProfile.objects.all(),
        label="Certificate Profile (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.VirtualServerCertificateProfileAssignment
        fields = "__all__"


class LoadBalancerPoolMemberCertificateProfileAssignmentFilterSet(BaseFilterSet):  # pylint: disable=too-many-ancestors
    """Filter for LoadBalancerPoolMemberCertificateProfileAssignment."""

    load_balancer_pool_member = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=models.LoadBalancerPoolMember.objects.all(),
        label="Load Balancer Pool Member (name or ID)",
    )
    certificate_profile = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=models.CertificateProfile.objects.all(),
        label="Certificate Profile (name or ID)",
    )

    class Meta:
        """Meta attributes for filter."""

        model = models.LoadBalancerPoolMemberCertificateProfileAssignment
        fields = "__all__"
