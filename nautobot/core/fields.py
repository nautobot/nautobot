import json

from django.core import exceptions
from django.core.validators import RegexValidator
from django.db import models
from django_extensions.db.fields import AutoSlugField as _AutoSlugField

from nautobot.core import forms, ordering


class AutoSlugField(_AutoSlugField):
    """AutoSlugField

    By default, sets editable=True, blank=True, max_length=100, overwrite_on_add=False, unique=True
    Required arguments:
    populate_from
        Specifies which field, list of fields, or model method
        the slug will be populated from.

        populate_from can traverse a ForeignKey relationship
        by using Django ORM syntax:
            populate_from = 'related_model__field'

    Optional arguments:

    separator
        Defines the used separator (default: '-')

    overwrite
        If set to True, overwrites the slug on every save (default: False)

    overwrite_on_add
        If set to True, overwrites the provided slug on initial creation (default: False)

    slugify_function
        Defines the function which will be used to "slugify" a content
        (default: :py:func:`~django.template.defaultfilters.slugify` )

    It is possible to provide custom "slugify" function with
    the ``slugify_function`` function in a model class.

    ``slugify_function`` function in a model class takes priority over
    ``slugify_function`` given as an argument to :py:class:`~AutoSlugField`.

    Example

    .. code-block:: python
        # models.py

        from django.db import models
        from django_extensions.db.fields import AutoSlugField

        class MyModel(models.Model):
            def slugify_function(self, content):
                return content.replace('_', '-').lower()

            title = models.CharField(max_length=42)
            slug = AutoSlugField(populate_from='title')

    Taken from django_extensions AutoSlugField Documentation.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 100)
        kwargs.setdefault("editable", True)
        kwargs.setdefault("overwrite_on_add", False)
        kwargs.setdefault("unique", True)
        super().__init__(*args, **kwargs)

    def get_slug_fields(self, model_instance, lookup_value):
        """Workaround for https://github.com/django-extensions/django-extensions/issues/1713."""
        try:
            return super().get_slug_fields(model_instance, lookup_value)
        except AttributeError:
            return ""


ColorValidator = RegexValidator(
    regex="^[0-9a-f]{6}$",
    message="Enter a valid hexadecimal RGB color code.",
    code="invalid",
)


class AttributeSetter:
    def __init__(self, name, value):
        setattr(self, name, value)


class ColorField(models.CharField):
    default_validators = [ColorValidator]
    description = "A hexadecimal RGB color code"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 6
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        kwargs["widget"] = forms.ColorSelect
        return super().formfield(**kwargs)


class NaturalOrderingField(models.CharField):
    """
    A field which stores a naturalized representation of its target field, to be used for ordering its parent model.

    :param target_field: Name of the field of the parent model to be naturalized
    :param naturalize_function: The function used to generate a naturalized value (optional)
    """

    description = "Stores a representation of its target field suitable for natural ordering"

    def __init__(self, target_field, naturalize_function=ordering.naturalize, *args, **kwargs):
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
            "nautobot.core.fields.NaturalOrderingField",
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
        if isinstance(base_field, JSONArrayField):
            raise TypeError("cannot nest JSONArrayFields")
        self.base_field = base_field
        super().__init__(**kwargs)

    def set_attributes_from_name(self, name):
        super().set_attributes_from_name(name)
        self.base_field.set_attributes_from_name(name)

    @property
    def description(self):
        return f"JSON Array of {self.base_field.description}"

    def get_prep_value(self, value):
        """Perform preliminary non-db specific value checks and conversions."""
        if value is not None:
            if not isinstance(value, (list, tuple)):
                raise ValueError(f"value {value} is not list or tuple")
            value = [self.base_field.get_prep_value(v) for v in value]
        return super().get_prep_value(value)

    def deconstruct(self):
        """
        Return enough information to recreate the field as a 4-tuple:
         * The name of the field on the model, if contribute_to_class() has
           been run.
         * The import path of the field, including the class:e.g.
           django.db.models.IntegerField This should be the most portable
           version, so less specific may be better.
         * A list of positional arguments.
         * A dict of keyword arguments.
        """
        name, path, args, kwargs = super().deconstruct()
        kwargs.update(
            {
                "base_field": self.base_field.clone(),
            }
        )
        return name, path, args, kwargs

    def to_python(self, value):
        """
        Convert `value` into JSON, raising django.core.exceptions.ValidationError
        if the data can't be converted. Return the converted value.
        """
        if isinstance(value, str):
            try:
                # Assume we're deserializing
                vals = json.loads(value)
                value = [self.base_field.to_python(val) for val in vals]
            except json.JSONDecodeError as e:
                raise exceptions.ValidationError(e) from e
        return value

    def value_to_string(self, obj):
        """
        Return a string value of this field from the passed obj.
        This is used by the serialization framework.
        """
        values = []
        vals = self.value_from_object(obj)
        base_field = self.base_field

        for val in vals:
            if val is None:
                values.append(None)
            else:
                obj = AttributeSetter(base_field.attname, val)
                values.append(base_field.value_to_string(obj))
        return json.dumps(values, ensure_ascii=False)

    def validate(self, value, model_instance):
        """
        Validate `value` and raise ValidationError if necessary.
        """
        super().validate(value, model_instance)
        for part in value:
            self.base_field.validate(part, model_instance)

    def run_validators(self, value):
        """
        Runs all validators against `value` and raise ValidationError if necessary.
        Some validators can't be created at field initialization time.
        """
        super().run_validators(value)
        for part in value:
            self.base_field.run_validators(part)

    def formfield(self, **kwargs):
        """Return a django.forms.Field instance for this field."""
        return super().formfield(
            **{
                "form_class": forms.JSONArrayFormField,
                "base_field": self.base_field.formfield(),
                **kwargs,
            }
        )
