from django.conf import settings

from nautobot.apps.models import CustomValidator
from nautobot.dcim.choices import DeviceUniquenessChoices
from nautobot.dcim.models import Device


class DeviceUniquenessValidator(CustomValidator):
    """Custom validator enforcing device uniqueness based on DEVICE_UNIQUENESS setting."""

    model = "dcim.device"

    def clean(self):
        obj = self.context["object"]
        uniqueness_mode = getattr(settings, "DEVICE_UNIQUENESS", DeviceUniquenessChoices.DEFAULT)

        if not obj.name:
            return

        if uniqueness_mode == DeviceUniquenessChoices.LOCATION_TENANT_NAME:
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
                            "Device names must be unique per (Location, Tenant) when DEVICE_UNIQUENESS='location_tenant_name'."
                        )
                    }
                )

        elif uniqueness_mode == DeviceUniquenessChoices.NAME:
            duplicates = Device.objects.filter(name=obj.name).exclude(pk=obj.pk)
            if duplicates.exists():
                self.validation_error(
                    {
                        "name": (
                            f"At least one other device named '{obj.name}' already exists. "
                            "Device names must be globally unique when DEVICE_UNIQUENESS='name'."
                        )
                    }
                )

        elif uniqueness_mode == "none":
            # Explicitly no uniqueness enforcement
            return

        else:
            self.validation_error(
                {
                    "__all__": (
                        f"Invalid DEVICE_UNIQUENESS setting '{uniqueness_mode}'. "
                        f"Expected one of: {', '.join(DeviceUniquenessChoices.values())}."
                    )
                }
            )


custom_validators = [DeviceUniquenessValidator]
