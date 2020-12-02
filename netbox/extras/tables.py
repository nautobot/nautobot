import django_tables2 as tables
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils.html import format_html

from utilities.tables import BaseTable, BooleanColumn, ButtonsColumn, ChoiceFieldColumn, ColorColumn, ToggleColumn
from .custom_jobs import get_custom_job
from .models import ConfigContext, JobResult, ObjectChange, Tag, TaggedItem

TAGGED_ITEM = """
{% if value.get_absolute_url %}
    <a href="{{ value.get_absolute_url }}">{{ value }}</a>
{% else %}
    {{ value }}
{% endif %}
"""

CONFIGCONTEXT_ACTIONS = """
{% if perms.extras.change_configcontext %}
    <a href="{% url 'extras:configcontext_edit' pk=record.pk %}" class="btn btn-xs btn-warning"><i class="mdi mdi-pencil" aria-hidden="true"></i></a>
{% endif %}
{% if perms.extras.delete_configcontext %}
    <a href="{% url 'extras:configcontext_delete' pk=record.pk %}" class="btn btn-xs btn-danger"><i class="mdi mdi-trash-can-outline" aria-hidden="true"></i></a>
{% endif %}
"""

OBJECTCHANGE_OBJECT = """
{% if record.changed_object.get_absolute_url %}
    <a href="{{ record.changed_object.get_absolute_url }}">{{ record.object_repr }}</a>
{% else %}
    {{ record.object_repr }}
{% endif %}
"""

OBJECTCHANGE_REQUEST_ID = """
<a href="{% url 'extras:objectchange_list' %}?request_id={{ value }}">{{ value }}</a>
"""


class TagTable(BaseTable):
    pk = ToggleColumn()
    color = ColorColumn()
    actions = ButtonsColumn(Tag, pk_field='slug')

    class Meta(BaseTable.Meta):
        model = Tag
        fields = ('pk', 'name', 'items', 'slug', 'color', 'description', 'actions')


class TaggedItemTable(BaseTable):
    content_object = tables.TemplateColumn(
        template_code=TAGGED_ITEM,
        orderable=False,
        verbose_name='Object'
    )
    content_type = tables.Column(
        verbose_name='Type'
    )

    class Meta(BaseTable.Meta):
        model = TaggedItem
        fields = ('content_object', 'content_type')


class ConfigContextTable(BaseTable):
    pk = ToggleColumn()
    name = tables.LinkColumn()
    is_active = BooleanColumn(
        verbose_name='Active'
    )

    class Meta(BaseTable.Meta):
        model = ConfigContext
        fields = (
            'pk', 'name', 'weight', 'is_active', 'description', 'regions', 'sites', 'roles', 'platforms',
            'cluster_groups', 'clusters', 'tenant_groups', 'tenants',
        )
        default_columns = ('pk', 'name', 'weight', 'is_active', 'description')


def customjob_link(value, record):
    if record.obj_type == ContentType.objects.get(app_label='extras', model='customjob') and '.' in record.name:
        module, name = record.name.split('.', 1)
        if get_custom_job(module, name) is not None:
            return reverse('extras:customjob', kwargs={'module': module, 'name': name})
    return None


class JobResultTable(BaseTable):
    name = tables.Column(linkify=customjob_link)
    created = tables.DateTimeColumn(linkify=True, format=settings.SHORT_DATETIME_FORMAT)
    status = tables.TemplateColumn(
        template_code="{% include 'extras/inc/job_label.html' with result=record %}",
    )
    data = tables.TemplateColumn(
        '''
        <label class="label label-success">{{ value.total.success }}</label>
        <label class="label label-info">{{ value.total.info }}</label>
        <label class="label label-warning">{{ value.total.warning }}</label>
        <label class="label label-danger">{{ value.total.failure }}</label>
        ''',
        verbose_name='Results',
        orderable=False,
        attrs={"td": {"class": "text-nowrap report-stats"}}
    )

    class Meta(BaseTable.Meta):
        model = JobResult
        fields = ('created', 'name', 'duration', 'completed', 'user', 'status', 'data')
        default_columns = ('created', 'name', 'user', 'status', 'data')


class ObjectChangeTable(BaseTable):
    time = tables.DateTimeColumn(
        linkify=True,
        format=settings.SHORT_DATETIME_FORMAT
    )
    action = ChoiceFieldColumn()
    changed_object_type = tables.Column(
        verbose_name='Type'
    )
    object_repr = tables.TemplateColumn(
        template_code=OBJECTCHANGE_OBJECT,
        verbose_name='Object'
    )
    request_id = tables.TemplateColumn(
        template_code=OBJECTCHANGE_REQUEST_ID,
        verbose_name='Request ID'
    )

    class Meta(BaseTable.Meta):
        model = ObjectChange
        fields = ('time', 'user_name', 'action', 'changed_object_type', 'object_repr', 'request_id')
