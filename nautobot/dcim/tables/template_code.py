import django_tables2 as tables

from nautobot.dcim.constants import DEVICE_COMPONENT_ICONS


class DeviceComponentNameColumn(tables.TemplateColumn):
    def __init__(self, *args, modelname, **kwargs):
        self.modelname = modelname
        self.icon = DEVICE_COMPONENT_ICONS[modelname]
        kwargs.setdefault(
            "template_code",
            (f'<span class="mdi {self.icon}"></span> <a href="{{{{ record.get_absolute_url }}}}">{{{{ value }}}}</a>'),
        )
        kwargs.setdefault("attrs", {}).setdefault("td", {})["class"] = "text-nowrap"
        kwargs.setdefault("order_by", ("_name",))
        super().__init__(*args, **kwargs)


# When this row's termination sits on the fan-out side of a breakout cable and the trunk-side peer
# being rendered is an Interface with a matching child interface, append the child interface in
# brackets on the same line, e.g. "TenGigabitEthernet1/1 [TenGigabitEthernet1/1.2]". `peer_var` is
# the loop variable name (the trunk-side peer/endpoint) in the surrounding template.
#
# This inspects only the *immediately attached* cable, so it's right for the one-hop `cable_peer`
# column. For the n-hop `connection` column use `_breakout_endpoint_child_bracket`, which resolves
# the trunk child through the fully-traced path (i.e. also when a patch panel sits in between).
def _breakout_child_brackets(peer_var):
    return (
        "{% for entry in record.get_breakout_trunk_child_interfaces %}"
        "{% if entry.child_interface and entry.trunk_interface == " + peer_var + " %} "
        "[{{ entry.child_interface|hyperlinked_object }}]"
        "{% endif %}{% endfor %}"
    )


# `connection`-column counterpart of `_breakout_child_brackets`: annotate a *connected endpoint*
# with the remote breakout-trunk's child (sub)interface, resolved via the fully-traced cable path so
# it works even when the breakout cable is reached through patch-panel front/rear ports. `endpoint_var`
# is the loop variable naming the connected endpoint in the surrounding template.
def _breakout_endpoint_child_bracket(endpoint_var):
    return (
        "{% with trunk_child=" + endpoint_var + "|breakout_trunk_child_interface:record %}"
        "{% if trunk_child %} [{{ trunk_child|hyperlinked_object }}]{% endif %}"
        "{% endwith %}"
    )


# Fallback markup for the `connection` / `cable_peer` columns when an interface has no cable
# termination of its own. A virtual breakout child interface is never cabled and a cabled interface
# can't have a breakout_position, so the cabled and breakout cases are mutually exclusive and one
# column serves both. `termination_expr` is the template expression yielding the termination object
# to render (or a falsy value for the em-dash). Used with two different expressions:
#
#   - `cable_peer` shows the *one-hop* peer on the parent's breakout cable
#     (`record.get_breakout_lane.far_termination`).
#   - `connection` shows the *n-hop* connected endpoint reached by traversing any intermediate
#     front/rear pass-through ports (`record.get_breakout_connected_endpoint`).
def _breakout_fallback(termination_expr):
    return (
        "{% with far=" + termination_expr + " %}"
        """
{% if far %}
    <a href="{{ far.parent.get_absolute_url }}">{{ far.parent }}</a>
    /
    <span class="mdi {{ far|termination_type_icon }}" title="{{ far|meta:'verbose_name'|capfirst }}"></span>
    <a href="{{ far.get_absolute_url }}">{{ far }}</a>
{% else %}
    <span class="text-secondary">&mdash;</span>
{% endif %}
{% endwith %}
"""
    )


CABLETERMINATION = (
    """
{% load cables %}
{% load helpers %}
{% if value %}
    {% for peer in value %}
        <a href="{{ peer.parent.get_absolute_url }}">{{ peer.parent }}</a>
        /
        <span class="mdi {{ peer|termination_type_icon }}" title="{{ peer|meta:'verbose_name'|capfirst }}"></span>
        <a href="{{ peer.get_absolute_url }}">{{ peer }}</a>"""
    + _breakout_child_brackets("peer")
    + """
        {% if not forloop.last %}<br>{% endif %}
    {% endfor %}
{% else %}"""
    + _breakout_fallback("record.get_breakout_lane.far_termination")
    + """
{% endif %}
"""
)

PATHENDPOINT = (
    """
{% load cables %}
{% load helpers %}
{% if value %}
    {% for endpoint in value %}
        <a href="{{ endpoint.parent.get_absolute_url }}">{{ endpoint.parent }}</a>
        /
        <span class="mdi {{ endpoint|termination_type_icon }}" title="{{ endpoint|meta:'verbose_name'|capfirst }}"></span>
        <a href="{{ endpoint.get_absolute_url }}">{{ endpoint }}</a>"""
    + _breakout_endpoint_child_bracket("endpoint")
    + """
        {% if not forloop.last %}<br>{% endif %}
    {% endfor %}
{% else %}"""
    + _breakout_fallback("record.get_breakout_connected_endpoint")
    + """
{% endif %}
"""
)

CABLE_LENGTH = """
{% if record.length %}
    {{ record.length }} {{ record.get_length_unit_display }}
{% else %}
    <span class="text-secondary">&mdash;</span>
{% endif %}
"""

CABLE_TERMINATION_PARENT = """
{% if value.parent %}
    <a href="{{ value.parent.get_absolute_url }}">{{ value.parent }}</a>
{% endif %}
"""

CABLE_TERMINATIONS_MULTI = """
{% load cables %}
{% load helpers %}
{% for row in value.rows %}
    {% if row.rowspan %}
        {% if row.info.termination %}
            {% if row.info.termination.parent %}
                {{ row.info.termination.parent|hyperlinked_object }} /
            {% endif %}
            <span class="mdi {{ row.info.termination|termination_type_icon }}" title="{{ row.info.termination|meta:'verbose_name'|capfirst }}"></span>
        {% endif %}
        {{ row.info.termination|hyperlinked_object }}
        {% if value.is_breakout %}
            <small class="text-secondary">({{ row.info.side }}{{ row.info.connector }})</small>
        {% endif %}
    {% endif %}
    {% if not forloop.last %}<br>{% endif %}
{% empty %}
    <span class="text-secondary">&mdash;</span>
{% endfor %}
"""

DEVICE_LINK = """
<a href="{% url 'dcim:device' pk=record.pk %}">
    {{ record.name|default:'<span class="badge bg-info">Unnamed device</span>' }}
</a>
"""

INTERFACE_IPADDRESSES = """
{% for ip in record.ip_addresses.all %}
    <a href="{{ ip.get_absolute_url }}">{{ ip }}</a> (<a href="{{ ip.parent.namespace.get_absolute_url }}">{{ ip.parent.namespace }}</a>)<br />
{% endfor %}
"""

INTERFACE_REDUNDANCY_GROUP_INTERFACES = """
<a href="{% url 'dcim:interface_list' %}?interface_redundancy_groups={{record}}">{{ record.interfaces.count }}</a>
"""

INTERFACE_REDUNDANCY_GROUP_INTERFACES_IPADDRESSES = """
{% for ip in record.interface.ip_addresses.all %}
    <a href="{{ ip.get_absolute_url }}">{{ ip }}</a> (<a href="{{ ip.parent.namespace.get_absolute_url }}">{{ ip.parent.namespace }}</a>)<br />
{% endfor %}
"""

INTERFACE_REDUNDANCY_INTERFACE_PRIORITY = """
{% load helpers %}
<span class="badge badge-default">
    {{ record.priority|placeholder }}
</span>
"""

INTERFACE_TAGGED_VLANS = """
{% if record.mode == 'tagged' %}
    {% for vlan in record.tagged_vlans.all %}
        <a href="{{ vlan.get_absolute_url }}">{{ vlan }}</a><br />
    {% endfor %}
{% elif record.mode == 'tagged-all' %}
  All
{% else %}
  <span class="text-secondary">&mdash;</span>
{% endif %}
"""

LINKED_RECORD_COUNT = """
<a href="{{ record.get_absolute_url }}">{{ value }}</a>
"""

TREE_LINK = """
{% load helpers %}
{% if not table.hide_hierarchy_ui %}
{% tree_hierarchy_ui_representation record.tree_depth|as_range table.hide_hierarchy_ui %}
{% endif %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""

LOCATION_TREE_LINK = """
{% load helpers %}
{% spaceless %}
    {% if not table.hide_hierarchy_ui %}
        {% with children_exists=record.children.exists %}
            {% for i in record.ancestors.count|as_range %}
                <span class="nb-subtree"></span>
            {% endfor %}
            {% if table_expandable|default:False %}
                {% if children_exists %}
                    <button class="nb-subtree nb-subtree-expandable"
                            hx-get="{% url 'dcim:location_children' pk=record.pk %}{% django_querystring return_url=return_url %}"
                            hx-indicator="closest .table-responsive"
                            hx-select=".table-responsive tr"
                            hx-select-oob="none"
                            hx-swap="afterend"
                            hx-target="closest tr"
                            type="button"
                    ></button>
                {% else %}
                    {# placeholder for alignment with expandable rows #}
                    <span class="nb-subtree nb-subtree-not-expandable"></span>
                {% endif %}
            {% endif %}
            <a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
            {% if table_expandable|default:False and not table.hide_hierarchy_ui and record.present_in_database %}
                <span class="float-end">
                    {% if children_exists %}
                        <a class="mdi mdi-table-filter"
                           href="{% url 'dcim:location_list' %}?subtree={{ record.pk }}"
                           aria-hidden="true"
                           title="Filter to this location and its descendants"
                        >
                        </a>
                    {% endif %}
                </span>
            {% endif %}
        {% endwith %}
    {% else %}
        <a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
    {% endif %}
{% endspaceless %}
"""


RACKGROUP_ELEVATIONS = """
<li>
    <a href="{% url 'dcim:rack_elevation_list' %}?location={{ record.location.pk }}&rack_group={{ record.pk }}" class="dropdown-item text-primary">
        <span class="mdi mdi-server me-4" aria-hidden="true"></span>View elevations
    </a>
</li>
"""

# Value is a namedtuple that takes a numerator and denominator to pass in.
UTILIZATION_GRAPH = """
{% load helpers %}
{% utilization_graph value %}
"""

#
# Device component buttons
#

# Shared row-action template for any CableTermination subclass (ConsolePort, ConsoleServerPort, PowerPort,
# PowerOutlet, Interface, FrontPort, RearPort, etc.). Each table column passing this in as `prepend_template`
# may also concatenate additional model-specific buttons (e.g. Interface adds an "Add IP address" entry).
CABLE_TERMINATION_BUTTONS = """
{% load helpers %}
{% if record.cable %}
    {% with trace_url=record|viewname:"trace" %}
        <li><a href="{% url trace_url pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant me-4" aria-hidden="true"></span>Trace</a></li>
    {% endwith %}
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif record.is_connectable and perms.dcim.add_cable %}
    <li>
        <a href="{% url 'dcim:cable_add' %}?termination_a_type={{ record|meta:'app_label' }}.{{ record|meta:'model_name' }}&termination_a_id={{ record.pk }}&return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable me-4" aria-hidden="true"></span>Add cable
        </a>
    </li>
{% endif %}
"""

# A breakout child (sub)interface is virtual and never directly cabled, so `CABLE_TERMINATION_BUTTONS`
# offers it no Trace action. When its parent trunk is cabled, trace that lane via the parent's trace
# view plus the lane's `cablepath_id` (resolved by `PathTraceView` to originate from this subinterface).
INTERFACE_BREAKOUT_TRACE_BUTTON = """
{% with breakout_path=record.get_breakout_lane_cable_path %}
    {% if breakout_path %}
        <li><a href="{% url 'dcim:interface_trace' pk=record.parent_interface.pk %}?cablepath_id={{ breakout_path.pk }}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant me-4" aria-hidden="true"></span>Trace</a></li>
    {% endif %}
{% endwith %}
"""

INTERFACE_BUTTONS = (
    """
{% if perms.ipam.add_ipaddress and perms.dcim.change_interface %}
    <li>
        <a href="{% url 'ipam:ipaddress_add' %}?interface={{ record.pk }}&return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-plus-thick me-4" aria-hidden="true"></span>Add IP address
        </a>
    </li>
{% endif %}
"""
    + INTERFACE_BREAKOUT_TRACE_BUTTON
    + CABLE_TERMINATION_BUTTONS
)

DEVICEBAY_BUTTONS = """
{% if perms.dcim.change_devicebay %}
    {% if record.installed_device %}
        <li>
            <a href="{% url 'dcim:devicebay_depopulate' pk=record.pk %}?return_url={{ request.path }}" class="dropdown-item text-danger">
                <span class="mdi mdi-minus-thick me-4" aria-hidden="true"></span>Remove device
            </a>
        </li>
    {% else %}
        <li>
            <a href="{% url 'dcim:devicebay_populate' pk=record.pk %}?return_url={{ request.path }}" class="dropdown-item text-success">
                <span class="mdi mdi-plus-thick me-4" aria-hidden="true"></span>Install device
            </a>
        </li>
    {% endif %}
{% endif %}
"""

MODULEBAY_BUTTONS = """
{% if perms.dcim.change_modulebay and perms.dcim.add_module %}
    {% if not record.installed_module %}
        <li>
            <a href="{% url 'dcim:module_add' %}?parent_module_bay={{ record.pk }}&return_url={{ request.path }}" class="dropdown-item text-success">
                <span class="mdi mdi-plus-thick me-4" aria-hidden="true"></span>Install module
            </a>
        </li>
    {% else %}
        <li>
            <a href="{% url 'dcim:module_delete' pk=record.installed_module.pk %}?return_url={{ request.path }}" class="dropdown-item text-danger">
                <span class="mdi mdi-minus-thick me-4" aria-hidden="true"></span>Delete installed module
            </a>
        </li>
    {% endif %}
{% endif %}
"""

PARENT_DEVICE = """
{% load helpers %}
{% if record.parent_bay %}
    {{ record.parent_bay.device|hyperlinked_object }}
{% else %}
    {{ None|placeholder }}
{% endif %}
"""
