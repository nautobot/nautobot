from django.urls import reverse

from nautobot.circuits.models import Circuit, CircuitType, Provider
from nautobot.extras.models import Status
from nautobot.utilities.testing import TestCase


class URLTestCase(TestCase):
    def test_nautobot_ui_viewset_urls(self):
        """Asset that NautobotUIViewSet views urls includes a trailing slash"""
        provider = Provider.objects.create(name="Provider")
        circuit_type = CircuitType.objects.create(name="Circuit Type 1")
        status = Status.objects.get_for_model(Circuit).first()
        circuit = Circuit.objects.create(
            cid="Circuit",
            provider=provider,
            type=circuit_type,
            status=status,
        )
        url = f"/circuits/circuits/{circuit.pk}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 301)
        # Assert url is redirected to include a trailing slash
        self.assertEqual(response.url, f"/circuits/circuits/{circuit.pk}/")
        # Assert reverse url include a trailing slash
        self.assertEqual(reverse("circuits:provider", args=[circuit.pk]), f"/circuits/providers/{circuit.pk}/")
