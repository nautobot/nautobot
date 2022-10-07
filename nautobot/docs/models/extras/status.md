# Statuses

Nautobot provides the ability for custom statuses to be defined within an organization to be used on various objects to facilitate business workflows around object statuses.

## Status Basics

The value of a `status` field on a model (such as `Device.status`) will be represented as a `nautobot.extras.models.Status` object.

When created, a `Status` can be associated to one or more model content-types using a many-to-many relationship. The relationship to each model is referenced across all user interfaces using the `{app_label}.{model}` naming convention (e.g. `dcim.device`).

Statuses may be managed by navigating to **Organization > Statuses** in the navigation menu.

### Importing Objects with a `status` Field

When using CSV import to reference a `status` field on an object, the `Status.slug` field is used.

For example, the default **Active** status has a slug of `active`, so the `active` value would be used for import.

## Customizing Statuses

With Status as a model, statuses can be customized. This can be as simple as removing the option to configure an existing status with a particular model or to remove that status entirely.

The real benefit of custom status is adding your own organization status and process names directly to Nautobot. An example of custom statuses would be including End of Life information for your devices. A simple End of Life status could be EOx for a device hitting any end of life milestone; more specific statuses like EOSS (End of Software Support), EOS (End of Sale), and Pre-EOS (for 1 year prior to EOS) to be more specific. Once the end of life information is tracked as a status, developing a report for Devices that have reached EOSS is trivial.

Another example for sites is tracking the nature of a specific site's installation status. A site that is under construction could received a status like 'Pre Production'.

For Virtual Machines, if utilizing OpenStack, statuses in Nautobot could be customized to reflect the specific [Nova virtual machine states](https://docs.openstack.org/nova/latest/reference/vm-states.html).

## Status Internals

!!! warning
    The section below is largely intended for developers who may need to create
    data models of their own that implement a `status` field. Proceed at your
    own risk!

Any model that is intended to have a `status` field must inherit from `nautobot.extras.models.statuses.StatusModel`. This abstract model will add an `nautobot.extras.models.statuses.StatusField` to the model. The abstract base will automatically assign a `related_name` for the reverse relationship back to the inheriting model's name (e.g. `devices`).

### `StatusField` model field

The `StatusField` field type subclass of a `django.db.models.ForeignKey` with extra extensions to have it behave like field with choices. Because this pattern is replacing hard-coded `ChoiceSets` (such as `dcim.choices.DeviceStatusChoices`) with database objects, it is not possible to use the `choices=` argument on a foreign key.

Because of this, `StatusField` implements a `.contribute_to_class()` method which will automatically bind `.get_status_display()` and `.get_status_color()` methods to any model that implements this field, so that these do not need to be manually defined on each model.

This model field also emits its own form field to eliminate the requirement for a form field to be explicitly added to model forms.

### `StatusFilter` filter field

Any filter that is intended to have a `status` field must inherit from `nautobot.extras.filters.StatusModelFilterSetMixin`. This will add a `nautobot.extras.filters.StatusFilter` to the filter, which allows filtering by the `name` of the status.

### Form fields

Any model form that is intended to have a `status` field must inherit from one of three mixins, depending on the use-case:

- `nautobot.extras.forms.StatusModelFilterFormMixin` should be used to add a non-required, multiple-choice `status` filter field to UI filter forms. This multiple-choice field allows for multiple status values to be selected for filtering objects in list views in the web UI.
- `nautobot.extras.forms.StatusModelBulkEditFormMixin` should be used to add a non-required `status` form field to a an object's model form. This field constrains status choices eligible to the object type being edited.

+/- 1.4.0
    In prior Nautobot versions these mixins were named `StatusFilterFormMixin` and `StatusBulkEditFormMixin`; the old names are still available as aliases but will be removed in a future major release.

- FIXME: CSV import forms

### `StatusSerializerField` serializer field

Any serializer that is intended to have a `status` field must inherit from `nautobot.extras.api.serializers.StatusModelSerializerMixin`. This adds an `nautobot.extras.api.fields.StatusSerializerField` to the serializer.

The `StatusSerializerField` is a writable slug-related choice field that allows writing to the field using the `name` value of the status (e.g. `"active"`). Writing to this field is normalized to always be converted to lowercase.

### Table field

If you wish for a table to include a `status` field, your table must inherit from `nautobot.extras.tables.StatusTableMixin`. This includes a `ColorColumn` on the table.

## Status object integrations

To fully integrate a model to include a `status` field, assert the following:

### Model

- The model must inherit from `nautobot.extras.models.statuses.StatusModel`
- Decorate the model class with `@extras_features('statuses')` (`from nautobot.extras.utils import extras_features`)

### Forms

- Generic model forms will automatically include a `StatusField`
- CSV model import forms must inherit from `nautobot.extras.forms.StatusModelCSVFormMixin`
- Bulk edit model forms must inherit from `nautobot.extras.forms.StatusModelBulkEditFormMixin`
- Filter forms must inherit from `nautobot.extras.forms.StatusModelFilterFormMixin`

+/- 1.4.0
    In prior Nautobot releases the latter two mixins were named `StatusBulkEditFormMixin` and `StatusFilterFormMixin` respectively; the old names are still available as aliases but will be removed in a future major release.

### Filters

- Filtersets for your model must inherit from `nautobot.extras.filters.StatusModelFilterSetMixin`

### Serializers

- Serializers for your model must inherit from `nautobot.extras.api.serializers.StatusModelSerializerMixin`

### Tables

- The table class for your model must inherit from `nautobot.extras.tables.StatusTableMixin`
