import datetime
import random

from netaddr import IPNetwork
from django.contrib.contenttypes.models import ContentType
from django.test import override_settings
from django.utils.html import strip_tags
from django.utils.timezone import make_aware
from django.urls import reverse

from nautobot.circuits.models import Circuit, Provider
from nautobot.core.templatetags.helpers import queryset_to_pks
from nautobot.core.testing import post_data, ModelViewTestCase, ViewTestCases
from nautobot.core.testing.utils import extract_page_body
from nautobot.dcim.models import Device, DeviceType, Interface, Location, LocationType, Manufacturer
from nautobot.extras.choices import CustomFieldTypeChoices, RelationshipTypeChoices
from nautobot.extras.models import (
    CustomField,
    CustomFieldChoice,
    Relationship,
    RelationshipAssociation,
    Role,
    Status,
    Tag,
)
from nautobot.ipam.choices import IPAddressTypeChoices, PrefixTypeChoices, ServiceProtocolChoices
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


class NamespaceTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.GetObjectNotesViewTestCase,
    ViewTestCases.CreateObjectViewTestCase,
    ViewTestCases.EditObjectViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
    ViewTestCases.BulkImportObjectsViewTestCase,
):
    model = Namespace

    @classmethod
    def setUpTestData(cls):
        locations = Location.objects.all()[:4]

        cls.form_data = {"name": "Namespace X", "location": locations[0].pk, "description": "A new Namespace"}

        cls.csv_data = (
            "name,location",
            f"Namespace 4,{locations[1].pk}",
            f"Namespace 5,{locations[2].pk}",
            "Namespace 6,",
        )


class VRFTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VRF

    @classmethod
    def setUpTestData(cls):
        tenants = Tenant.objects.all()[:2]
        namespace = Namespace.objects.create(name="ipam_test_views_vrf_test")

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
        cls.namespace = Namespace.objects.create(name="ipam_test_views_prefix_test")

        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        vrfs = VRF.objects.all()[:2]

        cls.roles = Role.objects.get_for_model(Prefix)[:2]

        cls.statuses = Status.objects.get_for_model(Prefix)

        cls.form_data = {
            "prefix": IPNetwork("192.0.2.0/24"),
            "namespace": cls.namespace.pk,
            "location": cls.locations[1].pk,
            "vrf": vrfs[1].pk,
            "tenant": None,
            "vlan": None,
            "status": cls.statuses[1].pk,
            "role": cls.roles[1].pk,
            "type": "pool",
            "rir": rir.pk,
            "date_allocated": make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0, 0)),
            "description": "A new prefix",
            "tags": [t.pk for t in Tag.objects.get_for_model(Prefix)],
        }

        cls.csv_data = (
            "vrf,prefix,status,rir,namespace",
            f"{vrfs[0].name},10.4.0.0/16,{cls.statuses[0].name},{rir.name},{cls.namespace.name}",
            f"{vrfs[0].name},10.5.0.0/16,{cls.statuses[0].name},{rir.name},{cls.namespace.name}",
            f"{vrfs[0].name},10.6.0.0/16,{cls.statuses[1].name},{rir.name},{cls.namespace.name}",
        )

        cls.bulk_edit_data = {
            "location": None,
            "vrf": vrfs[1].pk,
            "tenant": None,
            "status": cls.statuses[1].pk,
            "role": cls.roles[1].pk,
            "rir": RIR.objects.last().pk,
            "date_allocated": make_aware(datetime.datetime(2020, 1, 1, 0, 0, 0, 0)),
            "description": "New description",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_empty_queryset(self):
        """
        Testing that filtering items for a non-existent Status actually returns 0 results.

        For issue #1312 in which the filter view expected to return 0 results was instead returning items in list.
        Used the Status of "deprecated" in this test,
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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_object_warnings(self):
        """Test various object creation scenarios that should result in a warning to the user."""
        Prefix.objects.create(
            prefix="10.0.0.0/8",
            namespace=self.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            status=self.statuses[1],
        )
        Prefix.objects.create(
            prefix="10.0.0.0/16",
            namespace=self.namespace,
            type=PrefixTypeChoices.TYPE_NETWORK,
            status=self.statuses[1],
        )
        Prefix.objects.create(
            prefix="10.0.0.0/24",
            namespace=self.namespace,
            type=PrefixTypeChoices.TYPE_POOL,
            status=self.statuses[1],
        )
        IPAddress.objects.create(
            address="10.0.0.1/32",
            status=Status.objects.get_for_model(IPAddress).first(),
            namespace=self.namespace,
        )
        self.add_permissions("ipam.add_prefix")

        common_data = {"namespace": self.namespace.pk, "status": self.statuses[0].pk}

        with self.subTest("Creating a Pool as child of a Container raises a warning"):
            data = {
                "prefix": "10.1.0.0/16",
                "type": PrefixTypeChoices.TYPE_POOL,
            }
            response = self.client.post(self._get_url("add"), data={**common_data, **data}, follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "10.1.0.0/16 is a Pool prefix but its parent 10.0.0.0/8 is a Container. "
                "This will be considered invalid data in a future release. "
                "Consider changing the type of 10.1.0.0/16 and/or 10.0.0.0/8 to resolve this issue.",
                strip_tags(content),
            )

        # We could test for Pool-in-Pool, Container-in-Network, Network-in-Network, Container-in-Pool, and
        # Network-in-Pool, but they all use the same code path and similar message

        with self.subTest("Creating a Container that will have a Pool as its child raises a warning"):
            data = {
                "prefix": "10.0.0.0/20",
                "type": PrefixTypeChoices.TYPE_CONTAINER,
            }
            response = self.client.post(self._get_url("add"), data={**common_data, **data}, follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "10.0.0.0/20 is a Container prefix and should not contain child prefixes of type Pool. "
                "This will be considered invalid data in a future release. "
                "Consider creating an intermediary Network prefix, or changing the type of its children to Network, "
                "to resolve this issue.",
                strip_tags(content),
            )

        with self.subTest("Creating a Network that will have another Network as its child raises a warning"):
            data = {
                "prefix": "10.0.0.0/12",
                "type": PrefixTypeChoices.TYPE_NETWORK,
            }
            response = self.client.post(self._get_url("add"), data={**common_data, **data}, follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "10.0.0.0/12 is a Network prefix and should not contain child prefixes of types Container or Network. "
                "This will be considered invalid data in a future release. "
                "Consider changing the type of 10.0.0.0/12 to Container, or changing the type of its children to Pool, "
                "to resolve this issue.",
                strip_tags(content),
            )

        with self.subTest("Creating a Pool that will have any other Prefix as its child raises a warning"):
            data = {
                "prefix": "0.0.0.0/0",
                "type": PrefixTypeChoices.TYPE_POOL,
            }
            response = self.client.post(self._get_url("add"), data={**common_data, **data}, follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "0.0.0.0/0 is a Pool prefix and should not contain other prefixes. "
                "This will be considered invalid data in a future release. "
                "Consider either changing the type of 0.0.0.0/0 to Container or Network, or deleting its children, "
                "to resolve this issue.",
                strip_tags(content),
            )

        with self.subTest("Creating a large Container that will contain IPs raises a warning"):
            data = {
                "prefix": "10.0.0.0/28",
                "type": PrefixTypeChoices.TYPE_CONTAINER,
            }
            response = self.client.post(self._get_url("add"), data={**common_data, **data}, follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "10.0.0.0/28 is a Container prefix and should not directly contain IP addresses. "
                "This will be considered invalid data in a future release. "
                "Consider either changing the type of 10.0.0.0/28 to Network, or creating one or more child "
                "prefix(es) of type Network to contain these IP addresses, to resolve this issue.",
                strip_tags(content),
            )

        with self.subTest("Creating a small Container that will contain IPs raises a different warning"):
            data = {
                "prefix": "10.0.0.1/32",
                "type": PrefixTypeChoices.TYPE_CONTAINER,
            }
            response = self.client.post(self._get_url("add"), data={**common_data, **data}, follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "10.0.0.1/32 is a Container prefix and should not directly contain IP addresses. "
                "This will be considered invalid data in a future release. "
                "Consider changing the type of 10.0.0.1/32 to Network to resolve this issue.",
                strip_tags(content),
            )


class IPAddressTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = IPAddress

    @classmethod
    def setUpTestData(cls):
        cls.namespace = Namespace.objects.create(name="ipam_test_views_ip_address_test")
        statuses = Status.objects.get_for_model(IPAddress)
        cls.prefix_status = Status.objects.get_for_model(Prefix).first()
        roles = Role.objects.get_for_model(IPAddress)
        parent, _ = Prefix.objects.get_or_create(
            prefix="192.0.2.0/24",
            defaults={"namespace": cls.namespace, "status": cls.prefix_status, "type": "network"},
        )

        cls.form_data = {
            "namespace": cls.namespace.pk,
            "address": IPNetwork("192.0.2.99/24"),
            "tenant": None,
            "status": statuses[1].pk,
            "type": IPAddressTypeChoices.TYPE_DHCP,
            "role": roles[0].pk,
            "nat_inside": None,
            "dns_name": "example",
            "description": "A new IP address",
            "tags": [t.pk for t in Tag.objects.get_for_model(IPAddress)],
        }

        cls.csv_data = (
            "address,status,parent",
            f"192.0.2.4/24,{statuses[0].name},{parent.composite_key}",
            f"192.0.2.5/24,{statuses[0].name},{parent.composite_key}",
            f"192.0.2.6/24,{statuses[0].name},{parent.composite_key}",
        )

        cls.bulk_edit_data = {
            "tenant": None,
            "status": statuses[1].pk,
            "role": roles[1].pk,
            "type": IPAddressTypeChoices.TYPE_HOST,
            "dns_name": "example",
            "description": "New description",
        }

    def test_edit_object_with_permission(self):
        instance = self._get_queryset().first()
        form_data = self.form_data.copy()
        form_data["address"] = instance.address  # Host address is not modifiable
        form_data["namespace"] = instance.parent.namespace.pk
        self.form_data = form_data
        super().test_edit_object_with_permission()

    # TODO Revise these tests by borrowing the pattern that already exists in nautobot.core.testing.api
    # where by default the same data is used for both create and edit tests, but you have the option to override one or the other if needed.
    def test_edit_object_with_constrained_permission(self):
        instance = self._get_queryset().first()
        form_data = self.form_data.copy()
        form_data["address"] = instance.address  # Host address is not modifiable
        form_data["namespace"] = instance.parent.namespace.pk
        self.form_data = form_data
        super().test_edit_object_with_constrained_permission()

    def test_host_non_modifiable_once_set(self):
        """`host` field of the IPAddress should not be modifiable once the IPAddress is created."""
        ip_address_1 = self._get_queryset().first()
        ip_address_2 = self._get_queryset().last()

        # Assign model-level permission
        self.add_permissions("ipam.change_ipaddress")

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

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_move_ip_addresses_between_namespaces(self):
        instance = self._get_queryset().first()
        new_namespace = Namespace.objects.create(name="Test Namespace")
        # Assign model-level permission
        self.add_permissions("ipam.change_ipaddress")

        # Try GET with model-level permission
        self.assertHttpStatus(self.client.get(self._get_url("edit", instance)), 200)

        form_data = self.form_data.copy()
        form_data["address"] = instance.address  # Host address is not modifiable
        form_data["namespace"] = new_namespace.pk
        request = {
            "path": self._get_url("edit", instance),
            "data": post_data(form_data),
        }
        response = self.client.post(**request)
        self.assertEqual(200, response.status_code)
        self.assertIn("No suitable parent Prefix exists in this Namespace", str(response.content))
        # Create an exact copy of the parent prefix but in a different namespace. See if the re-parenting is successful
        new_parent = Prefix.objects.create(
            prefix=instance.parent.prefix,
            namespace=new_namespace,
            status=instance.parent.status,
            type=instance.parent.type,
        )
        response = self.client.post(**request)
        self.assertEqual(302, response.status_code)
        created_ip = IPAddress.objects.get(parent__namespace=new_namespace, address=instance.address)
        self.assertEqual(created_ip.parent, new_parent)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_create_object_warnings(self):
        self.add_permissions("ipam.add_ipaddress")

        Prefix.objects.create(
            prefix="192.0.2.0/25",
            namespace=self.namespace,
            type=PrefixTypeChoices.TYPE_CONTAINER,
            status=self.prefix_status,
        )

        with self.subTest("Creating an IPAddress as a child of a larger Container prefix raises a warning"):
            self.form_data["address"] = "192.0.2.98/28"
            response = self.client.post(self._get_url("add"), data=post_data(self.form_data), follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "IP address 192.0.2.98/28 currently has prefix 192.0.2.0/25 as its parent, which is a Container. "
                "This will be considered invalid data in a future release. "
                "Consider creating an intermediate /28 prefix of type Network to resolve this issue.",
                strip_tags(content),
            )

        with self.subTest("Creating an IP as a child of a same-size Container prefix raises a different warning"):
            self.form_data["address"] = "192.0.2.2/25"
            response = self.client.post(self._get_url("add"), data=post_data(self.form_data), follow=True)
            self.assertHttpStatus(response, 200)
            content = extract_page_body(response.content.decode(response.charset))
            self.assertIn(
                "IP address 192.0.2.2/25 currently has prefix 192.0.2.0/25 as its parent, which is a Container. "
                "This will be considered invalid data in a future release. "
                "Consider changing the prefix to type Network or Pool to resolve this issue.",
                strip_tags(content),
            )


class IPAddressMergeTestCase(ModelViewTestCase):
    @classmethod
    def setUpTestData(cls):
        cls.merge_url = reverse("ipam:ipaddress_merge")
        statuses = Status.objects.get_for_model(IPAddress)
        prefix_status = Status.objects.get_for_model(Prefix).first()
        roles = Role.objects.get_for_model(IPAddress)
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()

        devices = (
            Device.objects.create(
                name="Device 1",
                location=location,
                device_type=devicetype,
                role=devicerole,
                status=devicestatus,
            ),
            Device.objects.create(
                name="Device 2",
                location=location,
                device_type=devicetype,
                role=devicerole,
                status=devicestatus,
            ),
            Device.objects.create(
                name="Device 3",
                location=location,
                device_type=devicetype,
                role=devicerole,
                status=devicestatus,
            ),
        )
        cls.devices = devices

        intf_status = Status.objects.get_for_model(Interface).first()
        cls.interfaces = (
            Interface.objects.create(device=cls.devices[0], name="Interface 1", status=intf_status),
            Interface.objects.create(device=cls.devices[1], name="Interface 2", status=intf_status),
            Interface.objects.create(device=cls.devices[2], name="Interface 3", status=intf_status),
        )
        cls.services = (
            Service.objects.create(
                device=devices[0],
                name="Service 1",
                protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                ports=[1],
            ),
            Service.objects.create(
                device=devices[0],
                name="Service 2",
                protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                ports=[2],
            ),
            Service.objects.create(
                device=devices[0],
                name="Service 3",
                protocol=ServiceProtocolChoices.PROTOCOL_TCP,
                ports=[3],
            ),
        )
        custom_fields = (
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, label="Merge IP CF Text"),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_INTEGER, label="Merge IP CF Integer"),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_SELECT, label="Merge IP CF Select"),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_MULTISELECT, label="Merge IP CF Multi Select"),
        )
        for custom_field in custom_fields:
            custom_field.content_types.set([ContentType.objects.get_for_model(IPAddress)])
        for x in ["A", "B", "C"]:
            CustomFieldChoice.objects.create(custom_field=custom_fields[2], value=f"SingleSelect Option {x}")
            CustomFieldChoice.objects.create(custom_field=custom_fields[3], value=f"MultiSelect Option {x}")
        namespace_1 = Namespace.objects.create(name="merge_ip_namespace_1")
        cls.namespace_2 = Namespace.objects.create(name="merge_ip_namespace_2")
        namespace_3 = Namespace.objects.create(name="merge_ip_namespace_3")
        parent_1, _ = Prefix.objects.get_or_create(
            prefix="94.0.0.2/10",
            defaults={"namespace": namespace_1, "status": prefix_status, "type": "network"},
        )
        cls.dup_ip_1 = IPAddress.objects.create(
            parent=parent_1,
            address="94.0.0.2/10",
            dns_name="example_1",
            status=statuses[0],
            type=IPAddressTypeChoices.TYPE_DHCP,
            role=roles[0],
            description="duplicate 1",
            tenant=Tenant.objects.last(),
            _custom_field_data={
                "merge_ip_cf_text": "Hello",
                "merge_ip_cf_integer": 12,
                "merge_ip_cf_select": "SingleSelect Option A",
                "merge_ip_cf_multi_select": [
                    "MultiSelect Option A",
                    "MultiSelect Option B",
                ],
            },
        )
        cls.dup_ip_1.tags.set(random.choices(Tag.objects.get_for_model(IPAddress), k=3))
        parent_2, _ = Prefix.objects.get_or_create(
            prefix="94.0.0.2/12",
            defaults={"namespace": cls.namespace_2, "status": prefix_status, "type": "network"},
        )
        cls.dup_ip_2 = IPAddress.objects.create(
            parent=parent_2,
            address="94.0.0.2/15",
            dns_name="example_2",
            status=statuses[1],
            type=IPAddressTypeChoices.TYPE_HOST,
            role=roles[1],
            description="duplicate 2",
            tenant=Tenant.objects.first(),
            _custom_field_data={
                "merge_ip_cf_text": "Hey",
                "merge_ip_cf_integer": 15,
                "merge_ip_cf_select": "SingleSelect Option B",
                "merge_ip_cf_multi_select": [
                    "MultiSelect Option A",
                    "MultiSelect Option C",
                ],
            },
        )
        cls.dup_ip_2.tags.set(random.choices(Tag.objects.get_for_model(IPAddress), k=2))
        parent_3, _ = Prefix.objects.get_or_create(
            prefix="94.0.0.2/15",
            defaults={"namespace": namespace_3, "status": prefix_status, "type": "network"},
        )
        cls.dup_ip_3 = IPAddress.objects.create(
            parent=parent_3,
            address="94.0.0.2/27",
            dns_name="example_3",
            status=statuses[2],
            type=IPAddressTypeChoices.TYPE_HOST,
            role=roles[2],
            description="duplicate 3",
            tenant=None,
            _custom_field_data={
                "merge_ip_cf_text": "What's up",
                "merge_ip_cf_integer": 120,
                "merge_ip_cf_select": "SingleSelect Option C",
                "merge_ip_cf_multi_select": [
                    "MultiSelect Option B",
                    "MultiSelect Option C",
                ],
            },
        )
        cls.dup_ip_3.tags.set(random.choices(Tag.objects.get_for_model(IPAddress), k=3))
        cls.merge_data = {
            "pk": [cls.dup_ip_1.pk, cls.dup_ip_2.pk, cls.dup_ip_3.pk],
            "host": cls.dup_ip_1.host,
            "mask_length": cls.dup_ip_3.mask_length,
            "namespace": str(cls.dup_ip_2.parent.namespace.pk),
            "tenant": str(cls.dup_ip_2.tenant.pk),
            "status": str(cls.dup_ip_1.status.pk),
            "type": cls.dup_ip_3.type,
            "role": str(cls.dup_ip_3.role.pk),
            "nat_inside": None,
            "dns_name": cls.dup_ip_3.dns_name,
            "description": cls.dup_ip_2.description,
            "tags": ",".join(str(t.pk) for t in cls.dup_ip_3.tags.all()),
            "cf_merge_ip_cf_text": str(cls.dup_ip_1.pk),
            "cf_merge_ip_cf_integer": str(cls.dup_ip_2.pk),
            "cf_merge_ip_cf_select": str(cls.dup_ip_3.pk),
            "cf_merge_ip_cf_multi_select": str(cls.dup_ip_2.pk),
        }
        cls.services[0].ip_addresses.add(cls.dup_ip_1)
        cls.services[1].ip_addresses.add(cls.dup_ip_2)
        cls.services[2].ip_addresses.add(cls.dup_ip_3)
        cls.interfaces[0].ip_addresses.add(cls.dup_ip_1)
        device_1 = Device.objects.get(pk=cls.interfaces[0].device.pk)
        device_1.primary_ip4 = cls.dup_ip_1
        device_1.save()
        cls.interfaces[1].ip_addresses.add(cls.dup_ip_2)
        device_2 = Device.objects.get(pk=cls.interfaces[1].device.pk)
        device_2.primary_ip4 = cls.dup_ip_2
        device_2.save()
        cls.interfaces[2].ip_addresses.add(cls.dup_ip_3)
        device_3 = Device.objects.get(pk=cls.interfaces[2].device.pk)
        device_3.primary_ip4 = cls.dup_ip_3
        device_3.save()

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_merging_ip_addresses_success(self):
        self.add_permissions("ipam.change_ipaddress")
        num_ips_before = IPAddress.objects.all().count()
        self.assertHttpStatus(self.client.get(self.merge_url), 200)
        request = {
            "path": self.merge_url,
            "data": post_data(self.merge_data),
        }
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)
        merged_ip = IPAddress.objects.get(parent__namespace=self.namespace_2)
        self.assertEqual(merged_ip.host, self.merge_data["host"])
        self.assertEqual(merged_ip.mask_length, self.merge_data["mask_length"])
        self.assertEqual(str(merged_ip.parent.namespace.pk), self.merge_data["namespace"])
        self.assertEqual(str(merged_ip.tenant.pk), self.merge_data["tenant"])
        self.assertEqual(str(merged_ip.status.pk), self.merge_data["status"])
        self.assertEqual(str(merged_ip.role.pk), self.merge_data["role"])
        self.assertEqual(merged_ip.type, self.merge_data["type"])
        self.assertEqual(merged_ip.dns_name, self.merge_data["dns_name"])
        self.assertEqual(merged_ip.description, self.merge_data["description"])
        self.assertEqual(",".join(str(t.pk) for t in merged_ip.tags.all()), self.merge_data["tags"])
        self.assertEqual(
            merged_ip._custom_field_data["merge_ip_cf_text"], self.dup_ip_1._custom_field_data["merge_ip_cf_text"]
        )
        self.assertEqual(
            merged_ip._custom_field_data["merge_ip_cf_integer"],
            self.dup_ip_2._custom_field_data["merge_ip_cf_integer"],
        )
        self.assertEqual(
            merged_ip._custom_field_data["merge_ip_cf_select"],
            self.dup_ip_3._custom_field_data["merge_ip_cf_select"],
        )
        self.assertEqual(
            merged_ip._custom_field_data["merge_ip_cf_multi_select"],
            self.dup_ip_2._custom_field_data["merge_ip_cf_multi_select"],
        )
        self.assertEqual(num_ips_before - 2, IPAddress.objects.all().count())
        for service in self.services:
            self.assertIn(merged_ip, service.ip_addresses.all())
        for interface in self.interfaces:
            self.assertIn(merged_ip, interface.ip_addresses.all())
        for device in self.devices:
            device.refresh_from_db()
            self.assertEqual(merged_ip, device.primary_ip4)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_merging_only_one_or_zero_ip_addresses(self):
        self.add_permissions("ipam.change_ipaddress")
        self.assertHttpStatus(self.client.get(self.merge_url), 200)
        num_ips_before = IPAddress.objects.all().count()
        self.merge_data["pk"] = self.merge_data["pk"][0]
        request = {
            "path": self.merge_url,
            "data": post_data(self.merge_data),
        }
        response = self.client.post(**request)
        # redirect to IPAddressListView and no IP is merged
        self.assertHttpStatus(response, 302)
        self.assertEqual(num_ips_before, IPAddress.objects.all().count())
        self.merge_data["pk"] = []
        request = {
            "path": self.merge_url,
            "data": post_data(self.merge_data),
        }
        response = self.client.post(**request)
        # redirect to IPAddressListView and no IP is merged
        self.assertHttpStatus(response, 302)
        self.assertEqual(num_ips_before, IPAddress.objects.all().count())

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_relationship_data_changes_after_merging(self):
        self.add_permissions("ipam.change_ipaddress")
        num_ips_before = IPAddress.objects.all().count()
        ips = IPAddress.objects.all().exclude(pk__in=[self.dup_ip_1.pk, self.dup_ip_2.pk, self.dup_ip_3.pk])
        ip_ct = ContentType.objects.get_for_model(IPAddress)
        locations = Location.objects.all()
        location_ct = ContentType.objects.get_for_model(Location)
        device_types = DeviceType.objects.all()
        device_type_ct = ContentType.objects.get_for_model(DeviceType)
        provider_ct = ContentType.objects.get_for_model(Provider)
        providers = Provider.objects.all()
        circuit_ct = ContentType.objects.get_for_model(Circuit)
        circuits = Circuit.objects.all()

        m2m = Relationship.objects.create(
            label="IP Address 2 Location m2m",
            key="ip_address_2_location_m2m",
            source_type=ip_ct,
            destination_type=location_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY,
        )
        sym_m2m = Relationship.objects.create(
            label="IP 2 IP m2m",
            key="ip_2_ip_m2m",
            source_type=ip_ct,
            destination_type=ip_ct,
            type=RelationshipTypeChoices.TYPE_MANY_TO_MANY_SYMMETRIC,
        )
        o2o = Relationship.objects.create(
            label="IP Address 2 Circuit o2o",
            key="ip_address_2_circuit_o2o",
            source_type=ip_ct,
            destination_type=circuit_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE,
        )
        sym_o2o = Relationship.objects.create(
            label="IP 2 IP o2o",
            key="ip_2_ip_o2o",
            source_type=ip_ct,
            destination_type=ip_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_ONE_SYMMETRIC,
        )
        o2m_source = Relationship.objects.create(
            label="IP Address 2 Device Type o2m Source",
            key="ip_address_2_device_type_o2m_source",
            source_type=ip_ct,
            destination_type=device_type_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        o2m_destination = Relationship.objects.create(
            label="Provider 2 IP Address o2m Destination",
            key="provider_2_ip_address_o2m_destination",
            source_type=provider_ct,
            destination_type=ip_ct,
            type=RelationshipTypeChoices.TYPE_ONE_TO_MANY,
        )
        rel_associations = (
            RelationshipAssociation(
                relationship=m2m,
                source=self.dup_ip_1,
                destination=locations[0],
            ),
            RelationshipAssociation(
                relationship=m2m,
                source=self.dup_ip_2,
                destination=locations[0],
            ),
            RelationshipAssociation(
                relationship=m2m,
                source=self.dup_ip_3,
                destination=locations[1],
            ),
            RelationshipAssociation(
                relationship=m2m,
                source=self.dup_ip_1,
                destination=locations[1],
            ),
            RelationshipAssociation(
                relationship=m2m,
                source=self.dup_ip_2,
                destination=locations[2],
            ),
            RelationshipAssociation(
                relationship=sym_m2m,
                source=ips[0],
                destination=self.dup_ip_1,
            ),
            RelationshipAssociation(
                relationship=sym_m2m,
                source=ips[1],
                destination=self.dup_ip_2,
            ),
            RelationshipAssociation(
                relationship=sym_m2m,
                source=ips[2],
                destination=self.dup_ip_2,
            ),
            RelationshipAssociation(
                relationship=sym_m2m,
                source=self.dup_ip_2,
                destination=ips[3],
            ),
            RelationshipAssociation(
                relationship=o2o,
                source=self.dup_ip_1,
                destination=circuits[0],
            ),
            RelationshipAssociation(
                relationship=o2o,
                source=self.dup_ip_2,
                destination=circuits[1],
            ),
            RelationshipAssociation(
                relationship=o2o,
                source=self.dup_ip_3,
                destination=circuits[2],
            ),
            RelationshipAssociation(
                relationship=sym_o2o,
                source=self.dup_ip_1,
                destination=ips[4],
            ),
            RelationshipAssociation(
                relationship=sym_o2o,
                source=self.dup_ip_2,
                destination=ips[5],
            ),
            RelationshipAssociation(
                relationship=o2m_source,
                source=self.dup_ip_1,
                destination=device_types[0],
            ),
            RelationshipAssociation(
                relationship=o2m_source,
                source=self.dup_ip_1,
                destination=device_types[1],
            ),
            RelationshipAssociation(
                relationship=o2m_source,
                source=self.dup_ip_1,
                destination=device_types[2],
            ),
            RelationshipAssociation(
                relationship=o2m_source,
                source=self.dup_ip_1,
                destination=device_types[3],
            ),
            RelationshipAssociation(
                relationship=o2m_source,
                source=self.dup_ip_2,
                destination=device_types[4],
            ),
            RelationshipAssociation(
                relationship=o2m_source,
                source=self.dup_ip_2,
                destination=device_types[5],
            ),
            RelationshipAssociation(
                relationship=o2m_destination,
                source=providers[0],
                destination=self.dup_ip_1,
            ),
            RelationshipAssociation(
                relationship=o2m_destination,
                source=providers[0],
                destination=self.dup_ip_2,
            ),
            RelationshipAssociation(
                relationship=o2m_destination,
                source=providers[1],
                destination=self.dup_ip_3,
            ),
        )

        for assoc in rel_associations:
            assoc.validated_save()

        # Taking the dup_ip_2's many to many RelationshipAssociations and put into the merge data
        self.merge_data["cr_" + m2m.key] = queryset_to_pks(
            RelationshipAssociation.objects.filter(relationship=m2m, source_id=self.dup_ip_2.pk)
        )
        # Taking the dup_ip_2's symmetric many to many RelationshipAssociations and put into the merge data
        self.merge_data["cr_" + sym_m2m.key] = queryset_to_pks(
            RelationshipAssociation.objects.filter(relationship=sym_m2m, source_id=self.dup_ip_2.pk)
            | RelationshipAssociation.objects.filter(relationship=sym_m2m, destination_id=self.dup_ip_2.pk)
        )
        # Taking the dup_ip_3's one to one destination_id and put into the merge data
        self.merge_data["cr_" + o2o.key] = str(circuits[2].pk)
        # Taking the dup_ip_1's symmetric one to one destination_id and put into the merge data
        self.merge_data["cr_" + sym_o2o.key] = str(ips[4].pk)
        # Taking the dup_ip_1's one to many RelationshipAssociations and put into the merge data
        self.merge_data["cr_" + o2m_source.key] = queryset_to_pks(
            RelationshipAssociation.objects.filter(relationship=o2m_source, source_id=self.dup_ip_1.pk)
        )
        # Taking the dup_ip_3's one to many source_id and put into the merge data
        self.merge_data["cr_" + o2m_destination.key] = str(providers[1].pk)
        request = {
            "path": self.merge_url,
            "data": post_data(self.merge_data),
        }
        response = self.client.post(**request)
        # redirect to IPAddressListView and no IP is merged
        self.assertHttpStatus(response, 302)
        self.assertEqual(num_ips_before - 2, IPAddress.objects.all().count())
        merged_ip = IPAddress.objects.get(parent__namespace=self.namespace_2)
        for _, relationships in merged_ip.get_relationships_data().items():
            for relationship, value in relationships.items():
                if relationship == o2o:
                    self.assertEqual(value.get("value"), circuits[2])
                elif relationship == sym_o2o:
                    self.assertEqual(value.get("value"), ips[4])
                elif relationship == o2m_destination:
                    self.assertEqual(value.get("value"), providers[1])
                elif relationship == m2m:
                    associations = value.get("queryset")
                    correct_associations = RelationshipAssociation.objects.filter(
                        relationship=m2m, source_id=merged_ip.pk
                    )
                    self.assertEqual(set(associations), set(correct_associations))
                elif relationship == o2m_source:
                    associations = value.get("queryset")
                    correct_associations = RelationshipAssociation.objects.filter(
                        relationship=o2m_source, source_id=merged_ip.pk
                    )
                    self.assertEqual(set(associations), set(correct_associations))
                else:
                    associations = value.get("queryset")
                    correct_associations = RelationshipAssociation.objects.filter(
                        relationship=sym_m2m, source_id=merged_ip.pk
                    ) | RelationshipAssociation.objects.filter(relationship=sym_m2m, destination_id=merged_ip.pk)
                    self.assertEqual(set(associations), set(correct_associations))


class VLANGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = VLANGroup

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()

        cls.form_data = {
            "name": "VLAN Group X",
            "location": location.pk,
            "description": "A new VLAN group",
        }

        cls.csv_data = (
            "name,description",
            "VLAN Group 4,Fourth VLAN group",
            "VLAN Group 5,Fifth VLAN group",
            "VLAN Group 6,Sixth VLAN group",
            "VLAN Group 7,Seventh VLAN group",
        )


class VLANTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VLAN

    @classmethod
    def setUpTestData(cls):
        cls.locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))
        location_1 = cls.locations.first()

        vlangroups = (
            VLANGroup.objects.create(name="VLAN Group 1", location=cls.locations.first()),
            VLANGroup.objects.create(name="VLAN Group 2", location=cls.locations.last()),
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
            "vid,name,status,vlan_group",
            f"104,VLAN104,{status_1.name},{vlangroups[0].composite_key}",
            f"105,VLAN105,{status_1.name},{vlangroups[0].composite_key}",
            f"106,VLAN106,{status_1.name},{vlangroups[0].composite_key}",
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
            f"{cls.device.composite_key},Service 4,tcp,1,First service",
            f"{cls.device.composite_key},Service 5,tcp,2,Second service",
            f'{cls.device.composite_key},Service 6,udp,"3,4,5",Third service',
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
