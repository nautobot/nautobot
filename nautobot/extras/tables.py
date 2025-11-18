import logging
from textwrap import dedent

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html, format_html_join
import django_tables2 as tables
from django_tables2.utils import Accessor
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

from nautobot.core.tables import (
    ApprovalButtonsColumn,
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    ChoiceFieldColumn,
    ColorColumn,
    ColoredLabelColumn,
    ContentTypesColumn,
    LinkedCountColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.core.templatetags.helpers import HTML_NONE, render_boolean, render_json, render_markdown
from nautobot.tenancy.tables import TenantColumn

from .choices import JobResultStatusChoices, MetadataTypeDataTypeChoices
from .models import (
    ApprovalWorkflow,
    ApprovalWorkflowDefinition,
    ApprovalWorkflowStage,
    ApprovalWorkflowStageDefinition,
    ApprovalWorkflowStageResponse,
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    Contact,
    ContactAssociation,
    CustomField,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    ExternalIntegration,
    GitRepository,
    GraphQLQuery,
    ImageAttachment,
    Job as JobModel,
    JobButton,
    JobHook,
    JobLogEntry,
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
    TaggedItem,
    Team,
    Webhook,
)
from .registry import registry

logger = logging.getLogger(__name__)

APPROVAL_WORKFLOW_OBJECT = """
{% if record.object_under_review and record.object_under_review.get_absolute_url %}
    <a href="{{ record.object_under_review.get_absolute_url }}">{{ record.object_under_review }}</a>
{% else %}
    {{ record.object_under_review }}
{% endif %}
"""

ASSIGNED_OBJECT = """
{% load helpers %}
{{ record.assigned_object|hyperlinked_object }}
"""

CONTACT_OR_TEAM_ICON = """
{% if record.contact %}
<i class="mdi mdi-account" title="Contact"></i>
{% else %}
<i class="mdi mdi-account-group" title="Team"></i>
{% endif %}
"""

CONTACT_OR_TEAM = """
{% load helpers %}
{{ record.contact_or_team|hyperlinked_object:"name"}}
"""

PHONE = """
{% load helpers %}
{{ value|hyperlinked_phone_number }}
"""

EMAIL = """
{% load helpers %}
{{ value|hyperlinked_email }}
"""

TAGGED_ITEM = """
{% load helpers %}
{{ value|hyperlinked_object }}
"""

GITREPOSITORY_PROVIDES = """
<span class="text-nowrap">
{% for entry in datasource_contents %}
<span style="display: inline-block" title="{{ entry.name|title }}"
class="badge bg-{% if entry.content_identifier in record.provided_contents %}success{% else %}secondary{% endif %}">
<i class="mdi {{ entry.icon }}"></i></span>
{% endfor %}
</span>
"""

GITREPOSITORY_BUTTONS = """
<li>
    <button
        data-url="{% url 'extras:gitrepository_sync' pk=record.pk %}"
        type="submit"
        class="dropdown-item sync-repository{% if perms.extras.change_gitrepository %} text-primary"{% else %}" disabled{% endif %}
    >
        <span class="mdi mdi-source-branch-sync" aria-hidden="true"></span>
        Sync
    </button>
</li>
"""

IMAGEATTACHMENT_NAME = """
<span class="mdi mdi-file-image"></span>
<a class="image-preview" href="{{ record.image.url }}" target="_blank">{{ record }}</a>
"""

IMAGEATTACHMENT_SIZE = """{{ value|filesizeformat }}"""

JOB_BUTTONS = """
<li><a href="{% url 'extras:job' pk=record.pk %}" class="dropdown-item"><span class="mdi mdi-information-outline" aria-hidden="true"></span>Details</a></li>
<li><a href="{% url 'extras:jobresult_list' %}?job_model={{ record.name | urlencode }}" class="dropdown-item"><span class="mdi mdi-format-list-bulleted" aria-hidden="true"></span>Job Results</a></li>
"""

JOB_RESULT_BUTTONS = """
{% load helpers %}
{% if perms.extras.run_job %}
    {% if record.job_model and record.task_kwargs %}
        <li>
            <a href="{% url 'extras:job_run' pk=record.job_model.pk %}?kwargs_from_job_result={{ record.pk }}" class="dropdown-item text-success">
                <span class="mdi mdi-repeat" aria-hidden="true"></span>
                Re-run job with same arguments
            </a>
        </li>
    {% elif record.job_model is not None %}
        <li>
            <a href="{% url 'extras:job_run' pk=record.job_model.pk %}" class="dropdown-item text-primary">
                <span class="mdi mdi-play" aria-hidden="true"></span>
                Run job
            </a>
        </li>
    {% else %}
        <li>
            <a class="dropdown-item disabled" aria-disabled="true">
                <span class="mdi mdi-repeat-off" aria-hidden="true"></span>
                Job is not available, cannot be re-run
            </a>
        </li>
    {% endif %}
{% endif %}
"""

SCHEDULED_JOB_BUTTONS = """
<li><a href="{% url 'extras:jobresult_list' %}?scheduled_job={{ record.name | urlencode }}" class="dropdown-item"><span class="mdi mdi-format-list-bulleted" aria-hidden="true"></span>Job Results</a></li>
"""

OBJECTCHANGE_OBJECT = """
{% if record.changed_object and record.changed_object.get_absolute_url %}
    <a href="{{ record.changed_object.get_absolute_url }}">{{ record.object_repr }}</a>
{% else %}
    {{ record.object_repr }}
{% endif %}
"""

OBJECTCHANGE_REQUEST_ID = """
<a href="{% url 'extras:objectchange_list' %}?request_id={{ value }}">{{ value }}</a>
"""

MEMBERS_COUNT = """
{% load helpers %}
{% with urlname=record.model|validated_viewname:"list" %}
{% if urlname %}
    <a href="{% url urlname %}?dynamic_groups={{ record.name }}">{{ record.members_count }}</a>
{% else %}
    {{ record.members_count }}
{% endif %}
{% endwith %}
"""

# TODO: Webhook content_types in table order_by
WEBHOOK_CONTENT_TYPES = """
{{ value.all|join:", "|truncatewords:15 }}
"""

SCHEDULED_JOB_APPROVAL_QUEUE_BUTTONS = """
<div class="dropdown">
    <button class="btn dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
        <span class="mdi mdi-dots-vertical" aria-hidden="true"></span>
        <span class="visually-hidden">Toggle Dropdown</span>
    </button>
    <ul class="dropdown-menu dropdown-menu-end">
        <li>
            <button
                type="button"
                onClick="handleDetailPostAction('{% url 'extras:scheduledjob_approval_request_view' pk=record.pk %}', '_dry_run')"
                class="dropdown-item{% if perms.extras.run_job and record.job_model.supports_dryrun %} text-primary"{% else %}" disabled{% endif %}
            >
                <span class="mdi mdi-play" aria-hidden="true"></span>
                Dry Run
            </button>
        </li>
        <li>
            <button
                type="button"
                onClick="handleDetailPostAction('{% url 'extras:scheduledjob_approval_request_view' pk=record.pk %}', '_approve')"
                class="dropdown-item{% if perms.extras.run_job %} text-success"{% else %}" disabled{% endif %}
            >
                <span class="mdi mdi-check" aria-hidden="true"></span>
                Approve
            </button>
        </li>
        <li>
            <button
                type="button"
                onClick="handleDetailPostAction('{% url 'extras:scheduledjob_approval_request_view' pk=record.pk %}', '_deny')"
                class="dropdown-item{% if perms.extras.run_job %} text-danger"{% else %}" disabled{% endif %}
            >
                <span class="mdi mdi-close" aria-hidden="true"></span>
                Deny
            </button>
        </li>
    </ul>
</div>
"""

#
# Approval Workflow
#


class ApprovalWorkflowDefinitionTable(BaseTable):
    """Table for ApprovalWorkflowDefinitionTable list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(ApprovalWorkflowDefinition)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflowDefinition
        fields = (
            "pk",
            "name",
            "model_content_type",
        )
        default_columns = (
            "pk",
            "name",
            "model_content_type",
            "actions",
        )


class ApprovalWorkflowStageDefinitionTable(BaseTable):
    """Table for ApprovalWorkflowStageDefinition list view."""

    pk = ToggleColumn()
    approval_workflow_definition = tables.Column(linkify=True)
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(ApprovalWorkflowStageDefinition)

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflowStageDefinition
        fields = (
            "pk",
            "approval_workflow_definition",
            "sequence",
            "name",
            "min_approvers",
            "denial_message",
            "approver_group",
        )
        default_columns = (
            "pk",
            "approval_workflow_definition",
            "sequence",
            "name",
            "min_approvers",
            "denial_message",
            "approver_group",
            "actions",
        )


class ApprovalWorkflowTable(BaseTable):
    """Table for ApprovalWorkflow list view."""

    pk = ToggleColumn()
    approval_workflow_definition = tables.Column(linkify=True)
    object_under_review_content_type = tables.Column(verbose_name="Object Type Under Review")
    object_under_review = tables.TemplateColumn(
        template_code=APPROVAL_WORKFLOW_OBJECT, verbose_name="Object Under Review"
    )
    user = tables.TemplateColumn(
        template_code="{% if record.user %}{{record.user}}{% else %}{{ record.user_name }}{% endif %}",
        verbose_name="User",
    )
    current_state = ChoiceFieldColumn()
    actions = ApprovalButtonsColumn(ApprovalWorkflow, buttons=("detail", "changelog"))

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflow
        fields = (
            "pk",
            "object_under_review_content_type",
            "object_under_review",
            "user",
            "current_state",
            "approval_workflow_definition",
        )
        default_columns = (
            "pk",
            "object_under_review_content_type",
            "object_under_review",
            "user",
            "current_state",
            "approval_workflow_definition",
            "actions",
        )


class ApprovalChoiceFieldColumn(ChoiceFieldColumn):
    """
    Render a ChoiceField value just like ChoiceFieldColumn, but only if the record should be rendered.
    Otherwise, render a muted dash.
    """

    def render(self, *, record, bound_column, value):  # pylint: disable=arguments-differ  # tables2 varies its kwargs
        if record.should_render_state:
            return super().render(record=record, bound_column=bound_column, value=value)
        return HTML_NONE


class ApprovalWorkflowStageTable(BaseTable):
    """Table for ApprovalWorkflowStage list view."""

    pk = ToggleColumn()
    approval_workflow = tables.Column(linkify=True)
    approval_workflow_stage_definition = tables.Column(linkify=True)
    actions_needed = tables.TemplateColumn(
        template_code="""
        {% if record.remaining_approvals == 1 %}
        {{ record.remaining_approvals }} more approval needed
        {% elif record.remaining_approvals == 0 %}
        <span class="text-secondary">&mdash;</span>
        {% else %}
        {{ record.remaining_approvals }} more approvals needed
        {% endif %}
        """,
        orderable=False,
        verbose_name="Actions Needed",
    )
    state = ApprovalChoiceFieldColumn()
    actions = ApprovalButtonsColumn(
        ApprovalWorkflowStage, buttons=("detail", "changelog", "comment", "approve", "deny")
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflowStage
        fields = (
            "pk",
            "approval_workflow",
            "approval_workflow_stage_definition",
            "actions_needed",
            "state",
            "decision_date",
        )
        default_columns = (
            "pk",
            "approval_workflow",
            "approval_workflow_stage_definition",
            "actions_needed",
            "state",
            "decision_date",
            "actions",
        )


class ApproverDashboardTable(ApprovalWorkflowStageTable):
    """
    ApprovalWorkflowStageTable modified for the approver dashboard.
    """

    pk = ToggleColumn()
    approval_workflow = tables.TemplateColumn(
        template_code="<a href={{record.approval_workflow.get_absolute_url}}>{{ record.approval_workflow.approval_workflow_definition.name }}</a>",
        verbose_name="Workflow",
    )
    approval_workflow_stage = tables.TemplateColumn(
        template_code="<a href={{record.approval_workflow.get_absolute_url}}>{{ record.approval_workflow_stage_definition.name }}</a>",
        verbose_name="Current Stage",
    )
    approval_workflow__object_under_review_content_type = tables.Column(verbose_name="Object Type Under Review")
    object_under_review = tables.TemplateColumn(
        template_code="<a href={{record.approval_workflow.object_under_review.get_absolute_url }}>{{ record.approval_workflow.object_under_review }}</a>"
    )
    actions = ApprovalButtonsColumn(ApprovalWorkflowStage, buttons=("approve", "comment", "deny"))

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflowStage
        fields = (
            "pk",
            "approval_workflow__object_under_review_content_type",
            "object_under_review",
            "approval_workflow",
            "approval_workflow_stage",
            "actions_needed",
            "state",
            "decision_date",
        )
        default_columns = (
            "pk",
            "approval_workflow__object_under_review_content_type",
            "object_under_review",
            "approval_workflow",
            "approval_workflow_stage",
            "actions_needed",
            "state",
            "actions",
        )


class RelatedApprovalWorkflowStageTable(ApprovalWorkflowStageTable):
    """
    ApprovalWorkflowStageTable used in the detail view of ApprovalWorkflow detail view.
    """

    approval_workflow_stage = tables.TemplateColumn(
        template_code="<a href={{record.get_absolute_url}}>{{ record.approval_workflow_stage_definition.name }}</a>",
        verbose_name="Stage",
    )
    actions = ApprovalButtonsColumn(ApprovalWorkflowStage, buttons=("approve", "comment", "deny"))

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflowStage
        fields = (
            "pk",
            "approval_workflow",
            "approval_workflow_stage",
            "actions_needed",
            "state",
            "decision_date",
        )
        default_columns = (
            "pk",
            "approval_workflow",
            "approval_workflow_stage",
            "actions_needed",
            "state",
            "decision_date",
            "actions",
        )


class ApprovalWorkflowStageResponseTable(BaseTable):
    """Table for ApprovalWorkflowStageResponse list view."""

    pk = ToggleColumn()
    state = ChoiceFieldColumn()

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflowStageResponse
        fields = (
            "pk",
            "approval_workflow_stage",
            "user",
            "comments",
            "state",
        )
        default_columns = (
            "pk",
            "approval_workflow_stage",
            "user",
            "comments",
            "state",
        )

    def render_comments(self, value):
        return render_markdown(value)


class RelatedApprovalWorkflowStageResponseTable(ApprovalWorkflowStageResponseTable):
    """Table for ApprovalWorkflowStageResponse list view."""

    approval_workflow_stage = tables.TemplateColumn(
        template_code="<a href={{record.approval_workflow_stage.get_absolute_url}}>{{ record.approval_workflow_stage.approval_workflow_stage_definition.name }}</a>",
        verbose_name="Stage",
    )

    class Meta(BaseTable.Meta):
        """Meta attributes."""

        model = ApprovalWorkflowStageResponse
        fields = (
            "pk",
            "approval_workflow_stage",
            "user",
            "comments",
            "state",
        )
        default_columns = (
            "pk",
            "approval_workflow_stage",
            "user",
            "comments",
            "state",
            "actions",
        )


class ComputedFieldTable(BaseTable):
    pk = ToggleColumn()
    label = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        model = ComputedField
        fields = (
            "pk",
            "label",
            "key",
            "content_type",
            "description",
            "weight",
        )
        default_columns = (
            "pk",
            "label",
            "key",
            "content_type",
            "description",
        )


class ConfigContextTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    owner = tables.LinkColumn()
    is_active = BooleanColumn(verbose_name="Active")

    class Meta(BaseTable.Meta):
        model = ConfigContext
        fields = (
            "pk",
            "name",
            "owner",
            "weight",
            "is_active",
            "description",
            "locations",
            "roles",
            "platforms",
            "cluster_groups",
            "clusters",
            "tenant_groups",
            "tenants",
            "dynamic_groups",
        )
        default_columns = ("pk", "name", "weight", "is_active", "description")


class ConfigContextSchemaTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    owner = tables.LinkColumn()
    actions = ButtonsColumn(ConfigContextSchema)

    class Meta(BaseTable.Meta):
        model = ConfigContextSchema
        fields = (
            "pk",
            "name",
            "owner",
            "description",
            "actions",
        )
        default_columns = ("pk", "name", "description", "actions")


class ConfigContextSchemaValidationStateColumn(tables.Column):
    """
    Custom column that validates an instance's context data against a config context schema
    """

    def __init__(self, validator, data_field, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validator = validator
        self.data_field = data_field

    def render(self, *, record):  # pylint: disable=arguments-differ  # tables2 varies its kwargs
        data = getattr(record, self.data_field)
        try:
            self.validator.validate(data)
        except JSONSchemaValidationError as e:
            # Return a red x (like a boolean column) and the validation error message
            return render_boolean(False) + format_html('<span class="text-danger">{}</span>', e.message)

        # Return a green check (like a boolean column)
        return render_boolean(True)


class ContactTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    phone = tables.TemplateColumn(PHONE)
    tags = TagColumn(url_name="extras:contact_list")
    actions = ButtonsColumn(Contact)

    class Meta(BaseTable.Meta):
        model = Contact
        fields = (
            "pk",
            "name",
            "phone",
            "email",
            "address",
            "comments",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "phone",
            "email",
            "tags",
            "actions",
        )


class CustomFieldTable(BaseTable):
    pk = ToggleColumn()
    label = tables.Column(linkify=True)
    content_types = ContentTypesColumn(truncate_words=15)
    required = BooleanColumn()

    class Meta(BaseTable.Meta):
        model = CustomField
        fields = (
            "pk",
            "label",
            "key",
            "content_types",
            "type",
            "description",
            "required",
            "default",
            "weight",
        )
        default_columns = (
            "pk",
            "label",
            "key",
            "content_types",
            "type",
            "required",
            "weight",
        )

    def render_description(self, record):
        if record.description:
            return render_markdown(record.description)
        return self.default


class CustomLinkTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    new_window = BooleanColumn()

    class Meta(BaseTable.Meta):
        model = CustomLink
        fields = (
            "pk",
            "name",
            "content_type",
            "text",
            "target_url",
            "weight",
            "group_name",
            "button_class",
            "new_window",
        )
        default_columns = (
            "pk",
            "name",
            "content_type",
            "group_name",
            "weight",
        )


class DynamicGroupTable(BaseTable):
    """Base table for displaying dynamic groups in list view."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    members = tables.Column(accessor="count", verbose_name="Group Members", orderable=False)
    tenant = TenantColumn()
    tags = TagColumn(url_name="extras:dynamicgroup_list")
    actions = ButtonsColumn(DynamicGroup)

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        model = DynamicGroup
        fields = (
            "pk",
            "name",
            "description",
            "content_type",
            "group_type",
            "members",
            "tenant",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "content_type",
            "members",
            "actions",
        )

    def render_members(self, value, record):
        """Provide a filtered URL to the group members (if any)."""
        # Only linkify if there are members.
        if not value:
            return value
        return format_html('<a href="{}">{}</a>', record.get_group_members_url(), value)


class DynamicGroupMembershipTable(DynamicGroupTable):
    """Hybrid table for displaying info for both group and membership."""

    description = tables.Column(accessor="group__description")
    members = tables.Column(accessor="group__count", verbose_name="Group Members", orderable=False)

    class Meta(BaseTable.Meta):
        model = DynamicGroupMembership
        fields = (
            "pk",
            "operator",
            "name",
            "weight",
            "members",
            "description",
        )
        exclude = ("content_type", "actions", "group_type")


DESCENDANTS_LINK = """
{% load helpers %}
{% for node, depth in descendants_tree.items %}
    {% if record.pk == node %}
        {% for i in depth|as_range %}
            {% if not forloop.first %}
            <i class="mdi mdi-circle-small"></i>
            {% endif %}
        {% endfor %}
    {% endif %}
{% endfor %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


OPERATOR_LINK = """
{% load helpers %}
{% for node, depth in descendants_tree.items %}
    {% if record.pk == node %}
        {% for i in depth|as_range %}
            {% if not forloop.first %}
            <i class="mdi mdi-circle-small"></i>
            {% endif %}
        {% endfor %}
    {% endif %}
{% endfor %}
{{ record.get_operator_display }}
"""


class NestedDynamicGroupDescendantsTable(DynamicGroupMembershipTable):
    """
    Subclass of DynamicGroupMembershipTable used in detail views to show parenting hierarchy with dots.
    """

    operator = tables.TemplateColumn(template_code=OPERATOR_LINK)
    name = tables.TemplateColumn(template_code=DESCENDANTS_LINK)

    class Meta(DynamicGroupMembershipTable.Meta):
        pass


ANCESTORS_LINK = """
{% load helpers %}
{% for node in ancestors_tree %}
    {% if node.name == record.name %}
        {% for i in node.depth|as_range %}
            {% if not forloop.first %}
            <i class="mdi mdi-circle-small"></i>
            {% endif %}
        {% endfor %}
    {% endif %}
{% endfor %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


class NestedDynamicGroupAncestorsTable(DynamicGroupTable):
    """
    Subclass of DynamicGroupTable used in detail views to show parenting hierarchy with dots.
    """

    name = tables.TemplateColumn(template_code=ANCESTORS_LINK)
    actions = ButtonsColumn(DynamicGroup, pk_field="pk", buttons=("edit",))

    class Meta(DynamicGroupTable.Meta):
        fields = ["name", "members", "description", "actions"]
        exclude = ["content_type"]


class SavedViewTable(BaseTable):
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(SavedView)
    is_global_default = BooleanColumn()
    is_shared = BooleanColumn()

    class Meta(BaseTable.Meta):
        model = SavedView
        fields = (
            "name",
            "owner",
            "view",
            "config",
            "is_global_default",
            "is_shared",
            "actions",
        )
        default_columns = (
            "name",
            "owner",
            "view",
            "is_global_default",
            "actions",
        )

    def render_config(self, record):
        if record.config:
            return render_json(record.config, pretty_print=True)
        return self.default


class StaticGroupAssociationTable(BaseTable):
    """Table for list view of `StaticGroupAssociation` objects."""

    pk = ToggleColumn()
    dynamic_group = tables.Column(linkify=True)
    associated_object = tables.Column(linkify=True, verbose_name="Associated Object")
    actions = ButtonsColumn(StaticGroupAssociation, buttons=["changelog", "delete"])

    class Meta(BaseTable.Meta):
        model = StaticGroupAssociation
        fields = ["pk", "dynamic_group", "associated_object", "actions"]
        default_columns = ["pk", "dynamic_group", "associated_object", "actions"]


class ExportTemplateTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    owner = tables.LinkColumn()

    class Meta(BaseTable.Meta):
        model = ExportTemplate
        fields = (
            "pk",
            "owner",
            "content_type",
            "name",
            "description",
            "mime_type",
            "file_extension",
        )
        default_columns = (
            "pk",
            "name",
            "content_type",
            "file_extension",
        )


class ExternalIntegrationTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    remote_url = tables.Column()
    http_method = tables.Column()
    secrets_group = tables.Column(linkify=True)
    ca_file_path = tables.Column()
    tags = TagColumn(url_name="extras:externalintegration_list")

    class Meta(BaseTable.Meta):
        model = ExternalIntegration
        fields = (
            "pk",
            "name",
            "remote_url",
            "http_method",
            "secrets_group",
            "verify_ssl",
            "timeout",
            "ca_file_path",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "remote_url",
            "http_method",
            "secrets_group",
            "verify_ssl",
            "timeout",
            "tags",
        )


class GitRepositoryTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    remote_url = tables.Column(verbose_name="Remote URL")
    secrets_group = tables.Column(linkify=True)
    last_sync_time = tables.DateTimeColumn(
        empty_values=(), format=settings.SHORT_DATETIME_FORMAT, verbose_name="Sync Time"
    )

    last_sync_user = tables.Column(empty_values=(), verbose_name="Sync By")

    class JobResultColumn(tables.TemplateColumn):
        def render(self, record, table, value, bound_column, **kwargs):
            if hasattr(table, "context"):
                if str(record.pk) in table.context.get("job_results", {}):
                    table.context.update({"result": table.context["job_results"][str(record.pk)]})
                else:
                    table.context.update({"result": None})
            return super().render(record, table, value, bound_column, **kwargs)

    last_sync_status = JobResultColumn(template_name="extras/inc/job_label.html", verbose_name="Sync Status")
    provides = tables.TemplateColumn(GITREPOSITORY_PROVIDES)
    actions = ButtonsColumn(GitRepository, prepend_template=GITREPOSITORY_BUTTONS)

    class Meta(BaseTable.Meta):
        model = GitRepository
        fields = (
            "pk",
            "name",
            "slug",
            "remote_url",
            "branch",
            "secrets_group",
            "provides",
            "last_sync_time",
            "last_sync_user",
            "last_sync_status",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "remote_url",
            "branch",
            "provides",
            "last_sync_status",
            "actions",
        )

    def render_last_sync_time(self, record):
        if hasattr(self, "context"):
            if record.name in self.context.get("job_results", {}):
                return self.context["job_results"][record.name].date_done
        return self.default

    def render_last_sync_user(self, record):
        if hasattr(self, "context"):
            if record.name in self.context.get("job_results", {}):
                user = self.context["job_results"][record.name].user
                return user
        return self.default


class GitRepositoryBulkTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    remote_url = tables.Column(verbose_name="Remote URL")
    secrets_group = tables.Column(linkify=True)
    provides = tables.TemplateColumn(GITREPOSITORY_PROVIDES)

    class Meta(BaseTable.Meta):
        model = GitRepository
        fields = (
            "pk",
            "name",
            "remote_url",
            "branch",
            "secrets_group",
            "provides",
        )


class GraphQLQueryTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        model = GraphQLQuery
        fields = (
            "pk",
            "name",
        )


class ImageAttachmentTable(BaseTable):
    pk = ToggleColumn()
    name = tables.TemplateColumn(template_code=IMAGEATTACHMENT_NAME, verbose_name="Name")
    size = tables.TemplateColumn(template_code=IMAGEATTACHMENT_SIZE)
    created = tables.DateTimeColumn()
    actions = ButtonsColumn(ImageAttachment, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = ImageAttachment
        fields = ("pk", "name", "size", "created", "actions")


def log_object_link(value, record):
    return record.absolute_url or None


def log_entry_color_css(record):
    if record.log_level.lower() in ("failure", "error", "critical"):
        return "table-danger"
    return "table-" + record.log_level.lower()


class JobTable(BaseTable):
    pk = ToggleColumn()
    source = tables.Column()
    # grouping is used to, well, group the Jobs, so it isn't a column of its own.
    name = tables.Column(
        attrs={"a": {"class": "job_run", "title": "Run/Schedule"}},
        linkify=("extras:job_run", {"pk": tables.A("pk")}),
    )
    installed = BooleanColumn()
    enabled = BooleanColumn()
    has_sensitive_variables = BooleanColumn()
    description = tables.Column(accessor="description_first_line")
    dryrun_default = BooleanColumn()
    hidden = BooleanColumn()
    read_only = BooleanColumn()
    is_job_hook_receiver = BooleanColumn()
    is_job_button_receiver = BooleanColumn()
    supports_dryrun = BooleanColumn()
    soft_time_limit = tables.Column()
    time_limit = tables.Column()
    default_job_queue = tables.Column(linkify=True)
    job_queues_count = LinkedCountColumn(
        viewname="extras:jobqueue_list", url_params={"jobs": "pk"}, verbose_name="Job Queues"
    )
    last_run = tables.TemplateColumn(
        accessor="latest_result",
        template_code="""
            {% if value %}
                {{ value.date_created|date:SHORT_DATETIME_FORMAT }} by {{ value.user }}
            {% else %}
                <span class="text-secondary">Never</span>
            {% endif %}
        """,
        extra_context={"SHORT_DATETIME_FORMAT": settings.SHORT_DATETIME_FORMAT},
        linkify=lambda value: value.get_absolute_url() if value else None,
    )
    last_status = tables.TemplateColumn(
        template_code="{% include 'extras/inc/job_label.html' with result=record.latest_result %}",
    )
    tags = TagColumn(url_name="extras:job_list")
    actions = ButtonsColumn(JobModel, prepend_template=JOB_BUTTONS)

    def render_description(self, value):
        return render_markdown(value)

    def render_name(self, value):
        return format_html(
            '<span class="btn btn-primary btn-sm p-2 rounded-circle"><span class="mdi mdi-play"></span></span>{}',
            value,
        )

    class Meta(BaseTable.Meta):
        model = JobModel
        orderable = False
        fields = (
            "pk",
            "source",
            "name",
            "installed",
            "enabled",
            "has_sensitive_variables",
            "description",
            "dryrun_default",
            "hidden",
            "read_only",
            "is_job_hook_receiver",
            "is_job_button_receiver",
            "supports_dryrun",
            "soft_time_limit",
            "time_limit",
            "default_job_queue",
            "job_queues_count",
            "last_run",
            "last_status",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "enabled",
            "description",
            "last_run",
            "last_status",
            "actions",
        )


class JobHookTable(BaseTable):
    pk = ToggleColumn()
    enabled = BooleanColumn()
    name = tables.Column(linkify=True)
    content_types = tables.TemplateColumn(WEBHOOK_CONTENT_TYPES)
    job = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        model = JobHook
        fields = (
            "pk",
            "name",
            "content_types",
            "job",
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
        )
        default_columns = (
            "pk",
            "name",
            "content_types",
            "job",
            "enabled",
        )


class JobLogEntryTable(BaseTable):
    created = tables.DateTimeColumn(verbose_name="Time", format="Y-m-d H:i:s.u")
    grouping = tables.Column()
    log_level = tables.Column(
        verbose_name="Level",
        attrs={"td": {"class": "text-nowrap report-stats"}},
    )
    log_object = tables.Column(verbose_name="Object", linkify=log_object_link)
    message = tables.Column(
        attrs={"td": {"class": "nb-rendered-markdown"}},
    )

    def render_log_level(self, value):
        log_level = value.lower()
        # The css is bg-danger for failure items.
        if log_level in ["failure", "error", "critical"]:
            log_level = "danger"
        elif log_level == "debug":
            log_level = "secondary"

        return format_html('<label class="badge bg-{}">{}</label>', log_level, value)

    def render_message(self, value):
        return render_markdown(value)

    class Meta(BaseTable.Meta):
        model = JobLogEntry
        fields = ("created", "grouping", "log_level", "log_object", "message")
        default_columns = ("created", "grouping", "log_level", "log_object", "message")
        row_attrs = {
            "class": log_entry_color_css,
        }
        attrs = {
            "class": "table table-hover nb-table-headings",
            "id": "logs",
        }


class JobQueueTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    tenant = TenantColumn()
    jobs_count = LinkedCountColumn(viewname="extras:job_list", url_params={"job_queues": "pk"}, verbose_name="Jobs")

    class Meta(BaseTable.Meta):
        model = JobQueue
        fields = (
            "pk",
            "name",
            "queue_type",
            "tenant",
            "jobs_count",
            "description",
        )
        default_columns = (
            "pk",
            "name",
            "queue_type",
            "tenant",
            "jobs_count",
            "description",
        )


class JobResultTable(BaseTable):
    pk = ToggleColumn()
    job_model = tables.Column(linkify=True)
    date_created = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    date_started = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    date_done = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    status = tables.TemplateColumn(
        template_code="{% include 'extras/inc/job_label.html' with result=record %}",
    )
    summary = tables.Column(
        empty_values=(),
        verbose_name="Summary",
        orderable=False,
        attrs={"td": {"class": "text-nowrap report-stats"}},
    )
    scheduled_job = tables.Column(
        linkify=True,
        verbose_name="Scheduled Job",
    )
    duration = tables.Column(orderable=False)
    actions = ButtonsColumn(JobResult, buttons=("delete",), prepend_template=JOB_RESULT_BUTTONS)

    def render_summary(self, record):
        """
        Define custom rendering for the summary column.
        """
        # The *_log_count attributes will be calculated and updated at the end of a Job run when JobResult is saved.
        # If the values are not present due to a running Job or are missing in any field, skip display.
        if record.status not in JobResultStatusChoices.READY_STATES or None in [
            record.debug_log_count,
            record.success_log_count,
            record.info_log_count,
            record.warning_log_count,
            record.error_log_count,
        ]:
            return ""

        return format_html(
            """<label class="badge bg-secondary">{}</label>
            <label class="badge bg-success">{}</label>
            <label class="badge bg-info">{}</label>
            <label class="badge bg-warning">{}</label>
            <label class="badge bg-danger">{}</label>""",
            record.debug_log_count,
            record.success_log_count,
            record.info_log_count,
            record.warning_log_count,
            record.error_log_count,
        )

    class Meta(BaseTable.Meta):
        model = JobResult
        fields = (
            "pk",
            "date_created",
            "date_started",
            "date_done",
            "name",
            "job_model",
            "scheduled_job",
            "duration",
            "date_done",
            "user",
            "status",
            "summary",
            "actions",
        )
        default_columns = (
            "pk",
            "date_created",
            "name",
            "job_model",
            "user",
            "status",
            "summary",
            "actions",
        )


class JobButtonTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    job = tables.Column(linkify=True)
    enabled = BooleanColumn()
    confirmation = BooleanColumn()
    content_types = ContentTypesColumn(truncate_words=15)

    class Meta(BaseTable.Meta):
        model = JobButton
        fields = (
            "pk",
            "name",
            "content_types",
            "text",
            "job",
            "enabled",
            "group_name",
            "weight",
            "button_class",
            "confirmation",
        )
        default_columns = (
            "pk",
            "name",
            "content_types",
            "group_name",
            "weight",
            "job",
            "enabled",
            "confirmation",
        )


#
# Metadata
#


class MetadataTypeTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    content_types = ContentTypesColumn(truncate_words=15)
    actions = ButtonsColumn(MetadataType)

    class Meta(BaseTable.Meta):
        model = MetadataType
        fields = (
            "pk",
            "name",
            "description",
            "content_types",
            "data_type",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "content_types",
            "data_type",
            "actions",
        )


class MetadataChoiceTable(BaseTable):
    value = tables.Column()
    weight = tables.Column()

    class Meta(BaseTable.Meta):
        model = MetadataChoice
        fields = ("value", "weight")


class ObjectMetadataTable(BaseTable):
    pk = ToggleColumn()
    # NOTE: there is no identity column in this table; this is intentional as we have no detail view for ObjectMetadata
    metadata_type = tables.Column(linkify=True)
    assigned_object = tables.TemplateColumn(
        template_code=ASSIGNED_OBJECT, verbose_name="Assigned object", orderable=False
    )
    # This is needed so that render_value method below does not skip itself
    # when metadata_type.data_type is TYPE_CONTACT_TEAM and we need it to display either contact or team
    value = tables.Column(empty_values=[], order_by=("_value",))

    class Meta(BaseTable.Meta):
        model = ObjectMetadata
        fields = (
            "pk",
            "assigned_object",
            "metadata_type",
            "scoped_fields",
            "value",
        )
        default_columns = (
            "pk",
            "assigned_object",
            "scoped_fields",
            "value",
            "metadata_type",
        )

    def render_scoped_fields(self, value):
        if not value:
            return "(all fields)"
        return format_html_join(", ", "<code>{}</code>", ([v] for v in sorted(value)))

    def render_value(self, record):
        if record.value is not None and record.metadata_type.data_type == MetadataTypeDataTypeChoices.TYPE_JSON:
            return render_json(record.value, pretty_print=True)
        elif record.value is not None and record.metadata_type.data_type == MetadataTypeDataTypeChoices.TYPE_MARKDOWN:
            return render_markdown(record.value)
        elif record.value is not None and record.metadata_type.data_type == MetadataTypeDataTypeChoices.TYPE_BOOLEAN:
            return render_boolean(record.value)
        elif record.metadata_type.data_type == MetadataTypeDataTypeChoices.TYPE_CONTACT_TEAM:
            if record.contact:
                return format_html('<a href="{}">{}</a>', record.contact.get_absolute_url(), record.contact)
            else:
                return format_html('<a href="{}">{}</a>', record.team.get_absolute_url(), record.team)
        return record.value


#
# Notes
#


class NoteTable(BaseTable):
    actions = ButtonsColumn(Note)
    created = tables.DateTimeColumn(linkify=True)
    last_updated = tables.DateTimeColumn()
    note = tables.Column()

    class Meta(BaseTable.Meta):
        model = Note
        fields = ("created", "last_updated", "note", "user_name", "actions")

    def render_note(self, value):
        return render_markdown(value)


#
# ScheduledJobs
#


class ScheduledJobTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    job_model = tables.Column(verbose_name="Job", linkify=True)
    enabled = BooleanColumn()
    interval = tables.Column(verbose_name="Execution Type")
    start_time = tables.DateTimeColumn(verbose_name="First Run", format=settings.SHORT_DATETIME_FORMAT)
    last_run_at = tables.DateTimeColumn(verbose_name="Most Recent Run", format=settings.SHORT_DATETIME_FORMAT)
    crontab = tables.Column()
    total_run_count = tables.Column(verbose_name="Total Run Count")
    actions = ButtonsColumn(ScheduledJob, buttons=("delete",), prepend_template=SCHEDULED_JOB_BUTTONS)
    approval_state = tables.Column(empty_values=[], orderable=False)

    def render_approval_state(self, record):
        workflow = record.associated_approval_workflows.first()
        if workflow is not None:
            return format_html('<a href="{}">{}</a>', record.get_approval_workflow_url(), workflow.current_state)
        return HTML_NONE

    class Meta(BaseTable.Meta):
        model = ScheduledJob
        fields = (
            "pk",
            "name",
            "total_run_count",
            "job_model",
            "approval_state",
            "interval",
            "start_time",
            "last_run_at",
            "crontab",
            "time_zone",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "job_model",
            "enabled",
            "approval_state",
            "interval",
            "last_run_at",
            "actions",
        )


class ScheduledJobApprovalQueueTable(BaseTable):
    name = tables.LinkColumn(viewname="extras:scheduledjob_approval_request_view", args=[tables.A("pk")])
    job_model = tables.Column(verbose_name="Job", linkify=True)
    interval = tables.Column(verbose_name="Execution Type")
    start_time = tables.Column(verbose_name="Requested")
    user = tables.Column(verbose_name="Requestor")
    actions = tables.TemplateColumn(
        SCHEDULED_JOB_APPROVAL_QUEUE_BUTTONS,
        attrs={
            "td": {"class": "d-print-none text-end text-nowrap nb-actions nb-w-0"},
            "tf": {"class": "nb-w-0"},
            "th": {"class": "nb-actionable nb-w-0"},
        },
    )

    class Meta(BaseTable.Meta):
        model = ScheduledJob
        fields = ("name", "job_model", "interval", "user", "start_time", "actions")


class ObjectChangeTable(BaseTable):
    time = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    action = ChoiceFieldColumn()
    changed_object_type = tables.Column(verbose_name="Type")
    object_repr = tables.TemplateColumn(template_code=OBJECTCHANGE_OBJECT, verbose_name="Object")
    request_id = tables.TemplateColumn(template_code=OBJECTCHANGE_REQUEST_ID, verbose_name="Request ID")

    class Meta(BaseTable.Meta):
        model = ObjectChange
        fields = (
            "time",
            "user_name",
            "action",
            "changed_object_type",
            "object_repr",
            "request_id",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only prefetch if all content types are valid
        if all(ct.model_class() is not None for ct in ContentType.objects.all()):
            self.add_conditional_prefetch("object_repr", "changed_object")
        else:
            error_message = dedent("""\
                            One or more ContentType entries in the database are invalid.
                            This will likely cause performance degradation when viewing the Object Change log.
                            An administrator can follow these steps to resolve common issues:
                             - Run `nautobot-server remove_stale_contenttypes`
                             - Run `nautobot-server migrate <app_label> zero` for any app labels which no longer exist
                             - Manually dropping tables for any models which have been removed from Nautobot or its plugins from your database
                             - Run ```
                                    from django.contrib.contenttypes.models import ContentType
                                    qs = ContentType.objects.filter(
                                        app_label__in=[
                                            "<app_label_of_removed_plugin_1>",
                                            "<app_label_of_removed_plugin_2>",
                                        ]
                                    ) | ContentType.objects.filter(model__icontains="<name_of_removed_model_1>")
                                    # Review the queryset before running delete
                                    qs.delete()
                                   ```
                            Please ensure you fully understand the implications of these actions before proceeding.
                            """)
            logger.warning(error_message)


#
# Relationship
#


class RelationshipTable(BaseTable):
    pk = ToggleColumn()
    label = tables.Column(linkify=True)
    actions = ButtonsColumn(Relationship, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = Relationship
        fields = (
            "pk",
            "label",
            "description",
            "type",
            "source_type",
            "destination_type",
            "actions",
            "required_on",
        )


class RelationshipAssociationTable(BaseTable):
    pk = ToggleColumn()
    actions = ButtonsColumn(RelationshipAssociation, buttons=("delete",))
    relationship = tables.Column(linkify=True)

    source_type = tables.Column()
    source = tables.Column(linkify=True, orderable=False, accessor="get_source", default="unknown")

    destination_type = tables.Column()
    destination = tables.Column(linkify=True, orderable=False, accessor="get_destination", default="unknown")

    class Meta(BaseTable.Meta):
        model = RelationshipAssociation
        fields = (
            "pk",
            "relationship",
            "source_type",
            "source",
            "destination_type",
            "destination",
            "actions",
        )
        default_columns = ("pk", "relationship", "source", "destination", "actions")


#
# Role
#


class RoleTable(BaseTable):
    """Table for list view of `Role` objects."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    color = ColorColumn()
    actions = ButtonsColumn(Role)
    content_types = ContentTypesColumn(truncate_words=15)

    class Meta(BaseTable.Meta):
        model = Role
        fields = ["pk", "name", "color", "weight", "content_types", "description", "actions"]


class RoleTableMixin(BaseTable):
    """Mixin to add a `role` field to a table."""

    role = ColoredLabelColumn()


#
# Secrets
#


class SecretTable(BaseTable):
    """Table for list view of `Secret` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    tags = TagColumn(url_name="extras:secret_list")
    actions = ButtonsColumn(Secret)

    class Meta(BaseTable.Meta):
        model = Secret
        fields = (
            "pk",
            "name",
            "provider",
            "description",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "provider",
            "description",
            "tags",
            "actions",
        )

    def render_provider(self, value):
        return registry["secrets_providers"][value].name if value in registry["secrets_providers"] else value


class SecretsGroupTable(BaseTable):
    """Table for list view of `SecretsGroup` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    actions = ButtonsColumn(SecretsGroup)

    class Meta(BaseTable.Meta):
        model = SecretsGroup
        fields = (
            "pk",
            "name",
            "description",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "description",
            "actions",
        )


class SecretsGroupAssociationTable(BaseTable):
    secret = tables.Column(linkify=True)

    class Meta:
        model = SecretsGroupAssociation
        fields = ("access_type", "secret_type", "secret")
        default_columns = ("access_type", "secret_type", "secret")
        # Avoid extra UI clutter
        attrs = {"class": "table table-condensed"}


#
# Custom statuses
#


class StatusTable(BaseTable):
    """Table for list view of `Status` objects."""

    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    color = ColorColumn()
    actions = ButtonsColumn(Status)
    content_types = ContentTypesColumn(truncate_words=15)

    class Meta(BaseTable.Meta):
        model = Status
        fields = ["pk", "name", "color", "content_types", "description", "actions"]


class StatusTableMixin(BaseTable):
    """Mixin to add a `status` field to a table."""

    status = ColoredLabelColumn()


class TagTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn(viewname="extras:tag", args=[Accessor("pk")])
    color = ColorColumn()
    content_types = ContentTypesColumn(truncate_words=15)
    actions = ButtonsColumn(Tag)

    class Meta(BaseTable.Meta):
        model = Tag
        fields = (
            "pk",
            "name",
            "items",
            "color",
            "content_types",
            "description",
            "actions",
        )


class TaggedItemTable(BaseTable):
    content_object = tables.TemplateColumn(template_code=TAGGED_ITEM, orderable=False, verbose_name="Object")
    content_type = tables.Column(verbose_name="Type")

    class Meta(BaseTable.Meta):
        model = TaggedItem
        fields = ("content_object", "content_type")


class TeamTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    phone = tables.TemplateColumn(PHONE)
    tags = TagColumn(url_name="extras:team_list")
    actions = ButtonsColumn(Team)

    class Meta(BaseTable.Meta):
        model = Team
        fields = (
            "pk",
            "name",
            "phone",
            "email",
            "address",
            "comments",
            "tags",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "phone",
            "email",
            "tags",
            "actions",
        )


class WebhookTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    content_types = tables.TemplateColumn(WEBHOOK_CONTENT_TYPES)
    enabled = BooleanColumn()
    type_create = BooleanColumn()
    type_update = BooleanColumn()
    type_delete = BooleanColumn()
    ssl_verification = BooleanColumn()
    actions = ButtonsColumn(Webhook)

    class Meta(BaseTable.Meta):
        model = Webhook
        fields = (
            "pk",
            "name",
            "content_types",
            "payload_url",
            "http_content_type",
            "http_method",
            "enabled",
            "type_create",
            "type_update",
            "type_delete",
            "ssl_verification",
            "ca_file_path",
            "actions",
        )
        default_columns = (
            "pk",
            "name",
            "content_types",
            "payload_url",
            "http_content_type",
            "enabled",
            "actions",
        )


class AssociatedContactsTable(StatusTableMixin, RoleTableMixin, BaseTable):
    pk = ToggleColumn()
    contact_type = tables.TemplateColumn(
        CONTACT_OR_TEAM_ICON,
        verbose_name="Type",
        attrs={"td": {"style": "width:20px;"}},
    )
    name = tables.TemplateColumn(CONTACT_OR_TEAM, verbose_name="Name")
    contact_or_team_phone = tables.TemplateColumn(PHONE, accessor="contact_or_team__phone", verbose_name="Phone")
    contact_or_team_email = tables.TemplateColumn(EMAIL, accessor="contact_or_team__email", verbose_name="E-Mail")
    actions = actions = ButtonsColumn(model=ContactAssociation, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = ContactAssociation
        fields = (
            "pk",
            "contact_type",
            "name",
            "status",
            "role",
            "contact_or_team_phone",
            "contact_or_team_email",
            "actions",
        )
        default_columns = [
            "pk",
            "contact_type",
            "name",
            "status",
            "role",
            "contact_or_team_phone",
            "contact_or_team_email",
            "actions",
        ]
        orderable = False


class ContactAssociationTable(StatusTableMixin, RoleTableMixin, BaseTable):
    associated_object_type = tables.Column(verbose_name="Object Type")
    associated_object = tables.Column(linkify=True, verbose_name="Object")

    class Meta(BaseTable.Meta):
        model = ContactAssociation
        fields = ("role", "status", "associated_object_type", "associated_object")
