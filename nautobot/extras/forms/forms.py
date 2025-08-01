import inspect
import logging

from celery import chain
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db.models.fields import TextField
from django.forms import inlineformset_factory, ModelMultipleChoiceField, MultipleHiddenInput
from django.urls.base import reverse
from django.utils.timezone import get_current_timezone_name

from nautobot.core.constants import CHARFIELD_MAX_LENGTH
from nautobot.core.forms import (
    add_blank_choice,
    APISelect,
    APISelectMultiple,
    BootstrapMixin,
    BulkEditForm,
    BulkEditNullBooleanSelect,
    ColorSelect,
    CommentField,
    CSVContentTypeField,
    CSVModelForm,
    DateTimePicker,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    JSONField,
    LaxURLField,
    MultipleContentTypeField,
    SlugField,
    StaticSelect2,
    StaticSelect2Multiple,
    TagFilterField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.core.forms.forms import ConfirmationForm
from nautobot.core.forms.widgets import ClearableFileInput
from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
from nautobot.dcim.models import Device, DeviceRedundancyGroup, DeviceType, Location, Platform
from nautobot.extras.choices import (
    ButtonClassChoices,
    CustomFieldFilterLogicChoices,
    DynamicGroupTypeChoices,
    JobExecutionType,
    JobQueueTypeChoices,
    JobResultStatusChoices,
    ObjectChangeActionChoices,
    RelationshipTypeChoices,
    WebhookHttpMethodChoices,
)
from nautobot.extras.constants import JOB_OVERRIDABLE_FIELDS
from nautobot.extras.datasources import get_datasource_content_choices
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    ExternalIntegration,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobButton,
    JobHook,
    JobQueue,
    JobResult,
    MetadataChoice,
    MetadataType,
    Note,
    ObjectChange,
    ObjectMetadata,
    Relationship,
    RelationshipAssociation,
    Role,
    SavedView,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    StaticGroupAssociation,
    Status,
    Tag,
    Team,
    Webhook,
)
from nautobot.extras.registry import registry
from nautobot.extras.signals import change_context_state
from nautobot.extras.tasks import delete_custom_field_data
from nautobot.extras.utils import (
    ChangeLoggedModelsQuery,
    FeatureQuery,
    get_worker_count,
    RoleModelsQuery,
    TaggableClassesQuery,
)
from nautobot.tenancy.forms import TenancyFilterForm, TenancyForm
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.virtualization.models import Cluster, ClusterGroup, VirtualMachine

from .base import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
)
from .mixins import (
    CustomFieldModelBulkEditFormMixin,
    CustomFieldModelFormMixin,
    NoteModelBulkEditFormMixin,
    NoteModelFormMixin,
    TagsBulkEditFormMixin,
)

logger = logging.getLogger(__name__)

__all__ = (
    "BaseDynamicGroupMembershipFormSet",
    "ComputedFieldBulkEditForm",
    "ComputedFieldFilterForm",
    "ComputedFieldForm",
    "ConfigContextBulkEditForm",
    "ConfigContextFilterForm",
    "ConfigContextForm",
    "ConfigContextSchemaBulkEditForm",
    "ConfigContextSchemaFilterForm",
    "ConfigContextSchemaForm",
    "CustomFieldBulkCreateForm",  # 2.0 TODO remove this deprecated class
    "CustomFieldBulkDeleteForm",
    "CustomFieldBulkEditForm",
    "CustomFieldChoiceFormSet",
    "CustomFieldFilterForm",
    "CustomFieldForm",
    "CustomFieldModelCSVForm",
    "CustomLinkBulkEditForm",
    "CustomLinkFilterForm",
    "CustomLinkForm",
    "DynamicGroupBulkAssignForm",
    "DynamicGroupFilterForm",
    "DynamicGroupForm",
    "DynamicGroupMembershipFormSet",
    "ExportTemplateBulkEditForm",
    "ExportTemplateFilterForm",
    "ExportTemplateForm",
    "ExternalIntegrationBulkEditForm",
    "ExternalIntegrationFilterForm",
    "ExternalIntegrationForm",
    "GitRepositoryBulkEditForm",
    "GitRepositoryFilterForm",
    "GitRepositoryForm",
    "GraphQLQueryFilterForm",
    "GraphQLQueryForm",
    "ImageAttachmentForm",
    "JobBulkEditForm",
    "JobButtonBulkEditForm",
    "JobButtonFilterForm",
    "JobButtonForm",
    "JobEditForm",
    "JobFilterForm",
    "JobForm",
    "JobHookBulkEditForm",
    "JobHookFilterForm",
    "JobHookForm",
    "JobQueueBulkEditForm",
    "JobQueueFilterForm",
    "JobQueueForm",
    "JobResultFilterForm",
    "JobScheduleForm",
    "LocalContextFilterForm",
    "LocalContextModelBulkEditForm",
    "LocalContextModelForm",
    "MetadataChoiceFormSet",
    "MetadataTypeBulkEditForm",
    "MetadataTypeFilterForm",
    "MetadataTypeForm",
    "NoteFilterForm",
    "NoteForm",
    "ObjectChangeFilterForm",
    "ObjectMetadataFilterForm",
    "PasswordInputWithPlaceholder",
    "RelationshipAssociationFilterForm",
    "RelationshipBulkEditForm",
    "RelationshipFilterForm",
    "RelationshipForm",
    "RoleBulkEditForm",
    "RoleFilterForm",
    "RoleForm",
    "SavedViewForm",
    "SavedViewModalForm",
    "ScheduledJobFilterForm",
    "SecretFilterForm",
    "SecretForm",
    "SecretsGroupAssociationFormSet",
    "SecretsGroupBulkEditForm",
    "SecretsGroupFilterForm",
    "SecretsGroupForm",
    "StaticGroupAssociationFilterForm",
    "StatusBulkEditForm",
    "StatusFilterForm",
    "StatusForm",
    "TagBulkEditForm",
    "TagFilterForm",
    "TagForm",
    "WebhookBulkEditForm",
    "WebhookFilterForm",
    "WebhookForm",
)


#
# Computed Fields
#
class ComputedFieldBulkEditForm(BootstrapMixin, NoteModelBulkEditFormMixin):
    pk = forms.ModelMultipleChoiceField(queryset=ComputedField.objects.all(), widget=forms.MultipleHiddenInput())

    label = forms.CharField(
        max_length=CHARFIELD_MAX_LENGTH, required=False, help_text="Name of the field as displayed to users."
    )
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    grouping = forms.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        required=False,
        help_text="Human-readable grouping that this computed field belongs to.",
    )
    fallback_value = forms.CharField(
        max_length=500,
        required=False,
        help_text="Fallback value (if any) to be output for the field in the case of a template rendering error.",
    )
    weight = forms.IntegerField(required=False, min_value=0)
    advanced_ui = forms.NullBooleanField(
        required=False,
        label="Move to Advanced tab",
        help_text="Hide this field from the object's primary information tab. It will appear in the 'Advanced' tab instead.",
    )
    template = forms.CharField(
        max_length=500, widget=forms.Textarea, required=False, help_text="Jinja2 template code for field value"
    )

    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Type",
    )

    class Meta:
        model = ComputedField
        nullable_fields = ["description", "grouping", "fallback_value"]


class ComputedFieldForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
        required=True,
        label="Content Type",
    )
    key = SlugField(
        label="Key",
        max_length=CHARFIELD_MAX_LENGTH,
        slug_source="label",
        help_text="Internal name of this field. Please use underscores rather than dashes.",
    )
    template = forms.CharField(
        widget=forms.Textarea,
        help_text=(
            "Jinja2 template code for field value.<br>"
            "Use <code>obj</code> to refer to the object to which this computed field is attached."
        ),
    )

    class Meta:
        model = ComputedField
        fields = (
            "content_type",
            "label",
            "grouping",
            "key",
            "description",
            "template",
            "fallback_value",
            "weight",
            "advanced_ui",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.present_in_database:
            self.fields["key"].widget.attrs["readonly"] = True


class ComputedFieldFilterForm(BootstrapMixin, forms.Form):
    model = ComputedField
    q = forms.CharField(required=False, label="Search")
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Type",
    )


#
# Config contexts
#


class ConfigContextForm(BootstrapMixin, NoteModelFormMixin, forms.ModelForm):
    locations = DynamicModelMultipleChoiceField(queryset=Location.objects.all(), required=False)
    roles = DynamicModelMultipleChoiceField(
        queryset=Role.objects.get_for_models([Device, VirtualMachine]),
        query_params={"content_types": [Device._meta.label_lower, VirtualMachine._meta.label_lower]},
        required=False,
    )
    device_types = DynamicModelMultipleChoiceField(queryset=DeviceType.objects.all(), required=False)
    platforms = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), required=False)
    cluster_groups = DynamicModelMultipleChoiceField(queryset=ClusterGroup.objects.all(), required=False)
    clusters = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False)
    tenant_groups = DynamicModelMultipleChoiceField(queryset=TenantGroup.objects.all(), required=False)
    tenants = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), required=False)
    device_redundancy_groups = DynamicModelMultipleChoiceField(
        queryset=DeviceRedundancyGroup.objects.all(), required=False
    )
    tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)
    dynamic_groups = DynamicModelMultipleChoiceField(
        queryset=DynamicGroup.objects.all(), to_field_name="name", required=False
    )

    # Conditional enablement of dynamic groups filtering
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
            self.fields.pop("dynamic_groups")

    data = JSONField(label="")

    class Meta:
        model = ConfigContext
        fields = (
            "name",
            "weight",
            "description",
            "config_context_schema",
            "is_active",
            "locations",
            "roles",
            "device_types",
            "platforms",
            "cluster_groups",
            "clusters",
            "tenant_groups",
            "tenants",
            "device_redundancy_groups",
            "tags",
            "dynamic_groups",
            "data",
        )


class ConfigContextBulkEditForm(BootstrapMixin, NoteModelBulkEditFormMixin, BulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ConfigContext.objects.all(), widget=forms.MultipleHiddenInput)
    config_context_schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), required=False)
    weight = forms.IntegerField(required=False, min_value=0)
    is_active = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect())
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)

    class Meta:
        nullable_fields = [
            "description",
            "config_context_schema",
        ]


class ConfigContextFilterForm(BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label="Search")
    schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), to_field_name="name", required=False)
    location = DynamicModelMultipleChoiceField(queryset=Location.objects.all(), to_field_name="name", required=False)
    role = DynamicModelMultipleChoiceField(
        queryset=Role.objects.get_for_models([Device, VirtualMachine]), to_field_name="name", required=False
    )
    type = DynamicModelMultipleChoiceField(queryset=DeviceType.objects.all(), to_field_name="model", required=False)
    platform = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), to_field_name="name", required=False)
    cluster_group = DynamicModelMultipleChoiceField(
        queryset=ClusterGroup.objects.all(), to_field_name="name", required=False
    )
    cluster_id = DynamicModelMultipleChoiceField(queryset=Cluster.objects.all(), required=False, label="Cluster")
    tenant_group = DynamicModelMultipleChoiceField(
        queryset=TenantGroup.objects.all(), to_field_name="name", required=False
    )
    tenant = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), to_field_name="name", required=False)
    device_redundancy_group = DynamicModelMultipleChoiceField(
        queryset=DeviceRedundancyGroup.objects.all(), to_field_name="name", required=False
    )
    tag = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), to_field_name="name", required=False)
    dynamic_groups = DynamicModelMultipleChoiceField(
        queryset=DynamicGroup.objects.all(), to_field_name="name", required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not settings.CONFIG_CONTEXT_DYNAMIC_GROUPS_ENABLED:
            self.fields.pop("dynamic_groups")


#
# Config context schemas
#


class ConfigContextSchemaForm(NautobotModelForm):
    data_schema = JSONField(label="")

    class Meta:
        model = ConfigContextSchema
        fields = (
            "name",
            "description",
            "data_schema",
        )


class ConfigContextSchemaBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ConfigContextSchema.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)

    class Meta:
        nullable_fields = [
            "description",
        ]


class ConfigContextSchemaFilterForm(BootstrapMixin, forms.Form):
    q = forms.CharField(required=False, label="Search")


#
# Custom fields
#


# CustomFieldChoice inline formset for use with providing dynamic rows when creating/editing choices
# for `CustomField` objects in UI views. Fields/exclude must be set but since we're using all the
# fields we're just setting `exclude=()` here.
CustomFieldChoiceFormSet = inlineformset_factory(
    parent_model=CustomField,
    model=CustomFieldChoice,
    exclude=(),
    extra=5,
    widgets={
        "value": forms.TextInput(attrs={"class": "form-control"}),
        "weight": forms.NumberInput(attrs={"class": "form-control"}),
    },
)


class CustomFieldDescriptionField(CommentField):
    @property
    def default_helptext(self):
        return "Also used as the help text when editing models using this custom field.<br>" + super().default_helptext


class CustomFieldBulkEditForm(BootstrapMixin, NoteModelBulkEditFormMixin):
    pk = forms.ModelMultipleChoiceField(queryset=CustomField.objects.all(), widget=forms.MultipleHiddenInput)
    grouping = forms.CharField(
        required=False,
        max_length=CHARFIELD_MAX_LENGTH,
        label="Grouping",
        help_text="Human-readable grouping that this custom field belongs to.",
    )
    description = forms.CharField(
        required=False,
        max_length=CHARFIELD_MAX_LENGTH,
        label="Description",
        help_text="A helpful description for this field.",
    )
    required = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect,
        label="Required",
        help_text="If true, this field is required when creating new objects or editing an existing object.",
    )
    filter_logic = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(CustomFieldFilterLogicChoices.CHOICES),
        label="Filter logic",
        help_text="Loose matches any instance of a given string; Exact matches the entire field.",
    )
    weight = forms.IntegerField(
        required=False, label="Weight", help_text="Fields with higher weights appear lower in a form."
    )
    advanced_ui = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect,
        label="Move to Advanced tab",
        help_text="Hide this field from the object's primary information tab. It will appear in the 'Advanced' tab instead.",
    )
    add_content_types = MultipleContentTypeField(
        limit_choices_to=FeatureQuery("custom_fields"), required=False, label="Add Content Types"
    )
    remove_content_types = MultipleContentTypeField(
        limit_choices_to=FeatureQuery("custom_fields"), required=False, label="Remove Content Types"
    )

    class Meta:
        model = CustomField
        fields = (
            "grouping",
            "description",
            "required",
            "filter_logic",
            "weight",
            "advanced_ui",
            "add_content_types",
            "remove_content_types",
        )
        nullable_fields = [
            "grouping",
            "description",
        ]


class CustomFieldForm(BootstrapMixin, forms.ModelForm):
    label = forms.CharField(
        required=True, max_length=CHARFIELD_MAX_LENGTH, help_text="Name of the field as displayed to users."
    )
    key = SlugField(
        label="Key",
        max_length=CHARFIELD_MAX_LENGTH,
        slug_source="label",
        help_text="Internal name of this field. Please use underscores rather than dashes.",
    )
    description = CustomFieldDescriptionField(
        label="Description",
        required=False,
    )
    content_types = MultipleContentTypeField(
        feature="custom_fields", help_text="The object(s) to which this field applies."
    )

    class Meta:
        model = CustomField
        fields = (
            "label",
            "grouping",
            "key",
            "type",
            "weight",
            "description",
            "required",
            "default",
            "filter_logic",
            "advanced_ui",
            "content_types",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.initial.get("key"):
            self.fields["key"].disabled = True


class CustomFieldFilterForm(NautobotFilterForm):
    model = CustomField
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()),
        choices_as_strings=True,
        required=False,
        label="Content Type(s)",
    )


class CustomFieldModelCSVForm(CSVModelForm, CustomFieldModelFormMixin):
    """
    Base class for CSV/JSON/YAML import of models that support custom fields.

    TODO: The class name is a misnomer; as of 2.0 this class is **not** used for any CSV imports,
    as that's now handled by the REST API. However it is still used when importing component-templates as
    part of a JSON/YAML DeviceType import.
    """

    def _append_customfield_fields(self):
        # Append form fields
        for cf in CustomField.objects.filter(content_types=self.obj_type):
            field_name = cf.add_prefix_to_cf_key()
            self.fields[field_name] = cf.to_form_field(for_csv_import=True)

            # Annotate the field in the list of CustomField form fields
            self.custom_fields.append(field_name)


# 2.0 TODO: remove this class
@class_deprecated_in_favor_of(CustomFieldModelBulkEditFormMixin)
class CustomFieldBulkCreateForm(CustomFieldModelBulkEditFormMixin):
    """No longer needed as a separate class - use CustomFieldModelBulkEditFormMixin instead."""


class CustomFieldBulkDeleteForm(ConfirmationForm):
    def __init__(self, *args, delete_all=False, **kwargs):
        super().__init__(*args, **kwargs)
        queryset = CustomField.objects.all()
        self.fields["pk"] = ModelMultipleChoiceField(
            queryset=queryset, widget=MultipleHiddenInput, required=not delete_all
        )

    def construct_custom_field_delete_tasks(self, queryset):
        """
        Helper method to construct a list of celery tasks to execute when bulk deleting custom fields.
        """
        change_context = change_context_state.get()
        if change_context is None:
            context = None
        else:
            context = change_context.as_dict(queryset)
            context["context_detail"] = "bulk delete custom field data"
        tasks = []
        for obj in queryset:
            pk_set = set(obj.content_types.values_list("pk", flat=True))
            if pk_set:
                tasks.append(delete_custom_field_data.si(obj.key, pk_set, context))
        return tasks

    def perform_pre_delete(self, queryset):
        """
        Remove all Custom Field Keys/Values from _custom_field_data of the related ContentType in the background.
        """
        if not get_worker_count():
            logger.error("Celery worker process not running. Object custom fields may fail to reflect this deletion.")
            return
        tasks = self.construct_custom_field_delete_tasks(queryset)
        if tasks:
            # Executing the tasks in the background sequentially using chain() aligns with how a single
            # CustomField object is deleted.  We decided to not check the result because it needs at least one worker
            # to be active and comes with extra performance penalty.
            chain(*tasks).apply_async()


#
# Custom Links
#
class CustomLinkBulkEditForm(BootstrapMixin, NoteModelBulkEditFormMixin):
    """Bulk edit form for CustomLink objects."""

    pk = forms.ModelMultipleChoiceField(queryset=CustomLink.objects.all(), widget=forms.MultipleHiddenInput())
    group_name = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    weight = forms.IntegerField(required=False)
    target_url = forms.CharField(max_length=500, required=False)
    text = forms.CharField(max_length=500, required=False)
    button_class = forms.ChoiceField(choices=add_blank_choice(ButtonClassChoices.CHOICES), required=False)
    new_window = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Type",
    )

    class Meta:
        model = CustomLink
        nullable_fields = ["group_name"]


class CustomLinkForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
        label="Content Type",
    )

    class Meta:
        model = CustomLink
        fields = (
            "content_type",
            "name",
            "text",
            "target_url",
            "weight",
            "group_name",
            "button_class",
            "new_window",
        )


class CustomLinkFilterForm(BootstrapMixin, forms.Form):
    model = CustomLink
    q = forms.CharField(required=False, label="Search")
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_links").get_query()).order_by("app_label", "model"),
        required=False,
        label="Content Type",
    )


#
# Dynamic Groups
#


class DynamicGroupForm(TenancyForm, NautobotModelForm):
    """DynamicGroup model form."""

    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
        label="Content Type",
    )
    group_type = forms.ChoiceField(choices=DynamicGroupTypeChoices, widget=StaticSelect2())

    class Meta:
        model = DynamicGroup
        fields = [
            "name",
            "description",
            "content_type",
            "group_type",
            "tenant",
            "tags",
        ]


class DynamicGroupMembershipFormSetForm(forms.ModelForm):
    """DynamicGroupMembership model form for use inline on DynamicGroupFormSet."""

    group = DynamicModelChoiceField(
        queryset=DynamicGroup.objects.filter(
            group_type__in=[DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET]
        ),
        query_params={
            "content_type": "$content_type",
            "group_type": [DynamicGroupTypeChoices.TYPE_DYNAMIC_FILTER, DynamicGroupTypeChoices.TYPE_DYNAMIC_SET],
        },
    )

    class Meta:
        model = DynamicGroupMembership
        fields = ("operator", "group", "weight")


# Inline formset for use with providing dynamic rows when creating/editing memberships of child
# DynamicGroups to a parent DynamicGroup.
BaseDynamicGroupMembershipFormSet = inlineformset_factory(
    parent_model=DynamicGroup,
    model=DynamicGroupMembership,
    form=DynamicGroupMembershipFormSetForm,
    extra=4,
    fk_name="parent_group",
    widgets={
        "operator": StaticSelect2,
        "weight": forms.HiddenInput(),
    },
)


class DynamicGroupMembershipFormSet(BaseDynamicGroupMembershipFormSet):
    """
    Inline formset for use with providing dynamic rows when creating/editing memberships of child
    groups to a parent DynamicGroup.
    """


class DynamicGroupFilterForm(TenancyFilterForm, NautobotFilterForm):
    """DynamicGroup filter form."""

    model = DynamicGroup
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(
        feature="dynamic_groups", choices_as_strings=True, label="Content Type", required=False
    )
    tags = TagFilterField(model)


class DynamicGroupBulkAssignForm(BootstrapMixin, BulkEditForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
        widget=forms.HiddenInput(),
    )
    create_and_assign_to_new_group_name = forms.CharField(
        required=False,
        label="Create a new group",
        help_text="Create a new group with this name and assign the selected objects to it.",
    )

    def __init__(self, model, *args, **kwargs):
        super().__init__(model, *args, **kwargs)
        self.fields["content_type"].initial = ContentType.objects.get_for_model(model)
        self.fields["pk"] = forms.ModelMultipleChoiceField(
            queryset=model.objects.all(),
            widget=forms.MultipleHiddenInput(),
            required=False,
        )
        self.fields["add_to_groups"] = DynamicModelMultipleChoiceField(
            queryset=DynamicGroup.objects.filter(group_type=DynamicGroupTypeChoices.TYPE_STATIC),
            required=False,
            query_params={
                "group_type": "static",
                "content_type": model._meta.label_lower,
            },
            label="Add to existing group(s)",
        )
        self.fields["remove_from_groups"] = DynamicModelMultipleChoiceField(
            queryset=DynamicGroup.objects.filter(group_type=DynamicGroupTypeChoices.TYPE_STATIC),
            required=False,
            query_params={
                "group_type": "static",
                "content_type": model._meta.label_lower,
            },
            label="Remove from group(s)",
        )

    class Meta:
        nullable_fields = []

    def clean(self):
        data = super().clean()

        if "add_to_groups" in data and "remove_from_groups" in data:
            if data["add_to_groups"].filter(pk__in=data["remove_from_groups"].values_list("pk", flat=True)).exists():
                raise ValidationError("Same group specified for both addition and removal")

        return data


#
# Saved View
#


class SavedViewForm(BootstrapMixin, forms.ModelForm):
    is_global_default = forms.BooleanField(
        label="Is global default",
        required=False,
        help_text="If checked, this saved view will be used globally as the default saved view for this particular view",
    )
    is_shared = forms.BooleanField(
        label="Is shared",
        required=False,
        help_text="If checked, all users will be able to see this saved view",
    )

    class Meta:
        model = SavedView
        fields = ["name", "is_global_default", "is_shared"]


class SavedViewModalForm(BootstrapMixin, forms.ModelForm):
    is_shared = forms.BooleanField(
        label="Is shared",
        required=False,
        help_text="If checked, all users will be able to see this saved view",
    )

    class Meta:
        model = SavedView
        fields = ["name", "config", "is_shared"]


class StaticGroupAssociationFilterForm(NautobotFilterForm):
    model = StaticGroupAssociation
    q = forms.CharField(required=False, label="Search")
    dynamic_group = DynamicModelMultipleChoiceField(queryset=DynamicGroup.objects.all(), required=False)
    assigned_object_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
        required=False,
    )


#
# Export Templates
#
class ExportTemplateBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=ExportTemplate.objects.all(), widget=forms.MultipleHiddenInput())

    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    mime_type = forms.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        required=False,
        label="MIME type",
        help_text="Defaults to <code>text/plain</code>",
    )
    file_extension = forms.CharField(
        max_length=CHARFIELD_MAX_LENGTH, required=False, help_text="Extension to append to the rendered filename"
    )

    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()).order_by(
            "app_label", "model"
        ),
        required=False,
        label="Content Type",
    )

    class Meta:
        model = ExportTemplate
        nullable_fields = ["description", "mime_type", "file_extension"]


class ExportTemplateForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()).order_by(
            "app_label", "model"
        ),
        label="Content Type",
    )

    class Meta:
        model = ExportTemplate
        fields = (
            "content_type",
            "name",
            "description",
            "template_code",
            "mime_type",
            "file_extension",
        )


class ExportTemplateFilterForm(BootstrapMixin, forms.Form):
    model = ExportTemplate
    q = forms.CharField(required=False, label="Search")
    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("export_templates").get_query()).order_by(
            "app_label", "model"
        ),
        required=False,
        label="Content Type",
    )


#
# External integrations
#


class ExternalIntegrationForm(NautobotModelForm):
    class Meta:
        model = ExternalIntegration
        fields = "__all__"

        HEADERS_HELP_TEXT = """
            Optional user-defined <a href="https://json.org/">JSON</a> data for this integration. Example:
            <pre><code class="language-json">{
                "Accept": "application/json",
                "Content-Type": "application/json"
            }</code></pre>
        """
        EXTRA_CONFIG_HELP_TEXT = """
            Optional user-defined <a href="https://json.org/">JSON</a> data for this integration. Example:
            <pre><code class="language-json">{
                "key": "value",
                "key2": [
                    "value1",
                    "value2"
                ]
            }</code></pre>
        """
        help_texts = {
            "headers": inspect.cleandoc(HEADERS_HELP_TEXT),
            "extra_config": inspect.cleandoc(EXTRA_CONFIG_HELP_TEXT),
        }


class ExternalIntegrationBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=ExternalIntegration.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    remote_url = forms.CharField(required=False, label="Remote URL")
    secrets_group = DynamicModelChoiceField(required=False, queryset=SecretsGroup.objects.all())
    verify_ssl = forms.NullBooleanField(required=False, label="Verify SSL", widget=BulkEditNullBooleanSelect)
    timeout = forms.IntegerField(required=False, min_value=0)
    extra_config = JSONField(required=False, widget=forms.Textarea, help_text="JSON data")
    http_method = forms.ChoiceField(
        required=False,
        label="HTTP Method",
        choices=add_blank_choice(WebhookHttpMethodChoices),
    )
    headers = JSONField(required=False, widget=forms.Textarea, help_text="Headers for the HTTP request")

    class Meta:
        model = ExternalIntegration
        nullable_fields = ["extra_config", "secrets_group", "headers"]


class ExternalIntegrationFilterForm(NautobotFilterForm):
    model = ExternalIntegration
    q = forms.CharField(required=False, label="Search")
    secrets_group = DynamicModelMultipleChoiceField(
        queryset=SecretsGroup.objects.all(), to_field_name="name", required=False
    )


#
# Git repositories and other data sources
#


def get_git_datasource_content_choices():
    return get_datasource_content_choices("extras.gitrepository")


class PasswordInputWithPlaceholder(forms.PasswordInput):
    """PasswordInput that is populated with a placeholder value if any existing value is present."""

    def __init__(self, attrs=None, placeholder="", render_value=False):
        if placeholder:
            render_value = True
        self._placeholder = placeholder
        super().__init__(attrs=attrs, render_value=render_value)

    def get_context(self, name, value, attrs):
        if value:
            value = self._placeholder
        return super().get_context(name, value, attrs)


class GitRepositoryForm(NautobotModelForm):
    slug = SlugField(help_text="Filesystem-friendly unique shorthand")

    remote_url = LaxURLField(
        required=True,
        label="Remote URL",
        help_text="Only http:// and https:// URLs are presently supported",
    )

    secrets_group = DynamicModelChoiceField(required=False, queryset=SecretsGroup.objects.all())

    provided_contents = forms.MultipleChoiceField(
        required=False,
        label="Provides",
        choices=get_git_datasource_content_choices,
    )

    class Meta:
        model = GitRepository
        fields = [
            "name",
            "slug",
            "remote_url",
            "branch",
            "secrets_group",
            "provided_contents",
            "tags",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.present_in_database:
            self.fields["slug"].widget.attrs["readonly"] = True

    def save(self, commit=True):
        instance = super().save(commit=commit)

        # TODO(jathan): Move sync() call out of the form and into the view. However, in v2 UI this
        # probably just goes away since UI views will be making API calls. For now, the user is
        # magically stored on the instance by the view code.
        if commit:
            # Set dryrun if that button was clicked in the UI, otherwise perform a normal sync.
            dry_run = "_dryrun_create" in self.data or "_dryrun_update" in self.data
            instance.sync(user=instance.user, dry_run=dry_run)

        return instance


class GitRepositoryBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=GitRepository.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    remote_url = LaxURLField(
        label="Remote URL",
        required=False,
    )
    branch = forms.CharField(
        required=False,
    )
    secrets_group = DynamicModelChoiceField(required=False, queryset=SecretsGroup.objects.all())

    class Meta:
        model = GitRepository
        nullable_fields = ["secrets_group"]


class GitRepositoryFilterForm(BootstrapMixin, forms.Form):
    model = GitRepository
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    branch = forms.CharField(required=False)
    provided_contents = forms.ChoiceField(
        required=False,
        label="Provides",
        choices=add_blank_choice(get_git_datasource_content_choices()),
    )


#
# GraphQL saved queries
#


class GraphQLQueryForm(BootstrapMixin, forms.ModelForm):
    query = TextField()

    class Meta:
        model = GraphQLQuery
        fields = (
            "name",
            "query",
        )

    def get_action_url(self):
        return reverse("extras:graphqlquery_add")


class GraphQLQueryFilterForm(BootstrapMixin, forms.Form):
    model = GraphQLQuery
    q = forms.CharField(required=False, label="Search")


#
# Image attachments
#


class ImageAttachmentForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = ImageAttachment
        fields = [
            "name",
            "image",
        ]
        widgets = {
            "image": ClearableFileInput,
        }


#
# Jobs
#


class JobForm(BootstrapMixin, forms.Form):
    """
    This form is used to render the user input fields for a Job class. Its fields are dynamically
    controlled by the job definition. See `nautobot.extras.jobs.BaseJob.as_form`
    """


class JobEditForm(NautobotModelForm):
    job_queues = DynamicModelMultipleChoiceField(
        label="Job Queues",
        queryset=JobQueue.objects.all(),
    )
    default_job_queue = DynamicModelChoiceField(
        label="Default Job Queue",
        queryset=JobQueue.objects.all(),
        help_text="The default job queue to route this job to",
        required=False,
    )

    class Meta:
        model = Job
        fields = [
            "enabled",
            "name_override",
            "name",
            "grouping_override",
            "grouping",
            "description_override",
            "description",
            "dryrun_default_override",
            "dryrun_default",
            "hidden_override",
            "hidden",
            "approval_required_override",
            "approval_required",
            "soft_time_limit_override",
            "soft_time_limit",
            "time_limit_override",
            "time_limit",
            "has_sensitive_variables_override",
            "has_sensitive_variables",
            "job_queues_override",
            "job_queues",
            "default_job_queue_override",
            "default_job_queue",
            "is_singleton",
            "is_singleton_override",
            "tags",
        ]

    def clean(self):
        """
        For all overridable fields, if they aren't marked as overridden, revert them to the underlying value if known.
        """
        from nautobot.extras.jobs import get_job  # avoid circular import

        cleaned_data = super().clean() or self.cleaned_data
        job_class = get_job(self.instance.class_path, reload=True)
        if job_class is not None:
            for field_name in JOB_OVERRIDABLE_FIELDS:
                if not cleaned_data.get(f"{field_name}_override", False):
                    cleaned_data[field_name] = getattr(job_class, field_name)
            # Get default Job Queue first
            if not cleaned_data.get("default_job_queue_override", False):
                meta_task_queues = getattr(job_class, "task_queues", []) or [settings.CELERY_TASK_DEFAULT_QUEUE]
                cleaned_data["default_job_queue"], _ = JobQueue.objects.get_or_create(
                    name=meta_task_queues[0], defaults={"queue_type": JobQueueTypeChoices.TYPE_CELERY}
                )
            default_job_queue = cleaned_data["default_job_queue"]
            # Include the default Job Queue in the Job Queues selection
            if not cleaned_data.get("job_queues_override", False):
                names = getattr(job_class, "task_queues", []) or [settings.CELERY_TASK_DEFAULT_QUEUE]
            else:
                names = list(cleaned_data["job_queues"].values_list("name", flat=True))
            names += [default_job_queue]
            cleaned_data["job_queues"] = JobQueue.objects.filter(name__in=names)

        return cleaned_data

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)
        instance.job_queues.set(self.cleaned_data["job_queues"])
        return instance


class JobBulkEditForm(NautobotBulkEditForm):
    """Bulk edit form for `Job` objects."""

    pk = forms.ModelMultipleChoiceField(
        queryset=Job.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    grouping = forms.CharField(
        required=False,
        help_text="Human-readable grouping that this job belongs to",
    )
    description = forms.CharField(
        max_length=CHARFIELD_MAX_LENGTH,
        required=False,
        help_text="Markdown formatting and a limited subset of HTML are supported",
    )
    enabled = forms.NullBooleanField(
        required=False, widget=BulkEditNullBooleanSelect, help_text="Whether this job can be executed by users"
    )
    has_sensitive_variables = forms.NullBooleanField(
        required=False, widget=BulkEditNullBooleanSelect, help_text="Whether this job contains sensitive variables"
    )
    approval_required = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect,
        help_text="Whether the job requires approval from another user before running",
    )
    hidden = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect,
        help_text="Whether the job defaults to not being shown in the UI",
    )
    dryrun_default = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect,
        help_text="Whether the job defaults to running with dryrun argument set to true",
    )
    soft_time_limit = forms.FloatField(
        required=False,
        validators=[MinValueValidator(0)],
        help_text="Maximum runtime in seconds before the job will receive a <code>SoftTimeLimitExceeded</code> "
        "exception.<br>Set to 0 to use Nautobot system default",
    )
    time_limit = forms.FloatField(
        required=False,
        validators=[MinValueValidator(0)],
        help_text="Maximum runtime in seconds before the job will be forcibly terminated."
        "<br>Set to 0 to use Nautobot system default",
    )
    job_queues = DynamicModelMultipleChoiceField(
        label="Job Queues",
        queryset=JobQueue.objects.all(),
        required=False,
        help_text="Job Queue instances that this job can run on",
    )
    default_job_queue = DynamicModelChoiceField(
        label="Default Job Queue",
        queryset=JobQueue.objects.all(),
        required=False,
        help_text="Default Job Queue the job runs on if no Job Queue is specified",
    )
    is_singleton = forms.NullBooleanField(
        required=False,
        widget=BulkEditNullBooleanSelect,
        help_text="Whether this job should fail to run if another instance of this job is already running",
    )
    # Flags to indicate whether the above properties are inherited from the source code or overridden by the database
    # Text field overrides
    clear_grouping_override = forms.BooleanField(
        required=False,
        help_text="If checked, groupings will be reverted to the default values defined in each Job's source code",
    )
    clear_description_override = forms.BooleanField(
        required=False,
        help_text="If checked, descriptions will be reverted to the default values defined in each Job's source code",
    )
    clear_soft_time_limit_override = forms.BooleanField(
        required=False,
        help_text="If checked, soft time limits will be reverted to the default values defined in each Job's source code",
    )
    clear_time_limit_override = forms.BooleanField(
        required=False,
        help_text="If checked, time limits will be reverted to the default values defined in each Job's source code",
    )
    clear_job_queues_override = forms.BooleanField(
        required=False,
        help_text="If checked, the selected job queues will be reverted to the default values defined in each Job's source code",
    )
    clear_default_job_queue_override = forms.BooleanField(
        required=False,
        help_text="If checked, the default job queue will be reverted to the first value of task_queues defined in each Job's source code",
    )
    # Boolean overrides
    clear_approval_required_override = forms.BooleanField(
        required=False,
        help_text="If checked, the values of approval required will be reverted to the default values defined in each Job's source code",
    )
    clear_dryrun_default_override = forms.BooleanField(
        required=False,
        help_text="If checked, the values of dryrun default will be reverted to the default values defined in each Job's source code",
    )
    clear_hidden_override = forms.BooleanField(
        required=False,
        help_text="If checked, the values of hidden will be reverted to the default values defined in each Job's source code",
    )
    clear_has_sensitive_variables_override = forms.BooleanField(
        required=False,
        help_text="If checked, the values of has sensitive variables will be reverted to the default values defined in each Job's source code",
    )
    is_singleton_override = forms.BooleanField(
        required=False,
        help_text="If checked, the values of is singleton will be reverted to the default values defined in each Job's source code",
    )

    class Meta:
        model = Job

    def post_save(self, obj):
        super().post_save(obj)

        cleaned_data = self.cleaned_data

        # Handle text related fields
        for overridable_field in JOB_OVERRIDABLE_FIELDS:
            override_field = overridable_field + "_override"
            clear_override_field = "clear_" + overridable_field + "_override"
            reset_override = cleaned_data.get(clear_override_field, False)
            override_value = cleaned_data.get(overridable_field)
            if reset_override:
                setattr(obj, override_field, False)
            elif not reset_override and override_value not in [None, ""]:
                setattr(obj, override_field, True)
                setattr(obj, overridable_field, override_value)

        # Handle job queues
        clear_override_field = "clear_job_queues_override"
        reset_override = cleaned_data.get(clear_override_field, False)
        if reset_override:
            meta_task_queues = obj.job_class.task_queues
            job_queues = []
            for queue_name in meta_task_queues:
                try:
                    job_queues.append(JobQueue.objects.get(name=queue_name))
                except JobQueue.DoesNotExist:
                    # Do we want to create the Job Queue for the users here if we do not have it in the database?
                    pass
            obj.job_queues_override = False
            obj.job_queues.set(job_queues)
        elif cleaned_data["job_queues"]:
            obj.job_queues_override = True

        # Handle default job queue
        clear_override_field = "clear_default_job_queue_override"
        reset_override = cleaned_data.get(clear_override_field, False)
        if reset_override:
            meta_task_queues = obj.job_class.task_queues
            obj.default_job_queue_override = False
            obj.default_job_queue, _ = JobQueue.objects.get_or_create(
                name=meta_task_queues[0] if meta_task_queues else settings.CELERY_TASK_DEFAULT_QUEUE
            )
        elif cleaned_data["default_job_queue"]:
            obj.default_job_queue_override = True

        obj.validated_save()


class JobFilterForm(BootstrapMixin, forms.Form):
    model = Job
    q = forms.CharField(required=False, label="Search")
    installed = forms.NullBooleanField(
        initial=True,
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    has_sensitive_variables = forms.NullBooleanField(
        required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES)
    )
    dryrun_default = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    hidden = forms.NullBooleanField(
        initial=False,
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    read_only = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    approval_required = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    is_job_hook_receiver = forms.NullBooleanField(
        initial=False,
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    is_job_button_receiver = forms.NullBooleanField(
        initial=False,
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tags = TagFilterField(model)


class JobHookBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=JobHook.objects.all(), widget=forms.MultipleHiddenInput())
    job = DynamicModelChoiceField(
        queryset=Job.objects.all(),
        query_params={"is_job_hook_receiver": True},
        required=False,
        label="Job",
    )
    enabled = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    type_create = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    type_update = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    type_delete = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    add_content_types = MultipleContentTypeField(
        queryset=ChangeLoggedModelsQuery().as_queryset(),
        required=False,
        label="Add Content Type(s)",
    )

    remove_content_types = MultipleContentTypeField(
        queryset=ChangeLoggedModelsQuery().as_queryset(),
        required=False,
        label="Remove Content Type(s)",
    )

    class Meta:
        model = JobHook
        fields = (
            "job",
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
            "add_content_types",
            "remove_content_types",
        )


class JobHookForm(BootstrapMixin, forms.ModelForm):
    content_types = MultipleContentTypeField(
        queryset=ChangeLoggedModelsQuery().as_queryset(), required=True, label="Content Type(s)"
    )
    job = DynamicModelChoiceField(
        queryset=Job.objects.filter(is_job_hook_receiver=True),
        query_params={"is_job_hook_receiver": True},
    )

    class Meta:
        model = JobHook
        fields = (
            "name",
            "content_types",
            "job",
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
        )

    def clean(self):
        data = super().clean()

        conflicts = JobHook.check_for_conflicts(
            instance=self.instance,
            content_types=self.cleaned_data.get("content_types"),
            job=self.cleaned_data.get("job"),
            type_create=self.cleaned_data.get("type_create"),
            type_update=self.cleaned_data.get("type_update"),
            type_delete=self.cleaned_data.get("type_delete"),
        )

        if conflicts:
            raise ValidationError(conflicts)

        return data


class JobHookFilterForm(BootstrapMixin, forms.Form):
    model = JobHook
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        queryset=ChangeLoggedModelsQuery().as_queryset(),
        choices_as_strings=True,
        required=False,
        label="Content Type(s)",
    )
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    job = DynamicModelMultipleChoiceField(
        label="Job",
        queryset=Job.objects.all(),
        required=False,
        to_field_name="name",
        widget=APISelectMultiple(api_url="/api/extras/jobs/"),
    )
    type_create = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    type_update = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    type_delete = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))


class JobQueueBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=JobQueue.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    queue_type = forms.ChoiceField(
        choices=JobQueueTypeChoices,
        help_text="The job can either run immediately, once in the future, or on a recurring schedule.",
        label="Type",
        required=False,
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
    )
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)

    class Meta:
        model = JobQueue
        nullable_fields = [
            "description",
            "tenant",
        ]


class JobQueueFilterForm(NautobotFilterForm):
    model = JobQueue
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    jobs = DynamicModelMultipleChoiceField(queryset=Job.objects.all(), required=False)
    queue_type = forms.MultipleChoiceField(
        choices=JobQueueTypeChoices,
        required=False,
        widget=StaticSelect2Multiple(),
    )
    tenant = DynamicModelMultipleChoiceField(queryset=Tenant.objects.all(), to_field_name="name", required=False)
    tags = TagFilterField(model)


class JobQueueForm(NautobotModelForm):
    name = forms.CharField(required=True, max_length=CHARFIELD_MAX_LENGTH)
    queue_type = forms.ChoiceField(
        choices=JobQueueTypeChoices,
        label="Queue Type",
    )
    tenant = DynamicModelChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
    )
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    tags = DynamicModelMultipleChoiceField(queryset=Tag.objects.all(), required=False)

    class Meta:
        model = JobQueue
        fields = ("name", "queue_type", "description", "tenant", "tags")


class JobScheduleForm(BootstrapMixin, forms.Form):
    """
    This form is rendered alongside the JobForm but deals specifically with the fields needed to either
    execute the job immediately, or schedule it for later. Each field name is prefixed with an underscore
    because in the POST body, they share a namespace with the JobForm which includes fields defined by the
    job author, so the underscore prefix helps to avoid name collisions.
    """

    _schedule_type = forms.ChoiceField(
        choices=JobExecutionType,
        help_text="The job can either run immediately, once in the future, or on a recurring schedule.",
        label="Type",
    )
    _schedule_name = forms.CharField(
        required=False,
        label="Schedule name",
        help_text="Name for the job schedule.",
    )
    _schedule_start_time = forms.DateTimeField(
        required=False,
        label="Starting date and time",
        widget=DateTimePicker(),
    )
    _recurrence_custom_time = forms.CharField(
        required=False,
        label="Crontab",
        help_text="Custom crontab syntax (* * * * *)",
    )

    def clean(self):
        """
        Validate all required information is present if the job needs to be scheduled
        """
        cleaned_data = super().clean()

        if "_schedule_type" in cleaned_data and cleaned_data.get("_schedule_type") != JobExecutionType.TYPE_IMMEDIATELY:
            if not cleaned_data.get("_schedule_name"):
                raise ValidationError({"_schedule_name": "Please provide a name for the job schedule."})

            if (
                not cleaned_data.get("_schedule_start_time")
                and cleaned_data.get("_schedule_type") != JobExecutionType.TYPE_CUSTOM
            ) or (
                cleaned_data.get("_schedule_start_time")
                and cleaned_data.get("_schedule_start_time") < ScheduledJob.earliest_possible_time()
            ):
                raise ValidationError(
                    {
                        "_schedule_start_time": "Please enter a valid date and time greater than or equal to the current date and time."
                    }
                )

            if cleaned_data.get("_schedule_type") == JobExecutionType.TYPE_CUSTOM:
                try:
                    ScheduledJob.get_crontab(cleaned_data.get("_recurrence_custom_time"))
                except Exception as e:
                    raise ValidationError({"_recurrence_custom_time": e})

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # setting the help_text for `_schedule_start_time` here instead of in the field definition
        # because Django needs to be fully initialized before we can accurately retrieve the current timezone.
        self.fields[
            "_schedule_start_time"
        ].help_text = (
            f"The scheduled time is relative to the Nautobot configured timezone: {get_current_timezone_name()}."
        )


class JobResultFilterForm(BootstrapMixin, forms.Form):
    model = JobResult
    q = forms.CharField(required=False, label="Search")
    job_model = DynamicModelMultipleChoiceField(
        label="Job",
        queryset=Job.objects.all(),
        required=False,
        to_field_name="name",
        widget=APISelectMultiple(api_url="/api/extras/jobs/"),
    )
    # 2.0 TODO(glenn) filtering by obj_type should be solved by dynamic filter form generation
    name = forms.CharField(required=False)
    user = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="User",
        widget=APISelectMultiple(
            api_url="/api/users/users/",
        ),
    )
    status = forms.MultipleChoiceField(
        choices=JobResultStatusChoices,
        required=False,
        widget=StaticSelect2Multiple(),
    )
    scheduled_job = DynamicModelMultipleChoiceField(
        label="Scheduled Job",
        queryset=ScheduledJob.objects.all(),
        required=False,
        to_field_name="name",
    )


class ScheduledJobFilterForm(BootstrapMixin, forms.Form):
    model = ScheduledJob
    q = forms.CharField(required=False, label="Search")
    name = forms.CharField(required=False)
    job_model = DynamicModelMultipleChoiceField(
        label="Job",
        queryset=Job.objects.all(),
        required=False,
        to_field_name="name",
        widget=APISelectMultiple(api_url="/api/extras/job-models/"),
    )
    total_run_count = forms.IntegerField(required=False)


#
# Job Button
#


class JobButtonForm(BootstrapMixin, forms.ModelForm):
    content_types = DynamicModelMultipleChoiceField(
        queryset=ContentType.objects.all(),
        label="Object Types",
        widget=APISelectMultiple(
            api_url="/api/extras/content-types/",
        ),
    )
    job = DynamicModelChoiceField(
        queryset=Job.objects.filter(is_job_button_receiver=True),
        query_params={"is_job_button_receiver": True},
    )

    class Meta:
        model = JobButton
        fields = (
            "content_types",
            "name",
            "job",
            "enabled",
            "text",
            "weight",
            "group_name",
            "button_class",
            "confirmation",
        )


class JobButtonBulkEditForm(BootstrapMixin, BulkEditForm):
    """Bulk edit form for `JobButton` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=JobButton.objects.all(), widget=forms.MultipleHiddenInput)
    content_types = DynamicModelMultipleChoiceField(
        queryset=ContentType.objects.all(),
        label="Object Types",
        widget=APISelectMultiple(
            api_url="/api/extras/content-types/",
        ),
        required=False,
    )
    enabled = forms.NullBooleanField(
        required=False, widget=BulkEditNullBooleanSelect, help_text="Whether this job button appears in the UI"
    )
    weight = forms.IntegerField(required=False)
    group_name = forms.CharField(required=False)

    class Meta:
        nullable_fields = ["group_name"]


class JobButtonFilterForm(BootstrapMixin, forms.Form):
    model = JobButton
    q = forms.CharField(required=False, label="Search")
    content_types = CSVContentTypeField(
        queryset=ContentType.objects.all(),
        required=False,
        label="Object Types",
    )


#
# Metadata
#


# MetadataChoice inline formset for use with providing dynamic rows when creating/editing choices
# for `MetadataType` objects in UI views. Fields/exclude must be set but since we're using all the
# fields we're just setting `exclude=()` here.
MetadataChoiceFormSet = inlineformset_factory(
    parent_model=MetadataType,
    model=MetadataChoice,
    exclude=(),
    extra=5,
    widgets={
        "value": forms.TextInput(attrs={"class": "form-control"}),
        "weight": forms.NumberInput(attrs={"class": "form-control"}),
    },
)


class MetadataTypeForm(NautobotModelForm):
    name = forms.CharField(required=True, max_length=CHARFIELD_MAX_LENGTH)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    content_types = MultipleContentTypeField(
        feature="metadata", help_text="The object(s) to which Metadata of this type can be applied."
    )

    class Meta:
        model = MetadataType
        fields = (
            "name",
            "description",
            "data_type",
            "content_types",
            "tags",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.initial.get("data_type"):
            self.fields["data_type"].disabled = True


class MetadataTypeFilterForm(NautobotFilterForm):
    model = MetadataType
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("metadata").get_query()),
        choices_as_strings=True,
        required=False,
        label="Content Type(s)",
    )
    tags = TagFilterField(model)


class MetadataTypeBulkEditForm(TagsBulkEditFormMixin, NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=MetadataType.objects.all(), widget=forms.MultipleHiddenInput)
    description = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)

    class Meta:
        nullable_fields = [
            "description",
        ]


class ObjectMetadataFilterForm(BootstrapMixin, forms.Form):
    model = ObjectMetadata
    q = forms.CharField(required=False, label="Search")
    contact = DynamicModelMultipleChoiceField(
        queryset=Contact.objects.all(),
        required=False,
    )
    team = DynamicModelMultipleChoiceField(
        queryset=Team.objects.all(),
        required=False,
    )
    assigned_object_type = MultipleContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("metadata").get_query()),
        choices_as_strings=True,
        required=False,
        label="Content Type(s)",
    )
    metadata_type = DynamicModelMultipleChoiceField(
        queryset=MetadataType.objects.all(),
        required=False,
    )


#
# Notes
#


class NoteForm(BootstrapMixin, forms.ModelForm):
    note = CommentField()

    class Meta:
        model = Note
        fields = ["assigned_object_type", "assigned_object_id", "note"]
        widgets = {
            "assigned_object_type": forms.HiddenInput,
            "assigned_object_id": forms.HiddenInput,
        }


class NoteFilterForm(BootstrapMixin, forms.Form):
    model = Note
    q = forms.CharField(required=False, label="Search")

    assigned_object_type_id = DynamicModelMultipleChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        label="Object Type",
        widget=APISelectMultiple(
            api_url="/api/extras/content-types/",
        ),
    )


#
# Filter form for local config context data
#


class LocalContextFilterForm(forms.Form):
    local_config_context_data = forms.NullBooleanField(
        required=False,
        label="Has local config context data",
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    local_config_context_schema = DynamicModelMultipleChoiceField(
        queryset=ConfigContextSchema.objects.all(), to_field_name="name", required=False
    )


#
# Model form for local config context data
#


class LocalContextModelForm(forms.ModelForm):
    local_config_context_schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), required=False)
    local_config_context_data = JSONField(required=False, label="")


class LocalContextModelBulkEditForm(BulkEditForm):
    local_config_context_schema = DynamicModelChoiceField(queryset=ConfigContextSchema.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # append nullable fields
        self.nullable_fields.append("local_config_context_schema")


#
# Change logging
#


class ObjectChangeFilterForm(BootstrapMixin, forms.Form):
    model = ObjectChange
    q = forms.CharField(required=False, label="Search")
    time__gte = forms.DateTimeField(label="After", required=False, widget=DateTimePicker())
    time__lte = forms.DateTimeField(label="Before", required=False, widget=DateTimePicker())
    action = forms.ChoiceField(
        choices=add_blank_choice(ObjectChangeActionChoices),
        required=False,
        widget=StaticSelect2(),
    )
    user_id = DynamicModelMultipleChoiceField(
        queryset=get_user_model().objects.all(),
        required=False,
        label="User",
        widget=APISelectMultiple(
            api_url="/api/users/users/",
        ),
    )
    changed_object_type_id = DynamicModelMultipleChoiceField(
        queryset=ContentType.objects.all(),
        required=False,
        label="Object Type",
        widget=APISelectMultiple(
            api_url="/api/extras/content-types/",
        ),
    )


#
# Relationship
#


class RelationshipBulkEditForm(BootstrapMixin, CustomFieldModelBulkEditFormMixin, NoteModelBulkEditFormMixin):
    pk = forms.ModelMultipleChoiceField(queryset=Relationship.objects.all(), widget=forms.MultipleHiddenInput())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    type = forms.ChoiceField(
        required=False,
        label="type",
        choices=add_blank_choice(RelationshipTypeChoices),
    )
    source_hidden = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    destination_hidden = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    source_filter = JSONField(required=False, widget=forms.Textarea, help_text="Filter for the source")
    destination_filter = JSONField(required=False, widget=forms.Textarea, help_text="Filter for the destination")
    source_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()), required=False
    )
    destination_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()), required=False
    )
    source_label = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    destination_label = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    advanced_ui = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)

    class Meta:
        model = Relationship
        fields = [
            "description",
            "type",
            "source_hidden",
            "destination_hidden",
            "source_filter",
            "destination_filter",
            "source_type",
            "destination_type",
            "source_label",
            "destination_label",
            "advanced_ui",
        ]


class RelationshipForm(BootstrapMixin, forms.ModelForm):
    key = SlugField(
        help_text="Internal name of this relationship. Please use underscores rather than dashes.",
        label="Key",
        max_length=CHARFIELD_MAX_LENGTH,
        slug_source="label",
    )
    source_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()).order_by("app_label", "model"),
        help_text="The source object type to which this relationship applies.",
    )
    source_filter = JSONField(
        required=False,
        help_text="Filterset filter matching the applicable source objects of the selected type.<br>"
        'Enter in <a href="https://json.org/">JSON</a> format.',
    )
    destination_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("relationships").get_query()).order_by("app_label", "model"),
        help_text="The destination object type to which this relationship applies.",
    )
    destination_filter = JSONField(
        required=False,
        help_text="Filterset filter matching the applicable destination objects of the selected type.<br>"
        'Enter in <a href="https://json.org/">JSON</a> format.',
    )

    class Meta:
        model = Relationship
        fields = [
            "label",
            "key",
            "description",
            "type",
            "required_on",
            "advanced_ui",
            "source_type",
            "source_label",
            "source_hidden",
            "source_filter",
            "destination_type",
            "destination_label",
            "destination_hidden",
            "destination_filter",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.present_in_database:
            self.fields["key"].widget.attrs["readonly"] = True

    def save(self, commit=True):
        # TODO add support for owner when a CR is created in the UI
        obj = super().save(commit)

        return obj


class RelationshipFilterForm(BootstrapMixin, forms.Form):
    model = Relationship

    type = forms.MultipleChoiceField(choices=RelationshipTypeChoices, required=False, widget=StaticSelect2Multiple())

    source_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Source Type"
    )

    destination_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Destination Type"
    )


class RelationshipAssociationFilterForm(BootstrapMixin, forms.Form):
    model = RelationshipAssociation

    relationship = DynamicModelMultipleChoiceField(
        queryset=Relationship.objects.all(),
        to_field_name="key",
        required=False,
    )

    source_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Source Type"
    )

    destination_type = MultipleContentTypeField(
        feature="relationships", choices_as_strings=True, required=False, label="Destination Type"
    )


#
# Role
#


class RoleForm(NautobotModelForm):
    """Generic create/update form for `Role` objects."""

    content_types = MultipleContentTypeField(
        required=False,
        label="Content Type(s)",
        queryset=RoleModelsQuery().as_queryset(),
    )

    class Meta:
        model = Role
        widgets = {"color": ColorSelect()}
        fields = ["name", "weight", "description", "content_types", "color"]


class RoleBulkEditForm(NautobotBulkEditForm):
    """Bulk edit/delete form for `Role` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=Role.objects.all(), widget=forms.MultipleHiddenInput)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)
    weight = forms.IntegerField(required=False)
    add_content_types = MultipleContentTypeField(
        queryset=RoleModelsQuery().as_queryset(), required=False, label="Add Content Type(s)"
    )
    remove_content_types = MultipleContentTypeField(
        queryset=RoleModelsQuery().as_queryset(), required=False, label="Remove Content Type(s)"
    )

    class Meta:
        nullable_fields = ["weight"]


class RoleFilterForm(NautobotFilterForm):
    model = Role
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        queryset=RoleModelsQuery().as_queryset(),
        required=False,
        choices_as_strings=True,
        label="Content Type(s)",
    )


#
# Secrets
#


class SecretsGroupBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=SecretsGroup.objects.all(), widget=forms.MultipleHiddenInput())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        model = SecretsGroup


def provider_choices():
    return sorted([(slug, provider.name) for slug, provider in registry["secrets_providers"].items()])


class SecretForm(NautobotModelForm):
    """Create/update form for `Secret` objects."""

    provider = forms.ChoiceField(choices=provider_choices, widget=StaticSelect2())

    parameters = JSONField(help_text='Enter parameters in <a href="https://json.org/">JSON</a> format.')

    class Meta:
        model = Secret
        fields = [
            "name",
            "description",
            "provider",
            "parameters",
            "tags",
        ]


def provider_choices_with_blank():
    return add_blank_choice(sorted([(slug, provider.name) for slug, provider in registry["secrets_providers"].items()]))


class SecretFilterForm(NautobotFilterForm):
    model = Secret
    q = forms.CharField(required=False, label="Search")
    provider = forms.MultipleChoiceField(
        choices=provider_choices_with_blank, widget=StaticSelect2Multiple(), required=False
    )
    tags = TagFilterField(model)


# Inline formset for use with providing dynamic rows when creating/editing assignments of Secrets to SecretsGroups.
SecretsGroupAssociationFormSet = inlineformset_factory(
    parent_model=SecretsGroup,
    model=SecretsGroupAssociation,
    fields=("access_type", "secret_type", "secret"),
    extra=5,
    widgets={
        "access_type": StaticSelect2,
        "secret_type": StaticSelect2,
        "secret": APISelect(api_url="/api/extras/secrets/"),
    },
)


class SecretsGroupForm(NautobotModelForm):
    """Create/update form for `SecretsGroup` objects."""

    class Meta:
        model = SecretsGroup
        fields = [
            "name",
            "description",
        ]


class SecretsGroupFilterForm(NautobotFilterForm):
    model = SecretsGroup
    q = forms.CharField(required=False, label="Search")


#
# Statuses
#


class StatusForm(NautobotModelForm):
    """Generic create/update form for `Status` objects."""

    content_types = MultipleContentTypeField(feature="statuses", label="Content Type(s)")

    class Meta:
        model = Status
        widgets = {"color": ColorSelect()}
        fields = ["name", "description", "content_types", "color"]


class StatusFilterForm(NautobotFilterForm):
    """Filtering/search form for `Status` objects."""

    model = Status
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        feature="statuses", choices_as_strings=True, required=False, label="Content Type(s)"
    )
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())


class StatusBulkEditForm(NautobotBulkEditForm):
    """Bulk edit/delete form for `Status` objects."""

    pk = forms.ModelMultipleChoiceField(queryset=Status.objects.all(), widget=forms.MultipleHiddenInput)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())
    add_content_types = MultipleContentTypeField(feature="statuses", required=False, label="Add Content Type(s)")
    remove_content_types = MultipleContentTypeField(feature="statuses", required=False, label="Remove Content Type(s)")

    class Meta:
        nullable_fields = []


#
# Tags
#


class TagForm(NautobotModelForm):
    content_types = ModelMultipleChoiceField(
        label="Content Type(s)",
        queryset=TaggableClassesQuery().as_queryset(),
    )

    class Meta:
        model = Tag
        fields = ["name", "color", "description", "content_types"]

    def clean(self):
        data = super().clean()

        if self.instance.present_in_database:
            # check if tag is assigned to any of the removed content_types
            content_types_id = [content_type.id for content_type in self.cleaned_data.get("content_types", [])]
            errors = self.instance.validate_content_types_removal(content_types_id)

            if errors:
                raise ValidationError(errors)

        return data


class TagFilterForm(NautobotFilterForm):
    model = Tag
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        choices_as_strings=True,
        required=False,
        label="Content Type(s)",
        queryset=TaggableClassesQuery().as_queryset(),
    )


class TagBulkEditForm(NautobotBulkEditForm):
    pk = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(), widget=forms.MultipleHiddenInput)
    color = forms.CharField(max_length=6, required=False, widget=ColorSelect())
    description = forms.CharField(max_length=CHARFIELD_MAX_LENGTH, required=False)

    class Meta:
        nullable_fields = ["description"]


#
# Webhooks
#
class WebhookBulkEditForm(BootstrapMixin, NoteModelBulkEditFormMixin):
    """Bulk edit form for Webhook objects."""

    pk = forms.ModelMultipleChoiceField(queryset=Webhook.objects.all(), widget=forms.MultipleHiddenInput())

    # Boolean fields
    enabled = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    type_create = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    type_update = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    type_delete = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)
    ssl_verification = forms.NullBooleanField(required=False, widget=BulkEditNullBooleanSelect)

    # Editable string fields
    payload_url = forms.CharField(required=False, max_length=500)
    secret = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    ca_file_path = forms.CharField(required=False, max_length=4096)
    http_content_type = forms.CharField(required=False, max_length=CHARFIELD_MAX_LENGTH)
    additional_headers = forms.CharField(required=False, widget=forms.Textarea)
    body_template = forms.CharField(required=False, widget=forms.Textarea)

    # Choice field
    http_method = forms.ChoiceField(
        required=False,
        choices=add_blank_choice(WebhookHttpMethodChoices.CHOICES),
    )

    add_content_types = MultipleContentTypeField(
        limit_choices_to=FeatureQuery("webhooks"), required=False, label="Add Content Type(s)"
    )
    remove_content_types = MultipleContentTypeField(
        limit_choices_to=FeatureQuery("webhooks"), required=False, label="Remove Content Type(s)"
    )

    class Meta:
        model = Webhook
        fields = (
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
            "http_method",
            "http_content_type",
            "additional_headers",
            "body_template",
            "ssl_verification",
            "ca_file_path",
            "payload_url",
            "secret",
            "add_content_types",
            "remove_content_types",
        )
        nullable_fields = ("additional_headers",)


class WebhookForm(BootstrapMixin, forms.ModelForm):
    content_types = MultipleContentTypeField(feature="webhooks", required=False, label="Content Type(s)")

    class Meta:
        model = Webhook
        fields = (
            "name",
            "content_types",
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
            "payload_url",
            "http_method",
            "http_content_type",
            "additional_headers",
            "body_template",
            "secret",
            "ssl_verification",
            "ca_file_path",
        )

    def clean(self):
        data = super().clean()

        conflicts = Webhook.check_for_conflicts(
            instance=self.instance,
            content_types=self.cleaned_data.get("content_types"),
            payload_url=self.cleaned_data.get("payload_url"),
            type_create=self.cleaned_data.get("type_create"),
            type_update=self.cleaned_data.get("type_update"),
            type_delete=self.cleaned_data.get("type_delete"),
        )

        if conflicts:
            raise ValidationError(conflicts)

        return data


class WebhookFilterForm(BootstrapMixin, forms.Form):
    model = Webhook
    q = forms.CharField(required=False, label="Search")
    content_types = MultipleContentTypeField(
        feature="webhooks", choices_as_strings=True, required=False, label="Content Type(s)"
    )
    type_create = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    type_update = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    type_delete = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
    enabled = forms.NullBooleanField(required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES))
