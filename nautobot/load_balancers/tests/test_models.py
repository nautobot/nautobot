"""Test VirtualServer."""

from django.db.utils import IntegrityError

from nautobot.core.testing.models import ModelTestCases
from nautobot.ipam.models import IPAddress
from nautobot.load_balancers import choices, models
from nautobot.load_balancers.tests import LoadBalancerModelsTestCaseMixin


# pylint: disable=no-member
class TestVirtualServer(LoadBalancerModelsTestCaseMixin, ModelTestCases.BaseModelTestCase):
    """Test VirtualServer."""

    model = models.VirtualServer

    @classmethod
    def setUpTestData(cls):
        """Setup test data."""
        super().setUpTestData()

        # Create a Virtual Server for the generic tests to use
        vip = IPAddress.objects.create(address="10.0.0.50/32", namespace=cls.namespace, status=cls.status)
        cls.virtual_server = models.VirtualServer.objects.create(name="VS0", vip=vip)
        cls.lb_pool = models.LoadBalancerPool.objects.first()

    def test_create_virtualserver_only_required(self):
        """Create VirtualServer with only required fields, and validate __str__."""
        virtual_server = models.VirtualServer.objects.create(name="VS1", vip=self.ip_address)
        self.assertEqual(virtual_server.name, "VS1")
        self.assertEqual(str(virtual_server), "VS1")

    def test_create_virtualserver_vip_required(self):
        """Create VirtualServer without vip."""
        with self.assertRaises(IntegrityError):
            models.VirtualServer.objects.create(name="VS1")

    def test_create_virtualserver_all_fields_success(self):
        """Create VirtualServer with all fields."""
        # Assign to a device
        virtual_server = models.VirtualServer.objects.create(
            name="VS1",
            vip=self.ip_address,
            port=80,
            protocol=choices.ProtocolChoices.PROTOCOL_TCP,
            source_nat_pool=self.source_nat_pool1,
            source_nat_type=choices.SourceNATTypeChoices.TYPE_POOL,
            load_balancer_pool=self.lb_pool,
            load_balancer_type=choices.LoadBalancerTypeChoices.TYPE_LAYER4,
            enabled=False,
            ssl_offload=True,
            tenant=self.tenant1,
            device=self.device1,
        )
        self.assertEqual(virtual_server.name, "VS1")

        # Assign to a device redundancy group
        virtual_server.device = None
        virtual_server.device_redundancy_group = self.device_redundancy_group1
        virtual_server.save()
        virtual_server.refresh_from_db()
        self.assertIsNone(virtual_server.device)
        self.assertEqual(virtual_server.device_redundancy_group, self.device_redundancy_group1)

        # Assign to a cloud service
        virtual_server.device_redundancy_group = None
        virtual_server.cloud_service = self.cloud_service1
        virtual_server.save()
        virtual_server.refresh_from_db()
        self.assertIsNone(virtual_server.device_redundancy_group)
        self.assertEqual(virtual_server.cloud_service, self.cloud_service1)

        # Assign to a virtual chassis
        virtual_server.cloud_service = None
        virtual_server.virtual_chassis = self.virtual_chassis1
        virtual_server.save()
        virtual_server.refresh_from_db()
        self.assertIsNone(virtual_server.cloud_service)
        self.assertEqual(virtual_server.virtual_chassis, self.virtual_chassis1)


class TestLoadBalancerPool(LoadBalancerModelsTestCaseMixin, ModelTestCases.BaseModelTestCase):
    """Test LoadBalancerPool."""

    model = models.LoadBalancerPool

    @classmethod
    def setUpTestData(cls):
        """Setup test data."""
        super().setUpTestData()

        # Create a LoadBalancerPool for the generic tests to use
        cls.lb_pool = models.LoadBalancerPool.objects.create(name="Pool0", load_balancing_algorithm="round_robin")

    def test_create_load_balancer_pool_only_required(self):
        """Create LoadBalancerPool with only required fields, and validate __str__."""
        lb_pool = models.LoadBalancerPool.objects.create(
            name="Pool1",
            load_balancing_algorithm="url_hash",
        )
        self.assertEqual(lb_pool.name, "Pool1")
        self.assertEqual(str(lb_pool), "Pool1")

    def test_create_load_balancer_pool_load_balancing_algorithm_required(self):
        """Create LoadBalancerPool without load_balancing_algorithm."""
        with self.assertRaises(IntegrityError):
            models.LoadBalancerPool.objects.create(name="Pool2", load_balancing_algorithm=None)

    def test_create_load_balancer_pool_name_required(self):
        """Create LoadBalancerPool without name."""
        with self.assertRaises(IntegrityError):
            models.LoadBalancerPool.objects.create(load_balancing_algorithm="url_hash", name=None)


# pylint: disable=no-member
class TestLoadBalancerPoolMemberModel(LoadBalancerModelsTestCaseMixin, ModelTestCases.BaseModelTestCase):
    """Test LoadBalancerPoolMember model."""

    model = models.LoadBalancerPoolMember

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        # Create a LoadBalancerPool for the generic tests to use
        cls.lb_pool = models.LoadBalancerPool.objects.create(name="Pool0", load_balancing_algorithm="round_robin")

        # Create a LoadBalancerPoolMember for the generic tests to use
        cls.load_balancer_pool_member = models.LoadBalancerPoolMember.objects.create(
            ip_address=cls.ip_address,
            port=80,
            tenant=cls.tenant1,
            ssl_offload=True,
            load_balancer_pool=cls.lb_pool,
            status=cls.status,
        )

    def test_create_load_balancer_pool_member_only_required(self):
        """Create LoadBalancerPoolMember with only required fields, and validate __str__."""
        ip_address = IPAddress.objects.create(address="10.0.0.50/32", namespace=self.namespace, status=self.status)
        load_balancer_pool_member = models.LoadBalancerPoolMember.objects.create(
            ip_address=ip_address, port=80, load_balancer_pool=self.lb_pool, status=self.status
        )
        self.assertEqual(load_balancer_pool_member.port, 80)
        self.assertEqual(str(load_balancer_pool_member), f"{ip_address.host}:80")

    def test_create_load_balancer_pool_member_ipaddress_required(self):
        """Create LoadBalancerPoolMember without ipaddress."""
        with self.assertRaises(IntegrityError):
            models.LoadBalancerPoolMember.objects.create(port=80, load_balancer_pool=self.lb_pool, status=self.status)

    def test_create_load_balancer_pool_member_port_required(self):
        """Create LoadBalancerPoolMember without port."""
        ip_address = IPAddress.objects.create(address="10.0.0.50/32", namespace=self.namespace, status=self.status)
        with self.assertRaises(IntegrityError):
            models.LoadBalancerPoolMember.objects.create(
                ip_address=ip_address, port=None, load_balancer_pool=self.lb_pool, status=self.status
            )

    def test_create_load_balancer_pool_member_load_balancer_pool_required(self):
        """Create LoadBalancerPoolMember without load_balancer_pool."""
        ip_address = IPAddress.objects.create(address="10.0.0.50/32", namespace=self.namespace, status=self.status)
        with self.assertRaises(IntegrityError):
            models.LoadBalancerPoolMember.objects.create(ip_address=ip_address, port=80, status=self.status)

    def test_create_load_balancer_pool_member_status_required(self):
        """Create LoadBalancerPoolMember without status."""
        ip_address = IPAddress.objects.create(address="10.0.0.50/32", namespace=self.namespace, status=self.status)
        with self.assertRaises(IntegrityError):
            models.LoadBalancerPoolMember.objects.create(
                ip_address=ip_address, port=80, load_balancer_pool=self.lb_pool
            )


class TestHealthCheckMonitorModel(LoadBalancerModelsTestCaseMixin, ModelTestCases.BaseModelTestCase):
    """Test HealthCheckMonitor model."""

    model = models.HealthCheckMonitor

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()


class TestCertificateProfileModel(LoadBalancerModelsTestCaseMixin, ModelTestCases.BaseModelTestCase):
    """Test CertificateProfile model."""

    model = models.CertificateProfile

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()
