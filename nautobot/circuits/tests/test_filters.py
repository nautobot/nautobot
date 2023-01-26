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
from nautobot.core.testing import FilterTestCases
from nautobot.dcim.models import Cable, Device, DeviceType, Interface, Location, Region, Site
from nautobot.extras.models import Role, Status


class ProviderTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = Provider.objects.all()
    filterset = ProviderFilterSet

    generic_filter_tests = (
        ["account"],
        ["admin_contact"],
        ["asn"],
        ["circuits", "circuits__id"],
        ["circuits", "circuits__cid"],
        ["comments"],
        ["noc_contact"],
        ["portal_url"],
        ["provider_networks", "provider_networks__id"],
        ["provider_networks", "provider_networks__slug"],
        ["site", "circuits__circuit_terminations__site__id"],
        ["site", "circuits__circuit_terminations__site__slug"],
    )

    @classmethod
    def setUpTestData(cls):

        providers = Provider.objects.all()[:2]
        circuit_types = CircuitType.objects.all()[:2]
        cls.regions = Region.objects.filter(sites__isnull=False, children__isnull=True, parent__isnull=True)[:2]
        cls.locations = Location.objects.filter(children__isnull=True)[:2]

        sites = (
            Site.objects.filter(region=cls.regions[0]).first(),
            Site.objects.filter(region=cls.regions[1]).first(),
        )

        circuits = (
            Circuit.objects.create(provider=providers[0], circuit_type=circuit_types[0], cid="Test Circuit 1"),
            Circuit.objects.create(provider=providers[1], circuit_type=circuit_types[1], cid="Test Circuit 1"),
        )

        CircuitTermination.objects.create(circuit=circuits[0], site=sites[0], term_side="A")
        CircuitTermination.objects.create(circuit=circuits[1], site=sites[0], term_side="A")
        CircuitTermination.objects.create(
            circuit=circuits[0], site=cls.locations[0].base_site, location=cls.locations[0], term_side="Z"
        )
        CircuitTermination.objects.create(
            circuit=circuits[1], site=cls.locations[1].base_site, location=cls.locations[1], term_side="Z"
        )

    def test_region(self):
        expected = self.queryset.filter(
            circuits__circuit_terminations__site__region__in=[self.regions[0].pk, self.regions[1].pk]
        )
        params = {"region": [self.regions[0].pk, self.regions[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)
        params = {"region": [self.regions[0].slug, self.regions[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)

    def test_location(self):
        expected = self.queryset.filter(
            circuits__circuit_terminations__location__in=[self.locations[0].pk, self.locations[1].pk]
        )
        params = {"location": [self.locations[0].pk, self.locations[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)
        params = {"location": [self.locations[0].slug, self.locations[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)


class CircuitTypeTestCase(FilterTestCases.NameSlugFilterTestCase):
    queryset = CircuitType.objects.all()
    filterset = CircuitTypeFilterSet

    generic_filter_tests = (
        ["description"],
        ["name"],
        ["slug"],
    )


class CircuitTestCase(FilterTestCases.FilterTestCase, FilterTestCases.TenancyFilterTestCaseMixin):
    queryset = Circuit.objects.all()
    filterset = CircuitFilterSet
    tenancy_related_name = "circuits"

    generic_filter_tests = (
        ["cid"],
        ["comments"],
        ["description"],
        ["install_date"],
        ["commit_rate"],
        ["provider", "provider__id"],
        ["provider", "provider__slug"],
        ["provider_network", "circuit_terminations__provider_network__id"],
        ["provider_network", "circuit_terminations__provider_network__slug"],
        ["circuit_type", "circuit_type__id"],
        ["circuit_type", "circuit_type__slug"],
        ["status", "status__slug"],
        ["site", "circuit_terminations__site__id"],
        ["site", "circuit_terminations__site__slug"],
        ["circuit_termination_a"],
        ["circuit_termination_z"],
        ["circuit_terminations"],
    )

    def test_location(self):
        locations = Location.objects.filter(children__isnull=True, site__isnull=False)[:2]
        factory.CircuitTerminationFactory.create(
            has_location=True, location=locations[0], has_site=True, site=locations[0].site
        )
        factory.CircuitTerminationFactory.create(
            has_location=True, location=locations[1], has_site=True, site=locations[1].site
        )
        expected = self.queryset.filter(circuit_terminations__location__in=[locations[0].pk, locations[1].pk])
        params = {"location": [locations[0].pk, locations[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)
        params = {"location": [locations[0].slug, locations[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)

    def test_region(self):
        regions = Region.objects.filter(sites__isnull=False, children__isnull=True)[:2]
        factory.CircuitTerminationFactory.create(has_site=True, site=regions[0].sites.first())
        factory.CircuitTerminationFactory.create(has_site=True, site=regions[1].sites.first())
        expected = self.queryset.filter(circuit_terminations__site__region__in=[regions[0].pk, regions[1].pk])
        params = {"region": [regions[0].pk, regions[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertQuerysetEqualAndNotEmpty(self.filterset(params, self.queryset).qs, expected)

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
        ["description"],
        ["port_speed"],
        ["pp_info"],
        ["provider_network", "provider_network__slug"],
        ["provider_network", "provider_network__id"],
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

    generic_filter_tests = (
        ["circuit_terminations", "circuit_terminations__id"],
        ["comments"],
        ["description"],
        ["name"],
        ["provider", "provider__id"],
        ["provider", "provider__slug"],
        ["slug"],
    )
