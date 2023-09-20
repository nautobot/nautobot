from django.test import override_settings
from django.contrib.contenttypes.models import ContentType
from netaddr import EUI

from nautobot.core.testing import ViewTestCases, post_data
from nautobot.dcim.choices import InterfaceModeChoices
from nautobot.dcim.models import Device, Location, LocationType, Platform
from nautobot.extras.models import ConfigContextSchema, CustomField, Role, Status, Tag
from nautobot.ipam.factory import VLANGroupFactory
from nautobot.ipam.models import VLAN
from nautobot.virtualization.factory import ClusterGroupFactory, ClusterTypeFactory
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
        ClusterGroupFactory.create_batch(4)

        cls.form_data = {
            "name": "Cluster Group X",
            "description": "A new cluster group",
        }

        cls.csv_data = (
            "name,description",
            "Cluster Group 4,Fourth cluster group",
            "Cluster Group 5,Fifth cluster group",
            "Cluster Group 6,Sixth cluster group",
            "Cluster Group 7,Seventh cluster group",
        )


class ClusterTypeTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = ClusterType

    @classmethod
    def setUpTestData(cls):
        ClusterType.objects.all().delete()

        ClusterType.objects.create(name="Cluster Type 1")
        ClusterType.objects.create(name="Cluster Type 2")
        ClusterType.objects.create(name="Cluster Type 3")
        ClusterType.objects.create(name="Cluster Type 8")

        cls.form_data = {
            "name": "Cluster Type X",
            "description": "A new cluster type",
        }

        cls.csv_data = (
            "name,description",
            'Cluster Type ""4"",Fourth cluster type',
            'Cluster Type ""5"",Fifth cluster type',
            'Cluster Type ""6"",Sixth cluster type',
            'Cluster Type ""7"",Seventh cluster type',
        )


class ClusterTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Cluster

    @classmethod
    def setUpTestData(cls):
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        locations = (
            Location.objects.create(name="Location 1", location_type=location_type, status=location_status),
            Location.objects.create(name="Location 2", location_type=location_type, status=location_status),
        )

        clustergroups = ClusterGroupFactory.create_batch(2)

        clustertypes = ClusterTypeFactory.create_batch(2)

        Cluster.objects.create(
            name="Cluster 1",
            cluster_group=clustergroups[0],
            cluster_type=clustertypes[0],
            location=locations[0],
        )
        Cluster.objects.create(
            name="Cluster 2",
            cluster_group=clustergroups[0],
            cluster_type=clustertypes[0],
            location=locations[0],
        )
        Cluster.objects.create(
            name="Cluster 3",
            cluster_group=clustergroups[0],
            cluster_type=clustertypes[0],
            location=locations[0],
        )

        cls.form_data = {
            "name": "Cluster X",
            "cluster_group": clustergroups[1].pk,
            "cluster_type": clustertypes[1].pk,
            "tenant": None,
            "location": locations[1].pk,
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(Cluster)],
        }

        cls.csv_data = (
            "name,cluster_type",
            f"Cluster 4,{clustertypes[0].name}",
            f"Cluster 5,{clustertypes[0].name}",
            f"Cluster 6,{clustertypes[0].name}",
        )

        cls.bulk_edit_data = {
            "cluster_group": clustergroups[1].pk,
            "cluster_type": clustertypes[1].pk,
            "tenant": None,
            "location": locations[1].pk,
            "comments": "New comments",
        }


class VirtualMachineTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = VirtualMachine

    @classmethod
    def setUpTestData(cls):
        vmroles = Role.objects.get_for_model(VirtualMachine)[:2]
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        locations = (
            Location.objects.create(name="Location 1", location_type=location_type, status=location_status),
            Location.objects.create(name="Location 2", location_type=location_type, status=location_status),
        )

        platforms = Platform.objects.all()[:2]

        clustertype = ClusterType.objects.create(name="Cluster Type 1")

        clusters = (
            Cluster.objects.create(name="Cluster 1", cluster_type=clustertype, location=locations[0]),
            Cluster.objects.create(name="Cluster 2", cluster_type=clustertype, location=locations[0]),
        )

        statuses = Status.objects.get_for_model(VirtualMachine)
        status_staged = statuses[0]

        VirtualMachine.objects.create(
            name="Virtual Machine 1",
            cluster=clusters[0],
            role=vmroles[0],
            platform=platforms[0],
            status=statuses[0],
        )
        VirtualMachine.objects.create(
            name="Virtual Machine 2",
            cluster=clusters[0],
            role=vmroles[0],
            platform=platforms[0],
            status=statuses[0],
        )
        VirtualMachine.objects.create(
            name="Virtual Machine 3",
            cluster=clusters[0],
            role=vmroles[0],
            platform=platforms[0],
            status=statuses[0],
        )

        cls.form_data = {
            "cluster": clusters[1].pk,
            "tenant": None,
            "platform": platforms[1].pk,
            "name": "Virtual Machine X",
            "status": status_staged.pk,
            "role": vmroles[1].pk,
            "primary_ip4": None,
            "primary_ip6": None,
            "vcpus": 4,
            "memory": 32768,
            "disk": 4000,
            "comments": "Some comments",
            "tags": [t.pk for t in Tag.objects.get_for_model(VirtualMachine)],
            "local_config_context_data": None,
        }

        cls.csv_data = (
            "name,cluster,status",
            f"Virtual Machine 4,Cluster 1,{statuses[0].name}",
            f"Virtual Machine 5,Cluster 1,{statuses[0].name}",
            f"Virtual Machine 6,Cluster 1,{statuses[0].name}",
        )

        cls.bulk_edit_data = {
            "cluster": clusters[1].pk,
            "tenant": None,
            "platform": platforms[1].pk,
            "status": status_staged.pk,
            "role": vmroles[1].pk,
            "vcpus": 8,
            "memory": 65535,
            "disk": 8000,
            "comments": "New comments",
        }

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_local_config_context_schema_validation_pass(self):
        """
        Given a config context schema
        And a vm with local context that conforms to that schema
        Assert that the local context passes schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "string"}}}
        )
        self.add_permissions("virtualization.add_virtualmachine")

        form_data = self.form_data.copy()
        form_data["local_config_context_schema"] = schema.pk
        form_data["local_config_context_data"] = '{"foo": "bar"}'

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 302)
        self.assertEqual(self._get_queryset().get(name="Virtual Machine X").local_config_context_schema.pk, schema.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_local_config_context_schema_validation_fails(self):
        """
        Given a config context schema
        And a vm with local context that *does not* conform to that schema
        Assert that the local context fails schema validation via full_clean()
        """
        schema = ConfigContextSchema.objects.create(
            name="Schema 1", data_schema={"type": "object", "properties": {"foo": {"type": "integer"}}}
        )
        self.add_permissions("virtualization.add_virtualmachine")

        form_data = self.form_data.copy()
        form_data["local_config_context_schema"] = schema.pk
        form_data["local_config_context_data"] = '{"foo": "bar"}'

        # Try POST with model-level permission
        request = {
            "path": self._get_url("add"),
            "data": post_data(form_data),
        }
        self.assertHttpStatus(self.client.post(**request), 200)
        self.assertEqual(self._get_queryset().filter(name="Virtual Machine X").count(), 0)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"])
    def test_sort_by_ip_address(self):
        # Assert https://github.com/nautobot/nautobot/issues/3503 is fixed.
        self.add_permissions("virtualization.view_virtualmachine")
        url = self._get_url("list") + "?sort=primary_ip"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = response.content.decode(response.charset)
        self.assertInHTML("Virtual Machine 1", response)
        self.assertInHTML("Virtual Machine 2", response)
        self.assertInHTML("Virtual Machine 3", response)


class VMInterfaceTestCase(ViewTestCases.DeviceComponentViewTestCase):
    model = VMInterface

    @classmethod
    def setUpTestData(cls):
        location_type = LocationType.objects.get(name="Campus")
        location_status = Status.objects.get_for_model(Location).first()
        location = Location.objects.create(name="Location 1", location_type=location_type, status=location_status)
        devicerole = Role.objects.get_for_model(Device).first()
        clustertype = ClusterType.objects.create(name="Cluster Type 1")
        cluster = Cluster.objects.create(name="Cluster 1", cluster_type=clustertype, location=location)
        vm_status = Status.objects.get_for_model(VirtualMachine).first()
        virtualmachines = (
            VirtualMachine.objects.create(name="Virtual Machine 1", cluster=cluster, role=devicerole, status=vm_status),
            VirtualMachine.objects.create(name="Virtual Machine 2", cluster=cluster, role=devicerole, status=vm_status),
        )

        statuses = Status.objects.get_for_model(VMInterface)
        status = statuses.first()

        interfaces = (
            VMInterface.objects.create(virtual_machine=virtualmachines[0], name="Interface 1", status=status),
            VMInterface.objects.create(virtual_machine=virtualmachines[0], name="Interface 2", status=status),
            VMInterface.objects.create(virtual_machine=virtualmachines[0], name="Interface 3", status=status),
            VMInterface.objects.create(virtual_machine=virtualmachines[1], name="BRIDGE", status=status),
        )
        # Required by ViewTestCases.DeviceComponentViewTestCase.test_bulk_rename
        cls.selected_objects = interfaces[:3]
        cls.selected_objects_parent_name = virtualmachines[0].name

        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroupFactory.create(location=location)
        vlans = (
            VLAN.objects.create(vid=1, name="VLAN1", location=location, status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=101, name="VLAN101", location=location, status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=102, name="VLAN102", location=location, status=vlan_status, vlan_group=vlan_group),
            VLAN.objects.create(vid=103, name="VLAN103", location=location, status=vlan_status, vlan_group=vlan_group),
        )

        obj_type = ContentType.objects.get_for_model(VMInterface)
        cf = CustomField.objects.create(label="Custom Field 1", type="text")
        cf.save()
        cf.content_types.set([obj_type])

        cls.form_data = {
            "virtual_machine": virtualmachines[1].pk,
            "name": "Interface X",
            "status": status.pk,
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
            "status": status.pk,
            "mac_address": EUI("01-02-03-04-05-06"),
            "mtu": 2000,
            "description": "New description",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "custom_field_1": "Custom Field Data",
            "tags": [t.pk for t in Tag.objects.get_for_model(VMInterface)],
        }

        cls.bulk_add_data = {
            "virtual_machine": virtualmachines[1].pk,
            "name_pattern": "Interface [4-6]",
            "enabled": True,
            "status": status.pk,
            "mtu": 1500,
            "description": "New Description",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "custom_field_1": "Custom field data",
            "tags": [],
        }

        cls.csv_data = (
            "virtual_machine,name,status",
            f"{virtualmachines[1].composite_key},Interface 4,{statuses[0].name}",
            f"{virtualmachines[1].composite_key},Interface 5,{statuses[0].name}",
            f"{virtualmachines[1].composite_key},Interface 6,{statuses[0].name}",
        )

        cls.bulk_edit_data = {
            "enabled": False,
            "mtu": 2000,
            "status": status.pk,
            "description": "New description",
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "untagged_vlan": vlans[0].pk,
            "tagged_vlans": [v.pk for v in vlans[1:4]],
            "custom_field_1": "New Custom Field Data",
        }
