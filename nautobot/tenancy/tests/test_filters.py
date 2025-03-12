import factory

from nautobot.core.testing import FilterTestCases

# TODO: move this to nautobot.core.management.commands.generate_test_data and update all impacted tests
from nautobot.dcim.factory import RackFactory, RackReservationFactory
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Platform
from nautobot.extras.models import Role, Status, Tag
from nautobot.tenancy.filters import TenantFilterSet, TenantGroupFilterSet
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.users.factory import UserFactory
from nautobot.virtualization.factory import (
    ClusterFactory,
    ClusterGroupFactory,
    ClusterTypeFactory,
    VirtualMachineFactory,
)


class TenantGroupTestCase(FilterTestCases.FilterTestCase):
    queryset = TenantGroup.objects.all()
    filterset = TenantGroupFilterSet
    generic_filter_tests = (
        ("description",),
        ("name",),
        ("tenants", "tenants__id"),
        ("tenants", "tenants__name"),
    )

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


class TenantTestCase(FilterTestCases.FilterTestCase):
    queryset = Tenant.objects.all()
    filterset = TenantFilterSet
    generic_filter_tests = (
        ("circuits", "circuits__id"),
        ("clusters", "clusters__id"),
        ("clusters", "clusters__name"),
        ("comments",),
        ("description",),
        ("devices", "devices__id"),
        ("devices", "devices__name"),
        ("ip_addresses", "ip_addresses__id"),
        ("name",),
        ("prefixes", "prefixes__id"),
        ("rack_reservations", "rack_reservations__id"),
        ("racks", "racks__id"),
        ("route_targets", "route_targets__id"),
        ("route_targets", "route_targets__name"),
        ("virtual_machines", "virtual_machines__id"),
        ("virtual_machines", "virtual_machines__name"),
        ("vlans", "vlans__id"),
        ("vrfs", "vrfs__id"),
    )

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

    def test_locations(self):
        params = {"locations": [self.locations[0].pk, self.locations[1].name]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(locations__in=[self.locations[0], self.locations[1]]).distinct(),
        )

    def test_prefixes_by_string(self):
        """Test filtering by prefix strings as an alternative to pk."""
        prefix = self.queryset.filter(prefixes__isnull=False).first().prefixes.first()
        params = {"prefixes": [prefix.prefix]}
        self.assertQuerysetEqualAndNotEmpty(
            self.filterset(params, self.queryset).qs,
            self.queryset.filter(prefixes__network=prefix.network, prefixes__prefix_length=prefix.prefix_length),
            ordered=False,
        )
