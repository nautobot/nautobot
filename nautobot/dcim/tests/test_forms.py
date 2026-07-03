import uuid

from constance.test import override_config
from django.test import TestCase

from nautobot.circuits.models import Circuit, CircuitTermination
from nautobot.core.testing.forms import FormTestCases
from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.dcim.choices import (
    ConsolePortTypeChoices,
    DeviceFaceChoices,
    InterfaceDuplexChoices,
    InterfaceModeChoices,
    InterfaceSpeedChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    RackWidthChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.constants import RACK_U_HEIGHT_DEFAULT
from nautobot.dcim.forms import (
    CableForm,
    DeviceFilterForm,
    DeviceForm,
    InterfaceBulkEditForm,
    InterfaceCreateForm,
    InterfaceForm,
    PopulateDeviceBayForm,
    RackForm,
)
from nautobot.dcim.models import (
    Cable,
    CableToCableTermination,
    CableType,
    ConsolePort,
    ConsoleServerPort,
    Device,
    DeviceBay,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    PowerFeed,
    PowerPanel,
    Rack,
    SoftwareImageFile,
    SoftwareVersion,
)
from nautobot.dcim.termination_field_set import CableTerminationFieldSet, detect_termination_type
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


class PopulateDeviceBayFormTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        cls.status = Status.objects.get_for_model(Device).first()
        cls.role = Role.objects.get_for_model(Device).first()
        cls.manufacturer = Manufacturer.objects.first() or Manufacturer.objects.create(name="Form Manufacturer")
        rack_status = Status.objects.get_for_model(Rack).first()
        cls.rack = Rack.objects.create(name="Form Rack 1", location=cls.location, status=rack_status)
        cls.alt_location = Location.objects.exclude(pk=cls.location.pk).first()
        if cls.alt_location is None:
            location_status = Status.objects.get_for_model(Location).first()
            cls.alt_location = Location.objects.create(
                name="Form Location 2",
                location_type=cls.location.location_type,
                status=location_status,
            )

        cls.parent_device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturer,
            model="Form Parent DeviceType",
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        )
        cls.child_device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturer,
            model="Form Child DeviceType",
            u_height=0,
            subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
        )
        cls.parent_child_device_type = DeviceType.objects.create(
            manufacturer=cls.manufacturer,
            model="Form ParentChild DeviceType",
            u_height=0,
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT_CHILD,
        )

        cls.parent_device = Device.objects.create(
            name="Form Parent Device",
            device_type=cls.parent_device_type,
            role=cls.role,
            location=cls.location,
            rack=cls.rack,
            position=1,
            status=cls.status,
        )
        cls.device_bay = DeviceBay.objects.create(device=cls.parent_device, name="Form Bay 1")

        cls.child_device = Device.objects.create(
            name="Form Child Device",
            device_type=cls.child_device_type,
            role=cls.role,
            location=cls.location,
            rack=cls.rack,
            status=cls.status,
        )
        cls.parent_child_device = Device.objects.create(
            name="Form ParentChild Device",
            device_type=cls.parent_child_device_type,
            role=cls.role,
            location=cls.location,
            rack=cls.rack,
            status=cls.status,
        )

        cls.assigned_child = Device.objects.create(
            name="Form Assigned Child Device",
            device_type=cls.child_device_type,
            role=cls.role,
            location=cls.location,
            rack=cls.rack,
            status=cls.status,
        )
        DeviceBay.objects.create(device=cls.parent_device, name="Form Bay 2", installed_device=cls.assigned_child)

        cls.offsite_child = Device.objects.create(
            name="Form Offsite Child Device",
            device_type=cls.child_device_type,
            role=cls.role,
            location=cls.alt_location,
            status=cls.status,
        )

        cls.parent_only_device = Device.objects.create(
            name="Form Parent Device Only",
            device_type=cls.parent_device_type,
            role=cls.role,
            location=cls.location,
            rack=cls.rack,
            status=cls.status,
        )

    def test_installed_device_queryset_includes_parent_child_role(self):
        form = PopulateDeviceBayForm(self.device_bay)
        queryset = form.fields["installed_device"].queryset

        actual_pks = set(queryset.values_list("pk", flat=True))
        expected_pks = {self.child_device.pk, self.parent_child_device.pk}

        self.assertSetEqual(actual_pks, expected_pks)


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

    def test_rack_form_initial_u_height_default(self):
        """Test that RackForm sets initial u_height from default Constance config (42)."""
        # Create a new form (not bound to an instance)
        form = RackForm()

        # The initial value should be 42 (default Constance config)
        self.assertEqual(form.fields["u_height"].initial, RACK_U_HEIGHT_DEFAULT)

    @override_config(RACK_DEFAULT_U_HEIGHT=48)
    def test_rack_form_initial_u_height_custom(self):
        """Test that RackForm sets initial u_height from custom Constance config."""
        # Create a new form (not bound to an instance)
        form = RackForm()

        # The initial value should be 48 (from Constance config)
        self.assertEqual(form.fields["u_height"].initial, 48)

    def test_rack_form_initial_u_height_not_set_on_edit(self):
        """Test that RackForm does NOT override u_height when editing an existing rack."""
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        status = Status.objects.get(name="Active")

        # Create a rack with u_height of 24
        rack = Rack.objects.create(name="Test Rack", location=location, status=status, u_height=24)

        # Create a form bound to the existing rack
        form = RackForm(instance=rack)

        # The initial value should NOT be overridden - it should use the rack's actual value
        # (The form will show the model instance's value, not the Constance config)
        self.assertEqual(form.initial["u_height"], 24)


class InterfaceTestCase(NautobotTestCaseMixin, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.device = Device.objects.first()
        cls.status = Status.objects.get_for_model(Interface).first()
        cls.interface = Interface.objects.create(
            device=cls.device,
            name="test interface form 0.0",
            type=InterfaceTypeChoices.TYPE_2GFC_SFP,
            status=cls.status,
        )
        cls.vlan = VLAN.objects.first()
        cls.data = {
            "device": cls.device.pk,
            "name": "test interface form 0.0",
            "type": InterfaceTypeChoices.TYPE_2GFC_SFP,
            "port_type": PortTypeChoices.TYPE_LC,
            "status": cls.status.pk,
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
                port_type=PortTypeChoices.TYPE_LC,
                status=self.status,
            ),
            Interface.objects.create(
                device=devices[1],
                name="Test Interface 2",
                type=InterfaceTypeChoices.TYPE_LAG,
                port_type=PortTypeChoices.TYPE_8P8C,
                status=self.status,
            ),
            Interface.objects.create(
                device=devices[2],
                name="Test Interface 3",
                type=InterfaceTypeChoices.TYPE_100ME_FIXED,
                status=self.status,
            ),
        )
        edit_form = InterfaceForm(data=self.data, instance=interfaces[0])
        bulk_edit_form = InterfaceBulkEditForm(
            model=Interface,
            data={"pks": [interface.pk for interface in interfaces]},
        )
        self.assertQuerySetEqualAndNotEmpty(
            edit_form.fields["untagged_vlan"].queryset,
            bulk_edit_form.fields["untagged_vlan"].queryset,
        )

    def test_bulk_interface_form_clean_tagged_vlan_fail(self):
        """Assert that form validation fails when adding a tagged VLAN and mode is not tagged to an interface in bulk edit form."""
        # Create an interface that is NOT in tagged mode.
        interface = Interface.objects.create(
            device=self.device,
            name="Non-Tagged Interface",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mode=InterfaceModeChoices.MODE_ACCESS,
            status=self.status,
        )
        form = InterfaceBulkEditForm(
            model=Interface,
            data={
                "pk": [interface.pk],
                "add_tagged_vlans": [self.vlan.pk],
            },
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            "Attempting to update VLAN when not all of the interfaces were in tagged mode including",
            form.errors["mode"][0],
        )
        form = InterfaceBulkEditForm(
            model=Interface,
            data={
                "pk": [interface.pk],
                "add_tagged_vlans": [self.vlan.pk],
                "mode": InterfaceModeChoices.MODE_TAGGED,
            },
        )
        self.assertTrue(form.is_valid())

    def test_interface_mode_tagged_vlans_interaction(self):
        """Assert that form validation correctly handles various combinations of mode and tagged_vlans."""
        data = {
            "device": self.device.pk,
            "name": "Interface Tester",
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "status": self.status.pk,
        }

        # Tagged mode + tagged VLANs - valid
        location = self.device.location
        self.vlan.locations.set([location.id])
        data.update({"mode": InterfaceModeChoices.MODE_TAGGED, "tagged_vlans": [self.vlan.pk]})
        form = InterfaceForm(data=data)
        self.assertTrue(form.is_valid())

        # Tagged-all mode + tagged VLANs - valid, VLANs will be auto-cleared.
        data.update({"mode": InterfaceModeChoices.MODE_TAGGED_ALL})
        form = InterfaceForm(data=data)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["tagged_vlans"], [])

        # Access mode + tagged VLANs - invalid
        data.update({"mode": InterfaceModeChoices.MODE_ACCESS})
        form = InterfaceForm(data=data)
        self.assertFalse(form.is_valid())

    def test_interface_form_fields_and_blank(self):
        data = {
            "device": self.device.pk,
            "name": self.interface.name,
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "status": self.status.pk,
            "speed": "",  # blank should coerce to None
            "duplex": "",  # blank allowed
        }
        form = InterfaceForm(data=data, instance=self.interface)
        self.assertIn("speed", form.fields)
        self.assertIn("duplex", form.fields)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["speed"])  # TypedChoiceField(empty->None)
        self.assertEqual(form.cleaned_data["duplex"], "")

    def test_interface_form_speed_choice_coerces_int(self):
        speed_choice = InterfaceSpeedChoices.SPEED_10G
        data = {
            "device": self.device.pk,
            "name": self.interface.name,
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "status": self.status.pk,
            # Posted value is a string; TypedChoiceField should coerce to int
            "speed": str(speed_choice),
            "duplex": InterfaceDuplexChoices.DUPLEX_FULL,
        }
        form = InterfaceForm(data=data, instance=self.interface)
        self.assertTrue(form.is_valid())
        self.assertIsInstance(form.cleaned_data["speed"], int)
        self.assertEqual(form.cleaned_data["speed"], speed_choice)
        self.assertEqual(form.cleaned_data["duplex"], InterfaceDuplexChoices.DUPLEX_FULL)

    def test_interface_create_form_blank_and_choice(self):
        # Blank speed
        data_blank = {
            "device": self.device.pk,
            "name_pattern": "eth1",
            "status": self.status.pk,
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "speed": "",
            "duplex": "",
        }
        form_blank = InterfaceCreateForm(data_blank)
        self.assertTrue(form_blank.is_valid())
        self.assertIsNone(form_blank.cleaned_data["speed"])  # TypedChoiceField(empty->None)

        # With a specific choice
        speed_choice = InterfaceSpeedChoices.SPEED_1G
        data_choice = {
            "device": self.device.pk,
            "name_pattern": "eth2",
            "status": self.status.pk,
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "speed": str(speed_choice),
            "duplex": InterfaceDuplexChoices.DUPLEX_AUTO,
        }
        form_choice = InterfaceCreateForm(data_choice)
        self.assertTrue(form_choice.is_valid())
        self.assertEqual(form_choice.cleaned_data["speed"], speed_choice)
        self.assertEqual(form_choice.cleaned_data["duplex"], InterfaceDuplexChoices.DUPLEX_AUTO)


class CableTerminationFieldSetTestCase(TestCase):
    """Tests for the centralized cable termination picker fieldset."""

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Fieldset Test Device Type")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            location=location,
            device_type=device_type,
            role=device_role,
            name="Fieldset Test Device",
            status=device_status,
        )
        interface_status = Status.objects.get_for_model(Interface).first()
        cls.interface = Interface.objects.create(
            device=cls.device, name="eth0", status=interface_status, type="1000base-t"
        )

    def test_detect_termination_type_none_returns_default(self):
        self.assertEqual(detect_termination_type(None), "interface")

    def test_detect_termination_type_known_model(self):
        # Unsaved instance is fine — only `_meta.model_name` is consulted.
        self.assertEqual(detect_termination_type(Interface()), "interface")

    def test_detect_termination_type_unknown_model_raises(self):
        # Device is not a CableTermination subclass — should raise rather than silently default.
        with self.assertRaisesMessage(ValueError, "not a registered cable termination type"):
            detect_termination_type(Device())

    def test_get_fields_unknown_term_type_raises(self):
        with self.assertRaisesMessage(ValueError, "not a registered cable termination type"):
            CableTerminationFieldSet().get_fields("test", term_type="not_a_real_type")

    def test_get_fields_default_shape(self):
        """With no args, get_fields() returns three fields plus a meta dict for the Interface default."""
        result = CableTerminationFieldSet().get_fields("a_conn_1")
        self.assertEqual(set(result.keys()), {"fields", "initial", "meta"})
        self.assertEqual(
            set(result["fields"].keys()),
            {"a_conn_1_type", "a_conn_1_parent", "a_conn_1_termination"},
        )
        # The type field initial reflects the auto-detected default.
        self.assertEqual(result["initial"]["a_conn_1_type"], "interface")
        # The parent field's queryset model defaults to Device (interface is Device-parented).
        self.assertIs(result["fields"]["a_conn_1_parent"].queryset.model, Device)
        # No existing termination means no parent/term pre-population.
        self.assertNotIn("a_conn_1_parent", result["initial"])
        self.assertNotIn("a_conn_1_termination", result["initial"])
        # Meta carries the resolved term_type and field-name mapping.
        self.assertEqual(result["meta"]["term_type"], "interface")
        self.assertEqual(result["meta"]["type_field"], "a_conn_1_type")
        self.assertEqual(result["meta"]["parent_field"], "a_conn_1_parent")
        self.assertEqual(result["meta"]["term_field"], "a_conn_1_termination")

    def test_get_fields_prepopulates_from_existing_term(self):
        """An existing termination pre-fills parent and termination initial values."""
        result = CableTerminationFieldSet().get_fields("a_conn_1", existing_term=self.interface)
        self.assertEqual(result["initial"]["a_conn_1_type"], "interface")
        self.assertEqual(result["initial"]["a_conn_1_parent"], self.device.pk)
        self.assertEqual(result["initial"]["a_conn_1_termination"], self.interface.pk)

    def test_get_fields_circuittermination_uses_circuit_parent(self):
        """The `circuittermination` config produces a Circuit parent field, not Device."""
        result = CableTerminationFieldSet().get_fields("b_conn_1", term_type="circuittermination")
        self.assertIs(result["fields"]["b_conn_1_parent"].queryset.model, Circuit)
        self.assertIs(result["fields"]["b_conn_1_termination"].queryset.model, CircuitTermination)

    def test_get_fields_powerfeed_uses_powerpanel_parent(self):
        """The `powerfeed` config produces a PowerPanel parent field."""
        result = CableTerminationFieldSet().get_fields("b_conn_1", term_type="powerfeed")
        self.assertIs(result["fields"]["b_conn_1_parent"].queryset.model, PowerPanel)
        self.assertIs(result["fields"]["b_conn_1_termination"].queryset.model, PowerFeed)


class CableFormTestCase(FormTestCases.BaseFormTestCase):
    """Behavioral tests for `CableForm`. Scope expected to grow over time."""

    form_class = CableForm

    @classmethod
    def setUpTestData(cls):
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="Cable Swap DT")
        device_role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            name="Cable Swap Device",
            device_type=device_type,
            role=device_role,
            location=location,
            status=device_status,
        )
        iface_status = Status.objects.get_for_model(Interface).first()
        cls.iface_a = Interface.objects.create(
            device=cls.device, name="iface-a", status=iface_status, type="1000base-t"
        )
        cls.iface_b = Interface.objects.create(
            device=cls.device, name="iface-b", status=iface_status, type="1000base-t"
        )
        cls.cable_status = Status.objects.get_for_model(Cable).get(name="Connected")
        cls.cable = Cable.objects.create(termination_a=cls.iface_a, termination_b=cls.iface_b, status=cls.cable_status)

    def _form_data_with_swapped_terminations(self):
        """Return POST data for the existing cable with A/B termination assignments swapped."""
        return {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
            "cable_type": "",
            # Swapped: was A=iface_a, B=iface_b — now A=iface_b, B=iface_a.
            "a_conn_1_type": "interface",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(self.iface_b.pk),
            "b_conn_1_type": "interface",
            "b_conn_1_parent": str(self.device.pk),
            "b_conn_1_termination": str(self.iface_a.pk),
        }

    def test_swap_termination_sides_saves_cleanly(self):
        """A form submission that flips A/B terminations should save without IntegrityError."""
        form = CableForm(data=self._form_data_with_swapped_terminations(), instance=self.cable)
        self.assertTrue(form.is_valid(), msg=form.errors)
        form.save()  # Must not raise IntegrityError on the (cable, cable_end) unique constraint.

        rows = {row.cable_end: row.termination for row in CableToCableTermination.objects.filter(cable=self.cable)}
        self.assertEqual(rows.get("A"), self.iface_b)
        self.assertEqual(rows.get("B"), self.iface_a)
        # Exactly two join rows — no orphans left from the previous arrangement.
        self.assertEqual(CableToCableTermination.objects.filter(cable=self.cable).count(), 2)

    def test_blank_termination_type_falls_back_to_default(self):
        """A form submission with an empty `<side>_conn_N_type` value should not raise from
        `CableTerminationFieldSet.get_fields`. The "---------" choice in the type dropdown
        (value="") is valid form input and should be treated as "no type selected" (default to
        the existing-term-derived default), not as an unknown type."""
        data = {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
            "cable_type": "",
            "a_conn_1_type": "interface",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(self.iface_a.pk),
            # User cleared the B side's type dropdown (and termination); the type field's
            # empty-string value used to propagate into the fieldset and raise ValueError.
            "b_conn_1_type": "",
            "b_conn_1_parent": "",
            "b_conn_1_termination": "",
        }
        # The form construction should succeed without raising.
        form = CableForm(data=data, instance=self.cable)
        self.assertTrue(hasattr(form, "fields"))

    def test_form_rejects_incompatible_termination_pair(self):
        """A form submission pairing an Interface with a ConsolePort must fail validation, not save."""
        iface_status = Status.objects.get_for_model(Interface).first()
        iface_free = Interface.objects.create(
            device=self.device, name="iface-free", status=iface_status, type="1000base-t"
        )
        cp = ConsolePort.objects.create(
            device=self.device, name="cp-incompatible", type=ConsolePortTypeChoices.TYPE_RJ45
        )
        data = {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
            "cable_type": "",
            "a_conn_1_type": "interface",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(iface_free.pk),
            "b_conn_1_type": "consoleport",
            "b_conn_1_parent": str(self.device.pk),
            "b_conn_1_termination": str(cp.pk),
        }
        form = CableForm(data=data)
        self.assertFalse(form.is_valid())
        # Error is attached to the B-side termination field for clear UX, not buried in non-field errors.
        self.assertIn("b_conn_1_termination", form.errors)
        self.assertIn("Incompatible termination types", str(form.errors["b_conn_1_termination"]))
        # The freshly-created ConsolePort never got attached to any cable.
        self.assertFalse(CableToCableTermination.objects.filter(console_port=cp).exists())

    def test_form_rejects_incompatible_breakout_lane_pair(self):
        """On a 1x2 breakout, lane 2 (A1↔B2) incompatibility must surface as a form error at submit time."""
        ct = CableType.objects.create(name="form-test 1x2", a_connectors=1, b_connectors=2, total_lanes=2)
        iface_status = Status.objects.get_for_model(Interface).first()
        iface_a1 = Interface.objects.create(
            device=self.device, name="lane-iface-a1", status=iface_status, type="1000base-t"
        )
        iface_b1 = Interface.objects.create(
            device=self.device, name="lane-iface-b1", status=iface_status, type="1000base-t"
        )
        cp_b2 = ConsolePort.objects.create(device=self.device, name="lane-cp-b2", type=ConsolePortTypeChoices.TYPE_RJ45)
        data = {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
            "cable_type": str(ct.pk),
            "a_conn_1_type": "interface",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(iface_a1.pk),
            "b_conn_1_type": "interface",
            "b_conn_1_parent": str(self.device.pk),
            "b_conn_1_termination": str(iface_b1.pk),
            # Lane 2: A1 (interface) ↔ B2 (consoleport) — incompatible.
            "b_conn_2_type": "consoleport",
            "b_conn_2_parent": str(self.device.pk),
            "b_conn_2_termination": str(cp_b2.pk),
        }
        form = CableForm(data=data)
        self.assertFalse(form.is_valid())
        # The incompatibility is on lane 2 (b_conn_2), not lane 1.
        self.assertIn("b_conn_2_termination", form.errors)
        self.assertNotIn("b_conn_1_termination", form.errors)
        self.assertIn("Incompatible termination types", str(form.errors["b_conn_2_termination"]))
        # No CableToCableTermination row was created for the rejected ConsolePort.
        self.assertFalse(CableToCableTermination.objects.filter(console_port=cp_b2).exists())

    def test_disconnect_one_side_of_invalid_cable_is_allowed(self):
        """A cable that's already in an invalid state (e.g. incompatible termination types saved
        before the create-time validation gap was fixed) should be editable to *remove* one side's
        termination so the user can recover. The form's pair-compatibility check must validate the
        cleaned form data, not silently fall back to the existing saved (invalid) pair when the
        user has cleared one side."""
        iface_status = Status.objects.get_for_model(Interface).first()
        iface_orphan = Interface.objects.create(
            device=self.device, name="iface-orphan-for-disconnect", status=iface_status, type="1000base-t"
        )
        cp = ConsolePort.objects.create(
            device=self.device, name="cp-incompatible-disconnect", type=ConsolePortTypeChoices.TYPE_RJ45
        )
        # Bypass form validation to create an invalid cable directly via the join model. This
        # mirrors the situation a user might be in before the create-time validation fix landed.
        invalid_cable = Cable.objects.create(status=self.cable_status)
        CableToCableTermination.objects.create(cable=invalid_cable, cable_end="A", interface=iface_orphan)
        CableToCableTermination.objects.create(cable=invalid_cable, cable_end="B", console_port=cp)

        # Edit the cable, clearing the B-side termination entirely.
        data = {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
            "cable_type": "",
            "a_conn_1_type": "interface",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(iface_orphan.pk),
            "b_conn_1_type": "",
            "b_conn_1_parent": "",
            "b_conn_1_termination": "",
        }
        form = CableForm(data=data, instance=invalid_cable)
        self.assertTrue(
            form.is_valid(),
            msg=f"Form should accept disconnecting one side, got errors: {form.errors}",
        )

    def test_incompatible_termination_pair_rejected_on_create(self):
        """A new cable connecting an Interface to a ConsolePort should be rejected at form
        validation time, the same way it is during edit. The previous implementation only ran
        the pair-compatibility check via `Cable.clean()` reading the saved join rows, which
        don't exist yet at create-time, so invalid pairs slipped through to save."""
        iface_status = Status.objects.get_for_model(Interface).first()
        iface_uncabled = Interface.objects.create(
            device=self.device, name="iface-uncabled", status=iface_status, type="1000base-t"
        )
        cp = ConsolePort.objects.create(
            device=self.device, name="cp-incompatible", type=ConsolePortTypeChoices.TYPE_RJ45
        )
        data = {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
            "cable_type": "",
            "a_conn_1_type": "interface",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(iface_uncabled.pk),
            "b_conn_1_type": "consoleport",
            "b_conn_1_parent": str(self.device.pk),
            "b_conn_1_termination": str(cp.pk),
        }
        form = CableForm(data=data)  # No `instance=` — creating a new cable.
        self.assertFalse(form.is_valid(), msg="Form should have rejected the incompatible pair")
        self.assertIn("Incompatible termination types", str(form.errors))

    def test_unchanged_terminations_preserve_join_rows(self):
        """Saving the form without touching terminations should leave the CableToCableTermination
        rows (and their PKs) untouched — no spurious change-log churn for unrelated edits."""
        original_pks = set(CableToCableTermination.objects.filter(cable=self.cable).values_list("pk", flat=True))

        data = {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "42",
            "length_unit": "m",
            "label": "edited-length",
            "cable_type": "",
            # Same termination arrangement as setUpTestData.
            "a_conn_1_type": "interface",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(self.iface_a.pk),
            "b_conn_1_type": "interface",
            "b_conn_1_parent": str(self.device.pk),
            "b_conn_1_termination": str(self.iface_b.pk),
        }
        form = CableForm(data=data, instance=self.cable)
        self.assertTrue(form.is_valid(), msg=form.errors)
        form.save()

        self.cable.refresh_from_db()
        self.assertEqual(self.cable.label, "edited-length")
        # Same set of CableToCableTermination row PKs as before — no delete/recreate happened.
        new_pks = set(CableToCableTermination.objects.filter(cable=self.cable).values_list("pk", flat=True))
        self.assertSetEqual(new_pks, original_pks)

    def test_edit_form_prepopulates_lane_fields(self):
        """Editing an existing non-breakout cable should prepopulate the lane termination fields."""
        form = CableForm(instance=self.cable)
        self.assertEqual(form.initial.get("a_conn_1_type"), "interface")
        self.assertEqual(form.initial.get("a_conn_1_parent"), self.device.pk)
        self.assertEqual(form.initial.get("a_conn_1_termination"), self.iface_a.pk)
        self.assertEqual(form.initial.get("b_conn_1_type"), "interface")
        self.assertEqual(form.initial.get("b_conn_1_parent"), self.device.pk)
        self.assertEqual(form.initial.get("b_conn_1_termination"), self.iface_b.pk)

    # `CableForm._init_lane_fields` — happy paths and the exception branches that turn malformed
    # URL/HTMX-supplied `initial` values into a fallback layout *plus* a form-error message.

    @classmethod
    def _breakout_cable_type(cls):
        """A 1x4 breakout CableType for lane-layout assertions."""
        return CableType.objects.create(name="Form Test 1x4", a_connectors=1, b_connectors=4, total_lanes=4)

    @classmethod
    def _shuffle_cable_type(cls):
        """A polarity-shuffled 2x2 CableType: each A connector wires to BOTH B connectors (a mesh)."""
        mapping = [
            {"label": "1", "a_connector": 1, "a_position": 1, "b_connector": 1, "b_position": 1},
            {"label": "2", "a_connector": 1, "a_position": 2, "b_connector": 1, "b_position": 2},
            {"label": "3", "a_connector": 1, "a_position": 3, "b_connector": 2, "b_position": 1},
            {"label": "4", "a_connector": 1, "a_position": 4, "b_connector": 2, "b_position": 2},
            {"label": "5", "a_connector": 2, "a_position": 1, "b_connector": 1, "b_position": 3},
            {"label": "6", "a_connector": 2, "a_position": 2, "b_connector": 1, "b_position": 4},
            {"label": "7", "a_connector": 2, "a_position": 3, "b_connector": 2, "b_position": 3},
            {"label": "8", "a_connector": 2, "a_position": 4, "b_connector": 2, "b_position": 4},
        ]
        return CableType.objects.create(
            name="Form Test 2x2 Shuffle", a_connectors=2, b_connectors=2, total_lanes=8, mapping=mapping
        )

    def _minimal_form_data(self):
        """Minimal POST data sufficient to make `is_valid()` run `clean()`.

        Intentionally omits `cable_type` — `_init_lane_fields` treats a key being present in
        `self.data` as a live-preview override (with falsy meaning "user cleared"), so including
        `cable_type=""` here would shadow any `initial['cable_type']` in tests that pair `initial`
        with this baseline data. Tests that specifically want to exercise the data-driven path
        add the key explicitly.
        """
        return {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
        }

    # ── Happy paths ───────────────────────────────────────────────────────────────

    def test_init_lane_fields_uses_cable_type_from_initial(self):
        """Validate `initial={'cable_type': pk}` works with no form-validation errors."""
        breakout = self._breakout_cable_type()
        form = CableForm(initial={"cable_type": str(breakout.pk)}, data=self._minimal_form_data())
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertIsNotNone(form.connection_info["cable_type"])
        self.assertEqual(len(form.connection_info["a_side"]), 1)
        self.assertEqual(len(form.connection_info["b_side"]), 4)
        self.assertEqual([conn["connector"] for conn in form.connection_info["b_side"]], [1, 2, 3, 4])
        self.assertIn("b_conn_4_type", form.fields)

    def test_init_lane_fields_uses_cable_type_from_submitted_data(self):
        """Validate `cable_type` in the POST data works with no form-validation errors."""
        breakout = self._breakout_cable_type()
        data = self._minimal_form_data()
        data["cable_type"] = str(breakout.pk)
        form = CableForm(data=data)
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(len(form.connection_info["b_side"]), 4)

    def test_init_lane_fields_prefills_a_side_from_initial_termination(self):
        """Validate termination_a prepopulation via `initial`."""
        form = CableForm(
            initial={"termination_a_type": "dcim.interface", "termination_a_id": str(self.iface_a.pk)},
            data=self._minimal_form_data(),
        )
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(form.initial.get("a_conn_1_type"), "interface")
        self.assertEqual(form.initial.get("a_conn_1_parent"), self.device.pk)
        self.assertEqual(form.initial.get("a_conn_1_termination"), self.iface_a.pk)

    def test_init_lane_fields_b_side_type_default_from_initial_b_type(self):
        """Validate termination_b_type prepopulation via `initial`."""
        form = CableForm(initial={"termination_b_type": "dcim.consoleserverport"}, data=self._minimal_form_data())
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(form.initial.get("b_conn_1_type"), "consoleserverport")

    def test_init_lane_fields_b_side_type_default_from_a_side_compatibility(self):
        """Validate auto-determination of termination_b_type when provided only a termination_a_type."""
        power_port = self.device.power_ports.create(name="psu-form-test")
        form = CableForm(
            initial={"termination_a_type": "dcim.powerport", "termination_a_id": str(power_port.pk)},
            data=self._minimal_form_data(),
        )
        self.assertTrue(form.is_valid(), msg=form.errors)
        self.assertEqual(form.initial.get("b_conn_1_type"), "poweroutlet")  # *not* "interface"!

    # ── Fallback layout + form error on submission ─────────────────────────────────

    def test_init_lane_fields_unknown_cable_type_pk_from_initial(self):
        """Test nonexistent `cable_type` PK in `initial` is handled gracefully."""
        bad_pk = str(uuid.uuid4())
        form = CableForm(initial={"cable_type": bad_pk}, data=self._minimal_form_data())
        # Layout fell back…
        self.assertIsNone(form.connection_info["cable_type"])
        self.assertEqual(len(form.connection_info["b_side"]), 1)
        # …and on submission the user sees an error.
        form.is_valid()
        self.assertIn("cable_type", form.errors)
        self.assertTrue(any(bad_pk in msg for msg in form.errors["cable_type"]))

    def test_init_lane_fields_malformed_cable_type_pk_from_initial(self):
        """Test non-UUID `cable_type` PK in `initial` is handled gracefully."""
        form = CableForm(initial={"cable_type": "not-a-uuid"}, data=self._minimal_form_data())
        self.assertIsNone(form.connection_info["cable_type"])
        form.is_valid()
        self.assertIn("cable_type", form.errors)

    def test_init_lane_fields_bad_cable_type_in_data_does_not_double_report(self):
        """Test nonexistent `cable_type` PK in POST data is handled gracefully."""
        data = self._minimal_form_data()
        data["cable_type"] = str(uuid.uuid4())
        form = CableForm(data=data)
        form.is_valid()
        # Field-level validation surfaces the error — and only once.
        self.assertIn("cable_type", form.errors)
        self.assertEqual(len(form.errors["cable_type"]), 1)

    def test_init_lane_fields_malformed_initial_a_type_with_id(self):
        """Test malformed `termination_a_type` in `initial` is handled gracefully."""
        form = CableForm(
            initial={"termination_a_type": "garbage-no-dot", "termination_a_id": str(self.iface_a.pk)},
            data=self._minimal_form_data(),
        )
        # No A-side prefill happened.
        self.assertIsNone(form.initial.get("a_conn_1_termination"))
        form.is_valid()
        self.assertIn("a_conn_1_type", form.errors)
        self.assertTrue(any("Invalid termination_a_type" in msg for msg in form.errors["a_conn_1_type"]))

    def test_init_lane_fields_unknown_content_type_for_initial_a_type(self):
        """Test nonexistent `termination_a_type` in `initial` is handled gracefully."""
        form = CableForm(
            initial={"termination_a_type": "dcim.bogusmodel", "termination_a_id": str(self.iface_a.pk)},
            data=self._minimal_form_data(),
        )
        self.assertIsNone(form.initial.get("a_conn_1_termination"))
        form.is_valid()
        self.assertIn("a_conn_1_type", form.errors)

    def test_init_lane_fields_missing_termination_for_initial_a_id(self):
        """Test nonexistent `termination_a_id` in `initial` is handled gracefully."""
        form = CableForm(
            initial={"termination_a_type": "dcim.interface", "termination_a_id": str(uuid.uuid4())},
            data=self._minimal_form_data(),
        )
        self.assertIsNone(form.initial.get("a_conn_1_termination"))
        form.is_valid()
        self.assertIn("a_conn_1_termination", form.errors)
        self.assertTrue(any("Could not load" in msg for msg in form.errors["a_conn_1_termination"]))

    def test_init_lane_fields_malformed_initial_b_type_reports_error(self):
        """Test malformed `termination_b_type` in `initial` is handled gracefully."""
        form = CableForm(initial={"termination_b_type": "garbage-no-dot"}, data=self._minimal_form_data())
        self.assertEqual(form.initial.get("b_conn_1_type"), "interface")  # Fell back to global default.
        form.is_valid()
        self.assertIn("b_conn_1_type", form.errors)
        self.assertTrue(any("Invalid termination_b_type" in msg for msg in form.errors["b_conn_1_type"]))

    # ── `CableForm.get_connection_fields()` — the per-lane row table the template renders. ────

    def test_get_connection_fields_single_row_for_non_breakout(self):
        """A non-breakout cable renders as one row connecting A connector 1 to B connector 1."""
        form = CableForm(instance=self.cable)
        result = form.get_connection_fields()
        self.assertIsNone(result["cable_type"])
        self.assertEqual(len(result["rows"]), 1)
        row = result["rows"][0]
        self.assertEqual((row["a"]["connector"], row["b"]["connector"]), (1, 1))
        self.assertEqual(row["a_rowspan"], 1)
        self.assertEqual(row["b_rowspan"], 1)
        # Each side carries the bound termination fields for that connector.
        self.assertIn("type_field", row["a"])
        self.assertIn("term_field", row["b"])

    def test_get_connection_fields_uses_instance_cable_type_for_breakout(self):
        """For a saved cable whose `cable_type` is a breakout, rows come from `cable_type.mapping`."""
        breakout = self._breakout_cable_type()
        cable = Cable.objects.create(status=self.cable_status, cable_type=breakout)
        result = CableForm(instance=cable).get_connection_fields()
        self.assertIsNotNone(result["cable_type"])
        # 1x4 → 4 rows: A1 spans them all (only the first row carries the A cell), B1..B4 down the side.
        self.assertEqual(len(result["rows"]), 4)
        self.assertEqual(result["rows"][0]["a"]["connector"], 1)
        self.assertEqual([row["b"]["connector"] for row in result["rows"]], [1, 2, 3, 4])

    def test_get_connection_fields_uses_initial_cable_type_for_breakout(self):
        """For an unsaved form whose `initial['cable_type']` is a breakout, rows come from `cable_type.mapping`."""
        breakout = self._breakout_cable_type()
        form = CableForm(initial={"cable_type": str(breakout.pk)})
        result = form.get_connection_fields()
        self.assertIsNotNone(result["cable_type"])
        self.assertEqual(len(result["rows"]), 4)

    def test_get_connection_fields_falls_back_when_initial_cable_type_unknown(self):
        """A bad `initial['cable_type']` makes get_connection_fields` renders a single row."""
        form = CableForm(initial={"cable_type": str(uuid.uuid4())})
        result = form.get_connection_fields()
        self.assertIsNone(result["cable_type"])
        self.assertEqual(len(result["rows"]), 1)

    def test_get_connection_fields_rowspans_for_1x4(self):
        """1x4 layout: the single A-side row spans all four B-side rows."""
        breakout = self._breakout_cable_type()
        cable = Cable.objects.create(status=self.cable_status, cable_type=breakout)
        rows = CableForm(instance=cable).get_connection_fields()["rows"]
        self.assertEqual(rows[0]["a_rowspan"], 4)
        self.assertEqual(rows[0]["b_rowspan"], 1)
        for row in rows[1:]:
            self.assertEqual(row["a_rowspan"], 0)  # Continuation of the merged A cell.
            self.assertEqual(row["b_rowspan"], 1)

    def test_get_connection_fields_dedupes_rows_for_1x1_multi_lane_cable_type(self):
        """Ensure that a cable with multiple lanes per connector generates only a single row, not multiple rows."""
        multi_lane_single_connector = CableType.objects.create(
            name="Form Test 1x1x4", a_connectors=1, b_connectors=1, total_lanes=4
        )
        # Sanity: the auto-generated mapping has 4 entries, all with (a_connector=1, b_connector=1).
        self.assertEqual(len(multi_lane_single_connector.mapping), 4)
        self.assertEqual(
            {(entry["a_connector"], entry["b_connector"]) for entry in multi_lane_single_connector.mapping},
            {(1, 1)},
        )
        cable = Cable.objects.create(status=self.cable_status, cable_type=multi_lane_single_connector)
        result = CableForm(instance=cable).get_connection_fields()
        self.assertIsNotNone(result["cable_type"])
        # Only one row despite four mapping entries — the layout collapses the (1, 1) repeats.
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual((result["rows"][0]["a"]["connector"], result["rows"][0]["b"]["connector"]), (1, 1))

    def _console_cable(self):
        """A saved, valid cable terminating on console ports — not breakout-eligible."""
        cp = ConsolePort.objects.create(device=self.device, name="cp-elig", type=ConsolePortTypeChoices.TYPE_RJ45)
        csp = ConsoleServerPort.objects.create(
            device=self.device, name="csp-elig", type=ConsolePortTypeChoices.TYPE_RJ45
        )
        return Cable.objects.create(termination_a=cp, termination_b=csp, status=self.cable_status)

    def test_cable_type_choices_restricted_not_disabled_for_non_breakout_eligible_cable(self):
        """A non-breakout-eligible cable still allows single-connector cable types; only multi-connector
        types are filtered out, and the field is no longer disabled wholesale."""
        cable = self._console_cable()
        self.assertFalse(cable.breakout_eligible)
        single = CableType.objects.create(name="Choices 1x1", a_connectors=1, b_connectors=1, total_lanes=1)
        multi = CableType.objects.create(name="Choices 1x4", a_connectors=1, b_connectors=4, total_lanes=4)

        field = CableForm(instance=cable).fields["cable_type"]
        self.assertFalse(field.disabled)
        self.assertIn(single, field.queryset)
        self.assertNotIn(multi, field.queryset)

    def test_form_rejects_multi_connector_cable_type_with_ineligible_termination(self):
        """Selecting a multi-connector cable type for console terminations is a form error, not a 500."""
        multi = CableType.objects.create(name="Reject form 1x2", a_connectors=1, b_connectors=2, total_lanes=2)
        cp = ConsolePort.objects.create(device=self.device, name="cp-multi", type=ConsolePortTypeChoices.TYPE_RJ45)
        csp = ConsoleServerPort.objects.create(
            device=self.device, name="csp-multi", type=ConsolePortTypeChoices.TYPE_RJ45
        )
        data = {
            "status": str(self.cable_status.pk),
            "type": "",
            "color": "",
            "length": "",
            "length_unit": "",
            "label": "",
            "cable_type": str(multi.pk),
            "a_conn_1_type": "consoleport",
            "a_conn_1_parent": str(self.device.pk),
            "a_conn_1_termination": str(cp.pk),
            "b_conn_1_type": "consoleserverport",
            "b_conn_1_parent": str(self.device.pk),
            "b_conn_1_termination": str(csp.pk),
        }
        form = CableForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("a_conn_1_termination", form.errors)
        self.assertIn("multi-connector cable type", str(form.errors["a_conn_1_termination"]))

    def test_get_connection_fields_mesh_2x2_is_structurally_valid(self):
        """Regression: a polarity-shuffled 2x2 (mesh) renders as a valid 2-row table without crashing."""
        shuffle = self._shuffle_cable_type()
        cable = Cable.objects.create(status=self.cable_status, cable_type=shuffle)
        # Construction must not raise, and the layout must collapse to two clean rows.
        rows = CableForm(instance=cable).get_connection_fields()["rows"]
        self.assertEqual(len(rows), 2)
        self.assertEqual([row["a"]["connector"] for row in rows], [1, 2])
        self.assertEqual([row["b"]["connector"] for row in rows], [1, 2])
        # Each column's rowspans tile the two rows exactly — no overlap, no skipped-only row.
        self.assertEqual(sum(row["a_rowspan"] for row in rows), 2)
        self.assertEqual(sum(row["b_rowspan"] for row in rows), 2)
