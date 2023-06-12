from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError

from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.core.testing.models import ModelTestCases
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import Status


class CircuitTerminationModelTestCase(ModelTestCases.BaseModelTestCase):
    model = CircuitTermination

    @classmethod
    def setUpTestData(cls):
        provider = Provider.objects.first()
        circuit_type = CircuitType.objects.first()

        location_type_1 = LocationType.objects.get(name="Campus")
        location_type_1.content_types.set([])
        location_type_2 = LocationType.objects.get(name="Building")
        location_type_2.content_types.add(ContentType.objects.get_for_model(CircuitTermination))
        status = Status.objects.get_for_model(Circuit).first()
        cls.circuit = Circuit.objects.create(
            cid="Circuit 1", provider=provider, circuit_type=circuit_type, status=status
        )
        cls.provider_network = ProviderNetwork.objects.create(name="Provider Network 1", provider=provider)
        cls.location_1 = Location.objects.filter(location_type=location_type_1)[0]
        cls.location_2 = Location.objects.filter(location_type=location_type_2)[0]

    def test_location_or_provider_network_are_required(self):
        ct = CircuitTermination(circuit=self.circuit, term_side=CircuitTerminationSideChoices.SIDE_A)
        with self.assertRaises(ValidationError) as cm:
            ct.validated_save()
        self.assertIn("must attach to either a location or a provider network", str(cm.exception))

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

    def test_location_content_type_enforced(self):
        ct = CircuitTermination(
            circuit=self.circuit,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            location=self.location_1,
        )
        with self.assertRaises(ValidationError) as cm:
            ct.validated_save()
        self.assertIn(
            f'may not associate to locations of type "{self.location_1.location_type.name}"', str(cm.exception)
        )
