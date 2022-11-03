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

    @classmethod
    def setUpTestData(cls):

        tenants = Tenant.objects.all()[:2]

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

    @classmethod
    def setUpTestData(cls):

        tenants = Tenant.objects.all()[:2]

        cls.form_data = {
            "name": "65000:100",
            "description": "A new route target",
            "tags": [t.pk for t in Tag.objects.get_for_model(RouteTarget)],
        }

        cls.csv_data = (
            "name,tenant,description",
            f'65000:1004,"{tenants[0].name}",Foo',
            f'65000:1005,"{tenants[1].name}",Bar',
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
        RIR.objects.create(name="RFC N/A")
        RIR.objects.create(name="MAGICNIC")
        RIR.objects.create(name="NOTANIC")

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
        cls.slug_test_object = RIR.objects.first().name


class AggregateTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Aggregate

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
        cls.slug_test_object = Role.objects.first().name


class PrefixTestCase(ViewTestCases.PrimaryObjectViewTestCase, ViewTestCases.ListObjectsViewTestCase):
    model = Prefix

    @classmethod
    def setUpTestData(cls):

        sites = Site.objects.all()[:2]
        vrfs = VRF.objects.all()[:2]

        roles = Role.objects.all()[:2]

        statuses = Status.objects.get_for_model(Prefix)
        status_reserved = statuses.get(slug="reserved")

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
            "location": None,
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
        s = Status.objects.create(name="nonexistentstatus")
        s.content_types.add(ContentType.objects.get_for_model(Prefix))
        self.assertNotEqual(prefixes.count(), 0)

        url = self._get_url("list")
        response = self.client.get(f"{url}?status=nonexistentstatus")
        self.assertHttpStatus(response, 200)
        content = extract_page_body(response.content.decode(response.charset))

        self.assertNotIn("Invalid filters were specified", content)
        for prefix in prefixes:
            self.assertNotIn(prefix.get_absolute_url(), content, msg=content)


class IPAddressTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = IPAddress

    @classmethod
    def setUpTestData(cls):

        vrfs = VRF.objects.all()[:2]

        statuses = Status.objects.get_for_model(IPAddress)
        status_reserved = statuses.get(slug="reserved")

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
        cls.slug_test_object = VLANGroup.objects.first().name


class VLANTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VLAN

    @classmethod
    def setUpTestData(cls):

        locations = Location.objects.filter(site__isnull=False)
        cls.sites = Site.objects.filter(locations__in=locations)

        site_1 = cls.sites.first()

        vlangroups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", site=site_1),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", site=cls.sites.last()),
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
            site=site_1,
            role=roles[0],
            status=status_active,
            _custom_field_data={"field": "Value"},
        )
        VLAN.objects.create(
            group=vlangroups[0],
            vid=102,
            name="VLAN102",
            site=site_1,
            role=roles[0],
            status=status_active,
            _custom_field_data={"field": "Value"},
        )
        VLAN.objects.create(
            group=vlangroups[0],
            vid=103,
            name="VLAN103",
            site=site_1,
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
            "location": Location.objects.filter(site=site_1).first().pk,
            "site": site_1.pk,
            "group": vlangroups[0].pk,
            "tenant": Tenant.objects.first().pk,
            "status": status_reserved.pk,
            "role": roles[0].pk,
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
