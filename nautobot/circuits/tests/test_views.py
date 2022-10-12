import datetime
from django.urls import reverse

from nautobot.circuits.models import (
    Circuit,
    CircuitTermination,
    CircuitTerminationSideChoices,
    CircuitType,
    Provider,
    ProviderNetwork,
)
from nautobot.extras.models import Status, Tag
from nautobot.utilities.testing import post_data, TestCase as NautobotTestCase, ViewTestCases


class ProviderTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Provider

    @classmethod
    def setUpTestData(cls):

        Provider.objects.create(name="Provider 1", slug="provider-1", asn=65001)
        Provider.objects.create(name="Provider 2", slug="provider-2", asn=65002)
        Provider.objects.create(name="Provider 3", slug="provider-3", asn=65003)
        Provider.objects.create(name="Provider 8", asn=65003)

        cls.form_data = {
            "name": "Provider X",
            "slug": "provider-x",
            "asn": 65123,
            "account": "this-is-a-long-account-number-012345678901234567890123456789",
            "portal_url": "http://example.com/portal",
            "noc_contact": "noc@example.com",
            "admin_contact": "admin@example.com",
            "comments": "Another provider",
            "tags": [t.pk for t in Tag.objects.get_for_model(Provider)],
        }

        cls.csv_data = (
            "name,slug",
            "Provider 4,provider-4",
            "Provider 5,provider-5",
            "Provider 6,provider-6",
            "Provider 7,",
        )

        cls.bulk_edit_data = {
            "asn": 65009,
            "account": "this-is-a-long-account-number-012345678901234567890123456789",
            "portal_url": "http://example.com/portal2",
            "noc_contact": "noc2@example.com",
            "admin_contact": "admin2@example.com",
            "comments": "New comments",
        }

        cls.slug_source = "name"
        cls.slug_test_object = "Provider 8"


class CircuitTypeTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = CircuitType

    @classmethod
    def setUpTestData(cls):

        CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1")
        CircuitType.objects.create(name="Circuit Type 2", slug="circuit-type-2")
        CircuitType.objects.create(name="Circuit Type 3", slug="circuit-type-3")
        CircuitType.objects.create(name="Circuit Type 8")

        cls.form_data = {
            "name": "Circuit Type X",
            "slug": "circuit-type-x",
            "description": "A new circuit type",
        }

        cls.csv_data = (
            "name,slug",
            "Circuit Type 4,circuit-type-4",
            "Circuit Type 5,circuit-type-5",
            "Circuit Type 6,circuit-type-6",
            "Circuit Type 7,",
        )

        cls.slug_source = "name"
        cls.slug_test_object = "Circuit Type 8"


class CircuitTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Circuit

    @classmethod
    def setUpTestData(cls):

        providers = (
            Provider.objects.create(name="Provider 1", slug="provider-1", asn=65001),
            Provider.objects.create(name="Provider 2", slug="provider-2", asn=65002),
        )

        circuittypes = (
            CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1"),
            CircuitType.objects.create(name="Circuit Type 2", slug="circuit-type-2"),
        )

        statuses = Status.objects.get_for_model(Circuit)

        Circuit.objects.create(
            cid="Circuit 1",
            provider=providers[0],
            type=circuittypes[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 2",
            provider=providers[0],
            type=circuittypes[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 3",
            provider=providers[0],
            type=circuittypes[0],
            status=statuses[0],
        )

        cls.form_data = {
            "cid": "Circuit X",
            "provider": providers[1].pk,
            "type": circuittypes[1].pk,
            "status": statuses.get(slug="decommissioned").pk,
            "tenant": None,
            "install_date": datetime.date(2020, 1, 1),
            "commit_rate": 1000,
            "description": "A new circuit",
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(Circuit)],
        }

        cls.csv_data = (
            "cid,provider,type,status",
            "Circuit 4,Provider 1,Circuit Type 1,active",
            "Circuit 5,Provider 1,Circuit Type 1,planned",
            "Circuit 6,Provider 1,Circuit Type 1,decommissioned",
        )

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "type": circuittypes[1].pk,
            "status": statuses.get(slug="decommissioned").pk,
            "tenant": None,
            "commit_rate": 2000,
            "description": "New description",
            "comments": "New comments",
        }


class ProviderNetworkTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = ProviderNetwork

    @classmethod
    def setUpTestData(cls):

        providers = (
            Provider(name="Provider 1", slug="provider-1"),
            Provider(name="Provider 2", slug="provider-2"),
        )
        Provider.objects.bulk_create(providers)

        ProviderNetwork.objects.bulk_create(
            [
                ProviderNetwork(name="Provider Network 1", slug="provider-network-1", provider=providers[0]),
                ProviderNetwork(name="Provider Network 2", slug="provider-network-2", provider=providers[0]),
                ProviderNetwork(name="Provider Network 3", slug="provider-network-3", provider=providers[0]),
                ProviderNetwork(name="Provider Network 8", provider=providers[0]),
            ]
        )

        cls.form_data = {
            "name": "ProviderNetwork X",
            "slug": "provider-network-x",
            "provider": providers[1].pk,
            "description": "A new ProviderNetwork",
            "comments": "Longer description goes here",
            "tags": [t.pk for t in Tag.objects.get_for_model(ProviderNetwork)],
        }

        cls.csv_data = (
            "name,slug,provider,description",
            "Provider Network 4,provider-network-4,Provider 1,Foo",
            "Provider Network 5,provider-network-5,Provider 1,Bar",
            "Provider Network 6,provider-network-6,Provider 1,Baz",
            "Provider Network 7,,Provider 1,Baz",
        )

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "description": "New description",
            "comments": "New comments",
        }

        cls.slug_test_object = "Provider Network 8"
        cls.slug_source = "name"


class CircuitTerminationTestCase(NautobotTestCase):
    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()

    def test_circuit_termination_detail_200(self):
        """
        This tests that a circuit termination's detail page (with a provider
        network instead of a site) returns a 200 response and doesn't contain the connect menu button.
        """

        # Set up the required objects:
        provider = Provider.objects.create(name="Test Provider", slug="test-provider", asn=12345)
        provider_network = ProviderNetwork.objects.create(
            name="Test Provider Network",
            slug="test-provider-network",
            provider=provider,
        )
        circuit_type = CircuitType.objects.create(name="Test Circuit Type", slug="test-circuit-type")
        active_status = Status.objects.get_for_model(Circuit).get(slug="active")
        circuit = Circuit.objects.create(
            cid="Test Circuit",
            provider=provider,
            type=circuit_type,
            status=active_status,
        )
        termination = CircuitTermination.objects.create(
            circuit=circuit, provider_network=provider_network, term_side=CircuitTerminationSideChoices.SIDE_A
        )

        # Visit the termination detail page and assert responses:
        response = self.client.get(reverse("circuits:circuittermination", kwargs={"pk": termination.pk}))
        self.assertEqual(200, response.status_code)
        self.assertIn("Test Provider Network", str(response.content))
        self.assertNotIn("</span> Connect", str(response.content))

        # Visit the circuit object detail page and check there is no connect button present:
        response = self.client.get(reverse("circuits:circuit", kwargs={"pk": circuit.pk}))
        self.assertNotIn("</span> Connect", str(response.content))


class CircuitSwapTerminationsTestCase(NautobotTestCase):
    def setUp(self):
        super().setUp()
        self.user.is_superuser = True
        self.user.save()

    def test_swap_circuit_termination(self):
        # Set up the required objects:
        provider = Provider.objects.create(name="Test Provider", slug="test-provider", asn=12345)
        provider_networks = (
            ProviderNetwork.objects.create(
                name="Test Provider Network 1",
                slug="test-provider-network-1",
                provider=provider,
            ),
            ProviderNetwork.objects.create(
                name="Test Provider Network 2",
                slug="test-provider-network-2",
                provider=provider,
            ),
        )
        circuit_type = CircuitType.objects.create(name="Test Circuit Type", slug="test-circuit-type")
        active_status = Status.objects.get_for_model(Circuit).get(slug="active")
        circuit = Circuit.objects.create(
            cid="Test Circuit",
            provider=provider,
            type=circuit_type,
            status=active_status,
        )
        CircuitTermination.objects.create(
            circuit=circuit,
            provider_network=provider_networks[0],
            term_side=CircuitTerminationSideChoices.SIDE_A,
        )
        CircuitTermination.objects.create(
            circuit=circuit,
            provider_network=provider_networks[1],
            term_side=CircuitTerminationSideChoices.SIDE_Z,
        )
        request = {
            "path": reverse("circuits:circuit_terminations_swap", kwargs={"pk": circuit.pk}),
            "data": post_data({"confirm": True}),
        }
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)

        termination_a = CircuitTermination.objects.get(circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_A)
        termination_z = CircuitTermination.objects.get(circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_Z)

        # Assert Swap
        self.assertEqual(termination_a.provider_network, provider_networks[1])
        self.assertEqual(termination_z.provider_network, provider_networks[0])
