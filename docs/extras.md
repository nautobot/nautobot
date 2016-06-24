<h1>Extras</h1>

This section entails features of NetBox which are not crucial to its primary functions, but that provide additional value.

[TOC]

# Export Templates

NetBox allows users to define custom templates that can be used when exporting objects. To create an export template, navigate to Extras > Export Templates under the admin interface.

Each export template is associated with a certain type of object. For instance, if you create an export template for VLANs, your custom template will appear under the "Export" button on the VLANs list.

Export templates are written in [Django's template language](https://docs.djangoproject.com/en/1.9/ref/templates/language/), which is very similar to Jinja2. The list of objects returned from the database is stored in the `queryset` variable. Typically, you'll want to iterate through this list using a for loop.

A MIME type and file extension can optionally be defined for each export template. The default MIME type is `text/plain`.

## Example

Here's an example device export template that will generate a simple Nagios configuration from a list of devices.

```
{% for d in queryset %}{% if d.status and d.primary_ip %}define host{
        use                     generic-switch
        host_name               {{ d.name }}
        address                 {{ d.primary_ip.address.ip }}
}
{% endif %}{% endfor %}
```

The generated output will look something like this:

```
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

# Graphs

NetBox does not generate graphs itself. This feature allows you to embed contextual graphs from an external resources inside certain NetBox views. Each embedded graph must be defined with the following parameters:

* **Type:** Interface, provider, or site. This determines where the graph will be displayed.
* **Weight:** Determines the order in which graphs are displayed (lower weights are displayed first). Graphs with equal weights will be ordered alphabetically by name.
* **Name:** The title to display above the graph.
* **Source URL:** The source of the image to be embedded. The associated object will be available as a template variable named `obj`.
* **Link URL (optional):** A URL to which the graph will be linked. The associated object will be available as a template variable named `obj`.
