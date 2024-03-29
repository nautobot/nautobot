<!-- markdownlint-disable MD024 -->

# Nautobot v2.2

This document describes all new features and changes in Nautobot 2.2.

## Release Overview

### Added

#### Contact and Team Models ([#230](https://github.com/nautobot/nautobot/issues/230))

Contact and Team are models that represent an individual and a group of individuals who can be linked to an object. Contacts and teams store the necessary information (name, phone number, email, and address) to uniquely identify and contact them. They are added to track ownerships of organizational entities and to manage resources more efficiently in Nautobot. Check out the documentation for [contact](../user-guide/core-data-model/extras/contact.md) and [team](../user-guide/core-data-model/extras/team.md). There is also a [user guide](../user-guide/feature-guides/contacts-and-teams.md) available on how to utilize these models.

A new management command has been introduced to assist with migrating the Location fields `contact_name`, `contact_phone` and `contact_email` to the new Contact and Team models. This command can be invoked with `nautobot-server migrate_location_contacts` and will present a series of prompts to guide you through migrating Locations that have data in the `contact_name`, `contact_phone`, or `contact_email` fields which are not already associated to a Contact or Team. This command will give you the option to create new Contacts or Teams or, if a similar Contact or Team already exists, to link the Location to the existing Contact or Team. Note that when assigning a Location to an existing Contact or Team that has a blank `phone` or `email` field, the value from the Location will be copied to the Contact/Team. After a Location has been associated to a Contact or Team, the `contact_name`, `contact_phone`, and `contact_email` fields will be cleared from the Location.

#### Controller Model ([#3111](https://github.com/nautobot/nautobot/issues/3111))

Controller models have been added to the `dcim` app. A Controller in Nautobot is an abstraction meant to represent network or SDN (Software-Defined Networking) controllers. These may include, but are not limited to, wireless controllers, cloud-based network management systems, and other forms of central network control mechanisms.

For more details, refer to the user guide for a [`Controller` model](../user-guide/core-data-model/dcim/controller.md), a [`ControllerManagedDeviceGroup` model](../user-guide/core-data-model/dcim/controllermanageddevicegroup.md), or developer documentation for [controllers](../development/core/controllers.md).

#### DeviceFamily Model ([#3559](https://github.com/nautobot/nautobot/issues/3559))

A [device family](../user-guide/core-data-model/dcim/devicefamily.md) represents a group of related [device types](../user-guide/core-data-model/dcim/devicetype.md). A device type can be optionally assigned to a device family. Each device family must have a unique name and may have a description assigned to it.

#### Jobs tile view ([#5129](https://github.com/nautobot/nautobot/issues/5129))

Job list is now available in two display variants: list and tiles. List is a standard table view with no major changes introduced. Tiles is a new type of view displaying jobs in a two-dimensional grid.

#### Prefix and VLAN Many Locations ([#4334](https://github.com/nautobot/nautobot/issues/4334), [#4412](https://github.com/nautobot/nautobot/issues/4412))

The Prefix and VLAN models have replaced their single `location` foreign-key field with a many-to-many `locations` field, allowing multiple Locations to be attached to a single Prefix or VLAN. To ensure backwards compatibility with pre-2.2 code, these models now have a `location` property which can be get or set for the case of a single associated Location, but will raise a `MultipleObjectsReturned` exception if the Prefix or VLAN in question has more than one associated Location. REST API versions 2.0 and 2.1 similarly still have a `location` field, while REST API version 2.2 and later replace this with `locations`.

#### Software Image File and Software Version models ([#1](https://github.com/nautobot/nautobot/issues/1))

New models have been added for software image files and software versions. These models are used to track the software versions of devices, inventory items and virtual machines and their associated image files. These models have been ported from the [Device Lifecycle Management App](https://github.com/nautobot/nautobot-app-device-lifecycle-mgmt/) and a future update to that app will migrate all existing data from the `nautobot_device_lifecycle_mgmt.SoftwareImageLCM` and `nautobot_device_lifecycle_mgmt.SoftwareLCM` models to the `dcim.SoftwareImageFile` and `dcim.SoftwareVersion` models added here.

Software versions must be associated to a platform. Software image files must be associated to one software version and may be associated to one or more device types. Devices, inventory items and virtual machines may be associated to one software version to track their current version. See the documentation for [software image file](../user-guide/core-data-model/dcim/softwareimagefile.md) and [software version](../user-guide/core-data-model/dcim/softwareversion.md). There is also a [user guide](../user-guide/feature-guides/software-image-files-and-versions.md) with instructions on how to create these models.

#### Syntax highlighting ([#5098](https://github.com/nautobot/nautobot/issues/5098))

Language syntax highlighting for GraphQL, JSON, XML and YAML is now supported in the UI via JavaScript. To enable the feature, a code snippet has to be wrapped in the following HTML structure:

```html
<pre><code class="language-{graphql,json,xml,yaml}">...</code></pre>
```

[`render_json`](../user-guide/platform-functionality/template-filters.md#render_json) and [`render_yaml`](../user-guide/platform-functionality/template-filters.md#render_yaml) template filters default to this new behavior with an optional opt-out `syntax_highlight=False` arg.

### Changed

#### Data Imports as a System Job ([#5064](https://github.com/nautobot/nautobot/issues/5064))

The CSV import functionality for all models has been changed from a synchronous operation to an asynchronous background task (system Job). As a result, imports of large CSV files will no longer fail due to browser timeout.

!!! tip
    Users now must have the `run` action permission for `extras > job` (specifically the `nautobot.core.jobs.ImportObjects` Job) in order to import objects, in addition to the normal `add` permissions for the object type being imported.

#### Plugin to App Renames([#5341](https://github.com/nautobot/nautobot/issues/5341))

`Installed Plugins` view has been renamed to `Installed Apps`. `Plugin` terminologies in `Installed Plugins` (now `Installed Apps`) view and dependent views have been changed to `App` throughout. `Plugin` references in documentation (excluding old release-notes) have been replaced by `App`. `Plugins` navigation menu has been renamed to `Apps`.

#### Standardization of `max_length` on all Charfields ([#2906](https://github.com/nautobot/nautobot/issues/2906))

Model CharFields' `max_length` attributes have been standardized globally to have at least 255 characters except where a shorter `max_length` is explicitly justified.

<!-- towncrier release notes start -->
## v2.2.0-beta.1 (2024-03-19)

### Added

- [#1](https://github.com/nautobot/nautobot/issues/1) - Added new models for software versions and software image files.
- [#1](https://github.com/nautobot/nautobot/issues/1) - Added a many-to-many relationship from `Device` to `SoftwareImageFile`.
- [#1](https://github.com/nautobot/nautobot/issues/1) - Added a many-to-many relationship from `DeviceType` to `SoftwareImageFile`.
- [#1](https://github.com/nautobot/nautobot/issues/1) - Added a many-to-many relationship from `InventoryItem` to `SoftwareImageFile`.
- [#1](https://github.com/nautobot/nautobot/issues/1) - Added a many-to-many relationship from `VirtualMachine` to `SoftwareImageFile`.
- [#1](https://github.com/nautobot/nautobot/issues/1) - Added a foreign key relationship from `Device` to `SoftwareVersion`.
- [#1](https://github.com/nautobot/nautobot/issues/1) - Added a foreign key relationship from `InventoryItem` to `SoftwareVersion`.
- [#1](https://github.com/nautobot/nautobot/issues/1) - Added a foreign key relationship from `VirtualMachine` to `SoftwareVersion`.
- [#230](https://github.com/nautobot/nautobot/issues/230) - Added Contact and Team Models.
- [#1150](https://github.com/nautobot/nautobot/issues/1150) - Added environment variable support for most admin-configurable settings (`ALLOW_REQUEST_PROFILING`, `BANNER_TOP`, etc.)
- [#3111](https://github.com/nautobot/nautobot/issues/3111) - Initial work on the controller model.
- [#3559](https://github.com/nautobot/nautobot/issues/3559) - Added `HardwareFamily` model class. (Renamed before release to `DeviceFamily`.)
- [#3559](https://github.com/nautobot/nautobot/issues/3559) - Added `device_family` field to Device Type model class.
- [#4269](https://github.com/nautobot/nautobot/issues/4269) - Added REST API endpoint for `VRFDeviceAssignment` model.
- [#4270](https://github.com/nautobot/nautobot/issues/4270) - Added REST API endpoint for `VRFPrefixAssignment` model.
- [#4811](https://github.com/nautobot/nautobot/issues/4811) - Enabled sorting on the API endpoints for tree node models.
- [#5012](https://github.com/nautobot/nautobot/issues/5012) - Added database indexes to the ObjectChange model to improve performance when filtering by `user_name`, `changed_object`, or `related_object`, and also by `changed_object` in combination with `user` or `user_name`.
- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Added `job_import_button` template-tag and marked `import_button` button template-tag as deprecated.
- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Added `nautobot.apps.utils.get_view_for_model` utility function.
- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Added `can_add`, `can_change`, `can_delete`, `can_view`, and `has_serializer` filters to the `/api/extras/content-types/` REST API.
- [#5067](https://github.com/nautobot/nautobot/issues/5067) - Added `q` (SearchFilter) filter to all filtersets where it was missing.
- [#5067](https://github.com/nautobot/nautobot/issues/5067) - Added two generic test cases for `q` filter: `test_q_filter_exists` and `test_q_filter_valid`.
- [#5097](https://github.com/nautobot/nautobot/issues/5097) - Added a JSON Schema file for Nautobot settings (`nautobot/core/settings.yaml`).
- [#5097](https://github.com/nautobot/nautobot/issues/5097) - Added REST API endpoint to show the JSON Schema for authenticated users.
- [#5098](https://github.com/nautobot/nautobot/issues/5098) - Added client-side GraphQL, JSON, XML, and YAML syntax highlighting with the `highlight.js` library.
- [#5101](https://github.com/nautobot/nautobot/issues/5101) - Added a utility to help when writing migrations that replace database models.
- [#5107](https://github.com/nautobot/nautobot/issues/5107) - Added `hyperlinked_email` and `hyperlinked_phone_number` template tags/filters.
- [#5127](https://github.com/nautobot/nautobot/issues/5127) - Added bulk-edit and bulk-delete capabilities for Jobs.
- [#5129](https://github.com/nautobot/nautobot/issues/5129) - Implemented jobs tile view.
- [#5188](https://github.com/nautobot/nautobot/issues/5188) - Added table of related Device Families to the DeviceType detail view.
- [#5278](https://github.com/nautobot/nautobot/issues/5278) - Added permission constraint for User Token.
- [#5341](https://github.com/nautobot/nautobot/issues/5341) - Added `/apps/` and `/api/apps/` URL groupings, initially containing only the `installed-apps/` sub-items.
- [#5341](https://github.com/nautobot/nautobot/issues/5341) - Added `nautobot-apps` key to the `/api/status/` REST API endpoint.
- [#5342](https://github.com/nautobot/nautobot/issues/5342) - Added `MigrationsBackend` to health-check, which will fail if any unapplied database migrations are present.
- [#5347](https://github.com/nautobot/nautobot/issues/5347) - Added an option to the Job-based CSV import to make atomic transactions optional.
- [#5349](https://github.com/nautobot/nautobot/issues/5349) - Added REST API for vlan-to-location and prefix-to-location M2M.

### Changed

- [#2906](https://github.com/nautobot/nautobot/issues/2906) - Increased `max_length` on all CharFields to at least 255 characters except where a shorter `max_length` is explicitly justified.
- [#4334](https://github.com/nautobot/nautobot/issues/4334) - Changed `Prefix.location` to `Prefix.locations` allowing multiple Locations to be associated with a given Prefix.
- [#4334](https://github.com/nautobot/nautobot/issues/4334) - Changed VLANGroup default ordering to be sorted by `name` alone since it is a unique field.
- [#4412](https://github.com/nautobot/nautobot/issues/4412) - Changed `VLAN.location` to `VLAN.locations` allowing multiple Locations to be associated with a given VLAN.
- [#4811](https://github.com/nautobot/nautobot/issues/4811) - Changed the behavior of tree model tables: now they are sortable, and after sorting is applied, all hierarchy indentations are removed.
- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Changed CSV import functionality to run as a system Job, avoiding HTTP timeouts when importing large data sets.
- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Updated JobResult main tab to render any return value from the Job as syntax-highlighted JSON.
- [#5126](https://github.com/nautobot/nautobot/issues/5126) - Rearranged Job List table row contents.
- [#5341](https://github.com/nautobot/nautobot/issues/5341) - Renamed `Plugins` navigation menu to `Apps`. Apps that add to this menu are encouraged to update their `navigation.py` to use the new name.
- [#5341](https://github.com/nautobot/nautobot/issues/5341) - Renamed `Installed Plugins` view to `Installed Apps`.
- [#5341](https://github.com/nautobot/nautobot/issues/5341) - Changed permissions on the `Installed Apps` views to be visible to all authenticated users, not just staff/superuser accounts.
- [#5342](https://github.com/nautobot/nautobot/issues/5342) - Changed default Docker HEALTHCHECK to use `nautobot-server health_check` CLI command.
- [#5405](https://github.com/nautobot/nautobot/issues/5405) - Changed DeviceType list view "Import" button to include a dropdown to select between JSON/YAML or CSV import formats.
- [#5405](https://github.com/nautobot/nautobot/issues/5405) - Changed DeviceType list view "Export" button to default to YAML format.
- [#5412](https://github.com/nautobot/nautobot/issues/5412) - Changed DeviceType YAML/JSON import to now map unrecognized port template `type` values to `"other"` instead of failing the import.
- [#5414](https://github.com/nautobot/nautobot/issues/5414) - Changed `ImportObjects.roll_back_if_error` form field help text and label.

### Deprecated

- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Deprecated the `import_button` button template-tag.
- [#5116](https://github.com/nautobot/nautobot/issues/5116) - Deprecated the `nautobot.apps.exceptions.ConfigurationError` class as it is no longer used in Nautobot core and is trivially reimplementable by any App if desired.
- [#5341](https://github.com/nautobot/nautobot/issues/5341) - Deprecated the `plugins` key under the `/api/status/` REST API endpoint. Refer to `nautobot-apps` instead.

### Removed

- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Removed the requirement for `ViewTestCases` subclasses to define `csv_data` for testing bulk-import views, as this functionality is now covered by a generic system Job.
- [#5116](https://github.com/nautobot/nautobot/issues/5116) - Removed `logan`-derived application startup logic, simplifying the Nautobot startup code flow.

### Fixed

- [#4334](https://github.com/nautobot/nautobot/issues/4334) - Fixed ordering of VLANs in the UI list view.
- [#5064](https://github.com/nautobot/nautobot/issues/5064) - Fixed an exception in `Job.after_return()` if a Job with an optional `FileVar` was executed without supplying a value for that variable.
- [#5116](https://github.com/nautobot/nautobot/issues/5116) - Fixed inability to specify a `--config PATH` value with the `nautobot-server runserver` command.
- [#5186](https://github.com/nautobot/nautobot/issues/5186) - Fixed `Prefix.ip_version` and `IPAddress.ip_version` fields to be non-nullable.
- [#5220](https://github.com/nautobot/nautobot/issues/5220) - Fixed contacts field in "Add a new team" form not populating.
- [#5241](https://github.com/nautobot/nautobot/issues/5241) - Fixed rendering of `NavMenuItems` that do not define any specific required `permissions`.
- [#5241](https://github.com/nautobot/nautobot/issues/5241) - Fixed incorrect construction of `NavMenuTab` and `NavMenuGroup` permissions.
- [#5241](https://github.com/nautobot/nautobot/issues/5241) - Fixed incorrect permissions required for `Roles` navigation menu item.
- [#5298](https://github.com/nautobot/nautobot/issues/5298) - Fixed a `ValidationError` that was being thrown when a user logged out.
- [#5298](https://github.com/nautobot/nautobot/issues/5298) - Fixed a case where viewing a completed JobResult that was missing a `date_done` value would cause the JobResult view to repeatedly refresh.

### Dependencies

- [#5248](https://github.com/nautobot/nautobot/issues/5248) - Broadened `Markdown` dependency to permit versions up to 3.5.x.

### Documentation

- [#5179](https://github.com/nautobot/nautobot/issues/5179) - Updated all documentation referencing the `example_plugin` to refer to the (renamed) `example_app`.
- [#5179](https://github.com/nautobot/nautobot/issues/5179) - Replaced some "plugin" references in the documentation with "App" or "Nautobot App" as appropriate.
- [#5248](https://github.com/nautobot/nautobot/issues/5248) - Removed source code excerpts from the "App Developer Guide > Code Reference" section of the documentation.
- [#5341](https://github.com/nautobot/nautobot/issues/5341) - Replaced references to "plugins" in the documentation with "Apps".

### Housekeeping

- [#5099](https://github.com/nautobot/nautobot/issues/5099) - Added `mkdocs-macros-plugin` as a development/documentation-rendering dependency.
- [#5099](https://github.com/nautobot/nautobot/issues/5099) - Refactored documentation in `optional-settings` and `required-settings` to be generated automatically from `settings.yaml` schema.
- [#5099](https://github.com/nautobot/nautobot/issues/5099) - Replaced `nautobot/core/settings.json` with `nautobot/core/settings.yaml` for improved readability and maintainability.
- [#5105](https://github.com/nautobot/nautobot/issues/5105) - Added Bulk Edit functionality for ContactAssociation.
- [#5105](https://github.com/nautobot/nautobot/issues/5105) - Added Bulk Edit buttons for associated contact tables in the contacts tabs of object detail views.
- [#5145](https://github.com/nautobot/nautobot/issues/5145) - Added data migration to populate default statuses and default roles for the `ContactAssociation` model.
- [#5179](https://github.com/nautobot/nautobot/issues/5179) - Renamed `example_plugin` to `example_app`.
- [#5179](https://github.com/nautobot/nautobot/issues/5179) - Renamed `example_plugin_with_view_override` to `example_app_with_view_override`.
- [#5179](https://github.com/nautobot/nautobot/issues/5179) - Replaced all "plugin" terminology within the `examples` directory with "App", except in cases where the terminology is embedded in core code (`settings.PLUGINS`, `plugins:` and `plugins-api` named URLs, etc.)
- [#5179](https://github.com/nautobot/nautobot/issues/5179) - Replaced some "plugin" terminology in docstrings, comments, and test code with "app" as appropriate.
- [#5187](https://github.com/nautobot/nautobot/issues/5187) - Removed "Add Contact" button from the standard buttons in the detail views.
- [#5187](https://github.com/nautobot/nautobot/issues/5187) - Renamed "Assign Contact/Team" UI buttons text from "Create", "Create and Add Another" to "Assign" and "Assign and Add Another".
- [#5187](https://github.com/nautobot/nautobot/issues/5187) - Split out Contact/Team icons into a separate column and renamed the columns to "Type" and "Name" on AssociatedContactsTable.
- [#5207](https://github.com/nautobot/nautobot/issues/5207) - Made `role` attribute required on `ContactAssociation` Model.
- [#5213](https://github.com/nautobot/nautobot/issues/5213) - Made the default action when assigning a contact/team to an object to be the assignment of an existing contact/team.
- [#5214](https://github.com/nautobot/nautobot/issues/5214) - Fixed the bug causing Contact Tab disappear when the user navigates to the Notes and Changelog Tabs.
- [#5221](https://github.com/nautobot/nautobot/issues/5221) - Fixed the return URL from adding/assigning a contact/team from ObjectDetailView to redirect to the contacts tab instead of the main tab.
- [#5248](https://github.com/nautobot/nautobot/issues/5248) - Updated development dependencies including `coverage`, `django-debug-toolbar`, `factory-boy`, `mkdocs-material`, `mkdocstrings`, `mkdocstrings-python`, `pylint`, `rich`, `ruff`, `selenium`, `splinter`, `towncrier`, `watchdog`, and `yamllint` to their latest available versions.
- [#5272](https://github.com/nautobot/nautobot/issues/5272) - Fixed incorrectly set return urls on the edit and delete buttons of job tile view.
- [#5352](https://github.com/nautobot/nautobot/issues/5352) - Renamed `HardwareFamily` to `DeviceFamily`.
