# Custom Fields

Each model in Nautobot is represented in the database as a discrete table, and each attribute of a model exists as a column within its table. For example, sites are stored in the `dcim_site` table, which has columns named `name`, `facility`, `physical_address`, and so on. As new attributes are added to objects throughout the development of Nautobot, tables are expanded to include new columns.

However, some users might want to store additional object attributes that are somewhat esoteric in nature, and that would not make sense to include in the core Nautobot database schema. For instance, suppose your organization needs to associate each device with a ticket number correlating it with an internal support system record. This is certainly a legitimate use for Nautobot, but it's not a common enough need to warrant including a field for _every_ Nautobot installation. Instead, you can create a custom field to hold this data.

Within the database, custom fields are stored as JSON data directly alongside each object. This alleviates the need for complex queries when retrieving objects.

## Creating Custom Fields

Custom fields can be created through the UI under **Extensibility > Miscellaneous > Custom Fields** or through the REST API.

Nautobot supports these custom field types:

* Text: Free-form text (up to 255 characters)
* Integer: A whole number (positive or negative)
* Boolean: True or false
* Date: A date in ISO 8601 format (YYYY-MM-DD)
* URL: This will be presented as a link in the web UI
* JSON: Arbitrary JSON data
* Selection: A selection of one of several pre-defined custom choices
* Multiple selection: A selection field which supports the assignment of multiple values

+++ 1.3.0
    Support for JSON-type custom fields was added.

Each custom field must have a name and slug; this should be a simple database-friendly string, e.g. `tps_report`. You may also assign a corresponding human-friendly label (e.g. "TPS report"); the label will be displayed on web forms. A weight is also required: Higher-weight fields will be ordered lower within a form. (The default weight is 100.) If a description is provided, it will appear beneath the field in a form.

+/- 1.4.0
    Custom fields now have both a `name` and a `slug`; in older versions there was no `slug` field. When migrating existing data to Nautobot 1.4.0 or later, the `label` and `slug` will be automatically populated for existing custom fields if necessary.

!!! warning
    In all Nautobot 1.x versions, the custom field `name` is used as the key to store and retrieve custom field data via the database and GraphQL. In a future major release, the `name` field will be removed and custom field data will be accessible via the `slug` instead. See [below](#custom-fields-and-the-rest-api) for REST API versioning behavior in this area.

!!! tip
    Because custom field data is included in the database, in the REST API and in GraphQL, we strongly recommend that when defining a custom field, you provide a `slug` that contains underscores rather than dashes (`my_field_slug`, not `my-field-slug`), as some features may not work optimally if dashes are included in the slug. Similarly, the provided `name` should also contain only alphanumeric characters and underscores, as it is currently treated in some cases like a slug.

!!! note
    The name, slug, and type of a custom field cannot be modified once created, so take care in defining these fields. This helps to reduce the possibility of inconsistent data and enforces the importance of thinking about the data model when defining a new custom field.

Marking a field as required will force the user to provide a value for the field when creating a new object or when saving an existing object. A default value for the field may also be provided. Use "true" or "false" for boolean fields, or the exact value of a choice for selection fields.

The filter logic controls how values are matched when filtering objects by the custom field. Loose filtering (the default) matches on a partial value, whereas exact matching requires a complete match of the given string to a field's value. For example, exact filtering with the string "red" will only match the exact value "red", whereas loose filtering will match on the values "red", "red-orange", or "bored". Setting the filter logic to "disabled" disables filtering by the field entirely.

+/- 1.4.0
    Custom field [extended filtering](../../rest-api/filtering.md#lookup-expressions) introduced extended lookup expression filters for `exact` and `icontains`, duplicating the functionality of both the `Strict` and `Loose` settings.

A custom field must be assigned to one or more object types, or models, in Nautobot. Once created, custom fields will automatically appear as part of these models in the web UI and REST API.

When creating a custom field, if "Move to Advanced tab" is checked, this custom field won't appear on the object's main detail tab in the UI, but will appear in the "Advanced" tab. This is useful when the requirement is to hide this field from the main detail tab when, for instance, it is only required for machine-to-machine communication and not user consumption.

### Custom Field Validation

Nautobot supports limited custom validation for custom field values. Following are the types of validation enforced for each field type:

* Text: Regular expression (optional)
* URL: Regular expression (optional)
* Integer: Minimum and/or maximum value (optional)
* JSON: If not empty, this field must contain valid JSON data
* Selection: Must exactly match one of the prescribed choices
    * Selection Fields: Regular expression (optional)

### Custom Selection Fields

Choices are stored as independent values and are assigned a numeric weight which affects their ordering in selection lists and dropdowns. Note that choice values are saved exactly as they appear, so it's best to avoid superfluous punctuation or symbols where possible.

A regular expression can optionally be defined on custom selection choices to validate the defined field choices in the user interface and the API.

If a default value is specified for a selection field, it must exactly match one of the provided choices. Note that the default value can only be set on the custom field after its corresponding choice has been added.

The value of a multiple selection field will always return a list, even if only one value is selected.

### Filtering on Custom Fields

There are a number of available built-in filters for custom fields.

Filtering on an object's list view follows the same pattern as [custom field filtering on the API](../../rest-api/filtering.md#filtering-by-custom-field).

When using the ORM, you can filter on custom fields using `_custom_field_data__<field name>` (note the underscore before `custom_field_data` and the double-underscore before the field name). For example, if a custom field of string type with a `name` of  `"site_code"` was created for Site objects, you could filter as follows:

```python
from nautobot.dcim.models import Site

all_sites = Site.objects.all()  # -> ['Raleigh', 'Charlotte', 'Greensboro']
filtered_sites_1 = Site.objects.filter(_custom_field_data__site_code="US-NC-RAL42")  # -> ['Raleigh']
filtered_sites_2 = Site.objects.filter(_custom_field_data__site_code__in=["US-NC-RAL42", "US-NC-CLT22"])  # -> ['Raleigh', 'Charlotte']
```

## Custom Fields and the REST API

When retrieving an object via the REST API, all of its custom field data will be included within the `custom_fields` attribute. For example, below is the partial output of a site with two custom fields defined:

```json
{
    "id": 123,
    "url": "http://localhost:8080/api/dcim/sites/123/",
    "name": "Raleigh 42",
    ...
    "custom_fields": {
        "deployed": "2018-06-19",
        "site_code": "US-NC-RAL42"
    },
    ...
```

!!! version-changed "Changed in API version 1.4"
    In REST API versions 1.3 and earlier, each custom field's `name` is used as the key under `custom_fields` in the REST API. As part of the planned future transition to removing the `name` attribute entirely from custom fields, when REST API version 1.4 or later is requested, the `custom_fields` data in the REST API is instead indexed by custom field `slug`.

    Refer to the documentation on [REST API versioning](../../rest-api/overview.md#versioning) for more information about REST API versioning and how to request a specific version of the REST API.

To set or change custom field values, simply include nested JSON data in your REST API POST, PATCH, or PUT request. Unchanged fields may be omitted from the data. For example, the below would set a value for the `deployed` custom field but would leave the `site_code` value unchanged:

```json
{
    "name": "New Site",
    "slug": "new-site",
    "custom_fields": {
        "deployed": "2019-03-24"
    }
}
```

## Custom Fields User Guide

More in depth documentation on how to use custom fields can be found in the [custom fields user guide](../../user-guides/custom-fields.md).
