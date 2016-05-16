import django_tables2 as tables
from django_tables2.utils import Accessor

from .models import SecretRole, Secret


SECRETROLE_EDIT_LINK = """
{% if perms.secrets.change_secretrole %}<a href="{% url 'secrets:secretrole_edit' slug=record.slug %}">Edit</a>{% endif %}
"""


#
# Secret roles
#

class SecretRoleTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    name = tables.LinkColumn(verbose_name='Name')
    secret_count = tables.Column(verbose_name='Secrets')
    slug = tables.Column(verbose_name='Slug')
    edit = tables.TemplateColumn(template_code=SECRETROLE_EDIT_LINK, verbose_name='')

    class Meta:
        model = SecretRole
        fields = ('pk', 'name', 'secret_count', 'slug', 'edit')
        empty_text = "No secret roles were found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Secrets
#

class SecretTable(tables.Table):
    pk = tables.CheckBoxColumn(visible=False, default='')
    device = tables.LinkColumn('secrets:secret', args=[Accessor('pk')], verbose_name='Device')
    role = tables.Column(verbose_name='Role')
    name = tables.Column(verbose_name='Name')
    last_modified = tables.DateTimeColumn(verbose_name='Last modified')

    class Meta:
        model = Secret
        fields = ('pk', 'device', 'role', 'name', 'last_modified')
        empty_text = "No secrets found."
        attrs = {
            'class': 'table table-hover',
        }
