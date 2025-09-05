from django.test import TestCase

from nautobot.core.testing.forms import FormTestCases
from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.dcim.choices import DeviceFaceChoices, InterfaceModeChoices, InterfaceTypeChoices, RackWidthChoices
from nautobot.dcim.forms import (
    DeviceFilterForm,
    DeviceForm,
    InterfaceBulkEditForm,
    InterfaceCreateForm,
    InterfaceForm,
    RackForm,
)
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    Rack,
    SoftwareImageFile,
    SoftwareVersion,
)
from nautobot.extras.models import Role, SecretsGroup, Status
from nautobot.ipam.models import VLAN
from nautobot.tenancy.models import Tenant
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType


class DeviceTestCase(FormTestCases.BaseFormTestCase):
    form_class = DeviceForm

    def setUp(self):
        self.device_status = Status.objects.get_for_model(Device).first()

    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        rack_status = Status.objects.get_for_model(Rack).first()
        cls.rack = Rack.objects.create(name="Rack 1", location=cls.location, status=rack_status)

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
        cls.device_role = Role.objects.get_for_model(Device).first()
        cls.software_version_contains_no_valid_image_for_device_type = SoftwareVersion.objects.create(
            platform=cls.platform,
            version="New version 1.0.0",
            status=Status.objects.get_for_model(SoftwareVersion).first(),
        )
        cls.software_version = SoftwareVersion.objects.first()
        cls.software_image_files = SoftwareImageFile.objects.exclude(software_version=cls.software_version).exclude(
            default_image=True
        )

        Device.objects.create(
            name="Device 1",
            status=Status.objects.get_for_model(Device).first(),
            device_type=cls.device_type,
            role=cls.device_role,
            location=cls.location,
            rack=cls.rack,
            position=1,
        )
        cluster_type = ClusterType.objects.create(name="Cluster Type 1")
        cluster_group = ClusterGroup.objects.create(name="Cluster Group 1")
        Cluster.objects.create(name="Cluster 1", cluster_type=cluster_type, cluster_group=cluster_group)
        SecretsGroup.objects.create(name="Secrets Group 1")

    def test_racked_device(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "location": self.location.pk,
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
                "role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "location": self.location.pk,
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
                "role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "location": self.location.pk,
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
                "role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "location": self.location.pk,
                "rack": None,
                "face": DeviceFaceChoices.FACE_REAR,
                "platform": None,
                "status": self.device_status.pk,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("face", form.errors)

    def test_no_software_image_file_specified_is_valid(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "location": self.location.pk,
                "rack": None,
                "face": None,
                "position": None,
                "platform": self.platform.pk,
                "status": self.device_status.pk,
                "secrets_group": SecretsGroup.objects.first().pk,
                "software_version": self.software_version_contains_no_valid_image_for_device_type.pk,
                "software_image_files": [],
            }
        )
        self.assertTrue(form.is_valid())

    def test_invalid_software_image_file_specified(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "location": self.location.pk,
                "rack": None,
                "face": None,
                "position": None,
                "platform": self.platform.pk,
                "status": self.device_status.pk,
                "secrets_group": SecretsGroup.objects.first().pk,
                "software_version": self.software_version.pk,
                "software_image_files": list(self.software_image_files.values_list("pk", flat=True)),
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("software_image_files", form.errors)

    def test_non_racked_device_with_position(self):
        form = DeviceForm(
            data={
                "name": "New Device",
                "role": self.device_role.pk,
                "tenant": None,
                "manufacturer": self.manufacturer.pk,
                "device_type": self.device_type.pk,
                "location": self.location.pk,
                "rack": None,
                "position": 10,
                "platform": None,
                "status": self.device_status.pk,
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("position", form.errors)

    def test_filter_form_dg_priority_correct_value(self):
        """Validate the form allows a string separated by a comma for multiple values."""
        form = DeviceFilterForm(data={"device_redundancy_group_priority": "1,2"})
        self.assertTrue(form.is_valid())
        self.assertListEqual(form.cleaned_data["device_redundancy_group_priority"], [1, 2])


class LabelTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        device_type = DeviceType.objects.first()
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            name="Device 2",
            device_type=device_type,
            role=device_role,
            location=location,
            status=device_status,
        )

    def test_interface_label_count_valid(self):
        """Test that a `label` can be generated for each generated `name` from `name_pattern` on InterfaceCreateForm"""
        status_active = Status.objects.get_for_model(Interface).first()
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


class RackTestCase(TestCase):
    def test_update_rack_location(self):
        """Asset updating duplicate device caused by update to rack location is caught by rack clean"""
        # Rack post save signal tries updating rack devices if location is changed, which may result in an Exception
        # Asset this error is caught by RackForm.clean
        tenant = Tenant.objects.first()
        locations = Location.objects.filter(location_type=LocationType.objects.get(name="Campus"))[:2]
        manufacturer = Manufacturer.objects.create(name="Manufacturer 1")
        devicetype = DeviceType.objects.create(model="Device Type 1", manufacturer=manufacturer)
        devicerole = Role.objects.get_for_model(Device).first()
        status = Status.objects.get(name="Active")
        racks = (
            Rack.objects.create(name="Rack 1", location=locations[0], status=status),
            Rack.objects.create(name="Rack 2", location=locations[1], status=status),
        )

        Device.objects.create(
            name="device1",
            role=devicerole,
            device_type=devicetype,
            location=racks[0].location,
            rack=racks[0],
            tenant=tenant,
            status=status,
        )
        Device.objects.create(
            name="device1",
            role=devicerole,
            device_type=devicetype,
            location=racks[1].location,
            rack=racks[1],
            tenant=tenant,
            status=status,
        )
        data = {
            "name": racks[0].name,
            "location": racks[1].location.pk,
            "status": racks[0].status.pk,
            "u_height": 48,
            "width": RackWidthChoices.WIDTH_19IN,
        }
        form = RackForm(data=data, instance=racks[0])
        self.assertEqual(
            str(form.errors.as_data()["location"][0]),
            str(
                [
                    f"Device(s) ['device1'] already exist in location {locations[1]} and "
                    "would conflict with same-named devices in this rack."
                ]
            ),
        )

        # Check for https://github.com/nautobot/nautobot/issues/4149
        data = {
            "name": "New name",
            "location": racks[0].location.pk,
            "status": racks[0].status.pk,
            "u_height": 48,
            "width": RackWidthChoices.WIDTH_19IN,
        }
        form = RackForm(data=data, instance=racks[0])
        self.assertTrue(form.is_valid())


class InterfaceTestCase(NautobotTestCaseMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.device = Device.objects.first()
        status = Status.objects.get_for_model(Interface).first()
        cls.interface = Interface.objects.create(
            device=cls.device,
            name="test interface form 0.0",
            type=InterfaceTypeChoices.TYPE_2GFC_SFP,
            status=status,
        )
        cls.vlan = VLAN.objects.first()
        cls.data = {
            "device": cls.device.pk,
            "name": "test interface form 0.0",
            "type": InterfaceTypeChoices.TYPE_2GFC_SFP,
            "status": status.pk,
            "mode": InterfaceModeChoices.MODE_TAGGED,
            "tagged_vlans": [cls.vlan.pk],
        }

    def test_interface_form_clean_vlan_location_success(self):
        """Assert that form validation succeeds when matching locations/parent locations are associated to tagged VLAN"""
        location = self.device.location
        location_ids = location.ancestors(include_self=True).values_list("id", flat=True)
        self.vlan.locations.set([location.id])
        self.data["tagged_vlans"] = [self.vlan]
        form = InterfaceForm(data=self.data, instance=self.interface)
        self.assertTrue(form.is_valid())
        self.vlan.locations.set(location_ids[:2])
        self.data["tagged_vlans"] = [self.vlan]
        form = InterfaceForm(data=self.data, instance=self.interface)
        self.assertTrue(form.is_valid())

    def test_interface_form_clean_vlan_location_fail(self):
        """Assert that form validation fails when no matching locations are associated to tagged VLAN"""
        location = self.device.location
        location_ids = location.ancestors(include_self=True).values_list("id", flat=True)
        self.vlan.locations.set(list(Location.objects.exclude(pk__in=location_ids))[:2])
        self.data["tagged_vlans"] = [self.vlan]
        form = InterfaceForm(data=self.data, instance=self.interface)
        self.assertFalse(form.is_valid())

    def test_interface_vlan_location_clean_multiple_locations_pass(self):
        """Assert that form validation passes when multiple locations are associated to tagged VLAN with one matching"""
        self.vlan.locations.add(self.device.location)
        form = InterfaceForm(data=self.data, instance=self.interface)
        self.assertTrue(form.is_valid())

    def test_interface_vlan_location_clean_single_location_pass(self):
        """Assert that form validation passes when a single location is associated to tagged VLAN"""
        self.vlan.locations.set([self.device.location])
        form = InterfaceForm(data=self.data, instance=self.interface)
        self.assertTrue(form.is_valid())

    def test_interface_vlan_location_clean_no_locations_pass(self):
        """Assert that form validation passes when no locations are associated to tagged VLAN"""
        self.vlan.locations.clear()
        form = InterfaceForm(data=self.data, instance=self.interface)
        self.assertTrue(form.is_valid())

    def test_untagged_vlans_dropdown_options_align_in_interface_edit_form_and_bulk_edit_form(self):
        """
        Assert that untagged_vlans field dropdown are populated correctly in InterfaceForm and InterfaceBulkEditForm,
        and that the queryset is the same for both forms.
        """
        status = Status.objects.get_for_model(Interface).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        devices = Device.objects.all()[:3]
        for device in devices:
            device.location = location
            device.save()
        interfaces = (
            Interface.objects.create(
                device=devices[0],
                name="Test Interface 1",
                type=InterfaceTypeChoices.TYPE_2GFC_SFP,
                status=status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Test Interface 2",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Test Interface 3",
                type=InterfaceTypeChoices.TYPE_100ME_FIXED,
                status=status,
            ),
        )
        edit_form = InterfaceForm(data=self.data, instance=interfaces[0])
        bulk_edit_form = InterfaceBulkEditForm(
            model=Interface,
            data={"pks": [interface.pk for interface in interfaces]},
        )
        self.assertQuerysetEqualAndNotEmpty(
            edit_form.fields["untagged_vlan"].queryset,
            bulk_edit_form.fields["untagged_vlan"].queryset,
        )
