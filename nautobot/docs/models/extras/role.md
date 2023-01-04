# Roles

The Role model represents a role that can be assigned to a device, rack, virtual machine, IP address, VLAN, or prefix. Each role is identified by a unique name and has a slug, weight, color and content-types associated with it.

## Role Basics

The value of a `role` field on a model (such as `Device.role`) will be represented as a `nautobot.extras.models.Role` object.

When created, a `Role` can be associated to one or more model content-types using a many-to-many relationship. The relationship to each model is referenced across all user interfaces using the `{app_label}.{model}` naming convention (e.g. `dcim.device`).

Roles may be managed by navigating to **Organization > Roles** in the navigation menu.

### Importing Objects with a `role` Field

When using CSV import to reference a `role` field on an object, the `Role.name` field is used.

## Role Internals

!!! warning
    The section below is largely intended for developers who may need to create
    data models of their own that implement a `role` field. Proceed at your
    own risk!

Any model that is intended to have a `role` field must inherit from either of these two mixins: `nautobot.extras.models.roles.RoleModelMixin` or `nautobot.extras.models.roles.RoleRequiredRoleModelMixin`. The `RoleModelMixin` adds a nullable `role` field, while the `RoleRequiredRoleModelMixin` adds a required `role` field. This abstract model will add an `nautobot.extras.models.roles.RoleField` to the model. The abstract base will automatically assign a `related_name` for the reverse relationship back to the inheriting model's name (e.g. `dcim_device_related`).

### `RoleField` model field

The `RoleField` field type is a subclass of `django.db.models.ForeignKey`.

This model field also emits its own form field to eliminate the requirement for a form field to be explicitly added to model forms.

### `RoleFilter` filter field

Any filter that is intended to have a `role` field must inherit from `nautobot.extras.filters.RoleModelFilterSetMixin`. This will add a `nautobot.extras.filters.RoleFilter` to the filter, which allows filtering by the `name` or `id` of the role.

### Form fields

Any filter form that is intended to have a `role` field must inherit from `nautobot.extras.forms.RoleModelFilterFormMixin`. This mixin adds a non-required, multiple-choice `role` filter field to the filter form.

Any bulk edit form that is intended to have a `role` field must inherit from `nautobot.extras.forms.RoleModelBulkEditFormMixin`. This mixin adds a non-required `role` field to the form, and constrains the eligible role choices to the object type being edited.

### `RoleSerializerField` serializer field

Any serializer that is intended to have a `role` field must either inherit from one of these:

- `nautobot.extras.api.serializers.RoleModelSerializerMixin` should be used if `role` field is non-required.
- `nautobot.extras.api.serializers.RoleRequiredRoleModelSerializerMixin`should be used if `role` field is required.

This adds an `nautobot.extras.api.fields.RoleSerializerField` to the serializer.

### Table field

If you wish for a table to include a `role` column, your table must inherit from `nautobot.extras.tables.RoleTableMixin`. This includes a `ColorColumn` with the header `role` on the table.
