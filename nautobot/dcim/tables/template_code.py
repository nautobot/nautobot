CABLETERMINATION = """
{% if value %}
    <a href="{{ value.parent.get_absolute_url }}">{{ value.parent }}</a>
    <i class="mdi mdi-chevron-right"></i>
    <a href="{{ value.get_absolute_url }}">{{ value }}</a>
{% else %}
    &mdash;
{% endif %}
"""

PATHENDPOINT = """
{% if value.destination %}
    <a href="{{ value.destination.parent.get_absolute_url }}">{{ value.destination.parent }}</a>
    <i class="mdi mdi-chevron-right"></i>
    <a href="{{ value.destination.get_absolute_url }}">{{ value.destination }}</a>
    {% with traced_path=value.origin.trace %}
        {% for near_end, cable, far_end in traced_path %}
            {% if near_end.circuit %}
                <small>via
                    <a href="{{ near_end.circuit.get_absolute_url }}">
                        {{ near_end.circuit }}
                        {{ near_end.circuit.provider }}
                    </a>
                </small>
            {% endif %}
        {% endfor %}
    {% endwith %}
{% else %}
    &mdash;
{% endif %}
"""

CABLE_LENGTH = """
{% if record.length %}{{ record.length }} {{ record.get_length_unit_display }}{% else %}&mdash;{% endif %}
"""

CABLE_TERMINATION_PARENT = """
{% if value.device %}
    <a href="{{ value.device.get_absolute_url }}">{{ value.device }}</a>
{% elif value.circuit %}
    <a href="{{ value.circuit.get_absolute_url }}">{{ value.circuit }}</a>
{% elif value.power_panel %}
    <a href="{{ value.power_panel.get_absolute_url }}">{{ value.power_panel }}</a>
{% endif %}
"""

DEVICE_LINK = """
<a href="{% url 'dcim:device' pk=record.pk %}">
    {{ record.name|default:'<span class="label label-info">Unnamed device</span>' }}
</a>
"""

DEVICEBAY_STATUS = """
{% if record.installed_device_id %}
    {% load helpers %}
    <span class="label" style="color: {{ record.installed_device.status.color|fgcolor }}; background-color: #{{ record.installed_device.status.color }}">
        {{ record.installed_device.get_status_display }}
    </span>
{% else %}
    <span class="label label-default">Vacant</span>
{% endif %}
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

INTERFACE_REDUNDANCY_GROUP_STATUS = """
{% load helpers %}
<span class="label"
    style="color: {{ record.interface_redundancy_group.status.color|fgcolor }};
    background-color: #{{ record.interface_redundancy_group.status.color }}">
    {{ record.interface_redundancy_group.get_status_display }}
</span>
"""

INTERFACE_REDUNDANCY_INTERFACE_PRIORITY = """
{% load helpers %}
<span class="badge badge-default">
    {{ record.priority|placeholder }}
</span>
"""

INTERFACE_REDUNDANCY_INTERFACE_STATUS = """
{% load helpers %}
<span class="label" style="color: {{ record.interface.status.color|fgcolor }}; background-color: #{{ record.interface.status.color }}">
    {{ record.interface.get_status_display }}
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
  &mdash;
{% endif %}
"""

LINKED_RECORD_COUNT = """
<a href="{{ record.get_absolute_url }}">{{ value }}</a>
"""

TREE_LINK = """
{% load helpers %}
{% for i in record.tree_depth|as_range %}
    <i class="mdi mdi-circle-small"></i>
{% endfor %}
<a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
"""


POWERFEED_CABLE = """
<a href="{{ value.get_absolute_url }}">{{ value }}</a>
<a href="{% url 'dcim:powerfeed_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace">
    <i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i>
</a>
"""

POWERFEED_CABLETERMINATION = """
<a href="{{ value.parent.get_absolute_url }}">{{ value.parent }}</a>
<i class="mdi mdi-chevron-right"></i>
<a href="{{ value.get_absolute_url }}">{{ value }}</a>
"""

RACKGROUP_ELEVATIONS = """
<a href="{% url 'dcim:rack_elevation_list' %}?location={{ record.location.pk }}&rack_group={{ record.pk }}" class="btn btn-xs btn-primary" title="View elevations">
    <i class="mdi mdi-server"></i>
</a>
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
    <a href="{% url 'dcim:consoleport_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace"><i class="mdi mdi-transit-connection-variant"></i></a>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable %}
{% elif perms.dcim.add_cable %}
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i></a>
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-lan-connect" aria-hidden="true"></i></a>
    <span class="dropdown">
        <button type="button" class="btn btn-success btn-xs dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Connect cable">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
        </button>
        <ul class="dropdown-menu dropdown-menu-right">
            <li><a href="{% url 'dcim:consoleport_connect' termination_a_id=record.pk termination_b_type='console-server-port' %}?return_url={% url 'dcim:device_consoleports' pk=object.pk %}">Console Server Port</a></li>
            <li><a href="{% url 'dcim:consoleport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={% url 'dcim:device_consoleports' pk=object.pk %}">Front Port</a></li>
            <li><a href="{% url 'dcim:consoleport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={% url 'dcim:device_consoleports' pk=object.pk %}">Rear Port</a></li>
        </ul>
    </span>
{% endif %}
"""

CONSOLESERVERPORT_BUTTONS = """
{% if record.cable %}
    <a href="{% url 'dcim:consoleserverport_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace"><i class="mdi mdi-transit-connection-variant"></i></a>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable %}
{% elif perms.dcim.add_cable %}
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i></a>
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-lan-connect" aria-hidden="true"></i></a>
    <span class="dropdown">
        <button type="button" class="btn btn-success btn-xs dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Connect cable">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
        </button>
        <ul class="dropdown-menu dropdown-menu-right">
            <li><a href="{% url 'dcim:consoleserverport_connect' termination_a_id=record.pk termination_b_type='console-port' %}?return_url={% url 'dcim:device_consoleserverports' pk=object.pk %}">Console Port</a></li>
            <li><a href="{% url 'dcim:consoleserverport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={% url 'dcim:device_consoleserverports' pk=object.pk %}">Front Port</a></li>
            <li><a href="{% url 'dcim:consoleserverport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={% url 'dcim:device_consoleserverports' pk=object.pk %}">Rear Port</a></li>
        </ul>
    </span>
{% endif %}
"""

POWERPORT_BUTTONS = """
{% if record.cable %}
    <a href="{% url 'dcim:powerport_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace"><i class="mdi mdi-transit-connection-variant"></i></a>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable %}
{% elif perms.dcim.add_cable %}
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i></a>
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-lan-connect" aria-hidden="true"></i></a>
    <span class="dropdown">
        <button type="button" class="btn btn-success btn-xs dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Connect cable">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
        </button>
        <ul class="dropdown-menu dropdown-menu-right">
            <li><a href="{% url 'dcim:powerport_connect' termination_a_id=record.pk termination_b_type='power-outlet' %}?return_url={% url 'dcim:device_powerports' pk=object.pk %}">Power Outlet</a></li>
            <li><a href="{% url 'dcim:powerport_connect' termination_a_id=record.pk termination_b_type='power-feed' %}?return_url={% url 'dcim:device_powerports' pk=object.pk %}">Power Feed</a></li>
        </ul>
    </span>
{% endif %}
"""

POWEROUTLET_BUTTONS = """
{% if record.cable %}
    <a href="{% url 'dcim:poweroutlet_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace"><i class="mdi mdi-transit-connection-variant"></i></a>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable %}
{% elif perms.dcim.add_cable %}
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i></a>
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-lan-connect" aria-hidden="true"></i></a>
    <a href="{% url 'dcim:poweroutlet_connect' termination_a_id=record.pk termination_b_type='power-port' %}?return_url={% url 'dcim:device_poweroutlets' pk=object.pk %}" title="Connect" class="btn btn-success btn-xs">
        <i class="mdi mdi-ethernet-cable" aria-hidden="true"></i>
    </a>
{% endif %}
"""

INTERFACE_BUTTONS = """
{% if perms.ipam.add_ipaddress and perms.dcim.change_interface %}
    <a href="{% url 'ipam:ipaddress_add' %}?interface={{ record.pk }}&return_url={% url 'dcim:device_interfaces' pk=object.pk %}" class="btn btn-xs btn-success" title="Add IP address">
        <i class="mdi mdi-plus-thick" aria-hidden="true"></i>
    </a>
{% endif %}
{% if record.cable %}
    <a href="{% url 'dcim:interface_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace"><i class="mdi mdi-transit-connection-variant"></i></a>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable %}
{% elif record.is_connectable and perms.dcim.add_cable %}
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i></a>
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-lan-connect" aria-hidden="true"></i></a>
    <span class="dropdown">
        <button type="button" class="btn btn-success btn-xs dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Connect cable">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
        </button>
        <ul class="dropdown-menu dropdown-menu-right">
            <li><a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='interface' %}?return_url={% url 'dcim:device_interfaces' pk=object.pk %}">Interface</a></li>
            <li><a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={% url 'dcim:device_interfaces' pk=object.pk %}">Front Port</a></li>
            <li><a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={% url 'dcim:device_interfaces' pk=object.pk %}">Rear Port</a></li>
            <li><a href="{% url 'dcim:interface_connect' termination_a_id=record.pk termination_b_type='circuit-termination' %}?return_url={% url 'dcim:device_interfaces' pk=object.pk %}">Circuit Termination</a></li>
        </ul>
    </span>
{% endif %}
"""

FRONTPORT_BUTTONS = """
{% if record.cable %}
    <a href="{% url 'dcim:frontport_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace"><i class="mdi mdi-transit-connection-variant"></i></a>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable %}
{% elif perms.dcim.add_cable %}
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i></a>
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-lan-connect" aria-hidden="true"></i></a>
    <span class="dropdown">
        <button type="button" class="btn btn-success btn-xs dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Connect cable">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
        </button>
        <ul class="dropdown-menu dropdown-menu-right">
            <li><a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='interface' %}?return_url={% url 'dcim:device_frontports' pk=object.pk %}">Interface</a></li>
            <li><a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='console-server-port' %}?return_url={% url 'dcim:device_frontports' pk=object.pk %}">Console Server Port</a></li>
            <li><a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='console-port' %}?return_url={% url 'dcim:device_frontports' pk=object.pk %}">Console Port</a></li>
            <li><a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={% url 'dcim:device_frontports' pk=object.pk %}">Front Port</a></li>
            <li><a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={% url 'dcim:device_frontports' pk=object.pk %}">Rear Port</a></li>
            <li><a href="{% url 'dcim:frontport_connect' termination_a_id=record.pk termination_b_type='circuit-termination' %}?return_url={% url 'dcim:device_frontports' pk=object.pk %}">Circuit Termination</a></li>
        </ul>
    </span>
{% endif %}
"""

REARPORT_BUTTONS = """
{% if record.cable %}
    <a href="{% url 'dcim:rearport_trace' pk=record.pk %}" class="btn btn-primary btn-xs" title="Trace"><i class="mdi mdi-transit-connection-variant"></i></a>
    {% include 'dcim/inc/cable_toggle_buttons.html' with cable=record.cable %}
{% elif perms.dcim.add_cable %}
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-transit-connection-variant" aria-hidden="true"></i></a>
    <a href="#" class="btn btn-default btn-xs disabled"><i class="mdi mdi-lan-connect" aria-hidden="true"></i></a>
    <span class="dropdown">
        <button type="button" class="btn btn-success btn-xs dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false" title="Connect cable">
            <span class="mdi mdi-ethernet-cable" aria-hidden="true"></span>
        </button>
        <ul class="dropdown-menu dropdown-menu-right">
            <li><a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='interface' %}?return_url={% url 'dcim:device_rearports' pk=object.pk %}">Interface</a></li>
            <li><a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='front-port' %}?return_url={% url 'dcim:device_rearports' pk=object.pk %}">Front Port</a></li>
            <li><a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='rear-port' %}?return_url={% url 'dcim:device_rearports' pk=object.pk %}">Rear Port</a></li>
            <li><a href="{% url 'dcim:rearport_connect' termination_a_id=record.pk termination_b_type='circuit-termination' %}?return_url={% url 'dcim:device_rearports' pk=object.pk %}">Circuit Termination</a></li>
        </ul>
    </span>
{% endif %}
"""

DEVICEBAY_BUTTONS = """
{% if perms.dcim.change_devicebay %}
    {% if record.installed_device %}
        <a href="{% url 'dcim:devicebay_depopulate' pk=record.pk %}?return_url={% url 'dcim:device_devicebays' pk=object.pk %}" class="btn btn-danger btn-xs">
            <i class="mdi mdi-minus-thick" aria-hidden="true" title="Remove device"></i>
        </a>
    {% else %}
        <a href="{% url 'dcim:devicebay_populate' pk=record.pk %}?return_url={% url 'dcim:device_devicebays' pk=object.pk %}" class="btn btn-success btn-xs">
            <i class="mdi mdi-plus-thick" aria-hidden="true" title="Install device"></i>
        </a>
    {% endif %}
{% endif %}
"""
