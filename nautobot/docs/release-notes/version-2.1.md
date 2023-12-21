<!-- markdownlint-disable MD024 -->

# Nautobot v2.1

This document describes all new features and changes in Nautobot 2.1.

## Release Overview

### Added

#### Django Admin Log Entries ([#4646](https://github.com/nautobot/nautobot/pull/4646))

Django Admin Log Entries record administrative changes made under the "Admin" section of the user interface. Changes (add/delete/update) to Objects like Users, Group, Object Permissions, etc. in the "Admin" user interface are now displayed as "Log Entries" under the "Administration" section of the Admin UI.

!!! info
    Django Admin Log Entries are automatically created when adminstrative changes happen and have always existed natively in Django Admin. This feature is simply providung a read-only UI view for admin/privileged users to access them with more ease.

See [Administrative Change-logging](../user-guide/platform-functionality/change-logging.md#administrative-changes) for more details.

#### External Integration Model ([#4694](https://github.com/nautobot/nautobot/issues/4694))

A new [`ExternalIntegration` model](../user-guide/platform-functionality/externalintegration.md) has been added which provides a centralized store for data such as URLs and credentials that are used to access systems external to Nautobot. This information can then be used by jobs or apps to perform actions such as creating DNS records or updating configuration management tickets.

#### Home Page Panels Can Be Customized ([#2149](https://github.com/nautobot/nautobot/issues/2149))

The panels displayed on the Nautobot home page have been modified to enable a more personalized user experience. Individual panels can now be collapsed, hiding the contents from view. Additionally, panels can be reordered by dragging and dropping the panels to the desired order.

#### Job File Outputs ([#3352](https://github.com/nautobot/nautobot/issues/3352), [#4820](https://github.com/nautobot/nautobot/issues/4820))

The `Job` base class now includes a [`create_file(filename, content)`](../development/jobs/index.md#file-output) method which can be called by a Job to create a persistent file with the provided content when run. This file will be linked from the Job Result detail view for subsequent downloading by users, and can also be downloaded via the REST API (`/api/extras/file-proxies/<id>/download/`) as desired.

The size of files Jobs can create via this method are constrained by the [`JOB_CREATE_FILE_MAX_SIZE`](../user-guide/administration/configuration/optional-settings.md#job_create_file_max_size) settings variable.

!!! info
    The specific storage backend used to retain such files is controlled by the [`JOB_FILE_IO_STORAGE`](../user-guide/administration/configuration/optional-settings.md#job_file_io_storage) settings variable. The default value of this setting uses the Nautobot database to store output files, which should work in all deployments but is generally not optimal and better alternatives may exist in your specific deployment. Refer to the documentation link above for more details.

!!! tip
    Users must have permission to `view` the `extras > file proxy` object type in order to list and download files from the REST API.

#### Job JSONVar inputs ([#4926](https://github.com/nautobot/nautobot/issues/4926))

Provides the ability to have native JSON data inputs for Jobs, this is provided by a multi-line text input on the Job form and the provided JSON data is serialized prior to passing to the `run()` method of the Job.

#### UI/API `isnull` Filter on Nullable Fields ([#1905](https://github.com/nautobot/nautobot/issues/1905))

Models with nullable fields (i.e. model fields with `null=True`) can now be filtered in the UI and the API with `<field>__isnull=true/false` filters. These filters are automatically added to all appropriate fields.

!!! note
    Model fields that have the value `""` (i.e. blank) will not match with `__isnull=True`. Instead, they will match with `__isnull=False`.

### Changed

#### Data Exports as a System Job ([#4745](https://github.com/nautobot/nautobot/issues/4745))

The data export functionality in all object list views (allowing export of all or a filtered subset of objects to CSV, YAML, and/or as defined by an `ExportTemplate`) has been changed from a synchronous operation to an asynchronous background task, leveraging the new `ExportObjectList` system Job. As a result, exports of thousands of objects in a single operation will no longer fail due to browser timeout.

!!! tip
    Users now must have the `run` action permission for `extras > job` (specifically the `nautobot.core.jobs.ExportObjectList` Job) in order to export objects, in addition to the normal `view` permissions for the objects being exported.

#### Nautobot UI Reskin ([#4677](https://github.com/nautobot/nautobot/issues/4677), [#4765](https://github.com/nautobot/nautobot/issues/4765))

The Nautobot UI has been updated with a customized theme, giving it a brand new look. In addition, Nautobot's navigation bar has been moved from the top to the left.

### Removed

#### Drop Support for Legacy PostgreSQL Versions ([#4757](https://github.com/nautobot/nautobot/issues/4757))

Support for versions of PostgreSQL prior to 12.0 has been removed as these versions are no longer maintained and contain bugs that prevent migrations from running in certain scenarios. The `nautobot-server migrate` or `nautobot-server post_upgrade` commands will now abort when detecting an unsupported PostgreSQL version.

#### Remove `HIDE_RESTRICTED_UI` Toggle ([#4787](https://github.com/nautobot/nautobot/issues/4787))

Support for `HIDE_RESTRICTED_UI` has been removed. UI elements requiring specific permissions will now always be hidden from users lacking those permissions. Additionally, users not logged in will now be automatically redirected to the login page.

<!-- towncrier release notes start -->
## v2.1.0 (2023-12-21)

### Security

- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Fixed missing object-level permissions enforcement when running a JobButton ([GHSA-vf5m-xrhm-v999](https://github.com/nautobot/nautobot/security/advisories/GHSA-vf5m-xrhm-v999)).
- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Removed the requirement for users to have both `extras.run_job` and `extras.run_jobbutton` permissions to run a Job via a Job Button. Only `extras.run_job` permission is now required.
- [#5002](https://github.com/nautobot/nautobot/issues/5002) - Updated `paramiko` to `3.4.0` due to CVE-2023-48795. As this is not a direct dependency of Nautobot, it will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added

- [#2149](https://github.com/nautobot/nautobot/issues/2149) - Added customizable panels on the homepage.
- [#4708](https://github.com/nautobot/nautobot/issues/4708) - Added VRF to interface bulk edit form.
- [#4757](https://github.com/nautobot/nautobot/issues/4757) - Added system check for minimum PostgreSQL version.
- [#4893](https://github.com/nautobot/nautobot/issues/4893) - Added reverse capability from `IPAddress` to the custom through table `IPAddressToInterface`.
- [#4895](https://github.com/nautobot/nautobot/issues/4895) - Added `http_method`, `headers`, and `ca_file_path` fields, as well as `render_headers`, `render_extra_config`, and `render_remote_url` APIs, to the `ExternalIntegration` model.
- [#4926](https://github.com/nautobot/nautobot/issues/4926) - Added support for a JSONVar in Nautobot Jobs.
- [#4942](https://github.com/nautobot/nautobot/issues/4942) - Added DynamicRoute() to NautobotUIViewSet to support custom actions.
- [#4965](https://github.com/nautobot/nautobot/issues/4965) - Added MMF OM5 cable type to cable type choices.
- [#4973](https://github.com/nautobot/nautobot/issues/4973) - Created convenience methods to access Git with and without secrets.
- [#4984](https://github.com/nautobot/nautobot/issues/4984) - Added `JOB_CREATE_FILE_MAX_SIZE` setting.
- [#4989](https://github.com/nautobot/nautobot/issues/4989) - Added a link to the Advanced tab on detail views to easily open the object in the API browser.

### Changed

- [#4884](https://github.com/nautobot/nautobot/issues/4884) - Added Bootstrap tooltips for all HTML elements with a `title` attribute.
- [#4888](https://github.com/nautobot/nautobot/issues/4888) - Moved username and user actions menu from the top of the nav bar to the bottom.
- [#4896](https://github.com/nautobot/nautobot/issues/4896) - Updated UI colors to match updated Nautobot branding guidelines.
- [#4897](https://github.com/nautobot/nautobot/issues/4897) - Changed screenshots in docs to reflect UI changes.
- [#4961](https://github.com/nautobot/nautobot/issues/4961) - Widened left navigation menu and made longer menus truncate instead of overflowing into the next line.
- [#4961](https://github.com/nautobot/nautobot/issues/4961) - Inserted a divider in between the standard navigation menus and the user menu at the bottom.
- [#4996](https://github.com/nautobot/nautobot/issues/4996) - Changed the order and help text of fields in the External Integration create and edit forms.
- [#5003](https://github.com/nautobot/nautobot/issues/5003) - Updated gifs to showcase new Nautobot 2.1 interface.

### Removed

- [#4757](https://github.com/nautobot/nautobot/issues/4757) - Dropped support for PostgreSQL versions before 12.0.
- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Removed redundant `/extras/job-button/<uuid>/run/` URL endpoint; Job Buttons now use `/extras/jobs/<uuid>/run/` endpoint like any other job.

### Fixed

- [#4620](https://github.com/nautobot/nautobot/issues/4620) - Ensure UI build directory is created on init of nautobot-server.
- [#4627](https://github.com/nautobot/nautobot/issues/4627) - Fixed JSON custom field being returned as a `repr()` string when using GraphQL.
- [#4834](https://github.com/nautobot/nautobot/issues/4834) - Fixed display of custom field choices when editing a CustomField.
- [#4834](https://github.com/nautobot/nautobot/issues/4834) - Fixed display of child groups when editing a DynamicGroup.
- [#4835](https://github.com/nautobot/nautobot/issues/4835) - Fixed incorrect (too dark) color for disabled text fields in forms.
- [#4835](https://github.com/nautobot/nautobot/issues/4835) - Fixed incorrect (too low contrast) color for text fields and select menus in forms in dark theme.
- [#4917](https://github.com/nautobot/nautobot/issues/4917) - Improved performance of location hierarchy HTML template.
- [#4961](https://github.com/nautobot/nautobot/issues/4961) - Fixed bug in dark mode where the left navigation menu top level items would turn white when losing focus.
- [#4968](https://github.com/nautobot/nautobot/issues/4968) - Fixed some cases in which the `ipam.0025` data migration might throw an exception due to invalid data.
- [#4977](https://github.com/nautobot/nautobot/issues/4977) - Fixed early return conditional in `ensure_git_repository`.

### Documentation

- [#4735](https://github.com/nautobot/nautobot/issues/4735) - Documented Django Admin Log Entries in v2.1 Release Overview.
- [#4736](https://github.com/nautobot/nautobot/issues/4736) - Documented `isnull` filter expression in v2.1 Release Overview.
- [#4766](https://github.com/nautobot/nautobot/issues/4766) - Updated documentation for registering tab views.
- [#4984](https://github.com/nautobot/nautobot/issues/4984) - Fixed up docstrings for a number of Job-related classes and methods.

### Housekeeping

- [#4647](https://github.com/nautobot/nautobot/issues/4647) - Added DeviceFactory.
- [#4896](https://github.com/nautobot/nautobot/issues/4896) - Added `/theme-preview/` view (only when `settings.DEBUG` is enabled) to preview various UI elements and layouts.
- [#4942](https://github.com/nautobot/nautobot/issues/4942) - Added example of a custom action on a NautobotUIViewSet to the Example App.
- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Fixed some bugs in `example_plugin.jobs.ExampleComplexJobButtonReceiver`.

## v2.1.0-beta.1 (2023-11-30)

### Added

- [#1905](https://github.com/nautobot/nautobot/issues/1905) - Added the ability to automatically apply `isnull` filters when model field is nullable.
- [#1905](https://github.com/nautobot/nautobot/issues/1905) - Enhanced `status` filters to support filtering by ID (UUID) as an alternative to filtering by `name`.
- [#3352](https://github.com/nautobot/nautobot/issues/3352) - Added `Job.create_file()` API and `JOB_FILE_IO_STORAGE` configuration setting.
- [#3994](https://github.com/nautobot/nautobot/issues/3994) - Added "Data Provenance" section to the Advanced tab in ObjectDetailView to display the user that created and last updated the object.
- [#4272](https://github.com/nautobot/nautobot/issues/4272) - Added bulk edit and bulk destroy views to Namespaces.
- [#4646](https://github.com/nautobot/nautobot/issues/4646) - Added read-only view in admin panel for Django admin log entries.
- [#4694](https://github.com/nautobot/nautobot/issues/4694) - Added `ExternalIntegration` model to track connections to systems external to Nautobot.
- [#4745](https://github.com/nautobot/nautobot/issues/4745) - Added `ExportObjectList` system Job.
- [#4750](https://github.com/nautobot/nautobot/issues/4750) - Added "copy" button support to titles of all object retrieve views.
- [#4750](https://github.com/nautobot/nautobot/issues/4750) - Added support for `BRANDING_FILEPATHS["header_bullet"]` to customize the view header appearance.
- [#4765](https://github.com/nautobot/nautobot/issues/4765) - Added support for `BRANDING_FILEPATHS["nav_bullet"]` to customize the nav menu appearance.
- [#4796](https://github.com/nautobot/nautobot/issues/4796) - Added InterfaceRedundancyGroupAssociation to GraphQL.
- [#4796](https://github.com/nautobot/nautobot/issues/4796) - Added IPAddressToInterface to GraphQL.
- [#4796](https://github.com/nautobot/nautobot/issues/4796) - Added VRFDeviceAssignment to GraphQL.
- [#4796](https://github.com/nautobot/nautobot/issues/4796) - Added VRFPrefixAssignment to GraphQL.
- [#4820](https://github.com/nautobot/nautobot/issues/4820) - Added listing of related `files` to the `/api/extras/job-results/` REST API.
- [#4820](https://github.com/nautobot/nautobot/issues/4820) - Added read-only REST API for the FileProxy model (files generated by a Job run), including a `/download/` endpoint for downloading the file content.

### Changed

- [#4677](https://github.com/nautobot/nautobot/issues/4677) - Updated and customized nautobot UI bootstrap theme with LESS variables.
- [#4745](https://github.com/nautobot/nautobot/issues/4745) - Changed object export (CSV, YAML, export-template) to run as a background task, avoiding HTTP timeouts when exporting thousands of objects in a single operation.
- [#4750](https://github.com/nautobot/nautobot/issues/4750) - Refined CSS to Nautobot Bootstrap UI.
- [#4765](https://github.com/nautobot/nautobot/issues/4765) - Moved navbar to the left.
- [#4786](https://github.com/nautobot/nautobot/issues/4786) - Lightened table row background color in dark mode.
- [#4808](https://github.com/nautobot/nautobot/issues/4808) - Make NavItem link text margin-right slightly larger.

### Removed

- [#4765](https://github.com/nautobot/nautobot/issues/4765) - Removed "Import" buttons from navbar dropdown menus.
- [#4787](https://github.com/nautobot/nautobot/issues/4787) - Removed support for `HIDE_RESTRICTED_UI`. UI elements requiring specific permissions will now always be hidden from users lacking those permissions. Additionally, users not logged in will now be automatically redirected to the login page.

### Fixed

- [#4646](https://github.com/nautobot/nautobot/issues/4646) - Fixed a bug in `ObjectPermission` where `users.user` permissions could not be created.
- [#4786](https://github.com/nautobot/nautobot/issues/4786) - Fixed default button background color in dark mode.
- [#4818](https://github.com/nautobot/nautobot/issues/4818) - Fixed various inconsistencies with UI reskin in dark mode.
- [#4862](https://github.com/nautobot/nautobot/issues/4862) - Fixes issues with uninstalled apps & lingering contenttypes referenced in changelog.
- [#4882](https://github.com/nautobot/nautobot/issues/4882) - Fixed a regression in the rendering of the Jobs table view.

### Housekeeping

- [#3352](https://github.com/nautobot/nautobot/issues/3352) - Added a shared `media_root` volume to developer Docker Compose environment.
- [#4781](https://github.com/nautobot/nautobot/issues/4781) - Added Gherkin writeups for "Locations" and "Prefixes" feature workflows.
