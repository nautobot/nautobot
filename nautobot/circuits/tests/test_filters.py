from django.test import TestCase

from nautobot.circuits.choices import *
from nautobot.circuits.filters import *
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider
from nautobot.dcim.models import Cable, Device, DeviceRole, DeviceType, Interface, Manufacturer, Region, Site
from nautobot.extras.models import Status
from nautobot.tenancy.models import Tenant, TenantGroup


class ProviderTestCase(TestCase):
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
        )

        regions = (
            Region.objects.create(name="Test Region 1", slug="test-region-1"),
            Region.objects.create(name="Test Region 2", slug="test-region-2"),
        )

        sites = (
            Site.objects.create(name="Test Site 1", slug="test-site-1", region=regions[0]),
            Site.objects.create(name="Test Site 2", slug="test-site-2", region=regions[1]),
        )

        circuit_types = (
            CircuitType.objects.create(name="Test Circuit Type 1", slug="test-circuit-type-1"),
            CircuitType.objects.create(name="Test Circuit Type 2", slug="test-circuit-type-2"),
        )

        circuits = (
            Circuit.objects.create(provider=providers[0], type=circuit_types[0], cid="Test Circuit 1"),
            Circuit.objects.create(provider=providers[1], type=circuit_types[1], cid="Test Circuit 1"),
        )

        CircuitTermination.objects.create(circuit=circuits[0], site=sites[0], term_side="A")
        CircuitTermination.objects.create(circuit=circuits[1], site=sites[0], term_side="A")

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_name(self):
        params = {"name": ["Provider 1", "Provider 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_slug(self):
        params = {"slug": ["provider-1", "provider-2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_asn(self):
        params = {"asn": ["65001", "65002"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_account(self):
        params = {"account": ["1234", "2345"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = Site.objects.all()[:2]
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_region(self):
        regions = Region.objects.all()[:2]
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)


class CircuitTypeTestCase(TestCase):
    queryset = CircuitType.objects.all()
    filterset = CircuitTypeFilterSet

    @classmethod
    def setUpTestData(cls):

        CircuitType.objects.create(name="Circuit Type 1", slug="circuit-type-1")
        CircuitType.objects.create(name="Circuit Type 2", slug="circuit-type-2")
        CircuitType.objects.create(name="Circuit Type 3", slug="circuit-type-3")

    def test_id(self):
        params = {"id": [self.queryset.first().pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_name(self):
        params = {"name": ["Circuit Type 1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_slug(self):
        params = {"slug": ["circuit-type-1"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)


class CircuitTestCase(TestCase):
    queryset = Circuit.objects.all()
    filterset = CircuitFilterSet

    @classmethod
    def setUpTestData(cls):

        regions = (
            Region.objects.create(name="Test Region 1", slug="test-region-1"),
            Region.objects.create(name="Test Region 2", slug="test-region-2"),
            Region.objects.create(name="Test Region 3", slug="test-region-3"),
        )

        sites = (
            Site.objects.create(name="Test Site 1", slug="test-site-1", region=regions[0]),
            Site.objects.create(name="Test Site 2", slug="test-site-2", region=regions[1]),
            Site.objects.create(name="Test Site 3", slug="test-site-3", region=regions[2]),
        )

        tenant_groups = (
            TenantGroup.objects.create(name="Tenant group 1", slug="tenant-group-1"),
            TenantGroup.objects.create(name="Tenant group 2", slug="tenant-group-2"),
            TenantGroup.objects.create(name="Tenant group 3", slug="tenant-group-3"),
        )

        tenants = (
            Tenant.objects.create(name="Tenant 1", slug="tenant-1", group=tenant_groups[0]),
            Tenant.objects.create(name="Tenant 2", slug="tenant-2", group=tenant_groups[1]),
            Tenant.objects.create(name="Tenant 3", slug="tenant-3", group=tenant_groups[2]),
        )

        circuit_types = (
            CircuitType.objects.create(name="Test Circuit Type 1", slug="test-circuit-type-1"),
            CircuitType.objects.create(name="Test Circuit Type 2", slug="test-circuit-type-2"),
        )

        providers = (
            Provider.objects.create(name="Provider 1", slug="provider-1"),
            Provider.objects.create(name="Provider 2", slug="provider-2"),
        )

        circ_statuses = Status.objects.get_for_model(Circuit)
        circ_status_map = {s.slug: s for s in circ_statuses.all()}

        circuits = (
            Circuit.objects.create(
                provider=providers[0],
                tenant=tenants[0],
                type=circuit_types[0],
                cid="Test Circuit 1",
                install_date="2020-01-01",
                commit_rate=1000,
                status=circ_status_map["active"],
            ),
            Circuit.objects.create(
                provider=providers[0],
                tenant=tenants[0],
                type=circuit_types[0],
                cid="Test Circuit 2",
                install_date="2020-01-02",
                commit_rate=2000,
                status=circ_status_map["active"],
            ),
            Circuit.objects.create(
                provider=providers[0],
                tenant=tenants[1],
                type=circuit_types[0],
                cid="Test Circuit 3",
                install_date="2020-01-03",
                commit_rate=3000,
                status=circ_status_map["planned"],
            ),
            Circuit.objects.create(
                provider=providers[1],
                tenant=tenants[1],
                type=circuit_types[1],
                cid="Test Circuit 4",
                install_date="2020-01-04",
                commit_rate=4000,
                status=circ_status_map["planned"],
            ),
            Circuit.objects.create(
                provider=providers[1],
                tenant=tenants[2],
                type=circuit_types[1],
                cid="Test Circuit 5",
                install_date="2020-01-05",
                commit_rate=5000,
                status=circ_status_map["offline"],
            ),
            Circuit.objects.create(
                provider=providers[1],
                tenant=tenants[2],
                type=circuit_types[1],
                cid="Test Circuit 6",
                install_date="2020-01-06",
                commit_rate=6000,
                status=circ_status_map["offline"],
            ),
        )

        CircuitTermination.objects.create(circuit=circuits[0], site=sites[0], term_side="A")
        CircuitTermination.objects.create(circuit=circuits[1], site=sites[1], term_side="A")
        CircuitTermination.objects.create(circuit=circuits[2], site=sites[2], term_side="A")

    def test_id(self):
        params = {"id": self.queryset.values_list("pk", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_cid(self):
        params = {"cid": ["Test Circuit 1", "Test Circuit 2"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_install_date(self):
        params = {"install_date": ["2020-01-01", "2020-01-02"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_commit_rate(self):
        params = {"commit_rate": ["1000", "2000"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_provider(self):
        provider = Provider.objects.first()
        params = {"provider_id": [provider.pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {"provider": [provider.slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_type(self):
        circuit_type = CircuitType.objects.first()
        params = {"type_id": [circuit_type.pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {"type": [circuit_type.slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_status(self):
        params = {"status": ["active", "planned"]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_region(self):
        regions = Region.objects.all()[:2]
        params = {"region_id": [regions[0].pk, regions[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"region": [regions[0].slug, regions[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_site(self):
        sites = Site.objects.all()[:2]
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_tenant(self):
        tenants = Tenant.objects.all()[:2]
        params = {"tenant_id": [tenants[0].pk, tenants[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"tenant": [tenants[0].slug, tenants[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_tenant_group(self):
        tenant_groups = TenantGroup.objects.all()[:2]
        params = {"tenant_group_id": [tenant_groups[0].pk, tenant_groups[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"tenant_group": [tenant_groups[0].slug, tenant_groups[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)


class CircuitTerminationTestCase(TestCase):
    queryset = CircuitTermination.objects.all()
    filterset = CircuitTerminationFilterSet

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site.objects.create(name="Test Site 1", slug="test-site-1"),
            Site.objects.create(name="Test Site 2", slug="test-site-2"),
            Site.objects.create(name="Test Site 3", slug="test-site-3"),
        )
        manufacturer = Manufacturer.objects.create(name="Test Manufacturer 1", slug="test-manufacturer-1")
        devicetype = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 1",
            slug="test-device-type-1",
        )
        devicerole = DeviceRole.objects.create(name="Test Device Role 1", slug="test-device-role-1", color="ff0000")
        device_status = Status.objects.get_for_model(Device).get(slug="active")
        device1 = Device.objects.create(
            device_type=devicetype,
            device_role=devicerole,
            name="TestDevice1",
            site=sites[0],
            status=device_status,
        )
        device2 = Device.objects.create(
            device_type=devicetype,
            device_role=devicerole,
            name="TestDevice2",
            site=sites[1],
            status=device_status,
        )
        interface1 = Interface.objects.create(device=device1, name="eth0")
        interface2 = Interface.objects.create(device=device2, name="eth0")

        circuit_types = (CircuitType.objects.create(name="Test Circuit Type 1", slug="test-circuit-type-1"),)

        providers = (Provider.objects.create(name="Provider 1", slug="provider-1"),)

        circuits = (
            Circuit.objects.create(provider=providers[0], type=circuit_types[0], cid="Test Circuit 1"),
            Circuit.objects.create(provider=providers[0], type=circuit_types[0], cid="Test Circuit 2"),
            Circuit.objects.create(provider=providers[0], type=circuit_types[0], cid="Test Circuit 3"),
        )

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
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

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

    def test_site(self):
        sites = Site.objects.all()[:2]
        params = {"site_id": [sites[0].pk, sites[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
        params = {"site": [sites[0].slug, sites[1].slug]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_cabled(self):
        params = {"cabled": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_connected(self):
        params = {"connected": True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {"connected": False}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)
