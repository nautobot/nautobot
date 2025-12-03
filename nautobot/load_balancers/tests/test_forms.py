"""Test virtualserver forms."""

from nautobot.core.testing.forms import FormTestCases
from nautobot.load_balancers import choices, forms
from nautobot.load_balancers.tests import LoadBalancerModelsTestCaseMixin


# pylint: disable=no-member
class VirtualServerFormTest(LoadBalancerModelsTestCaseMixin, FormTestCases.BaseFormTestCase):
    """Test VirtualServer forms."""

    form_class = forms.VirtualServerForm

    def test_specifying_all_fields_success(self):
        form = forms.VirtualServerForm(
            data={
                "name": "Virtual Server 1",
                "vip": self.ip_address.pk,
                "enabled": True,
                "port": 80,
                "protocol": choices.ProtocolChoices.PROTOCOL_TCP,
                "load_balancer_pool": self.load_balancer_pools[0].pk,
                "load_balancer_type": choices.LoadBalancerTypeChoices.TYPE_LAYER4,
                "tenant": self.tenant1.pk,
                "source_nat_pool": self.source_nat_pool1.pk,
                "source_nat_type": choices.SourceNATTypeChoices.TYPE_STATIC,
                "device": self.device1.pk,
                "health_check_monitor": self.health_check_monitors[1].pk,
                "ssl_offload": True,
                "certificate_profiles": [self.certificate_profiles[0]],
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_only_required_success(self):
        form = forms.VirtualServerForm(
            data={
                "name": "Virtual Server 1",
                "vip": self.ip_address.pk,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_validate_name_is_required(self):
        form = forms.VirtualServerForm(data={"vip": self.ip_address.pk})
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])


# pylint: disable=no-member
class LoadBalancerPoolFormTest(LoadBalancerModelsTestCaseMixin, FormTestCases.BaseFormTestCase):
    """Test the LoadBalancerPool form."""

    form_class = forms.LoadBalancerPoolForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "name": "Load Balance Pool 1",
            "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
            "health_check_monitor": self.health_check_monitors[0].pk,
            "tenant": self.tenant1.pk,
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "name": "Load Balance Pool 2",
            "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_validate_name_is_required(self):
        """Test that the name field is required."""

        data = {
            "load_balancing_algorithm": choices.LoadBalancingAlgorithmChoices.ROUND_ROBIN,
            "virtual_server": self.virtual_servers[0].pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["name"])

    def test_validate_load_balancing_algorithm_is_required(self):
        """Test that the load_balancing_algorithm field is required."""

        data = {
            "name": "Load Balance Pool 4",
            "virtual_server": self.virtual_servers[0].pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["load_balancing_algorithm"])


# pylint: disable=no-member
class LoadBalancerPoolMemberFormTest(LoadBalancerModelsTestCaseMixin, FormTestCases.BaseFormTestCase):
    """Test the LoadBalancerPoolMember form."""

    form_class = forms.LoadBalancerPoolMemberForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "ip_address": self.ip1.pk,
            "load_balancer_pool": self.load_balancer_pools[0].pk,
            "certificate_profiles": [self.certificate_profiles[0]],
            "port": 123,
            "ssl_offload": True,
            "health_check_monitor": self.health_check_monitors[1].pk,
            "tenant": self.tenant1.pk,
            "status": self.status.pk,
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {
            "ip_address": self.ip2.pk,
            "load_balancer_pool": self.load_balancer_pools[0].pk,
            "port": 123,
            "ssl_offload": False,
            "status": self.status.pk,
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_validate_ip_address_is_required(self):
        """Test that the ip_address field is required."""

        data = {
            "load_balancer_pool": self.load_balancer_pools[0].pk,
            "certificate_profiles": [self.certificate_profiles[0]],
            "port": 123,
            "ssl_offload": True,
            "health_check_monitor": self.health_check_monitors[0].pk,
            "tenant": self.tenant1.pk,
            "status": self.status.pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["ip_address"])

    def test_validate_load_balancer_pool_is_required(self):
        """Test that the load_balancer_pool field is required."""

        data = {
            "ip_address": self.ip1.pk,
            "certificate_profiles": [self.certificate_profiles[0]],
            "port": 123,
            "ssl_offload": True,
            "health_check_monitor": self.health_check_monitors[0].pk,
            "tenant": self.tenant1.pk,
            "status": self.status.pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["load_balancer_pool"])

    def test_validate_port_is_required(self):
        """Test that the port field is required."""

        data = {
            "ip_address": self.ip1.pk,
            "load_balancer_pool": self.load_balancer_pools[0].pk,
            "port": None,
            "certificate_profiles": [self.certificate_profiles[0]],
            "ssl_offload": True,
            "health_check_monitor": self.health_check_monitors[1].pk,
            "tenant": self.tenant1.pk,
            "status": self.status.pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["port"])

    def test_validate_status_is_required(self):
        """Test that the status field is required."""

        data = {
            "ip_address": self.ip1.pk,
            "load_balancer_pool": self.load_balancer_pools[0].pk,
            "certificate_profiles": [self.certificate_profiles[0]],
            "port": 123,
            "ssl_offload": True,
            "health_check_monitor": self.health_check_monitors[0].pk,
            "tenant": self.tenant1.pk,
        }
        form = self.form_class(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("This field is required.", form.errors["status"])


class HealthCheckMonitorFormTest(LoadBalancerModelsTestCaseMixin, FormTestCases.BaseFormTestCase):
    """Test the HealthCheckMonitor form."""

    form_class = forms.HealthCheckMonitorForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "name": "HTTPS Monitor 4",
            "interval": 4,
            "retry": 5,
            "timeout": 6,
            "port": 443,
            "health_check_type": choices.HealthCheckTypeChoices.HTTPS,
            "tenant": self.tenant2.pk,
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {"name": "DNS Monitor 4"}
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())


class CertificateProfileFormTest(LoadBalancerModelsTestCaseMixin, FormTestCases):
    """Test the CertificateProfile form."""

    form_class = forms.CertificateProfileForm

    def test_specifying_all_fields_success(self):
        """Test specifying all fields."""

        data = {
            "name": "Certificate Profile 4",
            "certificate_type": choices.CertificateTypeChoices.TYPE_CLIENT,
            "certificate_file_path": "test_certificate.crt",
            "chain_file_path": "chain.pem",
            "key_file_path": "id_rsa.key",
            "expiration_date": "2022-01-01",
            "cipher": "RSA-AES256-GCM-SHA384",
            "tenant": self.tenant2.pk,
        }
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_specifying_required_fields_success(self):
        """Test specifying only required fields."""

        data = {"name": "Certificate Profile 5"}
        form = self.form_class(data=data)
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())
