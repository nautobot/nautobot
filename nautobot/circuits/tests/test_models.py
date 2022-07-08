from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import TestCase

from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.dcim.models import Location, LocationType, Site
from nautobot.extras.models import Status


class CircuitTerminationModelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        active = Status.objects.get(name="Active")
        provider = Provider.objects.create(name="Provider 1", slug="provider-1")
        circuit_type = CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1")

        location_type_1 = LocationType.objects.create(name="Root Type")
        location_type_2 = LocationType.objects.create(name="Leaf Type", parent=location_type_1)
        location_type_2.content_types.add(ContentType.objects.get_for_model(CircuitTermination))

        cls.circuit = Circuit.objects.create(cid="Circuit 1", provider=provider, type=circuit_type)
        cls.site = Site.objects.create(name="Site 1", slug="site-1", status=active)
        cls.provider_network = ProviderNetwork.objects.create(name="Provider Network 1", provider=provider)
        cls.location_1 = Location.objects.create(
            name="Root", location_type=location_type_1, status=active, site=cls.site
        )
        cls.location_2 = Location.objects.create(
            name="Leaf", location_type=location_type_2, status=active, parent=cls.location_1
        )

    def test_site_or_provider_network_are_required(self):
        ct = CircuitTermination(circuit=self.circuit, term_side=CircuitTerminationSideChoices.SIDE_A)
        with self.assertRaises(ValidationError) as cm:
            ct.validated_save()
        self.assertIn("must attach to either a site or a provider network", str(cm.exception))

    def test_site_and_provider_network_mutually_exclusive(self):
        ct = CircuitTermination(
            circuit=self.circuit,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            site=self.site,
            provider_network=self.provider_network,
        )
        with self.assertRaises(ValidationError) as cm:
            ct.validated_save()
        self.assertIn("cannot attach to both a site and a provider network", str(cm.exception))

    def test_location_and_provider_network_mutually_exclusive(self):
        ct = CircuitTermination(
            circuit=self.circuit,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            provider_network=self.provider_network,
            location=self.location_2,
        )
        with self.assertRaises(ValidationError) as cm:
            ct.validated_save()
        self.assertIn("cannot attach to both a location and a provider network", str(cm.exception))

    def test_location_same_site_enforced(self):
        ct = CircuitTermination(
            circuit=self.circuit,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            site=self.site,
            location=self.location_2,
        )
        ct.validated_save()

        ct2 = CircuitTermination(
            circuit=self.circuit,
            term_side=CircuitTerminationSideChoices.SIDE_Z,
            site=Site.objects.create(name="Different Site"),
            location=self.location_2,
        )
        with self.assertRaises(ValidationError) as cm:
            ct2.validated_save()
        self.assertIn('does not belong to site "Different Site"', str(cm.exception))

    def test_location_content_type_enforced(self):
        ct = CircuitTermination(
            circuit=self.circuit,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            site=self.site,
            location=self.location_1,
        )
        with self.assertRaises(ValidationError) as cm:
            ct.validated_save()
        self.assertIn('may not associate to locations of type "Root Type"', str(cm.exception))
