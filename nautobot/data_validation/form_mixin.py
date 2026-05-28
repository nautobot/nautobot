from django.utils.html import strip_tags

from nautobot.data_validation.models import RequiredValidationRule


class DataValidationModelFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._apply_data_validation_rules()

    def _apply_data_validation_rules(self):
        # Use only with ModelForm's
        if not hasattr(self, "_meta") or not hasattr(self._meta, "model"):
            raise TypeError("This mixin works only with ModelForms")

        required_fields_rules = RequiredValidationRule.objects.get_enabled_for_model(self._meta.model._meta.label_lower)

        for rule in required_fields_rules:
            if rule.field in self.fields:
                field = self.fields[rule.field]
                field.required = True

                if rule.error_message:
                    field.widget.attrs["oninvalid"] = f"this.setCustomValidity('{strip_tags(rule.error_message)}')"
