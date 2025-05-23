from django.contrib.contenttypes.models import ContentType

from nautobot.data_validation.models import RequiredValidationRule


class DataValidationFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._apply_data_validation_rules()

    def _apply_data_validation_rules(self):
        # Use only with ModelForm's
        if hasattr(self, "_meta") and hasattr(self._meta, "model"):
            content_type = ContentType.objects.get_for_model(self._meta.model)
            required_fields_rules = RequiredValidationRule.objects.get_enabled_for_model(
                f"{content_type.app_label}.{content_type.model}"
            )

            for rule in required_fields_rules:
                if rule.field in self.fields:
                    field = self.fields[rule.field]
                    field.required = True

                    if rule.error_message:
                        field.widget.attrs["oninvalid"] = f"this.setCustomValidity('{rule.error_message}')"
