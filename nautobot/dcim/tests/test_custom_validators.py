from django.core.exceptions import ValidationError
from django.test import override_settings, TestCase

from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.dcim.choices import DeviceUniquenessChoices
from nautobot.dcim.models import Device, DeviceType, Location
from nautobot.extras.models import Role, Status
from nautobot.tenancy.models import Tenant


class DeviceUniquenessValidatorTest(NautobotTestCaseMixin, TestCase):
    """Tests for the DeviceUniquenessValidator custom validator."""

    def setUp(self):
        super().setUp()
        self.device_status = Status.objects.get_for_model(Device).first()
        self.device_type = DeviceType.objects.first()
        self.device_role = Role.objects.get_for_model(Device).first()
        self.location = Location.objects.first()
        self.tenant = Tenant.objects.create(name="Tenant")
        self.device_name = "Device"
        self.device = Device.objects.create(
            name=self.device_name,
            device_type=self.device_type,
            role=self.device_role,
            location=self.location,
            status=self.device_status,
            tenant=self.tenant,
        )

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.LOCATION_TENANT_NAME)
    def test_location_tenant_name_uniqueness(self):
        """Devices must be unique by (Location, Tenant, Name)."""
        dup_device = Device(
            name=self.device_name,
            device_type=self.device_type,
            role=self.device_role,
            location=self.location,
            status=self.device_status,
            tenant=self.tenant,
        )
        # Should fail because same (location, tenant, name)
        with self.assertRaises(ValidationError):
            dup_device.full_clean()

        # Different tenant should be fine
        dup_device.tenant = None
        dup_device.full_clean()  # should not raise

        # Different location should be fine
        dup_device.tenant = self.tenant
        dup_device.location = Location.objects.exclude(pk=self.location.pk).first()
        dup_device.full_clean()  # should not raise

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.NAME)
    def test_global_name_uniqueness(self):
        """Devices must have globally unique names when DEVICE_UNIQUENESS='name'."""
        dup_device = Device(
            name=self.device_name,
            device_type=self.device_type,
            role=self.device_role,
            location=self.location,
            status=self.device_status,
            tenant=None,
        )

        # Should fail because same name globally
        with self.assertRaises(ValidationError):
            dup_device.full_clean()

        # Different name should succeed
        dup_device.name = "device-2"
        dup_device.full_clean()  # should not raise

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.NONE)
    def test_no_uniqueness_enforced(self):
        """Devices should not trigger validation errors when uniqueness is disabled."""
        dup_device = Device(
            name=self.device.name,
            location=self.location,
            tenant=self.tenant,
            role=self.device_role,
            device_type=self.device_type,
            status=self.device_status,
        )

        # Should NOT raise any error since uniqueness enforcement is off
        dup_device.full_clean()  # should not raise
