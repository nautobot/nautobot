import inspect

import django_tables2 as tables

from django.conf import settings
from django.urls import reverse
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
    ToggleColumn,
)
from .jobs import get_job_classpaths, Job
from .models import (
    ComputedField,
    ConfigContext,
    ConfigContextSchema,
    CustomLink,
    ExportTemplate,
    GitRepository,
    GraphQLQuery,
    JobResult,
    ObjectChange,
    Relationship,
    RelationshipAssociation,
    Status,
    Tag,
    TaggedItem,
    Webhook,
)

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


class TagTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn(viewname="extras:tag", args=[Accessor("slug")])
    color = ColorColumn()
    actions = ButtonsColumn(Tag, pk_field="slug")

    class Meta(BaseTable.Meta):
        model = Tag
        fields = ("pk", "name", "items", "slug", "color", "description", "actions")


class TaggedItemTable(BaseTable):
    content_object = tables.TemplateColumn(template_code=TAGGED_ITEM, orderable=False, verbose_name="Object")
    content_type = tables.Column(verbose_name="Type")

    class Meta(BaseTable.Meta):
        model = TaggedItem
        fields = ("content_object", "content_type")


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
            return format_html(f'<span class="text-danger"><i class="mdi mdi-close-thick"></i>{e.message}</span>')

        # Return a green check (like a boolean column)
        return mark_safe('<span class="text-success"><i class="mdi mdi-check-bold"></i></span>')


class GitRepositoryTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    remote_url = tables.Column(verbose_name="Remote URL")
    token_rendered = tables.Column(verbose_name="Token")
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
            "token_rendered",
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
    token_rendered = tables.Column(verbose_name="Token")
    provides = tables.TemplateColumn(GITREPOSITORY_PROVIDES)

    class Meta(BaseTable.Meta):
        model = GitRepository
        fields = (
            "pk",
            "name",
            "remote_url",
            "branch",
            "token_rendered",
            "provides",
        )


def job_creator_link(value, record):
    """
    Get a link to the related object, if any, associated with the given JobResult record.
    """
    related_object = record.related_object
    if inspect.isclass(related_object) and issubclass(related_object, Job):
        return reverse("extras:job", kwargs={"class_path": related_object.class_path})
    elif related_object:
        return related_object.get_absolute_url()
    return None


class JobResultTable(BaseTable):
    pk = ToggleColumn()
    obj_type = tables.Column(verbose_name="Object Type", accessor="obj_type.name")
    name = tables.Column(linkify=job_creator_link)
    job_id = tables.Column(linkify=job_creator_link, verbose_name="Job ID")
    created = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    status = tables.TemplateColumn(
        template_code="{% include 'extras/inc/job_label.html' with result=record %}",
    )
    data = tables.TemplateColumn(
        """
        <label class="label label-success">{{ value.total.success }}</label>
        <label class="label label-info">{{ value.total.info }}</label>
        <label class="label label-warning">{{ value.total.warning }}</label>
        <label class="label label-danger">{{ value.total.failure }}</label>
        """,
        verbose_name="Results",
        orderable=False,
        attrs={"td": {"class": "text-nowrap report-stats"}},
    )

    class Meta(BaseTable.Meta):
        model = JobResult
        fields = (
            "pk",
            "created",
            "obj_type",
            "name",
            "job_id",
            "duration",
            "completed",
            "user",
            "status",
            "data",
        )
        default_columns = ("pk", "created", "name", "user", "status", "data")


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


#
# Relationship
#


class RelationshipTable(BaseTable):
    pk = ToggleColumn()
    actions = ButtonsColumn(Relationship, buttons=("edit", "delete"))

    class Meta(BaseTable.Meta):
        model = Relationship
        fields = (
            "name",
            "description",
            "type",
            "source_type",
            "destination_type",
            "actions",
        )


class RelationshipAssociationTable(BaseTable):
    pk = ToggleColumn()
    actions = ButtonsColumn(RelationshipAssociation, buttons=("delete",))

    source = tables.Column(linkify=True)

    destination = tables.Column(linkify=True)

    class Meta(BaseTable.Meta):
        model = RelationshipAssociation
        fields = ("relationship", "source", "destination", "actions")


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
