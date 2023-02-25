# Role Internals

!!! warning
    The section below is largely intended for developers who may need to create
    data models of their own that implement a `role` field. Proceed at your
    own risk!

Any model that is intended to have a `role` field must inherit from either of these two mixins: `nautobot.extras.models.roles.RoleModelMixin` or `nautobot.extras.models.roles.RoleRequiredRoleModelMixin`. The `RoleModelMixin` adds a nullable `role` field, while the `RoleRequiredRoleModelMixin` adds a required `role` field. This abstract model will add an `nautobot.extras.models.roles.RoleField` to the model. The abstract base will automatically assign a `related_name` for the reverse relationship back to the inheriting model's verbose plural name (e.g. `devices`).

## `RoleField` model field

The `RoleField` field type is a subclass of `django.db.models.ForeignKey`.

This model field also emits its own form field to eliminate the requirement for a form field to be explicitly added to model forms.

## `RoleFilter` filter field

Any filter that is intended to have a `role` field must inherit from `nautobot.extras.filters.RoleModelFilterSetMixin`. This will add a `nautobot.extras.filters.RoleFilter` to the filter, which allows filtering by the `name` or `id` of the role.

## Form fields

Any filter form that is intended to have a `role` field must inherit from `nautobot.extras.forms.RoleModelFilterFormMixin`. This mixin adds a non-required, multiple-choice `role` filter field to the filter form.

Any bulk edit form that is intended to have a `role` field must inherit from `nautobot.extras.forms.RoleModelBulkEditFormMixin`. This mixin adds a non-required `role` field to the form, and constrains the eligible role choices to the object type being edited.

Any CSV import form that is intended to have a required or non-required `role` field must inherit from either `nautobot.extras.forms.RoleRequiredRoleModelCSVFormMixin` or `nautobot.extras.forms.RoleModelCSVFormMixin`, respectively, which adds the specified role field to the form and constrains the eligible role choices to the object type being imported.

## `RoleSerializerField` serializer field

Any serializer that is intended to have a `role` field must either inherit from one of these:

- `nautobot.extras.api.serializers.RoleModelSerializerMixin` should be used if `role` field is non-required.
- `nautobot.extras.api.serializers.RoleRequiredRoleModelSerializerMixin`should be used if `role` field is required.

This adds an `nautobot.extras.api.fields.RoleSerializerField` to the serializer.

## Table field

If you wish for a table to include a `role` column, your table must inherit from `nautobot.extras.tables.RoleTableMixin`. This includes a `ColorColumn` with the header `role` on the table.
