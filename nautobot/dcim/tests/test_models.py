from decimal import Decimal

from constance.test import override_config
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import Model
from django.test import TestCase
from django.test.utils import override_settings

from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.core import settings
from nautobot.core.testing.models import ModelTestCases
from nautobot.dcim.choices import (
    CableStatusChoices,
    CableTypeChoices,
    ConsolePortTypeChoices,
    DeviceFaceChoices,
    InterfaceModeChoices,
    InterfaceTypeChoices,
    PortTypeChoices,
    PowerFeedBreakerPoleChoices,
    PowerFeedPhaseChoices,
    PowerFeedSupplyChoices,
    PowerFeedTypeChoices,
    PowerOutletFeedLegChoices,
    PowerOutletTypeChoices,
    PowerPortTypeChoices,
    SubdeviceRoleChoices,
)
from nautobot.dcim.models import (
    Cable,
    ConsolePort,
    ConsolePortTemplate,
    ConsoleServerPort,
    ConsoleServerPortTemplate,
    Controller,
    ControllerManagedDeviceGroup,
    Device,
    DeviceBay,
    DeviceBayTemplate,
    DeviceRedundancyGroup,
    DeviceType,
    DeviceTypeToSoftwareImageFile,
    FrontPort,
    FrontPortTemplate,
    Interface,
    InterfaceRedundancyGroup,
    InterfaceTemplate,
    InventoryItem,
    Location,
    LocationType,
    Manufacturer,
    Module,
    ModuleBay,
    ModuleBayTemplate,
    ModuleFamily,
    ModuleType,
    Platform,
    PowerFeed,
    PowerOutlet,
    PowerOutletTemplate,
    PowerPanel,
    PowerPort,
    PowerPortTemplate,
    Rack,
    RackGroup,
    RearPort,
    RearPortTemplate,
    SoftwareImageFile,
    SoftwareVersion,
    VirtualDeviceContext,
)
from nautobot.extras import context_managers
from nautobot.extras.choices import CustomFieldTypeChoices
from nautobot.extras.models import CustomField, Role, SecretsGroup, Status
from nautobot.ipam.models import IPAddress, IPAddressToInterface, Namespace, Prefix, VLAN, VLANGroup
from nautobot.tenancy.models import Tenant
from nautobot.users.models import User
from nautobot.virtualization.models import Cluster, ClusterType, VirtualMachine


class ModularDeviceComponentTestCaseMixin:
    """Generic test for modular device components. Also used for testing modular component templates."""

    # fields required to create instances of the model, with the exception of name, device_field and module_field
    modular_component_create_data = {}
    model: type[Model]
    device_field = "device"  # field name for the parent device
    module_field = "module"  # field name for the parent module

    @classmethod
    def setUpTestData(cls):
        cls.device = Device.objects.first()
        cls.module = Module.objects.first()

    def test_parent_validation_device_and_module(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            **{self.device_field: self.device, self.module_field: self.module},
            **self.modular_component_create_data,
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_parent_validation_no_device_or_module(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            **self.modular_component_create_data,
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_parent_validation_succeeds(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        with self.subTest(f"{self.model._meta.model_name} with a parent device"):
            instance = self.model(
                name=f"test {self.model._meta.model_name} 1",
                **{self.device_field: self.device},
                **self.modular_component_create_data,
            )

            instance.full_clean()
            instance.save()

        with self.subTest(f"{self.model._meta.model_name} with a parent module"):
            instance = self.model(
                name=f"test {self.model._meta.model_name} 1",
                **{self.module_field: self.module},
                **self.modular_component_create_data,
            )

            instance.full_clean()
            instance.save()

    def test_uniqueness_device(self):
        """Assert that the combination of device and name is unique."""
        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            **{self.device_field: self.device},
            **self.modular_component_create_data,
        )

        instance.full_clean()
        instance.save()

        # same device, different name works
        instance = self.model(
            name=f"test {self.model._meta.model_name} 2",
            **{self.device_field: self.device},
            **self.modular_component_create_data,
        )

        instance.full_clean()
        instance.save()

        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            **{self.device_field: self.device},
            **self.modular_component_create_data,
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

        with self.assertRaises(IntegrityError):
            instance.save()

    def test_uniqueness_module(self):
        """Assert that the combination of module and name is unique."""
        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            **{self.module_field: self.module},
            **self.modular_component_create_data,
        )

        instance.full_clean()
        instance.save()

        # same module, different name works
        instance = self.model(
            name=f"test {self.model._meta.model_name} 2",
            **{self.module_field: self.module},
            **self.modular_component_create_data,
        )

        instance.full_clean()
        instance.save()

        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            **{self.module_field: self.module},
            **self.modular_component_create_data,
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

        with self.assertRaises(IntegrityError):
            instance.save()


class ConsolePortTestCase(ModularDeviceComponentTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = ConsolePort
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}


class ConsoleServerPortTestCase(ModularDeviceComponentTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = ConsoleServerPort
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}


class PowerPortTestCase(ModularDeviceComponentTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = PowerPort
    modular_component_create_data = {"type": PowerPortTypeChoices.TYPE_NEMA_1030P}


class PowerOutletTestCase(ModularDeviceComponentTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = PowerOutlet
    modular_component_create_data = {"type": PowerOutletTypeChoices.TYPE_IEC_C13}


class RearPortTestCase(ModularDeviceComponentTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = RearPort
    modular_component_create_data = {"type": PortTypeChoices.TYPE_8P8C}


class FrontPortTestCase(ModelTestCases.BaseModelTestCase):
    model = FrontPort

    @classmethod
    def setUpTestData(cls):
        cls.module = Module.objects.filter(rear_ports__isnull=False).first()
        cls.module_rear_port = cls.module.rear_ports.first()
        module_used_positions = set(cls.module_rear_port.front_ports.values_list("rear_port_position", flat=True))
        cls.module_available_positions = set(range(1, cls.module_rear_port.positions + 1)).difference(
            module_used_positions
        )

        cls.device = Device.objects.filter(rear_ports__isnull=False).first()
        cls.device_rear_port = cls.device.rear_ports.first()
        device_used_positions = set(cls.device_rear_port.front_ports.values_list("rear_port_position", flat=True))
        cls.device_available_positions = set(range(1, cls.device_rear_port.positions + 1)).difference(
            device_used_positions
        )

    def test_parent_validation_device_and_module(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        instance = self.model(
            device=self.device,
            module=self.module,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.module_rear_port,
            rear_port_position=self.module_available_positions.copy().pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_parent_validation_no_device_or_module(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.module_rear_port,
            rear_port_position=self.module_available_positions.copy().pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_parent_validation_succeeds(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        with self.subTest(f"{self.model._meta.model_name} with a parent device"):
            instance = self.model(
                device=self.device,
                name=f"test {self.model._meta.model_name} 1",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=self.device_rear_port,
                rear_port_position=self.device_available_positions.copy().pop(),
            )

            instance.full_clean()
            instance.save()

        with self.subTest(f"{self.model._meta.model_name} with a parent module"):
            instance = self.model(
                module=self.module,
                name=f"test {self.model._meta.model_name} 1",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port=self.module_rear_port,
                rear_port_position=self.module_available_positions.copy().pop(),
            )

            instance.full_clean()
            instance.save()

    def test_uniqueness_device(self):
        """Assert that the combination of device and name is unique."""
        device_available_positions = self.device_available_positions.copy()
        instance = self.model(
            device=self.device,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.device_rear_port,
            rear_port_position=device_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        # same device, different name works
        instance = self.model(
            device=self.device,
            name=f"test {self.model._meta.model_name} 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.device_rear_port,
            rear_port_position=device_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        instance = self.model(
            device=self.device,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.device_rear_port,
            rear_port_position=device_available_positions.pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

        with self.assertRaises(IntegrityError):
            instance.save()

    def test_uniqueness_module(self):
        """Assert that the combination of module and name is unique."""
        module_available_positions = self.module_available_positions.copy()
        instance = self.model(
            module=self.module,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.module_rear_port,
            rear_port_position=module_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        # same module, different name works
        instance = self.model(
            module=self.module,
            name=f"test {self.model._meta.model_name} 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.module_rear_port,
            rear_port_position=module_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        instance = self.model(
            module=self.module,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=self.module_rear_port,
            rear_port_position=module_available_positions.pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

        with self.assertRaises(IntegrityError):
            instance.save()


class ModularDeviceComponentTemplateTestCaseMixin(ModularDeviceComponentTestCaseMixin):
    """Generic test for modular device component templates."""

    device_field = "device_type"  # field name for the parent device_type
    module_field = "module_type"  # field name for the parent module_type

    @classmethod
    def setUpTestData(cls):
        cls.device = DeviceType.objects.first()
        cls.module = ModuleType.objects.first()


class ConsolePortTemplateTestCase(ModularDeviceComponentTemplateTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = ConsolePortTemplate
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}


class ConsoleServerPortTemplateTestCase(ModularDeviceComponentTemplateTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = ConsoleServerPortTemplate
    modular_component_create_data = {"type": ConsolePortTypeChoices.TYPE_RJ45}


class PowerPortTemplateTestCase(ModularDeviceComponentTemplateTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = PowerPortTemplate
    modular_component_create_data = {"type": PowerPortTypeChoices.TYPE_NEMA_1030P}


class PowerOutletTemplateTestCase(ModularDeviceComponentTemplateTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = PowerOutletTemplate
    modular_component_create_data = {"type": PowerOutletTypeChoices.TYPE_IEC_C13}


class RearPortTemplateTestCase(ModularDeviceComponentTemplateTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = RearPortTemplate
    modular_component_create_data = {"type": PortTypeChoices.TYPE_8P8C}


class FrontPortTemplateTestCase(ModelTestCases.BaseModelTestCase):
    model = FrontPortTemplate

    @classmethod
    def setUpTestData(cls):
        cls.module_type = ModuleType.objects.filter(rear_port_templates__isnull=False).first()
        cls.module_rear_port = cls.module_type.rear_port_templates.first()
        module_used_positions = set(
            cls.module_rear_port.front_port_templates.values_list("rear_port_position", flat=True)
        )
        cls.module_available_positions = set(range(1, cls.module_rear_port.positions + 1)).difference(
            module_used_positions
        )

        cls.device_type = DeviceType.objects.filter(rear_port_templates__isnull=False).first()
        cls.device_rear_port = cls.device_type.rear_port_templates.first()
        device_used_positions = set(
            cls.device_rear_port.front_port_templates.values_list("rear_port_position", flat=True)
        )
        cls.device_available_positions = set(range(1, cls.device_rear_port.positions + 1)).difference(
            device_used_positions
        )

    def test_parent_validation_device_and_module(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        instance = self.model(
            device_type=self.device_type,
            module_type=self.module_type,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.module_rear_port,
            rear_port_position=self.module_available_positions.copy().pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_parent_validation_no_device_or_module(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        instance = self.model(
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.module_rear_port,
            rear_port_position=self.module_available_positions.copy().pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

    def test_parent_validation_succeeds(self):
        """Assert that a modular component must have a parent device or parent module but not both."""
        with self.subTest(f"{self.model._meta.model_name} with a parent device"):
            instance = self.model(
                device_type=self.device_type,
                name=f"test {self.model._meta.model_name} 1",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port_template=self.device_rear_port,
                rear_port_position=self.device_available_positions.copy().pop(),
            )

            instance.full_clean()
            instance.save()

        with self.subTest(f"{self.model._meta.model_name} with a parent module"):
            instance = self.model(
                module_type=self.module_type,
                name=f"test {self.model._meta.model_name} 1",
                type=PortTypeChoices.TYPE_8P8C,
                rear_port_template=self.module_rear_port,
                rear_port_position=self.module_available_positions.copy().pop(),
            )

            instance.full_clean()
            instance.save()

    def test_uniqueness_device(self):
        """Assert that the combination of device and name is unique."""
        device_available_positions = self.device_available_positions.copy()
        instance = self.model(
            device_type=self.device_type,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.device_rear_port,
            rear_port_position=device_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        # same device, different name works
        instance = self.model(
            device_type=self.device_type,
            name=f"test {self.model._meta.model_name} 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.device_rear_port,
            rear_port_position=device_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        instance = self.model(
            device_type=self.device_type,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.device_rear_port,
            rear_port_position=device_available_positions.pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

        with self.assertRaises(IntegrityError):
            instance.save()

    def test_uniqueness_module(self):
        """Assert that the combination of module and name is unique."""
        module_available_positions = self.module_available_positions.copy()
        instance = self.model(
            module_type=self.module_type,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.module_rear_port,
            rear_port_position=module_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        # same module, different name works
        instance = self.model(
            module_type=self.module_type,
            name=f"test {self.model._meta.model_name} 2",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.module_rear_port,
            rear_port_position=module_available_positions.pop(),
        )

        instance.full_clean()
        instance.save()

        instance = self.model(
            module_type=self.module_type,
            name=f"test {self.model._meta.model_name} 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=self.module_rear_port,
            rear_port_position=module_available_positions.pop(),
        )

        with self.assertRaises(ValidationError):
            instance.full_clean()

        with self.assertRaises(IntegrityError):
            instance.save()


class CableLengthTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        cls.manufacturer = Manufacturer.objects.first()
        cls.devicetype = DeviceType.objects.create(
            manufacturer=cls.manufacturer,
            model="Test Device Type 1",
        )
        cls.devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        cls.device1 = Device.objects.create(
            device_type=cls.devicetype,
            role=cls.devicerole,
            name="TestDevice1",
            location=cls.location,
            status=devicestatus,
        )
        cls.device2 = Device.objects.create(
            device_type=cls.devicetype,
            role=cls.devicerole,
            name="TestDevice2",
            location=cls.location,
            status=devicestatus,
        )
        cls.status = Status.objects.get_for_model(Cable).get(name="Connected")

    def test_cable_validated_save(self):
        interfacestatus = Status.objects.get_for_model(Interface).first()
        interface1 = Interface.objects.create(device=self.device1, name="eth0", status=interfacestatus)
        interface2 = Interface.objects.create(device=self.device2, name="eth0", status=interfacestatus)
        cable = Cable(
            termination_a=interface1,
            termination_b=interface2,
            length_unit="ft",
            length=1,
            status=self.status,
        )
        cable.validated_save()
        cable.validated_save()

    def test_cable_full_clean(self):
        interfacestatus = Status.objects.get_for_model(Interface).first()
        interface3 = Interface.objects.create(device=self.device1, name="eth1", status=interfacestatus)
        interface4 = Interface.objects.create(device=self.device2, name="eth1", status=interfacestatus)
        cable = Cable(
            termination_a=interface3,
            termination_b=interface4,
            length_unit="in",
            length=1,
            status=self.status,
        )
        cable.length = 2
        cable.save()
        cable.full_clean()


class InterfaceTemplateCustomFieldTestCase(TestCase):
    def test_instantiate_model(self):
        """
        Check that all _custom_field_data is present and all customfields are filled with the correct default values.
        """
        statuses = Status.objects.get_for_model(Device)
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_role = Role.objects.get_for_model(Device).first()
        custom_fields = [
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, label="Field 1", default="value_1"),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, label="Field 2", default="value_2"),
            CustomField.objects.create(type=CustomFieldTypeChoices.TYPE_TEXT, label="Field 3", default="value_3"),
        ]
        for custom_field in custom_fields:
            custom_field.content_types.set([ContentType.objects.get_for_model(Interface)])
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="FrameForwarder 2048")
        interface_template_1 = InterfaceTemplate.objects.create(
            device_type=device_type,
            name="Test_Template_1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        )
        interface_template_2 = InterfaceTemplate.objects.create(
            device_type=device_type,
            name="Test_Template_2",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        )
        interface_templates = [interface_template_1, interface_template_2]
        device_type.interface_templates.set(interface_templates)
        # instantiate_model() is run when device is created
        device = Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=statuses[0],
            name="Test Device",
            location=location,
        )
        interfaces = device.interfaces.all()
        self.assertEqual(Interface.objects.get(pk=interfaces[0].pk).cf["field_1"], "value_1")
        self.assertEqual(Interface.objects.get(pk=interfaces[0].pk).cf["field_2"], "value_2")
        self.assertEqual(Interface.objects.get(pk=interfaces[0].pk).cf["field_3"], "value_3")
        self.assertEqual(Interface.objects.get(pk=interfaces[1].pk).cf["field_1"], "value_1")
        self.assertEqual(Interface.objects.get(pk=interfaces[1].pk).cf["field_2"], "value_2")
        self.assertEqual(Interface.objects.get(pk=interfaces[1].pk).cf["field_3"], "value_3")


class InterfaceTemplateTestCase(ModularDeviceComponentTemplateTestCaseMixin, TestCase):
    modular_component_create_data = {"type": InterfaceTypeChoices.TYPE_1GE_FIXED}
    model = InterfaceTemplate

    def test_interface_template_sets_interface_status(self):
        """
        When a device is created with a device type associated with the template,
        assert interface templates sets the interface status.
        """
        statuses = Status.objects.get_for_model(Device)
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        manufacturer = Manufacturer.objects.first()
        device_role = Role.objects.get_for_model(Device).first()
        device_type = DeviceType.objects.create(manufacturer=manufacturer, model="FrameForwarder 2048")
        InterfaceTemplate.objects.create(
            device_type=device_type,
            name="Test_Template_1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        )
        device_1 = Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=statuses[0],
            name="Test Device 1",
            location=location,
        )

        status = Status.objects.get_for_model(Interface).get(name="Active")
        self.assertEqual(device_1.interfaces.get(name="Test_Template_1").status, status)

        # Assert that a different status is picked if active status is not found for interface
        interface_ct = ContentType.objects.get_for_model(Interface)
        status.content_types.remove(interface_ct)

        device_2 = Device.objects.create(
            device_type=device_type,
            role=device_role,
            status=statuses[0],
            name="Test Device 2",
            location=location,
        )
        first_status = Status.objects.get_for_model(Interface).first()
        self.assertIsNotNone(device_2.interfaces.get(name="Test_Template_1").status, first_status)


class InterfaceRedundancyGroupTestCase(ModelTestCases.BaseModelTestCase):
    model = InterfaceRedundancyGroup

    @classmethod
    def setUpTestData(cls):
        statuses = Status.objects.get_for_model(InterfaceRedundancyGroup)
        cls.ips = IPAddress.objects.all()
        cls.secrets_groups = (
            SecretsGroup.objects.create(name="Secrets Group 1"),
            SecretsGroup.objects.create(name="Secrets Group 2"),
            SecretsGroup.objects.create(name="Secrets Group 3"),
        )

        cls.interface_redundancy_groups = (
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 1",
                protocol="hsrp",
                status=statuses[0],
                virtual_ip=None,
                secrets_group=cls.secrets_groups[0],
                protocol_group_id="1",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 2",
                protocol="carp",
                status=statuses[1],
                virtual_ip=cls.ips[1],
                secrets_group=cls.secrets_groups[1],
                protocol_group_id="2",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 3",
                protocol="vrrp",
                status=statuses[2],
                virtual_ip=cls.ips[2],
                secrets_group=None,
                protocol_group_id="3",
            ),
            InterfaceRedundancyGroup(
                name="Interface Redundancy Group 4",
                protocol="glbp",
                status=statuses[3],
                virtual_ip=cls.ips[3],
                secrets_group=cls.secrets_groups[2],
            ),
        )

        for group in cls.interface_redundancy_groups:
            group.validated_save()

        cls.device_type = DeviceType.objects.first()
        cls.device_role = Role.objects.get_for_model(Device).first()
        cls.device_status = Status.objects.get_for_model(Device).first()
        cls.location = Location.objects.filter(location_type__name="Campus").first()
        cls.device = Device.objects.create(
            device_type=cls.device_type,
            role=cls.device_role,
            name="Device 1",
            location=cls.location,
            status=cls.device_status,
        )
        non_default_status = Status.objects.get_for_model(Interface).exclude(name="Active").first()
        cls.interfaces = (
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 1",
                type="1000base-t",
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 2",
                type="1000base-t",
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 3",
                type=InterfaceTypeChoices.TYPE_BRIDGE,
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 4",
                type=InterfaceTypeChoices.TYPE_1GE_GBIC,
                status=non_default_status,
            ),
            Interface.objects.create(
                device=cls.device,
                name="Test Interface 5",
                type=InterfaceTypeChoices.TYPE_LAG,
                status=non_default_status,
            ),
        )

    def test_add_interface(self):
        interfaces = Interface.objects.all()
        interface_redundancy_group = self.interface_redundancy_groups[0]
        previous_count = interface_redundancy_group.interfaces.count()
        for i in range(3):
            interface_redundancy_group.add_interface(interfaces[i], i * 100)
        after_count = interface_redundancy_group.interfaces.count()
        self.assertEqual(previous_count + 3, after_count)

    def test_remove_interface(self):
        interfaces = Interface.objects.all()
        interface_redundancy_group = self.interface_redundancy_groups[0]
        for i in range(3):
            interface_redundancy_group.add_interface(interfaces[i], i * 100)
        previous_count = interface_redundancy_group.interfaces.count()
        self.assertEqual(previous_count, 3)
        for i in range(2):
            interface_redundancy_group.remove_interface(interfaces[i])
        after_count = interface_redundancy_group.interfaces.count()
        self.assertEqual(after_count, 1)


class RackGroupTestCase(ModelTestCases.BaseModelTestCase):
    model = RackGroup

    @classmethod
    def setUpTestData(cls):
        """
        Location A
          - RackGroup A1
            - RackGroup A2
              - Rack 2
            - Rack 1
            - PowerPanel 1
        """
        cls.location_type_a = LocationType.objects.get(name="Campus")
        cls.location_a = Location.objects.filter(location_type=cls.location_type_a).first()
        cls.location_status = Status.objects.get_for_model(Location).first()
        cls.rackgroup_a1 = RackGroup(location=cls.location_a, name="RackGroup A1")
        cls.rackgroup_a1.save()
        cls.rackgroup_a2 = RackGroup(location=cls.location_a, parent=cls.rackgroup_a1, name="RackGroup A2")
        cls.rackgroup_a2.save()

        rack_status = Status.objects.get_for_model(Rack).first()
        cls.rack1 = Rack.objects.create(
            location=cls.location_a, rack_group=cls.rackgroup_a1, name="Rack 1", status=rack_status
        )
        cls.rack2 = Rack.objects.create(
            location=cls.location_a, rack_group=cls.rackgroup_a2, name="Rack 2", status=rack_status
        )

        cls.powerpanel1 = PowerPanel.objects.create(
            location=cls.location_a, rack_group=cls.rackgroup_a1, name="Power Panel 1"
        )

    def test_rackgroup_location_validation(self):
        """Check that rack group locations are validated correctly."""
        # Group location, if specified, must permit RackGroups
        location_type_c = LocationType.objects.get(name="Elevator")
        location_c = Location.objects.create(
            name="Location C", location_type=location_type_c, status=self.location_status
        )
        child = RackGroup(parent=self.rackgroup_a1, location=location_c, name="Child Group")
        with self.assertRaises(ValidationError) as cm:
            child.validated_save()
        self.assertIn(f'Rack groups may not associate to locations of type "{location_type_c}"', str(cm.exception))

        # Child group location must descend from parent group location
        location_type_d = LocationType.objects.get(name="Room")
        location_type_d.content_types.add(ContentType.objects.get_for_model(RackGroup))
        location_d = Location.objects.create(
            name="Location D", location_type=location_type_d, parent=location_c, status=self.location_status
        )
        child = RackGroup(parent=self.rackgroup_a1, location=location_d, name="Child Group")
        with self.assertRaises(ValidationError) as cm:
            child.validated_save()
        self.assertIn(
            f'Location "Location D" is not descended from parent rack group "RackGroup A1" location "{self.location_a.name}"',
            str(cm.exception),
        )

    def test_change_rackgroup_location_children_permitted(self):
        """
        Check that all child RackGroups, Racks, and PowerPanels get updated when a RackGroup changes Locations.

        In this test, the new Location permits Racks and PowerPanels so the Location should match.
        """
        location_b = Location.objects.create(
            name="Location B", location_type=self.location_type_a, status=self.location_status
        )

        self.rackgroup_a1.location = location_b
        self.rackgroup_a1.save()

        self.assertEqual(RackGroup.objects.get(pk=self.rackgroup_a1.pk).location, location_b)
        self.assertEqual(RackGroup.objects.get(pk=self.rackgroup_a2.pk).location, location_b)
        self.assertEqual(Rack.objects.get(pk=self.rack1.pk).location, location_b)
        self.assertEqual(Rack.objects.get(pk=self.rack2.pk).location, location_b)
        self.assertEqual(PowerPanel.objects.get(pk=self.powerpanel1.pk).location, location_b)

    def test_change_rackgroup_location_children_not_permitted(self):
        """
        Check that all child RackGroups, Racks, and PowerPanels get updated when a RackGroup changes Locations.

        In this test, the new location does not permit Racks and PowerPanels so the Location should be nulled.
        """
        location_type_c = LocationType.objects.create(name="Location Type C", parent=self.location_type_a)
        location_type_c.content_types.add(ContentType.objects.get_for_model(RackGroup))
        location_c = Location.objects.create(
            name="Location C", location_type=location_type_c, parent=self.location_a, status=self.location_status
        )

        self.rackgroup_a1.location = location_c
        with self.assertRaises(ValidationError) as cm:
            self.rackgroup_a1.save()
        self.assertIn(f'Racks may not associate to locations of type "{location_type_c}"', str(cm.exception))
        self.assertEqual(RackGroup.objects.get(pk=self.rackgroup_a2.pk).location, self.location_a)
        self.assertEqual(Rack.objects.get(pk=self.rack1.pk).location, self.location_a)
        self.assertEqual(Rack.objects.get(pk=self.rack2.pk).location, self.location_a)
        self.assertEqual(PowerPanel.objects.get(pk=self.powerpanel1.pk).location, self.location_a)


class RackTestCase(ModelTestCases.BaseModelTestCase):
    model = Rack

    @classmethod
    def setUpTestData(cls):
        cls.status = Status.objects.get_for_model(Rack).first()
        cls.location_type_a = LocationType.objects.create(name="Location Type A")
        cls.location_type_a.content_types.add(
            ContentType.objects.get_for_model(RackGroup),
            ContentType.objects.get_for_model(Rack),
            ContentType.objects.get_for_model(Device),
        )

        cls.location_status = Status.objects.get_for_model(Location).first()
        cls.location1 = Location.objects.create(
            name="Location1", location_type=cls.location_type_a, status=cls.location_status
        )
        cls.location2 = Location.objects.create(
            name="Location2", location_type=cls.location_type_a, status=cls.location_status
        )
        cls.group1 = RackGroup.objects.create(name="TestGroup1", location=cls.location1)
        cls.group2 = RackGroup.objects.create(name="TestGroup2", location=cls.location2)
        cls.rack = Rack.objects.create(
            name="TestRack1",
            facility_id="A101",
            location=cls.location1,
            rack_group=cls.group1,
            status=cls.status,
            u_height=42,
        )
        cls.manufacturer = Manufacturer.objects.first()

        cls.device_type = {
            "ff2048": DeviceType.objects.create(
                manufacturer=cls.manufacturer,
                model="FrameForwarder 2048",
            ),
            "cc5000": DeviceType.objects.create(
                manufacturer=cls.manufacturer,
                model="CurrentCatapult 5000",
                u_height=0,
            ),
        }
        cls.roles = Role.objects.get_for_model(Rack)
        cls.device_roles = Role.objects.get_for_model(Device)
        cls.device_status = Status.objects.get_for_model(Device).first()

    def test_rack_device_outside_height(self):
        rack1 = Rack(
            name="TestRack2",
            facility_id="A102",
            location=self.location1,
            status=self.status,
            u_height=42,
        )
        rack1.save()

        device1 = Device(
            name="TestSwitch1",
            device_type=self.device_type["ff2048"],
            role=self.device_roles[0],
            status=self.device_status,
            location=self.location1,
            rack=rack1,
            position=43,
            face=DeviceFaceChoices.FACE_FRONT,
        )
        device1.save()

        with self.assertRaises(ValidationError):
            rack1.clean()

    def test_mount_single_device(self):
        device1 = Device(
            name="TestSwitch1",
            device_type=self.device_type["ff2048"],
            role=self.device_roles[1],
            status=self.device_status,
            location=self.location1,
            rack=self.rack,
            position=10,
            face=DeviceFaceChoices.FACE_REAR,
        )
        device1.save()

        # Validate rack height
        self.assertEqual(list(self.rack.units), list(reversed(range(1, 43))))

        # Validate inventory (front face)
        rack1_inventory_front = self.rack.get_rack_units(face=DeviceFaceChoices.FACE_FRONT)
        self.assertEqual(rack1_inventory_front[-10]["device"], device1)
        del rack1_inventory_front[-10]
        for u in rack1_inventory_front:
            self.assertIsNone(u["device"])

        # Validate inventory (rear face)
        rack1_inventory_rear = self.rack.get_rack_units(face=DeviceFaceChoices.FACE_REAR)
        self.assertEqual(rack1_inventory_rear[-10]["device"], device1)
        del rack1_inventory_rear[-10]
        for u in rack1_inventory_rear:
            self.assertIsNone(u["device"])

    def test_mount_zero_ru(self):
        pdu = Device.objects.create(
            name="TestPDU",
            role=self.device_roles[3],
            status=self.device_status,
            device_type=self.device_type.get("cc5000"),
            location=self.location1,
            rack=self.rack,
            position=None,
            face="",
        )
        self.assertTrue(pdu)

    def test_change_rack_location_devices_permitted(self):
        """
        Check that changing a Rack's Location also affects child Devices.

        In this test, the new Location also permits Devices.
        """
        # Device1 is explicitly assigned to the same location as the Rack
        device1 = Device.objects.create(
            location=self.location1,
            rack=self.rack,
            device_type=self.device_type["cc5000"],
            role=self.device_roles[3],
            status=self.device_status,
        )
        # Device2 is explicitly assigned to the same location as the Rack
        device2 = Device.objects.create(
            location=self.location1,
            rack=self.rack,
            device_type=self.device_type["cc5000"],
            role=self.device_roles[3],
            status=self.device_status,
        )

        # Move self.rack to a new location
        self.rack.location = self.location2
        self.rack.save()

        self.assertEqual(Device.objects.get(pk=device1.pk).location, self.location2)
        self.assertEqual(Device.objects.get(pk=device2.pk).location, self.location2)

    def test_change_rack_location_devices_not_permitted(self):
        """
        Check that changing a Rack's Location also affects child Devices.

        In this test, the new Location does not permit Devices.
        """
        Device.objects.create(
            location=self.location1,
            rack=self.rack,
            device_type=self.device_type["cc5000"],
            role=self.device_roles[3],
            status=self.device_status,
        )

        # Move self.rack to a new location that permits Racks but not Devices
        location_type_b = LocationType.objects.create(name="Location Type B")
        location_type_b.content_types.add(ContentType.objects.get_for_model(Rack))
        location3 = Location.objects.create(
            name="Location3", location_type=location_type_b, status=self.location_status
        )
        self.rack.location = location3
        with self.assertRaises(ValidationError) as cm:
            self.rack.save()
        self.assertIn(f'Devices may not associate to locations of type "{location_type_b}"', str(cm.exception))

    def test_rack_location_validation(self):
        # Rack group location and rack location must relate
        rack = Rack(name="Rack", rack_group=self.group1, location=self.location2, status=self.status)
        with self.assertRaises(ValidationError) as cm:
            rack.validated_save()
        self.assertIn(
            'group "TestGroup1" belongs to a location ("Location1") that does not include location "Location2"',
            str(cm.exception),
        )

        # Location type must permit Racks
        location_type_b = LocationType.objects.create(name="Location Type B")
        locationb = Location.objects.create(
            name="Location3", location_type=location_type_b, status=self.location_status
        )
        rack = Rack(name="Rack", location=locationb, status=self.status)
        with self.assertRaises(ValidationError) as cm:
            rack.validated_save()
        self.assertIn('Racks may not associate to locations of type "Location Type B"', str(cm.exception))


class LocationTypeTestCase(TestCase):
    def test_reserved_names(self):
        """Confirm that certain names are reserved for now."""
        for candidate_name in (
            "RackGroup",
            "rack groups",
        ):
            with self.assertRaises(ValidationError) as cm:
                LocationType(name=candidate_name).clean()
            self.assertIn("This name is reserved", str(cm.exception))

    def test_changing_parent(self):
        """Validate clean logic around changing the parent of a LocationType."""
        parent = LocationType.objects.create(name="Parent LocationType")
        child = LocationType.objects.create(name="Child LocationType")

        # If there are no Locations using it yet, parent can be freely changed
        child.parent = None
        child.validated_save()
        child.parent = parent
        child.validated_save()

        # Once there are Locations using it, parent cannot be changed.
        parent_loc = Location.objects.create(
            name="Parent 1", location_type=parent, status=Status.objects.get_for_model(Location).first()
        )
        child_loc = Location.objects.create(
            name="Child 1", location_type=child, parent=parent_loc, status=Status.objects.get_for_model(Location).last()
        )
        child.parent = None
        with self.assertRaisesMessage(
            ValidationError,
            "This LocationType currently has Locations using it, therefore its parent cannot be changed at this time.",
        ):
            child.validated_save()

        # If the locations are deleted, it again becomes re-parent-able.
        child_loc.delete()
        child.validated_save()

    def test_removing_content_type(self):
        """Validation check to prevent removing an in-use content type from a LocationType."""

        location_type = LocationType.objects.get(name="Campus")
        device_ct = ContentType.objects.get_for_model(Device)

        with self.assertRaises(ValidationError) as cm:
            location_type.content_types.remove(device_ct)
        self.assertIn(
            f"Cannot remove the content type {device_ct} as currently at least one device is associated to a location",
            str(cm.exception),
        )


class LocationTestCase(ModelTestCases.BaseModelTestCase):
    model = Location

    def setUp(self):
        self.root_type = LocationType.objects.get(name="Campus")
        self.intermediate_type = LocationType.objects.get(name="Building")
        self.leaf_type = LocationType.objects.get(name="Floor")

        self.root_nestable_type = LocationType.objects.get(name="Root")
        self.leaf_nestable_type = LocationType.objects.create(
            name="Pseudo-RackGroup", parent=self.root_nestable_type, nestable=True
        )

        self.status = Status.objects.get_for_model(Location).first()

    def test_custom_natural_key_field_lookups(self):
        """Test that the custom implementation of Location.natural_key_field_lookups works as intended."""
        # We know that with current test data, the maximum tree depth is 5:
        # Campus-00 -> Campus-07 -> Building-29 -> Floor-32 -> Room-39
        # but let's try to make this a *bit* more robust!
        expected = [
            "name",
            "parent__name",
            "parent__parent__name",
            "parent__parent__parent__name",
            "parent__parent__parent__parent__name",
            "parent__parent__parent__parent__parent__name",
            "parent__parent__parent__parent__parent__parent__name",
            "parent__parent__parent__parent__parent__parent__parent__name",
        ][: Location.objects.max_depth + 1]
        self.assertEqual(len(expected), Location.objects.max_depth + 1, "Not enough expected entries, fix the test!")
        self.assertEqual(expected, Location.natural_key_field_lookups)
        # Grab an arbitrary leaf node
        location = Location.objects.filter(parent__isnull=False, children__isnull=True).first()
        # Since we trim trailing None from the natural key, it may not be as many as `expected`, but since it's a leaf
        # of some sort, it should definitely have more than just the single `name`.
        self.assertGreater(len(location.natural_key()), 1)
        self.assertLessEqual(len(location.natural_key()), len(expected))
        self.assertEqual(location, Location.objects.get_by_natural_key(location.natural_key()))

    @override_config(LOCATION_NAME_AS_NATURAL_KEY=True)
    def test_custom_natural_key_field_lookups_override(self):
        """Test that just name is used as the natural key when LOCATION_NAME_AS_NATURAL_KEY is set."""
        self.assertEqual(["name"], Location.natural_key_field_lookups)
        # Grab an arbitrary leaf node
        location = Location.objects.filter(parent__isnull=False, children__isnull=True).first()
        self.assertEqual([location.name], location.natural_key())
        # self.assertEqual(construct_composite_key([location.name]), location.composite_key)  # TODO: Revist this if we reintroduce composite keys
        self.assertEqual(location, Location.objects.get_by_natural_key([location.name]))
        # self.assertEqual(location, Location.objects.get(composite_key=location.composite_key))  # TODO: Revist this if we reintroduce composite keys

    def test_custom_natural_key_args_to_kwargs(self):
        """Test that the custom implementation of Location.natural_key_args_to_kwargs works as intended."""
        natural_key_field_lookups = Location.natural_key_field_lookups
        for args in [
            # fewer args than natural_key_field_lookups
            ("me",),
            ("me", "my_parent", "my_grandparent"),
            # more args than natural_key_field_lookups
            ("me", "my_parent", "my_grandparent", "my_g_gp", "my_g2_gp", "my_g3_gp", "my_g4_gp", "my_g5_gp"),
        ]:
            kwargs = Location.natural_key_args_to_kwargs(args)
            self.assertEqual(len(kwargs), max(len(args), len(natural_key_field_lookups)))
            for i, value in enumerate(kwargs.values()):
                if i < len(args):
                    self.assertEqual(args[i], value)
                else:
                    # not-specified args get set as None
                    self.assertIsNone(value)

    def test_latitude_or_longitude(self):
        """Test latitude and longitude is parsed to string."""
        status = Status.objects.get_for_model(Location).first()
        location = Location(
            location_type=self.root_type,
            name="Location A",
            status=status,
            longitude=55.1234567896,
            latitude=55.1234567896,
        )
        location.validated_save()

        self.assertEqual(location.longitude, Decimal("55.123457"))
        self.assertEqual(location.latitude, Decimal("55.123457"))

    def test_validate_unique(self):
        """Confirm that the uniqueness constraint on (parent, name) works when parent is None."""
        location_1 = Location(name="Campus 1", location_type=self.root_type, status=self.status)
        location_1.validated_save()

        location_2 = Location(name="Campus 1", location_type=self.root_type, status=self.status)
        with self.assertRaises(ValidationError):
            location_2.validated_save()

    def test_changing_type_forbidden(self):
        """Once created, a location cannot change location_type."""
        location = Location(name="Campus 1", location_type=self.root_type, status=self.status)
        location.validated_save()
        location.location_type = self.root_nestable_type
        with self.assertRaises(ValidationError) as cm:
            location.validated_save()
        self.assertIn("location_type", str(cm.exception))
        self.assertIn("not permitted", str(cm.exception))

    def test_parent_type_must_match(self):
        """A location's parent's location_type must match its location_type's parent."""
        location_1 = Location(name="Building 1", location_type=self.root_type, status=self.status)
        location_1.validated_save()
        location_2 = Location(name="Room 1", location_type=self.leaf_type, parent=location_1, status=self.status)
        with self.assertRaises(ValidationError) as cm:
            location_2.validated_save()
        self.assertIn(
            "A Location of type Floor can only have a Location of type Building as its parent.", str(cm.exception)
        )

    def test_parent_type_nestable_logic(self):
        """A location of a nestable type may have a parent of the same type."""
        # A location using a root-level nestable type can have no parent
        location_1 = Location(name="Region 1", location_type=self.root_nestable_type, status=self.status)
        location_1.validated_save()
        # A location using a root-level nestable type can have no parent
        location_2 = Location(
            name="Region 1-A", location_type=self.root_nestable_type, parent=location_1, status=self.status
        )
        location_2.validated_save()
        # A location using a lower-level nestable type can be parented under the parent location type
        location_3 = Location(
            name="RackGroup 3", location_type=self.leaf_nestable_type, parent=location_2, status=self.status
        )
        location_3.validated_save()
        # A location using a lower-level nestable type can be parented under its own type
        location_4 = Location(
            name="RackGroup 3-B", location_type=self.leaf_nestable_type, parent=location_3, status=self.status
        )
        location_4.validated_save()
        # Can't mix and match location types though
        with self.assertRaises(ValidationError) as cm:
            location_5 = Location(
                name="Region 5", location_type=self.root_nestable_type, parent=location_4, status=self.status
            )
            location_5.validated_save()
        self.assertIn("only have a Location of the same type as its parent", str(cm.exception))
        location_6 = Location(name="Campus 1", location_type=self.root_type, status=self.status)
        location_6.validated_save()
        with self.assertRaises(ValidationError) as cm:
            location_7 = Location(
                name="RackGroup 7",
                location_type=self.leaf_nestable_type,
                parent=location_6,
                status=self.status,
            )
            location_7.validated_save()
        self.assertIn(
            f"only have a Location of the same type or of type {self.root_nestable_type} as its parent",
            str(cm.exception),
        )

    def test_default_treemodel_display(self):
        location_1 = Location(name="Building 1", location_type=self.root_type, status=self.status)
        location_1.validated_save()
        location_2 = Location(name="Room 1", location_type=self.leaf_type, parent=location_1, status=self.status)
        self.assertEqual(location_2.display, "Building 1 → Room 1")

    @override_settings(LOCATION_NAME_AS_NATURAL_KEY=True)
    def test_location_name_as_natural_key_display(self):
        location_1 = Location(name="Building 1", location_type=self.root_type, status=self.status)
        location_1.validated_save()
        location_2 = Location(name="Room 1", location_type=self.leaf_type, parent=location_1, status=self.status)
        self.assertEqual(location_2.display, "Room 1")


class PlatformTestCase(TestCase):
    def setUp(self):
        self.standard_platform = Platform(name="Cisco IOS", network_driver="cisco_ios")
        self.custom_platform = Platform(name="Private Platform", network_driver="secret_sauce")

    def test_network_driver_netutils_defaults(self):
        """Test that a network_driver setting derives related fields from netutils by default."""
        self.assertEqual(self.standard_platform.network_driver_mappings["ansible"], "cisco.ios.ios")
        self.assertEqual(self.standard_platform.network_driver_mappings["hier_config"], "ios")
        self.assertEqual(self.standard_platform.network_driver_mappings["netmiko"], "cisco_ios")
        self.assertEqual(self.standard_platform.network_driver_mappings["netutils_parser"], "cisco_ios")
        self.assertEqual(self.standard_platform.network_driver_mappings["ntc_templates"], "cisco_ios")
        self.assertEqual(self.standard_platform.network_driver_mappings["pyats"], "iosxe")
        self.assertEqual(self.standard_platform.network_driver_mappings["pyntc"], "cisco_ios_ssh")
        self.assertEqual(self.standard_platform.network_driver_mappings["scrapli"], "cisco_iosxe")

    def test_network_driver_unknown(self):
        """Test that properties are not set if the network_driver setting is not known by netutils."""
        self.assertNotIn("ansible", self.custom_platform.network_driver_mappings)
        self.assertNotIn("hier_config", self.custom_platform.network_driver_mappings)
        self.assertNotIn("netmiko", self.custom_platform.network_driver_mappings)
        self.assertNotIn("netutils_parser", self.custom_platform.network_driver_mappings)
        self.assertNotIn("ntc_templates", self.custom_platform.network_driver_mappings)
        self.assertNotIn("pyats", self.custom_platform.network_driver_mappings)
        self.assertNotIn("pyntc", self.custom_platform.network_driver_mappings)
        self.assertNotIn("scrapli", self.custom_platform.network_driver_mappings)

    @override_settings(
        NETWORK_DRIVERS={
            "netmiko": {
                "secret_sauce": "secret_driver",
                "cisco_ios": "cisco_xe",
            },
            "scrapli": {
                "secret_sauce": "secret_scrapli",
            },
            "supercoolnewtool": {
                "cisco_ios": "cisco_xyz",
                "secret_sauce": "secret_xyz",
            },
        },
    )
    def test_network_driver_settings_override(self):
        """Test that settings.NETWORK_DRIVERS can extend and override the default behavior."""
        # Not overridden
        self.assertEqual(self.standard_platform.network_driver_mappings["ansible"], "cisco.ios.ios")
        self.assertEqual(self.standard_platform.network_driver_mappings["pyats"], "iosxe")
        self.assertEqual(self.standard_platform.network_driver_mappings["scrapli"], "cisco_iosxe")
        self.assertNotIn("ansible", self.custom_platform.network_driver_mappings)
        self.assertNotIn("pyats", self.custom_platform.network_driver_mappings)
        # Overridden
        self.assertEqual(self.standard_platform.network_driver_mappings["netmiko"], "cisco_xe")
        self.assertEqual(self.custom_platform.network_driver_mappings["netmiko"], "secret_driver")
        self.assertEqual(self.custom_platform.network_driver_mappings["scrapli"], "secret_scrapli")
        self.assertIn("supercoolnewtool", self.standard_platform.network_driver_mappings)
        self.assertEqual(self.standard_platform.network_driver_mappings["supercoolnewtool"], "cisco_xyz")
        self.assertIn("supercoolnewtool", self.custom_platform.network_driver_mappings)
        self.assertEqual(self.custom_platform.network_driver_mappings["supercoolnewtool"], "secret_xyz")


class DeviceTestCase(ModelTestCases.BaseModelTestCase):
    model = Device

    def setUp(self):
        manufacturer = Manufacturer.objects.first()
        self.device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 1",
            subdevice_role=SubdeviceRoleChoices.ROLE_PARENT,
        )
        self.child_devicetype = DeviceType.objects.create(
            model="Child Device Type 1",
            manufacturer=manufacturer,
            subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
            u_height=0,
        )
        self.device_role = Role.objects.get_for_model(Device).first()
        self.device_status = Status.objects.get_for_model(Device).first()
        self.intf_role = Role.objects.get_for_model(Interface).first()
        self.location_type_1 = LocationType.objects.get(name="Building")
        self.location_type_2 = LocationType.objects.get(name="Floor")
        self.location_type_3 = LocationType.objects.get(name="Campus")
        self.location_type_2.content_types.add(ContentType.objects.get_for_model(Device))
        self.location_type_3.content_types.add(ContentType.objects.get_for_model(Device))
        self.location_1 = Location.objects.create(
            name="Root", status=self.device_status, location_type=self.location_type_1
        )
        self.location_2 = Location.objects.create(
            name="Leaf", status=self.device_status, location_type=self.location_type_2, parent=self.location_1
        )
        self.location_3 = Location.objects.create(
            name="Device Allowed Location",
            status=self.device_status,
            location_type=self.location_type_3,
        )
        self.device_redundancy_group = DeviceRedundancyGroup.objects.first()

        # Create DeviceType components
        ConsolePortTemplate(device_type=self.device_type, name="Console Port 1").save()

        ConsoleServerPortTemplate(device_type=self.device_type, name="Console Server Port 1").save()

        ppt = PowerPortTemplate(
            device_type=self.device_type,
            name="Power Port 1",
            maximum_draw=1000,
            allocated_draw=500,
        )
        ppt.save()

        PowerOutletTemplate(
            device_type=self.device_type,
            name="Power Outlet 1",
            power_port_template=ppt,
            feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
        ).save()

        InterfaceTemplate(
            device_type=self.device_type,
            name="Interface 1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        ).save()

        rpt = RearPortTemplate(
            device_type=self.device_type,
            name="Rear Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            positions=8,
        )
        rpt.save()

        FrontPortTemplate(
            device_type=self.device_type,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=rpt,
            rear_port_position=2,
        ).save()

        DeviceBayTemplate(device_type=self.device_type, name="Device Bay 1").save()
        ModuleBayTemplate.objects.create(device_type=self.device_type, position="1111")

        self.device = Device(
            location=self.location_3,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
            name="Test Device 1",
        )
        self.device.validated_save()

    def test_natural_key_default(self):
        """Ensure that default natural-key for Device is (name, tenant, location)."""
        self.assertEqual([self.device.name, None, *self.device.location.natural_key()], self.device.natural_key())
        # self.assertEqual(
        #     construct_composite_key([self.device.name, None, *self.device.location.natural_key()]),
        #     self.device.composite_key,
        # )  # TODO: Revist this if we reintroduce composite keys
        self.assertEqual(
            self.device,
            Device.objects.get_by_natural_key([self.device.name, None, *self.device.location.natural_key()]),
        )
        # self.assertEqual(self.device, Device.objects.get(composite_key=self.device.composite_key))  # TODO: Revist this if we reintroduce composite keys

    def test_natural_key_overrides(self):
        """Ensure that the natural-key for Device is affected by settings/Constance."""
        with override_config(DEVICE_NAME_AS_NATURAL_KEY=True):
            self.assertEqual([self.device.name], self.device.natural_key())
            # self.assertEqual(construct_composite_key([self.device.name]), self.device.composite_key)  # TODO: Revist this if we reintroduce composite keys
            self.assertEqual(self.device, Device.objects.get_by_natural_key([self.device.name]))
            # self.assertEqual(self.device, Device.objects.get(composite_key=self.device.composite_key))  # TODO: Revist this if we reintroduce composite keys

        with override_config(LOCATION_NAME_AS_NATURAL_KEY=True):
            self.assertEqual([self.device.name, None, self.device.location.name], self.device.natural_key())
            # self.assertEqual(
            #     construct_composite_key([self.device.name, None, self.device.location.name]),
            #     self.device.composite_key,
            # )  # TODO: Revist this if we reintroduce composite keys
            self.assertEqual(
                self.device, Device.objects.get_by_natural_key([self.device.name, None, self.device.location.name])
            )
            # self.assertEqual(self.device, Device.objects.get(composite_key=self.device.composite_key))  # TODO: Revist this if we reintroduce composite keys

    def test_device_creation(self):
        """
        Ensure that all Device components are copied automatically from the DeviceType.
        """
        ConsolePort.objects.get(device=self.device, name="Console Port 1")

        ConsoleServerPort.objects.get(device=self.device, name="Console Server Port 1")

        pp = PowerPort.objects.get(device=self.device, name="Power Port 1", maximum_draw=1000, allocated_draw=500)

        PowerOutlet.objects.get(
            device=self.device,
            name="Power Outlet 1",
            power_port=pp,
            feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
        )

        Interface.objects.get(
            device=self.device,
            name="Interface 1",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        )

        rp = RearPort.objects.get(device=self.device, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C, positions=8)

        FrontPort.objects.get(
            device=self.device,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rp,
            rear_port_position=2,
        )

        DeviceBay.objects.get(device=self.device, name="Device Bay 1")
        ModuleBay.objects.get(parent_device=self.device, position="1111")

    def test_multiple_unnamed_devices(self):
        device1 = Device(
            location=self.location_3,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
            name="",
        )
        device1.save()

        device2 = Device(
            location=device1.location,
            device_type=device1.device_type,
            role=device1.role,
            status=self.device_status,
            name="",
        )
        device2.full_clean()
        device2.save()

        self.assertEqual(Device.objects.filter(name="").count(), 2)

    def test_device_duplicate_names(self):
        device2 = Device(
            location=self.device.location,
            device_type=self.device.device_type,
            role=self.device.role,
            status=self.device_status,
            name=self.device.name,
        )

        # Two devices assigned to the same Location and no Tenant should fail validation
        with self.assertRaises(ValidationError):
            device2.full_clean()

        tenant = Tenant.objects.first()
        self.device.tenant = tenant
        self.device.save()
        device2.tenant = tenant

        # Two devices assigned to the same Location and the same Tenant should fail validation
        with self.assertRaises(ValidationError):
            device2.full_clean()

        device2.tenant = None

        # Two devices assigned to the same Location and different Tenants should pass validation
        device2.full_clean()
        device2.save()

    def test_device_location_content_type_not_allowed(self):
        self.location_type_2.content_types.clear()
        device = Device(
            name="Device 3",
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
            location=self.location_2,
        )
        with self.assertRaises(ValidationError) as cm:
            device.validated_save()
        self.assertIn(
            f'Devices may not associate to locations of type "{self.location_type_2.name}"', str(cm.exception)
        )

    def test_device_redundancy_group_validation(self):
        d2 = Device(
            name="Test Device 2",
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
            location=self.location_3,
        )
        d2.validated_save()

        # Validate we can set a redundancy group without any priority set
        self.device.device_redundancy_group = self.device_redundancy_group
        self.device.validated_save()

        # Validate two devices can be a part of the same redundancy group without any priority set
        d2.device_redundancy_group = self.device_redundancy_group
        d2.validated_save()

        # Validate we can assign a priority to at least one device in the group
        self.device.device_redundancy_group_priority = 1
        self.device.validated_save()

        # Validate both devices in the same group can have the same priority
        d2.device_redundancy_group_priority = 1
        d2.validated_save()

        # Validate devices in the same group can have different priority
        d2.device_redundancy_group_priority = 2
        d2.validated_save()

        # Validate devices cannot have an assigned priority without an assigned group
        self.device.device_redundancy_group = None
        with self.assertRaisesMessage(
            ValidationError, "Must assign a redundancy group when defining a redundancy group priority."
        ):
            self.device.validated_save()

    def test_primary_ip_validation_logic(self):
        device = Device(
            name="Test IP Device",
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
            location=self.location_3,
        )
        device.validated_save()
        interface = Interface.objects.create(name="Int1", device=device, status=self.device_status, role=self.intf_role)
        ips = list(IPAddress.objects.filter(ip_version=4)[:5]) + list(IPAddress.objects.filter(ip_version=6)[:5])
        interface.add_ip_addresses(ips)
        device.primary_ip4 = interface.ip_addresses.all().filter(ip_version=6).first()
        self.assertIsNotNone(device.primary_ip4)
        with self.assertRaises(ValidationError) as cm:
            device.validated_save()
        self.assertIn(
            f"{interface.ip_addresses.all().filter(ip_version=6).first()} is not an IPv4 address",
            str(cm.exception),
        )
        device.primary_ip4 = None
        device.primary_ip6 = interface.ip_addresses.all().filter(ip_version=4).first()
        self.assertIsNotNone(device.primary_ip6)
        with self.assertRaises(ValidationError) as cm:
            device.validated_save()
        self.assertIn(
            f"{interface.ip_addresses.all().filter(ip_version=4).first()} is not an IPv6 address",
            str(cm.exception),
        )
        device.primary_ip4 = interface.ip_addresses.all().filter(ip_version=4).first()
        device.primary_ip6 = interface.ip_addresses.all().filter(ip_version=6).first()
        device.validated_save()

    def test_primary_ip_validation_logic_modules(self):
        device = Device(
            name="Test IP Device",
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
            location=self.location_3,
        )
        device.validated_save()
        manufacturer = Manufacturer.objects.first()
        module_type = ModuleType.objects.create(manufacturer=manufacturer, model="module model tests")

        status = Status.objects.get_for_model(Module).first()
        module_bay = ModuleBay.objects.create(
            parent_device=device,
            name="1111",
            position="1111",
        )

        module = Module.objects.create(
            module_type=module_type,
            parent_module_bay=module_bay,
            status=status,
        )

        interface = Interface.objects.create(name="Int1", module=module, status=self.device_status, role=self.intf_role)
        ips = list(IPAddress.objects.filter(ip_version=4)[:5]) + list(IPAddress.objects.filter(ip_version=6)[:5])
        interface.add_ip_addresses(ips)
        device.primary_ip4 = interface.ip_addresses.all().filter(ip_version=4).first()
        self.assertIsNotNone(device.primary_ip4)
        device.primary_ip6 = interface.ip_addresses.all().filter(ip_version=6).first()
        self.assertIsNotNone(device.primary_ip6)
        device.validated_save()

    def test_software_version_device_type_validation(self):
        """
        Assert that device's software version contains a software image file that matches the device's device type or a default image.
        """

        software_version = SoftwareVersion.objects.filter(software_image_files__isnull=False).first()
        software_version.software_image_files.all().update(default_image=False)
        self.device_type.software_image_files.set([])
        self.device.software_version = software_version
        invalid_software_image_file = SoftwareImageFile.objects.filter(default_image=False).first()
        invalid_software_image_file.device_types.set([])
        self.device.software_image_files.set([invalid_software_image_file])

        # There is an invalid non-default software_image_file specified for the software version
        # It is not a default image and it does not match any device type
        with self.assertRaises(ValidationError):
            self.device.validated_save()

        # user should be able to specify any software version without specifying software_image_files
        self.device.software_image_files.set([])
        self.device.validated_save()

        # Default image matches
        software_image_file = software_version.software_image_files.first()
        software_image_file.default_image = True
        software_image_file.save()
        self.device.validated_save()

        # Device type matches
        software_image_file.default_image = False
        software_image_file.save()
        self.device_type.software_image_files.add(software_image_file)
        self.device.validated_save()

    def test_all_x_properties(self):
        self.assertTrue(self.device.has_module_bays)
        self.assertEqual(self.device.all_modules.count(), 0)
        self.assertEqual(self.device.all_module_bays.count(), 1)
        self.assertEqual(self.device.all_console_server_ports.count(), 1)
        self.assertEqual(self.device.all_console_ports.count(), 1)
        self.assertEqual(self.device.all_front_ports.count(), 1)
        self.assertEqual(self.device.all_interfaces.count(), 1)
        self.assertEqual(self.device.all_rear_ports.count(), 1)
        self.assertEqual(self.device.all_power_ports.count(), 1)
        self.assertEqual(self.device.all_power_outlets.count(), 1)

        parent_module_bay = self.device.all_module_bays.first()

        manufacturer = Manufacturer.objects.first()
        module_type = ModuleType.objects.create(manufacturer=manufacturer, model="module model tests")
        status = Status.objects.get_for_model(Module).first()

        # Create ModuleType components
        ConsolePortTemplate.objects.create(module_type=module_type, name="Console Port 1")
        ConsoleServerPortTemplate.objects.create(module_type=module_type, name="Console Server Port 1")

        ppt = PowerPortTemplate.objects.create(
            module_type=module_type,
            name="Power Port 1",
            maximum_draw=1000,
            allocated_draw=500,
        )

        PowerOutletTemplate.objects.create(
            module_type=module_type,
            name="Power Outlet 1",
            power_port_template=ppt,
            feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
        )

        InterfaceTemplate.objects.create(
            module_type=module_type,
            name="Interface {module.parent.parent}/{module.parent}/{module}",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        )

        rpt = RearPortTemplate.objects.create(
            module_type=module_type,
            name="Rear Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            positions=8,
        )

        FrontPortTemplate.objects.create(
            module_type=module_type,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=rpt,
            rear_port_position=2,
        )

        ModuleBayTemplate.objects.create(
            module_type=module_type,
            position="1111",
        )

        module = Module.objects.create(
            module_type=module_type,
            status=status,
            parent_module_bay=parent_module_bay,
        )

        self.assertEqual(self.device.all_modules.count(), 1)
        self.assertEqual(self.device.all_module_bays.count(), 2)
        self.assertEqual(self.device.all_console_server_ports.count(), 2)
        self.assertEqual(self.device.all_console_ports.count(), 2)
        self.assertEqual(self.device.all_front_ports.count(), 2)
        self.assertEqual(self.device.all_interfaces.count(), 2)
        self.assertEqual(self.device.all_rear_ports.count(), 2)
        self.assertEqual(self.device.all_power_ports.count(), 2)
        self.assertEqual(self.device.all_power_outlets.count(), 2)

        child_module_bay = module.module_bays.first()
        Module.objects.create(
            module_type=module_type,
            status=status,
            parent_module_bay=child_module_bay,
        )

        self.assertEqual(self.device.all_modules.count(), 2)
        self.assertEqual(self.device.all_module_bays.count(), 3)
        self.assertEqual(self.device.all_console_server_ports.count(), 3)
        self.assertEqual(self.device.all_console_ports.count(), 3)
        self.assertEqual(self.device.all_front_ports.count(), 3)
        self.assertEqual(self.device.all_interfaces.count(), 3)
        self.assertEqual(self.device.all_rear_ports.count(), 3)
        self.assertEqual(self.device.all_power_ports.count(), 3)
        self.assertEqual(self.device.all_power_outlets.count(), 3)

    def test_child_devices_are_not_saved_when_unnecessary(self):
        parent_device = Device.objects.create(
            name="Parent Device 1",
            location=self.location_3,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        parent_device.validated_save()

        child_device = Device.objects.create(
            name="Child Device 1",
            location=parent_device.location,
            device_type=self.child_devicetype,
            role=parent_device.role,
            status=self.device_status,
        )
        child_device.validated_save()
        child_mtime_before_parent_saved = str(child_device.last_updated)

        devicebay = DeviceBay.objects.get(device=parent_device, name="Device Bay 1")
        devicebay.installed_device = child_device
        devicebay.validated_save()

        #
        # Tests
        #

        #
        # On a NOOP save, the child device shouldn't be updated
        parent_device.save()

        child_mtime_after_parent_noop_save = str(Device.objects.get(name="Child Device 1").last_updated)

        self.assertEqual(child_mtime_before_parent_saved, child_mtime_after_parent_noop_save)

        #
        # On a serial number update, the child device shouldn't be updated
        parent_device.serial = "12345"
        parent_device.save()

        child_mtime_after_parent_serial_update_save = str(Device.objects.get(name="Child Device 1").last_updated)

        self.assertEqual(child_mtime_before_parent_saved, child_mtime_after_parent_serial_update_save)

        #
        # If the parent rack updates, the child mtime should update.
        rack = Rack.objects.create(name="Rack 1", location=parent_device.location, status=self.device_status)
        parent_device.rack = rack
        parent_device.save()

        # Test assigning a rack in the child location of the parent device location
        location_status = Status.objects.get_for_model(Location).first()
        child_location = Location.objects.create(
            name="Child Location 1",
            location_type=self.location_type_3,
            status=location_status,
            parent=parent_device.location,
        )
        child_rack = Rack.objects.create(name="Rack 2", location=child_location, status=self.device_status)
        parent_device.rack = child_rack
        parent_device.validated_save()

        # Test assigning a rack outside the child locations of the parent device location
        new_location = Location.objects.create(
            name="New Location 1",
            status=location_status,
            location_type=self.location_type_3,
        )
        invalid_rack = Rack.objects.create(name="Rack 3", location=new_location, status=self.device_status)
        parent_device.rack = invalid_rack
        with self.assertRaises(ValidationError) as cm:
            parent_device.validated_save()
        self.assertIn(
            f'Rack "{invalid_rack}" does not belong to location "{parent_device.location}" and its descendants.',
            str(cm.exception),
        )

        child_mtime_after_parent_rack_update_save = str(Device.objects.get(name="Child Device 1").last_updated)

        self.assertNotEqual(child_mtime_after_parent_noop_save, child_mtime_after_parent_rack_update_save)

        #
        # If the parent site updates, the child mtime should update
        location = Location.objects.create(
            name="New Site 1", status=self.device_status, location_type=self.location_type_3
        )
        parent_device.location = location
        parent_device.save()

        child_mtime_after_parent_site_update_save = str(Device.objects.get(name="Child Device 1").last_updated)

        self.assertNotEqual(child_mtime_after_parent_rack_update_save, child_mtime_after_parent_site_update_save)


class DeviceBayTestCase(ModelTestCases.BaseModelTestCase):
    model = DeviceBay

    def setUp(self):
        self.devices = Device.objects.filter(device_type__subdevice_role=SubdeviceRoleChoices.ROLE_PARENT)
        devicetype = DeviceType.objects.create(
            manufacturer=self.devices[0].device_type.manufacturer,
            model="TestDeviceType1",
            u_height=0,
            subdevice_role=SubdeviceRoleChoices.ROLE_CHILD,
        )
        child_device = Device.objects.create(
            device_type=devicetype,
            role=self.devices[0].role,
            name="TestDevice1",
            status=self.devices[0].status,
            location=self.devices[0].location,
        )
        DeviceBay.objects.create(device=self.devices[0], name="Device Bay 1", installed_device=child_device)

    def test_assigning_installed_device(self):
        server = Device.objects.exclude(device_type__subdevice_role=SubdeviceRoleChoices.ROLE_CHILD).last()
        bay = DeviceBay(device=self.devices[1], name="Device Bay Err", installed_device=server)
        with self.assertRaises(ValidationError) as err:
            bay.validated_save()
        self.assertIn(
            f'Cannot install device "{server}"; device-type "{server.device_type}" subdevice_role is not "child".',
            str(err.exception),
        )


class DeviceTypeToSoftwareImageFileTestCase(ModelTestCases.BaseModelTestCase):
    model = DeviceTypeToSoftwareImageFile

    def test_get_docs_url(self):
        """No docs for this through table model."""


class CableTestCase(ModelTestCases.BaseModelTestCase):
    model = Cable

    @classmethod
    def setUpTestData(cls):
        cls.interface_choices = {section[0]: dict(section[1]) for section in InterfaceTypeChoices.CHOICES}

        location = Location.objects.first()
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(
            manufacturer=manufacturer,
            model="Test Device Type 1",
        )
        devicerole = Role.objects.get_for_model(Device).first()
        devicestatus = Status.objects.get_for_model(Device).first()
        cls.user = User.objects.create(username="Test User", is_active=True)
        cls.device1 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice1",
            location=location,
            status=devicestatus,
        )
        cls.device2 = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestDevice2",
            location=location,
            status=devicestatus,
        )
        interfacestatus = Status.objects.get_for_model(Interface).first()
        cls.interface1 = Interface.objects.create(device=cls.device1, name="eth0", status=interfacestatus)
        cls.interface2 = Interface.objects.create(device=cls.device2, name="eth0", status=interfacestatus)
        cls.interface3 = Interface.objects.create(device=cls.device2, name="eth1", status=interfacestatus)
        cls.status = Status.objects.get_for_model(Cable).get(name="Connected")
        cls.cable = Cable(
            termination_a=cls.interface1,
            termination_b=cls.interface2,
            status=cls.status,
        )
        cls.cable.save()

        cls.power_port1 = PowerPort.objects.create(device=cls.device2, name="psu1")
        cls.patch_panel = Device.objects.create(
            device_type=devicetype,
            role=devicerole,
            name="TestPatchPanel",
            location=location,
            status=devicestatus,
        )
        cls.rear_port1 = RearPort.objects.create(device=cls.patch_panel, name="RP1", type="8p8c")
        cls.front_port1 = FrontPort.objects.create(
            device=cls.patch_panel,
            name="FP1",
            type="8p8c",
            rear_port=cls.rear_port1,
            rear_port_position=1,
        )
        cls.rear_port2 = RearPort.objects.create(device=cls.patch_panel, name="RP2", type="8p8c", positions=2)
        cls.front_port2 = FrontPort.objects.create(
            device=cls.patch_panel,
            name="FP2",
            type="8p8c",
            rear_port=cls.rear_port2,
            rear_port_position=1,
        )
        cls.rear_port3 = RearPort.objects.create(device=cls.patch_panel, name="RP3", type="8p8c", positions=3)
        cls.front_port3 = FrontPort.objects.create(
            device=cls.patch_panel,
            name="FP3",
            type="8p8c",
            rear_port=cls.rear_port3,
            rear_port_position=1,
        )
        cls.rear_port4 = RearPort.objects.create(device=cls.patch_panel, name="RP4", type="8p8c", positions=3)
        cls.front_port4 = FrontPort.objects.create(
            device=cls.patch_panel,
            name="FP4",
            type="8p8c",
            rear_port=cls.rear_port4,
            rear_port_position=1,
        )
        cls.provider = Provider.objects.first()
        provider_network = ProviderNetwork.objects.create(name="Provider Network 1", provider=cls.provider)
        cls.circuittype = CircuitType.objects.first()
        circuit_status = Status.objects.get_for_model(Circuit).first()
        cls.circuit1 = Circuit.objects.create(
            provider=cls.provider, circuit_type=cls.circuittype, cid="1", status=circuit_status
        )
        cls.circuit2 = Circuit.objects.create(
            provider=cls.provider, circuit_type=cls.circuittype, cid="2", status=circuit_status
        )
        cls.circuittermination1 = CircuitTermination.objects.create(
            circuit=cls.circuit1, location=location, term_side="A"
        )
        cls.circuittermination2 = CircuitTermination.objects.create(
            circuit=cls.circuit1, location=location, term_side="Z"
        )
        cls.circuittermination3 = CircuitTermination.objects.create(
            circuit=cls.circuit2, provider_network=provider_network, term_side="Z"
        )

    def test_cable_creation(self):
        """
        When a new Cable is created, it must be cached on either termination point.
        """
        interface1 = Interface.objects.get(pk=self.interface1.pk)
        interface2 = Interface.objects.get(pk=self.interface2.pk)
        self.assertEqual(self.cable.termination_a, interface1)
        self.assertEqual(interface1._cable_peer, interface2)
        self.assertEqual(self.cable.termination_b, interface2)
        self.assertEqual(interface2._cable_peer, interface1)

    def test_cable_deletion(self):
        """
        When a Cable is deleted, the `cable` field on its termination points must be nullified. The str() method
        should still return the PK of the string even after being nullified.
        """
        self.cable.delete()
        self.assertIsNone(self.cable.pk)
        self.assertNotEqual(str(self.cable), "#None")
        interface1 = Interface.objects.get(pk=self.interface1.pk)
        self.assertIsNone(interface1.cable)
        self.assertIsNone(interface1._cable_peer)
        interface2 = Interface.objects.get(pk=self.interface2.pk)
        self.assertIsNone(interface2.cable)
        self.assertIsNone(interface2._cable_peer)

    def test_cabletermination_deletion(self):
        """
        When a CableTermination object is deleted, its attached Cable (if any) must also be deleted.
        """
        self.interface1.delete()
        cable = Cable.objects.filter(pk=self.cable.pk).first()
        self.assertIsNone(cable)

    def test_cable_validates_compatible_types(self):
        """
        The clean method should have a check to ensure only compatible port types can be connected by a cable
        """
        # An interface cannot be connected to a power port
        cable = Cable(termination_a=self.interface1, termination_b=self.power_port1)
        with self.assertRaises(ValidationError):
            cable.clean()

    def test_cable_cannot_have_the_same_terminination_on_both_ends(self):
        """
        A cable cannot be made with the same A and B side terminations
        """
        cable = Cable(termination_a=self.interface1, termination_b=self.interface1)
        with self.assertRaises(ValidationError):
            cable.clean()

    def test_cable_front_port_cannot_connect_to_corresponding_rear_port(self):
        """
        A cable cannot connect a front port to its corresponding rear port
        """
        cable = Cable(termination_a=self.front_port1, termination_b=self.rear_port1)
        with self.assertRaises(ValidationError):
            cable.clean()

    def test_cable_cannot_terminate_to_an_existing_connection(self):
        """
        Either side of a cable cannot be terminated when that side already has a connection
        """
        # Try to create a cable with the same interface terminations
        cable = Cable(termination_a=self.interface2, termination_b=self.interface1)
        with self.assertRaises(ValidationError):
            cable.clean()

    def test_cable_cannot_terminate_to_a_provider_network_circuittermination(self):
        """
        Neither side of a cable can be terminated to a CircuitTermination which is attached to a Provider Network
        """
        cable = Cable(termination_a=self.interface3, termination_b=self.circuittermination3)
        with self.assertRaises(ValidationError):
            cable.clean()

    def test_rearport_connections(self):
        """
        Test various combinations of RearPort connections.
        """
        # Connecting a single-position RearPort to a multi-position RearPort is ok
        Cable(
            termination_a=self.rear_port1,
            termination_b=self.rear_port2,
            status=self.status,
        ).full_clean()

        # Connecting a single-position RearPort to an Interface is ok
        Cable(
            termination_a=self.rear_port1,
            termination_b=self.interface3,
            status=self.status,
        ).full_clean()

        # Connecting a single-position RearPort to a CircuitTermination is ok
        Cable(
            termination_a=self.rear_port1,
            termination_b=self.circuittermination1,
            status=self.status,
        ).full_clean()

        # Connecting a multi-position RearPort to another RearPort with the same number of positions is ok
        Cable(
            termination_a=self.rear_port3,
            termination_b=self.rear_port4,
            status=self.status,
        ).full_clean()

        # Connecting a multi-position RearPort to an Interface is ok
        Cable(
            termination_a=self.rear_port2,
            termination_b=self.interface3,
            status=self.status,
        ).full_clean()

        # Connecting a multi-position RearPort to a CircuitTermination is ok
        Cable(
            termination_a=self.rear_port2,
            termination_b=self.circuittermination1,
            status=self.status,
        ).full_clean()

        # Connecting a two-position RearPort to a three-position RearPort is NOT ok
        with self.assertRaises(
            ValidationError,
            msg="Connecting a 2-position RearPort to a 3-position RearPort should fail",
        ):
            Cable(termination_a=self.rear_port2, termination_b=self.rear_port3).full_clean()

    def test_cable_cannot_terminate_to_a_virtual_interface(self):
        """
        A cable cannot terminate to a virtual interface
        """
        virtual_interface_choices = self.interface_choices["Virtual interfaces"]

        self.cable.delete()
        interface_status = Status.objects.get_for_model(Interface).first()

        for virtual_interface_type in virtual_interface_choices:
            virtual_interface = Interface.objects.create(
                device=self.device1,
                name=f"V-{virtual_interface_type}",
                type=virtual_interface_type,
                status=interface_status,
            )
            with self.assertRaises(
                ValidationError,
                msg=f"Virtual interface type '{virtual_interface_choices[virtual_interface_type]}' should not accept a cable.",
            ) as cm:
                Cable(
                    termination_a=self.interface2,
                    termination_b=virtual_interface,
                ).clean()

            self.assertIn(
                f"Cables cannot be terminated to {virtual_interface_choices[virtual_interface_type]} interfaces",
                str(cm.exception),
            )

    def test_cable_cannot_terminate_to_a_wireless_interface(self):
        """
        A cable cannot terminate to a wireless interface
        """
        wireless_interface_choices = self.interface_choices["Wireless"]

        self.cable.delete()
        interface_status = Status.objects.get_for_model(Interface).first()

        for wireless_interface_type in wireless_interface_choices:
            wireless_interface = Interface.objects.create(
                device=self.device1,
                name=f"W-{wireless_interface_type}",
                type=wireless_interface_type,
                status=interface_status,
            )

            with self.assertRaises(
                ValidationError,
                msg=f"Wireless interface type '{wireless_interface_choices[wireless_interface_type]}' should not accept a cable.",
            ) as cm:
                Cable(termination_a=self.interface2, termination_b=wireless_interface).clean()

            self.assertIn(
                f"Cables cannot be terminated to {wireless_interface_choices[wireless_interface_type]} interfaces",
                str(cm.exception),
            )

    def test_create_cable_with_missing_status_connected(self):
        """Test for https://github.com/nautobot/nautobot/issues/2081"""
        # Delete all cables because some cables has connected status.
        Cable.objects.all().delete()
        connected_status_name = CableStatusChoices.as_dict()[CableStatusChoices.STATUS_CONNECTED]
        Status.objects.get(name=connected_status_name).delete()
        device = Device.objects.first()

        interface_status = Status.objects.get_for_model(Interface).first()
        interfaces = (
            Interface.objects.create(
                device=device,
                name="eth-0",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
            Interface.objects.create(
                device=device,
                name="eth-1",
                type=InterfaceTypeChoices.TYPE_1GE_FIXED,
                status=interface_status,
            ),
        )

        cable = Cable.objects.create(
            termination_a=interfaces[0],
            termination_b=interfaces[1],
            type=CableTypeChoices.TYPE_CAT6,
            status=Status.objects.get_for_model(Cable).first(),
        )

        self.assertTrue(Cable.objects.filter(id=cable.pk).exists())

    def test_deleting_device_with_multiple_types_of_connected_interfaces_successful(self):
        """
        This is a test to make sure that the bug described in https://github.com/nautobot/nautobot/issues/4416 does not occur again.
        We enabled change logging on device.delete() because the bug is derived from constructing
        ObjectChange objects when we are deleting the device and its associated objects.
        """

        Cable.objects.all().delete()
        interface_status = Status.objects.get_for_model(Interface).first()
        Interface.objects.all().update(status=interface_status)
        self.interface4 = Interface.objects.create(device=self.device2, name="eth4", status=interface_status)
        device1_power_ports = [
            PowerPort.objects.create(device=self.device1, name="Power Port 1"),
            PowerPort.objects.create(device=self.device1, name="Power Port 2"),
        ]
        device2_power_outlets = [
            PowerOutlet.objects.create(name="Power Outlet 1", device=self.device2),
            PowerOutlet.objects.create(name="Power Outlet 2", device=self.device2),
        ]

        cable_0 = Cable.objects.create(
            termination_a=self.interface1,
            termination_b=self.interface2,
            length_unit="in",
            length=1,
            status=self.status,
        )
        cable_0.validated_save()
        cable_1 = Cable.objects.create(
            termination_a=self.interface3,
            termination_b=self.interface4,
            length_unit="in",
            length=1,
            status=self.status,
        )
        cable_1.validated_save()
        cable_2 = Cable.objects.create(
            termination_a=device2_power_outlets[0],
            termination_b=device1_power_ports[0],
            length_unit="in",
            length=1,
            status=self.status,
        )
        cable_2.validated_save()
        cable_3 = Cable.objects.create(
            termination_a=device2_power_outlets[1],
            termination_b=device1_power_ports[1],
            length_unit="in",
            length=1,
            status=self.status,
        )
        cable_3.validated_save()

        self.device1.validated_save()
        self.device2.validated_save()

        # Enable change logging
        with context_managers.web_request_context(self.user):
            self.device1.delete()


class PowerFeedTestCase(ModelTestCases.BaseModelTestCase):
    model = PowerFeed

    @classmethod
    def setUpTestData(cls):
        cls.location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        cls.status = Status.objects.get_for_model(PowerFeed).first()
        cls.rack_status = Status.objects.get_for_model(Rack).first()

        cls.source_panel = PowerPanel.objects.create(location=cls.location, name="Source Panel 1")
        cls.destination_panel = PowerPanel.objects.create(location=cls.location, name="Destination Panel 1")

        # Create location in different hierarchy for rack validation test
        cls.other_location = Location.objects.create(
            name="Other Location",
            location_type=LocationType.objects.get(name="Campus"),
            status=Status.objects.get_for_model(Location).first(),
        )

        cls.rack = Rack.objects.create(location=cls.location, name="Test Rack", status=cls.rack_status)
        cls.other_rack = Rack.objects.create(location=cls.other_location, name="Other Rack", status=cls.rack_status)

        PowerFeed.objects.create(
            name="Test Power Feed 1",
            power_panel=cls.source_panel,
            rack=cls.rack,
            status=cls.status,
        )
        PowerFeed.objects.create(
            name="Test Power Feed 2",
            power_panel=cls.source_panel,
            status=cls.status,
        )
        PowerFeed.objects.create(
            name="Test Power Feed 3",
            power_panel=cls.destination_panel,
            status=cls.status,
        )

    def test_destination_panel_self_reference_validation(self):
        """Test that a power feed cannot reference itself."""
        feed = PowerFeed(
            name="Self Reference",
            power_panel=self.source_panel,
            destination_panel=self.source_panel,
            status=self.status,
        )

        with self.assertRaises(ValidationError) as cm:
            feed.full_clean()
        self.assertIn("destination_panel", cm.exception.message_dict)

    def test_circuit_breaker_position_conflict_validation(self):
        """Test that overlapping circuit breaker positions raise validation errors."""
        # Create first feed at position 1 with 2 poles (occupies 1,3)
        PowerFeed.objects.create(
            name="Feed 1",
            power_panel=self.source_panel,
            status=self.status,
            breaker_position=1,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_2,
        )

        # Try to create conflicting feed at position 3
        conflicting_feed = PowerFeed(
            name="Feed 2",
            power_panel=self.source_panel,
            status=self.status,
            breaker_position=3,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_1,
        )

        with self.assertRaises(ValidationError) as cm:
            conflicting_feed.full_clean()
        self.assertIn("breaker_position", cm.exception.message_dict)

    def test_rack_location_hierarchy_validation(self):
        """Test that rack must belong to same location hierarchy as power panel."""
        feed = PowerFeed(
            name="Invalid Rack Location",
            power_panel=self.source_panel,
            rack=self.other_rack,  # Different location hierarchy
            status=self.status,
        )

        with self.assertRaises(ValidationError) as cm:
            feed.full_clean()
        self.assertIn("rack", cm.exception.message_dict)

    def test_ac_voltage_negative_validation(self):
        """Test that AC supply cannot have negative voltage."""
        feed = PowerFeed(
            name="Negative Voltage",
            power_panel=self.source_panel,
            status=self.status,
            voltage=-120,
            supply=PowerFeedSupplyChoices.SUPPLY_AC,
        )

        with self.assertRaises(ValidationError) as cm:
            feed.full_clean()
        self.assertIn("voltage", cm.exception.message_dict)

    def test_phase_designation_single_pole(self):
        """Test phase designation calculation for single-pole breakers."""
        # Pattern: positions 1,2=A, 3,4=B, 5,6=C, 7,8=A, etc.
        test_cases = [
            (1, "A"),
            (2, "A"),
            (3, "B"),
            (4, "B"),
            (5, "C"),
            (6, "C"),
            (7, "A"),
            (8, "A"),
            (9, "B"),
            (10, "B"),
        ]

        for position, expected_phase in test_cases:
            with self.subTest(position=position):
                feed = PowerFeed.objects.create(
                    name=f"1P Test {position}",
                    power_panel=self.source_panel,
                    status=self.status,
                    breaker_position=position,
                    breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_1,
                    # phase defaults to PHASE_SINGLE which is correct for all single-pole feeds
                )
                self.assertEqual(feed.phase_designation, expected_phase)

    def test_phase_designation_two_pole_single_phase(self):
        """Test phase designation for 2-pole breakers delivering single-phase power."""
        # Common datacenter scenario: 2P breaker for 208V single-phase to rack PDU
        # Uses two phase conductors but delivers single-phase power
        test_cases = [
            (1, "A-B"),  # occupies 1,3 → A,B → 208V single-phase
            (2, "A-B"),  # occupies 2,4 → A,B → 208V single-phase
            (3, "B-C"),  # occupies 3,5 → B,C → 208V single-phase
            (4, "B-C"),  # occupies 4,6 → B,C → 208V single-phase
            (5, "A-C"),  # occupies 5,7 → C,A → sorted to A-C → 208V single-phase
            (6, "A-C"),  # occupies 6,8 → C,A → sorted to A-C → 208V single-phase
            (7, "A-B"),  # occupies 7,9 → A,B → 208V single-phase (cycle continues)
        ]

        for position, expected_designation in test_cases:
            with self.subTest(position=position):
                feed = PowerFeed.objects.create(
                    name=f"2P Single-Phase Test {position}",
                    power_panel=self.source_panel,
                    status=self.status,
                    breaker_position=position,
                    breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_2,
                    # phase defaults to PHASE_SINGLE - correct for 208V single-phase feeds
                )
                self.assertEqual(feed.phase_designation, expected_designation)
                # Verify it's still marked as single-phase power
                self.assertEqual(feed.phase, PowerFeedPhaseChoices.PHASE_SINGLE)

    def test_phase_designation_three_pole_three_phase(self):
        """Test phase designation for 3-pole breakers delivering three-phase power."""
        # True three-phase power using all three phases
        test_cases = [1, 2, 3, 4, 5]

        for position in test_cases:
            with self.subTest(position=position):
                feed = PowerFeed.objects.create(
                    name=f"3P Three-Phase Test {position}",
                    power_panel=self.source_panel,
                    status=self.status,
                    breaker_position=position,
                    breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_3,
                    phase=PowerFeedPhaseChoices.PHASE_3PHASE,  # Explicitly set to three-phase
                )
                self.assertEqual(feed.phase_designation, "A-B-C")
                # Verify it's marked as three-phase power
                self.assertEqual(feed.phase, PowerFeedPhaseChoices.PHASE_3PHASE)

    def test_phase_designation_edge_cases(self):
        """Test phase designation calculation for edge cases and None values."""
        # Test missing breaker_position
        feed = PowerFeed.objects.create(
            name="No Position",
            power_panel=self.source_panel,
            status=self.status,
            breaker_position=None,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_1,
        )
        self.assertIsNone(feed.phase_designation)

        # Test missing breaker_pole_count (should default to single pole)
        feed = PowerFeed.objects.create(
            name="No Pole Count",
            power_panel=self.source_panel,
            status=self.status,
            breaker_position=1,
            breaker_pole_count=None,
        )
        # Should default to single pole and have phase designation
        self.assertEqual(feed.breaker_pole_count, PowerFeedBreakerPoleChoices.POLE_1)
        self.assertEqual(feed.phase_designation, "A")

        # Test both missing
        feed = PowerFeed.objects.create(
            name="No Position or Pole Count",
            power_panel=self.source_panel,
            status=self.status,
            breaker_position=None,
            breaker_pole_count=None,
        )
        self.assertIsNone(feed.phase_designation)

    def test_phase_field_defaults(self):
        """Test that phase field defaults correctly and type field defaults to primary."""
        feed = PowerFeed.objects.create(
            name="Default Fields Test",
            power_panel=self.source_panel,
            status=self.status,
        )

        # Verify defaults
        self.assertEqual(feed.phase, PowerFeedPhaseChoices.PHASE_SINGLE)
        self.assertEqual(feed.type, PowerFeedTypeChoices.TYPE_PRIMARY)

    def test_occupied_positions(self):
        """Test occupied positions calculation."""
        feed = PowerFeed.objects.create(
            name="Test Feed",
            power_panel=self.source_panel,
            status=self.status,
            breaker_position=5,
            breaker_pole_count=PowerFeedBreakerPoleChoices.POLE_2,
        )

        self.assertEqual(feed.get_occupied_positions(), {5, 7})
        self.assertEqual(feed.occupied_positions, "5, 7")

    def test_breaker_pole_count_enforcement_in_save(self):
        """Test that breaker_pole_count defaults to POLE_1 when breaker_position is set during save."""
        # Create feed with breaker_position but no breaker_pole_count
        feed = PowerFeed(
            name="Test Save Enforcement",
            power_panel=self.source_panel,
            status=self.status,
            breaker_position=10,
        )

        # Verify breaker_pole_count is None before save
        self.assertIsNone(feed.breaker_pole_count)

        # Save without calling clean() to bypass form validation
        feed.save()

        # Verify breaker_pole_count was set to POLE_1 during save
        self.assertEqual(feed.breaker_pole_count, PowerFeedBreakerPoleChoices.POLE_1)


class PowerPanelTestCase(TestCase):  # TODO: change to BaseModelTestCase once we have a PowerPanelFactory
    def test_power_panel_validation(self):
        status = Status.objects.get_for_model(Location).first()
        location_type_1 = LocationType.objects.create(name="Location Type 1")
        location_1 = Location.objects.create(name="Location 1", location_type=location_type_1, status=status)
        power_panel = PowerPanel(name="Power Panel 1", location=location_1)
        with self.assertRaises(ValidationError) as cm:
            power_panel.validated_save()
        self.assertIn(f'Power panels may not associate to locations of type "{location_type_1}"', str(cm.exception))

        location_type_1.content_types.add(ContentType.objects.get_for_model(PowerPanel))
        rack_group = RackGroup.objects.create(name="Rack Group 1", location=location_1)
        power_panel.rack_group = rack_group
        location_2 = Location.objects.create(name="Location 2", location_type=location_type_1, status=status)
        rack_group.location = location_2
        rack_group.save()
        with self.assertRaises(ValidationError) as cm:
            power_panel.validated_save()
        self.assertIn(
            f'Rack group "Rack Group 1" belongs to a location ("{location_2.name}") that does not contain "{location_1.name}"',
            str(cm.exception),
        )


class InterfaceTestCase(ModularDeviceComponentTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = Interface

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.modular_component_create_data = {
            "type": InterfaceTypeChoices.TYPE_1GE_FIXED,
            "status": Status.objects.get_for_model(Interface).first(),
        }
        manufacturer = Manufacturer.objects.first()
        devicetype = DeviceType.objects.create(manufacturer=manufacturer, model="Device Type 1")
        devicerole = Role.objects.get_for_model(Device).first()
        location = Location.objects.filter(location_type=LocationType.objects.get(name="Campus")).first()
        vlan_status = Status.objects.get_for_model(VLAN).first()
        vlan_group = VLANGroup.objects.filter(location=location).first()
        cls.vlan = VLAN.objects.create(
            name="VLAN 1", vid=100, location=location, status=vlan_status, vlan_group=vlan_group
        )
        status = Status.objects.get_for_model(Device).first()
        cls.device = Device.objects.create(
            name="Device 1",
            device_type=devicetype,
            role=devicerole,
            location=location,
            status=status,
        )
        location_2 = Location.objects.create(
            name="Other Location",
            location_type=LocationType.objects.get(name="Campus"),
            status=Status.objects.get_for_model(Location).first(),
        )
        cls.other_location_vlan = VLAN.objects.create(
            name="Other Location VLAN",
            vid=100,
            location=location_2,
            status=vlan_status,
        )

        cls.namespace = Namespace.objects.create(name="dcim_test_interface_ip_addresses")
        prefix_status = Status.objects.get_for_model(Prefix).first()
        ip_address_status = Status.objects.get_for_model(IPAddress).first()
        Prefix.objects.create(prefix="1.1.1.0/24", status=prefix_status, namespace=cls.namespace)
        for last_octet in range(1, 11):
            IPAddress.objects.create(
                address=f"1.1.1.{last_octet}/32", status=ip_address_status, namespace=cls.namespace
            )

    def test_vdcs_validation_logic(self):
        """Assert Interface raises error when adding virtual_device_contexts that do not belong to same device as the Interface device."""
        interface = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device,
            status=Status.objects.get_for_model(Interface).first(),
            role=Role.objects.get_for_model(Interface).first(),
        )
        vdc = VirtualDeviceContext.objects.create(
            name="Sample VDC",
            device=Device.objects.exclude(pk=self.device.pk).first(),
            identifier=100,
            status=Status.objects.get_for_model(VirtualDeviceContext).first(),
        )

        with self.assertRaises(ValidationError) as err:
            interface.virtual_device_contexts.add(vdc)
        self.assertEqual(
            err.exception.message_dict["virtual_device_contexts"][0],
            f"Virtual Device Context with names {[vdc.name]} must all belong to the "
            f"same device as the interface's device.",
        )

    def test_tagged_vlan_raise_error_if_mode_not_set_to_tagged(self):
        interface = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device,
            status=Status.objects.get_for_model(Interface).first(),
            role=Role.objects.get_for_model(Interface).first(),
        )
        with self.assertRaises(ValidationError) as err:
            interface.tagged_vlans.add(self.vlan)
        self.assertEqual(
            err.exception.message_dict["tagged_vlans"][0], "Mode must be set to tagged when specifying tagged_vlans"
        )

    def test_error_raised_when_adding_tagged_vlan_with_different_location_from_interface_parent_location(self):
        intf_status = Status.objects.get_for_model(Interface).first()
        intf_role = Role.objects.get_for_model(Interface).first()
        location_type = LocationType.objects.get(name="Campus")
        child_location = Location.objects.filter(parent__isnull=False, location_type=location_type).first()
        self.device.location = child_location
        self.device.validated_save()
        # Same location as the device
        interface = Interface.objects.create(
            name="Test Interface 2",
            mode=InterfaceModeChoices.MODE_TAGGED,
            device=self.device,
            status=intf_status,
            role=intf_role,
        )
        self.other_location_vlan.locations.set([self.device.location.pk])
        interface.tagged_vlans.set([self.other_location_vlan.pk])

        # One of the parent locations of the device's location
        interface = Interface.objects.create(
            name="Test Interface 3",
            mode=InterfaceModeChoices.MODE_TAGGED,
            device=self.device,
            status=intf_status,
            role=intf_role,
        )
        self.other_location_vlan.locations.set([self.device.location.ancestors().first().pk])
        interface.tagged_vlans.set([self.other_location_vlan.pk])

        with self.assertRaises(ValidationError) as err:
            interface = Interface.objects.create(
                name="Test Interface 1",
                mode=InterfaceModeChoices.MODE_TAGGED,
                device=self.device,
                status=intf_status,
                role=intf_role,
            )
            location_3 = Location.objects.create(
                name="Invalid VLAN Location",
                location_type=LocationType.objects.get(name="Campus"),
                status=Status.objects.get_for_model(Location).first(),
            )
            # clear the valid locations
            self.other_location_vlan.locations.set([])
            # assign the invalid location
            self.other_location_vlan.location = location_3
            self.other_location_vlan.validated_save()
            interface.tagged_vlans.add(self.other_location_vlan)
        self.assertEqual(
            err.exception.message_dict["tagged_vlans"][0],
            f"Tagged VLAN with names {[self.other_location_vlan.name]} must all belong to the "
            f"same location as the interface's parent device, one of the parent locations of the interface's parent device's location, or it must be global.",
        )

    def test_add_ip_addresses(self):
        """Test the `add_ip_addresses` helper method on `Interface`"""
        interface = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device,
            status=Status.objects.get_for_model(Interface).first(),
            role=Role.objects.get_for_model(Interface).first(),
        )
        ips = list(IPAddress.objects.filter(parent__namespace=self.namespace))

        # baseline (no interface to ip address relationships exists)
        self.assertFalse(IPAddressToInterface.objects.filter(interface=interface).exists())

        # add single instance
        count = interface.add_ip_addresses(ips[-1])
        self.assertEqual(count, 1)
        self.assertEqual(IPAddressToInterface.objects.filter(ip_address=ips[-1], interface=interface).count(), 1)

        # add multiple instances
        count = interface.add_ip_addresses(ips[:5])
        self.assertEqual(count, 5)
        self.assertEqual(IPAddressToInterface.objects.filter(interface=interface).count(), 6)
        for ip in ips[:5]:
            self.assertEqual(IPAddressToInterface.objects.filter(ip_address=ip, interface=interface).count(), 1)

    def test_remove_ip_addresses(self):
        """Test the `remove_ip_addresses` helper method on `Interface`"""
        interface = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=self.device,
            status=Status.objects.get_for_model(Interface).first(),
            role=Role.objects.get_for_model(Interface).first(),
        )
        ips = list(IPAddress.objects.filter(parent__namespace=self.namespace))

        # baseline (no interface to ip address relationships exists)
        self.assertFalse(IPAddressToInterface.objects.filter(interface=interface).exists())

        interface.add_ip_addresses(ips)
        self.assertEqual(IPAddressToInterface.objects.filter(interface=interface).count(), 10)

        # remove single instance
        count = interface.remove_ip_addresses(ips[-1])
        self.assertEqual(count, 1)
        self.assertEqual(IPAddressToInterface.objects.filter(interface=interface).count(), 9)

        # remove multiple instances
        count = interface.remove_ip_addresses(ips[:5])
        self.assertEqual(count, 5)
        self.assertEqual(IPAddressToInterface.objects.filter(interface=interface).count(), 4)

        count = interface.remove_ip_addresses(ips)
        self.assertEqual(count, 4)
        self.assertEqual(IPAddressToInterface.objects.filter(interface=interface).count(), 0)

        # Test the pre_delete signal for IPAddressToInterface instances
        interface.add_ip_addresses(ips)
        self.device.primary_ip4 = interface.ip_addresses.all().filter(ip_version=4).first()
        self.device.primary_ip6 = interface.ip_addresses.all().filter(ip_version=6).first()
        self.device.save()
        interface.remove_ip_addresses(self.device.primary_ip4)
        self.device.refresh_from_db()
        self.assertEqual(self.device.primary_ip4, None)
        interface.remove_ip_addresses(self.device.primary_ip6)
        self.device.refresh_from_db()
        self.assertEqual(self.device.primary_ip6, None)


class SoftwareImageFileTestCase(ModelTestCases.BaseModelTestCase):
    model = SoftwareImageFile

    def test_download_url_validation_behaviour(self):
        """
        Test that the `download_url` property behaves as expected in relation to laxURLField validation and
        the ALLOWED_URL_SCHEMES setting.
        """
        # Prepare prerequisite objects
        platform = Platform.objects.first()
        software_version_status = Status.objects.get_for_model(SoftwareVersion).first()
        software_image_file_status = Status.objects.get_for_model(SoftwareImageFile).first()
        software_version = SoftwareVersion.objects.create(
            platform=platform, version="Test version 1.0.0", status=software_version_status
        )

        # Test that the download_url field is correctly validated with the default ALLOWED_URL_SCHEMES setting
        for scheme in settings.ALLOWED_URL_SCHEMES:
            software_image = SoftwareImageFile(
                software_version=software_version,
                image_file_name=f"software_image_file_qs_test_{scheme}.bin",
                status=software_image_file_status,
                download_url=f"{scheme}://example.com/software_image_file_qs_test_1.bin",
            )
            try:
                software_image.validated_save()
            except ValidationError as e:
                self.fail(f"download_url Scheme {scheme} ValidationError: {e}")

        INVALID_SCHEMES = ["httpx", "rdp", "cryptoboi"]
        OVERRIDE_VALID_SCHEMES = ["sftp", "tftp", "https", "http", "newfs", "customfs"]
        # Invalid schemes should raise a ValidationError
        for scheme in INVALID_SCHEMES:
            software_image = SoftwareImageFile(
                software_version=software_version,
                image_file_name=f"software_image_file_qs_test_{scheme}2.bin",
                status=software_image_file_status,
                download_url=f"{scheme}://example.com/software_image_file_qs_test_2.bin",
            )
            with self.assertRaises(ValidationError) as err:
                software_image.validated_save()
            self.assertEqual(err.exception.message_dict["download_url"][0], "Enter a valid URL.")

        with override_settings(ALLOWED_URL_SCHEMES=OVERRIDE_VALID_SCHEMES):
            for scheme in OVERRIDE_VALID_SCHEMES:
                software_image = SoftwareImageFile(
                    software_version=software_version,
                    image_file_name=f"software_image_file_qs_test_{scheme}3.bin",
                    status=software_image_file_status,
                    download_url=f"{scheme}://example.com/software_image_file_qs_test_3.bin",
                )
                try:
                    software_image.validated_save()
                except ValidationError as e:
                    self.fail(f"download_url Scheme {scheme} ValidationError: {e}")

            for scheme in INVALID_SCHEMES:
                software_image = SoftwareImageFile(
                    software_version=software_version,
                    image_file_name=f"software_image_file_qs_test_{scheme}4.bin",
                    status=software_image_file_status,
                    download_url=f"{scheme}://example.com/software_image_file_qs_test_4.bin",
                )
                with self.assertRaises(ValidationError) as err:
                    software_image.validated_save()
                self.assertEqual(err.exception.message_dict["download_url"][0], "Enter a valid URL.")

    def test_queryset_get_for_object(self):
        """
        Test that the queryset get_for_object method returns the expected results for Device, DeviceType, InventoryItem and VirtualMachine
        """
        qs = SoftwareImageFile.objects.all()
        location = Location.objects.first()
        manufacturer = Manufacturer.objects.first()
        platform = Platform.objects.first()
        role = Role.objects.get_for_model(Device).first()
        device_status = Status.objects.get_for_model(Device).first()
        software_version_status = Status.objects.get_for_model(SoftwareVersion).first()
        software_image_file_status = Status.objects.get_for_model(SoftwareImageFile).first()
        virtual_machine_status = Status.objects.get_for_model(VirtualMachine).first()

        software_versions = (
            SoftwareVersion.objects.create(
                platform=platform, version="Test version 1.0.0", status=software_version_status
            ),
            SoftwareVersion.objects.create(
                platform=platform, version="Test version 2.0.0", status=software_version_status
            ),
        )
        software_image_files = (
            SoftwareImageFile.objects.create(
                software_version=software_versions[0],
                image_file_name="software_image_file_qs_test_1.bin",
                status=software_image_file_status,
            ),
            SoftwareImageFile.objects.create(
                software_version=software_versions[0],
                image_file_name="software_image_file_qs_test_2.bin",
                status=software_image_file_status,
                default_image=True,
            ),
            SoftwareImageFile.objects.create(
                software_version=software_versions[1],
                image_file_name="software_image_file_qs_test_3.bin",
                status=software_image_file_status,
            ),
            SoftwareImageFile.objects.create(
                software_version=software_versions[1],
                image_file_name="software_image_file_qs_test_4.bin",
                status=software_image_file_status,
            ),
        )

        device_types = (
            DeviceType.objects.create(
                manufacturer=manufacturer,
                model="Test SoftwareImageFileQs Device Type 1",
            ),
            DeviceType.objects.create(
                manufacturer=manufacturer,
                model="Test SoftwareImageFileQs Device Type 2",
            ),
        )
        device_types[0].software_image_files.set(software_image_files[0:2])
        device_types[1].software_image_files.set(software_image_files[2:4])

        # This should only return the device types with a direct m2m relationship to the software image files
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(device_types[0]), software_image_files[0:2])
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(device_types[1]), software_image_files[2:4])

        devices = (
            Device.objects.create(
                device_type=device_types[0],
                role=role,
                name="Test SoftwareImageFileQs Device1",
                location=location,
                status=device_status,
                software_version=software_versions[0],
            ),
            Device.objects.create(
                device_type=device_types[1],
                role=role,
                name="Test SoftwareImageFileQs Device2",
                location=location,
                status=device_status,
                software_version=software_versions[0],
            ),
        )

        # Only return the software image files associated with the device's software version and device type
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(devices[0]), software_image_files[0:2])

        # When the device's software image files are overridden with the direct m2m relationship, return those
        devices[1].software_image_files.set(software_image_files[1:3])
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(devices[1]), software_image_files[1:3])

        # If no device types are associated with the software image files, return the default software image file
        device_types[0].software_image_files.clear()
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(devices[0]), [software_image_files[1]])

        inventory_items = (
            InventoryItem.objects.create(
                device=devices[0],
                name="Test SoftwareImageFileQs Inventory Item 1",
                software_version=software_versions[0],
            ),
            InventoryItem.objects.create(
                device=devices[1],
                name="Test SoftwareImageFileQs Inventory Item 2",
                software_version=software_versions[1],
            ),
        )

        # Only return the software image files associated with the inventory item's software version
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(inventory_items[0]), software_image_files[0:2])

        # When the inventory item's software image files are overridden with the direct m2m relationship, return those
        inventory_items[1].software_image_files.set(software_image_files[1:3])
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(inventory_items[1]), software_image_files[1:3])

        cluster_type = ClusterType.objects.create(name="Test SoftwareImageFileQs Cluster Type 1")
        cluster = Cluster.objects.create(name="Test SoftwareImageFileQs Cluster 1", cluster_type=cluster_type)
        virtual_machines = (
            VirtualMachine.objects.create(
                cluster=cluster,
                name="Test SoftwareImageFileQs Virtual Machine 1",
                status=virtual_machine_status,
                software_version=software_versions[0],
            ),
            VirtualMachine.objects.create(
                cluster=cluster,
                name="Test SoftwareImageFileQs Virtual Machine 2",
                status=virtual_machine_status,
                software_version=software_versions[1],
            ),
        )

        # Only return the software image files associated with the virtual machine's software version
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(virtual_machines[0]), software_image_files[0:2])

        # When the virtual machine's software image files are overridden with the direct m2m relationship, return those
        virtual_machines[1].software_image_files.set(software_image_files[1:3])
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(virtual_machines[1]), software_image_files[1:3])

        with self.assertRaises(TypeError):
            qs.get_for_object(Circuit)


class SoftwareVersionTestCase(ModelTestCases.BaseModelTestCase):
    model = SoftwareVersion

    def test_queryset_get_for_object(self):
        """
        Test that the queryset get_for_object method returns the expected results for Device, DeviceType, InventoryItem and VirtualMachine
        """
        qs = SoftwareVersion.objects.all()

        # Only return the device types with a direct m2m relationship to the version's software image files
        device_type = DeviceType.objects.filter(software_image_files__isnull=False).first()
        self.assertIsNotNone(device_type)
        self.assertQuerysetEqualAndNotEmpty(
            qs.get_for_object(device_type), qs.filter(software_image_files__device_types=device_type)
        )

        # Only return the software version set on the device's software_version foreign key
        device = Device.objects.filter(software_version__isnull=False).first()
        self.assertIsNotNone(device)
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(device), [device.software_version])

        # Only return the software version set on the inventory item's software_version foreign key
        software_version = SoftwareVersion.objects.first()
        inventory_item = InventoryItem.objects.create(
            device=device,
            name="Test SoftwareVersionQs Inventory Item 1",
            software_version=software_version,
        )
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(inventory_item), [inventory_item.software_version])

        # Only return the software version set on the virtual machine's software_version foreign key
        cluster_type = ClusterType.objects.create(name="Test SoftwareImageFileQs Cluster Type 1")
        cluster = Cluster.objects.create(name="Test SoftwareImageFileQs Cluster 1", cluster_type=cluster_type)
        virtual_machine = VirtualMachine.objects.create(
            cluster=cluster,
            name="Test SoftwareImageFileQs Virtual Machine",
            status=Status.objects.get_for_model(VirtualMachine).first(),
            software_version=software_version,
        )
        self.assertQuerysetEqualAndNotEmpty(qs.get_for_object(virtual_machine), [virtual_machine.software_version])

        with self.assertRaises(TypeError):
            qs.get_for_object(Circuit)


class ControllerTestCase(ModelTestCases.BaseModelTestCase):
    model = Controller

    def test_device_or_device_redundancy_group_validation(self):
        """Ensure a controller cannot be linked to both a device and a device redundancy group."""
        controller = Controller(
            name="Controller testing Device and Device Redundancy Group exclusivity",
            status=Status.objects.get_for_model(Controller).first(),
            role=Role.objects.get_for_model(Controller).first(),
            location=Location.objects.first(),
            controller_device=Device.objects.first(),
            controller_device_redundancy_group=DeviceRedundancyGroup.objects.first(),
        )
        with self.assertRaises(ValidationError) as error:
            controller.validated_save()
        self.assertEqual(
            error.exception.message_dict["controller_device"][0],
            "Cannot assign both a device and a device redundancy group to a controller.",
        )

    def test_location_content_type_validation(self):
        """Ensure a controller cannot be linked to a location of the wrong type."""
        location_type = LocationType.objects.create(name="Location type without content type")
        location = Location.objects.create(
            name="Location testing Location content type",
            location_type=location_type,
            status=Status.objects.get_for_model(Location).first(),
        )
        controller = Controller.objects.first()
        controller.location = location
        with self.assertRaises(ValidationError) as error:
            controller.validated_save()
        self.assertEqual(
            error.exception.message_dict["location"][0],
            f'Controllers may not associate to locations of type "{location_type}".',
        )


class ControllerManagedDeviceGroupTestCase(ModelTestCases.BaseModelTestCase):
    model = ControllerManagedDeviceGroup

    def test_controller_matches_parent(self):
        """Ensure a controller device group cannot be linked to a controller that does not match its parent."""
        controllers = iter(Controller.objects.all())
        parent_group = ControllerManagedDeviceGroup(
            name="Parent Group testing Controller match",
            controller=next(controllers),
        )
        parent_group.validated_save()

        child_group = ControllerManagedDeviceGroup(
            name="Child Group testing Controller match",
            controller=next(controllers),
            parent=parent_group,
        )
        self.assertNotEqual(parent_group.controller, child_group.controller, "Controllers should be different")

        with self.assertRaises(ValidationError) as error:
            child_group.validated_save()
        self.assertEqual(
            error.exception.message_dict["controller"][0],
            "Controller device group must have the same controller as the parent group.",
        )

    def test_parent_controller_change(self):
        """Ensure the controller of a parent group is updated in all descendant groups."""
        controller1, controller2 = Controller.objects.all()[:2]
        self.assertNotEqual(controller1, controller2, "Controllers should be different")

        parent_group = ControllerManagedDeviceGroup.objects.create(
            name="Parent Group testing Controller match",
            controller=controller1,
        )
        child_group1 = ControllerManagedDeviceGroup.objects.create(
            name="Child Group 1 testing Controller match",
            controller=controller1,
            parent=parent_group,
        )
        child_group2 = ControllerManagedDeviceGroup.objects.create(
            name="Child Group 2 testing Controller match",
            controller=controller1,
            parent=child_group1,
        )

        parent_group = ControllerManagedDeviceGroup.objects.get(pk=parent_group.pk)
        parent_group.controller = controller2
        parent_group.save()

        self.assertEqual(
            ControllerManagedDeviceGroup.objects.get(pk=parent_group.pk).controller,
            controller2,
            "Parent group controller should have been updated",
        )
        self.assertEqual(
            ControllerManagedDeviceGroup.objects.get(pk=child_group1.pk).controller,
            controller2,
            "Child group 1 controller should have been updated",
        )
        self.assertEqual(
            ControllerManagedDeviceGroup.objects.get(pk=child_group2.pk).controller,
            controller2,
            "Child group 2 controller should have been updated",
        )


class ModuleBayTestCase(ModularDeviceComponentTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = ModuleBay
    device_field = "parent_device"  # field name for the parent device
    module_field = "parent_module"  # field name for the parent module

    @classmethod
    def setUpTestData(cls):
        cls.device = Device.objects.first()
        cls.device.module_bays.all().delete()
        cls.module = Module.objects.first()
        cls.module.module_bays.all().delete()

    def test_parent_property(self):
        """Assert that the parent property walks up the inheritance tree of Device -> ModuleBay -> Module -> ModuleBay."""
        module_type = ModuleType.objects.first()
        status = Status.objects.get_for_model(Module).first()

        parent_module_bay = ModuleBay.objects.create(
            parent_device=self.device,
            name="1111",
            position="1111",
        )
        module = Module.objects.create(
            module_type=module_type,
            parent_module_bay=parent_module_bay,
            status=status,
        )
        child_module_bay = ModuleBay.objects.create(
            parent_module=module,
            name="1111",
            position="1111",
        )
        child_module = Module.objects.create(
            module_type=module_type,
            parent_module_bay=child_module_bay,
            status=status,
        )
        grandchild_module_bay = ModuleBay.objects.create(
            parent_module=child_module,
            name="1111",
            position="1111",
        )

        self.assertEqual(parent_module_bay.parent, self.device)
        self.assertEqual(child_module_bay.parent, self.device)
        self.assertEqual(grandchild_module_bay.parent, self.device)

        # Remove the module from the module bay and put it in storage
        module.parent_module_bay = None
        module.location = Location.objects.get_for_model(Module).first()
        module.save()

        self.assertEqual(parent_module_bay.parent, self.device)
        self.assertIsNone(child_module_bay.parent)
        self.assertIsNone(grandchild_module_bay.parent)

    def test_position_value_auto_population(self):
        """
        Assert that the value of the module bay position is auto-populated by its name if position is not provided by the user.
        """

        module_bay = ModuleBay.objects.create(
            parent_device=self.device,
            name="1111",
        )
        module_bay.validated_save()
        self.assertEqual(module_bay.position, module_bay.name)
        # Test the default value is overriden if the user provides a position value.
        module_bay.position = "1222"
        module_bay.validated_save()
        self.assertEqual(module_bay.position, "1222")


class ModuleBayTemplateTestCase(ModularDeviceComponentTemplateTestCaseMixin, ModelTestCases.BaseModelTestCase):
    model = ModuleBayTemplate

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.first()
        cls.device_type = cls.device = DeviceType.objects.create(
            manufacturer=manufacturer, model="Test ModuleBayTemplate DT1"
        )
        cls.module_type = cls.module = ModuleType.objects.create(
            manufacturer=manufacturer, model="Test ModuleBayTemplate MT1"
        )

        # Create some instances for the generic natural key tests to use
        ModuleBayTemplate.objects.create(
            device_type=cls.device_type,
            name="2222",
            position="2222",
        )
        ModuleBayTemplate.objects.create(
            device_type=cls.device_type,
            name="3333",
            position="3333",
        )
        ModuleBayTemplate.objects.create(
            module_type=cls.module_type,
            name="3333",
            position="3333",
        )
        ModuleBayTemplate.objects.create(
            module_type=cls.module_type,
            name="4444",
            position="4444",
        )

    def test_parent_property(self):
        module_bay_template = ModuleBayTemplate.objects.create(
            device_type=self.device_type,
            name="1111",
            position="1111",
        )
        self.assertEqual(module_bay_template.parent, self.device_type)

        module_bay_template = ModuleBayTemplate.objects.create(
            module_type=self.module_type,
            name="1111",
            position="1111",
        )
        self.assertEqual(module_bay_template.parent, self.module_type)


class ModuleTestCase(ModelTestCases.BaseModelTestCase):
    model = Module

    @classmethod
    def setUpTestData(cls):
        cls.device = Device.objects.filter(module_bays__isnull=True).first()
        manufacturer = Manufacturer.objects.first()
        cls.module_type = ModuleType.objects.create(manufacturer=manufacturer, model="module model tests")
        cls.location = Location.objects.get_for_model(Module).first()
        cls.status = Status.objects.get_for_model(Module).first()

        # Create ModuleType components
        ConsolePortTemplate.objects.create(module_type=cls.module_type, name="Console Port 1")
        ConsoleServerPortTemplate.objects.create(module_type=cls.module_type, name="Console Server Port 1")

        ppt = PowerPortTemplate.objects.create(
            module_type=cls.module_type,
            name="Power Port 1",
            maximum_draw=1000,
            allocated_draw=500,
        )

        PowerOutletTemplate.objects.create(
            module_type=cls.module_type,
            name="Power Outlet 1",
            power_port_template=ppt,
            feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
        )

        InterfaceTemplate.objects.create(
            module_type=cls.module_type,
            name="Interface {module.parent.parent}/{module.parent}/{module}",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        )

        rpt = RearPortTemplate.objects.create(
            module_type=cls.module_type,
            name="Rear Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            positions=8,
        )

        FrontPortTemplate.objects.create(
            module_type=cls.module_type,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port_template=rpt,
            rear_port_position=2,
        )

        ModuleBayTemplate.objects.create(
            module_type=cls.module_type,
            position="1111",
        )

        cls.module = Module.objects.create(
            module_type=cls.module_type,
            location=cls.location,
            status=cls.status,
        )
        cls.module_bay = cls.module.module_bays.first()

    def test_parent_validation_module_bay_and_location(self):
        """Assert that a module must have a parent module bay or location but not both."""
        module = Module(
            module_type=self.module_type,
            parent_module_bay=self.module_bay,
            location=self.location,
            status=self.status,
        )

        with self.assertRaises(ValidationError):
            module.full_clean()

    def test_parent_validation_no_module_bay_or_location(self):
        """Assert that a module must have a parent module bay or location but not both."""
        module = Module(
            module_type=self.module_type,
            status=self.status,
        )

        with self.assertRaises(ValidationError):
            module.full_clean()

    def test_parent_validation_succeeds(self):
        """Assert that a module must have a parent module bay or location but not both."""
        with self.subTest("Module with a parent module bay"):
            module = Module(
                module_type=self.module_type,
                parent_module_bay=self.module_bay,
                status=self.status,
            )

            module.full_clean()
            module.save()

        with self.subTest("Module with a parent location"):
            module = Module(
                module_type=self.module_type,
                location=self.location,
                status=self.status,
            )

            module.full_clean()
            module.save()

    def test_device_property(self):
        """Assert that the device property walks up the inheritance tree of Device -> ModuleBay -> Module -> ModuleBay."""
        parent_module_bay = ModuleBay.objects.create(
            parent_device=self.device,
            position="1111",
        )
        parent_module = Module.objects.create(
            module_type=self.module_type,
            parent_module_bay=parent_module_bay,
            status=self.status,
        )
        child_module_bay = parent_module.module_bays.first()
        child_module = Module.objects.create(
            module_type=self.module_type,
            parent_module_bay=child_module_bay,
            status=self.status,
        )
        grandchild_module_bay = child_module.module_bays.first()
        grandchild_module = Module.objects.create(
            module_type=self.module_type,
            parent_module_bay=grandchild_module_bay,
            status=self.status,
        )

        self.assertEqual(parent_module.device, self.device)
        self.assertEqual(child_module.device, self.device)
        self.assertEqual(grandchild_module.device, self.device)

        # Remove the module from the module bay and put it in storage
        parent_module.parent_module_bay = None
        parent_module.location = self.location
        parent_module.save()

        self.assertIsNone(parent_module.device)
        self.assertIsNone(child_module.device)
        self.assertIsNone(grandchild_module.device)

    def test_null_serial_asset_tag(self):
        """Assert that the serial and asset_tag fields are converted to None if a blank string is supplied."""
        module = Module.objects.create(
            module_type=self.module_type,
            status=self.status,
            parent_module_bay=self.module_bay,
            serial="",
            asset_tag="",
        )

        module.refresh_from_db()

        self.assertIsNone(module.serial)
        self.assertIsNone(module.asset_tag)

        module.delete()
        module = Module.objects.create(
            module_type=self.module_type,
            status=self.status,
            parent_module_bay=self.module_bay,
        )

        module.refresh_from_db()

        self.assertIsNone(module.serial)
        self.assertIsNone(module.asset_tag)

    def test_module_components_created(self):
        module = Module(
            location=self.location,
            module_type=self.module_type,
            status=self.status,
        )
        module.validated_save()
        self.assertEqual(module.console_ports.count(), self.module_type.console_port_templates.count())
        self.assertEqual(module.console_server_ports.count(), self.module_type.console_server_port_templates.count())
        self.assertEqual(module.power_ports.count(), self.module_type.power_port_templates.count())
        self.assertEqual(module.power_outlets.count(), self.module_type.power_outlet_templates.count())
        self.assertEqual(module.interfaces.count(), self.module_type.interface_templates.count())
        self.assertEqual(module.front_ports.count(), self.module_type.front_port_templates.count())
        self.assertEqual(module.rear_ports.count(), self.module_type.rear_port_templates.count())
        self.assertEqual(module.module_bays.count(), self.module_type.module_bay_templates.count())

        ConsolePort.objects.get(module=module, name="Console Port 1")

        ConsoleServerPort.objects.get(module=module, name="Console Server Port 1")

        pp = PowerPort.objects.get(module=module, name="Power Port 1", maximum_draw=1000, allocated_draw=500)

        PowerOutlet.objects.get(
            module=module,
            name="Power Outlet 1",
            power_port=pp,
            feed_leg=PowerOutletFeedLegChoices.FEED_LEG_A,
        )

        Interface.objects.get(
            module=module,
            name="Interface {module.parent.parent}/{module.parent}/{module}",
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            mgmt_only=True,
        )

        rp = RearPort.objects.get(module=module, name="Rear Port 1", type=PortTypeChoices.TYPE_8P8C, positions=8)

        FrontPort.objects.get(
            module=module,
            name="Front Port 1",
            type=PortTypeChoices.TYPE_8P8C,
            rear_port=rp,
            rear_port_position=2,
        )

        ModuleBay.objects.get(parent_module=module, position="1111")

    def test_module_infinite_recursion_self_parent(self):
        """Assert that a module cannot be its own parent."""
        module = Module.objects.create(
            location=self.location,
            module_type=self.module_type,
            status=self.status,
        )
        module_bay = module.module_bays.first()
        module.parent_module_bay = module_bay

        with self.assertRaises(ValidationError) as context:
            module.save()
        self.assertEqual(context.exception.message, "Creating this instance would cause an infinite loop.")

    def test_module_infinite_recursion_ancestor(self):
        """Assert that a module cannot be its own ancestor."""
        parent_module = Module.objects.create(
            module_type=self.module_type,
            location=self.location,
            status=self.status,
        )
        parent_module_bay = parent_module.module_bays.first()
        child_module = Module.objects.create(
            module_type=self.module_type,
            parent_module_bay=parent_module_bay,
            status=self.status,
        )
        child_module_bay = child_module.module_bays.first()
        parent_module.parent_module_bay = child_module_bay
        parent_module.location = None

        with self.assertRaises(ValidationError) as context:
            parent_module.save()

        self.assertEqual(context.exception.message, "Creating this instance would cause an infinite loop.")

    def test_render_component_names(self):
        """Test that creating a Module with components properly renders the {module} and {module.parent} variables."""
        grandparent_module = Module.objects.create(
            module_type=self.module_type,
            location=self.location,
            status=self.status,
        )
        grandparent_module_bay = grandparent_module.module_bays.first()
        grandparent_module_bay.position = "3"
        grandparent_module_bay.save()
        parent_module = Module.objects.create(
            parent_module_bay=grandparent_module.module_bays.first(),
            module_type=self.module_type,
            status=self.status,
        )
        parent_module.clean()
        parent_module_bay = parent_module.module_bays.first()
        parent_module_bay.position = "2"
        parent_module_bay.save()
        child_module = Module.objects.create(
            parent_module_bay=parent_module.module_bays.first(),
            module_type=self.module_type,
            status=self.status,
        )
        child_module.clean()

        self.assertEqual(
            grandparent_module.interfaces.first().name, "Interface {module.parent.parent}/{module.parent}/{module}"
        )
        self.assertEqual(parent_module.interfaces.first().name, "Interface {module.parent.parent}/{module.parent}/3")
        self.assertEqual(child_module.interfaces.first().name, "Interface {module.parent.parent}/3/2")

        # Moving the grandparent module out of inventory populates the template variables on all descendant interfaces
        grandparent_module.parent_module_bay = self.module_bay
        grandparent_module.location = None
        grandparent_module.validated_save()
        module_bay_position = self.module_bay.position
        self.assertEqual(
            grandparent_module.interfaces.first().name,
            "Interface {module.parent.parent}/{module.parent}/" + module_bay_position,
        )
        self.assertEqual(
            parent_module.interfaces.first().name, "Interface {module.parent.parent}/" + module_bay_position + "/3"
        )
        self.assertEqual(child_module.interfaces.first().name, "Interface " + module_bay_position + "/3/2")

    def test_module_manufacturer_constraint_requires_first_party_false(self):
        """Test that modules are allowed when requires_first_party_modules is False, regardless of manufacturer."""
        manufacturer = Manufacturer.objects.create(name="Different Manufacturer")
        module_type = ModuleType.objects.create(manufacturer=manufacturer, model="Different Module")
        module_bay = ModuleBay.objects.create(
            parent_device=self.device, position="test1", requires_first_party_modules=False
        )
        module = Module(
            module_type=module_type,
            parent_module_bay=module_bay,
            status=self.status,
        )

        module.full_clean()
        module.save()

    def test_module_manufacturer_constraint_device_parent_same_manufacturer(self):
        """Test that modules are allowed when requires_first_party_modules is True and manufacturers match."""
        device_manufacturer = self.device.device_type.manufacturer
        module_type = ModuleType.objects.create(manufacturer=device_manufacturer, model="Same Manufacturer Module")
        module_bay = ModuleBay.objects.create(
            parent_device=self.device, position="test2", requires_first_party_modules=True
        )
        module = Module(
            module_type=module_type,
            parent_module_bay=module_bay,
            status=self.status,
        )

        module.full_clean()
        module.save()

    def test_module_manufacturer_constraint_device_parent_different_manufacturer(self):
        """Test that modules are rejected when requires_first_party_modules is True and manufacturers don't match."""
        manufacturer = Manufacturer.objects.create(name="Different Manufacturer")
        module_type = ModuleType.objects.create(manufacturer=manufacturer, model="Different Module")
        module_bay = ModuleBay.objects.create(
            parent_device=self.device, position="test3", requires_first_party_modules=True
        )
        module = Module(
            module_type=module_type,
            parent_module_bay=module_bay,
            status=self.status,
        )

        with self.assertRaises(ValidationError) as context:
            module.full_clean()

        self.assertIn("module_type", context.exception.message_dict)
        self.assertIn(
            "The selected module bay requires a module type from the same manufacturer as the parent device or module",
            context.exception.message_dict["module_type"],
        )

    def test_module_manufacturer_constraint_module_parent_same_manufacturer(self):
        """Test that modules are allowed when requires_first_party_modules is True and manufacturers match."""
        manufacturer = Manufacturer.objects.create(name="Parent Manufacturer")
        parent_module_type = ModuleType.objects.create(manufacturer=manufacturer, model="Parent Module")
        ModuleBayTemplate.objects.create(module_type=parent_module_type, position="child1")

        parent_module = Module.objects.create(
            module_type=parent_module_type,
            location=self.location,
            status=self.status,
        )
        child_module_type = ModuleType.objects.create(manufacturer=manufacturer, model="Child Module")
        parent_module_bay = parent_module.module_bays.first()
        parent_module_bay.requires_first_party_modules = True
        parent_module_bay.save()

        child_module = Module(
            module_type=child_module_type,
            parent_module_bay=parent_module_bay,
            status=self.status,
        )

        child_module.full_clean()
        child_module.save()

    def test_module_manufacturer_constraint_module_parent_different_manufacturer(self):
        """Test that modules are rejected when requires_first_party_modules is True and manufacturers don't match."""
        parent_manufacturer = Manufacturer.objects.create(name="Parent Manufacturer")
        parent_module_type = ModuleType.objects.create(manufacturer=parent_manufacturer, model="Parent Module")
        ModuleBayTemplate.objects.create(module_type=parent_module_type, position="child2")

        parent_module = Module.objects.create(
            module_type=parent_module_type,
            location=self.location,
            status=self.status,
        )
        child_manufacturer = Manufacturer.objects.create(name="Child Manufacturer")
        child_module_type = ModuleType.objects.create(manufacturer=child_manufacturer, model="Child Module")
        parent_module_bay = parent_module.module_bays.first()
        parent_module_bay.requires_first_party_modules = True
        parent_module_bay.save()

        child_module = Module(
            module_type=child_module_type,
            parent_module_bay=parent_module_bay,
            status=self.status,
        )

        with self.assertRaises(ValidationError) as context:
            child_module.full_clean()

        self.assertIn("module_type", context.exception.message_dict)
        self.assertIn(
            "The selected module bay requires a module type from the same manufacturer as the parent device or module",
            context.exception.message_dict["module_type"],
        )

    def test_module_manufacturer_constraint_no_parent_module_bay(self):
        """Test that manufacturer constraint validation is skipped when parent_module_bay is None."""
        manufacturer = Manufacturer.objects.create(name="Any Manufacturer")
        module_type = ModuleType.objects.create(manufacturer=manufacturer, model="Any Module")
        module = Module(
            module_type=module_type,
            location=self.location,
            status=self.status,
        )

        module.full_clean()
        module.save()


class ModuleTypeTestCase(ModelTestCases.BaseModelTestCase):
    model = ModuleType


class VirtualDeviceContextTestCase(ModelTestCases.BaseModelTestCase):
    model = VirtualDeviceContext

    def test_assigning_primary_ip(self):
        device = Device.objects.first()
        vdc_status = Status.objects.get_for_model(VirtualDeviceContext).first()
        vdc = VirtualDeviceContext(
            device=device,
            status=vdc_status,
            identifier=100,
            name="Test VDC 1",
        )
        vdc.validated_save()

        ip_v4 = IPAddress.objects.filter(ip_version=4).first()
        ip_v6 = IPAddress.objects.filter(ip_version=6).first()

        vdc.primary_ip4 = ip_v6
        with self.assertRaises(ValidationError) as err:
            vdc.validated_save()
        self.assertIn(
            f"{ip_v6} is not an IPv4 address",
            str(err.exception),
        )

        vdc.primary_ip4 = None
        vdc.primary_ip6 = ip_v4
        with self.assertRaises(ValidationError) as err:
            vdc.validated_save()
        self.assertIn(
            f"{ip_v4} is not an IPv6 address",
            str(err.exception),
        )

        namespace = Namespace.objects.create(name="test_name_space")
        Prefix.objects.create(
            prefix="10.1.1.0/24", namespace=namespace, status=Status.objects.get_for_model(Prefix).first()
        )
        vdc.primary_ip4 = IPAddress.objects.create(
            address="10.1.1.1/24", namespace=namespace, status=Status.objects.get_for_model(IPAddress).first()
        )
        with self.assertRaises(ValidationError) as err:
            vdc.validated_save()
        self.assertIn(
            f"{vdc.primary_ip4} is not part of an interface that belongs to this VDC's device.",
            str(err.exception),
        )

        # TODO: Uncomment test case when VDC primary_ip interface validation is active
        # interface = Interface.objects.create(
        #     name="Int1", device=device, status=intf_status, role=intf_role, type=InterfaceTypeChoices.TYPE_100GE_CFP
        # )
        # intf_status = Status.objects.get_for_model(Interface).first()
        # intf_role = Role.objects.get_for_model(Interface).first()
        # vdc.primary_ip6 = ip_v6
        # with self.assertRaises(ValidationError) as err:
        #     vdc.validated_save()
        # self.assertIn(
        #     f"The specified IP address ({ip_v6}) is not assigned to this Virtual Device Context.",
        #     str(err.exception),
        # )
        # interface.virtual_device_contexts.add(vdc)
        # interface.add_ip_addresses([ip_v4, ip_v6])

    def test_interfaces_validation_logic(self):
        """Assert Virtual Device COntext raises error when adding interfaces that do not belong to same device as the VDC's device."""
        device = Device.objects.first()
        interface = Interface.objects.create(
            name="Int1",
            type=InterfaceTypeChoices.TYPE_VIRTUAL,
            device=device,
            status=Status.objects.get_for_model(Interface).first(),
            role=Role.objects.get_for_model(Interface).first(),
        )
        vdc = VirtualDeviceContext.objects.create(
            name="Sample VDC",
            device=Device.objects.exclude(pk=device.pk).first(),
            identifier=99,  # factory creates identifiers starting from 100
            status=Status.objects.get_for_model(VirtualDeviceContext).first(),
        )

        with self.assertRaises(ValidationError) as err:
            vdc.interfaces.add(interface)
        self.assertEqual(
            err.exception.message_dict["interfaces"][0],
            f"Interfaces with names {[interface.name]} must all belong to the "
            f"same device as the Virtual Device Context's device.",
        )

    def test_modifying_vdc_device_not_allowed(self):
        vdc = VirtualDeviceContext.objects.first()
        old_device = vdc.device
        new_device = Device.objects.exclude(pk=old_device.pk).first()
        with self.assertRaises(ValidationError) as err:
            vdc.device = new_device
            vdc.validated_save()

        self.assertIn("Virtual Device Context's device cannot be changed once created", str(err.exception))


class ModuleFamilyTestCase(ModelTestCases.BaseModelTestCase):
    """Test cases for the ModuleFamily model."""

    model = ModuleFamily

    def setUp(self):
        """Create a ModuleFamily for use in test methods."""
        self.module_family = ModuleFamily.objects.create(
            name="Test Module Family", description="A module family for testing"
        )

    def test_create_modulefamily(self):
        """Test the creation of a ModuleFamily instance."""
        self.assertEqual(self.module_family.name, "Test Module Family")
        self.assertEqual(self.module_family.description, "A module family for testing")

    def test_modulefamily_str(self):
        """Test string representation of ModuleFamily."""
        self.assertEqual(str(self.module_family), "Test Module Family")
