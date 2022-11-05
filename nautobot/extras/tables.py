import django_tables2 as tables
from django.conf import settings
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django_tables2.utils import Accessor
from jsonschema.exceptions import ValidationError as JSONSchemaValidationError

from nautobot.utilities.tables import (
    BaseTable,
    BooleanColumn,
    ButtonsColumn,
    ChoiceFieldColumn,
    ColorColumn,
    ColoredLabelColumn,
    ContentTypesColumn,
    TagColumn,
    ToggleColumn,
)
from nautobot.utilities.templatetags.helpers import render_boolean, render_markdown
from .choices import LogLevelChoices
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomField,
    CustomLink,
    DynamicGroup,
    DynamicGroupMembership,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    Job as JobModel,
    JobHook,
    JobResult,
    JobLogEntry,
    Note,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    ScheduledJob,
    Secret,
    SecretsGroup,
    Status,
    Tag,
    TaggedItem,
    Webhook,
)
from .registry import registry


TAGGED_ITEM = """
{% if value.get_absolute_url %}
    <a href="{{ value.get_absolute_url }}">{{ value }}</a>
{% else %}
    {{ value }}
{% endif %}
"""

GITREPOSITORY_PROVIDES = """
<span class="text-nowrap">
{% for entry in datasource_contents %}
<span style="display: inline-block" title="{{ entry.name|title }}"
class="label label-{% if entry.content_identifier in record.provided_contents %}success{% else %}default{% endif %}">
<i class="mdi {{ entry.icon }}"></i></span>
{% endfor %}
</span>
"""

GITREPOSITORY_BUTTONS = """
<button data-url="{% url 'extras:gitrepository_sync' slug=record.slug %}" type="submit" class="btn btn-primary btn-xs sync-repository" title="Sync" {% if not perms.extras.change_gitrepository %}disabled="disabled"{% endif %}><i class="mdi mdi-source-branch-sync" aria-hidden="true"></i></button>
"""

JOB_BUTTONS = """
<a href="{% url 'extras:job_run' slug=record.slug %}" class="btn btn-primary btn-xs" title="Run/Schedule" {% if not perms.extras.run_job or not record.runnable %}disabled="disabled"{% endif %}><i class="mdi mdi-play" aria-hidden="true"></i></a>
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

# TODO: Webhook content_types in table order_by
WEBHOOK_CONTENT_TYPES = """
{{ value.all|join:", "|truncatewords:15 }}
"""

SCHEDULED_JOB_APPROVAL_QUEUE_BUTTONS = """
<button type="button"
        onClick="handleDetailPostAction('{% url 'extras:scheduledjob_approval_request_view' pk=record.pk %}', '_dry_run')"
        title="Dry Run"
        class="btn btn-primary btn-xs"{% if not perms.extras.run_job %} disabled="disabled"{% endif %}>
    <i class="mdi mdi-play"></i>
</button>
<button type="button"
        onClick="handleDetailPostAction('{% url 'extras:scheduledjob_approval_request_view' pk=record.pk %}', '_approve')"
        title="Approve"
        class="btn btn-success btn-xs"{% if not perms.extras.run_job %} disabled="disabled"{% endif %}>
    <i class="mdi mdi-check"></i>
</button>
<button type="button"
        onClick="handleDetailPostAction('{% url 'extras:scheduledjob_approval_request_view' pk=record.pk %}', '_deny')"
        title="Deny"
        class="btn btn-danger btn-xs"{% if not perms.extras.run_job %} disabled="disabled"{% endif %}>
    <i class="mdi mdi-close"></i>
</button>
"""


class ComputedFieldTable(BaseTable):
    pk = ToggleColumn()
    label = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        model = ComputedField
        fields = (
            "pk",
            "label",
            "slug",
            "content_type",
            "description",
            "weight",
        )
        default_columns = (
            "pk",
            "label",
            "slug",
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
            "regions",
            "sites",
            "roles",
            "platforms",
            "cluster_groups",
            "clusters",
            "tenant_groups",
            "tenants",
        )
        default_columns = ("pk", "name", "weight", "is_active", "description")


class ConfigContextSchemaTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    owner = tables.LinkColumn()
    actions = ButtonsColumn(ConfigContextSchema, pk_field="slug")

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

    def render(self, record):
        data = getattr(record, self.data_field)
        try:
            self.validator.validate(data)
        except JSONSchemaValidationError as e:
            # Return a red x (like a boolean column) and the validation error message
            return render_boolean(False) + format_html('<span class="text-danger">{}</span>', e.message)

        # Return a green check (like a boolean column)
        return render_boolean(True)


class CustomFieldTable(BaseTable):
    pk = ToggleColumn()
    label = tables.Column(linkify=True)
    # 2.0 TODO: #824 Remove name column
    name = tables.TemplateColumn(
        template_code="""
{{ value }}
{% if value != record.slug %}
<span class="text-warning mdi mdi-alert" title="Name does not match slug '{{ record.slug }}'"></span>
{% endif %}
"""
    )
    slug = tables.TemplateColumn(
        template_code="""
{{ value }}
{% if value != record.name %}
<span class="text-warning mdi mdi-alert" title="Name '{{ record.name }}' does not match slug"></span>
{% endif %}
"""
    )
    content_types = ContentTypesColumn(truncate_words=15)
    required = BooleanColumn()

    class Meta(BaseTable.Meta):
        model = CustomField
        fields = (
            "pk",
            "label",
            # 2.0 TODO: #824 Remove name column
            "name",
            "slug",
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
            "slug",
            "content_types",
            "type",
            "required",
            "weight",
        )

    def render_description(self, record):
        if record.description:
            return mark_safe(render_markdown(record.description))
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
    actions = ButtonsColumn(DynamicGroup, pk_field="slug")

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        model = DynamicGroup
        fields = (
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

    description = tables.Column(accessor="group.description")
    actions = ButtonsColumn(DynamicGroup, pk_field="slug", buttons=("edit",))

    class Meta(BaseTable.Meta):
        model = DynamicGroupMembership
        fields = (
            "pk",
            "operator",
            "name",
            "weight",
            "members",
            "description",
            "actions",
        )
        exclude = ("content_type",)


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
    actions = ButtonsColumn(DynamicGroup, pk_field="slug", buttons=("edit",))

    class Meta(DynamicGroupTable.Meta):
        fields = ["name", "members", "description", "actions"]
        exclude = ["content_type"]


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
            if record.name in table.context.get("job_results", {}):
                table.context.update({"result": table.context["job_results"][record.name]})
            else:
                table.context.update({"result": None})
            return super().render(record, table, value, bound_column, **kwargs)

    last_sync_status = JobResultColumn(template_name="extras/inc/job_label.html", verbose_name="Sync Status")
    provides = tables.TemplateColumn(GITREPOSITORY_PROVIDES)
    actions = ButtonsColumn(GitRepository, pk_field="slug", prepend_template=GITREPOSITORY_BUTTONS)

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
        if record.name in self.context["job_results"]:
            return self.context["job_results"][record.name].completed
        return self.default

    def render_last_sync_user(self, record):
        if record.name in self.context["job_results"]:
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
            "slug",
        )


def log_object_link(value, record):
    return record.absolute_url


def log_entry_color_css(record):
    if record.log_level.lower() == "failure":
        return "danger"
    return record.log_level.lower()


class JobTable(BaseTable):
    # TODO pk = ToggleColumn()
    source = tables.Column()
    # grouping is used to, well, group the Jobs, so it isn't a column of its own.
    name = tables.Column(linkify=True)
    installed = BooleanColumn()
    enabled = BooleanColumn()
    has_sensitive_variables = BooleanColumn()
    description = tables.Column(accessor="description_first_line")
    commit_default = BooleanColumn()
    hidden = BooleanColumn()
    read_only = BooleanColumn()
    approval_required = BooleanColumn()
    is_job_hook_receiver = BooleanColumn()
    soft_time_limit = tables.Column()
    time_limit = tables.Column()
    actions = ButtonsColumn(JobModel, pk_field="slug", prepend_template=JOB_BUTTONS)
    last_run = tables.TemplateColumn(
        accessor="latest_result",
        template_code="""
            {% if value %}
                {{ value.created }} by {{ value.user }}
            {% else %}
                <span class="text-muted">Never</span>
            {% endif %}
        """,
        linkify=lambda value: value.get_absolute_url() if value else None,
    )
    last_status = tables.TemplateColumn(
        template_code="{% include 'extras/inc/job_label.html' with result=record.latest_result %}",
    )
    tags = TagColumn(url_name="extras:job_list")

    def render_description(self, value):
        return render_markdown(value)

    class Meta(BaseTable.Meta):
        model = JobModel
        orderable = False
        fields = (
            "source",
            "name",
            "installed",
            "enabled",
            "has_sensitive_variables",
            "description",
            "commit_default",
            "hidden",
            "read_only",
            "is_job_hook_receiver",
            "approval_required",
            "soft_time_limit",
            "time_limit",
            "last_run",
            "last_status",
            "tags",
            "actions",
        )
        default_columns = (
            "name",
            "enabled",
            "description",
            "last_run",
            "last_status",
            "actions",
        )


class JobHookTable(BaseTable):
    pk = ToggleColumn()
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
        attrs={"td": {"class": "rendered-markdown"}},
    )

    def render_log_level(self, value):
        log_level = value.lower()
        # The css is label-danger for failure items.
        if log_level == "failure":
            log_level = "danger"

        return format_html('<label class="label label-{}">{}</label>', log_level, value)

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
            "class": "table table-hover table-headings",
            "id": "logs",
        }


class JobResultTable(BaseTable):
    pk = ToggleColumn()
    linked_record = tables.Column(verbose_name="Job / Git Repository", linkify=True)
    name = tables.Column()
    created = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    status = tables.TemplateColumn(
        template_code="{% include 'extras/inc/job_label.html' with result=record %}",
    )
    summary = tables.Column(
        empty_values=(),
        verbose_name="Results",
        orderable=False,
        attrs={"td": {"class": "text-nowrap report-stats"}},
    )
    actions = tables.TemplateColumn(
        template_code="""
            {% load helpers %}
            {% if perms.extras.run_job %}
                {% if record.job_model and record.job_kwargs %}
                    <a href="{% url 'extras:job_run' slug=record.job_model.slug %}?kwargs_from_job_result={{ record.pk }}"
                       class="btn btn-xs btn-success" title="Re-run job with same arguments.">
                        <i class="mdi mdi-repeat"></i>
                    </a>
                {% elif record.job_model is not None %}
                    <a href="{% url 'extras:job_run' slug=record.job_model.slug %}" class="btn btn-primary btn-xs"
                       title="Run job">
                        <i class="mdi mdi-play"></i>
                    </a>
                {% else %}
                    <a href="#" class="btn btn-xs btn-default disabled" title="Job is not available, cannot be re-run">
                        <i class="mdi mdi-repeat-off"></i>
                    </a>
                {% endif %}
            {% endif %}
            <a href="{% url 'extras:jobresult_delete' pk=record.pk %}" class="btn btn-xs btn-danger"
               title="Delete this job result.">
                <i class="mdi mdi-trash-can-outline"></i>
            </a>
        """
    )

    def order_linked_record(self, queryset, is_descending):
        return (
            queryset.order_by(
                ("-" if is_descending else "") + "job_model__name",
                ("-" if is_descending else "") + "name",
            ),
            True,
        )

    def render_summary(self, record):
        """
        Define custom rendering for the summary column.
        """
        log_objects = record.logs.all()
        success = log_objects.filter(log_level=LogLevelChoices.LOG_SUCCESS).count()
        info = log_objects.filter(log_level=LogLevelChoices.LOG_INFO).count()
        warning = log_objects.filter(log_level=LogLevelChoices.LOG_WARNING).count()
        failure = log_objects.filter(log_level=LogLevelChoices.LOG_FAILURE).count()
        return format_html(
            """<label class="label label-success">{}</label>
            <label class="label label-info">{}</label>
            <label class="label label-warning">{}</label>
            <label class="label label-danger">{}</label>""",
            success,
            info,
            warning,
            failure,
        )

    class Meta(BaseTable.Meta):
        model = JobResult
        fields = (
            "pk",
            "created",
            "name",
            "linked_record",
            "duration",
            "completed",
            "user",
            "status",
            "summary",
            "actions",
        )
        default_columns = ("pk", "created", "name", "linked_record", "user", "status", "summary", "actions")


#
# Notes
#


class NoteTable(BaseTable):
    actions = ButtonsColumn(Note, pk_field="slug")

    class Meta(BaseTable.Meta):
        model = Note
        fields = ("created", "note", "user_name")

    def render_note(self, value):
        return render_markdown(value)


#
# ScheduledJobs
#


class ScheduledJobTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    job_model = tables.Column(verbose_name="Job", linkify=True)
    interval = tables.Column(verbose_name="Execution Type")
    start_time = tables.Column(verbose_name="First Run")
    last_run_at = tables.Column(verbose_name="Most Recent Run")
    total_run_count = tables.Column(verbose_name="Total Run Count")

    class Meta(BaseTable.Meta):
        model = ScheduledJob
        fields = ("pk", "name", "job_model", "interval", "start_time", "last_run_at")


class ScheduledJobApprovalQueueTable(BaseTable):
    name = tables.LinkColumn(viewname="extras:scheduledjob_approval_request_view", args=[tables.A("pk")])
    job_model = tables.Column(verbose_name="Job", linkify=True)
    interval = tables.Column(verbose_name="Execution Type")
    start_time = tables.Column(verbose_name="Requested")
    user = tables.Column(verbose_name="Requestor")
    actions = tables.TemplateColumn(SCHEDULED_JOB_APPROVAL_QUEUE_BUTTONS)

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


#
# Relationship
#


class RelationshipTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    actions = ButtonsColumn(Relationship, pk_field="slug", buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = Relationship
        fields = (
            "pk",
            "name",
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
        fields = ("pk", "relationship", "source_type", "source", "destination_type", "destination", "actions")
        default_columns = ("pk", "relationship", "source", "destination", "actions")


#
# Secrets
#


class SecretTable(BaseTable):
    """Table for list view of `Secret` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()
    tags = TagColumn(url_name="extras:secret_list")

    class Meta(BaseTable.Meta):
        model = Secret
        fields = (
            "pk",
            "name",
            "provider",
            "description",
            "tags",
        )
        default_columns = (
            "pk",
            "name",
            "provider",
            "description",
            "tags",
        )

    def render_provider(self, value):
        return registry["secrets_providers"][value].name if value in registry["secrets_providers"] else value


class SecretsGroupTable(BaseTable):
    """Table for list view of `SecretsGroup` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn()

    class Meta(BaseTable.Meta):
        model = SecretsGroup
        fields = (
            "pk",
            "name",
            "description",
        )
        default_columns = (
            "pk",
            "name",
            "description",
        )


#
# Custom statuses
#


class StatusTable(BaseTable):
    """Table for list view of `Status` objects."""

    pk = ToggleColumn()
    name = tables.LinkColumn(viewname="extras:status", args=[Accessor("slug")])
    color = ColorColumn()
    actions = ButtonsColumn(Status, pk_field="slug")
    content_types = ContentTypesColumn(truncate_words=15)

    class Meta(BaseTable.Meta):
        model = Status
        fields = ["pk", "name", "slug", "color", "content_types", "description"]


class StatusTableMixin(BaseTable):
    """Mixin to add a `status` field to a table."""

    status = ColoredLabelColumn()


class TagTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn(viewname="extras:tag", args=[Accessor("slug")])
    color = ColorColumn()
    content_types = ContentTypesColumn(truncate_words=15)
    actions = ButtonsColumn(Tag, pk_field="slug")

    class Meta(BaseTable.Meta):
        model = Tag
        fields = ("pk", "name", "items", "slug", "color", "content_types", "description", "actions")


class TaggedItemTable(BaseTable):
    content_object = tables.TemplateColumn(template_code=TAGGED_ITEM, orderable=False, verbose_name="Object")
    content_type = tables.Column(verbose_name="Type")

    class Meta(BaseTable.Meta):
        model = TaggedItem
        fields = ("content_object", "content_type")


class WebhookTable(BaseTable):
    pk = ToggleColumn()
    name = tables.Column(linkify=True)
    content_types = tables.TemplateColumn(WEBHOOK_CONTENT_TYPES)
    enabled = BooleanColumn()
    type_create = BooleanColumn()
    type_update = BooleanColumn()
    type_delete = BooleanColumn()
    ssl_verification = BooleanColumn()

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
        )
        default_columns = (
            "pk",
            "name",
            "content_types",
            "payload_url",
            "http_content_type",
            "enabled",
        )
