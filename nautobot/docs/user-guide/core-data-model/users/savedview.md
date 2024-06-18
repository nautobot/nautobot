# Saved Views

+++ 2.3.0

Saved Views give users the ability to save multiple configurations of list views, including table columns, filtering, pagination, and sorting, for ease of later use and reuse.

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

Below is a user guide on how to create, update, save and use saved views in Nautobot.

## When to use Saved Views

This feature gives users the ability to save multiple list view configurations (table columns, filtering, pagination and sorting) into saved view instances for ease of access during later use and reuse.

## How to use Saved Views

### How to create a new Saved View

Navigate to any saved-view-supported model's list view. (We will use Location List View for the purpose of this guide)

Note that there is a "Saved Views" dropdown button in the group of buttons on the right hand side.

![Location List View](../../feature-guides/images/saved-views/default-location-list-view.png)

Configure the list view by clicking on the "Filter" and "Configure" buttons on the right hand side.

![Filter Button](../../feature-guides/images/saved-views/filter-button.png)

![Applying Filters to Location List View](../../feature-guides/images/saved-views/filter-application-to-locations.png)

![Configure Button](../../feature-guides/images/saved-views/configure-button.png)

![Configure Table Columns to Location List View](../../feature-guides/images/saved-views/config-table-columns-to-locations.png)

Once you are satisfied with the current list view configurations, click on the "Saved Views" dropdown button. There should be an option in the dropdown menu named "Save As New View".

![Save As New View Dropdown](../../feature-guides/images/saved-views/save-as-new-view-drop-down.png)

Click the "Save As New View" option, a modal should appear to prompt you to give a name to your new saved view and decide whether to make this saved view available to other users.

We will name this new saved view "Campus Staging Location List View" and make this view public.

![Saved View Modal](../../feature-guides/images/saved-views/save-view-modal.png)

Click the "Save" button on the modal and the browser should take you to the new saved view. Note the success banner on top of the page stating "Successfully created new Saved View Campus Staging Location List View". Note that the current saved view name also appeared in the page heading. This is an indicator that you are currently viewing a saved view.

![Successfully Created New Saved View](../../feature-guides/images/saved-views/create-saved-view-success.png)

Click the "Saved Views" dropdown button again and you should see your new saved view's name and a new option "Update Current View" populated in the dropdown menu.

![Dropdown Button After Creating New Saved View](../../feature-guides/images/saved-views/dropdown-button-after-new-saved-view.png)

### How to update an existing Saved View

Stay on the same page where we just created the new Saved View and make some modifications to the view.

Note that the title font of the saved view became italicized. This is an indicator that this saved view currently has unsaved changes.

![Unsaved saved view](../../feature-guides/images/saved-views/unsaved-saved-view.png)

Once you have made desired changes, click the "Saved Views" dropdown button and you should see the option "Update Current Saved View".

Click "Update Current Saved View" option and the page should refresh and you should see the success banner on top of the page stating "Successfully updated current view Campus Staging Location List View".

Congratulations, you have successfully updated your saved view!

![Updated saved view](../../feature-guides/images/saved-views/updated-saved-view.png)

### How to navigate Saved Views

There are several ways you can navigate saved views. All saved views created by any user for any list view can be accessed from the navigation menu on the left hand side under "Extensibility -> Saved Views" as an admin or user with "users:view_savedview" permission:

![Navigation Menu](../../feature-guides/images/saved-views/navigation-menu.png)

Another way is from the "Saved View" dropdown button on any given model list view. All saved views defined for this specific model list view are populated in the dropdown menu and the saved view the user is currently viewing will be highlighted in bold.

![Location List View with Saved Views](../../feature-guides/images/saved-views/location-list-view-with-saved-views.png)

![Current Saved View](../../feature-guides/images/saved-views/current-saved-view-drop-down-menu.png)

### How to set a saved view as global default for all users

There can only be one global default for each object list view and the only way to set a saved view as the global default for all users is from the SavedViewTable at SavedViewListView that is only accessible to admins and users with "users:view_savedview" and "users:edit_savedview" permissions.

![Saved View Table Edit Button](../../feature-guides/images/saved-views/saved-view-admin-edit-buttons.png)

Clicking on the edit button will direct you to a standard edit view where you can edit the `name`, `is_shared` and `is_global_default` attributes of the current saved view.

![Saved View Edit View](../../feature-guides/images/saved-views/saved-view-admin-edit-view.png)

Check the box for `is_global_default` and click on the Update button.

You should be redirected to the SavedViewListView with a success message. Now all users without a default view of their own will be directed to "Campus Staing Location List View" when they are trying to access location list view.

![Saved View Edit Success](../../feature-guides/images/saved-views/saved-view-admin-edit-success.png)

### How to hide a saved view from all other users but yourself

In order to create a saved view only for yourself to see, you should make sure that you uncheck the box for `is_shared` when you are creating a new saved view. This will make sure that you are the only who is able to see this saved view.

![Saved View Modal Unchecked](../../feature-guides/images/saved-views/saved-view-modal-unchecked.png)

As an admin or a user with the appropriate permissions, you can also edit the `is_shared` attribute from Saved View Edit View. Make sure to uncheck both the `is_shared` box and the `is_global_default` box as a global default view will be automatically made as public to all users.

![Saved View Edit View Unchecked](../../feature-guides/images/saved-views/saved-view-admin-edit-view-unchecked.png)

After the saved view is updated, we can log in as a **different** user and see that this private saved view is not available in the saved view dropdown of the ObjectListView.

![Privated Saved View Drop Down](../../feature-guides/images/saved-views/saved-view-different-user.png)

### How to set a user-specific default saved view

You can also set a saved view as default for an object list view for yourself, overriding the global default. You can set a view as default by navigate to the view from the saved view dropdown, for example, "Elevator Only Location List View". Clicking on the saved views dropdown again, you should be able to see the option named "Set As My Default".

![Set As My Default Button](../../feature-guides/images/saved-views/set-as-my-default-button.png)

Clicking on that option will set the current saved view as your default view for this object list view. The page should refresh with a success message. Now whenever this user is trying to access location list view, he/she will be redirected to "Elevator Only Location List View".

![Set As My Default Success](../../feature-guides/images/saved-views/set-as-my-default-success.png)

### How to clear configurations on a Saved View

If the user is currently viewing a saved view, the current saved view should have a checkmark next to its name in the dropdown menu. Clicking on button with the checkmark (current saved view) will direct you back to the default object list view with no configurations applied.

![Clear View Button](../../feature-guides/images/saved-views/clear-view-button.png)

![Cleared Saved View](../../feature-guides/images/saved-views/cleared-view.png)
