import django_tables2 as tables
from django_tables2.utils import Accessor

from utilities.tables import ToggleColumn

from .models import Circuit, CircuitType, Provider


CIRCUITTYPE_EDIT_LINK = """
{% if perms.circuit.change_circuittype %}
    <a href="{% url 'circuits:circuittype_edit' slug=record.slug %}">Edit</a>
{% endif %}
"""


#
# Providers
#

class ProviderTable(tables.Table):
    pk = ToggleColumn()
    name = tables.LinkColumn('circuits:provider', args=[Accessor('slug')], verbose_name='Name')
    asn = tables.Column(verbose_name='ASN')
    circuit_count = tables.Column(accessor=Accessor('count_circuits'), verbose_name='Circuits')

    class Meta:
        model = Provider
        fields = ('pk', 'name', 'asn', 'circuit_count')
        empty_text = "No providers found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Circuit types
#

class CircuitTypeTable(tables.Table):
    pk = ToggleColumn()
    name = tables.LinkColumn(verbose_name='Name')
    circuit_count = tables.Column(verbose_name='Circuits')
    slug = tables.Column(verbose_name='Slug')
    edit = tables.TemplateColumn(template_code=CIRCUITTYPE_EDIT_LINK, verbose_name='')

    class Meta:
        model = CircuitType
        fields = ('pk', 'name', 'circuit_count', 'slug', 'edit')
        empty_text = "No circuit types found."
        attrs = {
            'class': 'table table-hover',
        }


#
# Circuits
#

class CircuitTable(tables.Table):
    pk = ToggleColumn()
    cid = tables.LinkColumn('circuits:circuit', args=[Accessor('pk')], verbose_name='ID')
    type = tables.Column(verbose_name='Type')
    provider = tables.LinkColumn('circuits:provider', args=[Accessor('provider.slug')], verbose_name='Provider')
    site = tables.LinkColumn('dcim:site', args=[Accessor('site.slug')], verbose_name='Site')
    port_speed_human = tables.Column(verbose_name='Port Speed')
    commit_rate_human = tables.Column(verbose_name='Commit Rate')

    class Meta:
        model = Circuit
        fields = ('pk', 'cid', 'type', 'provider', 'site', 'port_speed_human', 'commit_rate_human')
        empty_text = "No circuits found."
        attrs = {
            'class': 'table table-hover',
        }
