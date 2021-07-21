from django.urls import reverse

from nautobot.circuits.choices import *
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.dcim.models import Site
from nautobot.extras.models import Status
from nautobot.utilities.testing import APITestCase, APIViewTestCases


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("circuits-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class ProviderTest(APIViewTestCases.APIViewTestCase):
    model = Provider
    brief_fields = ["circuit_count", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Provider 4",
            "slug": "provider-4",
        },
        {
            "name": "Provider 5",
            "slug": "provider-5",
        },
        {
            "name": "Provider 6",
            "slug": "provider-6",
        },
    ]
    bulk_update_data = {
        "asn": 1234,
    }

    @classmethod
    def setUpTestData(cls):

        Provider.objects.create(name="Provider 1", slug="provider-1")
        Provider.objects.create(name="Provider 2", slug="provider-2")
        Provider.objects.create(name="Provider 3", slug="provider-3")


class CircuitTypeTest(APIViewTestCases.APIViewTestCase):
    model = CircuitType
    brief_fields = ["circuit_count", "display", "id", "name", "slug", "url"]
    create_data = (
        {
            "name": "Circuit Type 4",
            "slug": "circuit-type-4",
        },
        {
            "name": "Circuit Type 5",
            "slug": "circuit-type-5",
        },
        {
            "name": "Circuit Type 6",
            "slug": "circuit-type-6",
        },
    )
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1")
        CircuitType.objects.create(name="Circuit Type 2", slug="circuit-type-2")
        CircuitType.objects.create(name="Circuit Type 3", slug="circuit-type-3")


class CircuitTest(APIViewTestCases.APIViewTestCase):
    model = Circuit
    brief_fields = ["cid", "display", "id", "url"]
    bulk_update_data = {
        "status": "planned",
    }
    choices_fields = ["status"]

    @classmethod
    def setUpTestData(cls):

        providers = (
            Provider.objects.create(name="Provider 1", slug="provider-1"),
            Provider.objects.create(name="Provider 2", slug="provider-2"),
        )

        circuit_types = (
            CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1"),
            CircuitType.objects.create(name="Circuit Type 2", slug="circuit-type-2"),
        )

        statuses = Status.objects.get_for_model(Circuit)

        Circuit.objects.create(
            cid="Circuit 1",
            provider=providers[0],
            type=circuit_types[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 2",
            provider=providers[0],
            type=circuit_types[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 3",
            provider=providers[0],
            type=circuit_types[0],
            status=statuses[0],
        )

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "cid": "Circuit 4",
                "provider": providers[1].pk,
                "type": circuit_types[1].pk,
                "status": "offline",
            },
            {
                "cid": "Circuit 5",
                "provider": providers[1].pk,
                "type": circuit_types[1].pk,
                "status": "offline",
            },
            {
                "cid": "Circuit 6",
                "provider": providers[1].pk,
                "type": circuit_types[1].pk,
                "status": "offline",
            },
        ]


class CircuitTerminationTest(APIViewTestCases.APIViewTestCase):
    model = CircuitTermination
    brief_fields = ["cable", "circuit", "display", "id", "term_side", "url"]
    choices_fields = ["term_side"]

    @classmethod
    def setUpTestData(cls):
        SIDE_A = CircuitTerminationSideChoices.SIDE_A
        SIDE_Z = CircuitTerminationSideChoices.SIDE_Z

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        provider = Provider.objects.create(name="Provider 1", slug="provider-1")
        circuit_type = CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1")

        circuits = (
            Circuit.objects.create(cid="Circuit 1", provider=provider, type=circuit_type),
            Circuit.objects.create(cid="Circuit 2", provider=provider, type=circuit_type),
            Circuit.objects.create(cid="Circuit 3", provider=provider, type=circuit_type),
        )

        CircuitTermination.objects.create(circuit=circuits[0], site=sites[0], term_side=SIDE_A)
        CircuitTermination.objects.create(circuit=circuits[0], site=sites[1], term_side=SIDE_Z)
        CircuitTermination.objects.create(circuit=circuits[1], site=sites[0], term_side=SIDE_A)
        CircuitTermination.objects.create(circuit=circuits[1], site=sites[1], term_side=SIDE_Z)

        cls.create_data = [
            {
                "circuit": circuits[2].pk,
                "term_side": SIDE_A,
                "site": sites[1].pk,
                "port_speed": 200000,
            },
            {
                "circuit": circuits[2].pk,
                "term_side": SIDE_Z,
                "site": sites[1].pk,
                "port_speed": 200000,
            },
        ]

        cls.bulk_update_data = {"port_speed": 123456}
