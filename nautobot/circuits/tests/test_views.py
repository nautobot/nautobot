import datetime

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from nautobot.circuits.models import (
    Circuit,
    CircuitTermination,
    CircuitTerminationSideChoices,
    CircuitType,
    Provider,
    ProviderNetwork,
)
from nautobot.cloud.models import CloudAccount, CloudNetwork, CloudResourceType
from nautobot.core.testing import post_data, TestCase as NautobotTestCase, utils, ViewTestCases
from nautobot.dcim.models.devices import Manufacturer
from nautobot.dcim.models.locations import Location, LocationType
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

        cls.bulk_edit_data = {
            "asn": 65009,
            "account": "this-is-a-long-account-number-012345678901234567890123456789",
            "portal_url": "http://example.com/portal2",
            "noc_contact": "noc2@example.com",
            "admin_contact": "admin2@example.com",
            "comments": "New comments",
        }


class CircuitTypeTestCase(ViewTestCases.OrganizationalObjectViewTestCase, ViewTestCases.BulkEditObjectsViewTestCase):
    model = CircuitType

    @classmethod
    def setUpTestData(cls):
        cls.form_data = {
            "name": "Circuit Type X",
            "description": "A new circuit type",
        }
        cls.bulk_edit_data = {
            "description": "A new updated circuit type",
        }


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
    ViewTestCases.BulkDeleteObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
):
    model = CircuitTermination

    @classmethod
    def setUpTestData(cls):
        provider = Provider.objects.first()

        # Set up Manufacturer for cloud account
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer")

        # Provider Network
        provider_network = ProviderNetwork.objects.create(
            name="Test Provider Network 1",
            provider=provider,
        )

        # Cloud account and resource type
        cloud_account = CloudAccount.objects.create(
            name="Test Cloud Account",
            provider=manufacturer,
        )
        cloud_resource_type = CloudResourceType.objects.create(
            name="VPC Network",
            provider=manufacturer,
        )
        cloud_network = CloudNetwork.objects.create(
            name="Test Cloud Network",
            cloud_account=cloud_account,
            cloud_resource_type=cloud_resource_type,
        )

        # Location Type and Location
        location_type = LocationType.objects.get(name="Building")
        location_type.content_types.add(ContentType.objects.get_for_model(CircuitTermination))
        status = Status.objects.get_for_model(Location).first()
        location = Location.objects.create(name="NYC02", location_type=location_type, status=status)

        # Circuit setup
        circuit_type = CircuitType.objects.first()
        status = Status.objects.get_for_model(Circuit).first()

        circuit1 = Circuit.objects.create(
            cid="Test Circuit 1",
            provider=provider,
            circuit_type=circuit_type,
            status=status,
        )
        circuit2 = Circuit.objects.create(
            cid="Test Circuit 2",
            provider=provider,
            circuit_type=circuit_type,
            status=status,
        )

        # Terminations
        CircuitTermination.objects.create(
            circuit=circuit1,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            location=location,
            port_speed=1000000,
            upstream_speed=1000000,
            xconnect_id="XC-001",
            pp_info="Patch-01",
            description="Initial termination A",
        )
        CircuitTermination.objects.create(
            circuit=circuit1,
            term_side=CircuitTerminationSideChoices.SIDE_Z,
            provider_network=provider_network,
            port_speed=1000000,
            upstream_speed=1000000,
            xconnect_id="XC-002",
            pp_info="Patch-02",
            description="Initial termination Z",
        )
        CircuitTermination.objects.create(
            circuit=circuit2,
            term_side=CircuitTerminationSideChoices.SIDE_A,
            cloud_network=cloud_network,
            port_speed=1000000,
            upstream_speed=1000000,
            xconnect_id="XC-003",
            pp_info="Patch-03",
            description="Initial termination cloud A",
        )

        cls.bulk_edit_data = {
            "location": location.pk,
            "provider_network": None,
            "cloud_network": None,
            "port_speed": 2000000,
            "upstream_speed": 1500000,
            "xconnect_id": "Updated XConnect Location",
            "pp_info": "Updated Patch Panel Info Location",
            "description": "Updated description for Location",
        }

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
        self.assertBodyContains(response, "Test Provider Network")
        self.assertNotIn("</span> Connect", utils.extract_page_body(response.content.decode(response.charset)))

        # Visit the circuit object detail page and check there is no connect button present:
        response = self.client.get(reverse("circuits:circuit", kwargs={"pk": circuit.pk}))
        self.assertNotIn("</span> Connect", utils.extract_page_body(response.content.decode(response.charset)))


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
