from concurrent.futures.thread import ThreadPoolExecutor
import json
import logging
from random import shuffle

from django.db import connection
from django.urls import reverse
from netaddr import IPNetwork
from rest_framework import status

from nautobot.core.testing import APITestCase, APIViewTestCases, disable_warnings
from nautobot.core.testing.api import APITransactionTestCase
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.ipam import choices
from nautobot.ipam.models import (
    IPAddress,
    Prefix,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VRF,
)


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


class RIRTest(APIViewTestCases.APIViewTestCase):
    model = RIR
    brief_fields = ["assigned_prefix_count", "display", "id", "name", "slug", "url"]
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

    def get_deletable_object(self):
        return RIR.objects.create(name="DELETE ME")

    def get_deletable_object_pks(self):
        RIRs = [
            RIR.objects.create(name="Deletable RIR 1"),
            RIR.objects.create(name="Deletable RIR 2"),
            RIR.objects.create(name="Deletable RIR 3"),
        ]
        return [rir.pk for rir in RIRs]


class PrefixTest(APIViewTestCases.APIViewTestCase):
    model = Prefix
    brief_fields = ["display", "family", "id", "prefix", "url"]
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        rir = RIR.objects.filter(is_private=False).first()
        cls.statuses = Status.objects.get_for_model(Prefix)
        cls.status_active = cls.statuses.get(slug="active")
        cls.create_data = [
            {
                "prefix": "192.168.4.0/24",
                "status": cls.status_active.pk,
                "rir": rir.pk,
                "type": choices.PrefixTypeChoices.TYPE_POOL,
            },
            {
                "prefix": "2001:db8:abcd:12::/80",
                "status": cls.status_active.pk,
                "rir": rir.pk,
                "type": choices.PrefixTypeChoices.TYPE_NETWORK,
            },
            {
                "prefix": "192.168.6.0/24",
                "status": cls.status_active.pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "New description",
            "status": cls.statuses[0].pk,
        }
        cls.choices_fields = ["type"]

    def test_list_available_prefixes(self):
        """
        Test retrieval of all available prefixes within a parent prefix.
        """
        prefix = (
            Prefix.objects.ip_family(6)
            .filter(prefix_length__lt=128)
            .exclude(type=choices.PrefixTypeChoices.TYPE_CONTAINER)
            .first()
        )
        if prefix is None:
            self.fail("Suitable prefix fixture not found")
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix")

        # Retrieve all available IPs
        response = self.client.get(url, **self.header)
        available_prefixes = prefix.get_available_prefixes().iter_cidrs()
        for i, p in enumerate(response.data):
            self.assertEqual(p["prefix"], str(available_prefixes[i]))

    def test_create_single_available_prefix(self):
        """
        Test retrieval of the first available prefix within a parent prefix.
        """
        # Find prefix with no child prefixes and large enough to create 4 child prefixes
        for instance in Prefix.objects.filter(vrf__isnull=False):
            if instance.get_child_prefixes().count() == 0 and instance.prefix.size > 2:
                prefix = instance
                break
        else:
            self.fail("Suitable prefix fixture not found")
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.add_prefix")

        # Create four available prefixes with individual requests
        child_prefix_length = prefix.prefix_length + 2
        prefixes_to_be_created = list(prefix.prefix.subnet(child_prefix_length))
        for i in range(4):
            data = {
                "prefix_length": child_prefix_length,
                "status": self.status_active.pk,
                "description": f"Test Prefix {i + 1}",
            }
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertEqual(response.data["prefix"], str(prefixes_to_be_created[i]))
            self.assertEqual(response.data["vrf"]["id"], str(prefix.vrf.pk))
            self.assertEqual(response.data["description"], data["description"])

        # Try to create one more prefix
        response = self.client.post(url, {"prefix_length": child_prefix_length}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

        # Try to create invalid prefix type
        response = self.client.post(url, {"prefix_length": str(child_prefix_length)}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("prefix_length", response.data[0])

    def test_create_multiple_available_prefixes(self):
        """
        Test the creation of available prefixes within a parent prefix.
        """
        # Find prefix with no child prefixes and large enough to create 4 child prefixes
        for instance in Prefix.objects.filter(vrf__isnull=False):
            if instance.get_child_prefixes().count() == 0 and instance.prefix.size > 2:
                prefix = instance
                break
        else:
            self.fail("Suitable prefix fixture not found")

        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_prefix")

        # Try to create five prefixes (only four are available)
        child_prefix_length = prefix.prefix_length + 2
        data = [
            {"prefix_length": child_prefix_length, "description": "Test Prefix 1", "status": self.status_active.pk},
            {"prefix_length": child_prefix_length, "description": "Test Prefix 2", "status": self.status_active.pk},
            {"prefix_length": child_prefix_length, "description": "Test Prefix 3", "status": self.status_active.pk},
            {"prefix_length": child_prefix_length, "description": "Test Prefix 4", "status": self.status_active.pk},
            {"prefix_length": child_prefix_length, "description": "Test Prefix 5", "status": self.status_active.pk},
        ]
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

        # Verify that no prefixes were created (the entire prefix is still available)
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data[0]["prefix"], prefix.cidr_str)

        # Create four prefixes in a single request
        response = self.client.post(url, data[:4], format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 4)

    def test_list_available_ips(self):
        """
        Test retrieval of all available IP addresses within a parent prefix.
        """
        prefix = Prefix.objects.create(
            prefix=IPNetwork("192.0.2.0/29"), type=choices.PrefixTypeChoices.TYPE_POOL, status=self.status_active
        )
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.view_ipaddress")

        # Retrieve all available IPs
        response = self.client.get(url, **self.header)
        self.assertEqual(len(response.data), 8)  # 8 because prefix.type = pool

        # Change the prefix to not be a pool and try again
        prefix.type = choices.PrefixTypeChoices.TYPE_NETWORK
        prefix.save()
        response = self.client.get(url, **self.header)
        self.assertEqual(len(response.data), 6)  # 8 - 2 because prefix.type = network

    def test_create_single_available_ip(self):
        """
        Test retrieval of the first available IP address within a parent prefix.
        """
        vrf = VRF.objects.first()
        prefix = Prefix.objects.create(
            prefix=IPNetwork("192.0.2.0/30"),
            vrf=vrf,
            type=choices.PrefixTypeChoices.TYPE_POOL,
            status=self.status_active,
        )
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_ipaddress", "extras.view_status")

        # Create all four available IPs with individual requests
        for i in range(1, 5):
            data = {
                "description": f"Test IP {i}",
                "status": self.status_active.pk,
            }
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertEqual(response.data["vrf"]["id"], str(vrf.pk))
            self.assertEqual(response.data["description"], data["description"])

        # Try to create one more IP
        response = self.client.post(url, {}, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

    def test_create_multiple_available_ips(self):
        """
        Test the creation of available IP addresses within a parent prefix.
        """
        prefix = Prefix.objects.create(
            prefix=IPNetwork("192.0.2.0/29"), type=choices.PrefixTypeChoices.TYPE_POOL, status=self.status_active
        )
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_ipaddress", "extras.view_status")

        # Try to create nine IPs (only eight are available)
        data = [{"description": f"Test IP {i}", "status": self.status_active.pk} for i in range(1, 10)]  # 9 IPs
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

        # Create all eight available IPs in a single request
        data = [{"description": f"Test IP {i}", "status": self.status_active.pk} for i in range(1, 9)]  # 8 IPs
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 8)


class ParallelPrefixTest(APITransactionTestCase):
    """
    Adapted from https://github.com/netbox-community/netbox/pull/3726
    """

    def test_create_multiple_available_prefixes_parallel(self):
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/28"), type=choices.PrefixTypeChoices.TYPE_POOL)
        status_active = Status.objects.get(slug="active")

        # 5 Prefixes
        requests = [
            {"prefix_length": 30, "description": f"Test Prefix {i}", "status": status_active.pk} for i in range(1, 6)
        ]
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        logging.disable(logging.ERROR)
        self._do_parallel_requests(url, requests)
        logging.disable(logging.NOTSET)

        prefixes = [str(o) for o in Prefix.objects.filter(prefix_length=30).all()]
        self.assertEqual(len(prefixes), len(set(prefixes)), "Duplicate prefixes should not exist")

    def test_create_multiple_available_ips_parallel(self):
        prefix = Prefix.objects.create(prefix=IPNetwork("192.0.2.0/29"), type=choices.PrefixTypeChoices.TYPE_POOL)
        status_active = Status.objects.get(slug="active")

        # 8 IPs
        requests = [{"description": f"Test IP {i}", "status": status_active.pk} for i in range(1, 9)]
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        logging.disable(logging.ERROR)
        self._do_parallel_requests(url, requests)
        logging.disable(logging.NOTSET)
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

    @classmethod
    def setUpTestData(cls):
        cls.statuses = Status.objects.get_for_model(IPAddress)
        cls.create_data = [
            {
                "address": "192.168.0.4/24",
                "status": cls.statuses[0].pk,
            },
            {
                "address": "2001:db8:abcd:12::20/128",
                "status": cls.statuses[0].pk,
            },
            {
                "address": "192.168.0.6/24",
                "status": cls.statuses[0].pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "New description",
            "status": cls.statuses[1].pk,
        }

    def test_create_invalid_address(self):
        """Pass various invalid inputs and confirm they are rejected cleanly."""
        self.add_permissions("ipam.add_ipaddress")

        for bad_address in ("", "192.168.0.0.100/24", "192.168.0.0/35", "2001:db8:1:2:3:4:5:6:7:8/64"):
            response = self.client.post(
                self._get_list_url(),
                {"address": bad_address, "status": self.statuses[0].pk},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertIn("address", response.data)

    def test_create_multiple_outside_nat_success(self):
        """Validate NAT inside address can tie to multiple NAT outside addresses."""
        # Create the two outside NAT IP Addresses tied back to the single inside NAT address
        self.add_permissions("ipam.add_ipaddress")
        self.add_permissions("ipam.view_ipaddress")
        nat_inside = IPAddress.objects.filter(nat_outside_list__isnull=True).first()
        # Create NAT outside with above address IP as inside NAT
        ip1 = self.client.post(
            self._get_list_url(),
            {"address": "192.0.2.1/24", "nat_inside": nat_inside.pk, "status": self.statuses[0].pk},
            format="json",
            **self.header,
        )
        self.assertHttpStatus(ip1, status.HTTP_201_CREATED)
        ip2 = self.client.post(
            self._get_list_url(),
            {"address": "192.0.2.2/24", "nat_inside": nat_inside.pk, "status": self.statuses[0].pk},
            format="json",
            **self.header,
        )
        self.assertHttpStatus(ip2, status.HTTP_201_CREATED)

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


class VLANTest(APIViewTestCases.APIViewTestCase):
    model = VLAN
    brief_fields = ["display", "id", "name", "url", "vid"]
    choices_fields = []

    @classmethod
    def setUpTestData(cls):

        statuses = Status.objects.get_for_model(VLAN)
        vlan_groups = VLANGroup.objects.filter(location__isnull=False)[:2]

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `core.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "vid": 4,
                "name": "VLAN 4 with a name much longer than 64 characters to verify that we increased the limit",
                "vlan_group": vlan_groups[0].pk,
                "status": statuses[0].pk,
                "location": vlan_groups[0].location.pk,
            },
            {
                "vid": 5,
                "name": "VLAN 5",
                "vlan_group": vlan_groups[0].pk,
                "status": statuses[0].pk,
                "location": vlan_groups[0].location.pk,
            },
            {
                "vid": 6,
                "name": "VLAN 6",
                "vlan_group": vlan_groups[0].pk,
                "status": statuses[0].pk,
                "location": vlan_groups[0].location.pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "New description",
            "status": statuses[1].pk,
        }

    def test_delete_vlan_with_prefix(self):
        """
        Attempt and fail to delete a VLAN with a Prefix assigned to it.
        """
        vlan = VLAN.objects.filter(prefixes__isnull=False).first()

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
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()

        devices = (
            Device.objects.create(
                name="Device 1",
                location=location,
                device_type=devicetype,
                role=devicerole,
            ),
            Device.objects.create(
                name="Device 2",
                location=location,
                device_type=devicetype,
                role=devicerole,
            ),
        )
        cls.devices = devices

        Service.objects.create(
            device=devices[0],
            name="Service 1",
            protocol=choices.ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[1],
        )
        Service.objects.create(
            device=devices[0],
            name="Service 2",
            protocol=choices.ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[2],
        )
        Service.objects.create(
            device=devices[0],
            name="Service 3",
            protocol=choices.ServiceProtocolChoices.PROTOCOL_TCP,
            ports=[3],
        )

        cls.create_data = [
            {
                "device": devices[1].pk,
                "name": "Service 4",
                "protocol": choices.ServiceProtocolChoices.PROTOCOL_TCP,
                "ports": [4],
            },
            {
                "device": devices[1].pk,
                "name": "Service 5",
                "protocol": choices.ServiceProtocolChoices.PROTOCOL_TCP,
                "ports": [5],
            },
            {
                "device": devices[1].pk,
                "name": "Service 6",
                "protocol": choices.ServiceProtocolChoices.PROTOCOL_TCP,
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
