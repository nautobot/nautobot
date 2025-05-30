import json
import re

from django.core import exceptions
from django.core.validators import MaxLengthValidator, RegexValidator
from django.db import models
from django.forms import TextInput
from django.utils.text import slugify
from django_extensions.db.fields import AutoSlugField as _AutoSlugField
from netaddr import AddrFormatError, EUI, mac_unix_expanded
from taggit.managers import TaggableManager

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import fields, widgets
from nautobot.core.forms.utils import compress_range, parse_numeric_range
from nautobot.core.models import ordering
from nautobot.core.models.managers import TagsManager
from nautobot.core.models.validators import EnhancedURLValidator


class mac_unix_expanded_uppercase(mac_unix_expanded):
    word_fmt = "%.2X"


class MACAddressCharField(models.CharField):
    description = "MAC Address Varchar field"

    def __init__(self, *args, **kwargs):
        kwargs["max_length"] = 18
        super().__init__(*args, **kwargs)
        for validator in list(self.validators):
            # CharField will automatically add a MaxLengthValidator, but that doesn't work with EUI objects
            if isinstance(validator, MaxLengthValidator):
                self.validators.remove(validator)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        del kwargs["max_length"]
        return name, path, args, kwargs

    def python_type(self):
        return EUI

    def from_db_value(self, value, expression, connection):
        return self.to_python(value)

    def to_python(self, value):
        if value is None:
            return value
        if isinstance(value, str):
            value = value.strip()
        if value == "":
            return None
        try:
            return EUI(value, version=48, dialect=mac_unix_expanded_uppercase)
        except AddrFormatError:
            raise exceptions.ValidationError(f"Invalid MAC address format: {value}")

    def get_prep_value(self, value):
        if not value:
            return ""
        return str(self.to_python(value))


def slugify_dots_to_dashes(content):
    """Custom slugify_function - convert '.' to '-' instead of removing dots outright."""
    return slugify(content.replace(".", "-"))


def slugify_dashes_to_underscores(content):
    """
    Custom slugify_function - use underscores instead of dashes; resulting slug can be used as a variable name,
    as well as a graphql safe string.
    Note: If content starts with a non graphql-safe character, e.g. a digit
    This method will prepend an "a" to content to make it graphql-safe
    e.g:
        123 main st -> a123_main_st
    """
    graphql_safe_pattern = re.compile("[_A-Za-z]")
    # If the first letter of the slug is not GraphQL safe.
    # We append "a" to it.
    if graphql_safe_pattern.fullmatch(content[0]) is None:
        content = "a" + content
    return slugify(content).replace("-", "_")


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
        kwargs.setdefault("max_length", CHARFIELD_MAX_LENGTH)
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


class ForeignKeyWithAutoRelatedName(models.ForeignKey):
    """
    Extend base ForeignKey functionality to create a smarter default `related_name`.

    For example, "ip_addresses" instead of "ipaddress_set", "ipaddresss", or "ipam_ipaddress_related".

    Primarily useful for cases of abstract base classes that define ForeignKeys, such as
    `nautobot.dcim.models.device_components.ComponentModel`.
    """

    def __init__(self, *args, related_name=None, **kwargs):
        super().__init__(*args, related_name=related_name, **kwargs)
        self._autogenerate_related_name = related_name is None

    def contribute_to_class(self, cls, *args, **kwargs):
        super().contribute_to_class(cls, *args, **kwargs)

        if self._autogenerate_related_name and not cls._meta.abstract and hasattr(cls._meta, "verbose_name_plural"):
            # "IP addresses" -> "ip_addresses"
            related_name = "_".join(re.findall(r"\w+", str(cls._meta.verbose_name_plural))).lower()
            self.remote_field.related_name = related_name


class ForeignKeyLimitedByContentTypes(ForeignKeyWithAutoRelatedName):
    """
    An abstract model field that automatically restricts ForeignKey options based on content_types.

    For instance, if the model "Role" contains two records: role_1 and role_2, role_1's content_types
    are set to "dcim.location" and "dcim.device" while the role_2's content_types are set to
    "circuit.circuit" and "dcim.location."

    Then, for the field `role` on the Device model, role_1 is the only Role that is available,
    while role_1 & role_2 are both available for the Location model.

    The limit_choices_to for the field are automatically derived from:
        - the content-type to which the field is attached (e.g. `dcim.device`)
    """

    def get_limit_choices_to(self):
        """
        Limit this field to only objects which are assigned to this model's content-type.

        Note that this is implemented via specifying `content_types__app_label=` and `content_types__model=`
        rather than via the more obvious `content_types=ContentType.objects.get_for_model(self.model)`
        because the latter approach would involve a database query, and in some cases
        (most notably FilterSet definition) this function is called **before** database migrations can be run.
        """
        return {
            "content_types__app_label": self.model._meta.app_label,
            "content_types__model": self.model._meta.model_name,
        }

    def formfield(self, **kwargs):
        """Return a prepped formfield for use in model forms."""
        defaults = {
            "form_class": fields.DynamicModelChoiceField,
            "queryset": self.related_model.objects.all(),
            # label_lower e.g. "dcim.device"
            "query_params": {"content_types": self.model._meta.label_lower},
        }
        defaults.update(**kwargs)
        return super().formfield(**defaults)


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
        kwargs["widget"] = widgets.ColorSelect
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
            "nautobot.core.models.fields.NaturalOrderingField",
            [self.target_field],
            kwargs,
        )


class JSONArrayField(models.JSONField):
    """
    An ArrayField implementation backed JSON storage.
    Replicates ArrayField's base field validation.

    Supports choices in the base field.
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
            except (TypeError, json.JSONDecodeError) as e:
                raise exceptions.ValidationError(e)
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
        defaults = {
            "form_class": fields.JSONArrayFormField,
            "base_field": self.base_field.formfield(),
        }
        # If the base field has choices, pass them to the form field.
        if self.base_field.choices:
            defaults["choices"] = self.base_field.choices
        defaults.update(**kwargs)
        return super().formfield(**defaults)


class LaxURLField(models.URLField):
    """Like models.URLField, but using validators.EnhancedURLValidator and forms.LaxURLField."""

    default_validators = [EnhancedURLValidator()]

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "form_class": fields.LaxURLField,
                **kwargs,
            },
        )


class TagsField(TaggableManager):
    """Override FormField method on taggit.managers.TaggableManager to match the Nautobot UI."""

    def __init__(self, *args, **kwargs):
        from nautobot.extras.models.tags import TaggedItem

        kwargs.setdefault("through", TaggedItem)
        kwargs.setdefault("manager", TagsManager)
        kwargs.setdefault("ordering", ["name"])
        super().__init__(*args, **kwargs)

    def formfield(self, form_class=fields.DynamicModelMultipleChoiceField, **kwargs):
        from nautobot.extras.models.tags import Tag

        queryset = Tag.objects.get_for_model(self.model)
        kwargs.setdefault("queryset", queryset)
        kwargs.setdefault("required", False)
        kwargs.setdefault("query_params", {"content_types": self.model._meta.label_lower})
        return super().formfield(form_class=form_class, **kwargs)


class PositiveRangeNumberTextField(models.TextField):
    default_error_messages = {
        "invalid": "Invalid value. Specify a value using non-negative integers in a range format (i.e. '10-20').",
    }

    description = "A text based representation of positive number range."

    def __init__(self, min_boundary=0, max_boundary=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_boundary = min_boundary
        self.max_boundary = max_boundary

    def to_python(self, value):
        if value is None:
            return None

        try:
            self.expanded = sorted(parse_numeric_range(value))
        except (ValueError, AttributeError):
            raise exceptions.ValidationError(
                self.error_messages["invalid"],
                code="invalid",
                params={"value": value},
            )

        converted_ranges = compress_range(self.expanded)
        normalized_range = ",".join([f"{x[0]}" if x[0] == x[1] else f"{x[0]}-{x[1]}" for x in converted_ranges])

        return normalized_range

    def validate(self, value, model_instance):
        """
        Validate `value` and raise ValidationError if necessary.
        """
        super().validate(value, model_instance)

        if (self.min_boundary is not None and self.expanded[0] < self.min_boundary) or (
            self.max_boundary is not None and self.expanded[-1] > self.max_boundary
        ):
            raise exceptions.ValidationError(
                message=f"Invalid value. Specify a range value between {self.min_boundary}-{self.max_boundary or 'unlimited'}",
                code="outofrange",
                params={"value": value},
            )

    def formfield(self, **kwargs):
        return super().formfield(
            **{
                "widget": TextInput,
                **kwargs,
            }
        )
