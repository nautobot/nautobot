import logging
import re
from collections import OrderedDict
from datetime import datetime, date

from django import forms
from django.db import models, transaction
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.core.validators import RegexValidator, ValidationError
from django.forms.widgets import TextInput
from django.utils.safestring import mark_safe

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
from nautobot.core.utils.data import render_jinja2
from nautobot.extras.choices import CustomFieldFilterLogicChoices, CustomFieldTypeChoices
from nautobot.extras.models import ChangeLoggedModel
from nautobot.extras.models.mixins import NotesMixin
from nautobot.extras.tasks import delete_custom_field_data, update_custom_field_choice_data
from nautobot.extras.utils import check_if_key_is_graphql_safe, FeatureQuery, extras_features

logger = logging.getLogger(__name__)


class ComputedFieldManager(BaseManager.from_queryset(RestrictedQuerySet)):
    use_in_migrations = True

    def get_for_model(self, model):
        """
        Return all ComputedFields assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.get_queryset().filter(content_type=content_type)


@extras_features("graphql")
class ComputedField(BaseModel, ChangeLoggedModel, NotesMixin):
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
    label = models.CharField(max_length=100, help_text="Name of the field as displayed to users")
    description = models.CharField(max_length=200, blank=True)
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
            rendered = render_jinja2(self.template, context)
            # If there is an undefined variable within a template, it returns nothing
            # Doesn't raise an exception either most likely due to using Undefined rather
            # than StrictUndefined, but return fallback_value if None is returned
            if rendered is None:
                logger.warning("Failed to render computed field %s", self.key)
                return self.fallback_value
            return rendered
        except Exception as exc:
            logger.warning("Failed to render computed field %s: %s", self.key, exc)
            return self.fallback_value

    def clean(self):
        super().clean()
        if self.key != "":
            check_if_key_is_graphql_safe(self.__class__.__name__, self.key)


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

    def get_for_model(self, model):
        """
        Return all CustomFields assigned to the given model.
        """
        content_type = ContentType.objects.get_for_model(model._meta.concrete_model)
        return self.get_queryset().filter(content_types=content_type)


@extras_features("webhooks")
class CustomField(BaseModel, ChangeLoggedModel, NotesMixin):
    content_types = models.ManyToManyField(
        to=ContentType,
        related_name="custom_fields",
        verbose_name="Object(s)",
        limit_choices_to=FeatureQuery("custom_fields"),
        help_text="The object(s) to which this field applies.",
    )
    grouping = models.CharField(
        max_length=255,
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
        max_length=50,
        help_text="Name of the field as displayed to users.",
        blank=False,
    )
    key = AutoSlugField(
        blank=True,
        max_length=50,
        separator="_",
        populate_from="label",
        help_text="Internal field name. Please use underscores rather than dashes in this key.",
        slugify_function=slugify_dashes_to_underscores,
    )
    description = models.CharField(max_length=200, blank=True, help_text="A helpful description for this field.")
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
            "Default value for the field (must be a JSON value). Encapsulate strings with double quotes (e.g. "
            '"Foo").'
        ),
    )
    weight = models.PositiveSmallIntegerField(
        default=100, help_text="Fields with higher weights appear lower in a form."
    )
    validation_minimum = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Minimum value",
        help_text="Minimum allowed value (for numeric fields).",
    )
    validation_maximum = models.BigIntegerField(
        blank=True,
        null=True,
        verbose_name="Maximum value",
        help_text="Maximum allowed value (for numeric fields).",
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

        # Minimum/maximum values can be set only for numeric fields
        if self.validation_minimum is not None and self.type != CustomFieldTypeChoices.TYPE_INTEGER:
            raise ValidationError({"validation_minimum": "A minimum value may be set only for numeric fields"})
        if self.validation_maximum is not None and self.type != CustomFieldTypeChoices.TYPE_INTEGER:
            raise ValidationError({"validation_maximum": "A maximum value may be set only for numeric fields"})

        # Regex validation can be set only for text, url, select and multi-select fields
        if self.validation_regex and self.type not in CustomFieldTypeChoices.REGEX_TYPES:
            raise ValidationError(
                {"validation_regex": "Regular expression validation is supported only for text, URL and select fields"}
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
        self, set_initial=True, enforce_required=True, for_csv_import=False, simple_json_filter=False, label=None
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

        # Text and URL
        elif self.type in (CustomFieldTypeChoices.TYPE_URL, CustomFieldTypeChoices.TYPE_TEXT):
            if self.type == CustomFieldTypeChoices.TYPE_URL:
                field = LaxURLField(required=required, initial=initial)
            elif self.type == CustomFieldTypeChoices.TYPE_TEXT:
                field = forms.CharField(max_length=255, required=required, initial=initial)

            if self.validation_regex:
                field.validators = [
                    RegexValidator(
                        regex=self.validation_regex,
                        message=mark_safe(f"Values must match this regex: <code>{self.validation_regex}</code>"),
                    )
                ]

        # Markdown
        elif self.type == CustomFieldTypeChoices.TYPE_MARKDOWN:
            field = CommentField(widget=SmallTextarea, label=None)

        # JSON
        elif self.type == CustomFieldTypeChoices.TYPE_JSON:
            if simple_json_filter:
                field = JSONField(encoder=DjangoJSONEncoder, required=required, initial=None, widget=TextInput)
            else:
                field = JSONField(encoder=DjangoJSONEncoder, required=required, initial=initial)

        # Select or Multi-select
        else:
            choices = [(cfc.value, cfc.value) for cfc in self.custom_field_choices.all()]
            default_choice = self.custom_field_choices.filter(value=self.default).first()

            # Set the initial value to the first available choice (if any)
            if self.type == CustomFieldTypeChoices.TYPE_SELECT:
                if not required or default_choice is None:
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
        form_field = self.to_form_field(*args, **kwargs)
        # We would handle type selection differently because:
        # 1. We'd need to use StaticSelect2Multiple for lookup_type 'exact' because self.type `select` uses StaticSelect2 by default.
        # 2. Remove the blank choice since StaticSelect2Multiple is always blank and interprets the blank choice as an extra option.
        # 3. If lookup_type is not the same as exact, use MultiValueCharInput
        if self.type == CustomFieldTypeChoices.TYPE_SELECT:
            if lookup_expr in ["exact", "contains"]:
                choices = form_field.choices[1:]
                form_field.widget = StaticSelect2Multiple(choices=choices)
            else:
                form_field.widget = MultiValueCharInput()
        return form_field

    def validate(self, value):
        """
        Validate a value according to the field's type validation rules.

        Returns the value, possibly cleaned up
        """
        if value not in [None, "", []]:
            # Validate text field
            if self.type in (CustomFieldTypeChoices.TYPE_TEXT, CustomFieldTypeChoices.TYPE_URL):
                if not isinstance(value, str):
                    raise ValidationError("Value must be a string")

                if self.validation_regex and not re.search(self.validation_regex, value):
                    raise ValidationError(f"Value must match regex '{self.validation_regex}'")

            # Validate integer
            if self.type == CustomFieldTypeChoices.TYPE_INTEGER:
                try:
                    value = int(value)
                except ValueError:
                    raise ValidationError("Value must be an integer.")
                if self.validation_minimum is not None and value < self.validation_minimum:
                    raise ValidationError(f"Value must be at least {self.validation_minimum}")
                if self.validation_maximum is not None and value > self.validation_maximum:
                    raise ValidationError(f"Value must not exceed {self.validation_maximum}")

            # Validate boolean
            if self.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
                try:
                    value = is_truthy(value)
                except ValueError as exc:
                    raise ValidationError("Value must be true or false.") from exc

            # Validate date
            if self.type == CustomFieldTypeChoices.TYPE_DATE:
                if not isinstance(value, date):
                    try:
                        datetime.strptime(value, "%Y-%m-%d")
                    except ValueError:
                        raise ValidationError("Date values must be in the format YYYY-MM-DD.")

            # Validate selected choice
            if self.type == CustomFieldTypeChoices.TYPE_SELECT:
                if value not in self.custom_field_choices.values_list("value", flat=True):
                    raise ValidationError(
                        f"Invalid choice ({value}). Available choices are: {', '.join(self.custom_field_choices.values_list('value', flat=True))}"
                    )

            if self.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
                if isinstance(value, str):
                    value = value.split(",")
                if not set(value).issubset(self.custom_field_choices.values_list("value", flat=True)):
                    raise ValidationError(
                        f"Invalid choice(s) ({value}). Available choices are: {', '.join(self.custom_field_choices.values_list('value', flat=True))}"
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

        delete_custom_field_data.delay(self.key, content_types)

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
    value = models.CharField(max_length=100)
    weight = models.PositiveSmallIntegerField(default=100, help_text="Higher weights appear later in the list")

    documentation_static_path = "docs/user-guide/platform-functionality/customfield.html"

    class Meta:
        ordering = ["custom_field", "weight", "value"]
        unique_together = ["custom_field", "value"]

    def __str__(self):
        return self.value

    def clean(self):
        if self.custom_field.type not in (CustomFieldTypeChoices.TYPE_SELECT, CustomFieldTypeChoices.TYPE_MULTISELECT):
            raise ValidationError("Custom field choices can only be assigned to selection fields.")

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
            transaction.on_commit(
                lambda: update_custom_field_choice_data.delay(self.custom_field.pk, database_object.value, self.value)
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
