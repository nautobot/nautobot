# Extending Tables

+++ 2.3.9

Apps can extend any model-based `Table` classes that are provided by the Nautobot core.

The requirements to extend a table are:

* The file must be named `table_extensions.py`
* The variable `table_extensions` must be declared in that file, and contain a list of `TableExtension` subclasses
* The `model` attribute of each `TableExtension` subclass must be set to a valid model name in the dotted pair format (`{app_label}.{model}`, e.g. `tenant.tenant` or `dcim.device`)

+++ 2.3.13
    Optionally, you can provide the additional `suffix` to be added when looking up the Table. This is useful for models that use a different table for the list view than `{model}Table`.

There are four ways that `TableExtension` can be used to modify a table.

* Custom columns can be added to a table by defining the `table_columns` dictionary.
* Core and custom columns can be added to the default visible columns by defining the `add_to_default_columns` attribute.
* Core columns can be removed from the default visible columns when they are not used or applicable. These are defined in the `remove_from_default_columns` attribute.
* Optimizations can be applied to the view queryset, such as `.prefetch_selected`, `.select_related`, `defer`, and `.only`. Modify the queryset by defining the `alter_queryset` classmethod.

!!! tip
    While queryset optimizations are optional, they are recommended whenever your custom columns are traversing foreign key relationships beyond those of the core tables.

```python
"""table_extensions.py."""

import django_tables2 as tables
from nautobot.apps.tables import TableExtension

class DeviceTableExtension(TableExtension):
    """TableExtension for dcim.Device model."""

    model = "dcim.device"

    # Add custom columns here as {"custom_app_name": Column}
    # Note that the column name must be prefixed with the app name in `snake_case` format.
    table_columns = {
        "my_app_manufacturer": tables.Column(
            verbose_name="Manufacturer",
            accessor="device_type__manufacturer",
            linkify=True,
        ),
    }

    # List any columns that you want to include in the default table.
    # This can be custom columns that you declared above,
    # or core columns that are not normally displayed by default.
    add_to_default_columns = [
        "asset_tag",
        "my_app_manufacturer",
    ]

    # List any columns that you want to remove from the default columns.
    # The column will still be available from the 'Configure' button.
    remove_from_default_columns = ["tenant"]

    @classmethod
    def alter_queryset(cls, queryset):
        """Return an optimized queryset."""
        return queryset.select_related("device_type__manufacturer")


class IPAddressTableExtension(TableExtension):
    """Table Extension for ipam.ipaddress model, which the List view uses IPAddressDetailTable."""

    model = "ipam.ipaddress"
    suffix = "DetailTable"  # Available in 2.3.13

    table_columns = {
        "my_app_mask_length": tables.Column(
            verbose_name="Mask Length",
            accessor="mask_length",
        ),
    }


table_extensions = [
    DeviceTableExtension,
    IPAddressTableExtension,
]
```
