from concurrent.futures.thread import ThreadPoolExecutor
import json
from random import shuffle

from django.db import connection
from django.urls import reverse
from netaddr import IPNetwork
from rest_framework import status

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Site
from nautobot.extras.models import Status
from nautobot.ipam.choices import ServiceProtocolChoices
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
from nautobot.utilities.testing import APITestCase, APIViewTestCases, disable_warnings
from nautobot.utilities.testing.api import APITransactionTestCase


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("ipam-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class VRFTest(APIViewTestCases.APIViewTestCase):
    model = VRF
    brief_fields = ["display", "id", "name", "prefix_count", "rd", "url"]
    create_data = [
        {
            "name": "VRF 4",
            "rd": "65000:4",
        },
        {
            "name": "VRF 5",
            "rd": "65000:5",
        },
        {
            "name": "VRF 6",
            "rd": "65000:6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        vrfs = (
            VRF(name="VRF 1", rd="65000:1"),
            VRF(name="VRF 2", rd="65000:2"),
            VRF(name="VRF 3"),  # No RD
        )
        VRF.objects.bulk_create(vrfs)


class RouteTargetTest(APIViewTestCases.APIViewTestCase):
    model = RouteTarget
    brief_fields = ["display", "id", "name", "url"]
    create_data = [
        {
            "name": "65000:1004",
        },
        {
            "name": "65000:1005",
        },
        {
            "name": "65000:1006",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        route_targets = (
            RouteTarget(name="65000:1001"),
            RouteTarget(name="65000:1002"),
            RouteTarget(name="65000:1003"),
        )
        RouteTarget.objects.bulk_create(route_targets)


class RIRTest(APIViewTestCases.APIViewTestCase):
    model = RIR
    brief_fields = ["aggregate_count", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "RIR 4",
            "slug": "rir-4",
        },
        {
            "name": "RIR 5",
            "slug": "rir-5",
        },
        {
            "name": "RIR 6",
            "slug": "rir-6",
        },
        {
            "name": "RIR 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    slug_source = "name"

    @classmethod
    def setUpTestData(cls):

        rirs = (
            RIR(name="RIR 1", slug="rir-1"),
            RIR(name="RIR 2", slug="rir-2"),
            RIR(name="RIR 3", slug="rir-3"),
        )
        RIR.objects.bulk_create(rirs)


class AggregateTest(APIViewTestCases.APIViewTestCase):
    model = Aggregate
    brief_fields = ["display", "family", "id", "prefix", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        rirs = (
            RIR.objects.create(name="RIR 1", slug="rir-1"),
            RIR.objects.create(name="RIR 2", slug="rir-2"),
        )

        Aggregate.objects.create(prefix=IPNetwork("10.0.0.0/8"), rir=rirs[0])
        Aggregate.objects.create(prefix=IPNetwork("172.16.0.0/12"), rir=rirs[0])
        Aggregate.objects.create(prefix=IPNetwork("192.168.0.0/16"), rir=rirs[0])
        Aggregate.objects.create(prefix=IPNetwork("2001:db8:abcd::/64"), rir=rirs[0])

        cls.create_data = [
            {
                "prefix": "100.0.0.0/8",
                "rir": rirs[1].pk,
            },
            {
                "prefix": "2001:db8:abcd:12::/64",
                "rir": rirs[1].pk,
            },
            {
                "prefix": "102.0.0.0/8",
                "rir": rirs[1].pk,
            },
        ]


class RoleTest(APIViewTestCases.APIViewTestCase):
    model = Role
    brief_fields = ["display", "id", "name", "prefix_count", "slug", "url", "vlan_count"]
    create_data = [
        {
            "name": "Role 4",
            "slug": "role-4",
        },
        {
            "name": "Role 5",
            "slug": "role-5",
        },
        {
            "name": "Role 6",
            "slug": "role-6",
        },
        {
            "name": "Role 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):

        roles = (
            Role(name="Role 1", slug="role-1"),
            Role(name="Role 2", slug="role-2"),
            Role(name="Role 3", slug="role-3"),
        )
        Role.objects.bulk_create(roles)


class PrefixTest(APIViewTestCases.APIViewTestCase):
    model = Prefix
    brief_fields = ["display", "family", "id", "prefix", "url"]

    create_data = [
        {
            "prefix": "192.168.4.0/24",
            "status": "active",
        },
        {
            "prefix": "2001:db8:abcd:12::/80",
            "status": "active",
        },
        {
            "prefix": "192.168.6.0/24",
            "status": "active",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["status"]

    def setUp(self):
        super().setUp()
        self.statuses = Status.objects.get_for_model(Prefix)
        self.status_active = self.statuses.get(slug="active")

    @classmethod
    def setUpTestData(cls):

        statuses = Status.objects.get_for_model(Prefix)

        Prefix.objects.create(prefix=IPNetwork("192.168.1.0/24"), status=statuses[0])
        Prefix.objects.create(prefix=IPNetwork("192.168.2.0/24"), status=statuses[0])
        Prefix.objects.create(prefix=IPNetwork("192.168.3.0/24"), status=statuses[0])
        Prefix.objects.create(prefix=IPNetwork("2001:db8:abcd::/80"), status=statuses[0])

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

    def test_list_available_prefixes(self):
        """
        Test retrieval of all available prefixes within a parent prefix.
        """
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/24"))
        Prefix.objects.create(prefix=IPNetwork("192.0.2.64/26"), status=self.status_active)
        Prefix.objects.create(prefix=IPNetwork("192.0.2.192/27"), status=self.status_active)
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix")

        # Retrieve all available IPs
        response = self.client.get(url, **self.header)
        available_prefixes = ["192.0.2.0/26", "192.0.2.128/26", "192.0.2.224/27"]
        for i, p in enumerate(response.data):
            self.assertEqual(p["prefix"], available_prefixes[i])

    def test_create_single_available_prefix(self):
        """
        Test retrieval of the first available prefix within a parent prefix.
        """
        vrf = VRF.objects.create(name="Test VRF 1", rd="1234")
        prefix = Prefix.objects.create(
            prefix=IPNetwork("192.0.2.0/28"),
            vrf=vrf,
            is_pool=True,
            status=self.status_active,
        )
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.add_prefix")

        # Create four available prefixes with individual requests
        prefixes_to_be_created = [
            "192.0.2.0/30",
            "192.0.2.4/30",
            "192.0.2.8/30",
            "192.0.2.12/30",
        ]
        for i in range(4):
            data = {
                "prefix_length": 30,
                "status": "active",
                "description": f"Test Prefix {i + 1}",
            }
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertEqual(response.data["prefix"], prefixes_to_be_created[i])
            self.assertEqual(response.data["vrf"]["id"], str(vrf.pk))
            self.assertEqual(response.data["description"], data["description"])

        # Try to create one more prefix
        response = self.client.post(url, {"prefix_length": 30}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

        # Try to create invalid prefix type
        response = self.client.post(url, {"prefix_length": "30"}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prefix_length", response.data[0])

    def test_create_multiple_available_prefixes(self):
        """
        Test the creation of available prefixes within a parent prefix.
        """
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/28"), is_pool=True)
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_prefix")

        # Try to create five /30s (only four are available)
        data = [
            {"prefix_length": 30, "description": "Test Prefix 1", "status": "active"},
            {"prefix_length": 30, "description": "Test Prefix 2", "status": "active"},
            {"prefix_length": 30, "description": "Test Prefix 3", "status": "active"},
            {"prefix_length": 30, "description": "Test Prefix 4", "status": "active"},
            {"prefix_length": 30, "description": "Test Prefix 5", "status": "active"},
        ]
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

        # Verify that no prefixes were created (the entire /28 is still available)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["prefix"], "192.0.2.0/28")

        # Create four /30s in a single request
        response = self.client.post(url, data[:4], format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 4)

    def test_list_available_ips(self):
        """
        Test retrieval of all available IP addresses within a parent prefix.
        """
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/29"), is_pool=True, status=self.status_active)
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.view_ipaddress")

        # Retrieve all available IPs
        response = self.client.get(url, **self.header)
        self.assertEqual(len(response.data), 8)  # 8 because prefix.is_pool = True

        # Change the prefix to not be a pool and try again
        prefix.is_pool = False
        prefix.save()
        response = self.client.get(url, **self.header)
        self.assertEqual(len(response.data), 6)  # 8 - 2 because prefix.is_pool = False

    def test_create_single_available_ip(self):
        """
        Test retrieval of the first available IP address within a parent prefix.
        """
        vrf = VRF.objects.create(name="Test VRF 1", rd="1234")
        prefix = Prefix.objects.create(
            prefix=IPNetwork("192.0.2.0/30"),
            vrf=vrf,
            is_pool=True,
            status=self.status_active,
        )
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_ipaddress", "extras.view_status")

        # Create all four available IPs with individual requests
        for i in range(1, 5):
            data = {
                "description": f"Test IP {i}",
                "status": "active",
            }
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertEqual(response.data["vrf"]["id"], str(vrf.pk))
            self.assertEqual(response.data["description"], data["description"])

        # Try to create one more IP
        response = self.client.post(url, {}, **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

    def test_create_multiple_available_ips(self):
        """
        Test the creation of available IP addresses within a parent prefix.
        """
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/29"), is_pool=True, status=self.status_active)
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_ipaddress", "extras.view_status")

        # Try to create nine IPs (only eight are available)
        data = [{"description": f"Test IP {i}", "status": "active"} for i in range(1, 10)]  # 9 IPs
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

        # Create all eight available IPs in a single request
        data = [{"description": f"Test IP {i}", "status": "active"} for i in range(1, 9)]  # 8 IPs
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 8)


class ParallelPrefixTest(APITransactionTestCase):
    """
    Adapted from https://github.com/netbox-community/netbox/pull/3726
    """

    def test_create_multiple_available_prefixes_parallel(self):
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/28"), is_pool=True)

        # 5 Prefixes
        requests = [{"prefix_length": 30, "description": f"Test Prefix {i}", "status": "active"} for i in range(1, 6)]
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})

        self._do_parallel_requests(url, requests)

        prefixes = [str(o) for o in Prefix.objects.filter(prefix_length=30).all()]
        self.assertEqual(len(prefixes), len(set(prefixes)), "Duplicate prefixes should not exist")

    def test_create_multiple_available_ips_parallel(self):
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/29"), is_pool=True)

        # 8 IPs
        requests = [{"description": f"Test IP {i}", "status": "active"} for i in range(1, 9)]
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})

        self._do_parallel_requests(url, requests)

        ips = [str(o) for o in IPAddress.objects.filter().all()]
        self.assertEqual(len(ips), len(set(ips)), "Duplicate IPs should not exist")

    def _do_parallel_requests(self, url, requests):
        # Randomize request order, such that test run more closely simulates
        # a real calling pattern.
        shuffle(requests)
        with ThreadPoolExecutor(max_workers=len(requests)) as executor:
            futures = []
            for req in requests:
                futures.append(executor.submit(self._threaded_post, url, req))

    def _threaded_post(self, url, data):
        try:
            self.assertHttpStatus(self.client.post(url, data, format="json", **self.header), status.HTTP_201_CREATED)
        finally:
            # Django will use a separate DB connection for each thread, but will not
            # automatically close connections, it must be done here.
            connection.close()


class IPAddressTest(APIViewTestCases.APIViewTestCase):
    model = IPAddress
    brief_fields = ["address", "display", "family", "id", "url"]
    create_data = [
        {
            "address": "192.168.0.4/24",
            "status": "active",
        },
        {
            "address": "2001:db8:abcd:12::20/128",
            "status": "active",
        },
        {
            "address": "192.168.0.6/24",
            "status": "active",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["assigned_object_type", "role", "status"]

    @classmethod
    def setUpTestData(cls):

        statuses = Status.objects.get_for_model(IPAddress)

        IPAddress.objects.create(address=IPNetwork("192.168.0.1/24"), status=statuses[0])
        IPAddress.objects.create(address=IPNetwork("192.168.0.2/24"), status=statuses[0])
        IPAddress.objects.create(address=IPNetwork("192.168.0.3/24"), status=statuses[0])
        IPAddress.objects.create(address=IPNetwork("2001:db8:abcd::20/128"), status=statuses[0])

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

    def test_create_invalid_address(self):
        """Pass various invalid inputs and confirm they are rejected cleanly."""
        self.add_permissions("ipam.add_ipaddress")

        for bad_address in ("", "192.168.0.0.100/24", "192.168.0.0/35", "2001:db8:1:2:3:4:5:6:7:8/64"):
            response = self.client.post(
                self._get_list_url(), {"address": bad_address, "status": "active"}, format="json", **self.header
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertIn("address", response.data)

    def test_create_multiple_outside_nat_success(self):
        """Validate NAT inside address can tie to multiple NAT outside addresses."""
        # Create the two outside NAT IP Addresses tied back to the single inside NAT address
        self.add_permissions("ipam.add_ipaddress")
        self.add_permissions("ipam.view_ipaddress")
        nat_inside = IPAddress.objects.get(address="192.168.0.1/24")
        # Create NAT outside with 192.168.0.1/24 IP as inside NAT
        ip1 = self.client.post(
            self._get_list_url(),
            {"address": "192.0.2.1/24", "nat_inside": nat_inside.pk, "status": "active"},
            format="json",
            **self.header,
        )
        self.assertHttpStatus(ip1, status.HTTP_201_CREATED)
        ip2 = self.client.post(
            self._get_list_url(),
            {"address": "192.0.2.2/24", "nat_inside": nat_inside.pk, "status": "active"},
            format="json",
            **self.header,
        )
        self.assertHttpStatus(ip2, status.HTTP_201_CREATED)

        # Fetch nat inside IP address with default (1.2) API
        response = self.client.get(
            self._get_detail_url(nat_inside),
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_412_PRECONDITION_FAILED)

        self.set_api_version(api_version="1.3")
        # Fetch nat inside IP address with 1.3 API
        response = self.client.get(
            self._get_detail_url(nat_inside),
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["nat_outside"][0]["address"], "192.0.2.1/24")
        self.assertEqual(response.data["nat_outside"][1]["address"], "192.0.2.2/24")


class VLANGroupTest(APIViewTestCases.APIViewTestCase):
    model = VLANGroup
    brief_fields = ["display", "id", "name", "slug", "url", "vlan_count"]
    create_data = [
        {
            "name": "VLAN Group 4",
            "slug": "vlan-group-4",
        },
        {
            "name": "VLAN Group 5",
            "slug": "vlan-group-5",
        },
        {
            "name": "VLAN Group 6",
            "slug": "vlan-group-6",
        },
        {
            "name": "VLAN Group 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }
    slug_source = "name"

    @classmethod
    def setUpTestData(cls):

        vlan_groups = (
            VLANGroup(name="VLAN Group 1", slug="vlan-group-1"),
            VLANGroup(name="VLAN Group 2", slug="vlan-group-2"),
            VLANGroup(name="VLAN Group 3", slug="vlan-group-3"),
        )
        VLANGroup.objects.bulk_create(vlan_groups)


class VLANTest(APIViewTestCases.APIViewTestCase):
    model = VLAN
    brief_fields = ["display", "id", "name", "url", "vid"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["status"]

    @classmethod
    def setUpTestData(cls):

        vlan_groups = (
            VLANGroup.objects.create(name="VLAN Group 1", slug="vlan-group-1"),
            VLANGroup.objects.create(name="VLAN Group 2", slug="vlan-group-2"),
        )

        statuses = Status.objects.get_for_model(VLAN)

        VLAN.objects.create(name="VLAN 1", vid=1, group=vlan_groups[0], status=statuses[0])
        VLAN.objects.create(name="VLAN 2", vid=2, group=vlan_groups[0], status=statuses[0])
        VLAN.objects.create(name="VLAN 3", vid=3, group=vlan_groups[0], status=statuses[0])

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "vid": 4,
                "name": "VLAN 4",
                "group": vlan_groups[1].pk,
                "status": "active",
            },
            {
                "vid": 5,
                "name": "VLAN 5",
                "group": vlan_groups[1].pk,
                "status": "active",
            },
            {
                "vid": 6,
                "name": "VLAN 6",
                "group": vlan_groups[1].pk,
                "status": "active",
            },
        ]

    def test_delete_vlan_with_prefix(self):
        """
        Attempt and fail to delete a VLAN with a Prefix assigned to it.
        """
        vlan = VLAN.objects.first()
        Prefix.objects.create(prefix=IPNetwork("192.0.2.0/24"), vlan=vlan)

        self.add_permissions("ipam.delete_vlan")
        url = reverse("ipam-api:vlan-detail", kwargs={"pk": vlan.pk})
        with disable_warnings("django.request"):
            response = self.client.delete(url, **self.header)

        self.assertHttpStatus(response, status.HTTP_409_CONFLICT)

        content = json.loads(response.content.decode("utf-8"))
        self.assertIn("detail", content)
        self.assertTrue(content["detail"].startswith("Unable to delete object."))


class ServiceTest(APIViewTestCases.APIViewTestCase):
    model = Service
    brief_fields = ["display", "id", "name", "ports", "protocol", "url"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["protocol"]

    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="Site 1", slug="site-1")
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")

        devices = (
            Device.objects.create(
                name="Device 1",
                site=site,
                device_type=devicetype,
                device_role=devicerole,
            ),
            Device.objects.create(
                name="Device 2",
                site=site,
                device_type=devicetype,
                device_role=devicerole,
            ),
        )
        cls.devices = devices

        Service.objects.create(
            device=devices[0],
            name="Service 1",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[1],
        )
        Service.objects.create(
            device=devices[0],
            name="Service 2",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[2],
        )
        Service.objects.create(
            device=devices[0],
            name="Service 3",
            protocol=ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[3],
        )

        cls.create_data = [
            {
                "device": devices[1].pk,
                "name": "Service 4",
                "protocol": ServiceProtocolChoices.PROTOCOL_TCP,
                "ports": [4],
            },
            {
                "device": devices[1].pk,
                "name": "Service 5",
                "protocol": ServiceProtocolChoices.PROTOCOL_TCP,
                "ports": [5],
            },
            {
                "device": devices[1].pk,
                "name": "Service 6",
                "protocol": ServiceProtocolChoices.PROTOCOL_TCP,
                "ports": [6],
            },
        ]

    def test_ports_regression(self):
        """
        Test that ports can be provided as str or int.

        Ref: https://github.com/nautobot/nautobot/issues/265
        """
        self.add_permissions("ipam.add_service")
        url = reverse("ipam-api:service-list")
        device = self.devices[0]

        data = {
            "name": "http",
            "protocol": "tcp",
            "device": str(device.id),
            "ports": ["80"],
        }
        expected = [80]  # We'll test w/ this

        # Ports as string should be good.
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["ports"], expected)

        # And do it again, but with ports as int.
        data["ports"] = expected
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["ports"], expected)
