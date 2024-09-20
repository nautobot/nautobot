from django.urls import reverse

from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.core.testing import APITestCase, APIViewTestCases
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Cable, Device, DeviceType, FrontPort, Interface, Location, RearPort
from nautobot.extras.models import Role, Status


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("circuits-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class ProviderTest(APIViewTestCases.APIViewTestCase):
    model = Provider
    create_data = [
        {
            "name": "Provider 4",
        },
        {
            "name": "Provider 5",
        },
        {
            "name": "Provider 6",
        },
        {
            "name": "Provider 7",
        },
    ]
    bulk_update_data = {
        "asn": 1234,
    }


class ProviderNetworkTest(APIViewTestCases.APIViewTestCase):
    model = ProviderNetwork

    @classmethod
    def setUpTestData(cls):
        providers = Provider.objects.all()[:2]

        provider_networks = (
            ProviderNetwork(name="Provider Network 1", provider=providers[0]),
            ProviderNetwork(name="Provider Network 2", provider=providers[0]),
            ProviderNetwork(name="Provider Network 3", provider=providers[0]),
        )
        ProviderNetwork.objects.bulk_create(provider_networks)

        cls.create_data = [
            {
                "name": "Provider Network 4",
                "provider": providers[0].pk,
            },
            {
                "name": "Provider Network 5",
                "provider": providers[0].pk,
            },
            {
                "name": "Provider Network 6",
                "provider": providers[0].pk,
            },
        ]

        cls.bulk_update_data = {
            "provider": providers[1].pk,
            "description": "New description",
        }


class CircuitTypeTest(APIViewTestCases.APIViewTestCase):
    model = CircuitType
    create_data = (
        {
            "name": "Circuit Type 4",
        },
        {
            "name": "Circuit Type 5",
        },
        {
            "name": "Circuit Type 6",
        },
        {"name": "Circuit Type 7"},
    )
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        # TODO: There is not enough CircuitTypes without associated Circuits for test_bulk_delete to jus work
        CircuitType.objects.create(name="Circuit Type 1")
        CircuitType.objects.create(name="Circuit Type 2")
        CircuitType.objects.create(name="Circuit Type 3")


class CircuitTest(APIViewTestCases.APIViewTestCase):
    model = Circuit

    @classmethod
    def setUpTestData(cls):
        providers = Provider.objects.all()[:2]

        circuit_types = CircuitType.objects.all()[:2]

        statuses = Status.objects.get_for_model(Circuit)

        Circuit.objects.create(
            cid="Circuit 1",
            provider=providers[0],
            circuit_type=circuit_types[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 2",
            provider=providers[0],
            circuit_type=circuit_types[0],
            status=statuses[0],
        )
        Circuit.objects.create(
            cid="Circuit 3",
            provider=providers[0],
            circuit_type=circuit_types[0],
            status=statuses[0],
        )

        cls.create_data = [
            {
                "cid": "Circuit 4",
                "provider": providers[1].pk,
                "circuit_type": circuit_types[1].pk,
                "status": statuses[1].pk,
            },
            {
                "cid": "Circuit 5",
                "provider": providers[1].pk,
                "circuit_type": circuit_types[1].pk,
                "status": statuses[1].pk,
            },
            {
                "cid": "Circuit 6",
                "provider": providers[1].pk,
                "circuit_type": circuit_types[1].pk,
                "status": statuses[1].pk,
            },
        ]

        cls.bulk_update_data = {
            "status": statuses[2].pk,
        }


class CircuitTerminationTest(APIViewTestCases.APIViewTestCase):
    model = CircuitTermination
    choices_fields = ["term_side"]

    @classmethod
    def setUpTestData(cls):
        SIDE_A = CircuitTerminationSideChoices.SIDE_A
        SIDE_Z = CircuitTerminationSideChoices.SIDE_Z

        locations = (
            Location.objects.first(),
            Location.objects.last(),
        )
        cls.locations = locations

        provider = Provider.objects.first()
        circuit_type = CircuitType.objects.first()
        status = Status.objects.get_for_model(Circuit).first()

        circuits = (
            Circuit.objects.create(cid="Circuit 1", provider=provider, circuit_type=circuit_type, status=status),
            Circuit.objects.create(cid="Circuit 2", provider=provider, circuit_type=circuit_type, status=status),
            Circuit.objects.create(cid="Circuit 3", provider=provider, circuit_type=circuit_type, status=status),
        )
        cls.circuits = circuits

        CircuitTermination.objects.create(circuit=circuits[0], location=locations[0], term_side=SIDE_A)
        CircuitTermination.objects.create(circuit=circuits[0], location=locations[1], term_side=SIDE_Z)
        CircuitTermination.objects.create(circuit=circuits[1], location=locations[0], term_side=SIDE_A)
        CircuitTermination.objects.create(circuit=circuits[1], location=locations[1], term_side=SIDE_Z)

        cls.create_data = [
            {
                "circuit": circuits[2].pk,
                "term_side": SIDE_A,
                "location": locations[0].pk,
                "port_speed": 200000,
            },
            {
                "circuit": circuits[2].pk,
                "term_side": SIDE_Z,
                "location": locations[1].pk,
                "port_speed": 200000,
            },
        ]
        # Cannot use cls.create_data for test_update_object() here.
        # Because the first instance of CircuitTermination might have a provider_network
        # Setting a location on that instance will raise an validation error.
        cls.update_data = {
            "circuit": circuits[2].pk,
            "term_side": SIDE_A,
            "port_speed": 200000,
        }

        cls.bulk_update_data = {"port_speed": 123456}

    def test_circuit_termination_connected_endpoint(self):
        """Assert that API response for CircuitTermination connected cables to CircuitTermination, Interface, FortPort, or RearPort does not raise any errors"""
        # Fix for https://github.com/nautobot/nautobot/issues/3179
        self.add_permissions("circuits.view_circuittermination")

        status = Status.objects.get_for_model(Cable).first()
        device_status = Status.objects.get_for_model(Device).first()
        interface_status = Status.objects.get_for_model(Interface).first()
        device_type = DeviceType.objects.exclude(manufacturer__isnull=True).first()
        device_role = Role.objects.get_for_model(Device).first()
        device = Device.objects.create(
            device_type=device_type, role=device_role, name="Device", location=self.locations[0], status=device_status
        )
        circuits = self.circuits

        interface = Interface.objects.create(
            device=device, type=InterfaceTypeChoices.TYPE_1GE_FIXED, name="Interface 001", status=interface_status
        )
        rearport1 = RearPort.objects.create(device=device, name="Rear Port 1", positions=1)
        frontport1 = FrontPort.objects.create(
            device=device, name="Front Port 1", rear_port=rearport1, rear_port_position=1
        )

        CircuitTermination.objects.create(
            circuit=circuits[2], location=self.locations[0], term_side=CircuitTerminationSideChoices.SIDE_A
        )
        CircuitTermination.objects.create(
            circuit=circuits[2], location=self.locations[0], term_side=CircuitTerminationSideChoices.SIDE_Z
        )

        with self.subTest("Assert CircuitTermination Cable connected to an Interface and Rear Port"):
            Cable.objects.create(
                termination_a=circuits[0].circuit_termination_a, termination_b=interface, label="Cable 1", status=status
            )
            Cable.objects.create(
                termination_a=circuits[0].circuit_termination_z, termination_b=rearport1, label="Cable 2", status=status
            )

            response = self.client.get(
                circuits[0].circuit_termination_a.get_absolute_url(api=True),
                **self.header,
            )
            self.assertEqual(response.status_code, 200, response.json())
            response = self.client.get(
                circuits[0].circuit_termination_z.get_absolute_url(api=True),
                **self.header,
            )
            self.assertEqual(response.status_code, 200, response.json())

        with self.subTest("Assert CircuitTermination Cable connected to a FrontPort and CircuitTermination"):
            Cable.objects.create(
                termination_a=circuits[2].circuit_termination_a,
                termination_b=circuits[1].circuit_termination_z,
                label="Cable 3",
                status=status,
            )
            Cable.objects.create(
                termination_a=circuits[2].circuit_termination_z,
                termination_b=frontport1,
                label="Cable 4",
                status=status,
            )

            response = self.client.get(
                circuits[2].circuit_termination_a.get_absolute_url(api=True),
                **self.header,
            )
            self.assertEqual(response.status_code, 200, response.json())
            response = self.client.get(
                circuits[2].circuit_termination_z.get_absolute_url(api=True),
                **self.header,
            )
            self.assertEqual(response.status_code, 200, response.json())
