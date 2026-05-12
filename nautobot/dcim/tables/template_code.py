CABLETERMINATION = """
{% if value %}
    {% for peer in value %}
        <a href="{{ peer.parent.get_absolute_url }}">{{ peer.parent }}</a>
        <i class="mdi mdi-chevron-right"></i>
        <a href="{{ peer.get_absolute_url }}">{{ peer }}</a>
        {% if not forloop.last %}<br>{% endif %}
    {% endfor %}
{% else %}
    <span class="text-secondary">&mdash;</span>
{% endif %}
"""

PATHENDPOINT = """
{% if value %}
    {% for endpoint in value %}
        <a href="{{ endpoint.parent.get_absolute_url }}">{{ endpoint.parent }}</a>
        <i class="mdi mdi-chevron-right"></i>
        <a href="{{ endpoint.get_absolute_url }}">{{ endpoint }}</a>
        {% if not forloop.last %}<br>{% endif %}
    {% endfor %}
{% else %}
    <span class="text-secondary">&mdash;</span>
{% endif %}
"""

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
{% for endpoint in value %}
    {% with term=endpoint.termination %}
        {% if term %}
            {% termination_type_icon term as t_icon %}
            <span class="mdi {{ t_icon }}" title="{{ term|meta:'verbose_name'|capfirst }}"></span>
            {% if term.parent %}
                <a href="{{ term.parent.get_absolute_url }}">{{ term.parent }}</a> /
            {% endif %}
            <a href="{{ term.get_absolute_url }}">{{ term }}</a>
            {% if endpoint.connector is not None %}
                <small class="text-muted">({{ endpoint.cable_end }}{{ endpoint.connector }})</small>
            {% endif %}
            {% if not forloop.last %}<br>{% endif %}
        {% endif %}
    {% endwith %}
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


POWERFEED_CABLE = """
<a href="{{ value.get_absolute_url }}">{{ value }}</a>
<a href="{% url 'dcim:powerfeed_trace' pk=record.pk %}" class="btn btn-primary btn-sm" title="Trace">
    <i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i>
</a>
"""

POWERFEED_CABLETERMINATION = """
<a href="{{ value.parent.get_absolute_url }}">{{ value.parent }}</a>
<i class="mdi mdi-chevron-right"></i>
<a href="{{ value.get_absolute_url }}">{{ value }}</a>
"""

RACKGROUP_ELEVATIONS = """
<li>
    <a href="{% url 'dcim:rack_elevation_list' %}?location={{ record.location.pk }}&rack_group={{ record.pk }}" class="dropdown-item text-primary">
        <span class="mdi mdi-server" aria-hidden="true"></span>
        View elevations
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

CONSOLEPORT_BUTTONS = """
{% if record.cable %}
    <li><a href="{% url 'dcim:consoleport_trace' pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif perms.dcim.add_cable %}
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-lan-connect" aria-hidden="true"></span>Mark installed</a></li>
    <li>
        <a href="{% url 'dcim:consoleport_connect' termination_a_id=record.pk termination_b_type='console-server-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Console Server Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:consoleport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Front Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:consoleport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Rear Port
        </a>
    </li>
{% endif %}
"""

CONSOLESERVERPORT_BUTTONS = """
{% if record.cable %}
    <li><a href="{% url 'dcim:consoleserverport_trace' pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif perms.dcim.add_cable %}
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-lan-connect" aria-hidden="true"></span>Mark installed</a></li>
    <li>
        <a href="{% url 'dcim:consoleserverport_connect' termination_a_id=record.pk termination_b_type='console-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Console Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:consoleserverport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Front Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:consoleserverport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Rear Port
        </a>
    </li>
{% endif %}
"""

POWERPORT_BUTTONS = """
{% if record.cable %}
    <li><a href="{% url 'dcim:powerport_trace' pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif perms.dcim.add_cable %}
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-lan-connect" aria-hidden="true"></span>Mark installed</a></li>
    <li>
        <a href="{% url 'dcim:powerport_connect' termination_a_id=record.pk termination_b_type='power-outlet' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Power Outlet
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:powerport_connect' termination_a_id=record.pk termination_b_type='power-feed' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Power Feed
        </a>
    </li>
{% endif %}
"""

POWEROUTLET_BUTTONS = """
{% if record.cable %}
    <li><a href="{% url 'dcim:poweroutlet_trace' pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif perms.dcim.add_cable %}
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-lan-connect" aria-hidden="true"></span>Mark installed</a></li>
    <li>
        <a href="{% url 'dcim:poweroutlet_connect' termination_a_id=record.pk termination_b_type='power-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect
        </a>
    </li>
{% endif %}
"""

INTERFACE_BUTTONS = """
{% if perms.ipam.add_ipaddress and perms.dcim.change_interface %}
    <li>
        <a href="{% url 'ipam:ipaddress_add' %}?interface={{ record.pk }}&return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-plus-thick" aria-hidden="true"></span>
            Add IP address
        </a>
    </li>
{% endif %}
{% if record.cable %}
    <li><a href="{% url 'dcim:interface_trace' pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif record.is_connectable and perms.dcim.add_cable %}
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-lan-connect" aria-hidden="true"></span>Mark installed</a></li>
    <li>
        <a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='interface' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Interface
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Front Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Rear Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='circuit-termination' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Circuit Termination
        </a>
    </li>
{% endif %}
"""

FRONTPORT_BUTTONS = """
{% if record.cable %}
    <li><a href="{% url 'dcim:frontport_trace' pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif perms.dcim.add_cable %}
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-lan-connect" aria-hidden="true"></span>Mark installed</a></li>
    <li>
        <a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='interface' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Interface
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='console-server-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Console Server Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='console-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Console Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Front Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Rear Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='circuit-termination' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Circuit Termination
        </a>
    </li>
{% endif %}
"""

REARPORT_BUTTONS = """
{% if record.cable %}
    <li><a href="{% url 'dcim:rearport_trace' pk=record.pk %}" class="dropdown-item text-primary"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable termination=record %}
{% elif perms.dcim.add_cable %}
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-transit-connection-variant" aria-hidden="true"></span>Trace</a></li>
    <li><a class="dropdown-item disabled" aria-disabled="true"><span class="mdi mdi-lan-connect" aria-hidden="true"></span>Mark installed</a></li>
    <li>
        <a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='interface' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Interface
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Front Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Rear Port
        </a>
    </li>
    <li>
        <a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='circuit-termination' %}?return_url={{ request.path }}" class="dropdown-item text-success">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
            Connect to Circuit Termination
        </a>
    </li>
{% endif %}
"""

DEVICEBAY_BUTTONS = """
{% if perms.dcim.change_devicebay %}
    {% if record.installed_device %}
        <li>
            <a href="{% url 'dcim:devicebay_depopulate' pk=record.pk %}?return_url={{ request.path }}" class="dropdown-item text-danger">
                <span class="mdi mdi-minus-thick" aria-hidden="true"></span>
                Remove device
            </a>
        </li>
    {% else %}
        <li>
            <a href="{% url 'dcim:devicebay_populate' pk=record.pk %}?return_url={{ request.path }}" class="dropdown-item text-success">
                <span class="mdi mdi-plus-thick" aria-hidden="true"></span>
                Install device
            </a>
        </li>
    {% endif %}
{% endif %}
"""

MODULE_BUTTONS = """
<li><a href="{% url 'dcim:module' pk=record.pk %}" class="dropdown-item"><span class="mdi mdi-information-outline" aria-hidden="true"></span>Details</a></li>
"""

MODULEBAY_BUTTONS = """
{% if perms.dcim.change_modulebay and perms.dcim.add_module %}
    {% if not record.installed_module %}
        <li>
            <a href="{% url 'dcim:module_add' %}?parent_module_bay={{ record.pk }}&return_url={{ request.path }}" class="dropdown-item text-success">
                <span class="mdi mdi-plus-thick" aria-hidden="true"></span>
                Install module
            </a>
        </li>
    {% else %}
        <li>
            <a href="{% url 'dcim:module_delete' pk=record.installed_module.pk %}?return_url={{ request.path }}" class="dropdown-item text-danger">
                <span class="mdi mdi-minus-thick" aria-hidden="true"></span>
                Delete installed module
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
