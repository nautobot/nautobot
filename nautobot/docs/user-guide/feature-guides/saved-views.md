# Saved Views

Below is a user guide on how to create, update, save and use saved views in Nautobot.

## When to use Saved Views

This feature gives users the ability to save multiple list view configurations (table columns, filtering, pagination and sorting) into saved view instances for ease of access during later use and reuse.

## How to use Saved Views

### How to create a new Saved View

Navigate to any saved-view-supported model's list view. (We will use Location List View for the purpose of this guide)

Note that there is a "Saved Views" dropdown button in the group of buttons on the right hand side.

![Location List View](./images/saved-views/default-location-list-view.png)

Configure the list view by clicking on the "Filter" and "Configure" buttons on the right hand side.

![Filter Button](./images/saved-views/filter-button.png)

![Applying Filters to Location List View](./images/saved-views/filter-application-to-locations.png)

![Configure Button](./images/saved-views/configure-button.png)

![Configure Table Columns to Location List View](./images/saved-views/config-table-columns-to-locations.png)

Once you are satisfied with the current list view configurations, click on the "Saved Views" dropdown button. There should be an option in the dropdown menu named "Save As New View".

![Save As New View Dropdown](./images/saved-views/save-as-new-view-drop-down.png)

Click the "Save As New View" option, a modal should appear to prompt you to give a name to your new saved view.

We will name this new saved view "Campus Staging Location List View".

![Saved View Modal](./images/saved-views/save-view-modal.png)

Click the "Save" button on the modal and the browser should take you to the new saved view. Note the success banner on top of the page stating "Successfully created new Saved View Campus Staging Location List View". Note that the current saved view name also appeared in the page heading. This is an indicator that you are currently viewing a saved view.

![Successfully Created New Saved View](./images/saved-views/create-saved-view-success.png)

Click the "Saved Views" dropdown button again and you should see your new saved view's name and a new option "Update Current View" populated in the dropdown menu.

![Dropdown Button After Creating New Saved View](./images/saved-views/dropdown-button-after-new-saved-view.png)

### How to update an existing Saved View

Stay on the same page where we just created the new Saved View and make some modifications to the view.

Note that an asterisk appeared next to the title of the view. The asterisk is an indicator that this saved view currently has unsaved changes.

![Unsaved saved view](./images/saved-views/unsaved-saved-view.png)

Once you have made desired changes, click the "Saved Views" dropdown button and you should see the option "Update Current View".

Click "Update Current View" option and the page should refresh and you should see the success banner on top of the page stating "Successfully updated current view Campus Staging Location List View".

Congratulations, you have successfully updated your saved view!

![Updated saved view](./images/saved-views/updated-saved-view.png)

### How to navigate Saved Views

There are several ways you can navigate saved views. All saved views created by any user for any list view can be accessed from the navigation menu on the left hand side under "Extensibility -> Saved Views":

![Navigation Menu](./images/saved-views/navigation-menu.png)

Another way is from the "Saved View" dropdown button on any given model list view. All saved views defined for this specific model list view are populated in the dropdown menu and the saved view the user is currently viewing will be highlighted in bold.

![Location List View with Saved Views](./images/saved-views/location-list-view-with-saved-views.png)

![Current Saved View](./images/saved-views/current-saved-view-drop-down-menu.png)

### How to clear configurations on a Saved View

If the user is currently viewing a saved view, a "Clear View" button will be at the bottom of the dropdown menu. A modal should appear when the button is clicked, prompting the user to confirm the action.

![Clear View Button](./images/saved-views/clear-view-button.png)

![Clear View Modal](./images/saved-views/clear-view-modal.png)

Clicking the confirm button will clear the saved and unsaved configurations of the saved view and the saved view will have the same configuration as the default model list view.

![Cleared Saved View](./images/saved-views/cleared-view.png)
