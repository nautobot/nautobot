import datetime

from netaddr import IPNetwork
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.utils.timezone import make_aware

from nautobot.core.testing import post_data, ViewTestCases
from nautobot.core.testing.utils import extract_page_body
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import CustomField, Role, Status, Tag
from nautobot.ipam.choices import ServiceProtocolChoices
from nautobot.ipam.models import (
    IPAddress,
    Namespace,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)
from nautobot.tenancy.models import Tenant
from nautobot.users.models import ObjectPermission
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine


class VRFTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VRF

    @classmethod
    def setUpTestData(cls):
        tenants = Tenant.objects.all()[:2]
        namespace = Namespace.objects.get(name="Global")

        cls.form_data = {
            "name": "VRF X",
            "namespace": namespace.pk,
            "rd": "65000:999",
            "tenant": tenants[0].pk,
            "description": "A new VRF",
            "tags": [t.pk for t in Tag.objects.get_for_model(VRF)],
        }

        cls.csv_data = (
            "name,rd,namespace",
            f"VRF 4,abc123,{namespace.name}",
            f"VRF 5,xyz246,{namespace.name}",
            f"VRF 6,,{namespace.name}",
        )

        cls.bulk_edit_data = {
            "tenant": tenants[1].pk,
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
        cls.form_data = {
            "name": "RIR X",
            "is_private": True,
            "description": "A new RIR",
        }

        cls.csv_data = (
            "name,description",
            "RIR 4,Fourth RIR",
            "RIR 5,Fifth RIR",
            "RIR 6,Sixth RIR",
            "RIR 7,Seventh RIR",
        )

    def setUp(self):
        super().setUp()
        # Ensure that we have at least one RIR with no prefixes that can be used for the "delete_object" tests.
        RIR.objects.create(name="RIR XYZ")


class PrefixTestCase(ViewTestCases.PrimaryObjectViewTestCase, ViewTestCases.ListObjectsViewTestCase):
    model = Prefix

    @classmethod
    def setUpTestData(cls):
        rir = RIR.objects.first()
        namespace = Namespace.objects.get(name="Global")

        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        vrfs = VRF.objects.all()[:2]

        roles = Role.objects.get_for_model(Prefix)[:2]

        statuses = Status.objects.get_for_model(Prefix)

        cls.form_data = {
            "prefix": IPNetwork("192.0.2.0/24"),
            "namespace": namespace.pk,
            "location": locations[1].pk,
            "vrf": vrfs[1].pk,
            "tenant": None,
            "vlan": None,
            "status": statuses[1].pk,
            "role": roles[1].pk,
            "type": "pool",
            "rir": rir.pk,
            "date_allocated": make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0, 0)),
            "description": "A new prefix",
            "tags": [t.pk for t in Tag.objects.get_for_model(Prefix)],
        }

        cls.csv_data = (
            "vrf,prefix,status,rir,namespace",
            f"{vrfs[0].name},10.4.0.0/16,{statuses[0].name},{rir.name},{namespace.name}",
            f"{vrfs[0].name},10.5.0.0/16,{statuses[0].name},{rir.name},{namespace.name}",
            f"{vrfs[0].name},10.6.0.0/16,{statuses[1].name},{rir.name},{namespace.name}",
        )

        cls.bulk_edit_data = {
            "location": None,
            "vrf": vrfs[1].pk,
            "tenant": None,
            "status": statuses[1].pk,
            "role": roles[1].pk,
            "type": "network",
            "rir": RIR.objects.last().pk,
            "date_allocated": make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0, 0)),
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
        status = Status.objects.create(name="nonexistentstatus")
        status.content_types.add(ContentType.objects.get_for_model(Prefix))
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
        namespace = Namespace.objects.get(name="Global")
        statuses = Status.objects.get_for_model(IPAddress)
        roles = Role.objects.get_for_model(IPAddress)
        parent, _ = Prefix.objects.get_or_create(
            prefix="192.0.2.0/24",
            defaults={"namespace": namespace, "status": statuses[0], "type": "network"},
        )

        cls.form_data = {
            "namespace": namespace.pk,
            "address": IPNetwork("192.0.2.99/24"),
            "tenant": None,
            "status": statuses[1].pk,
            "role": roles[0].pk,
            "nat_inside": None,
            "dns_name": "example",
            "description": "A new IP address",
            "tags": [t.pk for t in Tag.objects.get_for_model(IPAddress)],
        }

        cls.csv_data = (
            "address,status,parent",
            f"192.0.2.4/24,{statuses[0].name},{parent.natural_key_slug}",
            f"192.0.2.5/24,{statuses[0].name},{parent.natural_key_slug}",
            f"192.0.2.6/24,{statuses[0].name},{parent.natural_key_slug}",
        )

        cls.bulk_edit_data = {
            "tenant": None,
            "status": statuses[1].pk,
            "role": roles[1].pk,
            "dns_name": "example",
            "description": "New description",
        }

    def test_edit_object_with_permission(self):
        instance = self._get_queryset().first()
        form_data = self.form_data.copy()
        form_data["address"] = instance.address  # Host address is not modifiable
        self.form_data = form_data
        super().test_edit_object_with_permission()

    # TODO Revise these tests by borrowing the pattern that already exists in nautobot.core.testing.api
    # where by default the same data is used for both create and edit tests, but you have the option to override one or the other if needed.
    def test_edit_object_with_constrained_permission(self):
        instance = self._get_queryset().first()
        form_data = self.form_data.copy()
        form_data["address"] = instance.address  # Host address is not modifiable
        self.form_data = form_data
        super().test_edit_object_with_constrained_permission()

    def test_host_non_modifiable_once_set(self):
        """`host` field of the IPAddress should not be modifiable once the IPAddress is created."""
        ip_address_1 = self._get_queryset().first()
        ip_address_2 = self._get_queryset().last()

        # Assign model-level permission
        obj_perm = ObjectPermission(name="Test permission", actions=["change"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with model-level permission
        self.assertHttpStatus(self.client.get(self._get_url("edit", ip_address_1)), 200)

        # Try POST with model-level permission, with a different address from that of ip_address_1
        # a.k.a Try to modify the host field of ip_address_1
        self.form_data["address"] = ip_address_2.address
        request = {
            "path": self._get_url("edit", ip_address_1),
            "data": post_data(self.form_data),
        }
        response = self.client.post(**request)
        self.assertEqual(200, response.status_code)
        self.assertIn("Host address cannot be changed once created", str(response.content))


class VLANGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = VLANGroup

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        cls.form_data = {
            "name": "VLAN Group X",
            "slug": "vlan-group-x",
            "location": location.pk,
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
        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))
        location_1 = cls.locations.first()

        vlangroups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1", location=cls.locations.first()),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2", location=cls.locations.last()),
        )

        roles = Role.objects.get_for_model(VLAN)[:2]

        statuses = Status.objects.get_for_model(VLAN)
        status_1 = statuses[0]
        status_2 = statuses[1]

        VLAN.objects.create(
            vlan_group=vlangroups[0],
            vid=101,
            name="VLAN101",
            location=location_1,
            role=roles[0],
            status=status_1,
            _custom_field_data={"custom_field": "Value"},
        )
        VLAN.objects.create(
            vlan_group=vlangroups[0],
            vid=102,
            name="VLAN102",
            location=location_1,
            role=roles[0],
            status=status_1,
            _custom_field_data={"custom_field": "Value"},
        )
        VLAN.objects.create(
            vlan_group=vlangroups[0],
            vid=103,
            name="VLAN103",
            location=location_1,
            role=roles[0],
            status=status_1,
            _custom_field_data={"custom_field": "Value"},
        )

        custom_field = CustomField.objects.create(
            type=CustomFieldTypeChoices.TYPE_TEXT, label="Custom Field", default=""
        )
        custom_field.content_types.set([ContentType.objects.get_for_model(VLAN)])

        cls.form_data = {
            "location": cls.locations.last().pk,
            "vlan_group": vlangroups[1].pk,
            "vid": 999,
            "name": "VLAN999 with an unwieldy long name since we increased the limit to more than 64 characters",
            "tenant": None,
            "status": status_2.pk,
            "role": roles[1].pk,
            "description": "A new VLAN",
            "tags": [t.pk for t in Tag.objects.get_for_model(VLAN)],
        }

        cls.csv_data = (
            "vid,name,status",
            f"104,VLAN104,{status_1.name}",
            f"105,VLAN105,{status_1.name}",
            f"106,VLAN106,{status_1.name}",
        )

        cls.bulk_edit_data = {
            "location": cls.locations.first().pk,
            "vlan_group": vlangroups[0].pk,
            "tenant": Tenant.objects.first().pk,
            "status": status_2.pk,
            "role": roles[0].pk,
            "description": "New description",
        }


class ServiceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Service

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            name="Device 1", location=location, device_type=devicetype, role=devicerole, status=devicestatus
        )
        cluster_type = ClusterType.objects.create(name="Circuit Type 2")
        cluster = Cluster.objects.create(name="Cluster 1", cluster_type=cluster_type, location=location)
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        cls.virtual_machine = VirtualMachine.objects.create(cluster=cluster, name="VM 1", status=vm_status)
        Service.objects.bulk_create(
            [
                Service(
                    device=cls.device,
                    name="Service 1",
                    protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                    ports=[101],
                ),
                Service(
                    device=cls.device,
                    name="Service 2",
                    protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                    ports=[102],
                ),
                Service(
                    device=cls.device,
                    name="Service 3",
                    protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                    ports=[103],
                ),
            ]
        )

        cls.form_data = {
            "device": cls.device.pk,
            "virtual_machine": None,
            "name": "Service X",
            "protocol": ServiceProtocolChoices.PROTOCOL_TCP,
            "ports": "104,105",
            "ip_addresses": [],
            "description": "A new service",
            "tags": [t.pk for t in Tag.objects.get_for_model(Service)],
        }

        cls.csv_data = (
            "device,name,protocol,ports,description",
            f"{cls.device.natural_key_slug},Service 4,tcp,1,First service",
            f"{cls.device.natural_key_slug},Service 5,tcp,2,Second service",
            f'{cls.device.natural_key_slug},Service 6,udp,"3,4,5",Third service',
        )

        cls.bulk_edit_data = {
            "protocol": ServiceProtocolChoices.PROTOCOL_UDP,
            "ports": "106,107",
            "description": "New description",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_duplicate_service_name_on_the_same_device_violates_uniqueness_constraint(self):
        # Assign unconstrained permission
        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with model-level permission
        self.assertHttpStatus(self.client.get(self._get_url("add")), 200)
        # Duplicate name for a Service that already exists
        self.form_data["name"] = "Service 1"
        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(self.form_data),
        }
        response = self.client.post(**request)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("Service with this Name and Device already exists.", response_body)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_service_cannot_be_assigned_to_both_device_and_vm(self):
        # Assign unconstrained permission
        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with model-level permission
        self.assertHttpStatus(self.client.get(self._get_url("add")), 200)
        # Input a virtual machine as well in the form data
        self.form_data["virtual_machine"] = self.virtual_machine.pk
        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(self.form_data),
        }
        response = self.client.post(**request)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("A service cannot be associated with both a device and a virtual machine.", response_body)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_service_cannot_be_assigned_to_neither_device_nor_vm(self):
        # Assign unconstrained permission
        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ContentType.objects.get_for_model(self.model))

        # Try GET with model-level permission
        self.assertHttpStatus(self.client.get(self._get_url("add")), 200)
        # Input a virtual machine as well in the form data
        self.form_data["device"] = None
        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(self.form_data),
        }
        response = self.client.post(**request)
        self.assertHttpStatus(response, 200)
        response_body = extract_page_body(response.content.decode(response.charset))
        self.assertIn("A service must be associated with either a device or a virtual machine.", response_body)
