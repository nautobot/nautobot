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
from nautobot.core.testing import post_data, TestCase as NautobotTestCase, ViewTestCases
from nautobot.dcim.models import Location
from nautobot.extras.models import Status, Tag


class ProviderTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Provider

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "Provider X",
            "asn": 65123,
            "account": "this-is-a-long-account-number-012345678901234567890123456789",
            "portal_url": "http://example.com/portal",
            "noc_contact": "noc@example.com",
            "admin_contact": "admin@example.com",
            "comments": "Another provider",
            "tags": [t.pk for t in Tag.objects.get_for_model(Provider)],
        }

        cls.csv_data = (
            "name,asn,comments",
            "Provider 4,1234,A comment",
            "Provider 5,1234,A comment",
            "Provider 6,1234,A comment",
            "Provider 7,1234,A comment",
        )

        cls.bulk_edit_data = {
            "asn": 65009,
            "account": "this-is-a-long-account-number-012345678901234567890123456789",
            "portal_url": "http://example.com/portal2",
            "noc_contact": "noc2@example.com",
            "admin_contact": "admin2@example.com",
            "comments": "New comments",
        }


class CircuitTypeTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = CircuitType

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "Circuit Type X",
            "description": "A new circuit type",
        }

        cls.csv_data = (
            "name,description",
            "Circuit Type 4,A circuit type",
            "Circuit Type 5,A circuit type",
            "Circuit Type 6,A circuit type",
            "Circuit Type 7,A circuit type",
        )


class CircuitTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Circuit

    @classmethod
    def setUpTestData(cls):
        providers = Provider.objects.all()[:2]

        circuittypes = CircuitType.objects.all()[:2]

        statuses = Status.objects.get_for_model(Circuit)

        Circuit.objects.create(
            cid="Circuit 1",
            provider=providers[0],
            circuit_type=circuittypes[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 2",
            provider=providers[0],
            circuit_type=circuittypes[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 3",
            provider=providers[0],
            circuit_type=circuittypes[0],
            status=statuses[0],
        )

        cls.form_data = {
            "cid": "Circuit X",
            "provider": providers[1].pk,
            "circuit_type": circuittypes[1].pk,
            "status": statuses.last().pk,
            "tenant": None,
            "install_date": datetime.date(2020, 1, 1),
            "commit_rate": 1000,
            "description": "A new circuit",
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(Circuit)],
        }

        cls.csv_data = (
            "cid,provider,circuit_type,status",
            f'Circuit 4,"{providers[0].name}",{circuittypes[0].name},{statuses.first().name}',
            f'Circuit 5,"{providers[0].name}",{circuittypes[1].name},{statuses.first().name}',
            f'Circuit 6,"{providers[1].name}",{circuittypes[1].name},{statuses.first().name}',
        )

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "circuit_type": circuittypes[1].pk,
            "status": statuses.last().pk,
            "tenant": None,
            "commit_rate": 2000,
            "description": "New description",
            "comments": "New comments",
        }


class ProviderNetworkTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = ProviderNetwork

    @classmethod
    def setUpTestData(cls):
        providers = Provider.objects.all()[:2]

        ProviderNetwork.objects.bulk_create(
            [
                ProviderNetwork(name="Provider Network 1", provider=providers[0]),
                ProviderNetwork(name="Provider Network 2", provider=providers[0]),
                ProviderNetwork(name="Provider Network 3", provider=providers[0]),
                ProviderNetwork(name="Provider Network 8", provider=providers[0]),
            ]
        )

        cls.form_data = {
            "name": "ProviderNetwork X",
            "provider": providers[1].pk,
            "description": "A new ProviderNetwork",
            "comments": "Longer description goes here",
            "tags": [t.pk for t in Tag.objects.get_for_model(ProviderNetwork)],
        }

        cls.csv_data = (
            "name,provider,description",
            f'Provider Network 4,"{providers[0].name}",Foo',
            f'Provider Network 5,"{providers[0].name}",Bar',
            f'Provider Network 6,"{providers[0].name}",Baz',
            f'Provider Network 7,"{providers[0].name}",Baz',
        )

        cls.bulk_edit_data = {
            "provider": providers[1].pk,
            "description": "New description",
            "comments": "New comments",
        }


class CircuitTerminationTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    # create/edit views are special cases, not currently tested
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
    # No bulk-edit support currently
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = CircuitTermination

    @classmethod
    def setUpTestData(cls):
        circuit = Circuit.objects.filter(circuit_terminations__isnull=True).first()
        provider_network = ProviderNetwork.objects.filter(circuit_terminations__isnull=True).first()
        location = Location.objects.get_for_model(CircuitTermination).first()

        cls.csv_data = (
            "term_side,circuit,location,provider_network,port_speed",
            f"A,{circuit.composite_key},{location.composite_key}",
            f"Z,{circuit.composite_key},,{provider_network.composite_key},1000",
        )

    def test_circuit_termination_detail_200(self):
        """
        This tests that a circuit termination's detail page (with a provider
        network instead of a site) returns a 200 response and doesn't contain the connect menu button.
        """
        self.user.is_superuser = True
        self.user.save()

        # Set up the required objects:
        provider = Provider.objects.first()
        provider_network = ProviderNetwork.objects.create(
            name="Test Provider Network",
            provider=provider,
        )
        circuit_type = CircuitType.objects.first()
        status = Status.objects.get_for_model(Circuit).first()
        circuit = Circuit.objects.create(
            cid="Test Circuit",
            provider=provider,
            circuit_type=circuit_type,
            status=status,
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
        provider = Provider.objects.first()
        provider_networks = (
            ProviderNetwork.objects.create(
                name="Test Provider Network 1",
                provider=provider,
            ),
            ProviderNetwork.objects.create(
                name="Test Provider Network 2",
                provider=provider,
            ),
        )
        circuit_type = CircuitType.objects.first()
        status = Status.objects.get_for_model(Circuit).first()
        circuit = Circuit.objects.create(
            cid="Test Circuit",
            provider=provider,
            circuit_type=circuit_type,
            status=status,
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

        circuit_termination_a = CircuitTermination.objects.get(
            circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_A
        )
        circuit_termination_z = CircuitTermination.objects.get(
            circuit=circuit, term_side=CircuitTerminationSideChoices.SIDE_Z
        )

        # Assert Swap
        self.assertEqual(circuit_termination_a.provider_network, provider_networks[1])
        self.assertEqual(circuit_termination_z.provider_network, provider_networks[0])
