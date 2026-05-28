"""Unit tests for views."""

import datetime

from django.utils.timezone import make_aware

from nautobot.core.testing.views import ViewTestCases
from nautobot.load_balancers import choices, models
from nautobot.load_balancers.tests import LoadBalancerModelsTestCaseMixin


# pylint: disable=too-many-ancestors, no-member
class VirtualServerViewTest(LoadBalancerModelsTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """Test the VirtualServer views."""

    model = models.VirtualServer

    @classmethod
    def setUpTestData(cls):
        """Setup test data."""
        super().setUpTestData()

        cls.form_data = {
            "name": "VS4",
            "vip": cls.vips[-4].pk,
            "port": 4444,
            "load_balancer_pool": cls.load_balancer_pools[0].pk,
            "protocol": choices.ProtocolChoices.PROTOCOL_TCP,
            "source_nat_pool": None,
            "source_nat_type": "",
            "load_balancer_type": choices.LoadBalancerTypeChoices.TYPE_LAYER4,
            "enabled": True,
            "ssl_offload": False,
            "device": cls.device1.pk,
            "device_redundancy_group": None,
            "cloud_service": None,
            "virtual_chassis": None,
            "tenant": None,
            "health_check_monitor": None,
        }

        cls.update_data = {
            "name": "VS5",
            "vip": cls.vips[-5].pk,
            "port": 5555,
            "protocol": choices.ProtocolChoices.PROTOCOL_DNS,
            "load_balancer_pool": cls.load_balancer_pools[1].pk,
            "source_nat_pool": None,
            "source_nat_type": "",
            "load_balancer_type": choices.LoadBalancerTypeChoices.TYPE_DNS,
            "enabled": False,
            "ssl_offload": True,
            "device": None,
            "device_redundancy_group": cls.device_redundancy_group1.pk,
            "cloud_service": None,
            "virtual_chassis": None,
            "tenant": None,
            "health_check_monitor": cls.health_check_monitors[0].pk,
        }

        cls.bulk_edit_data = {
            "port": 7777,
            "protocol": choices.ProtocolChoices.PROTOCOL_ANY,
            "source_nat_pool": None,
            "source_nat_type": "",
            "load_balancer_pool": cls.load_balancer_pools[0].pk,
            "load_balancer_type": choices.LoadBalancerTypeChoices.TYPE_LAYER2,
            "enabled": False,
            "ssl_offload": True,
            "device": None,
            "device_redundancy_group": None,
            "cloud_service": None,
            "virtual_chassis": cls.virtual_chassis1.pk,
            "tenant": None,
            "health_check_monitor": cls.health_check_monitors[1].pk,
            "add_certificate_profiles": [cls.certificate_profiles[1].pk],
            "remove_certificate_profiles": [cls.certificate_profiles[0].pk],
        }


# pylint: disable=too-many-ancestors, no-member
class LoadBalancerPoolViewTestCase(LoadBalancerModelsTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """Test the LoadBalancerPool views."""

    model = models.LoadBalancerPool

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "name": "Load Balancer Pool 1",
            "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
            "health_check_monitor": None,
            "tenant": cls.tenant1.pk,
        }

        cls.update_data = {
            "name": "Load Balancer Pool 2",
            "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.LEAST_CONNECTIONS,
            "health_check_monitor": cls.health_check_monitors[0].pk,
            "tenant": None,
        }

        cls.bulk_edit_data = {
            "name": "Load Balancer Pool 2",
            "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.URL_HASH,
            "health_check_monitor": cls.health_check_monitors[1].pk,
            "tenant": None,
        }


# pylint: disable=too-many-ancestors, no-member
class LoadBalancerPoolMemberViewTestCase(LoadBalancerModelsTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """Test the LoadBalancerPoolMember views."""

    model = models.LoadBalancerPoolMember

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "ip_address": cls.ip2.pk,
            "load_balancer_pool": cls.load_balancer_pools[1].pk,
            "port": 161,
            "ssl_offload": True,
            "tenant": cls.tenant1.pk,
            "status": cls.status.pk,
            "health_check_monitor": cls.health_check_monitors[0].pk,
        }

        cls.bulk_edit_data = {
            "load_balancer_pool": cls.load_balancer_pools[0].pk,
            "ssl_offload": False,
            "tenant": None,
            "status": cls.status.pk,
            "health_check_monitor": cls.health_check_monitors[1].pk,
            "add_certificate_profiles": [cls.certificate_profiles[1].pk],
            "remove_certificate_profiles": [cls.certificate_profiles[0].pk],
        }


# pylint: disable=too-many-ancestors, no-member
class HealthCheckMonitorViewTestCase(LoadBalancerModelsTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """Test the HealthCheckMonitor views."""

    model = models.HealthCheckMonitor

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "name": "HTTP Monitor 4",
            "interval": 35,
            "retry": 3,
            "timeout": 30,
            "port": 8008,
            "health_check_type": choices.HealthCheckTypeChoices.HTTP,
            "tenant": cls.tenant1.pk,
        }

        cls.update_data = {
            "name": "DNS Monitor 3",
            "interval": 4,
            "retry": 5,
            "timeout": 6,
            "port": 0,
            "health_check_type": choices.HealthCheckTypeChoices.DNS,
            "tenant": cls.tenant2.pk,
        }

        cls.bulk_edit_data = {
            "interval": 8,
            "retry": 9,
            "timeout": 10,
            "port": 11,
            "health_check_type": choices.HealthCheckTypeChoices.TCP,
            "tenant": None,
        }


# pylint: disable=too-many-ancestors, no-member
class CertificateProfileViewTestCase(LoadBalancerModelsTestCaseMixin, ViewTestCases.PrimaryObjectViewTestCase):
    """Test the CertificateProfile views."""

    model = models.CertificateProfile

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        super().setUpTestData()

        cls.form_data = {
            "name": "Test Certificate Profile 1",
            "certificate_type": choices.CertificateTypeChoices.TYPE_CLIENT,
            "certificate_file_path": "/this/is/a/path.crt",
            "chain_file_path": "/chain/certificate/path.pem",
            "key_file_path": "test_key.key",
            "expiration_date": make_aware(datetime.datetime(2023, 11, 1, 0, 0)),
            "cipher": "TLS_AES_256_GCM_SHA384",
            "tenant": cls.tenant1.pk,
        }

        cls.update_data = {
            "name": "Test Certificate Profile 2",
            "certificate_type": choices.CertificateTypeChoices.TYPE_SERVER,
            "certificate_file_path": "/test_cert.pem",
            "chain_file_path": "/test_chain.pem",
            "key_file_path": "/test_key",
            "expiration_date": make_aware(datetime.datetime(2030, 12, 1, 0, 0)),
            "cipher": "ECDHE_RSA",
            "tenant": cls.tenant2.pk,
        }

        cls.bulk_edit_data = {
            "name": "Test Certificate Profile 3",
            "tenant": None,
            "certificate_type": choices.CertificateTypeChoices.TYPE_MTLS,
            "certificate_file_path": "/etc/certificate.pem",
            "chain_file_path": "/bin/chain.pem",
            "key_file_path": "/home/key",
            "expiration_date": make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0, 0)),
            "cipher": "CHACHA20_POLY1305",
        }
