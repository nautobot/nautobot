# Export Templates

Nautobot allows users to define custom templates that can be used when exporting objects. To create an export template, navigate to Extensibility > Automation > Export Templates under the navigation bar. Export templates can also be managed within an external Git repository if desired.

Each export template is associated with a certain type of object. For instance, if you create an export template for VLANs, your custom template will appear in the **Actions** menu of the VLANs list view, under the **Export Templates** heading. Choosing it exports the list with that template straight away, without opening a dialog.

Exporting with a template runs the `Export Object List` system Job, like any other export from a list view. So you need _run_ permission on that Job, _view_ permission on the object type, and _view_ permission on the export template itself, and the Job's [size and time limits](../feature-guides/import-and-export.md#limits) apply. See [Importing and Exporting Objects](../feature-guides/import-and-export.md) for more about exports, and the [Export Job permission recipe](../administration/guides/permissions.md#export-job).

Export templates must be written in [Jinja2](https://jinja.palletsprojects.com/).

The list of objects being exported is stored in the `queryset` variable, which you'll typically want to iterate through using a `for` loop. It contains only the objects the user running the export is permitted to view, filtered and sorted as in the list view the export was started from. Object properties can be accessed by name. For example:

```jinja2
{% for rack in queryset %}
Rack: {{ rack.name }}
Location: {{ rack.location.name }}
Height: {{ rack.u_height }}U
{% endfor %}
```

!!! note
    To access `custom fields` of an object within a template, use the `cf` attribute. For example, `{{ obj.cf.color }}` will return the value (if any) for the custom field with a key of `color` on `obj`.

    Similarly, to access `computed fields` of an object within a template, use the `get_computed_field()` method. For example, `{{ obj.get_computed_field("site_code") }}` will return the value (if any) for the computed field with a key of `site_code` on `obj`.

A file extension can optionally be defined for each export template; it is added to the name of the exported file. A MIME type can also be defined, but exports from the list view don't currently use it.

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
