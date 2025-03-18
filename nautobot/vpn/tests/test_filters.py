"""Test nautobot_vpn_models Filters."""

from django.contrib.contenttypes.models import ContentType
from nautobot.apps.testing import FilterTestCases
from nautobot.tenancy.models import Tenant, TenantGroup

from nautobot_vpn_models import choices, filters, models











class VPNProfileFilterTestCase(
    # FilterTestCases.NameOnlyFilterTestCase,
    FilterTestCases.FilterTestCase,
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # FilterTestCases.TenancyFilterTestCaseMixin,
):
    """VPNProfileFilterSet Test Case."""

    queryset = models.VPNProfile.objects.all()
    filterset = filters.VPNProfileFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("vpn_phase1_policy",),
        ("vpn_phase2_policy",),
        ("name",),
        ("description",),
        ("keepalive_interval",),
        ("keepalive_retries",),
        ("extra_options",),
        ("secrets_group",),
        ("role",),
    )
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # tenancy_related_name = "vpn_profiles"


    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # TODO INIT Uncomment the below lines if the model has a tenancy relationship.
        # cls.tenant_group1 = TenantGroup.objects.create(name="Test Tenant Group 1")
        # cls.tenant_group2 = TenantGroup.objects.create(name="Test Tenant Group 2")
        # cls.tenant1 = Tenant.objects.create(name="Test VPN Profile Tenant 1", group=cls.tenant_group1)
        # cls.tenant2 = Tenant.objects.create(name="Test VPN Profile Tenant 2", group=cls.tenant_group2)
        # Create VPN Profile instances for the generic filter tests to use
        models.VPNProfile.objects.create(
            vpn_phase1_policy="ReplaceMe",
            vpn_phase2_policy="ReplaceMe",
            name="ReplaceMe",
            description="ReplaceMe",
            keepalive_enabled="ReplaceMe",
            keepalive_interval="ReplaceMe",
            keepalive_retries="ReplaceMe",
            nat_traversal="ReplaceMe",
            extra_options="ReplaceMe",
            secrets_group="ReplaceMe",
            role="ReplaceMe",
            # TODO INIT Uncomment the below line if the model has a tenancy relationship.
            # tenant=cls.tenant1,
        )
        # TODO INIT Add more instances as needed for testing. Not all fields should be used for all instances.


class VPNPhase1PolicyFilterTestCase(
    # FilterTestCases.NameOnlyFilterTestCase,
    FilterTestCases.FilterTestCase,
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # FilterTestCases.TenancyFilterTestCaseMixin,
):
    """VPNPhase1PolicyFilterSet Test Case."""

    queryset = models.VPNPhase1Policy.objects.all()
    filterset = filters.VPNPhase1PolicyFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
        ("description",),
        ("ike_version",),
        ("encryption_algorithm",),
        ("integrity_algorithm",),
        ("dh_group",),
        ("lifetime_seconds",),
        ("lifetime_kb",),
        ("authentication_method",),
    )
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # tenancy_related_name = "vpn_phase_1_policys"


    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # TODO INIT Uncomment the below lines if the model has a tenancy relationship.
        # cls.tenant_group1 = TenantGroup.objects.create(name="Test Tenant Group 1")
        # cls.tenant_group2 = TenantGroup.objects.create(name="Test Tenant Group 2")
        # cls.tenant1 = Tenant.objects.create(name="Test VPN Phase 1 Policy Tenant 1", group=cls.tenant_group1)
        # cls.tenant2 = Tenant.objects.create(name="Test VPN Phase 1 Policy Tenant 2", group=cls.tenant_group2)
        # Create VPN Phase 1 Policy instances for the generic filter tests to use
        models.VPNPhase1Policy.objects.create(
            name="ReplaceMe",
            description="ReplaceMe",
            ike_version="ReplaceMe",
            aggressive_mode="ReplaceMe",
            encryption_algorithm="ReplaceMe",
            integrity_algorithm="ReplaceMe",
            dh_group="ReplaceMe",
            lifetime_seconds="ReplaceMe",
            lifetime_kb="ReplaceMe",
            authentication_method="ReplaceMe",
            # TODO INIT Uncomment the below line if the model has a tenancy relationship.
            # tenant=cls.tenant1,
        )
        # TODO INIT Add more instances as needed for testing. Not all fields should be used for all instances.


class VPNPhase2PolicyFilterTestCase(
    # FilterTestCases.NameOnlyFilterTestCase,
    FilterTestCases.FilterTestCase,
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # FilterTestCases.TenancyFilterTestCaseMixin,
):
    """VPNPhase2PolicyFilterSet Test Case."""

    queryset = models.VPNPhase2Policy.objects.all()
    filterset = filters.VPNPhase2PolicyFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("name",),
        ("description",),
        ("encryption_algorithm",),
        ("integrity_algorithm",),
        ("pfs_group",),
        ("lifetime",),
    )
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # tenancy_related_name = "vpn_phase_2_policys"


    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # TODO INIT Uncomment the below lines if the model has a tenancy relationship.
        # cls.tenant_group1 = TenantGroup.objects.create(name="Test Tenant Group 1")
        # cls.tenant_group2 = TenantGroup.objects.create(name="Test Tenant Group 2")
        # cls.tenant1 = Tenant.objects.create(name="Test VPN Phase 2 Policy Tenant 1", group=cls.tenant_group1)
        # cls.tenant2 = Tenant.objects.create(name="Test VPN Phase 2 Policy Tenant 2", group=cls.tenant_group2)
        # Create VPN Phase 2 Policy instances for the generic filter tests to use
        models.VPNPhase2Policy.objects.create(
            name="ReplaceMe",
            description="ReplaceMe",
            encryption_algorithm="ReplaceMe",
            integrity_algorithm="ReplaceMe",
            pfs_group="ReplaceMe",
            lifetime="ReplaceMe",
            # TODO INIT Uncomment the below line if the model has a tenancy relationship.
            # tenant=cls.tenant1,
        )
        # TODO INIT Add more instances as needed for testing. Not all fields should be used for all instances.


class VPNFilterTestCase(
    # FilterTestCases.NameOnlyFilterTestCase,
    FilterTestCases.FilterTestCase,
    FilterTestCases.TenancyFilterTestCaseMixin,
):
    """VPNFilterSet Test Case."""

    queryset = models.VPN.objects.all()
    filterset = filters.VPNFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("vpn_profile",),
        ("name",),
        ("description",),
        ("vpn_id",),
        ("role",),
        ("contact_associations",),
    )
    tenancy_related_name = "vpns"


    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        cls.tenant_group1 = TenantGroup.objects.create(name="Test Tenant Group 1")
        cls.tenant_group2 = TenantGroup.objects.create(name="Test Tenant Group 2")
        cls.tenant1 = Tenant.objects.create(name="Test VPN Tenant 1", group=cls.tenant_group1)
        cls.tenant2 = Tenant.objects.create(name="Test VPN Tenant 2", group=cls.tenant_group2)
        # Create VPN instances for the generic filter tests to use
        models.VPN.objects.create(
            vpn_profile="ReplaceMe",
            name="ReplaceMe",
            description="ReplaceMe",
            vpn_id="ReplaceMe",
            role="ReplaceMe",
            contact_associations="ReplaceMe",
            tenant=cls.tenant1,
        )
        # TODO INIT Add more instances as needed for testing. Not all fields should be used for all instances.


class VPNTunnelFilterTestCase(
    # FilterTestCases.NameOnlyFilterTestCase,
    FilterTestCases.FilterTestCase,
    FilterTestCases.TenancyFilterTestCaseMixin,
):
    """VPNTunnelFilterSet Test Case."""

    queryset = models.VPNTunnel.objects.all()
    filterset = filters.VPNTunnelFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("vpn_profile",),
        ("vpn",),
        ("name",),
        ("description",),
        ("tunnel_id",),
        ("encapsulation",),
        ("role",),
        ("contact_associations",),
    )
    tenancy_related_name = "vpn_tunnels"


    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        cls.tenant_group1 = TenantGroup.objects.create(name="Test Tenant Group 1")
        cls.tenant_group2 = TenantGroup.objects.create(name="Test Tenant Group 2")
        cls.tenant1 = Tenant.objects.create(name="Test VPN Tunnel Tenant 1", group=cls.tenant_group1)
        cls.tenant2 = Tenant.objects.create(name="Test VPN Tunnel Tenant 2", group=cls.tenant_group2)
        # Create VPN Tunnel instances for the generic filter tests to use
        models.VPNTunnel.objects.create(
            vpn_profile="ReplaceMe",
            vpn="ReplaceMe",
            name="ReplaceMe",
            description="ReplaceMe",
            tunnel_id="ReplaceMe",
            encapsulation="ReplaceMe",
            role="ReplaceMe",
            contact_associations="ReplaceMe",
            tenant=cls.tenant1,
        )
        # TODO INIT Add more instances as needed for testing. Not all fields should be used for all instances.


class VPNTunnelEndpointFilterTestCase(
    # FilterTestCases.NameOnlyFilterTestCase,
    FilterTestCases.FilterTestCase,
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # FilterTestCases.TenancyFilterTestCaseMixin,
):
    """VPNTunnelEndpointFilterSet Test Case."""

    queryset = models.VPNTunnelEndpoint.objects.all()
    filterset = filters.VPNTunnelEndpointFilterSet
    generic_filter_tests = (
        ("id",),
        ("created",),
        ("last_updated",),
        ("vpn_profile",),
        ("vpn_tunnel",),
        ("source_ipaddress",),
        ("source_interface",),
        ("destination_ipaddress",),
        ("destination_fqdn",),
        ("tunnel_interface",),
        ("protected_prefixes_dg",),
        ("protected_prefixes",),
        ("role",),
        ("contact_associations",),
    )
    # TODO INIT Uncomment the line below if the model has a tenancy relationship.
    # tenancy_related_name = "vpn_tunnel_endpoints"


    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
        # TODO INIT Uncomment the below lines if the model has a tenancy relationship.
        # cls.tenant_group1 = TenantGroup.objects.create(name="Test Tenant Group 1")
        # cls.tenant_group2 = TenantGroup.objects.create(name="Test Tenant Group 2")
        # cls.tenant1 = Tenant.objects.create(name="Test VPN Tunnel Endpoint Tenant 1", group=cls.tenant_group1)
        # cls.tenant2 = Tenant.objects.create(name="Test VPN Tunnel Endpoint Tenant 2", group=cls.tenant_group2)
        # Create VPN Tunnel Endpoint instances for the generic filter tests to use
        models.VPNTunnelEndpoint.objects.create(
            vpn_profile="ReplaceMe",
            vpn_tunnel="ReplaceMe",
            source_ipaddress="ReplaceMe",
            source_interface="ReplaceMe",
            destination_ipaddress="ReplaceMe",
            destination_fqdn="ReplaceMe",
            tunnel_interface="ReplaceMe",
            protected_prefixes_dg="ReplaceMe",
            protected_prefixes="ReplaceMe",
            role="ReplaceMe",
            contact_associations="ReplaceMe",
            # TODO INIT Uncomment the below line if the model has a tenancy relationship.
            # tenant=cls.tenant1,
        )
        # TODO INIT Add more instances as needed for testing. Not all fields should be used for all instances.

