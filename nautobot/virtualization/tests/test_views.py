from django.test import override_settings
from django.contrib.contenttypes.models import ContentType
from netaddr import EUI

from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.models import DeviceRole, Platform, Site
from nautobot.extras.models import ConfigContextSchema, CustomField, Status, Tag
from nautobot.ipam.models import VLAN
from nautobot.utilities.testing import ViewTestCases, post_data
from nautobot.virtualization.models import (
    Cluster,
    ClusterGroup,
    ClusterType,
    VirtualMachine,
    VMInterface,
)


class ClusterGroupTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = ClusterGroup

    @classmethod
    def setUpTestData(cls):

        ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1")
        ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-group-2")
        ClusterGroup.objects.create(name="Cluster Group 3", slug="cluster-group-3")
        ClusterGroup.objects.create(name="Cluster Group 8")

        cls.form_data = {
            "name": "Cluster Group X",
            "slug": "cluster-group-x",
            "description": "A new cluster group",
        }

        cls.csv_data = (
            "name,slug,description",
            "Cluster Group 4,cluster-group-4,Fourth cluster group",
            "Cluster Group 5,cluster-group-5,Fifth cluster group",
            "Cluster Group 6,cluster-group-6,Sixth cluster group",
            "Cluster Group 7,,Seventh cluster group",
        )
        cls.slug_source = "name"
        cls.slug_test_object = "Cluster Group 8"


class ClusterTypeTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = ClusterType

    @classmethod
    def setUpTestData(cls):

        ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2")
        ClusterType.objects.create(name="Cluster Type 3", slug="cluster-type-3")
        ClusterType.objects.create(name="Cluster Type 8")

        cls.form_data = {
            "name": "Cluster Type X",
            "slug": "cluster-type-x",
            "description": "A new cluster type",
        }

        cls.csv_data = (
            "name,slug,description",
            "Cluster Type 4,cluster-type-4,Fourth cluster type",
            "Cluster Type 5,cluster-type-5,Fifth cluster type",
            "Cluster Type 6,cluster-type-6,Sixth cluster type",
            "Cluster Type 7,,Seventh cluster type",
        )
        cls.slug_source = "name"
        cls.slug_test_object = "Cluster Type 8"


class ClusterTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Cluster

    @classmethod
    def setUpTestData(cls):

        sites = (
            Site.objects.create(name="Site 1", slug="site-1"),
            Site.objects.create(name="Site 2", slug="site-2"),
        )

        clustergroups = (
            ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1"),
            ClusterGroup.objects.create(name="Cluster Group 2", slug="cluster-group-2"),
        )

        clustertypes = (
            ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1"),
            ClusterType.objects.create(name="Cluster Type 2", slug="cluster-type-2"),
        )

        Cluster.objects.create(
            name="Cluster 1",
            group=clustergroups[0],
            type=clustertypes[0],
            site=sites[0],
        )
        Cluster.objects.create(
            name="Cluster 2",
            group=clustergroups[0],
            type=clustertypes[0],
            site=sites[0],
        )
        Cluster.objects.create(
            name="Cluster 3",
            group=clustergroups[0],
            type=clustertypes[0],
            site=sites[0],
        )

        cls.form_data = {
            "name": "Cluster X",
            "group": clustergroups[1].pk,
            "type": clustertypes[1].pk,
            "tenant": None,
            "site": sites[1].pk,
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(Cluster)],
        }

        cls.csv_data = (
            "name,type",
            "Cluster 4,Cluster Type 1",
            "Cluster 5,Cluster Type 1",
            "Cluster 6,Cluster Type 1",
        )

        cls.bulk_edit_data = {
            "group": clustergroups[1].pk,
            "type": clustertypes[1].pk,
            "tenant": None,
            "site": sites[1].pk,
            "comments": "New comments",
        }


class VirtualMachineTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VirtualMachine

    @classmethod
    def setUpTestData(cls):

        deviceroles = (
            DeviceRole.objects.create(name="Device Role 1", slug="device-role-1"),
            DeviceRole.objects.create(name="Device Role 2", slug="device-role-2"),
        )

        platforms = (
            Platform.objects.create(name="Platform 1", slug="platform-1"),
            Platform.objects.create(name="Platform 2", slug="platform-2"),
        )

        clustertype = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")

        clusters = (
            Cluster.objects.create(name="Cluster 1", type=clustertype),
            Cluster.objects.create(name="Cluster 2", type=clustertype),
        )

        statuses = Status.objects.get_for_model(VirtualMachine)
        status_staged = statuses.get(slug="staged")

        VirtualMachine.objects.create(
            name="Virtual Machine 1",
            cluster=clusters[0],
            role=deviceroles[0],
            platform=platforms[0],
            status=statuses[0],
        )
        VirtualMachine.objects.create(
            name="Virtual Machine 2",
            cluster=clusters[0],
            role=deviceroles[0],
            platform=platforms[0],
            status=statuses[0],
        )
        VirtualMachine.objects.create(
            name="Virtual Machine 3",
            cluster=clusters[0],
            role=deviceroles[0],
            platform=platforms[0],
            status=statuses[0],
        )

        cls.form_data = {
            "cluster": clusters[1].pk,
            "tenant": None,
            "platform": platforms[1].pk,
            "name": "Virtual Machine X",
            "status": status_staged.pk,
            "role": deviceroles[1].pk,
            "primary_ip4": None,
            "primary_ip6": None,
            "vcpus": 4,
            "memory": 32768,
            "disk": 4000,
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(VirtualMachine)],
            "local_context_data": None,
        }

        cls.csv_data = (
            "name,cluster,status",
            "Virtual Machine 4,Cluster 1,active",
            "Virtual Machine 5,Cluster 1,active",
            "Virtual Machine 6,Cluster 1,staged",
        )

        cls.bulk_edit_data = {
            "cluster": clusters[1].pk,
            "tenant": None,
            "platform": platforms[1].pk,
            "status": status_staged.pk,
            "role": deviceroles[1].pk,
            "vcpus": 8,
            "memory": 65535,
            "disk": 8000,
            "comments": "New comments",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_local_context_schema_validation_pass(self):
        """
        Given a config context schema
        And a vm with local context that conforms to that schema
        Assert that the local context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        self.add_permissions("virtualization.add_virtualmachine")

        form_data = self.form_data.copy()
        form_data["local_context_schema"] = schema.pk
        form_data["local_context_data"] = '{"foo": "bar"}'

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(self._get_queryset().get(name="Virtual Machine X").local_context_schema.pk, schema.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_local_context_schema_validation_fails(self):
        """
        Given a config context schema
        And a vm with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", slug="schema-1", data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}}
        )
        self.add_permissions("virtualization.add_virtualmachine")

        form_data = self.form_data.copy()
        form_data["local_context_schema"] = schema.pk
        form_data["local_context_data"] = '{"foo": "bar"}'

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 200)
        self.assertEqual(self._get_queryset().filter(name="Virtual Machine X").count(), 0)


class VMInterfaceTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = VMInterface

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.create(name="Site 1", slug="site-1")
        devicerole = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1")
        clustertype = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        cluster = Cluster.objects.create(name="Cluster 1", type=clustertype, site=site)
        virtualmachines = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster, role=devicerole),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=cluster, role=devicerole),
        )

        interfaces = (
            VMInterface.objects.create(virtual_machine=virtualmachines[0], name="Interface 1"),
            VMInterface.objects.create(virtual_machine=virtualmachines[0], name="Interface 2"),
            VMInterface.objects.create(virtual_machine=virtualmachines[0], name="Interface 3"),
            VMInterface.objects.create(virtual_machine=virtualmachines[1], name="BRIDGE"),
        )

        vlans = (
            VLAN.objects.create(vid=1, name="VLAN1", site=site),
            VLAN.objects.create(vid=101, name="VLAN101", site=site),
            VLAN.objects.create(vid=102, name="VLAN102", site=site),
            VLAN.objects.create(vid=103, name="VLAN103", site=site),
        )

        obj_type = ContentType.objects.get_for_model(VMInterface)
        cf = CustomField.objects.create(name="custom_field_1", type="text")
        cf.save()
        cf.content_types.set([obj_type])

        statuses = Status.objects.get_for_model(VMInterface)
        status_active = statuses.get(slug="active")

        cls.form_data = {
            "virtual_machine": virtualmachines[1].pk,
            "name": "Interface X",
            "status": status_active.pk,
            "enabled": False,
            "bridge": interfaces[3].pk,
            "mac_address": EUI("01-02-03-04-05-06"),
            "mtu": 2000,
            "description": "New description",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "custom_field_1": "Custom Field Data",
            "tags": [t.pk for t in Tag.objects.get_for_model(VMInterface)],
        }

        cls.bulk_create_data = {
            "virtual_machine": virtualmachines[1].pk,
            "name_pattern": "Interface [4-6]",
            "enabled": False,
            "bridge": interfaces[3].pk,
            "status": status_active.pk,
            "mac_address": EUI("01-02-03-04-05-06"),
            "mtu": 2000,
            "description": "New description",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "custom_field_1": "Custom Field Data",
            "tags": [t.pk for t in Tag.objects.get_for_model(VMInterface)],
        }

        cls.csv_data = (
            "virtual_machine,name,status",
            "Virtual Machine 2,Interface 4,active",
            "Virtual Machine 2,Interface 5,active",
            "Virtual Machine 2,Interface 6,active",
        )

        cls.bulk_edit_data = {
            "enabled": False,
            "mtu": 2000,
            "status": status_active.pk,
            "description": "New description",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "custom_field_1": "New Custom Field Data",
        }
