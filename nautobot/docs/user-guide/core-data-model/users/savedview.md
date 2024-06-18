# Saved Views

+++ 2.3.0

Saved Views give users the ability to save multiple configurations of list views, including table columns, filtering, pagination, and sorting, for ease of later use and reuse. Check out this [user guide](../../feature-guides/saved-views.md) on how to use saved views.

The essential attributes for a Saved View are `owner`, `name`, `view`, `is_shared` and `is_global_default`. The `owner` attribute links to the user account active during the creation of the Saved View. The `view` attribute refers to the specific list view from which the Saved View is derived, such as `dcim:device_list` or `circuits:circuit_list`.
The `is_shared` attribute dictates whether the saved view will be public or private. The `is_global_default` attribute dictates whether all users trying to access the object list view indicated by the value of the `view` attribute will be redirected to the current saved view or not.

When a user creates a new Saved View, the `owner` and `view` attributes are automatically populated. The user only needs to provide the `name` attribute, which, in combination with owner and view, must form a unique set and set the `is_shared` attribute.

The `config` attribute holds the configuration of the list view, stored as a `dictionary`. For example, a configuration for the list view `dcim:location_list` might appear as follows:

```json
{
    "filter_params": {
        "location_type": [
            "Campus",
            "Floor",
            "Building"
        ],
        "status": [
            "Active"
        ]
    },
    "pagination_count": 50,
    "sort_order": [
        "name"
    ],
    "table_config": {
        "LocationTable": {
            "columns": [
                "name",
                "status",
                "location_type",
                "parent",
                "tenant",
                "description",
                "facility",
                "asn",
                "tags"
            ]
        }
    }
}
```
