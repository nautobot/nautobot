"""Example App Table Extensions.

TableExtensions provide a method for App developers to modify the table columns for core
Nautobot tables.  An app developer may:
- Add one or more new columns to a table.
- Add one or more, new or core columns, as default visible columns.
- Remove one or more core default columns from the default visible columns.
"""

import django_tables2 as tables

from nautobot.apps.tables import TableExtension


class CircuitTableExtension(TableExtension):
    """Example TableExtension for circuits.Circuit model.

    This TableExtension adds a `Provider ASN` column as a default column to the Circuit table.
    This TableExtension also removes the `Tenant` column from the default view.
    """

    model = "circuits.circuit"

    # Define any additional columns as {key: value} pairs: {"name": Column}.
    table_columns = {
        # Column names must be prefixed with the app name.
        "example_app_provider_asn": tables.Column(
            verbose_name="Provider ASN",
            accessor="provider__asn",
            linkify=False,
        ),
    }

    # Add extended columns here only if the columns should be visible by default.
    add_to_default_columns = ["example_app_provider_asn"]

    # Here we are removing the 'tenant' column from the table default columns.
    # The column will still be available from the 'Configure' button.
    remove_from_default_columns = ["tenant"]


class DeviceTableExtension(TableExtension):
    """Example TableExtension.

    This TableExtension adds a `Manufacturer` column as a default column to the Device table.
    """

    model = "dcim.device"

    # Define any additional columns as {key: value} pairs.
    table_columns = {
        # Column names must be prefixed with the app name.
        "example_app_manufacturer": tables.Column(
            verbose_name="Manufacturer",
            accessor="device_type__manufacturer",
            linkify=True,
        ),
    }

    # Add extended columns here only if the columns should be visible by default.
    add_to_default_columns = ["example_app_manufacturer"]

    @classmethod
    def alter_queryset(cls, queryset):
        """Return an optimized queryset.

        Implementing this method is optional but is recommended to optimize
        the database queries to account for the additional columns.
        """
        return queryset.select_related("device_type__manufacturer")


class IPAddressTableExtension(TableExtension):
    model = "ipam.ipaddress"
    suffix = "DetailTable"

    table_columns = {
        "example_app_mask_length": tables.Column(
            verbose_name="Mask Length",
            accessor="mask_length",
        ),
    }
    remove_from_default_columns = ["tenant"]
    add_to_default_columns = ["example_app_mask_length"]


table_extensions = [
    CircuitTableExtension,
    DeviceTableExtension,
    IPAddressTableExtension,
]
