import datetime

from netaddr import IPNetwork

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.extras.models import Status
from nautobot.ipam.choices import *
from nautobot.ipam.models import (
    Aggregate,
    IPAddress,
    Prefix,
    RIR,
    Role,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.tenancy.models import Tenant
from nautobot.utilities.testing import ViewTestCases


class VRFTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VRF

    @classmethod
    def setUpTestData(cls):

        tenants = (
            Tenant.objects.create(name="Tenant A", slug="tenant-a"),
            Tenant.objects.create(name="Tenant B", slug="tenant-b"),
        )

        VRF.objects.create(name="VRF 1", rd="65000:1"),
        VRF.objects.create(name="VRF 2", rd="65000:2"),
        VRF.objects.create(name="VRF 3", rd="65000:3"),

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "name": "VRF X",
            "rd": "65000:999",
            "tenant": tenants[0].pk,
            "enforce_unique": True,
            "description": "A new VRF",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name",
            "VRF 4",
            "VRF 5",
            "VRF 6",
        )

        cls.bulk_edit_data = {
            "tenant": tenants[1].pk,
            "enforce_unique": False,
            "description": "New description",
        }


class RouteTargetTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = RouteTarget

    @classmethod
    def setUpTestData(cls):

        tenants = (
            Tenant.objects.create(name="Tenant A", slug="tenant-a"),
            Tenant.objects.create(name="Tenant B", slug="tenant-b"),
        )

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        RouteTarget.objects.create(name="65000:1001", tenant=tenants[0]),
        RouteTarget.objects.create(name="65000:1002", tenant=tenants[1]),
        RouteTarget.objects.create(name="65000:1003"),

        cls.form_data = {
            "name": "65000:100",
            "description": "A new route target",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name,tenant,description",
            "65000:1004,Tenant A,Foo",
            "65000:1005,Tenant B,Bar",
            "65000:1006,,No tenant",
        )

        cls.bulk_edit_data = {
            "tenant": tenants[1].pk,
            "description": "New description",
        }


class RIRTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = RIR

    @classmethod
    def setUpTestData(cls):

        RIR.objects.bulk_create(
            [
                RIR(name="RIR 1", slug="rir-1"),
                RIR(name="RIR 2", slug="rir-2"),
                RIR(name="RIR 3", slug="rir-3"),
            ]
        )

        cls.form_data = {
            "name": "RIR X",
            "slug": "rir-x",
            "is_private": True,
            "description": "A new RIR",
        }

        cls.csv_data = (
            "name,slug,description",
            "RIR 4,rir-4,Fourth RIR",
            "RIR 5,rir-5,Fifth RIR",
            "RIR 6,rir-6,Sixth RIR",
        )


class AggregateTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Aggregate

    @classmethod
    def setUpTestData(cls):

        rirs = (
            RIR.objects.create(name="RIR 1", slug="rir-1"),
            RIR.objects.create(name="RIR 2", slug="rir-2"),
        )

        Aggregate.objects.create(prefix=IPNetwork("10.1.0.0/16"), rir=rirs[0]),
        Aggregate.objects.create(prefix=IPNetwork("10.2.0.0/16"), rir=rirs[0]),
        Aggregate.objects.create(prefix=IPNetwork("10.3.0.0/16"), rir=rirs[0]),

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "prefix": IPNetwork("10.99.0.0/16"),
            "rir": rirs[1].pk,
            "date_added": datetime.date(2020, 1, 1),
            "description": "A new aggregate",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "prefix,rir",
            "10.4.0.0/16,RIR 1",
            "10.5.0.0/16,RIR 1",
            "10.6.0.0/16,RIR 1",
        )

        cls.bulk_edit_data = {
            "rir": rirs[1].pk,
            "date_added": datetime.date(2020, 1, 1),
            "description": "New description",
        }


class RoleTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Role

    @classmethod
    def setUpTestData(cls):

        Role.objects.bulk_create(
            [
                Role(name="Role 1", slug="role-1"),
                Role(name="Role 2", slug="role-2"),
                Role(name="Role 3", slug="role-3"),
            ]
        )

        cls.form_data = {
            "name": "Role X",
            "slug": "role-x",
            "weight": 200,
            "description": "A new role",
        }

        cls.csv_data = (
            "name,slug,weight",
            "Role 4,role-4,1000",
            "Role 5,role-5,1000",
            "Role 6,role-6,1000",
        )


class PrefixTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Prefix

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        vrfs = (
            VRF.objects.create(name="VRF 1", rd="65000:1"),
            VRF.objects.create(name="VRF 2", rd="65000:2"),
        )

        roles = (
            Role.objects.create(name="Role 1", slug="role-1"),
            Role.objects.create(name="Role 2", slug="role-2"),
        )

        statuses = Status.objects.get_for_model(Prefix)
        status_reserved = statuses.get(slug="reserved")

        Prefix.objects.create(
            prefix=IPNetwork("10.1.0.0/16"),
            vrf=vrfs[0],
            site=sites[0],
            role=roles[0],
            status=statuses[0],
        )
        Prefix.objects.create(
            prefix=IPNetwork("10.2.0.0/16"),
            vrf=vrfs[0],
            site=sites[0],
            role=roles[0],
            status=statuses[0],
        )
        Prefix.objects.create(
            prefix=IPNetwork("10.3.0.0/16"),
            vrf=vrfs[0],
            site=sites[0],
            role=roles[0],
            status=statuses[0],
        )

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "prefix": IPNetwork("192.0.2.0/24"),
            "site": sites[1].pk,
            "vrf": vrfs[1].pk,
            "tenant": None,
            "vlan": None,
            "status": status_reserved.pk,
            "role": roles[1].pk,
            "is_pool": True,
            "description": "A new prefix",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "vrf,prefix,status",
            "VRF 1,10.4.0.0/16,active",
            "VRF 1,10.5.0.0/16,active",
            "VRF 1,10.6.0.0/16,active",
        )

        cls.bulk_edit_data = {
            "site": sites[1].pk,
            "vrf": vrfs[1].pk,
            "tenant": None,
            "status": status_reserved.pk,
            "role": roles[1].pk,
            "is_pool": False,
            "description": "New description",
        }


class IPAddressTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = IPAddress

    @classmethod
    def setUpTestData(cls):

        vrfs = (
            VRF.objects.create(name="VRF 1", rd="65000:1"),
            VRF.objects.create(name="VRF 2", rd="65000:2"),
        )

        statuses = Status.objects.get_for_model(IPAddress)
        status_reserved = statuses.get(slug="reserved")

        IPAddress.objects.create(address=IPNetwork("192.0.2.1/24"), vrf=vrfs[0], status=statuses[0])
        IPAddress.objects.create(address=IPNetwork("192.0.2.2/24"), vrf=vrfs[0], status=statuses[0])
        IPAddress.objects.create(address=IPNetwork("192.0.2.3/24"), vrf=vrfs[0], status=statuses[0])

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "vrf": vrfs[1].pk,
            "address": IPNetwork("192.0.2.99/24"),
            "tenant": None,
            "status": status_reserved.pk,
            "role": IPAddressRoleChoices.ROLE_ANYCAST,
            "nat_inside": None,
            "dns_name": "example",
            "description": "A new IP address",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "vrf,address,status",
            "VRF 1,192.0.2.4/24,active",
            "VRF 1,192.0.2.5/24,active",
            "VRF 1,192.0.2.6/24,active",
        )

        cls.bulk_edit_data = {
            "vrf": vrfs[1].pk,
            "tenant": None,
            "status": status_reserved.pk,
            "role": IPAddressRoleChoices.ROLE_ANYCAST,
            "dns_name": "example",
            "description": "New description",
        }


class VLANGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = VLANGroup

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.create(name="Site 1", slug="site-1")

        VLANGroup.objects.bulk_create(
            [
                VLANGroup(name="VLAN Group 1", slug="vlan-group-1", site=site),
                VLANGroup(name="VLAN Group 2", slug="vlan-group-2", site=site),
                VLANGroup(name="VLAN Group 3", slug="vlan-group-3", site=site),
            ]
        )

        cls.form_data = {
            "name": "VLAN Group X",
            "slug": "vlan-group-x",
            "site": site.pk,
            "description": "A new VLAN group",
        }

        cls.csv_data = (
            "name,slug,description",
            "VLAN Group 4,vlan-group-4,Fourth VLAN group",
            "VLAN Group 5,vlan-group-5,Fifth VLAN group",
            "VLAN Group 6,vlan-group-6,Sixth VLAN group",
        )


class VLANTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VLAN

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        vlangroups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=sites[0]),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=sites[1]),
        )

        roles = (
            Role.objects.create(name="Role 1", slug="role-1"),
            Role.objects.create(name="Role 2", slug="role-2"),
        )

        statuses = Status.objects.get_for_model(VLAN)
        status_reserved = statuses.get(slug="reserved")

        VLAN.objects.create(
            group=vlangroups[0],
            vid=101,
            name="VLAN101",
            site=sites[0],
            role=roles[0],
            status=statuses[0],
        )
        VLAN.objects.create(
            group=vlangroups[0],
            vid=102,
            name="VLAN102",
            site=sites[0],
            role=roles[0],
            status=statuses[0],
        )
        VLAN.objects.create(
            group=vlangroups[0],
            vid=103,
            name="VLAN103",
            site=sites[0],
            role=roles[0],
            status=statuses[0],
        )

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "site": sites[1].pk,
            "group": vlangroups[1].pk,
            "vid": 999,
            "name": "VLAN999",
            "tenant": None,
            "status": status_reserved.pk,
            "role": roles[1].pk,
            "description": "A new VLAN",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "vid,name,status",
            "104,VLAN104,active",
            "105,VLAN105,active",
            "106,VLAN106,active",
        )

        cls.bulk_edit_data = {
            "site": sites[1].pk,
            "group": vlangroups[1].pk,
            "tenant": None,
            "status": status_reserved.pk,
            "role": roles[1].pk,
            "description": "New description",
        }


# TODO: Update base class to PrimaryObjectViewTestCase
# Blocked by absence of standard creation view
class ServiceTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
    ViewTestCases.BulkEditObjectsViewTestCase,
    ViewTestCases.BulkDeleteObjectsViewTestCase,
):
    model = Service

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.create(name="Site 1", slug="site-1")
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        device = Device.objects.create(name="Device 1", site=site, device_type=devicetype, device_role=devicerole)

        Service.objects.bulk_create(
            [
                Service(
                    device=device,
                    name="Service 1",
                    protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                    ports=[101],
                ),
                Service(
                    device=device,
                    name="Service 2",
                    protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                    ports=[102],
                ),
                Service(
                    device=device,
                    name="Service 3",
                    protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                    ports=[103],
                ),
            ]
        )

        tags = cls.create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "device": device.pk,
            "virtual_machine": None,
            "name": "Service X",
            "protocol": ServiceProtocolChoices.PROTOCOL_TCP,
            "ports": "104,105",
            "ipaddresses": [],
            "description": "A new service",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "device,name,protocol,ports,description",
            "Device 1,Service 1,tcp,1,First service",
            "Device 1,Service 2,tcp,2,Second service",
            "Device 1,Service 3,udp,3,Third service",
        )

        cls.bulk_edit_data = {
            "protocol": ServiceProtocolChoices.PROTOCOL_UDP,
            "ports": "106,107",
            "description": "New description",
        }
