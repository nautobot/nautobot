from django.urls import reverse
from rest_framework import status

from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.extras.models import ConfigContextSchema, Status
from nautobot.ipam.models import VLAN
from nautobot.utilities.testing import APITestCase, APIViewTestCases
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
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class ClusterTypeTest(APIViewTestCases.APIViewTestCase):
    model = ClusterType
    brief_fields = ["cluster_count", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Cluster Type 4",
            "slug": "cluster-type-4",
        },
        {
            "name": "Cluster Type 5",
            "slug": "cluster-type-5",
        },
        {
            "name": "Cluster Type 6",
            "slug": "cluster-type-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2")
        ClusterType.objects.create(name="Cluster Type 3", slug="cluster-type-3")


class ClusterGroupTest(APIViewTestCases.APIViewTestCase):
    model = ClusterGroup
    brief_fields = ["cluster_count", "display", "id", "name", "slug", "url"]
    create_data = [
        {
            "name": "Cluster Group 4",
            "slug": "cluster-type-4",
        },
        {
            "name": "Cluster Group 5",
            "slug": "cluster-type-5",
        },
        {
            "name": "Cluster Group 6",
            "slug": "cluster-type-6",
        },
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-type-1")
        ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-type-2")
        ClusterGroup.objects.create(name="Cluster Group 3", slug="cluster-type-3")


class ClusterTest(APIViewTestCases.APIViewTestCase):
    model = Cluster
    brief_fields = ["display", "id", "name", "url", "virtualmachine_count"]
    bulk_update_data = {
        "comments": "New comment",
    }

    @classmethod
    def setUpTestData(cls):

        cluster_types = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2"),
        )

        cluster_groups = (
            ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1"),
            ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-group-2"),
        )

        Cluster.objects.create(name="Cluster 1", type=cluster_types[0], group=cluster_groups[0])
        Cluster.objects.create(name="Cluster 2", type=cluster_types[0], group=cluster_groups[0])
        Cluster.objects.create(name="Cluster 3", type=cluster_types[0], group=cluster_groups[0])

        cls.create_data = [
            {
                "name": "Cluster 4",
                "type": cluster_types[1].pk,
                "group": cluster_groups[1].pk,
            },
            {
                "name": "Cluster 5",
                "type": cluster_types[1].pk,
                "group": cluster_groups[1].pk,
            },
            {
                "name": "Cluster 6",
                "type": cluster_types[1].pk,
                "group": cluster_groups[1].pk,
            },
        ]


class VirtualMachineTest(APIViewTestCases.APIViewTestCase):
    model = VirtualMachine
    brief_fields = ["display", "id", "name", "url"]
    bulk_update_data = {
        "status": "staged",
    }
    choices_fields = ["status"]

    @classmethod
    def setUpTestData(cls):
        clustertype = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        clustergroup = ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1")

        clusters = (
            Cluster.objects.create(name="Cluster 1", type=clustertype, group=clustergroup),
            Cluster.objects.create(name="Cluster 2", type=clustertype, group=clustergroup),
        )

        statuses = Status.objects.get_for_model(VirtualMachine)

        VirtualMachine.objects.create(
            name="Virtual Machine 1",
            cluster=clusters[0],
            local_context_data={"A": 1},
            status=statuses[0],
        ),
        VirtualMachine.objects.create(
            name="Virtual Machine 2",
            cluster=clusters[0],
            local_context_data={"B": 2},
            status=statuses[0],
        ),
        VirtualMachine.objects.create(
            name="Virtual Machine 3",
            cluster=clusters[0],
            local_context_data={"C": 3},
            status=statuses[0],
        ),

        # FIXME(jathan): The writable serializer for `status` takes the
        # status `name` (str) and not the `pk` (int). Do not validate this
        # field right now, since we are asserting that it does create correctly.
        #
        # The test code for `utilities.testing.views.TestCase.model_to_dict()`
        # needs to be enhanced to use the actual API serializers when `api=True`
        cls.validation_excluded_fields = ["status"]

        cls.create_data = [
            {
                "name": "Virtual Machine 4",
                "cluster": clusters[1].pk,
                "status": "active",
            },
            {
                "name": "Virtual Machine 5",
                "cluster": clusters[1].pk,
                "status": "active",
            },
            {
                "name": "Virtual Machine 6",
                "cluster": clusters[1].pk,
                "status": "active",
            },
        ]

    def test_config_context_included_by_default_in_list_view(self):
        """
        Check that config context data is included by default in the virtual machines list.
        """
        virtualmachine = VirtualMachine.objects.first()
        url = "{}?id={}".format(reverse("virtualization-api:virtualmachine-list"), virtualmachine.pk)
        self.add_permissions("virtualization.view_virtualmachine")

        response = self.client.get(url, **self.header)
        self.assertEqual(response.data["results"][0].get("config_context", {}).get("A"), 1)

    def test_config_context_excluded(self):
        """
        Check that config context data can be excluded by passing ?exclude=config_context.
        """
        url = reverse("virtualization-api:virtualmachine-list") + "?exclude=config_context"
        self.add_permissions("virtualization.view_virtualmachine")

        response = self.client.get(url, **self.header)
        self.assertFalse("config_context" in response.data["results"][0])

    def test_unique_name_per_cluster_constraint(self):
        """
        Check that creating a virtual machine with a duplicate name fails.
        """
        data = {
            "name": "Virtual Machine 1",
            "cluster": Cluster.objects.first().pk,
            "status": "active",
        }
        url = reverse("virtualization-api:virtualmachine-list")
        self.add_permissions("virtualization.add_virtualmachine")

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_local_context_schema_validation_pass(self):
        """
        Given a config context schema
        And a vm with local context that conforms to that schema
        Assert that the local context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"A": {"type": "integer"}}}
        )
        self.add_permissions("virtualization.change_virtualmachine")

        patch_data = {"local_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(VirtualMachine.objects.get(name="Virtual Machine 1")),
            patch_data,
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["local_context_schema"]["id"], str(schema.pk))

    def test_local_context_schema_schema_validation_fails(self):
        """
        Given a config context schema
        And a vm with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 2", slug="schema-2", data_schema={"type": "object", "properties": {"B": {"type": "string"}}}
        )
        # Add object-level permission
        self.add_permissions("virtualization.change_virtualmachine")

        patch_data = {"local_context_schema": str(schema.pk)}

        response = self.client.patch(
            self._get_detail_url(VirtualMachine.objects.get(name="Virtual Machine 2")),
            patch_data,
            format="json",
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)


class VMInterfaceTest(APIViewTestCases.APIViewTestCase):
    model = VMInterface
    brief_fields = ["display", "id", "name", "url", "virtual_machine"]
    bulk_update_data = {
        "description": "New description",
    }
    choices_fields = ["mode"]

    @classmethod
    def setUpTestData(cls):

        clustertype = ClusterType.objects.create(name="Test Cluster Type 1", slug="test-cluster-type-1")
        cluster = Cluster.objects.create(name="Test Cluster 1", type=clustertype)
        virtualmachine = VirtualMachine.objects.create(cluster=cluster, name="Test VM 1")

        VMInterface.objects.create(virtual_machine=virtualmachine, name="Interface 1")
        VMInterface.objects.create(virtual_machine=virtualmachine, name="Interface 2")
        VMInterface.objects.create(virtual_machine=virtualmachine, name="Interface 3")

        vlans = (
            VLAN.objects.create(name="VLAN 1", vid=1),
            VLAN.objects.create(name="VLAN 2", vid=2),
            VLAN.objects.create(name="VLAN 3", vid=3),
        )

        cls.create_data = [
            {
                "virtual_machine": virtualmachine.pk,
                "name": "Interface 4",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
            {
                "virtual_machine": virtualmachine.pk,
                "name": "Interface 5",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
            {
                "virtual_machine": virtualmachine.pk,
                "name": "Interface 6",
                "mode": InterfaceModeChoices.MODE_TAGGED,
                "tagged_vlans": [vlans[0].pk, vlans[1].pk],
                "untagged_vlan": vlans[2].pk,
            },
        ]
