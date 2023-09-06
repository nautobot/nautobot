from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db.models.fields import TextField
from django.forms import ModelMultipleChoiceField, inlineformset_factory
from django.urls.base import reverse

from nautobot.core.utils.deprecation import class_deprecated_in_favor_of
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
    MultipleContentTypeField,
    SlugField,
    StaticSelect2,
    StaticSelect2Multiple,
    TagFilterField,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.dcim.models import Device, DeviceRedundancyGroup, DeviceType, Location, Platform
from nautobot.extras.choices import (
    JobExecutionType,
    JobResultStatusChoices,
    ObjectChangeActionChoices,
    RelationshipTypeChoices,
)
from nautobot.extras.constants import JOB_OVERRIDABLE_FIELDS
from nautobot.extras.datasources import get_datasource_content_choices
from nautobot.extras.models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomFieldChoice,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job,
    JobButton,
    JobHook,
    JobResult,
    Note,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Role,
    ScheduledJob,
    Secret,
    SecretsGroup,
    SecretsGroupAssociation,
    Status,
    Tag,
    Webhook,
)
from nautobot.extras.registry import registry
from nautobot.extras.utils import ChangeLoggedModelsQuery, FeatureQuery, RoleModelsQuery, TaggableClassesQuery
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
    RelationshipModelFormMixin,
)


__all__ = (
    "BaseDynamicGroupMembershipFormSet",
    "ComputedFieldForm",
    "ComputedFieldFilterForm",
    "ConfigContextForm",
    "ConfigContextBulkEditForm",
    "ConfigContextFilterForm",
    "ConfigContextSchemaForm",
    "ConfigContextSchemaBulkEditForm",
    "ConfigContextSchemaFilterForm",
    "CustomFieldForm",
    "CustomFieldModelCSVForm",
    "CustomFieldBulkCreateForm",  # 2.0 TODO remove this deprecated class
    "CustomFieldChoiceFormSet",
    "CustomLinkForm",
    "CustomLinkFilterForm",
    "DynamicGroupForm",
    "DynamicGroupFilterForm",
    "DynamicGroupMembershipFormSet",
    "ExportTemplateForm",
    "ExportTemplateFilterForm",
    "GitRepositoryForm",
    "GitRepositoryBulkEditForm",
    "GitRepositoryFilterForm",
    "GraphQLQueryForm",
    "GraphQLQueryFilterForm",
    "ImageAttachmentForm",
    "JobForm",
    "JobButtonForm",
    "JobButtonBulkEditForm",
    "JobButtonFilterForm",
    "JobEditForm",
    "JobFilterForm",
    "JobHookForm",
    "JobHookFilterForm",
    "JobScheduleForm",
    "JobResultFilterForm",
    "LocalContextFilterForm",
    "LocalContextModelForm",
    "LocalContextModelBulkEditForm",
    "NoteForm",
    "ObjectChangeFilterForm",
    "PasswordInputWithPlaceholder",
    "RelationshipForm",
    "RelationshipFilterForm",
    "RelationshipAssociationFilterForm",
    "RoleBulkEditForm",
    "RoleForm",
    "ScheduledJobFilterForm",
    "SecretForm",
    "SecretFilterForm",
    "SecretsGroupForm",
    "SecretsGroupFilterForm",
    "SecretsGroupAssociationFormSet",
    "StatusForm",
    "StatusFilterForm",
    "StatusBulkEditForm",
    "TagForm",
    "TagFilterForm",
    "TagBulkEditForm",
    "WebhookForm",
    "WebhookFilterForm",
)


#
# Computed Fields
#


class ComputedFieldForm(BootstrapMixin, forms.ModelForm):
    content_type = forms.ModelChoiceField(
        queryset=ContentType.objects.filter(FeatureQuery("custom_fields").get_query()).order_by("app_label", "model"),
        required=True,
        label="Content Type",
    )
    key = SlugField(
        label="Key",
        max_length=50,
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
    description = forms.CharField(required=False, max_length=100)

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
    description = forms.CharField(required=False, max_length=100)

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


class CustomFieldForm(BootstrapMixin, forms.ModelForm):
    label = forms.CharField(required=True, max_length=50, help_text="Name of the field as displayed to users.")
    key = SlugField(
        label="Key",
        max_length=50,
        slug_source="label",
        help_text="Internal name of this field. Please use underscores rather than dashes.",
    )
    description = forms.CharField(
        required=False,
        help_text="Also used as the help text when editing models using this custom field.<br>"
        '<a href="https://github.com/adam-p/markdown-here/wiki/Markdown-Cheatsheet" target="_blank">'
        "Markdown</a> syntax is supported.",
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

        if self.instance and self.instance.present_in_database:
            self.fields["key"].widget.attrs["readonly"] = True


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


#
# Custom Links
#


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


class DynamicGroupForm(NautobotModelForm):
    """DynamicGroup model form."""

    content_type = CSVContentTypeField(
        queryset=ContentType.objects.filter(FeatureQuery("dynamic_groups").get_query()).order_by("app_label", "model"),
        label="Content Type",
    )

    class Meta:
        model = DynamicGroup
        fields = [
            "name",
            "description",
            "content_type",
        ]


class DynamicGroupMembershipFormSetForm(forms.ModelForm):
    """DynamicGroupMembership model form for use inline on DynamicGroupFormSet."""

    group = DynamicModelChoiceField(
        queryset=DynamicGroup.objects.all(),
        query_params={"content_type": "$content_type"},
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


class DynamicGroupFilterForm(BootstrapMixin, forms.Form):
    """DynamicGroup filter form."""

    model = DynamicGroup
    q = forms.CharField(required=False, label="Search")
    content_type = MultipleContentTypeField(feature="dynamic_groups", choices_as_strings=True, label="Content Type")


#
# Export Templates
#


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


class GitRepositoryForm(BootstrapMixin, RelationshipModelFormMixin):
    slug = SlugField(help_text="Filesystem-friendly unique shorthand")

    remote_url = forms.URLField(
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
    remote_url = forms.CharField(
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


#
# Jobs
#


class JobForm(BootstrapMixin, forms.Form):
    """
    This form is used to render the user input fields for a Job class. Its fields are dynamically
    controlled by the job definition. See `nautobot.extras.jobs.BaseJob.as_form`
    """

    _profile = forms.BooleanField(
        required=False,
        initial=False,
        label="Profile job execution",
        help_text="Profiles the job execution using cProfile and outputs a report to /tmp/",
    )
    _task_queue = forms.ChoiceField(
        required=False,
        help_text="The task queue to route this job to",
        label="Task queue",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Move special fields to the end of the form
        for field in ["_task_queue", "_profile"]:
            value = self.fields.pop(field)
            self.fields[field] = value


class JobEditForm(NautobotModelForm):
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
            "task_queues_override",
            "task_queues",
            "tags",
        ]

    def clean(self):
        """
        For all overridable fields, if they aren't marked as overridden, revert them to the underlying value if known.
        """
        cleaned_data = super().clean() or self.cleaned_data
        job_class = self.instance.job_class
        if job_class is not None:
            for field_name in JOB_OVERRIDABLE_FIELDS:
                if not cleaned_data.get(f"{field_name}_override", False):
                    cleaned_data[field_name] = getattr(job_class, field_name)
        return cleaned_data


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


class JobHookForm(BootstrapMixin, forms.ModelForm):
    content_types = MultipleContentTypeField(
        queryset=ChangeLoggedModelsQuery().as_queryset(), required=True, label="Content Type(s)"
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
        help_text=f"The scheduled time is relative to the Nautobot configured timezone: {settings.TIME_ZONE}.",
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

    class Meta:
        model = JobButton
        fields = (
            "content_types",
            "name",
            "text",
            "job",
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
# Notes
#


class NoteForm(BootstrapMixin, forms.ModelForm):
    note = CommentField

    class Meta:
        model = Note
        fields = ["assigned_object_type", "assigned_object_id", "note"]
        widgets = {
            "assigned_object_type": forms.HiddenInput,
            "assigned_object_id": forms.HiddenInput,
        }


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


class RelationshipForm(BootstrapMixin, forms.ModelForm):
    key = SlugField(
        help_text="Internal name of this relationship. Please use underscores rather than dashes.",
        label="Key",
        max_length=50,
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
    content_types = MultipleContentTypeField(
        queryset=RoleModelsQuery().as_queryset(), required=False, label="Content Type(s)"
    )

    class Meta:
        nullable_fields = ["weight"]


#
# Secrets
#


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
    content_types = MultipleContentTypeField(feature="statuses", required=False, label="Content Type(s)")

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
    description = forms.CharField(max_length=200, required=False)

    class Meta:
        nullable_fields = ["description"]


#
# Webhooks
#


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
