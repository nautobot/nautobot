from io import StringIO

from django.core.management import call_command
import yaml

from nautobot.core.testing import TestCase


class ManagementCommandTestCase(TestCase):
    """Test case for core management commands."""

    def setUp(self):
        """Initialize user and client."""
        super().setUpNautobot()
        self.user.is_superuser = True
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)

    def test_generate_performance_test_endpoints(self):
        """Test the generate_performance_test_endpoints management command."""
        out = StringIO()
        call_command("generate_performance_test_endpoints", stdout=out)
        endpoints_dict = yaml.safe_load(out.getvalue())["endpoints"]
        # status_code_to_endpoints = collections.defaultdict(list)
        for view_name, value in endpoints_dict.items():
            for endpoint in value:
                response = self.client.get(endpoint, follow=True)
                self.assertHttpStatus(
                    response, 200, f"{view_name}: {endpoint} returns status Code {response.status_code} instead of 200"
                )
