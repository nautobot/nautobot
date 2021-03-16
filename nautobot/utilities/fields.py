import json

from django.core.validators import RegexValidator
from django.db import models
from django.db.models.fields import mixins
from django.core import checks, exceptions

from nautobot.utilities.ordering import naturalize
from .forms import ColorSelect
from .forms.fields import JSONArrayFormField

ColorValidator = RegexValidator(
    regex="^[0-9a-f]{6}$",
    message="Enter a valid hexadecimal RGB color code.",
    code="invalid",
)


class AttributeSetter:
    def __init__(self, name, value):
        setattr(self, name, value)


# Deprecated: Retained only to ensure successful migration from early releases
# Use models.CharField(null=True) instead
class NullableCharField(models.CharField):
    description = "Stores empty values as NULL rather than ''"

    def to_python(self, value):
        if isinstance(value, models.CharField):
            return value
        return value or ""

    def get_prep_value(self, value):
        return value or None


class ColorField(models.CharField):
    default_validators = [ColorValidator]
    description = "A hexadecimal RGB color code"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 6
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs["widget"] = ColorSelect
        return super().formfield(**kwargs)


class NaturalOrderingField(models.CharField):
    """
    A field which stores a naturalized representation of its target field, to be used for ordering its parent model.

    :param target_field: Name of the field of the parent model to be naturalized
    :param naturalize_function: The function used to generate a naturalized value (optional)
    """

    description = "Stores a representation of its target field suitable for natural ordering"

    def __init__(self, target_field, naturalize_function=naturalize, *args, **kwargs):
        self.target_field = target_field
        self.naturalize_function = naturalize_function
        super().__init__(*args, **kwargs)

    def pre_save(self, model_instance, add):
        """
        Generate a naturalized value from the target field
        """
        original_value = getattr(model_instance, self.target_field)
        naturalized_value = self.naturalize_function(original_value, max_length=self.max_length)
        setattr(model_instance, self.attname, naturalized_value)

        return naturalized_value

    def deconstruct(self):
        kwargs = super().deconstruct()[3]  # Pass kwargs from CharField
        kwargs["naturalize_function"] = self.naturalize_function
        return (
            self.name,
            "utilities.fields.NaturalOrderingField",
            [self.target_field],
            kwargs,
        )


class JSONArrayField(models.JSONField):
    """
    An ArrayField implementation backed JSON storage.
    Replicates ArrayField's base field validation.
    """

    _default_hint = ("list", "[]")

    def __init__(self, base_field, **kwargs):
        self.base_field = base_field
        super().__init__(**kwargs)

    def set_attributes_from_name(self, name):
        super().set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    @property
    def description(self):
        return "JSON Array of %s" % self.base_field.description

    def get_prep_value(self, value):
        if value is not None:
            if not isinstance(value, (list, tuple)):
                raise ValueError("value {} is not list or tuple".format(value))
            value = [self.base_field.get_prep_value(v) for v in value]
        return super().get_prep_value(value)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs.update(
            {
                "base_field": self.base_field.clone(),
            }
        )
        return name, path, args, kwargs

    def to_python(self, value):
        if isinstance(value, str):
            # Assume we're deserializing
            vals = json.loads(value)
            value = [self.base_field.to_python(val) for val in vals]
        return value

    def value_to_string(self, obj):
        values = []
        vals = self.value_from_object(obj)
        base_field = self.base_field

        for val in vals:
            if val is None:
                values.append(None)
            else:
                obj = AttributeSetter(base_field.attname, val)
                values.append(base_field.value_to_string(obj))
        return json.dumps(values)

    def validate(self, value, model_instance):
        super().validate(value, model_instance)
        if isinstance(self.base_field, JSONArrayField):
            raise exceptions.ValidationError("cannot nest JSONArrayFields")
        for index, part in enumerate(value):
            try:
                self.base_field.validate(part, model_instance)
            except exceptions.ValidationError as error:
                raise error

    def run_validators(self, value):
        super().run_validators(value)
        for index, part in enumerate(value):
            try:
                self.base_field.run_validators(part)
            except exceptions.ValidationError as error:
                raise error

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": JSONArrayFormField,
                "base_field": self.base_field.formfield(),
                **kwargs,
            }
        )
