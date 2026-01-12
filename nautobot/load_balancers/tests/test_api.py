"""Unit tests for nautobot_load_balancer_models."""

import datetime

from django.utils.timezone import make_aware

from nautobot.core.testing.api import APIViewTestCases
from nautobot.load_balancers import choices, models
from nautobot.load_balancers.tests import LoadBalancerModelsTestCaseMixin


# pylint: disable=too-many-ancestors, no-member
class VirtualServerAPITest(LoadBalancerModelsTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """Test the VirtualServer API."""

    model = models.VirtualServer
    choices_fields = ("source_nat_type", "load_balancer_type", "protocol")

    @classmethod
    def setUpTestData(cls):
        """Setup test data."""
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "VS4",
                "vip": cls.vips[-4].pk,
                "port": 4444,
                "protocol": choices.ProtocolChoices.PROTOCOL_TCP,
                "source_nat_pool": None,
                "source_nat_type": "",
                "load_balancer_pool": cls.load_balancer_pools[0].pk,
                "load_balancer_type": choices.LoadBalancerTypeChoices.TYPE_LAYER4,
                "enabled": True,
                "ssl_offload": False,
                "device": cls.device1.pk,
                "device_redundancy_group": None,
                "cloud_service": None,
                "virtual_chassis": None,
                "tenant": None,
            },
            {
                "name": "VS5",
                "vip": cls.vips[-5].pk,
                "port": 5555,
                "protocol": choices.ProtocolChoices.PROTOCOL_HTTP,
                "source_nat_pool": None,
                "source_nat_type": "",
                "load_balancer_pool": cls.load_balancer_pools[1].pk,
                "load_balancer_type": choices.LoadBalancerTypeChoices.TYPE_LAYER7,
                "enabled": True,
                "ssl_offload": False,
                "device": None,
                "device_redundancy_group": cls.device_redundancy_group1.pk,
                "cloud_service": None,
                "virtual_chassis": None,
                "tenant": cls.tenant1.pk,
                "health_check_monitor": cls.health_check_monitors[0].pk,
            },
            {
                "name": "VS6",
                "vip": cls.vips[-6].pk,
                "port": 6666,
                "protocol": choices.ProtocolChoices.PROTOCOL_DNS,
                "source_nat_pool": cls.source_nat_pool1.pk,
                "source_nat_type": choices.SourceNATTypeChoices.TYPE_AUTO,
                "load_balancer_pool": cls.load_balancer_pools[2].pk,
                "load_balancer_type": choices.LoadBalancerTypeChoices.TYPE_DNS,
                "enabled": True,
                "ssl_offload": False,
                "device": None,
                "device_redundancy_group": None,
                "cloud_service": cls.cloud_service1.pk,
                "virtual_chassis": None,
                "tenant": None,
                "health_check_monitor": cls.health_check_monitors[1].pk,
            },
        ]

        cls.update_data = {
            "name": "VS7",
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
        }


# pylint: disable=too-many-ancestors, no-member
class LoadBalancerPoolAPITest(LoadBalancerModelsTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """LoadBalancerPool API tests."""

    model = models.LoadBalancerPool
    choices_fields = ("load_balancing_algorithm",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "Pool1",
                "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.LEAST_CONNECTIONS,
                "health_check_monitor": None,
                "tenant": cls.tenant1.pk,
            },
            {
                "name": "Pool2",
                "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
                "health_check_monitor": cls.health_check_monitors[0].pk,
                "tenant": None,
            },
            {
                "name": "Pool3",
                "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
                "health_check_monitor": cls.health_check_monitors[1].pk,
                "tenant": cls.tenant1.pk,
            },
        ]

        cls.update_data = {
            "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.URL_HASH,
            "health_check_monitor": cls.health_check_monitors[1].pk,
            "tenant": None,
        }


# pylint: disable=too-many-ancestors, no-member
class LoadBalancerPoolMemberAPITest(LoadBalancerModelsTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """LoadBalancerPoolMember API tests."""

    model = models.LoadBalancerPoolMember

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "ip_address": cls.ip1.pk,
                "load_balancer_pool": cls.load_balancer_pools[0].pk,
                "label": "Test Member 1",
                "port": 8080,
                "ssl_offload": True,
                "health_check_monitor": None,
                "tenant": cls.tenant1.pk,
                "status": cls.status.pk,
            },
            {
                "ip_address": cls.ip2.pk,
                "load_balancer_pool": cls.load_balancer_pools[1].pk,
                "label": "Test Member 2",
                "port": 443,
                "ssl_offload": True,
                "health_check_monitor": cls.health_check_monitors[0].pk,
                "tenant": None,
                "status": cls.status.pk,
            },
            {
                "ip_address": cls.ip3.pk,
                "load_balancer_pool": cls.load_balancer_pools[2].pk,
                "label": "",
                "port": 80,
                "ssl_offload": False,
                "health_check_monitor": cls.health_check_monitors[1].pk,
                "tenant": cls.tenant1.pk,
                "status": cls.status.pk,
            },
        ]

        cls.update_data = {
            "load_balancer_pool": cls.load_balancer_pools[1].pk,
            "label": "Test Member 3",
            "ssl_offload": False,
            "health_check_monitor": cls.health_check_monitors[1].pk,
        }


# pylint: disable=too-many-ancestors
class HealthCheckMonitorAPITest(LoadBalancerModelsTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """HealthCheckMonitor API tests."""

    model = models.HealthCheckMonitor
    choices_fields = ("health_check_type",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "HTTP Monitor 3",
                "interval": 30,
                "retry": 3,
                "timeout": 30,
                "port": 8080,
                "health_check_type": choices.HealthCheckTypeChoices.HTTP,
                "tenant": cls.tenant1.pk,
            },
            {
                "name": "HTTPS Monitor 3",
                "interval": 10,
                "retry": 0,
                "timeout": 30,
                "port": 443,
                "health_check_type": choices.HealthCheckTypeChoices.HTTPS,
                "tenant": cls.tenant2.pk,
            },
            {
                "name": "ICMP Monitor 3",
                "interval": 5,
                "retry": 1,
                "timeout": 3,
                "health_check_type": choices.HealthCheckTypeChoices.PING,
                "tenant": None,
            },
        ]

        cls.update_data = {
            "name": "DNS Monitor 3",
            "interval": 6,
            "retry": 7,
            "timeout": 8,
            "port": 9,
            "health_check_type": choices.HealthCheckTypeChoices.DNS,
            "tenant": None,
        }


class CertificateProfileAPITest(LoadBalancerModelsTestCaseMixin, APIViewTestCases.APIViewTestCase):
    """CertificateProfile API tests."""

    model = models.CertificateProfile
    choices_fields = ("certificate_type",)

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "name": "Certificate1",
                "certificate_type": choices.CertificateTypeChoices.TYPE_CLIENT,
                "certificate_file_path": "/test_cert.cert",
                "key_file_path": "/test_key.key",
                "chain_file_path": "/test_chain.chain",
                "expiration_date": make_aware(datetime.datetime(2022, 11, 17, 12, 0, 0, 0)),
                "cipher": "RSA",
                "tenant": cls.tenant1.pk,
            },
            {
                "name": "Certificate2",
                "certificate_type": choices.CertificateTypeChoices.TYPE_MTLS,
                "certificate_file_path": "",
                "key_file_path": "",
                "chain_file_path": "",
                "expiration_date": make_aware(datetime.datetime(2023, 12, 31, 12, 0, 0, 0)),
                "cipher": "",
                "tenant": cls.tenant2.pk,
            },
            {
                "name": "Certificate3",
                "certificate_type": choices.CertificateTypeChoices.TYPE_SERVER,
                "certificate_file_path": "/path/to/test_cert.cert",
                "key_file_path": "/path/to/test_key.key",
                "chain_file_path": "/path/to/test_chain.chain",
                "expiration_date": make_aware(datetime.datetime(2023, 12, 31, 12, 0, 0, 0)),
                "cipher": "RSA",
                "tenant": None,
            },
        ]

        cls.update_data = {
            "name": "Certificate4",
            "certificate_type": choices.CertificateTypeChoices.TYPE_CLIENT,
            "certificate_file_path": "/test_cert.cert",
            "key_file_path": "/test_key.key",
            "chain_file_path": "/test_chain.chain",
            "cipher": "RSA",
            "tenant": None,
        }


class VirtualServerCertificateProfileAssignmentAPITest(
    LoadBalancerModelsTestCaseMixin, APIViewTestCases.APIViewTestCase
):
    """VirtualServerCertificateProfile API tests."""

    model = models.VirtualServerCertificateProfileAssignment

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "virtual_server": cls.virtual_servers[0].pk,
                "certificate_profile": cls.certificate_profiles[2].pk,
            },
            {
                "virtual_server": cls.virtual_servers[1].pk,
                "certificate_profile": cls.certificate_profiles[0].pk,
            },
            {
                "virtual_server": cls.virtual_servers[2].pk,
                "certificate_profile": cls.certificate_profiles[1].pk,
            },
        ]

        cls.update_data = {
            "certificate_profile": cls.certificate_profiles[3].pk,
        }


class LoadBalancerPoolMemberCertificateProfileAssignmentAPITest(
    LoadBalancerModelsTestCaseMixin, APIViewTestCases.APIViewTestCase
):
    """LoadBalancerPoolMemberCertificateProfile API tests."""

    model = models.LoadBalancerPoolMemberCertificateProfileAssignment

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.create_data = [
            {
                "load_balancer_pool_member": cls.load_balancer_pool_members[0].pk,
                "certificate_profile": cls.certificate_profiles[2].pk,
            },
            {
                "load_balancer_pool_member": cls.load_balancer_pool_members[1].pk,
                "certificate_profile": cls.certificate_profiles[0].pk,
            },
            {
                "load_balancer_pool_member": cls.load_balancer_pool_members[2].pk,
                "certificate_profile": cls.certificate_profiles[1].pk,
            },
        ]

        cls.update_data = {
            "certificate_profile": cls.certificate_profiles[3].pk,
        }
