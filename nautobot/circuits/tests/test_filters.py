from nautobot.circuits import factory
from nautobot.circuits.filters import (
    CircuitFilterSet,
    CircuitTerminationFilterSet,
    CircuitTypeFilterSet,
    ProviderFilterSet,
    ProviderNetworkFilterSet,
)
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.dcim.models import Cable, Device, DeviceType, Interface, Manufacturer, Region, Site
from nautobot.extras.models import Role, Status
from nautobot.utilities.testing import FilterTestCases


class ProviderTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Provider.objects.all()
    filterset = ProviderFilterSet

    @classmethod
    def setUpTestData(cls):

        providers = (
            Provider.objects.create(name="Provider 1", slug="provider-1", asn=65001, account="1234"),
            Provider.objects.create(name="Provider 2", slug="provider-2", asn=65002, account="2345"),
            Provider.objects.create(name="Provider 3", slug="provider-3", asn=65003, account="3456"),
            Provider.objects.create(name="Provider 4", slug="provider-4", asn=65004, account="4567"),
            Provider.objects.create(name="Provider 5", slug="provider-5", asn=65005, account="5678"),
            Provider.objects.create(
                name="Provider 6 (long account)",
                slug="provider-6",
                asn=65006,
                account="this-is-a-long-account-number-012345678901234567890123456789",
            ),
        )

        cls.regions = Region.objects.filter(sites__isnull=False, children__isnull=True, parent__isnull=True)[:2]

        cls.sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
        )

        circuit_types = (
            CircuitType.objects.create(name="Test Circuit Type 1", slug="test-circuit-type-1"),
            CircuitType.objects.create(name="Test Circuit Type 2", slug="test-circuit-type-2"),
        )

        circuits = (
            Circuit.objects.create(provider=providers[0], type=circuit_types[0], cid="Test Circuit 1"),
            Circuit.objects.create(provider=providers[1], type=circuit_types[1], cid="Test Circuit 1"),
        )

        CircuitTermination.objects.create(circuit=circuits[0], site=cls.sites[0], term_side="A")
        CircuitTermination.objects.create(circuit=circuits[1], site=cls.sites[0], term_side="A")

    def test_asn(self):
        params = {"asn": ["65001", "65002"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_account(self):
        params = {"account": ["1234", "2345"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        params = {"site_id": [self.sites[0].pk, self.sites[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"site": [self.sites[0].slug, self.sites[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        params = {"region_id": [self.regions[0].pk, self.regions[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"region": [self.regions[0].slug, self.regions[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class CircuitTypeTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = CircuitType.objects.all()
    filterset = CircuitTypeFilterSet

    @classmethod
    def setUpTestData(cls):

        CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1")
        CircuitType.objects.create(name="Circuit Type 2", slug="circuit-type-2")
        CircuitType.objects.create(name="Circuit Type 3", slug="circuit-type-3")


class CircuitTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Circuit.objects.all()
    filterset = CircuitFilterSet
    tenancy_related_name = "circuits"

    generic_filter_tests = (
        # (filter_name, field_name if different from filter name)
        ["cid"],
        ["install_date"],
        ["commit_rate"],
        ["provider_id", "provider__pk"],
        ["provider", "provider__slug"],
        ["provider_network_id", "terminations__provider_network"],
        ["type_id", "type__pk"],
        ["type", "type__slug"],
        ["status", "status__slug"],
        ["region_id", "terminations__site__region__pk"],  # failed no valid test data
        ["region", "terminations__site__region__slug"],  # failed no valid test data
        ["site_id", "terminations__site__pk"],
        ["site", "terminations__site__slug"],
    )

    @classmethod
    def setUpTestData(cls):

        factory.CircuitTypeFactory.create_batch(10)
        factory.ProviderFactory.create_batch(10)
        factory.CircuitFactory.create_batch(20)
        factory.CircuitTerminationFactory.create_batch(2, has_region=True, term_side="A")
        factory.CircuitTerminationFactory.create_batch(2, has_region=True, term_side="Z")
        factory.CircuitTerminationFactory.create_batch(2, has_site=False, term_side="A")
        factory.CircuitTerminationFactory.create_batch(2, has_site=False, term_side="Z")

    def test_filters_generic(self):
        for test in self.generic_filter_tests:
            filter_name = test[0]
            field_name = test[1] if len(test) == 2 else test[0]
            with self.subTest(f"{self.queryset.model._meta.object_name} filter {filter_name}"):
                test_data = self.get_filterset_test_values(field_name)
                params = {filter_name: test_data}
                filterset_result = self.filterset(params, self.queryset).qs
                qs_result = self.queryset.filter(**{f"{field_name}__in": test_data}).distinct()
                self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class CircuitTerminationTestCase(FilterTestCases.FilterTestCase):
    queryset = CircuitTermination.objects.all()
    filterset = CircuitTerminationFilterSet

    @classmethod
    def setUpTestData(cls):

        sites = Site.objects.all()
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 1",
            slug="test-device-type-1",
        )
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).get(slug="active")
        device1 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice1",
            site=sites[0],
            status=device_status,
        )
        device2 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice2",
            site=sites[1],
            status=device_status,
        )
        interface1 = Interface.objects.create(device=device1, name="eth0")
        interface2 = Interface.objects.create(device=device2, name="eth0")

        circuit_types = (CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1"),)

        providers = (
            Provider.objects.create(name="Provider 1", slug="provider-1"),
            Provider.objects.create(name="Provider 2", slug="provider-2"),
        )

        provider_networks = (
            ProviderNetwork(name="Provider Network 1", slug="provider-network-1", provider=providers[1]),
            ProviderNetwork(name="Provider Network 2", slug="provider-network-2", provider=providers[1]),
            ProviderNetwork(name="Provider Network 3", slug="provider-network-3", provider=providers[1]),
        )
        ProviderNetwork.objects.bulk_create(provider_networks)

        circuits = (
            Circuit(provider=providers[0], type=circuit_types[0], cid="Circuit 1"),
            Circuit(provider=providers[0], type=circuit_types[0], cid="Circuit 2"),
            Circuit(provider=providers[0], type=circuit_types[0], cid="Circuit 3"),
            Circuit(provider=providers[0], type=circuit_types[0], cid="Circuit 4"),
            Circuit(provider=providers[0], type=circuit_types[0], cid="Circuit 5"),
            Circuit(provider=providers[0], type=circuit_types[0], cid="Circuit 6"),
        )

        Circuit.objects.bulk_create(circuits)

        circuit_terminations = (
            CircuitTermination.objects.create(
                circuit=circuits[0],
                site=sites[0],
                term_side="A",
                port_speed=1000,
                upstream_speed=1000,
                xconnect_id="ABC",
            ),
            CircuitTermination.objects.create(
                circuit=circuits[0],
                site=sites[1],
                term_side="Z",
                port_speed=1000,
                upstream_speed=1000,
                xconnect_id="DEF",
            ),
            CircuitTermination.objects.create(
                circuit=circuits[1],
                site=sites[1],
                term_side="A",
                port_speed=2000,
                upstream_speed=2000,
                xconnect_id="GHI",
            ),
            CircuitTermination.objects.create(
                circuit=circuits[1],
                site=sites[2],
                term_side="Z",
                port_speed=2000,
                upstream_speed=2000,
                xconnect_id="JKL",
            ),
            CircuitTermination.objects.create(
                circuit=circuits[2],
                site=sites[2],
                term_side="A",
                port_speed=3000,
                upstream_speed=3000,
                xconnect_id="MNO",
            ),
            CircuitTermination.objects.create(
                circuit=circuits[2],
                site=sites[0],
                term_side="Z",
                port_speed=3000,
                upstream_speed=3000,
                xconnect_id="PQR",
            ),
            CircuitTermination.objects.create(
                circuit=circuits[3], provider_network=provider_networks[0], term_side="A"
            ),
            CircuitTermination.objects.create(
                circuit=circuits[4], provider_network=provider_networks[1], term_side="A"
            ),
            CircuitTermination.objects.create(
                circuit=circuits[5], provider_network=provider_networks[2], term_side="A"
            ),
        )

        cable_statuses = Status.objects.get_for_model(Cable)
        status_connected = cable_statuses.get(slug="connected")

        Cable.objects.create(
            termination_a=circuit_terminations[0],
            termination_b=interface1,
            status=status_connected,
        )
        Cable.objects.create(
            termination_a=circuit_terminations[1],
            termination_b=interface2,
            status=status_connected,
        )

    def test_term_side(self):
        params = {"term_side": "A"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 6)

    def test_port_speed(self):
        params = {"port_speed": ["1000", "2000"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_upstream_speed(self):
        params = {"upstream_speed": ["1000", "2000"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_xconnect_id(self):
        params = {"xconnect_id": ["ABC", "DEF"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_circuit_id(self):
        circuits = Circuit.objects.all()[:2]
        params = {"circuit_id": [circuits[0].pk, circuits[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_provider_network(self):
        provider_networks = ProviderNetwork.objects.all()[:2]
        params = {"provider_network_id": [provider_networks[0].pk, provider_networks[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = Site.objects.all()[:2]
        params = {"site": [sites[0].pk, sites[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_has_cable(self):
        params = {"has_cable": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_connected(self):
        params = {"connected": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"connected": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 7)


class ProviderNetworkTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = ProviderNetwork.objects.all()
    filterset = ProviderNetworkFilterSet

    @classmethod
    def setUpTestData(cls):

        providers = (
            Provider(name="Provider 1", slug="provider-1"),
            Provider(name="Provider 2", slug="provider-2"),
            Provider(name="Provider 3", slug="provider-3"),
        )
        Provider.objects.bulk_create(providers)

        provider_networks = (
            ProviderNetwork(name="Provider Network 1", slug="provider-network-1", provider=providers[0]),
            ProviderNetwork(name="Provider Network 2", slug="provider-network-2", provider=providers[1]),
            ProviderNetwork(name="Provider Network 3", slug="provider-network-3", provider=providers[2]),
        )
        ProviderNetwork.objects.bulk_create(provider_networks)

    def test_provider(self):
        providers = Provider.objects.all()[:2]
        params = {"provider_id": [providers[0].pk, providers[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"provider": [providers[0].slug, providers[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
