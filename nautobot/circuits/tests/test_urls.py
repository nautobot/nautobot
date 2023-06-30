from django.urls import reverse

from nautobot.circuits.models import Provider
from nautobot.utilities.testing import TestCase


class URLTestCase(TestCase):
    def test_nautobot_ui_viewset_urls(self):
        """Asset that NautobotUIViewSet views urls includes a trailing slash"""
        provider = Provider.objects.create(name="Provider 1", slug="provider-1")
        url = f"/circuits/providers/{provider.slug}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 301)
        # Assert url is redirected to include a trailing slash
        self.assertEqual(response.url, f"/circuits/providers/{provider.slug}/")
        # Assert reverse url include a trailing slash
        self.assertEqual(reverse("circuits:provider", args=[provider.slug]), f"/circuits/providers/{provider.slug}/")
