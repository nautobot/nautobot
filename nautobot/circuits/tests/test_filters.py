from django.db.models import Q

from nautobot.circuits import factory
from nautobot.circuits.choices import CircuitTerminationSideChoices
from nautobot.circuits.filters import (
    CircuitFilterSet,
    CircuitTerminationFilterSet,
    CircuitTypeFilterSet,
    ProviderFilterSet,
    ProviderNetworkFilterSet,
)
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.dcim.models import Cable, Device, DeviceType, Interface, Region, Site
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
        ["comments"],
        ["description"],
        ["install_date"],
        ["commit_rate"],
        ["provider_id", "provider__id"],
        ["provider", "provider__slug"],
        ["provider_network", "terminations__provider_network__slug"],
        ["provider_network", "terminations__provider_network__id"],
        ["provider_network_id", "terminations__provider_network"],
        ["type_id", "type__id"],
        ["type", "type__slug"],
        ["status", "status__slug"],
        ["region_id", "terminations__site__region__id"],
        ["region", "terminations__site__region__slug"],
        ["region", "terminations__site__region__id"],
        ["site_id", "terminations__site__id"],
        ["site", "terminations__site__slug"],
        ["termination_a"],
        ["termination_z"],
        ["terminations"],
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

    def test_search(self):
        value = self.queryset.values_list("pk", flat=True)[0]
        params = {"q": value}
        self.assertEqual(self.filterset(params, self.queryset).qs.values_list("pk", flat=True)[0], value)


class CircuitTerminationTestCase(FilterTestCases.FilterTestCase):
    queryset = CircuitTermination.objects.all()
    filterset = CircuitTerminationFilterSet

    generic_filter_tests = (
        ["circuit", "circuit__cid"],
        ["circuit", "circuit__id"],
        ["circuit_id"],
        ["description"],
        ["port_speed"],
        ["pp_info"],
        ["provider_network", "provider_network__slug"],
        ["provider_network", "provider_network__id"],
        ["provider_network_id"],
        ["site", "site__id"],
        ["site", "site__slug"],
        ["upstream_speed"],
        ["xconnect_id"],
    )

    @classmethod
    def setUpTestData(cls):

        sites = Site.objects.all()
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
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

        factory.CircuitTypeFactory.create_batch(10)
        factory.ProviderFactory.create_batch(10)
        factory.CircuitFactory.create_batch(20)
        factory.CircuitTerminationFactory.create_batch(2, has_region=True, term_side="A")
        factory.CircuitTerminationFactory.create_batch(2, has_region=True, term_side="Z")
        factory.CircuitTerminationFactory.create_batch(2, has_site=False, term_side="A")
        factory.CircuitTerminationFactory.create_batch(2, has_site=False, term_side="Z")
        factory.CircuitTerminationFactory.create_batch(2, has_port_speed=True, has_upstream_speed=False)
        factory.CircuitTerminationFactory.create_batch(
            size=2,
            has_site=True,
            has_location=True,
            has_port_speed=True,
            has_upstream_speed=True,
            has_xconnect_id=True,
            has_pp_info=True,
            has_description=True,
        )

        circuit_terminations = CircuitTermination.objects.all()

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
        for choice in CircuitTerminationSideChoices.values():
            with self.subTest(f"term_side: {choice}"):
                params = {"term_side": choice}
                filterset_result = self.filterset(params, self.queryset).qs
                qs_result = self.queryset.filter(term_side=choice)
                self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)

    def test_connected(self):
        params = {"connected": True}
        filterset_result = self.filterset(params, self.queryset).qs
        qs_result = self.queryset.filter(_path__is_active=True)
        self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)
        params = {"connected": False}
        filterset_result = self.filterset(params, self.queryset).qs
        qs_result = self.queryset.filter(Q(_path__isnull=True) | Q(_path__is_active=False))
        self.assertQuerysetEqualAndNotEmpty(filterset_result, qs_result)


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
