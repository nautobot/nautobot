from concurrent.futures.thread import ThreadPoolExecutor
import json
from random import shuffle
from unittest import skip

from django.contrib.contenttypes.models import ContentType
from django.db import connection
from django.db.models import Count
from django.urls import reverse
from rest_framework import status

from nautobot.core.testing import APITestCase, APIViewTestCases, disable_warnings
from nautobot.core.testing.api import APITransactionTestCase
from nautobot.dcim.choices import InterfaceTypeChoices
from nautobot.dcim.models import Device, DeviceType, Interface, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.ipam import choices
from nautobot.ipam.factory import VLANGroupFactory
from nautobot.ipam.models import (
    IPAddress,
    IPAddressToInterface,
    Namespace,
    Prefix,
    PrefixLocationAssignment,
    RIR,
    RouteTarget,
    Service,
    VLAN,
    VLANGroup,
    VLANLocationAssignment,
    VRF,
    VRFDeviceAssignment,
    VRFPrefixAssignment,
)
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine, VMInterface


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("ipam-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class NamespaceTest(APIViewTestCases.APIViewTestCase):
    model = Namespace

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.first()
        cls.create_data = [
            {
                "name": "Purple Monkey Namesapce 1",
                "description": "A perfectly cromulent namespace.",
                "location": location.pk,
            },
            {
                "name": "Purple Monkey Namesapce 2",
                "description": "A secondarily cromulent namespace.",
                "location": location.pk,
            },
            {
                "name": "Purple Monkey Namesapce 3",
                "description": "A third cromulent namespace.",
                "location": location.pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "A perfectly new description.",
        }

    def get_deletable_object_pks(self):
        namespaces = [
            Namespace.objects.create(name="Deletable Namespace 1"),
            Namespace.objects.create(name="Deletable Namespace 2"),
            Namespace.objects.create(name="Deletable Namespace 3"),
        ]
        return [ns.pk for ns in namespaces]


class VRFTest(APIViewTestCases.APIViewTestCase):
    model = VRF

    @classmethod
    def setUpTestData(cls):
        namespace = Namespace.objects.first()
        cls.create_data = [
            {
                "namespace": namespace.pk,
                "name": "VRF 4",
                "rd": "65000:4",
            },
            {
                "namespace": namespace.pk,
                "name": "VRF 5",
                "rd": "65000:5",
            },
            {
                "name": "VRF 6",
                "rd": "65000:6",
            },
        ]
        cls.bulk_update_data = {
            "description": "New description",
        }


class VRFDeviceAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = VRFDeviceAssignment

    @classmethod
    def setUpTestData(cls):
        cls.vrfs = VRF.objects.all()
        cls.devices = Device.objects.all()
        locations = Location.objects.filter(location_type__name="Campus")
        cluster_type = ClusterType.objects.create(name="Test Cluster Type")
        clusters = (
            Cluster.objects.create(name="Cluster 1", cluster_type=cluster_type, location=locations[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=cluster_type, location=locations[1]),
            Cluster.objects.create(name="Cluster 3", cluster_type=cluster_type, location=locations[2]),
        )
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        vm_role = Role.objects.get_for_model(VirtualMachine).first()

        cls.test_vm = VirtualMachine.objects.create(
            cluster=clusters[0],
            name="VM 1",
            role=vm_role,
            status=vm_status,
        )
        VRFDeviceAssignment.objects.create(
            vrf=cls.vrfs[0],
            device=cls.devices[0],
            rd="65000:1",
        )
        VRFDeviceAssignment.objects.create(
            vrf=cls.vrfs[0],
            device=cls.devices[1],
            rd="65000:2",
        )
        VRFDeviceAssignment.objects.create(
            vrf=cls.vrfs[0],
            virtual_machine=cls.test_vm,
            rd="65000:3",
        )
        VRFDeviceAssignment.objects.create(
            vrf=cls.vrfs[1],
            virtual_machine=cls.test_vm,
            rd="65000:4",
        )

        cls.create_data = [
            {
                "vrf": cls.vrfs[2].pk,
                "device": cls.devices[4].pk,
                "virtual_machine": None,
                "rd": "65000:4",
            },
            {
                "vrf": cls.vrfs[3].pk,
                "device": None,
                "virtual_machine": cls.test_vm.pk,
                "rd": "65000:5",
            },
            {
                "vrf": cls.vrfs[4].pk,
                "device": cls.devices[6].pk,
                "virtual_machine": None,
                "rd": "65000:6",
            },
        ]
        cls.bulk_update_data = {
            "rd": "65000:7",
        }

    def test_creating_invalid_vrf_device_assignments(self):
        # Add object-level permission
        duplicate_device_create_data = {
            "vrf": self.vrfs[0].pk,
            "device": self.devices[1].pk,
            "virtual_machine": None,
            "rd": "65000:6",
        }
        duplicate_vm_create_data = {
            "vrf": self.vrfs[1].pk,
            "device": None,
            "virtual_machine": self.test_vm.pk,
            "rd": "65000:6",
        }
        invalid_create_data = {
            "vrf": self.vrfs[2].pk,
            "device": self.devices[6].pk,
            "virtual_machine": self.test_vm.pk,
            "rd": "65000:6",
        }
        self.add_permissions("ipam.add_vrfdeviceassignment")
        response = self.client.post(self._get_list_url(), duplicate_device_create_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The fields device, vrf must make a unique set.", str(response.content))
        response = self.client.post(self._get_list_url(), duplicate_vm_create_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The fields virtual_machine, vrf must make a unique set.", str(response.content))
        response = self.client.post(self._get_list_url(), invalid_create_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("A VRF cannot be associated with both a device and a virtual machine.", str(response.content))


class VRFPrefixAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = VRFPrefixAssignment

    @classmethod
    def setUpTestData(cls):
        cls.vrfs = VRF.objects.all()
        cls.prefixes = Prefix.objects.all()

        VRFPrefixAssignment.objects.create(
            vrf=cls.vrfs[0],
            prefix=cls.prefixes.filter(namespace=cls.vrfs[0].namespace)[0],
        )
        VRFPrefixAssignment.objects.create(
            vrf=cls.vrfs[0],
            prefix=cls.prefixes.filter(namespace=cls.vrfs[0].namespace)[1],
        )
        VRFPrefixAssignment.objects.create(
            vrf=cls.vrfs[1],
            prefix=cls.prefixes.filter(namespace=cls.vrfs[1].namespace)[0],
        )
        VRFPrefixAssignment.objects.create(
            vrf=cls.vrfs[1],
            prefix=cls.prefixes.filter(namespace=cls.vrfs[1].namespace)[1],
        )
        cls.create_data = [
            {
                "vrf": cls.vrfs[2].pk,
                "prefix": cls.prefixes.filter(namespace=cls.vrfs[2].namespace)[0].pk,
            },
            {
                "vrf": cls.vrfs[3].pk,
                "prefix": cls.prefixes.filter(namespace=cls.vrfs[3].namespace)[0].pk,
            },
            {
                "vrf": cls.vrfs[4].pk,
                "prefix": cls.prefixes.filter(namespace=cls.vrfs[4].namespace)[0].pk,
            },
        ]

    def test_creating_invalid_vrf_prefix_assignments(self):
        duplicate_create_data = {
            "vrf": self.vrfs[0].pk,
            "prefix": self.prefixes.filter(namespace=self.vrfs[0].namespace)[0].pk,
        }
        wrong_namespace_create_data = {
            "vrf": self.vrfs[0].pk,
            "prefix": self.prefixes.exclude(namespace=self.vrfs[0].namespace)[0].pk,
        }
        missing_field_create_data = {
            "vrf": self.vrfs[0].pk,
            "prefix": None,
        }
        self.add_permissions("ipam.add_vrfprefixassignment")
        response = self.client.post(self._get_list_url(), duplicate_create_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("The fields vrf, prefix must make a unique set.", str(response.content))
        response = self.client.post(self._get_list_url(), wrong_namespace_create_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Prefix must be in same namespace as VRF", str(response.content))
        response = self.client.post(self._get_list_url(), missing_field_create_data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("This field may not be null.", str(response.content))


class RouteTargetTest(APIViewTestCases.APIViewTestCase):
    model = RouteTarget
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
    create_data = [
        {
            "name": "RIR 4",
        },
        {
            "name": "RIR 5",
        },
        {
            "name": "RIR 6",
        },
        {
            "name": "RIR 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

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
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        rir = RIR.objects.filter(is_private=False).first()
        cls.namespace = Namespace.objects.first()
        cls.statuses = Status.objects.get_for_model(Prefix)
        cls.status = cls.statuses[0]
        cls.locations = Location.objects.get_for_model(Prefix)
        cls.create_data = [
            {
                "prefix": "192.168.4.0/24",
                "status": cls.status.pk,
                "rir": rir.pk,
                "type": choices.PrefixTypeChoices.TYPE_POOL,
                "namespace": cls.namespace.pk,
            },
            {
                "prefix": "2001:db8:abcd:12::/80",
                "status": cls.status.pk,
                "rir": rir.pk,
                "type": choices.PrefixTypeChoices.TYPE_NETWORK,
                "namespace": cls.namespace.pk,
            },
            {
                "prefix": "192.168.6.0/24",
                "status": cls.status.pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "New description",
            "status": cls.statuses[0].pk,
        }
        cls.choices_fields = ["type"]

    def test_legacy_api_behavior(self):
        """
        Tests for the 2.0/2.1 REST API of Prefixes.
        """
        self.add_permissions("ipam.view_prefix", "ipam.add_prefix", "ipam.change_prefix")

        with self.subTest("valid GET"):
            prefix = Prefix.objects.annotate(location_count=Count("locations")).filter(location_count=1).first()
            self.assertIsNotNone(prefix)
            url = reverse("ipam-api:prefix-detail", kwargs={"pk": prefix.pk})
            response = self.client.get(f"{url}?api_version=2.1", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(response.data["location"]["id"], prefix.location.pk)

        with self.subTest("invalid GET"):
            prefix = Prefix.objects.annotate(location_count=Count("locations")).filter(location_count__gt=1).first()
            self.assertIsNotNone(prefix)
            url = reverse("ipam-api:prefix-detail", kwargs={"pk": prefix.pk})
            response = self.client.get(f"{url}?api_version=2.1", **self.header)
            self.assertHttpStatus(response, status.HTTP_412_PRECONDITION_FAILED)
            self.assertEqual(
                str(response.data["detail"]),
                "This object has multiple Locations and so cannot be represented in the 2.0 or 2.1 REST API. "
                "Please correct the data or use a later API version.",
            )

        with self.subTest("valid POST"):
            url = reverse("ipam-api:prefix-list")
            data = {**self.create_data[0]}
            data["location"] = self.locations[0].pk
            response = self.client.post(f"{url}?api_version=2.1", data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertTrue(Prefix.objects.filter(pk=response.data["id"]).exists())

        with self.subTest("valid PATCH"):
            prefix = Prefix.objects.annotate(locations_count=Count("locations")).filter(locations_count=1).first()
            self.assertIsNotNone(prefix)
            url = reverse("ipam-api:prefix-detail", kwargs={"pk": prefix.pk})
            data = {"location": self.locations[0].pk}
            response = self.client.patch(f"{url}?api_version=2.1", data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(response.data["location"]["id"], data["location"])

        with self.subTest("invalid PATCH"):
            prefix = Prefix.objects.annotate(locations_count=Count("locations")).filter(locations_count__gt=1).first()
            url = reverse("ipam-api:prefix-detail", kwargs={"pk": prefix.pk})
            data = {**self.create_data[0]}
            data["location"] = self.locations[0].pk
            response = self.client.patch(f"{url}?api_version=2.1", data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_412_PRECONDITION_FAILED)
            self.assertEqual(
                str(response.data["detail"]),
                "This object has multiple Locations and so cannot be represented in the 2.0 or 2.1 REST API. "
                "Please correct the data or use a later API version.",
            )

    def test_list_available_prefixes(self):
        """
        Test retrieval of all available prefixes within a parent prefix.
        """
        prefix = (
            Prefix.objects.filter(ip_version=6)
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
        for instance in Prefix.objects.filter(children__isnull=True):
            if instance.prefix.size > 2:
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
                "namespace": self.namespace.pk,
                "status": self.status.pk,
                "description": f"Test Prefix {i + 1}",
            }
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertEqual(response.data["prefix"], str(prefixes_to_be_created[i]))
            self.assertEqual(str(response.data["namespace"]["url"]), self.absolute_api_url(prefix.namespace))
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
        for instance in Prefix.objects.filter(children__isnull=True):
            if instance.prefix.size > 2:
                prefix = instance
                break
        else:
            self.fail("Suitable prefix fixture not found")

        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_prefix")

        # Try to create five prefixes (only four are available)
        child_prefix_length = prefix.prefix_length + 2
        data = [
            {
                "prefix_length": child_prefix_length,
                "description": "Test Prefix 1",
                "namespace": self.namespace.pk,
                "status": self.status.pk,
            },
            {
                "prefix_length": child_prefix_length,
                "description": "Test Prefix 2",
                "namespace": self.namespace.pk,
                "status": self.status.pk,
            },
            {
                "prefix_length": child_prefix_length,
                "description": "Test Prefix 3",
                "namespace": self.namespace.pk,
                "status": self.status.pk,
            },
            {
                "prefix_length": child_prefix_length,
                "description": "Test Prefix 4",
                "namespace": self.namespace.pk,
                "status": self.status.pk,
            },
            {
                "prefix_length": child_prefix_length,
                "description": "Test Prefix 5",
                "namespace": self.namespace.pk,
                "status": self.status.pk,
            },
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
            prefix="192.0.2.0/29",
            type=choices.PrefixTypeChoices.TYPE_POOL,
            namespace=self.namespace,
            status=self.status,
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
        prefix = Prefix.objects.create(
            prefix="192.0.2.0/29",
            namespace=self.namespace,
            type=choices.PrefixTypeChoices.TYPE_NETWORK,
            status=self.status,
        )
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_ipaddress", "extras.view_status")

        # Create all six available IPs with individual requests
        for i in range(1, 7):
            data = {
                "description": f"Test IP {i}",
                "namespace": self.namespace.pk,
                "status": self.status.pk,
            }
            response = self.client.post(url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertEqual(str(response.data["parent"]["url"]), self.absolute_api_url(prefix))
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
            prefix="192.0.2.0/29",
            type=choices.PrefixTypeChoices.TYPE_NETWORK,
            namespace=self.namespace,
            status=self.status,
        )
        url = reverse("ipam-api:prefix-available-ips", kwargs={"pk": prefix.pk})
        self.add_permissions("ipam.view_prefix", "ipam.add_ipaddress", "extras.view_status")

        # Try to create seven IPs (only six are available)
        data = [
            {"description": f"Test IP {i}", "namespace": self.namespace.pk, "status": self.status.pk}
            for i in range(1, 8)
        ]  # 7 IPs
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_204_NO_CONTENT)
        self.assertIn("detail", response.data)

        # Create all six available IPs in a single request
        data = [
            {"description": f"Test IP {i}", "namespace": self.namespace.pk, "status": self.status.pk}
            for i in range(1, 7)
        ]  # 6 IPs
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), 6)


class PrefixLocationAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = PrefixLocationAssignment

    @classmethod
    def setUpTestData(cls):
        cls.prefixes = Prefix.objects.filter(locations__isnull=False)
        cls.locations = Location.objects.filter(location_type__content_types=ContentType.objects.get_for_model(Prefix))
        locations_without_prefix = cls.locations.exclude(prefixes__in=[cls.prefixes[0], cls.prefixes[1]])

        cls.create_data = [
            {
                "prefix": cls.prefixes[0].pk,
                "location": locations_without_prefix[1].pk,
            },
            {
                "prefix": cls.prefixes[0].pk,
                "location": locations_without_prefix[2].pk,
            },
            {
                "prefix": cls.prefixes[1].pk,
                "location": locations_without_prefix[3].pk,
            },
            {
                "prefix": cls.prefixes[1].pk,
                "location": locations_without_prefix[4].pk,
            },
        ]


class ParallelPrefixTest(APITransactionTestCase):
    """
    Adapted from https://github.com/netbox-community/netbox/pull/3726
    """

    def setUp(self):
        super().setUp()
        self.namespace = Namespace.objects.create(name="Turtles", description="All the way down.")
        self.status = Status.objects.get_for_model(Prefix).first()

    def test_create_multiple_available_prefixes_parallel(self):
        prefix = Prefix.objects.create(
            prefix="192.0.2.0/28",
            type=choices.PrefixTypeChoices.TYPE_POOL,
            namespace=self.namespace,
            status=self.status,
        )

        # 5 Prefixes
        requests = [
            {
                "prefix_length": 30,
                "description": f"Test Prefix {i}",
                "namespace": self.namespace.pk,
                "status": self.status.pk,
            }
            for i in range(1, 6)
        ]
        url = reverse("ipam-api:prefix-available-prefixes", kwargs={"pk": prefix.pk})
        self._do_parallel_requests(url, requests)

        prefixes = [str(o) for o in Prefix.objects.filter(prefix_length=30).all()]
        self.assertEqual(len(prefixes), len(set(prefixes)), "Duplicate prefixes should not exist")

    def test_create_multiple_available_ips_parallel(self):
        prefix = Prefix.objects.create(
            prefix="192.0.2.0/29",
            type=choices.PrefixTypeChoices.TYPE_POOL,
            namespace=self.namespace,
            status=self.status,
        )

        # 8 IPs
        requests = [
            {"description": f"Test IP {i}", "namespace": self.namespace.pk, "status": self.status.pk}
            for i in range(1, 9)
        ]
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

    choices_fields = ["type"]

    # Namespace is a write-only field.
    validation_excluded_fields = ["namespace"]

    @classmethod
    def setUpTestData(cls):
        cls.statuses = Status.objects.get_for_model(IPAddress)
        cls.namespace = Namespace.objects.first()
        pfx_status = Status.objects.get_for_model(Prefix).first()
        parent4 = Prefix.objects.create(prefix="192.168.0.0/24", status=pfx_status, namespace=cls.namespace)
        parent6 = Prefix.objects.create(prefix="2001:db8:abcd:12::/64", status=pfx_status, namespace=cls.namespace)

        # Generic `test_update_object()` will grab the first object, so we're aligning this
        # update_data with that to make sure that it has a valid parent.
        first_ip = IPAddress.objects.first()
        cls.update_data = {
            "address": str(first_ip),
            "namespace": cls.namespace.pk,
            "status": cls.statuses[0].pk,
        }

        # Intermix `namespace` and `parent` arguments for create to assert either will work.
        cls.create_data = [
            {
                "address": "192.168.0.4/24",
                "namespace": cls.namespace.pk,
                "status": cls.statuses[0].pk,
            },
            {
                "address": "2001:db8:abcd:12::20/128",
                "parent": parent6.pk,
                "status": cls.statuses[0].pk,
            },
            {
                "address": "192.168.0.6/24",
                "parent": parent4.pk,
                "status": cls.statuses[0].pk,
            },
        ]
        cls.bulk_update_data = {
            "description": "New description",
            "status": cls.statuses[1].pk,
        }

    def test_create_requires_parent_or_namespace(self):
        """Test that missing parent/namespace fields result in an error."""
        self.add_permissions("ipam.add_ipaddress")
        data = {
            "address": "192.168.0.10/32",
            "status": self.statuses[0].pk,
        }
        response = self.client.post(
            self._get_list_url(),
            data,
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("__all__", response.data)

    def test_create_invalid_address(self):
        """Pass various invalid inputs and confirm they are rejected cleanly."""
        self.add_permissions("ipam.add_ipaddress")

        for bad_address in ("", "192.168.0.0.100/24", "192.168.0.0/35", "2001:db8:1:2:3:4:5:6:7:8/64"):
            response = self.client.post(
                self._get_list_url(),
                {"address": bad_address, "status": self.statuses[0].pk, "namespace": self.namespace.pk},
                format="json",
                **self.header,
            )
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertIn("address", response.data)

    def test_create_multiple_outside_nat_success(self):
        """Validate NAT inside address can tie to multiple NAT outside addresses."""
        # Create the two outside NAT IP Addresses tied back to the single inside NAT address
        self.add_permissions("ipam.add_ipaddress", "ipam.view_ipaddress")
        nat_inside = IPAddress.objects.filter(nat_outside_list__isnull=True).first()
        # Create NAT outside with above address IP as inside NAT
        ip1 = self.client.post(
            self._get_list_url(),
            {
                "address": "192.168.0.19/24",
                "nat_inside": nat_inside.pk,
                "status": self.statuses[0].pk,
                "namespace": self.namespace.pk,
            },
            format="json",
            **self.header,
        )
        self.assertHttpStatus(ip1, status.HTTP_201_CREATED)
        ip2 = self.client.post(
            self._get_list_url(),
            {
                "address": "192.168.0.20/24",
                "nat_inside": nat_inside.pk,
                "status": self.statuses[0].pk,
                "namespace": self.namespace.pk,
            },
            format="json",
            **self.header,
        )
        self.assertHttpStatus(ip2, status.HTTP_201_CREATED)

        response = self.client.get(
            self._get_detail_url(nat_inside) + "?depth=1",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["nat_outside_list"][0]["address"], "192.168.0.19/24")
        self.assertEqual(response.data["nat_outside_list"][1]["address"], "192.168.0.20/24")

    def test_creating_ipaddress_with_an_invalid_parent(self):
        self.add_permissions("ipam.add_ipaddress")
        prefixes = (
            Prefix.objects.create(prefix="10.0.0.0/8", status=self.statuses[0], namespace=self.namespace),
            Prefix.objects.create(prefix="192.168.0.0/25", status=self.statuses[0], namespace=self.namespace),
        )
        nat_inside = IPAddress.objects.filter(nat_outside_list__isnull=True).first()
        data = {
            "address": "192.168.0.10/32",
            "nat_inside": nat_inside.pk,
            "status": self.statuses[0].pk,
            "namespace": self.namespace.pk,
            "parent": prefixes[0].pk,
        }

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        expected_err_msg = (
            f"{prefixes[0]} cannot be assigned as the parent of {data['address']}. "
            f" In namespace {self.namespace}, the expected parent would be {prefixes[1]}."
        )
        self.assertEqual(response.data["parent"], [expected_err_msg])


class IPAddressToInterfaceTest(APIViewTestCases.APIViewTestCase):
    model = IPAddressToInterface
    update_data = {"is_destination": True, "is_preferred": True}
    bulk_update_data = {"is_default": True, "is_source": True}

    @classmethod
    def setUpTestData(cls):
        ip_addresses = list(IPAddress.objects.all()[:6])
        location = Location.objects.get_for_model(Device).first()
        devicetype = DeviceType.objects.first()
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        device = Device.objects.create(
            name="Device 1",
            location=location,
            device_type=devicetype,
            role=devicerole,
            status=devicestatus,
        )
        int_status = Status.objects.get_for_model(Interface).first()
        int_type = InterfaceTypeChoices.TYPE_1GE_FIXED
        interfaces = [
            Interface.objects.create(device=device, name="eth0", status=int_status, type=int_type),
            Interface.objects.create(device=device, name="eth1", status=int_status, type=int_type),
            Interface.objects.create(device=device, name="eth2", status=int_status, type=int_type),
            Interface.objects.create(device=device, name="eth3", status=int_status, type=int_type),
        ]

        clustertype = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(cluster_type=clustertype, name="Cluster 1")
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        virtual_machine = (VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster, status=vm_status),)
        vm_int_status = Status.objects.get_for_model(VMInterface).first()
        vm_interfaces = [
            VMInterface.objects.create(virtual_machine=virtual_machine[0], name="veth0", status=vm_int_status),
            VMInterface.objects.create(virtual_machine=virtual_machine[0], name="veth1", status=vm_int_status),
        ]

        IPAddressToInterface.objects.create(ip_address=ip_addresses[0], interface=interfaces[0], vm_interface=None)
        IPAddressToInterface.objects.create(ip_address=ip_addresses[1], interface=interfaces[1], vm_interface=None)
        IPAddressToInterface.objects.create(ip_address=ip_addresses[2], interface=None, vm_interface=vm_interfaces[0])

        cls.create_data = [
            {
                "ip_address": ip_addresses[3].pk,
                "interface": interfaces[2].pk,
                "vm_interface": None,
            },
            {
                "ip_address": ip_addresses[4].pk,
                "interface": interfaces[3].pk,
                "vm_interface": None,
            },
            {
                "ip_address": ip_addresses[5].pk,
                "interface": None,
                "vm_interface": vm_interfaces[1].pk,
            },
        ]


class VLANGroupTest(APIViewTestCases.APIViewTestCase):
    model = VLANGroup
    create_data = [
        {
            "name": "VLAN Group 4",
        },
        {
            "name": "VLAN Group 5",
        },
        {
            "name": "VLAN Group 6",
        },
        {
            "name": "VLAN Group 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    def get_deletable_object(self):
        return VLANGroup.objects.create(name="DELETE ME")

    def get_deletable_object_pks(self):
        vlangroups = VLANGroupFactory.create_batch(size=3)
        return [vg.pk for vg in vlangroups]


class VLANTest(APIViewTestCases.APIViewTestCase):
    model = VLAN
    choices_fields = []
    validation_excluded_fields = ["location"]

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(VLAN)
        vlan_groups = VLANGroup.objects.filter(location__isnull=False)[:2]
        cls.locations = Location.objects.filter(location_type__content_types=ContentType.objects.get_for_model(VLAN))

        cls.create_data = [
            {
                "vid": 4,
                "name": "VLAN 4 with a name much longer than 64 characters to verify that we increased the limit",
                "vlan_group": vlan_groups[0].pk,
                "status": statuses[0].pk,
            },
            {
                "vid": 5,
                "name": "VLAN 5",
                "vlan_group": vlan_groups[0].pk,
                "status": statuses[0].pk,
            },
            {
                "vid": 6,
                "name": "VLAN 6",
                "vlan_group": vlan_groups[0].pk,
                "status": statuses[0].pk,
                "location": cls.locations[3].pk,
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

    def test_vlan_2_1_api_version_response(self):
        """Assert location can be used in VLAN API create/retrieve."""

        self.add_permissions("ipam.view_vlan")
        self.add_permissions("ipam.add_vlan")
        self.add_permissions("ipam.change_vlan")
        with self.subTest("Assert GET"):
            vlan = VLAN.objects.annotate(locations_count=Count("locations")).filter(locations_count=1).first()
            url = reverse("ipam-api:vlan-detail", kwargs={"pk": vlan.pk})
            response = self.client.get(f"{url}?api_version=2.1", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(response.data["location"]["id"], vlan.location.pk)

        with self.subTest("Assert GET with multiple location"):
            vlan = VLAN.objects.annotate(locations_count=Count("locations")).filter(locations_count__gt=1).first()
            url = reverse("ipam-api:vlan-detail", kwargs={"pk": vlan.pk})
            response = self.client.get(f"{url}?api_version=2.1", **self.header)
            self.assertHttpStatus(response, status.HTTP_412_PRECONDITION_FAILED)
            self.assertEqual(
                str(response.data["detail"]),
                "This object has multiple Locations and so cannot be represented in the 2.0 or 2.1 REST API. "
                "Please correct the data or use a later API version.",
            )

        with self.subTest("Assert CREATE"):
            url = reverse("ipam-api:vlan-list")
            data = {**self.create_data[0]}
            data["location"] = self.locations[0].pk
            response = self.client.post(f"{url}?api_version=2.1", data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_201_CREATED)
            self.assertTrue(VLAN.objects.filter(pk=response.data["id"]).exists())

        with self.subTest("Assert UPDATE on multiple locations ERROR"):
            vlan = VLAN.objects.annotate(locations_count=Count("locations")).filter(locations_count__gt=1).first()
            url = reverse("ipam-api:vlan-detail", kwargs={"pk": vlan.pk})
            data = {**self.create_data[0]}
            data["vid"] = 19
            data["location"] = self.locations[0].pk
            data.pop("vlan_group")
            response = self.client.patch(f"{url}?api_version=2.1", data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_412_PRECONDITION_FAILED)
            self.assertEqual(
                str(response.data["detail"]),
                "This object has multiple Locations and so cannot be represented in the 2.0 or 2.1 REST API. "
                "Please correct the data or use a later API version.",
            )

        with self.subTest("Assert UPDATE on single location"):
            vlan = VLAN.objects.annotate(locations_count=Count("locations")).filter(locations_count=1).first()
            url = reverse("ipam-api:vlan-detail", kwargs={"pk": vlan.pk})
            data = {"location": self.locations[0].pk}
            response = self.client.patch(f"{url}?api_version=2.1", data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
            self.assertEqual(response.data["location"]["id"], data["location"])


class VLANLocationAssignmentTest(APIViewTestCases.APIViewTestCase):
    model = VLANLocationAssignment

    @classmethod
    def setUpTestData(cls):
        cls.vlans = VLAN.objects.filter(locations__isnull=False)
        cls.locations = Location.objects.filter(location_type__content_types=ContentType.objects.get_for_model(VLAN))
        locations_without_vlans = cls.locations.exclude(vlans__in=[cls.vlans[0], cls.vlans[1]])

        cls.create_data = [
            {
                "vlan": cls.vlans[0].pk,
                "location": locations_without_vlans[1].pk,
            },
            {
                "vlan": cls.vlans[0].pk,
                "location": locations_without_vlans[2].pk,
            },
            {
                "vlan": cls.vlans[1].pk,
                "location": locations_without_vlans[3].pk,
            },
            {
                "vlan": cls.vlans[1].pk,
                "location": locations_without_vlans[4].pk,
            },
        ]


class ServiceTest(APIViewTestCases.APIViewTestCase):
    model = Service
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["protocol"]

    @classmethod
    def setUpTestData(cls):
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
        data["name"] = "http-1"
        data["ports"] = expected
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.json()["ports"], expected)

    # TODO: Unskip after resolving #2908, #2909
    @skip("DRF's built-in OrderingFilter triggering natural key attribute error in our base")
    def test_list_objects_ascending_ordered(self):
        pass

    @skip("DRF's built-in OrderingFilter triggering natural key attribute error in our base")
    def test_list_objects_descending_ordered(self):
        pass
