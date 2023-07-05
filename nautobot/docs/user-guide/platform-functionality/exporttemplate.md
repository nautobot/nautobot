# Export Templates

Nautobot allows users to define custom templates that can be used when exporting objects. To create an export template, navigate to Extensibility > Automation > Export Templates under the navigation bar. Export templates can also be managed within an external Git repository if desired.

Each export template is associated with a certain type of object. For instance, if you create an export template for VLANs, your custom template will appear under the "Export" button on the VLANs list.

Export templates must be written in [Jinja2](https://jinja.palletsprojects.com/).

The list of objects returned from the database when rendering an export template is stored in the `queryset` variable, which you'll typically want to iterate through using a `for` loop. Object properties can be access by name. For example:

```jinja2
{% for rack in queryset %}
Rack: {{ rack.name }}
Location: {{ rack.location.name }}
Height: {{ rack.u_height }}U
{% endfor %}
```

!!! note
    To access custom fields of an object within a template, use the `cf` attribute. For example, `{{ obj.cf.color }}` will return the value (if any) for the custom field with a key of `color` on `obj`.

A MIME type and file extension can optionally be defined for each export template. The default MIME type is `text/plain`.

## Example

Here's an example device export template that will generate a simple Nagios configuration from a list of devices.

```jinja2
{% for device in queryset %}{% if device.status and device.primary_ip %}define host{
        use                     generic-switch
        host_name               {{ device.name }}
        address                 {{ device.primary_ip.address.ip }}
}
{% endif %}{% endfor %}
```

The generated output will look something like this:

```no-highlight
define host{
        use                     generic-switch
        host_name               switch1
        address                 192.0.2.1
}
define host{
        use                     generic-switch
        host_name               switch2
        address                 192.0.2.2
}
define host{
        use                     generic-switch
        host_name               switch3
        address                 192.0.2.3
}
```
