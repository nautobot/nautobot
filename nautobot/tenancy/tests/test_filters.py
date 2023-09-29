import factory

from nautobot.circuits.models import Circuit
from nautobot.core.testing import FilterTestCases
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Platform, Rack, RackReservation
from nautobot.extras.models import Role, Status, Tag
from nautobot.ipam.models import IPAddress, Prefix, RouteTarget, VLAN, VRF
from nautobot.tenancy.filters import TenantGroupFilterSet, TenantFilterSet
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.virtualization.models import Cluster, VirtualMachine

# TODO: move this to nautobot.core.management.commands.generate_test_data and update all impacted tests
from nautobot.dcim.factory import RackFactory, RackReservationFactory
from nautobot.users.factory import UserFactory
from nautobot.virtualization.factory import (
    ClusterFactory,
    ClusterGroupFactory,
    ClusterTypeFactory,
    VirtualMachineFactory,
)


class TenantGroupTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = TenantGroup.objects.all()
    filterset = TenantGroupFilterSet

    def test_description(self):
        params = {
            "description": TenantGroup.objects.exclude(description__exact="").values_list("description", flat=True)[:2]
        }
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_parent(self):
        parent_groups = TenantGroup.objects.filter(children__isnull=False)
        params = {"parent": [parent_groups[0].pk, parent_groups[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(parent__in=[parent_groups[0], parent_groups[1]]),
        )
        params = {"parent": [parent_groups[0].name, parent_groups[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(parent__in=[parent_groups[0], parent_groups[1]]),
        )

    def test_children(self):
        """Test the `children` filter."""
        child_groups = TenantGroup.objects.filter(parent__isnull=False)
        params = {"children": [child_groups[0].pk, child_groups[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(children__in=[child_groups[0], child_groups[1]]).distinct(),
        )

    def test_has_children(self):
        """Test the `has_children` filter."""
        params = {"has_children": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(children__isnull=False).distinct(),
        )
        params = {"has_children": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(children__isnull=True).distinct(),
        )

    def test_tenants(self):
        """Test the `tenants` filter."""
        tenants = Tenant.objects.filter(tenant_group__isnull=False)
        params = {"tenants": [tenants[0].pk, tenants[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(tenants__in=[tenants[0], tenants[1]]).distinct(),
        )

    def test_has_tenants(self):
        """Test the `has_tenants` filter."""
        params = {"has_tenants": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(tenants__isnull=False).distinct(),
        )
        params = {"has_tenants": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            TenantGroup.objects.filter(tenants__isnull=True).distinct(),
        )


class TenantTestCase(FilterTestCases.NameOnlyFilterTestCase):
    queryset = Tenant.objects.all()
    filterset = TenantFilterSet

    @classmethod
    def setUpTestData(cls):
        location_type = LocationType.objects.create(name="Root Type")
        location_status = Status.objects.get_for_model(Location).first()
        cls.locations = (
            Location.objects.create(
                name="Root 1", location_type=location_type, status=location_status, tenant=cls.queryset[0]
            ),
            Location.objects.create(
                name="Root 2", location_type=location_type, status=location_status, tenant=cls.queryset[1]
            ),
        )

        # TODO: move this to nautobot.core.management.commands.generate_test_data and update all impacted tests
        factory.random.reseed_random("Nautobot")
        UserFactory.create_batch(10)
        RackFactory.create_batch(10)
        RackReservationFactory.create_batch(10)
        ClusterTypeFactory.create_batch(10)
        ClusterGroupFactory.create_batch(10)
        ClusterFactory.create_batch(10)
        VirtualMachineFactory.create_batch(10)

        # We don't have a DeviceFactory yet
        device_status = Status.objects.get_for_model(Device).first()
        cls.devices = (
            Device.objects.create(
                name="Device 1",
                device_type=DeviceType.objects.first(),
                role=Role.objects.get_for_model(Device).first(),
                platform=Platform.objects.first(),
                location=cls.locations[0],
                status=device_status,
                tenant=Tenant.objects.first(),
            ),
            Device.objects.create(
                name="Device 2",
                device_type=DeviceType.objects.first(),
                role=Role.objects.get_for_model(Device).first(),
                platform=Platform.objects.first(),
                location=cls.locations[0],
                status=device_status,
                tenant=Tenant.objects.last(),
            ),
        )

        tenant = Tenant.objects.first()
        tenant.tags.set(Tag.objects.all()[:2])

    def test_description(self):
        params = {
            "description": Tenant.objects.exclude(description__exact="").values_list("description", flat=True)[:2]
        }
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_comments(self):
        params = {"comments": Tenant.objects.exclude(comments__exact="").values_list("comments", flat=True)[:2]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_circuits(self):
        """Test the `circuits` filter."""
        circuits = list(Circuit.objects.filter(tenant__isnull=False))[:2]
        params = {"circuits": [circuits[0].pk, circuits[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(circuits__in=circuits).distinct(),
        )

    def test_has_circuits(self):
        """Test the `has_circuits` filter."""
        params = {"has_circuits": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(circuits__isnull=False).distinct(),
        )
        params = {"has_circuits": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(circuits__isnull=True).distinct(),
        )

    def test_clusters(self):
        """Test the `clusters` filter."""
        clusters = list(Cluster.objects.filter(tenant__isnull=False))[:2]
        params = {"clusters": [clusters[0].pk, clusters[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(clusters__in=clusters).distinct(),
        )

    def test_has_clusters(self):
        """Test the `has_clusters` filter."""
        params = {"has_clusters": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(clusters__isnull=False).distinct(),
        )
        params = {"has_clusters": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(clusters__isnull=True).distinct(),
        )

    def test_devices(self):
        """Test the `devices` filter."""
        params = {"devices": [self.devices[0].pk, self.devices[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(devices__in=self.devices).distinct(),
        )

    def test_has_devices(self):
        """Test the `has_devices` filter."""
        params = {"has_devices": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(devices__isnull=False).distinct(),
        )
        params = {"has_devices": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(devices__isnull=True).distinct(),
        )

    def test_tenant_group(self):
        groups = list(TenantGroup.objects.filter(tenants__isnull=False))[:2]
        groups_including_children = []
        for group in groups:
            groups_including_children += group.descendants(include_self=True)
        params = {"tenant_group": [groups[0].pk, groups[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(tenant_group__in=groups_including_children),
        )
        params = {"tenant_group": [groups[0].name, groups[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(tenant_group__in=groups_including_children),
        )

    def test_ip_addresses(self):
        """Test the `ip_addresses` filter."""
        ip_addresses = list(IPAddress.objects.filter(tenant__isnull=False))[:2]
        params = {"ip_addresses": [ip_addresses[0].pk, ip_addresses[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(ip_addresses__in=ip_addresses).distinct(),
        )

    def test_has_ip_addresses(self):
        """Test the `has_ip_addresses` filter."""
        params = {"has_ip_addresses": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(ip_addresses__isnull=False).distinct(),
        )
        params = {"has_ip_addresses": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(ip_addresses__isnull=True).distinct(),
        )

    def test_locations(self):
        params = {"locations": [self.locations[0].pk, self.locations[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(locations__in=[self.locations[0], self.locations[1]]).distinct(),
        )

    def test_has_locations(self):
        params = {"has_locations": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(locations__isnull=False).distinct(),
        )
        params = {"has_locations": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(locations__isnull=True).distinct(),
        )

    def test_prefixes(self):
        """Test the `prefixes` filter."""
        prefixes = list(Prefix.objects.filter(tenant__isnull=False))[:2]
        params = {"prefixes": [prefixes[0].pk, prefixes[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(prefixes__in=prefixes).distinct(),
        )

    def test_has_prefixes(self):
        """Test the `has_prefixes` filter."""
        params = {"has_prefixes": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(prefixes__isnull=False).distinct(),
        )
        params = {"has_prefixes": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(prefixes__isnull=True).distinct(),
        )

    def test_rack_reservations(self):
        """Test the `rack_reservations` filter."""
        rack_reservations = list(RackReservation.objects.filter(tenant__isnull=False))[:2]
        params = {"rack_reservations": [rack_reservations[0].pk, rack_reservations[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(rack_reservations__in=rack_reservations).distinct(),
        )

    def test_has_rack_reservations(self):
        """Test the `has_rack_reservations` filter."""
        params = {"has_rack_reservations": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(rack_reservations__isnull=False).distinct(),
        )
        params = {"has_rack_reservations": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(rack_reservations__isnull=True).distinct(),
        )

    def test_racks(self):
        """Test the `racks` filter."""
        racks = list(Rack.objects.filter(tenant__isnull=False))[:2]
        params = {"racks": [racks[0].pk, racks[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(racks__in=racks).distinct(),
        )

    def test_has_racks(self):
        """Test the `has_racks` filter."""
        params = {"has_racks": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(racks__isnull=False).distinct(),
        )
        params = {"has_racks": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(racks__isnull=True).distinct(),
        )

    def test_route_targets(self):
        """Test the `route_targets` filter."""
        route_targets = list(RouteTarget.objects.filter(tenant__isnull=False))[:2]
        params = {"route_targets": [route_targets[0].pk, route_targets[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(route_targets__in=route_targets).distinct(),
        )

    def test_has_route_targets(self):
        """Test the `has_route_targets` filter."""
        params = {"has_route_targets": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(route_targets__isnull=False).distinct(),
        )
        params = {"has_route_targets": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(route_targets__isnull=True).distinct(),
        )

    def test_virtual_machines(self):
        """Test the `virtual_machines` filter."""
        virtual_machines = list(VirtualMachine.objects.filter(tenant__isnull=False))[:2]
        params = {"virtual_machines": [virtual_machines[0].pk, virtual_machines[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(virtual_machines__in=virtual_machines).distinct(),
        )

    def test_has_virtual_machines(self):
        """Test the `has_virtual_machines` filter."""
        params = {"has_virtual_machines": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(virtual_machines__isnull=False).distinct(),
        )
        params = {"has_virtual_machines": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(virtual_machines__isnull=True).distinct(),
        )

    def test_vlans(self):
        """Test the `vlans` filter."""
        vlans = list(VLAN.objects.filter(tenant__isnull=False))[:2]
        params = {"vlans": [vlans[0].pk, vlans[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vlans__in=vlans).distinct(),
        )

    def test_has_vlans(self):
        """Test the `has_vlans` filter."""
        params = {"has_vlans": True}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vlans__isnull=False).distinct(),
        )
        params = {"has_vlans": False}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vlans__isnull=True).distinct(),
        )

    def test_vrfs(self):
        """Test the `vrfs` filter."""
        vrfs = list(VRF.objects.filter(tenant__isnull=False))[:2]
        params = {"vrfs": [vrfs[0].pk, vrfs[1].pk]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(vrfs__in=vrfs).distinct(),
        )

    def test_search(self):
        params = {"q": self.queryset.first().name}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset(params, self.queryset).qs.first(), self.queryset.first())
