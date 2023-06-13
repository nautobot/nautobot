from django.urls import reverse
from rest_framework import status

from nautobot.core.testing import APITestCase, APIViewTestCases
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.models import Location, LocationType
from nautobot.extras.models import ConfigContextSchema, Status
from nautobot.ipam.models import VLAN, VLANGroup
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
    VMInterface,
)


class AppTest(APITestCase):
    def test_root(self):
        url = reverse("virtualization-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


class ClusterTypeTest(APIViewTestCases.APIViewTestCase):
    model = ClusterType
    create_data = [
        {
            "name": "Cluster Type 4",
        },
        {
            "name": "Cluster Type 5",
        },
        {
            "name": "Cluster Type 6",
        },
        {
            "name": "Cluster Type 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        ClusterType.objects.create(name="Cluster Type 1")
        ClusterType.objects.create(name="Cluster Type 2")
        ClusterType.objects.create(name="Cluster Type 3")


class ClusterGroupTest(APIViewTestCases.APIViewTestCase):
    model = ClusterGroup
    create_data = [
        {
            "name": "Cluster Group 4",
        },
        {
            "name": "Cluster Group 5",
        },
        {
            "name": "Cluster Group 6",
        },
        {
            "name": "Cluster Group 7",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        ClusterGroup.objects.create(name="Cluster Group 1")
        ClusterGroup.objects.create(name="Cluster Group 2")
        ClusterGroup.objects.create(name="Cluster Group 3")


class ClusterTest(APIViewTestCases.APIViewTestCase):
    model = Cluster
    bulk_update_data = {
        "comments": "New comment",
    }

    @classmethod
    def setUpTestData(cls):
        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1"),
            ClusterType.objects.create(name="Cluster Type 2"),
        )

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1"),
            ClusterGroup.objects.create(name="Cluster Group 2"),
        )

        Cluster.objects.create(name="Cluster 1", cluster_type=cluster_types[0], cluster_group=cluster_groups[0])
        Cluster.objects.create(name="Cluster 2", cluster_type=cluster_types[0], cluster_group=cluster_groups[0])
        Cluster.objects.create(name="Cluster 3", cluster_type=cluster_types[0], cluster_group=cluster_groups[0])

        cls.create_data = [
            {
                "name": "Cluster 4",
                "cluster_type": cluster_types[1].pk,
                "cluster_group": cluster_groups[1].pk,
            },
            {
                "name": "Cluster 5",
                "cluster_type": cluster_types[1].pk,
                "cluster_group": cluster_groups[1].pk,
            },
            {
                "name": "Cluster 6",
                "cluster_type": cluster_types[1].pk,
                "cluster_group": cluster_groups[1].pk,
            },
        ]


class VirtualMachineTest(APIViewTestCases.APIViewTestCase):
    model = VirtualMachine
    choices_fields = []

    @classmethod
    def setUpTestData(cls):
        clustertype = ClusterType.objects.create(
            name="Cluster Type 1",
        )
        clustergroup = ClusterGroup.objects.create(
            name="Cluster Group 1",
        )
        location_type = LocationType.objects.get(name="Campus")
        locations = Location.objects.filter(location_type=location_type)[:2]

        clusters = (
            Cluster.objects.create(
                name="Cluster 1", cluster_type=clustertype, cluster_group=clustergroup, location=locations[0]
            ),
            Cluster.objects.create(
                name="Cluster 2", cluster_type=clustertype, cluster_group=clustergroup, location=locations[1]
            ),
        )

        cls.statuses = Status.objects.get_for_model(VirtualMachine)

        VirtualMachine.objects.create(
            name="Virtual Machine 1",
            cluster=clusters[0],
            local_config_context_data={"A": 1},
            status=cls.statuses[0],
        )
        VirtualMachine.objects.create(
            name="Virtual Machine 2",
            cluster=clusters[0],
            local_config_context_data={"B": 2},
            status=cls.statuses[0],
        )
        VirtualMachine.objects.create(
            name="Virtual Machine 3",
            cluster=clusters[0],
            local_config_context_data={"C": 3},
            status=cls.statuses[0],
        )

        cls.create_data = [
            {
                "name": "Virtual Machine 4",
                "cluster": clusters[1].pk,
                "status": cls.statuses[0].pk,
            },
            {
                "name": "Virtual Machine 5",
                "cluster": clusters[1].pk,
                "status": cls.statuses[0].pk,
            },
            {
                "name": "Virtual Machine 6",
                "cluster": clusters[1].pk,
                "status": cls.statuses[0].pk,
            },
        ]
        cls.bulk_update_data = {
            "status": cls.statuses[1].pk,
        }

    def test_config_context_excluded_by_default_in_list_view(self):
        """
        Check that config context data is excluded by default in the virtual machines list.
        """
        virtualmachine = VirtualMachine.objects.first()
        reverse_url = reverse("virtualization-api:virtualmachine-list")
        url = f"{reverse_url}?id={virtualmachine.pk}"
        self.add_permissions("virtualization.view_virtualmachine")

        response = self.client.get(url, **self.header)
        self.assertNotIn("config_context", response.data["results"][0])

    def test_config_context_included(self):
        """
        Check that config context data can be included by passing ?include=config_context.
        """
        url = reverse("virtualization-api:virtualmachine-list") + "?include=config_context"
        self.add_permissions("virtualization.view_virtualmachine")

        response = self.client.get(url, **self.header)
        self.assertIn("config_context", response.data["results"][0])
        self.assertEqual(response.data["results"][0]["config_context"], {"A": 1})

    def test_unique_name_per_cluster_constraint(self):
        """
        Check that creating a virtual machine with a duplicate name fails.
        """
        data = {
            "name": "Virtual Machine 1",
            "cluster": Cluster.objects.first().pk,
            "status": self.statuses[1].pk,
        }
        url = reverse("virtualization-api:virtualmachine-list")
        self.add_permissions("virtualization.add_virtualmachine")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_local_config_context_schema_validation_pass(self):
        """
        Given a config context schema
        And a vm with local context that conforms to that schema
        Assert that the local context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"A": {"type": "integer"}}}
        )
        self.add_permissions("virtualization.change_virtualmachine")

        patch_data = {"local_config_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(VirtualMachine.objects.get(name="Virtual Machine 1")),
            patch_data,
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(str(response.data["local_config_context_schema"]["url"]), self.absolute_api_url(schema))

    def test_local_config_context_schema_schema_validation_fails(self):
        """
        Given a config context schema
        And a vm with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 2", data_schema={"type": "object", "properties": {"B": {"type": "string"}}}
        )
        # Add object-level permission
        self.add_permissions("virtualization.change_virtualmachine")

        patch_data = {"local_config_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(VirtualMachine.objects.get(name="Virtual Machine 2")),
            patch_data,
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)


class VMInterfaceTest(APIViewTestCases.APIViewTestCase):
    model = VMInterface
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["mode"]

    @classmethod
    def setUpTestData(cls):
        clustertype = ClusterType.objects.create(name="Test Cluster Type 1")
        cluster = Cluster.objects.create(name="Test Cluster 1", cluster_type=clustertype)
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        virtualmachine = VirtualMachine.objects.create(cluster=cluster, name="Test VM 1", status=vm_status)
        cls.interface_status = Status.objects.get_for_model(VMInterface).first()

        interfaces = (
            VMInterface.objects.create(virtual_machine=virtualmachine, name="Interface 1", status=cls.interface_status),
            VMInterface.objects.create(virtual_machine=virtualmachine, name="Interface 2", status=cls.interface_status),
            VMInterface.objects.create(virtual_machine=virtualmachine, name="Interface 3", status=cls.interface_status),
        )

        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroup.objects.first()
        vlans = (
            VLAN.objects.create(name="VLAN 1", vid=1, status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(name="VLAN 2", vid=2, status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(name="VLAN 3", vid=3, status=vlan_status, vlan_group=vlan_group),
        )

        cls.create_data = [
            {
                "virtual_machine": virtualmachine.pk,
                "name": "Interface 4",
                "status": cls.interface_status.pk,
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
            {
                "virtual_machine": virtualmachine.pk,
                "name": "Interface 5",
                "status": cls.interface_status.pk,
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "bridge": interfaces[0].pk,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
            {
                "virtual_machine": virtualmachine.pk,
                "name": "Interface 6",
                "status": cls.interface_status.pk,
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "parent_interface": interfaces[1].pk,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
        ]

        cls.untagged_vlan_data = {
            "virtual_machine": virtualmachine.pk,
            "name": "expected-to-fail",
            "status": cls.interface_status.pk,
            "untagged_vlan": vlans[0].pk,
        }

    def test_untagged_vlan_requires_mode(self):
        """Test that when an `untagged_vlan` is specified, `mode` is also required."""
        self.add_permissions("virtualization.add_vminterface")

        # This will fail.
        url = self._get_list_url()
        self.assertHttpStatus(
            self.client.post(url, self.untagged_vlan_data, format="json", **self.header), status.HTTP_400_BAD_REQUEST
        )

        # Now let's add mode and it will work.
        self.untagged_vlan_data["mode"] = InterfaceModeChoices.MODE_ACCESS
        self.assertHttpStatus(
            self.client.post(url, self.untagged_vlan_data, format="json", **self.header), status.HTTP_201_CREATED
        )

    def test_tagged_vlan_raise_error_if_mode_not_set_to_tagged(self):
        self.add_permissions("virtualization.add_vminterface", "virtualization.change_vminterface")
        vlan = VLAN.objects.get(name="VLAN 1")
        virtualmachine = VirtualMachine.objects.first()
        with self.subTest("On create, assert 400 status."):
            payload = {
                "virtual_machine": virtualmachine.pk,
                "name": "Tagged Interface",
                "status": self.interface_status.pk,
                "tagged_vlans": [vlan.pk],
            }
            response = self.client.post(self._get_list_url(), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["tagged_vlans"][0], "Mode must be set to tagged when specifying tagged_vlans"
            )

        with self.subTest("On update, assert 400 status."):
            # Error
            interface = VMInterface.objects.create(
                virtual_machine=virtualmachine,
                name="VMInterface 1",
                mode=InterfaceModeChoices.MODE_TAGGED,
                status=self.interface_status,
            )
            interface.tagged_vlans.add(vlan)
            payload = {"mode": None, "tagged_vlans": [vlan.pk]}
            response = self.client.patch(self._get_detail_url(interface), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(
                response.data["tagged_vlans"][0], "Mode must be set to tagged when specifying tagged_vlans"
            )

    def test_change_mode_from_tagged_to_others(self):
        self.add_permissions("virtualization.change_vminterface")
        vlan = VLAN.objects.get(name="VLAN 1")
        interface = VMInterface.objects.first()
        interface.mode = InterfaceModeChoices.MODE_TAGGED
        interface.validated_save()
        interface.tagged_vlans.add(vlan)

        with self.subTest("Update Fail"):
            payload = {"mode": InterfaceModeChoices.MODE_ACCESS}
            response = self.client.patch(self._get_detail_url(interface), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data["tagged_vlans"][0], "Clear tagged_vlans to set mode to access")

        with self.subTest("Update Successful"):
            payload = {"mode": InterfaceModeChoices.MODE_ACCESS, "tagged_vlans": []}
            response = self.client.patch(self._get_detail_url(interface), data=payload, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_200_OK)
