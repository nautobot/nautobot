from django.test import TestCase

from nautobot.dcim.forms import DeviceForm, InterfaceCreateForm, CableCSVForm
from nautobot.dcim.choices import DeviceFaceChoices, InterfaceTypeChoices

from nautobot.dcim.models import Device, DeviceRole, DeviceType, Manufacturer, Platform, Rack, Site, Interface
from nautobot.extras.models import SecretsGroup, Status
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType


def get_id(model, slug):
    return model.objects.get(slug=slug).id


class DeviceTestCase(TestCase):
    def setUp(self):
        self.device_status = Status.objects.get_for_model(Device).get(slug="active")

    @classmethod
    def setUpTestData(cls):

        site = Site.objects.create(name="Site 1", slug="site-1")
        rack = Rack.objects.create(name="Rack 1", site=site)
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1", slug="manufacturer-1")
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Device Type 1",
            slug="device-type-1",
            u_height=1,
        )
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ff0000")
        Platform.objects.create(name="Platform 1", slug="platform-1")
        Device.objects.create(
            name="Device 1",
            device_type=device_type,
            device_role=device_role,
            site=site,
            rack=rack,
            position=1,
        )
        cluster_type = ClusterType.objects.create(name="Cluster Type 1", slug="cluster-type-1")
        cluster_group = ClusterGroup.objects.create(name="Cluster Group 1", slug="cluster-group-1")
        Cluster.objects.create(name="Cluster 1", type=cluster_type, group=cluster_group)
        SecretsGroup.objects.create(name="Secrets Group 1", slug="secrets-group-1")

    def test_racked_device(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "device_role": DeviceRole.objects.first().pk,
                "tenant": None,
                "manufacturer": Manufacturer.objects.first().pk,
                "device_type": DeviceType.objects.first().pk,
                "site": Site.objects.first().pk,
                "rack": Rack.objects.first().pk,
                "face": DeviceFaceChoices.FACE_FRONT,
                "position": 2,
                "platform": Platform.objects.first().pk,
                "status": self.device_status.pk,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_racked_device_occupied(self):
        form = DeviceForm(
            data={
                "name": "test",
                "device_role": DeviceRole.objects.first().pk,
                "tenant": None,
                "manufacturer": Manufacturer.objects.first().pk,
                "device_type": DeviceType.objects.first().pk,
                "site": Site.objects.first().pk,
                "rack": Rack.objects.first().pk,
                "face": DeviceFaceChoices.FACE_FRONT,
                "position": 1,
                "platform": Platform.objects.first().pk,
                "status": self.device_status.pk,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("position", form.errors)

    def test_non_racked_device(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "device_role": DeviceRole.objects.first().pk,
                "tenant": None,
                "manufacturer": Manufacturer.objects.first().pk,
                "device_type": DeviceType.objects.first().pk,
                "site": Site.objects.first().pk,
                "rack": None,
                "face": None,
                "position": None,
                "platform": Platform.objects.first().pk,
                "status": self.device_status.pk,
                "secrets_group": SecretsGroup.objects.first().pk,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_non_racked_device_with_face(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "device_role": DeviceRole.objects.first().pk,
                "tenant": None,
                "manufacturer": Manufacturer.objects.first().pk,
                "device_type": DeviceType.objects.first().pk,
                "site": Site.objects.first().pk,
                "rack": None,
                "face": DeviceFaceChoices.FACE_REAR,
                "platform": None,
                "status": self.device_status.pk,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("face", form.errors)

    def test_non_racked_device_with_position(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "device_role": DeviceRole.objects.first().pk,
                "tenant": None,
                "manufacturer": Manufacturer.objects.first().pk,
                "device_type": DeviceType.objects.first().pk,
                "site": Site.objects.first().pk,
                "rack": None,
                "position": 10,
                "platform": None,
                "status": self.device_status.pk,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("position", form.errors)


class LabelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="Site 2", slug="site-2")
        manufacturer = Manufacturer.objects.create(name="Manufacturer 2", slug="manufacturer-2")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Device Type 2",
            slug="device-type-2",
            u_height=1,
        )
        device_role = DeviceRole.objects.create(name="Device Role 2", slug="device-role-2", color="ffff00")
        cls.device = Device.objects.create(
            name="Device 2",
            device_type=cls.device_type,
            device_role=device_role,
            site=site,
        )

    def test_interface_label_count_valid(self):
        """Test that a `label` can be generated for each generated `name` from `name_pattern` on InterfaceCreateForm"""
        interface_data = {
            "device": self.device.pk,
            "name_pattern": "eth[0-9]",
            "label_pattern": "Interface[0-9]",
            "type": InterfaceTypeChoices.TYPE_100ME_FIXED,
        }
        form = InterfaceCreateForm(interface_data)

        self.assertTrue(form.is_valid())

    def test_interface_label_count_mismatch(self):
        """Test that a `label` cannot be generated for each generated `name` from `name_pattern` due to invalid `label_pattern` on InterfaceCreateForm"""
        bad_interface_data = {
            "device": self.device.pk,
            "name_pattern": "eth[0-9]",
            "label_pattern": "Interface[0-1]",
            "type": InterfaceTypeChoices.TYPE_100ME_FIXED,
        }
        form = InterfaceCreateForm(bad_interface_data)

        self.assertFalse(form.is_valid())
        self.assertIn("label_pattern", form.errors)


class TestCableCSVForm(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = Site.objects.create(name="Site 2", slug="site-2")
        manufacturer = Manufacturer.objects.create(name="Manufacturer 2", slug="manufacturer-2")
        device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Device Type 1",
            slug="device-type-1",
            u_height=1,
        )
        device_role = DeviceRole.objects.create(name="Device Role 1", slug="device-role-1", color="ffff00")
        cls.device_1 = Device.objects.create(
            name="Device 1",
            device_type=device_type,
            device_role=device_role,
            site=site,
        )
        cls.device_2 = Device.objects.create(
            name="Device 2",
            device_type=device_type,
            device_role=device_role,
            site=site,
        )
        cls.interface_1 = Interface.objects.create(
            device=cls.device_1,
            name="Interface 1",
            type=InterfaceTypeChoices.TYPE_LAG,
        )
        cls.interface_2 = Interface.objects.create(
            device=cls.device_2,
            name="Interface 2",
            type=InterfaceTypeChoices.TYPE_LAG,
        )

    def test_add_error_method_converts_error_fields_to_equivalent_in_CableCSVForm(self):
        """Test invalid input (cabling to LAG interfaces) is correctly reported in the form."""
        data = {
            "side_a_device": self.device_1.name,
            "side_a_type": "dcim.interface",
            "side_a_name": self.interface_1.name,
            "side_b_device": self.device_2.name,
            "side_b_type": "dcim.interface",
            "side_b_name": self.interface_2.name,
            "status": "connected",
        }
        headers = {
            "side_a_device": None,
            "side_a_type": None,
            "side_a_name": None,
            "side_b_device": None,
            "side_b_type": None,
            "side_b_name": None,
            "status": None,
        }
        form = CableCSVForm(data, headers=headers)
        self.assertFalse(form.is_valid())
        self.assertIn("side_a_name", form.errors)
        self.assertNotIn("termination_a_id", form.errors)
