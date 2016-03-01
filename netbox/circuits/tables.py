import django_tables2 as tables
from django_tables2.utils import Accessor

from .models import Circuit, Provider


#
# Providers
#

class ProviderTable(tables.Table):
    name = tables.LinkColumn('circuits:provider', args=[Accessor('slug')], verbose_name='Name')
    asn = tables.Column(verbose_name='ASN')
    circuit_count = tables.Column(accessor=Accessor('count_circuits'), verbose_name='Circuits')

    class Meta:
        model = Provider
        fields = ('name', 'asn', 'circuit_count')
        empty_text = "No providers found."
        attrs = {
            'class': 'table table-hover',
        }


class ProviderBulkEditTable(ProviderTable):
    pk = tables.CheckBoxColumn()

    class Meta(ProviderTable.Meta):
        model = None  # django_tables2 bugfix
        fields = ('pk', 'name', 'asn', 'circuit_count')


#
# Circuits
#

class CircuitTable(tables.Table):
    cid = tables.LinkColumn('circuits:circuit', args=[Accessor('pk')], verbose_name='ID')
    type = tables.Column(verbose_name='Type')
    provider = tables.LinkColumn('circuits:provider', args=[Accessor('provider.slug')], verbose_name='Provider')
    site = tables.LinkColumn('dcim:site', args=[Accessor('site.slug')], verbose_name='Site')
    port_speed = tables.Column(verbose_name='Port Speed')
    commit_rate = tables.Column(verbose_name='Commit (Mbps)')

    class Meta:
        model = Circuit
        fields = ('cid', 'type', 'provider', 'site', 'port_speed', 'commit_rate')
        empty_text = "No circuits found."
        attrs = {
            'class': 'table table-hover',
        }


class CircuitBulkEditTable(CircuitTable):
    pk = tables.CheckBoxColumn()

    class Meta(CircuitTable.Meta):
        model = None  # django_tables2 bugfix
        fields = ('pk', 'cid', 'type', 'provider', 'site', 'port_speed', 'commit_rate')
