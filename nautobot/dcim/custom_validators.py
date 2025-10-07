from django.conf import settings

from nautobot.apps.models import CustomValidator
from nautobot.dcim.models import Device


class DeviceUniqueTogetherValidator(CustomValidator):
    """Custom validator enforcing device uniqueness by Location, Tenant, and Name."""

    model = "dcim.device"

    def clean(self):
        obj = self.context["object"]
        if getattr(settings, "DEVICE_UNIQUENESS") != "location_tenant_name":
            return

        if not obj.name:
            return

        # Check for duplicates
        duplicates = Device.objects.filter(
            name=obj.name,
            tenant=obj.tenant,
            location=obj.location,
        ).exclude(pk=obj.pk)

        if duplicates.exists():
            self.validation_error(
                {
                    "__all__": (
                        f"A device named '{obj.name}' already exists in this location: {obj.location} and tenant: {obj.tenant}. "
                        "Device names must be unique per (Location, Tenant)."
                    )
                }
            )


class DeviceNameUniqueValidator(CustomValidator):
    """Custom validator enforcing that all device names are globally unique."""

    model = "dcim.device"

    def clean(self):
        obj = self.context["object"]

        if getattr(settings, "DEVICE_UNIQUENESS") != "name":
            return

        # Skip validation if name is blank or null
        if not obj.name:
            return

        # Check for other devices using the same name
        duplicates = Device.objects.filter(name=obj.name).exclude(pk=obj.pk)

        if duplicates.exists():
            self.validation_error(
                {
                    "name": (
                        f"A device named '{obj.name}' already exists. "
                        "Device names must be globally unique when DEVICE_UNIQUENESS='name'."
                    )
                }
            )


custom_validators = [DeviceUniqueTogetherValidator, DeviceNameUniqueValidator]
