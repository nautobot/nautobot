"""Models for Data Validation Engine."""

import re

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.cache import cache
from django.core.validators import MinValueValidator, ValidationError
from django.db import models

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.models import BaseManager, BaseModel
from nautobot.core.models.generics import PrimaryModel
from nautobot.core.models.querysets import RestrictedQuerySet
from nautobot.core.utils.cache import construct_cache_key
from nautobot.extras.models.mixins import DynamicGroupsModelMixin, NotesMixin, SavedViewMixin
from nautobot.extras.utils import extras_features, FeatureQuery


def validate_regex(value):
    """
    Checks that the value is a valid regular expression.

    Don't confuse this with RegexValidator, which *uses* a regex to validate a value.
    """
    try:
        re.compile(value)
    except re.error as e:
        raise ValidationError(f"{value} is not a valid regular expression.") from e


class ValidationRuleManager(BaseManager.from_queryset(RestrictedQuerySet)):
    """Adds a helper method for getting all active instances for a given content type."""

    def get_for_model(self, content_type: str):
        """Given a content type string (<app_label>.<model>), return all instances that are enabled for that model."""
        app_label, model = content_type.split(".")
        cache_key = construct_cache_key(self, method_name="get_for_model", branch_aware=True, content_type=content_type)
        queryset = cache.get(cache_key)
        if queryset is None:
            queryset = self.filter(content_type__app_label=app_label, content_type__model=model)
            cache.set(cache_key, queryset)
        return queryset

    @property
    def get_for_model_cache_key_prefix(self):
        return construct_cache_key(self, method_name="get_for_model", branch_aware=True)

    def get_enabled_for_model(self, content_type: str):
        """As get_for_model(), but only return enabled rules."""
        app_label, model = content_type.split(".")
        cache_key = construct_cache_key(
            self, method_name="get_enabled_for_model", branch_aware=True, content_type=content_type
        )
        queryset = cache.get(cache_key)
        if queryset is None:
            queryset = self.filter(content_type__app_label=app_label, content_type__model=model, enabled=True)
            cache.set(cache_key, queryset)
        return queryset

    @property
    def get_enabled_for_model_cache_key_prefix(self):
        return construct_cache_key(self, method_name="get_enabled_for_model", branch_aware=True)


class ValidationRuleModelMixin(models.Model):
    """Base model for all validation engine rule models."""

    name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, unique=True)
    field = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
    )
    content_type = models.ForeignKey(
        to=ContentType, on_delete=models.CASCADE, limit_choices_to=FeatureQuery("custom_validators")
    )
    enabled = models.BooleanField(default=True)
    error_message = models.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        blank=True,
        default="",
        help_text="Optional error message to display when validation fails.",
    )

    objects = ValidationRuleManager()
    documentation_static_path = "docs/user-guide/platform-functionality/data-validation.html"

    is_data_compliance_model = False

    class Meta:
        """Model metadata for all validation engine rule models."""

        abstract = True

    def __str__(self):
        """Return a sane string representation of the instance."""
        return self.name


@extras_features(
    "custom_fields",
    "custom_links",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class RegularExpressionValidationRule(ValidationRuleModelMixin, PrimaryModel):
    """A type of validation rule that applies a regular expression to a given model field."""

    regular_expression = models.TextField()
    context_processing = models.BooleanField(
        default=False,
        help_text="When enabled, the regular expression value is first processed as a Jinja2 template with access to the context of the data being validated in a variable named <code>object</code>.",
    )

    clone_fields = ["enabled", "content_type", "regular_expression", "error_message"]

    class Meta:
        """Model metadata for the RegularExpressionValidationRule model."""

        db_table = "data_validation_regexrule"
        ordering = ("name",)
        unique_together = [["content_type", "field"]]

    def clean(self):
        """Ensure field is valid for the model and has not been blacklisted."""
        # Only validate the regular_expression if context processing is disabled
        if not self.context_processing:
            validate_regex(self.regular_expression)

        # Check that field exists on model
        if self.field not in [f.name for f in self.content_type.model_class()._meta.get_fields()]:
            raise ValidationError(
                {
                    "field": f"Not a valid field for content type {self.content_type.app_label}.{self.content_type.model}."
                }
            )

        blacklisted_field_types = (
            models.AutoField,
            models.BigAutoField,
            models.BooleanField,
            models.FileField,
            models.FilePathField,
            models.ForeignKey,
            models.ImageField,
            models.JSONField,
            models.Manager,
            models.ManyToManyField,
            models.NullBooleanField,
            models.OneToOneField,
            models.fields.related.RelatedField,
            models.SmallAutoField,
            models.UUIDField,
        )

        model_field = self.content_type.model_class()._meta.get_field(self.field)

        if self.field.startswith("_") or not model_field.editable or isinstance(model_field, blacklisted_field_types):
            raise ValidationError({"field": "This field's type does not support regular expression validation."})


@extras_features(
    "custom_fields",
    "custom_links",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class MinMaxValidationRule(ValidationRuleModelMixin, PrimaryModel):
    """A type of validation rule that applies min/max constraints to a given numeric model field."""

    min = models.FloatField(
        null=True, blank=True, help_text="When set, apply a minimum value contraint to the value of the model field."
    )
    max = models.FloatField(
        null=True, blank=True, help_text="When set, apply a maximum value contraint to the value of the model field."
    )

    clone_fields = ["enabled", "content_type", "min", "max", "error_message"]

    class Meta:
        """Model metadata for the MinMaxValidationRule model."""

        db_table = "data_validation_minmaxrule"
        ordering = ("name",)
        unique_together = [["content_type", "field"]]

    def clean(self):
        """Ensure field is valid for the model and has not been blacklisted."""
        if self.field not in [f.name for f in self.content_type.model_class()._meta.get_fields()]:
            raise ValidationError(
                {
                    "field": f"Not a valid field for content type {self.content_type.app_label}.{self.content_type.model}."
                }
            )

        allowed_field_types = (
            models.DecimalField,
            models.FloatField,
            models.IntegerField,
        )

        excluded_field_types = (
            models.AutoField,
            models.BigAutoField,
        )

        model_field = self.content_type.model_class()._meta.get_field(self.field)

        if not isinstance(model_field, allowed_field_types) or (
            self.field.startswith("_") or not model_field.editable or isinstance(model_field, excluded_field_types)
        ):
            raise ValidationError({"field": "This field's type does not support min/max validation."})

        if self.min is None and self.max is None:
            raise ValidationError("At least a minimum or maximum value must be specified.")

        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValidationError(
                {
                    "min": "Minimum value cannot be more than the maximum value.",
                    "max": "Maximum value cannot be less than the minimum value.",
                }
            )


@extras_features(
    "custom_fields",
    "custom_links",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class RequiredValidationRule(ValidationRuleModelMixin, PrimaryModel):
    """A type of validation rule that applies a required constraint to a given model field."""

    clone_fields = ["enabled", "content_type", "error_message"]

    class Meta:
        """Model metadata for the RequiredValidationRule model."""

        db_table = "data_validation_requiredrule"
        ordering = ("name",)
        unique_together = [["content_type", "field"]]

    def clean(self):
        """Ensure field is valid for the model and has not been blacklisted."""
        if self.field not in [f.name for f in self.content_type.model_class()._meta.get_fields()]:
            raise ValidationError(
                {
                    "field": f"Not a valid field for content type {self.content_type.app_label}.{self.content_type.model}."
                }
            )

        blacklisted_field_types = (
            models.AutoField,
            models.Manager,
            models.fields.related.RelatedField,
            models.ManyToManyField,
        )

        model_field = self.content_type.model_class()._meta.get_field(self.field)

        if self.field.startswith("_") or not model_field.editable or isinstance(model_field, blacklisted_field_types):
            raise ValidationError({"field": "This field's type does not support required validation."})

        # Generally, only Field(null=True) is considered except for the case of Field(null=False, blank=True)
        # which is commonly seen on CharFields and results in a default of empty string which is unacceptable
        # if the field is to be marked as required.
        if model_field.null is False and not (model_field.null is False and model_field.blank is True):
            raise ValidationError({"field": "This field is already required by default."})


@extras_features(
    "custom_fields",
    "custom_links",
    "export_templates",
    "graphql",
    "relationships",
    "webhooks",
)
class UniqueValidationRule(ValidationRuleModelMixin, PrimaryModel):
    """
    A type of validation rule that applies a unique constraint to a given model field.

    Optionally specify the max number of similar values for the field accross all model instances. Default of 1.
    """

    max_instances = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    clone_fields = ["enabled", "content_type", "max_instances", "error_message"]

    class Meta:
        """Model metadata for the UniqueValidationRule model."""

        db_table = "data_validation_uniquerule"
        ordering = ("name",)
        unique_together = [["content_type", "field"]]

    def clean(self):
        """Ensure field is valid for the model and has not been blacklisted."""
        if self.field not in [f.name for f in self.content_type.model_class()._meta.get_fields()]:
            raise ValidationError(
                {
                    "field": f"Not a valid field for content type {self.content_type.app_label}.{self.content_type.model}."
                }
            )

        blacklisted_field_types = (
            models.Manager,
            models.fields.related.RelatedField,
            models.ManyToManyField,
        )

        model_field = self.content_type.model_class()._meta.get_field(self.field)

        if self.field.startswith("_") or not model_field.editable or isinstance(model_field, blacklisted_field_types):
            raise ValidationError({"field": "This field's type does not support uniqueness validation."})

        if getattr(model_field, "unique", False):
            raise ValidationError({"field": "This field is already unique by default."})


@extras_features(
    "export_templates",
    "graphql",
)
class DataCompliance(DynamicGroupsModelMixin, NotesMixin, SavedViewMixin, BaseModel):
    """Model to represent the results of an audit method."""

    compliance_class_name = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=False, null=False)
    last_validation_date = models.DateTimeField(blank=False, null=False, auto_now=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.PROTECT, blank=False, null=False)
    object_id = models.UUIDField(blank=False, null=False)
    validated_object = GenericForeignKey(ct_field="content_type", fk_field="object_id")
    validated_object_str = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, default="")
    validated_attribute = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, default="")
    validated_attribute_value = models.CharField(max_length=CHARFIELD_MAX_LENGTH, blank=True, default="")
    valid = models.BooleanField(blank=False, null=False)
    message = models.TextField(blank=True, default="")

    is_data_compliance_model = False

    class Meta:
        """Meta class for Audit model."""

        verbose_name_plural = "Data Compliance"

        unique_together = (
            "compliance_class_name",
            "content_type",
            "object_id",
            "validated_attribute",
        )

    def __str__(self):
        """Return a string representation of this DataCompliance object."""
        return f"{self.compliance_class_name}: {self.validated_attribute} compliance for {self.validated_object}"
