"""Test VirtualServer Filter."""

from nautobot.core.testing.filters import FilterTestCases
from nautobot.load_balancers import filters, models
from nautobot.load_balancers.tests import LoadBalancerModelsTestCaseMixin


# pylint: disable=too-many-ancestors
class VirtualServerFilterTestCase(
    LoadBalancerModelsTestCaseMixin,
    FilterTestCases.TenancyFilterTestCaseMixin,
    FilterTestCases.FilterTestCase,
):
    """VirtualServerFilterSet Test Case."""

    queryset = models.VirtualServer.objects.all()
    filterset = filters.VirtualServerFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("vip",),
        ("name",),
        ("port",),
        ("protocol",),
        ("source_nat_pool",),
        ("source_nat_type",),
        ("load_balancer_pool",),
        ("load_balancer_type",),
        ("device",),
        ("device_redundancy_group",),
        ("cloud_service",),
        ("virtual_chassis",),
        ("health_check_monitor", "health_check_monitor__id"),
        ("health_check_monitor", "health_check_monitor__name"),
        ("certificate_profiles",),
    )
    tenancy_related_name = "virtual_servers"


class LoadBalancerPoolFilterTestCase(
    LoadBalancerModelsTestCaseMixin,
    FilterTestCases.FilterTestCase,
    FilterTestCases.TenancyFilterTestCaseMixin,
):
    """LoadBalancerPoolFilterSet Test Case."""

    queryset = models.LoadBalancerPool.objects.all()
    filterset = filters.LoadBalancerPoolFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
        ("load_balancing_algorithm",),
        ("health_check_monitor", "health_check_monitor__id"),
        ("health_check_monitor", "health_check_monitor__name"),
    )
    tenancy_related_name = "load_balancer_pools"


class LoadBalancerPoolMemberFilterTestCase(
    LoadBalancerModelsTestCaseMixin,
    FilterTestCases.FilterTestCase,
    FilterTestCases.TenancyFilterTestCaseMixin,
):
    """LoadBalancerPoolMemberFilterSet Test Case."""

    queryset = models.LoadBalancerPoolMember.objects.all()
    filterset = filters.LoadBalancerPoolMemberFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("ip_address",),
        ("label",),
        ("load_balancer_pool",),
        ("certificate_profiles",),
        ("port",),
        ("health_check_monitor", "health_check_monitor__id"),
        ("health_check_monitor", "health_check_monitor__name"),
    )
    tenancy_related_name = "load_balancer_pool_members"


class HealthCheckMonitorFilterTestCase(
    LoadBalancerModelsTestCaseMixin,
    FilterTestCases.FilterTestCase,
    FilterTestCases.TenancyFilterTestCaseMixin,
):
    """HealthCheckMonitorFilterSet Test Case."""

    queryset = models.HealthCheckMonitor.objects.all()
    filterset = filters.HealthCheckMonitorFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
        ("interval",),
        ("retry",),
        ("timeout",),
        ("port",),
        ("health_check_type",),
    )
    tenancy_related_name = "health_check_monitors"


class CertificateProfileFilterTestCase(
    LoadBalancerModelsTestCaseMixin,
    FilterTestCases.FilterTestCase,
    FilterTestCases.TenancyFilterTestCaseMixin,
):
    """CertificateProfileFilterSet Test Case."""

    queryset = models.CertificateProfile.objects.all()
    filterset = filters.CertificateProfileFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
        ("certificate_type",),
        ("certificate_file_path",),
        ("chain_file_path",),
        ("key_file_path",),
        ("expiration_date",),
        ("cipher",),
        ("load_balancer_pool_members", "load_balancer_pool_members__id"),
        ("load_balancer_pool_members", "load_balancer_pool_members__ip_address__host"),
        ("virtual_servers", "virtual_servers__id"),
        ("virtual_servers", "virtual_servers__name"),
    )
    tenancy_related_name = "certificate_profiles"
