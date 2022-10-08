import datetime

from netaddr import IPNetwork
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Location, Manufacturer, Site
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import CustomField, Status, Tag
from nautobot.ipam.choices import IPAddressRoleChoices, ServiceProtocolChoices
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
from nautobot.utilities.testing.utils import extract_page_body


class VRFTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VRF
    fixtures = ("tag",)

    @classmethod
    def setUpTestData(cls):

        tenants = (
            Tenant.objects.create(name="Tenant A", slug="tenant-a"),
            Tenant.objects.create(name="Tenant B", slug="tenant-b"),
        )

        cls.form_data = {
            "name": "VRF X",
            "rd": "65000:999",
            "tenant": tenants[0].pk,
            "enforce_unique": True,
            "description": "A new VRF",
            "tags": [t.pk for t in Tag.objects.get_for_model(VRF)],
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
    fixtures = ("tag",)

    @classmethod
    def setUpTestData(cls):

        tenants = (
            Tenant.objects.create(name="Tenant A", slug="tenant-a"),
            Tenant.objects.create(name="Tenant B", slug="tenant-b"),
        )

        cls.form_data = {
            "name": "65000:100",
            "description": "A new route target",
            "tags": [t.pk for t in Tag.objects.get_for_model(RouteTarget)],
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
        RIR.objects.create(name="RIR 8")

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
            "RIR 7,,Seventh RIR",
        )
        cls.slug_source = "name"
        cls.slug_test_object = "RIR 8"

    def get_deletable_object(self):
        """Return an RIR without any associated Aggregates."""
        return RIR.objects.get(name="RIR 8")

    def get_deletable_object_pks(self):
        """Return a list of PKs corresponding to RIRs without any associated Aggregates."""
        rirs = [
            RIR.objects.create(name="RFC N/A"),
            RIR.objects.create(name="MAGICNIC"),
            RIR.objects.create(name="NOTANIC"),
        ]
        return [rir.pk for rir in rirs]


class AggregateTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Aggregate
    fixtures = ("tag",)

    @classmethod
    def setUpTestData(cls):
        rir = RIR.objects.first()

        cls.form_data = {
            "prefix": IPNetwork("22.99.0.0/16"),
            "rir": rir.pk,
            "date_added": datetime.date(2020, 1, 1),
            "description": "A new aggregate",
            "tags": [t.pk for t in Tag.objects.get_for_model(Aggregate)],
        }

        cls.csv_data = (
            "prefix,rir",
            f"22.4.0.0/16,{rir.name}",
            f"22.5.0.0/16,{rir.name}",
            f"22.6.0.0/16,{rir.name}",
        )

        cls.bulk_edit_data = {
            "rir": RIR.objects.last().pk,
            "date_added": datetime.date(2020, 1, 1),
            "description": "New description",
        }


class RoleTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Role

    @classmethod
    def setUpTestData(cls):
        Role.objects.create(name="Role 8")

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
            "Role 7,,1000",
        )
        cls.slug_source = "name"
        cls.slug_test_object = "Role 8"


class PrefixTestCase(ViewTestCases.PrimaryObjectViewTestCase, ViewTestCases.ListObjectsViewTestCase):
    model = Prefix
    fixtures = (
        "status",
        "tag",
    )

    @classmethod
    def setUpTestData(cls):

        sites = Site.objects.all()[:2]
        vrfs = VRF.objects.all()[:2]

        roles = Role.objects.all()[:2]

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
            "tags": [t.pk for t in Tag.objects.get_for_model(Prefix)],
        }

        cls.csv_data = (
            "vrf,prefix,status",
            f"{vrfs[0].name},10.4.0.0/16,active",
            f"{vrfs[0].name},10.5.0.0/16,active",
            f"{vrfs[0].name},10.6.0.0/16,active",
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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_empty_queryset(self):
        """
        Testing filtering items for non-existent Status actually returns 0 results. For issue #1312 in which the filter
        view expected to return 0 results was instead returning items in list. Used the Status of "deprecated" in this test,
        but the same behavior was observed in other filters, such as IPv4/IPv6.
        """
        prefixes = self._get_queryset().all()
        self.assertEqual(prefixes.count(), 3)

        url = self._get_url("list")
        response = self.client.get(f"{url}?status=deprecated")
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))

        for prefix in prefixes:
            self.assertNotIn(prefix.get_absolute_url(), content, msg=content)


class IPAddressTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = IPAddress
    fixtures = (
        "status",
        "tag",
    )

    @classmethod
    def setUpTestData(cls):

        vrfs = VRF.objects.all()[:2]

        statuses = Status.objects.get_for_model(IPAddress)
        status_reserved = statuses.get(slug="reserved")

        IPAddress.objects.create(address=IPNetwork("192.0.2.1/24"), vrf=vrfs[0], status=statuses[0])
        IPAddress.objects.create(address=IPNetwork("192.0.2.2/24"), vrf=vrfs[0], status=statuses[0])
        IPAddress.objects.create(address=IPNetwork("192.0.2.3/24"), vrf=vrfs[0], status=statuses[0])

        cls.form_data = {
            "vrf": vrfs[1].pk,
            "address": IPNetwork("192.0.2.99/24"),
            "tenant": None,
            "status": status_reserved.pk,
            "role": IPAddressRoleChoices.ROLE_ANYCAST,
            "nat_inside": None,
            "dns_name": "example",
            "description": "A new IP address",
            "tags": [t.pk for t in Tag.objects.get_for_model(IPAddress)],
        }

        cls.csv_data = (
            "vrf,address,status",
            f"{vrfs[0].name},192.0.2.4/24,active",
            f"{vrfs[0].name},192.0.2.5/24,active",
            f"{vrfs[0].name},192.0.2.6/24,active",
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

        site = Site.objects.first()

        VLANGroup.objects.create(name="VLAN Group 8", site=site)

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
            "VLAN Group 7,,Seventh VLAN group",
        )
        cls.slug_source = "name"
        cls.slug_test_object = "VLAN Group 8"

    def get_deletable_object(self):
        """Return a VLANGroup without any associated VLANs."""
        return VLANGroup.objects.filter(vlans__isnull=True).first()

    def get_deletable_object_pks(self):
        """Return a list of PKs corresponding to VLANGroups without any associated VLANs."""
        groups = list(VLANGroup.objects.filter(vlans__isnull=True))[:3]
        return [group.pk for group in groups]


class VLANTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VLAN
    fixtures = (
        "status",
        "tag",
    )

    @classmethod
    def setUpTestData(cls):

        locations = Location.objects.filter(site__isnull=False)
        cls.sites = []
        for l in locations:
            if l.site not in cls.sites:
                cls.sites.append(l.site)

        vlangroups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=cls.sites[0]),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=cls.sites[1]),
        )

        roles = (
            Role.objects.create(name="Role 1", slug="role-1"),
            Role.objects.create(name="Role 2", slug="role-2"),
        )

        statuses = Status.objects.get_for_model(VLAN)
        status_active = statuses.get(slug="active")
        status_reserved = statuses.get(slug="reserved")

        VLAN.objects.create(
            group=vlangroups[0],
            vid=101,
            name="VLAN101",
            site=cls.sites[0],
            role=roles[0],
            status=status_active,
            _custom_field_data={"field": "Value"},
        )
        VLAN.objects.create(
            group=vlangroups[0],
            vid=102,
            name="VLAN102",
            site=cls.sites[0],
            role=roles[0],
            status=status_active,
            _custom_field_data={"field": "Value"},
        )
        VLAN.objects.create(
            group=vlangroups[0],
            vid=103,
            name="VLAN103",
            site=cls.sites[0],
            role=roles[0],
            status=status_active,
            _custom_field_data={"field": "Value"},
        )

        custom_field = CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, name="field", default="")
        custom_field.content_types.set([ContentType.objects.get_for_model(VLAN)])

        cls.form_data = {
            "location": Location.objects.filter(site=vlangroups[1].site).first().pk,
            "site": vlangroups[1].site.pk,
            "group": vlangroups[1].pk,
            "vid": 999,
            "name": "VLAN999",
            "tenant": None,
            "status": status_reserved.pk,
            "role": roles[1].pk,
            "description": "A new VLAN",
            "tags": [t.pk for t in Tag.objects.get_for_model(VLAN)],
        }

        cls.csv_data = (
            "vid,name,status",
            "104,VLAN104,active",
            "105,VLAN105,active",
            "106,VLAN106,active",
        )

        cls.bulk_edit_data = {
            "location": Location.objects.filter(site=vlangroups[1].site).first().pk,
            "site": vlangroups[1].site.pk,
            "group": vlangroups[1].pk,
            "tenant": Tenant.objects.first().pk,
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
    fixtures = ("tag",)

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.first()
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

        cls.form_data = {
            "device": device.pk,
            "virtual_machine": None,
            "name": "Service X",
            "protocol": ServiceProtocolChoices.PROTOCOL_TCP,
            "ports": "104,105",
            "ipaddresses": [],
            "description": "A new service",
            "tags": [t.pk for t in Tag.objects.get_for_model(Service)],
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
