from collections import OrderedDict

from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class CustomFieldModel(models.Model):
    """
    Abstract class for any model which may have custom fields associated with it.
    """

    _custom_field_data = models.JSONField(encoder=DjangoJSONEncoder, blank=True, default=dict)

    class Meta:
        abstract = True

    @property
    def custom_field_data(self):
        """
        Legacy interface to raw custom field data

        TODO(John): remove this entirely when the cf property is enhanced
        """
        return self._custom_field_data

    @property
    def cf(self):
        """
        Convenience wrapper for custom field data.
        """
        return self._custom_field_data

    def get_custom_fields_basic(self):
        """
        This method exists to help call get_custom_fields() in templates where a function argument (advanced_ui) cannot be specified.
        Return a dictionary of custom fields for a single object in the form {<field>: value}
        which have advanced_ui set to False
        """
        return self.get_custom_fields(advanced_ui=False)

    def get_custom_fields_advanced(self):
        """
        This method exists to help call get_custom_fields() in templates where a function argument (advanced_ui) cannot be specified.
        Return a dictionary of custom fields for a single object in the form {<field>: value}
        which have advanced_ui set to True
        """
        return self.get_custom_fields(advanced_ui=True)

    def get_custom_fields(self, advanced_ui=None):
        """
        Return a dictionary of custom fields for a single object in the form {<field>: value}.
        """
        # Avoid circular import
        from nautobot.extras.models import CustomField

        fields = CustomField.objects.get_for_model(self)
        if advanced_ui is not None:
            fields = fields.filter(advanced_ui=advanced_ui)
        # 2.0 TODO: #824 field.slug rather than field.name
        return OrderedDict([(field, self.cf.get(field.name)) for field in fields])

    def get_custom_field_groupings_basic(self):
        """
        This method exists to help call get_custom_field_groupings() in templates where a function argument (advanced_ui) cannot be specified.
        Return a dictonary of custom fields grouped by the same grouping in the form
        {
            <grouping_1>: [(cf1, <value for cf1>), (cf2, <value for cf2>), ...],
            ...
            <grouping_5>: [(cf8, <value for cf8>), (cf9, <value for cf9>), ...],
            ...
        }
        which have advanced_ui set to False
        """
        return self.get_custom_field_groupings(advanced_ui=False)

    def get_custom_field_groupings_advanced(self):
        """
        This method exists to help call get_custom_field_groupings() in templates where a function argument (advanced_ui) cannot be specified.
        Return a dictonary of custom fields grouped by the same grouping in the form
        {
            <grouping_1>: [(cf1, <value for cf1>), (cf2, <value for cf2>), ...],
            ...
            <grouping_5>: [(cf8, <value for cf8>), (cf9, <value for cf9>), ...],
            ...
        }
        which have advanced_ui set to True
        """
        return self.get_custom_field_groupings(advanced_ui=True)

    def get_custom_field_groupings(self, advanced_ui=None):
        """
        Return a dictonary of custom fields grouped by the same grouping in the form
        {
            <grouping_1>: [(cf1, <value for cf1>), (cf2, <value for cf2>), ...],
            ...
            <grouping_5>: [(cf8, <value for cf8>), (cf9, <value for cf9>), ...],
            ...
        }
        """
        # Avoid circular import
        from nautobot.extras.models import CustomField

        record = {}
        fields = CustomField.objects.get_for_model(self)
        if advanced_ui is not None:
            fields = fields.filter(advanced_ui=advanced_ui)

        for field in fields:
            data = (field, self.cf.get(field.name))
            record.setdefault(field.grouping, []).append(data)
        record = dict(sorted(record.items()))
        return record

    def clean(self):
        # Avoid circular import
        from nautobot.extras.models import CustomField
        from nautobot.extras.models.customfields import logger

        super().clean()

        # 2.0 TODO: #824 replace cf.name with cf.slug
        custom_fields = {cf.name: cf for cf in CustomField.objects.get_for_model(self)}

        # Validate all field values
        for field_name, value in self._custom_field_data.items():
            if field_name not in custom_fields:
                # log a warning instead of raising a ValidationError so as not to break the UI
                logger.warning(f"Unknown field name '{field_name}' in custom field data for {self} ({self.pk}).")
                continue
            try:
                custom_fields[field_name].validate(value)
            except ValidationError as e:
                raise ValidationError(f"Invalid value for custom field '{field_name}': {e.message}")

        # Check for missing required values
        for cf in custom_fields.values():
            # 2.0 TODO: #824 replace cf.name with cf.slug
            if cf.required and cf.name not in self._custom_field_data:
                raise ValidationError(f"Missing required custom field '{cf.name}'.")

    # Computed Field Methods
    def has_computed_fields(self, advanced_ui=None):
        """
        Return a boolean indicating whether or not this content type has computed fields associated with it.
        This can also check whether the advanced_ui attribute is True or False for UI display purposes.
        """
        # Avoid circular import
        from nautobot.extras.models import ComputedField

        computed_fields = ComputedField.objects.get_for_model(self)
        if advanced_ui is not None:
            computed_fields = computed_fields.filter(advanced_ui=advanced_ui)
        return computed_fields.exists()

    def has_computed_fields_basic(self):
        return self.has_computed_fields(advanced_ui=False)

    def has_computed_fields_advanced(self):
        return self.has_computed_fields(advanced_ui=True)

    def get_computed_field(self, slug, render=True):
        """
        Get a computed field for this model, lookup via slug.
        Returns the template of this field if render is False, otherwise returns the rendered value.
        """
        # Avoid circular import
        from nautobot.extras.models import ComputedField
        from nautobot.extras.models.customfields import logger

        try:
            computed_field = ComputedField.objects.get_for_model(self).get(slug=slug)
        except ComputedField.DoesNotExist:
            logger.warning("Computed Field with slug %s does not exist for model %s", slug, self._meta.verbose_name)
            return None
        if render:
            return computed_field.render(context={"obj": self})
        return computed_field.template

    def get_computed_fields(self, label_as_key=False, advanced_ui=None):
        """
        Return a dictionary of all computed fields and their rendered values for this model.
        Keys are the `slug` value of each field. If label_as_key is True, `label` values of each field are used as keys.
        """
        # Avoid circular import
        from nautobot.extras.models import ComputedField

        computed_fields_dict = {}
        computed_fields = ComputedField.objects.get_for_model(self)
        if advanced_ui is not None:
            computed_fields = computed_fields.filter(advanced_ui=advanced_ui)
        if not computed_fields:
            return {}
        for cf in computed_fields:
            computed_fields_dict[cf.label if label_as_key else cf.slug] = cf.render(context={"obj": self})
        return computed_fields_dict
