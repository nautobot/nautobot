# Computed Fields

Computed fields are largely based on custom fields. See the overview of [Custom Fields](./custom-fields.md). As the name suggests, computed fields serve the need for a custom field where the value is generated using data that Nautobot stores in it's database.

As an example, for use by some automation system, you might want to be able to have an automatically generated field on the Device model that combines the name of the device and the uppercased site name. To do that, you would define a Jinja template for this field that looks like such:
```jinja2
{{ obj.name }}_{{ obj.site.name | upper }}
```

!!! note
    Everytime an object with this computed field is loaded, the template gets rendered. It's important to note that these values are not stored in the database and are dynamically rendered.

## Creating Computed Fields

Computed fields can be created through the Nautobot UI under Extensibility > Computed Fields.

Each computed field must have a slug and a label.
- Slug must be a simple, database-friendly string, e.g. `device_with_site`
- Label is used as the human-friendly display name for this field in the UI, for example, `Device With Site`.

Similar to custom fields, the weight value is used to order computed fields within a form. A description can also be provided, and will appear beneath the field in a form.

Computed fields must define a template from which to render their values. The template field must contain a valid Jinja2 template string.

A computed field must be assigned to an object types, or model, in Nautobot. Once created, computed fields will automatically appear as part of these models in the web UI. See notes about viewing computed fields via the REST API below.


## Computed Field Template Context

Computed field templates can utilize the context of the object the field is being rendered on. This context is available for use in templates via the `obj` keyword. As an example, for a computed field being rendered on a Device object, the name of the site that this Device belongs to can be accessed like this:
```jinja2
{{ obj.site.name }}
```

## Computed Fields and the REST API

When retrieving an object via the REST API, computed field data is not included by default in order to prevent potentially computationally expensive rendering operations that degrade the user experience. In order to retrieve computed field data, you must use the `opt_in_fields` query parameter.

Take a look at an example URL that includes computed field data:
```
http://localhost:8080/api/dcim/sites?opt_in_fields=computed_fields
```
When explicitly requested as such, computed field data will be included in the `computed_fields` attribute. For example, below is the partial output of a site with one computed field defined:
```json
{
    "id": 123,
    "url": "http://localhost:8080/api/dcim/sites/123/",
    "name": "Raleigh 42",
    ...
    "computed_fields": {
        "site_name_uppercase": "RALEIGH"
    },
    ...
```

!!! note
    Note that the slug field is used as the key names for items in the `computed_fields` attribute.
