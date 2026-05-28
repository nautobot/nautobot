from django.contrib.contenttypes.models import ContentType

from nautobot.apps.models import CustomValidator
from nautobot.core.utils.config import get_settings_or_config
from nautobot.data_validation.models import RequiredValidationRule
from nautobot.dcim.choices import DeviceUniquenessChoices
from nautobot.dcim.models import Device


class DeviceUniquenessValidator(CustomValidator):
    """Custom validator enforcing device uniqueness based on DEVICE_UNIQUENESS setting."""

    model = "dcim.device"

    def clean(self):
        obj = self.context["object"]
        try:
            uniqueness_mode = get_settings_or_config("DEVICE_UNIQUENESS", fallback=DeviceUniquenessChoices.DEFAULT)
        except AttributeError:
            uniqueness_mode = DeviceUniquenessChoices.DEFAULT
        device_name_required = RequiredValidationRule.objects.filter(
            content_type=ContentType.objects.get_for_model(Device), field="name"
        ).exists()

        # Rule 1: If we don't set DEVICE_NAME_REQUIRED then it's acceptable for any number of devices to be "unnamed",
        # regardless of the DEVICE_UNIQUENESS setting. Note that we consider both `None` and `""` to be "unnamed".
        if not obj.name and not device_name_required:
            return

        # If not obj.name and device_name_required, this will be detected by RequiredValidationRule.

        if uniqueness_mode == DeviceUniquenessChoices.LOCATION_TENANT_NAME:
            # Rule 2: name is not None, tenant is None, given location --> no duplicates
            # Rule 3: tenant is None, name is duplicated --> error
            if obj.tenant is None:
                duplicates = Device.objects.filter(
                    name=obj.name,
                    tenant__isnull=True,
                    location=obj.location,
                ).exclude(pk=obj.pk)
                if duplicates.exists():
                    self.validation_error(
                        {
                            "__all__": (
                                f"A device named '{obj.name}' with no tenant already exists in this location: {obj.location}. "
                                "Device names must be unique when tenant is None and DEVICE_UNIQUENESS='location_tenant_name'."
                            )
                        }
                    )
            else:
                # When tenant is set, enforce uniqueness per (location, tenant, name)
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


custom_validators = [DeviceUniquenessValidator]
