# Computed Fields

+++ 1.1.0

Computed fields are very similar in design and implementation to custom fields. See the overview of [Custom Fields](./customfield.md). As the name suggests, computed fields serve the need for a custom field where the value is generated using data that Nautobot stores in its database and merging it into a Jinja2 template and associated filters.

As an example, within your automation system, you may want to be able to have an automatically generated field on the Device model that combines the name of the device and the location name in uppercase. To do that, you would define a Jinja2 template for this field that looks like such:

```jinja2
{{ obj.name }}_{{ obj.location.name | upper }}
```

!!! important
    Every time an object with this computed field is loaded, the template gets re-rendered with the currently available data. These rendered values are not stored in the database; only the Jinja2 template is stored.

+/- 2.0.0
    Computed field model's `label` attribute will be used exclusively for display purposes in the UI.

    Computed field model's `slug` attribute was renamed to `key` (unique for all Computed Field instances), which contains a GraphQL-safe string to be used in the API and GraphQL.

    These changes do not require users to do any manual work as they are properly handled by data migrations during the upgrade from Nautobot v1.x to v2.0.

## Creating Computed Fields

Computed fields can be created through the Nautobot UI under **Extensibility > Computed Fields**.

Each computed field must have a key and a label.

- Key must be a simple, database-friendly string, e.g. `device_with_location`
- Label is used as the human-friendly display name for this field in the UI, for example, `Device With Location`.

!!! tip
    Because computed field data can be included in the REST API and in GraphQL, we strongly recommend that when defining a computed field, you provide a key that contains underscores rather than dashes (`my_field_key`, not `my-field-key`), as some features may not work optimally if dashes are included in the key.

Similar to custom fields, the weight value is used to order computed fields within a form. A description can also be provided, and will appear beneath the field in a form.

Computed fields must define a template from which to render their values. The template field must contain a valid Jinja2 template string.

A computed field must be assigned to an object type, or model, in Nautobot. Once created, a computed field will automatically appear as part of this model's display. See notes about viewing computed fields via the REST API below.

When creating a computed field, if "Move to Advanced tab" is checked, this computed field won't appear on the object's main detail tab in the UI, but will appear in the "Advanced" tab. This is useful when the requirement is to hide this field from the main detail tab when, for instance, it is only required for machine-to-machine communication and not user consumption.

## Computed Field Template Context

Computed field templates can utilize the context of the object the field is being rendered on. This context is available for use in templates via the `obj` keyword. As an example, for a computed field being rendered on a Device object, the name of the location that this Device belongs to can be accessed like this:

```jinja2
{{ obj.location.name }}
```

!!! note
    To access custom fields of an object within a template, use the `cf` attribute. For example, `{{ obj.cf.color }}` will return the value (if any) for the custom field with a key of `color` on `obj`.

## Computed Field Template Filters

Computed field templates can also utilize built-in Jinja2 filters or custom ones that have been registered via plugins. These filters can be used by providing the name of the filter function. As an example:

```jinja2
{{ obj.location.name | leet_speak }}
```

See the documentation on [built-in filters](./template-filters.md) or [registering custom Jinja2 filters](../../development/apps/api/platform-features/jinja2-filters.md) in plugins.

## Computed Fields and the REST API

When retrieving an object via the REST API, computed field data is not included by default in order to prevent potentially computationally expensive rendering operations that degrade the user experience. In order to retrieve computed field data, you must use the `include` query parameter.

Take a look at an example URL that includes computed field data:

```no-highlight
http://localhost:8080/api/dcim/locations?include=computed_fields
```

When explicitly requested as such, computed field data will be included in the `computed_fields` attribute. For example, below is the partial output of a location with one computed field defined:

```json
{
    "id": 123,
    "url": "http://localhost:8080/api/dcim/locations/123/",
    "name": "Raleigh 42",
    ...
    "computed_fields": {
        "location_name_uppercase": "RALEIGH"
    },
    ...
```

!!! note
    The `key` value of each computed field is used as the key name for items in the `computed_fields` attribute.
