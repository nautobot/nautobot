from django.test import TestCase

from nautobot.dcim.forms import CableCSVForm, DeviceForm, InterfaceCreateForm, InterfaceCSVForm
from nautobot.dcim.choices import DeviceFaceChoices, InterfaceStatusChoices, InterfaceTypeChoices

from nautobot.dcim.models import (
    Device,
    DeviceRole,
    DeviceType,
    Interface,
    Platform,
    Rack,
    Site,
    VirtualChassis,
)
from nautobot.extras.models import SecretsGroup, Status
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType


def get_id(model, slug):
    return model.objects.get(slug=slug).id


class DeviceTestCase(TestCase):
    def setUp(self):
        self.device_status = Status.objects.get_for_model(Device).get(slug="active")

    @classmethod
    def setUpTestData(cls):

        cls.site = Site.objects.first()
        cls.rack = Rack.objects.create(name="Rack 1", site=cls.site)

        # Platforms that have a manufacturer.
        mfr_platforms = Platform.objects.filter(manufacturer__isnull=False)

        # Get a DeviceType that has a manufacturer in line with one of the platforms.
        cls.device_type = DeviceType.objects.filter(
            manufacturer__in=mfr_platforms.values("manufacturer"),
            u_height__gt=0,
            is_full_depth=True,
        ).first()
        cls.manufacturer = cls.device_type.manufacturer
        cls.platform = Platform.objects.filter(manufacturer=cls.device_type.manufacturer).first()
        cls.device_role = DeviceRole.objects.first()

        Device.objects.create(
            name="Device 1",
            status=Status.objects.get_for_model(Device).get(slug="active"),
            device_type=cls.device_type,
            device_role=cls.device_role,
            site=cls.site,
            rack=cls.rack,
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
                "device_role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "site": self.site.pk,
                "rack": self.rack.pk,
                "face": DeviceFaceChoices.FACE_FRONT,
                "position": 1 + self.device_type.u_height,
                "platform": self.platform.pk,
                "status": self.device_status.pk,
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_racked_device_occupied(self):
        form = DeviceForm(
            data={
                "name": "test",
                "device_role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "site": self.site.pk,
                "rack": self.rack.pk,
                "face": DeviceFaceChoices.FACE_FRONT,
                "position": 1,
                "platform": self.platform.pk,
                "status": self.device_status.pk,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("position", form.errors)

    def test_non_racked_device(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "device_role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "site": self.site.pk,
                "rack": None,
                "face": None,
                "position": None,
                "platform": self.platform.pk,
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
                "device_role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "site": self.site.pk,
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
                "device_role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "site": self.site.pk,
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
        site = Site.objects.first()
        device_type = DeviceType.objects.first()
        device_role = DeviceRole.objects.first()
        cls.device = Device.objects.create(
            name="Device 2",
            device_type=device_type,
            device_role=device_role,
            site=site,
        )

    def test_interface_label_count_valid(self):
        """Test that a `label` can be generated for each generated `name` from `name_pattern` on InterfaceCreateForm"""
        status_active = Status.objects.get_for_model(Interface).get(slug=InterfaceStatusChoices.STATUS_ACTIVE)
        interface_data = {
            "device": self.device.pk,
            "name_pattern": "eth[0-9]",
            "label_pattern": "Interface[0-9]",
            "type": InterfaceTypeChoices.TYPE_100ME_FIXED,
            "status": status_active.pk,
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
        site = Site.objects.first()
        device_type = DeviceType.objects.first()
        device_role = DeviceRole.objects.first()
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


class TestInterfaceCSVForm(TestCase):
    @classmethod
    def setUpTestData(cls):
        site = Site.objects.first()
        device_type = DeviceType.objects.first()
        device_role = DeviceRole.objects.first()

        cls.devices = (
            Device.objects.create(
                name="Device 1",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 2",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
            Device.objects.create(
                name="Device 3",
                device_type=device_type,
                device_role=device_role,
                site=site,
            ),
        )

        virtualchassis = VirtualChassis.objects.create(
            name="Virtual Chassis 1", master=cls.devices[0], domain="domain-1"
        )
        Device.objects.filter(id=cls.devices[0].id).update(virtual_chassis=virtualchassis, vc_position=1)
        Device.objects.filter(id=cls.devices[1].id).update(virtual_chassis=virtualchassis, vc_position=2)

        cls.interfaces = (
            Interface.objects.create(
                device=cls.devices[0],
                name="Interface 1",
                type=InterfaceTypeChoices.TYPE_1GE_SFP,
            ),
            Interface.objects.create(
                device=cls.devices[1],
                name="Interface 2",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            ),
            Interface.objects.create(
                device=cls.devices[1],
                name="Interface 3",
                type=InterfaceTypeChoices.TYPE_LAG,
            ),
            Interface.objects.create(
                device=cls.devices[2],
                name="Interface 4",
                type=InterfaceTypeChoices.TYPE_LAG,
            ),
            Interface.objects.create(
                device=cls.devices[2],
                name="Interface 5",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            ),
        )
        cls.headers_1 = {
            "device": None,
            "name": None,
            "status": None,
            "parent_interface": None,
            "bridge": None,
            "type": None,
        }
        cls.headers_2 = {
            "device": None,
            "name": None,
            "status": None,
            "lag": None,
            "bridge": None,
            "type": None,
        }

    def test_interface_belonging_to_common_device_or_vc_allowed(self):
        """Test parent, bridge, and LAG interfaces belonging to common device or VC is valid"""

        data_1 = {
            "device": self.devices[0].name,
            "name": "interface test",
            "status": "active",
            "parent_interface": self.interfaces[0].name,
            "bridge": self.interfaces[2].name,
            "type": InterfaceTypeChoices.TYPE_VIRTUAL,
        }

        form = InterfaceCSVForm(data_1, headers=self.headers_1)
        self.assertTrue(form.is_valid())
        form.save()

        interface = Interface.objects.get(name="interface test", device=self.devices[0])
        self.assertEqual(interface.parent_interface, self.interfaces[0])
        self.assertEqual(interface.bridge, self.interfaces[2])

        # Assert LAG
        data_2 = {
            "device": self.devices[0].name,
            "name": "interface lagged",
            "status": "active",
            "lag": self.interfaces[2].name,
            "bridge": self.interfaces[1].name,
            "type": InterfaceTypeChoices.TYPE_100ME_FIXED,
        }

        form = InterfaceCSVForm(data_2, headers=self.headers_2)
        self.assertTrue(form.is_valid())
        form.save()

        interface = Interface.objects.get(name="interface lagged", device=self.devices[0])
        self.assertEqual(interface.lag, self.interfaces[2])
        self.assertEqual(interface.bridge, self.interfaces[1])

    def test_interface_not_belonging_to_common_device_or_vc_not_allowed(self):
        """Test parent, bridge, and LAG interfaces not belonging to common device or VC is invalid"""
        data = {
            "device": self.devices[0].name,
            "name": "interface test",
            "status": "active",
            "parent_interface": self.interfaces[4].name,
            "bridge": self.interfaces[4].name,
            "type": InterfaceTypeChoices.TYPE_VIRTUAL,
        }

        form = InterfaceCSVForm(data, headers=self.headers_1)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error("parent_interface"))
        self.assertTrue(form.has_error("bridge"))

        # Assert LAG
        data = {
            "device": self.devices[0].name,
            "name": "interface lagged",
            "status": "active",
            "lag": self.interfaces[3].name,
            "bridge": self.interfaces[1].name,
            "type": InterfaceTypeChoices.TYPE_VIRTUAL,
        }

        form = InterfaceCSVForm(data, headers=self.headers_2)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.has_error("lag"))
