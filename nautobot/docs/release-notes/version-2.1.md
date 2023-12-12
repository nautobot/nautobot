<!-- markdownlint-disable MD024 -->

# Nautobot v2.1

This document describes all new features and changes in Nautobot 2.1.

## Release Overview

### Added

#### Job File Outputs ([#3352](https://github.com/nautobot/nautobot/issues/3352), [#4820](https://github.com/nautobot/nautobot/issues/4820))

The `Job` base class now includes a [`create_file(filename, content)`](../development/jobs/index.md#file-output) method which can be called by a Job to create a persistent file with the provided content when run. This file will be linked from the Job Result detail view for subsequent downloading by users, and can also be downloaded via the REST API (`/api/extras/file-proxies/<id>/download/`) as desired.

!!! info
    The specific storage backend used to retain such files is controlled by the [`JOB_FILE_IO_STORAGE`](../user-guide/administration/configuration/optional-settings.md#job_file_io_storage) settings variable. The default value of this setting uses the Nautobot database to store output files, which should work in all deployments but is generally not optimal and better alternatives may exist in your specific deployment. Refer to the documentation link above for more details.

!!! tip
    Users must have permission to `view` the `extras > file proxy` object type in order to list and download files from the REST API.

#### Django Admin Log Entries ([#4646](https://github.com/nautobot/nautobot/pull/4646))

Django Admin Log Entries record administrative changes made under the "Admin" section of the user interface. Changes (add/delete/update) to Objects like Users, Group, Object Permissions, etc. in the "Admin" user interface are now displayed as "Log Entries" under the "Administration" section of the Admin UI.

!!! info
    Django Admin Log Entries are automatically created when adminstrative changes happen and have always existed natively in Django Admin. This feature is simply providung a read-only UI view for admin/privileged users to access them with more ease.

See [Administrative Change-logging](../user-guide/platform-functionality/change-logging.md#administrative-changes) for more details.

#### External Integration Model ([#4694](https://github.com/nautobot/nautobot/issues/4694))

A new [`ExternalIntegration` model](../user-guide/platform-functionality/externalintegration.md) has been added which provides a centralized store for data such as URLs and credentials that are used to access systems external to Nautobot. This information can then be used by jobs or apps to perform actions such as creating DNS records or updating configuration management tickets.

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
