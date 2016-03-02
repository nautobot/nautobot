import django_tables2 as tables
from django_tables2.utils import Accessor

from .models import Aggregate, Prefix, IPAddress, VLAN, VRF


UTILIZATION_GRAPH = """
{% with record.get_utilization as percentage %}
<div class="progress text-center">
    {% if percentage < 15 %}<span style="font-size: 12px;">{{ percentage }}%</span>{% endif %}
    <div class="progress-bar progress-bar-{% if percentage >= 90 %}danger{% elif percentage >= 75 %}warning{% else %}success{% endif %}" role="progressbar" aria-valuenow="{{ percentage }}" aria-valuemin="0" aria-valuemax="100" style="width: {{ percentage }}%">
        {% if percentage >= 15 %}{{ percentage }}%{% endif %}
    </div>
</div>
{% endwith %}
"""

PREFIX_LINK = """
{% if record.has_children %}
    <span style="padding-left: {{ record.depth }}0px "><i class="fa fa-caret-right"></i></a>
{% else %}
    <span style="padding-left: {{ record.depth }}9px">
{% endif %}
    <a href="{% if record.pk %}{% url 'ipam:prefix' pk=record.pk %}{% else %}{% url 'ipam:prefix_add' %}?prefix={{ record }}{% if site %}&site={{ site.pk }}{% endif %}{% endif %}">{{ record.prefix }}</a>
</span>
"""

PREFIX_LINK_BRIEF = """
<span style="padding-left: {{ record.depth }}0px">
    <a href="{% if record.pk %}{% url 'ipam:prefix' pk=record.pk %}{% else %}{% url 'ipam:prefix_add' %}?prefix={{ record }}{% if site %}&site={{ site.pk }}{% endif %}{% endif %}">{{ record.prefix }}</a>
</span>
"""

STATUS_LABEL = """
{% if record.pk %}
    <span class="label label-{{ record.status.get_bootstrap_class_display|lower }}">{{ record.status.name }}</span>
{% else %}
    <span class="label label-success">Available</span>
{% endif %}
"""


#
# VRFs
#

class VRFTable(tables.Table):
    name = tables.LinkColumn('ipam:vrf', args=[Accessor('pk')], verbose_name='Name')
    rd = tables.Column(verbose_name='RD')
    description = tables.Column(sortable=False, verbose_name='Description')

    class Meta:
        model = VRF
        fields = ('name', 'rd', 'description')
        empty_text = "No VRFs found."
        attrs = {
            'class': 'table table-hover',
        }


class VRFBulkEditTable(VRFTable):
    pk = tables.CheckBoxColumn()

    class Meta(VRFTable.Meta):
        model = None  # django_tables2 bugfix
        fields = ('pk', 'name', 'rd', 'description')


#
# Aggregates
#

class AggregateTable(tables.Table):
    prefix = tables.LinkColumn('ipam:aggregate', args=[Accessor('pk')], verbose_name='Aggregate')
    rir = tables.Column(verbose_name='RIR')
    child_count = tables.Column(verbose_name='Prefixes')
    utilization = tables.TemplateColumn(UTILIZATION_GRAPH, orderable=False, verbose_name='Utilization')
    date_added = tables.DateColumn(format="Y-m-d", verbose_name='Added')
    description = tables.Column(sortable=False, verbose_name='Description')

    class Meta:
        model = Aggregate
        fields = ('prefix', 'rir', 'child_count', 'utilization', 'date_added', 'description')
        empty_text = "No aggregates found."
        attrs = {
            'class': 'table table-hover',
        }


class AggregateBulkEditTable(AggregateTable):
    pk = tables.CheckBoxColumn()

    class Meta(AggregateTable.Meta):
        model = None  # django_tables2 bugfix
        fields = ('pk', 'prefix', 'rir', 'child_count', 'utilization', 'date_added', 'description')


#
# Prefixes
#

class PrefixTable(tables.Table):
    status = tables.TemplateColumn(STATUS_LABEL, verbose_name='Status')
    prefix = tables.TemplateColumn(PREFIX_LINK, verbose_name='Prefix')
    vrf = tables.Column(orderable=False, default='Global', verbose_name='VRF')
    site = tables.LinkColumn('dcim:site', args=[Accessor('site.slug')], verbose_name='Site')
    role = tables.Column(verbose_name='Role')
    description = tables.Column(sortable=False, verbose_name='Description')

    class Meta:
        model = Prefix
        fields = ('prefix', 'status', 'vrf', 'site', 'role', 'description')
        empty_text = "No prefixes found."
        attrs = {
            'class': 'table table-hover',
        }


class PrefixBriefTable(tables.Table):
    prefix = tables.TemplateColumn(PREFIX_LINK_BRIEF, verbose_name='Prefix')
    site = tables.LinkColumn('dcim:site', args=[Accessor('site.slug')], verbose_name='Site')
    status = tables.TemplateColumn(STATUS_LABEL, verbose_name='Status')
    role = tables.Column(verbose_name='Role')

    class Meta:
        model = Prefix
        fields = ('prefix', 'status', 'site', 'role')
        empty_text = "No prefixes found."
        attrs = {
            'class': 'table table-hover',
        }


class PrefixBulkEditTable(PrefixTable):
    pk = tables.CheckBoxColumn(default='')

    class Meta(PrefixTable.Meta):
        model = None  # django_tables2 bugfix
        fields = ('pk', 'prefix', 'status', 'vrf', 'site', 'role', 'description')


#
# IPAddresses
#

class IPAddressTable(tables.Table):
    address = tables.LinkColumn('ipam:ipaddress', args=[Accessor('pk')], verbose_name='IP Address')
    vrf = tables.Column(orderable=False, default='Global', verbose_name='VRF')
    device = tables.LinkColumn('dcim:device', args=[Accessor('interface.device.pk')], orderable=False, verbose_name='Device')
    interface = tables.Column(orderable=False, verbose_name='Interface')
    description = tables.Column(sortable=False, verbose_name='Description')

    class Meta:
        model = IPAddress
        fields = ('address', 'vrf', 'device', 'interface', 'description')
        empty_text = "No IP addresses found."
        attrs = {
            'class': 'table table-hover',
        }


class IPAddressBriefTable(tables.Table):
    address = tables.LinkColumn('ipam:ipaddress', args=[Accessor('pk')], verbose_name='IP Address')
    device = tables.LinkColumn('dcim:device', args=[Accessor('interface.device.pk')], orderable=False, verbose_name='Device')
    interface = tables.Column(orderable=False, verbose_name='Interface')
    nat_inside = tables.LinkColumn('ipam:ipaddress', args=[Accessor('nat_inside.pk')], orderable=False, verbose_name='NAT (Inside)')

    class Meta:
        model = IPAddress
        fields = ('address', 'device', 'interface', 'nat_inside')
        empty_text = "No IP addresses found."
        attrs = {
            'class': 'table table-hover',
        }


class IPAddressBulkEditTable(IPAddressTable):
    pk = tables.CheckBoxColumn()

    class Meta(IPAddressTable.Meta):
        model = None  # django_tables2 bugfix
        fields = ('pk', 'address', 'vrf', 'device', 'interface', 'description')


#
# VLANs
#

class VLANTable(tables.Table):
    vid = tables.LinkColumn('ipam:vlan', args=[Accessor('pk')], verbose_name='ID')
    site = tables.LinkColumn('dcim:site', args=[Accessor('site.slug')], verbose_name='Site')
    name = tables.Column(verbose_name='Name')
    status = tables.TemplateColumn(STATUS_LABEL, verbose_name='Status')
    role = tables.Column(verbose_name='Role')

    class Meta:
        model = VLAN
        fields = ('vid', 'site', 'name', 'status', 'role')
        empty_text = "No VLANs found."
        attrs = {
            'class': 'table table-hover',
        }


class VLANBulkEditTable(VLANTable):
    pk = tables.CheckBoxColumn()

    class Meta(VLANTable.Meta):
        model = None  # django_tables2 bugfix
        fields = ('pk', 'vid', 'site', 'name', 'status', 'role')
