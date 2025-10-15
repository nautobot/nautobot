from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.test import override_settings, TestCase

from nautobot.core.testing.mixins import NautobotTestCaseMixin
from nautobot.data_validation.models import RequiredValidationRule
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
    def test_duplicate_same_location_tenant_name_fails(self):
        """Same name, tenant, and location should raise ValidationError."""
        dup_device = Device(
            name=self.device_name,
            device_type=self.device_type,
            role=self.device_role,
            location=self.location,
            status=self.device_status,
            tenant=self.tenant,
        )
        with self.assertRaises(ValidationError) as contextmanager:
            dup_device.full_clean()
        self.assertIn(
            f"A device named '{self.device_name}' already exists in this location: {self.location} and tenant: {self.tenant}. ",
            str(contextmanager.exception),
        )

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.LOCATION_TENANT_NAME)
    def test_different_tenant_allows_duplicate_name(self):
        """Same name and location, different tenant should be allowed."""
        tenant = Tenant.objects.create(name="Tenant2")
        non_dup_device = Device(
            name=self.device_name,
            device_type=self.device_type,
            role=self.device_role,
            location=self.location,
            status=self.device_status,
            tenant=tenant,
        )
        non_dup_device.full_clean()  # should not raise

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.LOCATION_TENANT_NAME)
    def test_different_location_allows_duplicate_name(self):
        """Same name and tenant, different location should be allowed."""
        location = Location.objects.last()
        non_dup_device = Device(
            name=self.device_name,
            device_type=self.device_type,
            role=self.device_role,
            location=location,
            status=self.device_status,
            tenant=self.tenant,
        )
        non_dup_device.full_clean()  # should not raise

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.LOCATION_TENANT_NAME)
    def test_duplicate_name_with_null_tenant_fails(self):
        """Duplicate name with tenant=None should raise ValidationError."""
        Device.objects.create(
            name="Device-2",
            location=self.location,
            tenant=None,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        dup = Device(
            name="Device-2",
            location=self.location,
            tenant=None,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        with self.assertRaises(ValidationError) as contextmanager:
            dup.full_clean()
        self.assertIn(
            f"A device named '{dup.name}' with no tenant already exists in this location: {self.location}. ",
            str(contextmanager.exception),
        )

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.NAME)
    def test_duplicate_name_globally_fails(self):
        """Duplicate name should raise ValidationError."""
        tenant = Tenant.objects.create(name="Tenant2")
        location = Location.objects.last()
        dup_device = Device(
            name=self.device_name,
            device_type=self.device_type,
            role=self.device_role,
            location=location,
            status=self.device_status,
            tenant=tenant,
        )
        with self.assertRaises(ValidationError) as contextmanager:
            dup_device.full_clean()
        self.assertIn(
            f"At least one other device named '{dup_device.name}' already exists. ", str(contextmanager.exception)
        )

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.NAME)
    def test_different_name_succeeds(self):
        """Different name should be allowed globally."""
        non_dup_device = Device(
            name="Device-2",
            device_type=self.device_type,
            role=self.device_role,
            location=self.location,
            status=self.device_status,
            tenant=self.tenant,
        )
        non_dup_device.full_clean()  # should not raise

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.NAME)
    def test_unnamed_device_allowed_if_name_not_required(self):
        """Unnamed device allowed if DEVICE_NAME_REQUIRED is False."""
        Device.objects.create(
            name=None,
            location=self.location,
            tenant=self.tenant,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        unnamed2 = Device(
            name=None,
            location=self.location,
            tenant=self.tenant,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        self.assertFalse(
            RequiredValidationRule.objects.filter(
                content_type=ContentType.objects.get_for_model(Device), field="name"
            ).exists()
        )
        unnamed2.full_clean()  # should not raise

    def test_unnamed_device_fails_if_name_is_required(self):
        """Unnamed device should raise a ValidationError if DEVICE_NAME_REQUIRED is True."""
        unnamed = Device(
            name=None,
            location=self.location,
            tenant=self.tenant,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        RequiredValidationRule.objects.create(content_type=ContentType.objects.get_for_model(Device), field="name")
        with self.assertRaises(ValidationError) as contextmanager:
            unnamed.full_clean()
        # This error is from RequiredValidationRule
        self.assertIn("{'name': ['This field cannot be blank.']}", str(contextmanager.exception))

    def test_empty_device_fails_if_name_is_required(self):
        """Empty name device should raise a ValidationError if DEVICE_NAME_REQUIRED is True."""
        unnamed = Device(
            name="",
            location=self.location,
            tenant=self.tenant,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        RequiredValidationRule.objects.create(content_type=ContentType.objects.get_for_model(Device), field="name")
        with self.assertRaises(ValidationError) as contextmanager:
            unnamed.full_clean()
        # This error is from RequiredValidationRule
        self.assertIn("{'name': ['This field cannot be blank.']}", str(contextmanager.exception))

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
        dup_device.full_clean()

    @override_settings(DEVICE_UNIQUENESS=DeviceUniquenessChoices.NONE)
    def test_allow_duplicate_devices_with_empty_name_when_uniqueness_is_none(self):
        """Allow duplicate devices with empty name when DEVICE_UNIQUENESS="none"."""
        Device.objects.create(
            name="",
            location=self.location,
            tenant=self.tenant,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        empty_name = Device(
            name="",
            location=self.location,
            tenant=self.tenant,
            device_type=self.device_type,
            role=self.device_role,
            status=self.device_status,
        )
        empty_name.full_clean()
