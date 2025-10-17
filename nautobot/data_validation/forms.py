"""Forms for data_validation."""

from django import forms
from django.contrib.contenttypes.models import ContentType

from nautobot.apps.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    BootstrapMixin,
    BulkEditNullBooleanSelect,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    MultipleContentTypeField,
    MultiValueCharField,
    StaticSelect2,
    TagFilterField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.core.utils.config import get_settings_or_config
from nautobot.data_validation.models import (
    DataCompliance,
    MinMaxValidationRule,
    RegularExpressionValidationRule,
    RequiredValidationRule,
    UniqueValidationRule,
)
from nautobot.dcim.choices import DeviceUniquenessChoices
from nautobot.dcim.models import Device
from nautobot.extras.forms import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
    TagsBulkEditFormMixin,
)
from nautobot.extras.utils import FeatureQuery

#
# RegularExpressionValidationRules
#


class RegularExpressionValidationRuleForm(NautobotModelForm):
    """Base model form for the RegularExpressionValidationRule model."""

    content_type = DynamicModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()).order_by(
            "app_label", "model"
        ),
    )

    class Meta:
        """Form metadata for the RegularExpressionValidationRule model."""

        model = RegularExpressionValidationRule
        fields = "__all__"


class RegularExpressionValidationRuleBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Base bulk edit form for the RegularExpressionValidationRule model."""

    pk = DynamicModelMultipleChoiceField(
        queryset=RegularExpressionValidationRule.objects.all(), widget=forms.MultipleHiddenInput
    )
    enabled = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    regular_expression = forms.CharField(required=False)
    error_message = forms.CharField(required=False)
    context_processing = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )

    class Meta:
        """Bulk edit form metadata for the RegularExpressionValidationRule model."""

        fields = ["tags"]
        nullable_fields = ["error_message"]


class RegularExpressionValidationRuleFilterForm(NautobotFilterForm):
    """Base filter form for the RegularExpressionValidationRule model."""

    model = RegularExpressionValidationRule
    field_order = [
        "q",
        "name",
        "enabled",
        "content_type",
        "field",
        "regular_expression",
        "context_processing",
        "error_message",
    ]
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(
        feature="custom_validators",
        queryset=ContentType.objects.all().order_by("app_label", "model"),
        choices_as_strings=True,
        required=False,
    )
    tags = TagFilterField(model)


#
# MinMaxValidationRules
#


class MinMaxValidationRuleForm(NautobotModelForm):
    """Base model form for the MinMaxValidationRule model."""

    content_type = DynamicModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()).order_by(
            "app_label", "model"
        ),
    )

    class Meta:
        """Form metadata for the MinMaxValidationRule model."""

        model = MinMaxValidationRule
        fields = "__all__"


class MinMaxValidationRuleBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Base bulk edit form for the MinMaxValidationRule model."""

    pk = DynamicModelMultipleChoiceField(queryset=MinMaxValidationRule.objects.all(), widget=forms.MultipleHiddenInput)
    enabled = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    min = forms.IntegerField(required=False)
    max = forms.IntegerField(required=False)
    error_message = forms.CharField(required=False)

    class Meta:
        """Bulk edit form metadata for the MinMaxValidationRule model."""

        fields = ["tags"]
        nullable_fields = ["error_message"]


class MinMaxValidationRuleFilterForm(NautobotFilterForm):
    """Base filter form for the MinMaxValidationRule model."""

    model = MinMaxValidationRule
    field_order = ["q", "name", "enabled", "content_type", "field", "min", "max", "error_message"]
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(
        feature="custom_validators",
        queryset=ContentType.objects.all().order_by("app_label", "model"),
        choices_as_strings=True,
        required=False,
    )
    min = forms.IntegerField(required=False)
    max = forms.IntegerField(required=False)
    tags = TagFilterField(model)


#
# RequiredValidationRules
#


class RequiredValidationRuleForm(NautobotModelForm):
    """Base model form for the RequiredValidationRule model."""

    content_type = DynamicModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()).order_by(
            "app_label", "model"
        ),
    )

    class Meta:
        """Form metadata for the RequiredValidationRule model."""

        model = RequiredValidationRule
        fields = "__all__"


class RequiredValidationRuleBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Base bulk edit form for the RequiredValidationRule model."""

    pk = DynamicModelMultipleChoiceField(
        queryset=RequiredValidationRule.objects.all(), widget=forms.MultipleHiddenInput
    )
    enabled = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    error_message = forms.CharField(required=False)

    class Meta:
        """Bulk edit form metadata for the RequiredValidationRule model."""

        fields = ["tags"]
        nullable_fields = ["error_message"]


class RequiredValidationRuleFilterForm(NautobotFilterForm):
    """Base filter form for the RequiredValidationRule model."""

    model = RequiredValidationRule
    field_order = [
        "q",
        "name",
        "enabled",
        "content_type",
        "field",
        "error_message",
    ]
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(
        feature="custom_validators",
        queryset=ContentType.objects.all().order_by("app_label", "model"),
        choices_as_strings=True,
        required=False,
    )
    tags = TagFilterField(model)


#
# UniqueValidationRules
#


class UniqueValidationRuleForm(NautobotModelForm):
    """Base model form for the UniqueValidationRule model."""

    content_type = DynamicModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_validators").get_query()).order_by(
            "app_label", "model"
        ),
    )

    class Meta:
        """Form metadata for the UniqueValidationRule model."""

        model = UniqueValidationRule
        fields = "__all__"


class UniqueValidationRuleBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    """Base bulk edit form for the UniqueValidationRule model."""

    pk = DynamicModelMultipleChoiceField(queryset=UniqueValidationRule.objects.all(), widget=forms.MultipleHiddenInput)
    enabled = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    max_instances = forms.IntegerField(required=False)
    error_message = forms.CharField(required=False)

    class Meta:
        """Bulk edit form metadata for the UniqueValidationRule model."""

        fields = ["tags"]
        nullable_fields = ["error_message"]


class UniqueValidationRuleFilterForm(NautobotFilterForm):
    """Base filter form for the UniqueValidationRule model."""

    model = UniqueValidationRule
    field_order = [
        "q",
        "name",
        "enabled",
        "content_type",
        "field",
        "max_instances",
        "error_message",
    ]
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(
        feature="custom_validators",
        queryset=ContentType.objects.all().order_by("app_label", "model"),
        choices_as_strings=True,
        required=False,
    )
    max_instances = forms.IntegerField(required=False)
    tags = TagFilterField(model)


#
# DataCompliance
#


class DataComplianceFilterForm(BootstrapMixin, forms.Form):
    """Form for DataCompliance instances."""

    model = DataCompliance
    compliance_class_name = MultiValueCharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    validated_attribute = MultiValueCharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    valid = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    content_type = MultipleContentTypeField(
        feature="custom_validators",
        queryset=ContentType.objects.all().order_by("app_label", "model"),
        choices_as_strings=True,
        required=False,
    )
    q = forms.CharField(required=False, label="Search")


#
# Device Constraints
#


class DeviceConstraintsForm(BootstrapMixin, forms.Form):
    DEVICE_UNIQUENESS = forms.ChoiceField(
        choices=DeviceUniquenessChoices.CHOICES,
        label="Device Uniqueness",
        required=True,
        error_messages={
            "invalid_choice": f"Invalid value. Available options are: {', '.join(DeviceUniquenessChoices.values())}"
        },
    )
    DEVICE_NAME_REQUIRED = forms.BooleanField(
        label="Device name required (cannot be blank or null)",
        initial=False,
        required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["DEVICE_UNIQUENESS"].initial = get_settings_or_config(
            "DEVICE_UNIQUENESS", fallback=DeviceUniquenessChoices.DEFAULT
        )

        device_ct = ContentType.objects.get_for_model(Device)
        name_rule_exists = RequiredValidationRule.objects.filter(content_type=device_ct, field="name").exists()

        self.fields["DEVICE_NAME_REQUIRED"].initial = name_rule_exists

        if user is not None and not user.is_staff:
            for field in self.fields.values():
                field.disabled = True
