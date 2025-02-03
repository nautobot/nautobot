import collections
from pathlib import Path

from django.core.management import call_command
import yaml

from nautobot.core.testing import TestCase


class ManagementCommandTestCase(TestCase):
    """Test case for core management commands."""

    def setUp(self):
        """Initialize user and client."""
        super().setUpNautobot()
        self.user.is_superuser = True
        self.user.save()
        self.client.force_login(self.user)

    def test_generate_performance_test_endpoints(self):
        """Test the generate_performance_test_endpoints management command."""

        call_command("generate_performance_test_endpoints")
        endpoints_dict = yaml.safe_load(Path("./endpoints.yml").read_text())["endpoints"]
        # status_code_to_endpoints = collections.defaultdict(list)
        for _, value in endpoints_dict.items():
            for endpoint in value:
                response = self.client.get(endpoint, follow=True)
                if response.status_code != 200:
                    print(endpoint)
                    print(response.content)
                # self.assertHttpStatus(response, 200, response.content)
