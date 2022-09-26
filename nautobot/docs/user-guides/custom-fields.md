# Custom Fields

Custom fields are a method of adding new fields to existing Nautobot models. For more general information on how custom fields work, refer to the [custom fields model documentation](../models/extras/customfield.md).

## When to use Custom Fields

Custom fields are commonly used for fields that need different values across individual objects. For example, a custom field on devices to reference an internal ticket number that inventories each device in Nautobot. If you need a solution for marking multiple objects with a common flag, [tags](../models/extras/tag.md) may be a better fit.

## Create a Custom Field

Navigate to the custom fields page by clicking on **Extensibility -> Custom Fields** in the Nautobot menu. Click on **Add** to create a new custom field.

!!! note
    Custom fields are initialized on associated objects when a content type is added to the custom field, including when the custom field is created. The initial value will be set to the `default` value of the custom field.

### Custom Field Attributes

#### Label

The label is the human readable label of the custom field that will be displayed on the associated object detail view.

![Custom Field Labels](../images/custom-fields/custom_field_detail_label.png)

#### Grouping

The optional grouping field allows you to group custom fields into collapsible menus.

![Custom Field Grouping](../images/custom-fields/custom_field_detail_grouped.png)

#### Slug

The slug is used to create the URL endpoint for the custom field and is also used as the key in the custom field dictionary. This is automatically created from the label if not supplied. The default value should be sufficient for most deployments.

#### Type

The type of data that the custom field will store. Valid choices are documented in the custom field [model documentation](../models/extras/customfield.md#creating-custom-fields).

#### Weight

Weight determines how custom fields are sorted in a form and object detail views. Higher-weight fields will be ordered lower within a form.

#### Description

The description of a custom field is shown as a mouseover tooltip in object detail views and as help text under form fields.

![Custom Field Edit](../images/custom-fields/custom_field_edit.png)

#### Required

Check the required box if this field cannot be null on the associated objects.

!!! warning
    If an associated object does not have a valid value assigned to a required custom field, that field must be updated with a valid value before the object can be saved. Try to supply a valid default value when creating required custom fields. Since automatic provisioning is only performed when a custom field's content types change, if an existing custom field is changed from optional to required the associated objects will have to be updated manually.

#### Default

The default value for the custom field. This form field only accepts JSON data so if you want to set the field default to a string of `foo` you must supply the JSON string `"foo"`. Boolean field valid values are `true` and `false` (all lowercase). Date fields are strings in the format `YYYY-MM-DD`.

### Assignment

#### Content Types

The list of content types to add this custom field to. Only models that subclass the `nautobot.extras.models.customfields.CustomFieldModel` model class can be selected.

### Validation Rules

Validation rules are used for constraining custom fields to specific values.

#### Minimum value

Minimum allowed value for `Integer` fields.

#### Maximum value

Maximum allowed value for `Integer` fields.

#### Validation Regex

Regular expression to enforce on `Text`, `URL`, `Selection` and `Multiple selection` field values. Regex validation is handled by the [python re engine](https://docs.python.org/3/library/re.html) which uses a PCRE or perl-like regular expression syntax. Examples of common regex validations:

Must start with companyname
> ^companyname

Must end with 5 digit zip code
> [0-9]{5}$

Must only contain digits
> ^\d+$

Must be exactly 8 alphanumeric characters
> ^[0-9a-zA-Z]{8}$

Must be between 8 and 10 alphanumeric characters and underscore
> ^\w+{8,10}$

Must contain anything that is not whitespace
> \S

### Custom Field Choices

The choices to be presented for `Selection` and `Multiple selection` custom field types. These are displayed in the order of the weight values supplied with the lowest weight on top. If regex validation is being used, these choices must match the regular expression.

![Custom Field Choices](../images/custom-fields/custom_field_choices.png)

![Custom Field Select](../images/custom-fields/custom_field_select.png)

## Modifying Custom Fields

Since automatic provisioning is only performed when a custom field's content types change, some changes made to custom fields are not reflected on the associated objects automatically. Some examples of cases where this might cause unexpected behavior are changes to the `required`, `default` and validation fields.

## Deleting Custom Fields

Custom fields are removed from associated objects when a content type is removed from the custom field, including when the custom field is deleted.
