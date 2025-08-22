from collections import defaultdict, OrderedDict
from datetime import date, datetime
import json
import logging
import re

from django import forms
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import RegexValidator, ValidationError
from django.db import models, transaction
from django.forms.widgets import TextInput
from django.utils.html import format_html
from jinja2 import TemplateError, TemplateSyntaxError

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    add_blank_choice,
    CommentField,
    CSVChoiceField,
    CSVMultipleChoiceField,
    DatePicker,
    JSONField,
    LaxURLField,
    MultiValueCharInput,
    NullableDateField,
    SmallTextarea,
    StaticSelect2,
    StaticSelect2Multiple,
)
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.fields import AutoSlugField, slugify_dashes_to_underscores
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.models.validators import validate_regex
from nautobot.core.settings_funcs import is_truthy
from nautobot.core.templatetags.helpers import render_markdown
from nautobot.core.utils.data import render_jinja2, validate_jinja2
from nautobot.extras.choices import CustomFieldFilterLogicChoices, CustomFieldTypeChoices
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.models.mixins import ContactMixin, DynamicGroupsModelMixin, NotesMixin, SavedViewMixin
from nautobot.extras.tasks import delete_custom_field_data, update_custom_field_choice_data
from nautobot.extras.utils import check_if_key_is_graphql_safe, extras_features, FeatureQuery

logger = logging.getLogger(__name__)


class ComputedFieldManager(BaseManager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def get_for_model(self, model, get_queryset=True):
        """
        Return all ComputedFields assigned to the given model.

        Returns a queryset by default, or a list if `get_queryset` param is False.
        """
        concrete_model = model._meta.concrete_model
        cache_key = f"{self.get_for_model.cache_key_prefix}.{concrete_model._meta.label_lower}"
        list_cache_key = f"{cache_key}.list"
        if not get_queryset:
            listing = cache.get(list_cache_key)
            if listing is not None:
                return listing
        queryset = cache.get(cache_key)
        if queryset is None:
            content_type = ContentType.objects.get_for_model(concrete_model)
            queryset = self.get_queryset().filter(content_type=content_type)
            cache.set(cache_key, queryset)
        if not get_queryset:
            listing = list(queryset)
            cache.set(list_cache_key, listing)
            return listing
        return queryset

    get_for_model.cache_key_prefix = "nautobot.extras.computedfield.get_for_model"

    def populate_list_caches(self):
        """Populate all caches for `get_for_model(..., get_queryset=False)` lookups."""
        queryset = self.all().select_related("content_type")
        listings = defaultdict(list)
        for cf in queryset:
            listings[f"{cf.content_type.app_label}.{cf.content_type.model}"].append(cf)
        for ct in ContentType.objects.all():
            label = f"{ct.app_label}.{ct.model}"
            cache.set(f"{self.get_for_model.cache_key_prefix}.{label}.list", listings[label])

    def bulk_create(self, objs, *args, **kwargs):
        """Validate templates before saving."""
        self._validate_templates_bulk(objs)
        return super().bulk_create(objs, *args, **kwargs)

    def bulk_update(self, objs, fields, *args, **kwargs):
        """Validate templates before updating if template field is being modified."""
        if "template" in fields:
            self._validate_templates_bulk(objs)

        return super().bulk_update(objs, fields, *args, **kwargs)

    def _validate_templates_bulk(self, objs):
        """Helper method to validate templates for multiple objects."""
        errors = []
        for obj in objs:
            try:
                obj.validate_template()
            except ValidationError as exc:
                message_list = [f"'{obj.label}': {x}" for x in exc.messages]
                errors.extend(message_list)

        if errors:
            raise ValidationError(f"Template validation failed - {'; '.join(errors)}")


@extras_features("graphql")
class ComputedField(
    ContactMixin,
    ChangeLoggedModel,
    DynamicGroupsModelMixin,
    NotesMixin,
    SavedViewMixin,
    BaseModel,
):
    """
    Read-only rendered fields driven by a Jinja2 template that are applied to objects within a ContentType.
    """

    content_type = models.ForeignKey(
        to=ContentType,
        on_delete=models.CASCADE,
        limit_choices_to=FeatureQuery("custom_fields"),
        related_name="computed_fields",
    )
    key = AutoSlugField(
        populate_from="label",
        help_text="Internal field name. Please use underscores rather than dashes in this key.",
        slugify_function=slugify_dashes_to_underscores,
    )
    grouping = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="Human-readable grouping that this computed field belongs to.",
    )
    label = models.CharField(max_length=CHARFIELD_MAX_LENGTH, help_text="Name of the field as displayed to users")
    description = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True)
    template = models.TextField(max_length=500, help_text="Jinja2 template code for field value")
    fallback_value = models.CharField(
        max_length=500,
        blank=True,
        help_text="Fallback value (if any) to be output for the field in the case of a template rendering error.",
    )
    weight = models.PositiveSmallIntegerField(default=100)
    advanced_ui = models.BooleanField(
        default=False,
        verbose_name="Move to Advanced tab",
        help_text="Hide this field from the object's primary information tab. "
        'It will appear in the "Advanced" tab instead.',
    )

    objects = ComputedFieldManager()

    clone_fields = ["content_type", "description", "template", "fallback_value", "weight"]
    natural_key_field_names = ["key"]

    class Meta:
        ordering = ["weight", "key"]
        unique_together = ("content_type", "label")

    def __str__(self):
        return self.label

    def render(self, context):
        try:
            return render_jinja2(self.template, context)
        except Exception as exc:
            logger.warning("Failed to render computed field %s: %s", self.key, exc)
            return self.fallback_value

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        self.validate_template()

        if self.key != "":
            check_if_key_is_graphql_safe(self.__class__.__name__, self.key)

    def validate_template(self):
        """
        Validate that the template contains valid Jinja2 syntax.
        """
        try:
            validate_jinja2(self.template)
        except TemplateSyntaxError as exc:
            raise ValidationError({"template": f"Template syntax error on line {exc.lineno}: {exc.message}"})
        except TemplateError as exc:
            raise ValidationError({"template": f"Template error: {exc}"})
        except Exception as exc:
            # System-level exceptions (very rare) - memory, recursion, encoding issues
            raise ValidationError(f"Template validation failed: {exc}")


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
        fields = CustomField.objects.get_for_model(self)
        if advanced_ui is not None:
            fields = fields.filter(advanced_ui=advanced_ui)
        return OrderedDict([(field, self.cf.get(field.key)) for field in fields])

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
        record = {}
        fields = CustomField.objects.get_for_model(self)
        if advanced_ui is not None:
            fields = fields.filter(advanced_ui=advanced_ui)

        for field in fields:
            data = (field, self.cf.get(field.key))
            record.setdefault(field.grouping, []).append(data)
        record = dict(sorted(record.items()))
        return record

    def clean(self):
        super().clean()

        custom_fields = {cf.key: cf for cf in CustomField.objects.get_for_model(self)}

        # Validate all field values
        for field_key, value in self._custom_field_data.items():
            if field_key not in custom_fields:
                # log a warning instead of raising a ValidationError so as not to break the UI
                logger.warning(f"Unknown field key '{field_key}' in custom field data for {self} ({self.pk}).")
                continue
            try:
                self._custom_field_data[field_key] = custom_fields[field_key].validate(value)
            except ValidationError as e:
                raise ValidationError(f"Invalid value for custom field '{field_key}': {e.message}")

        # Check for missing values, erroring on required ones and populating non-required ones automatically
        for cf in custom_fields.values():
            if cf.key not in self._custom_field_data:
                if cf.default is not None:
                    self._custom_field_data[cf.key] = cf.default
                elif cf.required:
                    raise ValidationError(f"Missing required custom field '{cf.key}'.")

    clean.alters_data = True

    # Computed Field Methods
    def has_computed_fields(self, advanced_ui=None):
        """
        Return a boolean indicating whether or not this content type has computed fields associated with it.
        This can also check whether the advanced_ui attribute is True or False for UI display purposes.
        """
        computed_fields = ComputedField.objects.get_for_model(self)
        if advanced_ui is not None:
            computed_fields = computed_fields.filter(advanced_ui=advanced_ui)
        return computed_fields.exists()

    def has_computed_fields_basic(self):
        return self.has_computed_fields(advanced_ui=False)

    def has_computed_fields_advanced(self):
        return self.has_computed_fields(advanced_ui=True)

    def get_computed_field(self, key, render=True):
        """
        Get a computed field for this model, lookup via key.
        Returns the template of this field if render is False, otherwise returns the rendered value.
        """
        try:
            computed_field = ComputedField.objects.get_for_model(self).get(key=key)
        except ComputedField.DoesNotExist:
            logger.warning("Computed Field with key %s does not exist for model %s", key, self._meta.verbose_name)
            return None
        if render:
            return computed_field.render(context={"obj": self})
        return computed_field.template

    def get_computed_fields_grouping_basic(self):
        """
        This method exists to help call get_computed_field_groupings() in templates where a function argument (advanced_ui) cannot be specified.
        Return a dictonary of computed fields grouped by the same grouping in the form
        {
            <grouping_1>: [(cf1, <value for cf1>), (cf2, <value for cf2>), ...],
            ...
            <grouping_5>: [(cf8, <value for cf8>), (cf9, <value for cf9>), ...],
            ...
        }
        which have advanced_ui set to False
        """
        return self.get_computed_fields_grouping(advanced_ui=False)

    def get_computed_fields_grouping_advanced(self):
        """
        This method exists to help call get_computed_field_groupings() in templates where a function argument (advanced_ui) cannot be specified.
        Return a dictonary of computed fields grouped by the same grouping in the form
        {
            <grouping_1>: [(cf1, <value for cf1>), (cf2, <value for cf2>), ...],
            ...
            <grouping_5>: [(cf8, <value for cf8>), (cf9, <value for cf9>), ...],
            ...
        }
        which have advanced_ui set to True
        """
        return self.get_computed_fields_grouping(advanced_ui=True)

    def get_computed_fields_grouping(self, advanced_ui=None):
        """
        Return a dictonary of computed fields grouped by the same grouping in the form
        {
            <grouping_1>: [(cf1, <value for cf1>), (cf2, <value for cf2>), ...],
            ...
            <grouping_5>: [(cf8, <value for cf8>), (cf9, <value for cf9>), ...],
            ...
        }
        """
        record = {}
        computed_fields = ComputedField.objects.get_for_model(self)
        if advanced_ui is not None:
            computed_fields = computed_fields.filter(advanced_ui=advanced_ui)

        for field in computed_fields:
            data = (field, field.render(context={"obj": self}))
            record.setdefault(field.grouping, []).append(data)
        record = dict(sorted(record.items()))
        return record

    def get_computed_fields(self, label_as_key=False, advanced_ui=None):
        """
        Return a dictionary of all computed fields and their rendered values for this model.
        Keys are the `key` value of each field. If label_as_key is True, `label` values of each field are used as keys.
        """
        computed_fields_dict = {}
        computed_fields = ComputedField.objects.get_for_model(self)
        if advanced_ui is not None:
            computed_fields = computed_fields.filter(advanced_ui=advanced_ui)
        if not computed_fields:
            return {}
        for cf in computed_fields:
            computed_fields_dict[cf.label if label_as_key else cf.key] = cf.render(context={"obj": self})
        return computed_fields_dict


class CustomFieldManager(BaseManager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def get_for_model(self, model, exclude_filter_disabled=False, get_queryset=True):
        """
        Return (and cache) all CustomFields assigned to the given model.

        Args:
            model (Model): The django model to which custom fields are registered
            exclude_filter_disabled (bool): Exclude any custom fields which have filter logic disabled
            get_queryset (bool): Whether to return a QuerySet or a list.
        """
        concrete_model = model._meta.concrete_model
        cache_key = (
            f"{self.get_for_model.cache_key_prefix}.{concrete_model._meta.label_lower}.{exclude_filter_disabled}"
        )
        list_cache_key = f"{cache_key}.list"
        if not get_queryset:
            listing = cache.get(list_cache_key)
            if listing is not None:
                return listing
        queryset = cache.get(cache_key)
        if queryset is None:
            content_type = ContentType.objects.get_for_model(concrete_model)
            queryset = self.get_queryset().filter(content_types=content_type)
            if exclude_filter_disabled:
                queryset = queryset.exclude(filter_logic=CustomFieldFilterLogicChoices.FILTER_DISABLED)
            cache.set(cache_key, queryset)
        if not get_queryset:
            listing = list(queryset)
            cache.set(list_cache_key, listing)
            return listing
        return queryset

    get_for_model.cache_key_prefix = "nautobot.extras.customfield.get_for_model"

    def keys_for_model(self, model):
        """Return list of all keys for CustomFields assigned to the given model."""
        concrete_model = model._meta.concrete_model
        cache_key = f"{self.keys_for_model.cache_key_prefix}.{concrete_model._meta.label_lower}"
        keys = cache.get(cache_key)
        if keys is None:
            keys = list(self.get_for_model(model).values_list("key", flat=True))
            cache.set(cache_key, keys)
        return keys

    keys_for_model.cache_key_prefix = "nautobot.extras.customfield.keys_for_model"

    def populate_list_caches(self):
        """Populate all caches for `get_for_model(..., get_queryset=False)` and `keys_for_model` lookups."""
        queryset = self.all().prefetch_related("content_types")
        cf_listings = defaultdict(lambda: defaultdict(list))
        key_listings = defaultdict(list)
        for cf in queryset:
            for ct in cf.content_types.all():
                label = f"{ct.app_label}.{ct.model}"
                cf_listings[label][False].append(cf)
                if cf.filter_logic != CustomFieldFilterLogicChoices.FILTER_DISABLED:
                    cf_listings[label][True].append(cf)
                key_listings[label].append(cf.key)
        for ct in ContentType.objects.all():
            label = f"{ct.app_label}.{ct.model}"
            cache.set(f"{self.get_for_model.cache_key_prefix}.{label}.True.list", cf_listings[label][True])
            cache.set(f"{self.get_for_model.cache_key_prefix}.{label}.False.list", cf_listings[label][False])
            cache.set(f"{self.keys_for_model.cache_key_prefix}.{label}", key_listings[label])


@extras_features("webhooks")
class CustomField(
    ContactMixin,
    ChangeLoggedModel,
    DynamicGroupsModelMixin,
    NotesMixin,
    SavedViewMixin,
    BaseModel,
):
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="custom_fields",
        verbose_name="Object(s)",
        limit_choices_to=FeatureQuery("custom_fields"),
        help_text="The object(s) to which this field applies.",
    )
    grouping = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        help_text="Human-readable grouping that this custom field belongs to.",
    )
    type = models.CharField(
        max_length=50,
        choices=CustomFieldTypeChoices,
        default=CustomFieldTypeChoices.TYPE_TEXT,
        help_text="The type of value(s) allowed for this field.",
    )
    label = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        help_text="Name of the field as displayed to users.",
        blank=False,
    )
    key = AutoSlugField(
        blank=True,
        max_length=CHARFIELD_MAX_LENGTH,
        separator="_",
        populate_from="label",
        help_text="Internal field name. Please use underscores rather than dashes in this key.",
        slugify_function=slugify_dashes_to_underscores,
    )
    description = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH, blank=True, help_text="A helpful description for this field."
    )
    required = models.BooleanField(
        default=False,
        help_text="If true, this field is required when creating new objects or editing an existing object.",
    )
    # todoindex:
    filter_logic = models.CharField(
        max_length=50,
        choices=CustomFieldFilterLogicChoices,
        default=CustomFieldFilterLogicChoices.FILTER_LOOSE,
        help_text="Loose matches any instance of a given string; Exact matches the entire field.",
    )
    default = models.JSONField(
        encoder=DjangoJSONEncoder,
        blank=True,
        null=True,
        help_text=(
            'Default value for the field (must be a JSON value). Encapsulate strings with double quotes (e.g. "Foo").'
        ),
    )
    weight = models.PositiveSmallIntegerField(
        default=100, help_text="Fields with higher weights appear lower in a form."
    )
    validation_minimum = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Minimum value",
        help_text="Minimum allowed value (for numeric fields) or length (for text fields).",
    )
    validation_maximum = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Maximum value",
        help_text="Maximum allowed value (for numeric fields) or length (for text fields).",
    )
    validation_regex = models.CharField(
        blank=True,
        validators=[validate_regex],
        max_length=500,
        verbose_name="Validation regex",
        help_text="Regular expression to enforce on text field values. Use ^ and $ to force matching of entire string. "
        "For example, <code>^[A-Z]{3}$</code> will limit values to exactly three uppercase letters. Regular "
        "expression on select and multi-select will be applied at <code>Custom Field Choices</code> definition.",
    )
    advanced_ui = models.BooleanField(
        default=False,
        verbose_name="Move to Advanced tab",
        help_text="Hide this field from the object's primary information tab. "
        'It will appear in the "Advanced" tab instead.',
    )

    objects = CustomFieldManager()

    clone_fields = [
        "content_types",
        "grouping",
        "type",
        "description",
        "required",
        "filter_logic",
        "default",
        "weight",
        "validation_minimum",
        "validation_maximum",
        "validation_regex",
    ]
    natural_key_field_names = ["key"]

    class Meta:
        ordering = ["weight", "label"]

    def __str__(self):
        return self.label

    @property
    def choices_cache_key(self):
        return f"nautobot.extras.customfield.choices.{self.pk}"

    @property
    def choices(self) -> list[str]:
        """
        Cacheable shorthand for retrieving custom_field_choices values associated with this model.

        Returns:
            list[str]: List of choice values, ordered by weight.
        """
        if self.type not in [CustomFieldTypeChoices.TYPE_SELECT, CustomFieldTypeChoices.TYPE_MULTISELECT]:
            return []
        choices = cache.get(self.choices_cache_key)
        if choices is None:
            choices = list(self.custom_field_choices.order_by("weight", "value").values_list("value", flat=True))
            cache.set(self.choices_cache_key, choices)
        return choices

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if self.key != "":
            check_if_key_is_graphql_safe(self.__class__.__name__, self.key)

        if self.present_in_database:
            # Check immutable fields
            database_object = self.__class__.objects.get(pk=self.pk)

            if self.key != database_object.key:
                raise ValidationError({"key": "Key cannot be changed once created"})

            if self.type != database_object.type:
                raise ValidationError({"type": "Type cannot be changed once created"})

        # Validate the field's default value (if any)
        if self.default is not None:
            try:
                self.default = self.validate(self.default)
            except ValidationError as err:
                raise ValidationError({"default": f'Invalid default value "{self.default}": {err.message}'})

        # Minimum/maximum values can be set only for fields that support them
        if self.validation_minimum is not None and self.type not in CustomFieldTypeChoices.MIN_MAX_TYPES:
            raise ValidationError({"validation_minimum": "A minimum value may not be set for fields of this type"})
        if self.validation_maximum is not None and self.type not in CustomFieldTypeChoices.MIN_MAX_TYPES:
            raise ValidationError({"validation_maximum": "A maximum value may not be set for fields of this type"})

        # Regex validation can be set only for text, url, select and multi-select fields
        if self.validation_regex and self.type not in CustomFieldTypeChoices.REGEX_TYPES:
            raise ValidationError(
                {"validation_regex": "Regular expression validation is not supported for fields of this type"}
            )

        # Choices can be set only on selection fields
        if self.custom_field_choices.exists() and self.type not in (
            CustomFieldTypeChoices.TYPE_SELECT,
            CustomFieldTypeChoices.TYPE_MULTISELECT,
        ):
            raise ValidationError("Choices may be set only for custom selection fields.")

        # A selection field's default (if any) must be present in its available choices
        if (
            self.type == CustomFieldTypeChoices.TYPE_SELECT
            and self.default
            and self.default not in self.custom_field_choices.values_list("value", flat=True)
        ):
            raise ValidationError(
                {"default": f"The specified default value ({self.default}) is not listed as an available choice."}
            )

    def to_form_field(
        self,
        set_initial=True,
        enforce_required=True,
        for_csv_import=False,
        simple_json_filter=False,
        label=None,
        for_filter_form=False,
    ):
        """
        Return a form field suitable for setting a CustomField's value for an object.

        Args:
            set_initial: Set initial date for the field. This should be False when generating a field for bulk editing.
            enforce_required: Honor the value of CustomField.required. Set to False for filtering/bulk editing.
            for_csv_import: Return a form field suitable for bulk import of objects. Despite the parameter name,
                this is *not* used for CSV imports since 2.0, but it *is* used for JSON/YAML import of DeviceTypes.
            simple_json_filter: Return a TextInput widget for JSON filtering instead of the default TextArea widget.
            label: Set the input label manually (if required); otherwise, defaults to field's __str__() implementation.
            for_filter_form: If True return the relevant form field for filter form
        """
        initial = self.default if set_initial else None
        required = self.required if enforce_required else False

        # Integer
        if self.type == CustomFieldTypeChoices.TYPE_INTEGER:
            field = forms.IntegerField(
                required=required,
                initial=initial,
                min_value=self.validation_minimum,
                max_value=self.validation_maximum,
            )

        # Boolean
        elif self.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
            choices = (
                (None, "---------"),
                (True, "True"),
                (False, "False"),
            )
            field = forms.NullBooleanField(
                required=required,
                initial=initial,
                widget=StaticSelect2(choices=choices),
            )

        # Date
        elif self.type == CustomFieldTypeChoices.TYPE_DATE:
            field = NullableDateField(
                required=required,
                initial=initial,
                widget=DatePicker(),
            )

        # Text-like fields
        elif self.type in (
            CustomFieldTypeChoices.TYPE_URL,
            CustomFieldTypeChoices.TYPE_TEXT,
            CustomFieldTypeChoices.TYPE_MARKDOWN,
        ):
            if self.type == CustomFieldTypeChoices.TYPE_URL:
                field = LaxURLField(
                    required=required,
                    initial=initial,
                    min_length=self.validation_minimum,
                    max_length=self.validation_maximum,
                )
            elif self.type == CustomFieldTypeChoices.TYPE_TEXT:
                field = forms.CharField(
                    required=required,
                    initial=initial,
                    min_length=self.validation_minimum,
                    max_length=self.validation_maximum,
                )
            elif self.type == CustomFieldTypeChoices.TYPE_MARKDOWN:
                field = CommentField(
                    required=required,
                    initial=initial,
                    widget=SmallTextarea,
                    label=None,
                    min_length=self.validation_minimum,
                    max_length=self.validation_maximum,
                )
            if self.validation_regex:
                field.validators = [
                    RegexValidator(
                        regex=self.validation_regex,
                        message=format_html("Values must match this regex: <code>{}</code>", self.validation_regex),
                    )
                ]

        # JSON
        elif self.type == CustomFieldTypeChoices.TYPE_JSON:
            # Unlike the above cases, we don't apply min_length/max_length to the field,
            # nor do we add a RegexValidator to the field, as these all apply after parsing and validating the JSON
            if simple_json_filter:
                field = JSONField(encoder=DjangoJSONEncoder, required=required, initial=None, widget=TextInput)
            else:
                field = JSONField(encoder=DjangoJSONEncoder, required=required, initial=initial)

        # Select or Multi-select
        else:
            choices = [(value, value) for value in self.choices]

            # Set the initial value to the first available choice (if any)
            if self.type == CustomFieldTypeChoices.TYPE_SELECT and not for_filter_form:
                if not required or self.default not in self.choices:
                    choices = add_blank_choice(choices)
                field_class = CSVChoiceField if for_csv_import else forms.ChoiceField
                field = field_class(
                    choices=choices,
                    required=required,
                    initial=initial,
                    widget=StaticSelect2(),
                )
            else:
                field_class = CSVMultipleChoiceField if for_csv_import else forms.MultipleChoiceField
                field = field_class(choices=choices, required=required, initial=initial, widget=StaticSelect2Multiple())

        field.model = self
        if label is not None:
            field.label = label
        else:
            field.label = str(self)

        if self.description:
            # Avoid script injection and similar attacks! Output HTML but only accept Markdown as input
            field.help_text = render_markdown(self.description)

        return field

    def to_filter_form_field(self, lookup_expr="exact", *args, **kwargs):
        """Return a filter form field suitable for filtering a CustomField's value for an object."""
        form_field = self.to_form_field(*args, **kwargs, for_filter_form=True)
        # We would handle type selection differently because: If lookup_type is not the same as exact, use MultiValueCharInput
        if self.type == CustomFieldTypeChoices.TYPE_SELECT:
            if lookup_expr not in ["exact", "contains"]:
                form_field.widget = MultiValueCharInput()
        return form_field

    def validate(self, value):
        """
        Validate a value according to the field's type validation rules.

        Returns the value, possibly cleaned up
        """
        if value not in [None, "", []]:
            # Validate text field
            if self.type in (
                CustomFieldTypeChoices.TYPE_TEXT,
                CustomFieldTypeChoices.TYPE_URL,
                CustomFieldTypeChoices.TYPE_MARKDOWN,
            ):
                if not isinstance(value, str):
                    raise ValidationError("Value must be a string")
                if self.validation_minimum is not None and len(value) < self.validation_minimum:
                    raise ValidationError(f"Value must be at least {self.validation_minimum} characters in length")
                if self.validation_maximum is not None and len(value) > self.validation_maximum:
                    raise ValidationError(f"Value must not exceed {self.validation_maximum} characters in length")
                if self.validation_regex and not re.search(self.validation_regex, value):
                    raise ValidationError(f"Value must match regex '{self.validation_regex}'")

            # Validate JSON
            elif self.type == CustomFieldTypeChoices.TYPE_JSON:
                if self.validation_regex or self.validation_minimum is not None or self.validation_maximum is not None:
                    json_value = json.dumps(value)
                    if self.validation_minimum is not None and len(json_value) < self.validation_minimum:
                        raise ValidationError(f"Value must be at least {self.validation_minimum} characters in length")
                    if self.validation_maximum is not None and len(json_value) > self.validation_maximum:
                        raise ValidationError(f"Value must not exceed {self.validation_maximum} characters in length")
                    if self.validation_regex and not re.search(self.validation_regex, json_value):
                        raise ValidationError(f"Value must match regex '{self.validation_regex}'")

            # Validate integer
            elif self.type == CustomFieldTypeChoices.TYPE_INTEGER:
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError("Value must be an integer.")
                if self.validation_minimum is not None and value < self.validation_minimum:
                    raise ValidationError(f"Value must be at least {self.validation_minimum}")
                if self.validation_maximum is not None and value > self.validation_maximum:
                    raise ValidationError(f"Value must not exceed {self.validation_maximum}")

            # Validate boolean
            elif self.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
                try:
                    value = is_truthy(value)
                except ValueError as exc:
                    raise ValidationError("Value must be true or false.") from exc

            # Validate date
            elif self.type == CustomFieldTypeChoices.TYPE_DATE:
                if not isinstance(value, date):
                    try:
                        datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        raise ValidationError("Date values must be in the format YYYY-MM-DD.")

            # Validate selected choice
            elif self.type == CustomFieldTypeChoices.TYPE_SELECT:
                if value not in self.choices:
                    raise ValidationError(f"Invalid choice ({value}). Available choices are: {', '.join(self.choices)}")

            elif self.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
                if isinstance(value, str):
                    value = value.split(",")
                if not set(value).issubset(self.choices):
                    raise ValidationError(
                        f"Invalid choice(s) ({value}). Available choices are: {', '.join(self.choices)}"
                    )

        elif self.required:
            raise ValidationError("Required field cannot be empty.")

        return value

    def delete(self, *args, **kwargs):
        """
        Handle the cleanup of old custom field data when a CustomField is deleted.
        """
        content_types = set(self.content_types.values_list("pk", flat=True))

        super().delete(*args, **kwargs)

        if content_types:
            # Circular Import
            from nautobot.extras.signals import change_context_state

            change_context = change_context_state.get()
            if change_context is None:
                context = None
            else:
                context = change_context.as_dict(instance=self)
                context["context_detail"] = "delete custom field data"
            delete_custom_field_data.delay(self.key, content_types, context)

    def add_prefix_to_cf_key(self):
        return "cf_" + str(self.key)


@extras_features(
    "graphql",
    "webhooks",
)
class CustomFieldChoice(BaseModel, ChangeLoggedModel):
    """
    The custom field choice is used to store the possible set of values for a selection type custom field
    """

    custom_field = models.ForeignKey(
        to="extras.CustomField",
        on_delete=models.CASCADE,
        related_name="custom_field_choices",
        limit_choices_to=models.Q(
            type__in=[CustomFieldTypeChoices.TYPE_SELECT, CustomFieldTypeChoices.TYPE_MULTISELECT]
        ),
    )
    value = models.CharField(max_length=CHARFIELD_MAX_LENGTH)
    weight = models.PositiveSmallIntegerField(default=100, help_text="Higher weights appear later in the list")

    documentation_static_path = "docs/user-guide/platform-functionality/customfield.html"
    is_metadata_associable_model = False

    class Meta:
        ordering = ["custom_field", "weight", "value"]
        unique_together = ["custom_field", "value"]

    def __str__(self):
        return self.value

    def clean(self):
        if self.custom_field.type not in (CustomFieldTypeChoices.TYPE_SELECT, CustomFieldTypeChoices.TYPE_MULTISELECT):
            raise ValidationError("Custom field choices can only be assigned to selection fields.")

        if self.custom_field.validation_minimum is not None and len(self.value) < self.custom_field.validation_minimum:
            raise ValidationError(f"Value must be at least {self.custom_field.validation_minimum} characters long.")
        if self.custom_field.validation_maximum is not None and len(self.value) > self.custom_field.validation_maximum:
            raise ValidationError(f"Value must not exceed {self.custom_field.validation_maximum} characters long.")

        if not re.search(self.custom_field.validation_regex, self.value):
            raise ValidationError(f"Value must match regex {self.custom_field.validation_regex} got {self.value}.")

    def save(self, *args, **kwargs):
        """
        When a custom field choice is saved, perform logic that will update data across all custom field data.
        """
        if self.present_in_database:
            database_object = self.__class__.objects.get(pk=self.pk)
        else:
            database_object = self

        super().save(*args, **kwargs)

        if self.value != database_object.value:
            # Circular Import
            from nautobot.extras.signals import change_context_state

            change_context = change_context_state.get()
            if change_context is None:
                context = None
            else:
                context = change_context.as_dict(instance=self)
                context["context_detail"] = "update custom field choice data"
            transaction.on_commit(
                lambda: update_custom_field_choice_data.delay(
                    self.custom_field.pk,
                    database_object.value,
                    self.value,
                    context,
                )
            )

    def delete(self, *args, **kwargs):
        """
        When a custom field choice is deleted, remove references to in custom field data
        """
        if self.custom_field.default:
            # Cannot delete the choice if it is the default value.
            if self.custom_field.type == CustomFieldTypeChoices.TYPE_SELECT and self.custom_field.default == self.value:
                raise models.ProtectedError(
                    msg="Cannot delete this choice because it is the default value for the field.",
                    protected_objects=[self],  # TODO: should this be self.field instead?
                )
            elif self.value in self.custom_field.default:
                raise models.ProtectedError(
                    msg="Cannot delete this choice because it is one of the default values for the field.",
                    protected_objects=[self],  # TODO: should this be self.field instead?
                )

        if self.custom_field.type == CustomFieldTypeChoices.TYPE_SELECT:
            # Check if this value is in active use in a select field
            for ct in self.custom_field.content_types.all():
                model = ct.model_class()
                if model.objects.filter(**{f"_custom_field_data__{self.custom_field.key}": self.value}).exists():
                    raise models.ProtectedError(
                        msg="Cannot delete this choice because it is in active use.",
                        protected_objects=[self],  # TODO should this be model.objects.filter(...) instead?
                    )

        else:
            # Check if this value is in active use in a multi-select field
            for ct in self.custom_field.content_types.all():
                model = ct.model_class()
                if model.objects.filter(
                    **{f"_custom_field_data__{self.custom_field.key}__contains": self.value}
                ).exists():
                    raise models.ProtectedError(
                        msg="Cannot delete this choice because it is in active use.",
                        protected_objects=[self],  # TODO should this be model.objects.filter(...) instead?
                    )

        super().delete(*args, **kwargs)

    def to_objectchange(self, action, related_object=None, **kwargs):
        # Annotate the parent field
        try:
            field = self.custom_field
        except ObjectDoesNotExist:
            # The parent field has already been deleted
            field = None

        return super().to_objectchange(action, related_object=field, **kwargs)
