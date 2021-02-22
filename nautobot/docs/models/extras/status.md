# Statuses

Nautobot provides the ability for custom statuses to be defined within an organization to be used on various objects to facilitate business workflows around object statuses.

The value of a `status` field on a model (such as `Device.status`) will be represented as a `Status` object. This is a foreign key relationship that is designed to behave like a regular choice field but constrained to the content-types for the associated models for that status.

When created, a `Status` can be associated to one or more model content-types using a many-to-many relationship. The relationship to each model is referenced across all user interfaces using the `{app_label}.{model}` naming convention (e.g. `dcim.device`).

Statuses may be managed by navigating to *Organization* > *Statuses* in the navigation menu.

## Status internals

!!! warning
    The section below is largely intended for developers who may need to create
    data models of their own that implement a `status` field. Proceed at your
    own risk!

Any model that is intended to have a `status` field must inherit from `extras.models.statuses.StatusModel`. This abstract model will add an `extras.models.statuses.StatusField` to the model. The abstract base will automatically assign a `related_name` for the reverse relationship back to the inheriting model's name (e.g. `devices`).o

### `StatusField` model field

The `StatusField` field type subclass of a `django.db.models.ForeignKey` with extra extensions to have it behave like field with choices. Because this pattern is replacing hard-coded `ChoiceSets` (such as `dcim.choices.DeviceStatusChoices`) with database objects, it is not possible to use the `choices=` argument on a foreign key.

Because of this, `StatusField` implements a `.contribute_to_class()` method which will automatically bind `.get_status_display()` and `.get_status_color()` methods to any model that implements this field, so that these do not need to be manually defined on each model.

This model field also emits its own form field to eliminate the requirement for a form field to be explicitly added to model forms.

### `StatusFilter` filter field

Any filter that is intended to have a `status` field must inherit from `extras.filters.StatusModelFilterSetMixin`. This will add a `extras.filters.StatusFilter` to the filter, which allows filtering by the `name` of the status.

### Form fields

Any model form that is intended to have a `status` field must inherit from one of three mixins, depending on the use-case:

- `extras.forms.StatusFilterFormMixin` should be used to add a non-required, multiple-choice `status` filter field to UI filter forms. This multiple-choice field allows for multiple status values to be selected for filtering objects in list views in the web UI.
- `extras.forms.StatusBulkEditFormMixin` should be used to add a non-required `status` form field to a an object's model form. This field constrains status choices eligible to the object type being edited.
- FIXME: CSV import forms

### `StatusSerializerField` serializer field

Any serializer that is intended to have a `status` field must inherit from `extras.api.serializers.StatusModelSerializerMixin`. This adds an `extras.api.fields.StatusSerializerField` to the serializer.

The `StatusSerializerField` is a writable slug-related choicee field that allows writing to the field using the `name` value of the status (e.g. `"active"`). Writing to this field is normalized to always be lowercased.

### Table field

If you wish for a table to include a `status` field, your table must inherit from `extras.tables.StatusTableMixin`. This includes a `ColorColumn` on the table.

## Status object integrations

To fully integrate a model to include a `status` field, assert the following:

### Model

- The model must inherit from `extras.models.statuses.StatusModel`
- Decorate the model class with `@extras.utils.extras_features('statuses')`

### Forms

- Generic model forms will automatically include a `StatusField`
- Bulk edit model forms must inherit from `extras.forms.StatusBulkEditFormMixin`
- CSV model import forms must inherit from `extras.forms.StatusModelCSVFormMixin`
- Filter forms must inherit from `extras.forms.StatusFilterFormMixin`

### Filters

- Filtersets for your model must inherit from `extras.filters.StatusModelFilterSetMixin`

### Serializers

- Serializers for your model must inherit from `extras.api.serializers.StatusModelSerializerMixin`

### Tables

- The table class for your model must inherit from `extras.tables.StatusTableMixin`
