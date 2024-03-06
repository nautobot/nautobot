<!-- markdownlint-disable MD024 -->

# Nautobot v2.1

This document describes all new features and changes in Nautobot 2.1.

## Release Overview

### Added

#### Django Admin Log Entries ([#4646](https://github.com/nautobot/nautobot/pull/4646))

Django Admin Log Entries record administrative changes made under the "Admin" section of the user interface. Changes (add/delete/update) to Objects like Users, Group, Object Permissions, etc. in the "Admin" user interface are now displayed as "Log Entries" under the "Administration" section of the Admin UI.

!!! info
    Django Admin Log Entries are automatically created when administrative changes happen and have always existed natively in Django Admin. This feature is simply providing a read-only UI view for admin/privileged users to access them with more ease.

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
## v2.1.7 (2024-03-05)

### Fixed

- [#5387](https://github.com/nautobot/nautobot/issues/5387) - Fixed an error in the Dockerfile that resulted in `pyuwsgi` being installed without SSL support.

## v2.1.6 (2024-03-04)

### Security

- [#5319](https://github.com/nautobot/nautobot/issues/5319) - Updated `cryptography` to 42.0.4 due to CVE-2024-26130. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added

- [#5172](https://github.com/nautobot/nautobot/issues/5172) - Added Collapse Capable Side Navbar: Side Navbar is now able to be expanded and collapsed
- [#5172](https://github.com/nautobot/nautobot/issues/5172) - Added Expandable Main Content: The Main Content part of the UI grows as the Side Navbar collapses and shrinks as the Side Navbar expands.
- [#5172](https://github.com/nautobot/nautobot/issues/5172) - Added Better mobile friendly bottom navbar: This update will switch to vertically aligned bottom nav menu items once a certain media query is hit, making for a better mobile experience.
- [#5172](https://github.com/nautobot/nautobot/issues/5172) - Added automatic Side Navbar collapse for mobile devices.  This is based on media query and will trigger at specific width.
- [#5329](https://github.com/nautobot/nautobot/issues/5329) - Added caching of `ChangeLoggedModelsQuery().as_queryset()` to improve performance when saving many objects in a change-logged context.
- [#5361](https://github.com/nautobot/nautobot/issues/5361) - Added `nautobot.core.testing.forms.FormTestCases` base class and added it to `nautobot.apps.testing` as well.

### Changed

- [#5082](https://github.com/nautobot/nautobot/issues/5082) - Adjusted Edit / Create panels to occupy more page width on medium and large screens.

### Fixed

- [#4106](https://github.com/nautobot/nautobot/issues/4106) - Fixed inefficient query in VirtualMachine create form.
- [#5172](https://github.com/nautobot/nautobot/issues/5172) - Fixed Brand Icon mouseover Background: Fix for mouseover effect on the Brand / Icon (was flashing white background vs being transparent) when in dark mode.
- [#5307](https://github.com/nautobot/nautobot/issues/5307) - Fixed Custom Field form field(s) missing from git repository edit form.
- [#5309](https://github.com/nautobot/nautobot/issues/5309) - Fixed `Tenant` UI detail view breadcrumb with invalid `TenantGroup` filter link.
- [#5309](https://github.com/nautobot/nautobot/issues/5309) - Fixed `TenantGroup` UI detail view with invalid "add tenant" button invalid `query_params` link.
- [#5309](https://github.com/nautobot/nautobot/issues/5309) - Fixed `DeviceForm` invalid `cluster` field `query_params`.
- [#5309](https://github.com/nautobot/nautobot/issues/5309) - Fixed `PrefixForm` invalid `vlan` and `vlan_group` fields `query_params`.
- [#5311](https://github.com/nautobot/nautobot/issues/5311) - Fixed dependencies in various migration files.
- [#5332](https://github.com/nautobot/nautobot/issues/5332) - Fixed Docker image missing OS-level dependencies for SSO (SAML) support.
- [#5334](https://github.com/nautobot/nautobot/issues/5334) - Fixed migration from 1.x failing when specific duplicate prefixes are present.
- [#5343](https://github.com/nautobot/nautobot/issues/5343) - Fixed incorrect reference for `device.device_role` on the Rack detail view for non-racked device objects.
- [#5345](https://github.com/nautobot/nautobot/issues/5345) - Fixed intermittent 405 errors when using the Docker image with SAML authentication.
- [#5346](https://github.com/nautobot/nautobot/issues/5346) - Fixed device LLDP view to work when interface names include a space.
- [#5365](https://github.com/nautobot/nautobot/issues/5365) - Fixed `invalidate_max_depth_cache` itself calculating `max_depth` on querysets without tree fields.

### Documentation

- [#4419](https://github.com/nautobot/nautobot/issues/4419) - Added documentation on `nautobot.apps` import locations.
- [#4419](https://github.com/nautobot/nautobot/issues/4419) - Added documentation about the supported public interfaces.
- [#4419](https://github.com/nautobot/nautobot/issues/4419) - Removed some incorrect content from the documentation about nav menu changes that were reverted during 2.0 development.
- [#4511](https://github.com/nautobot/nautobot/issues/4511) - Added documentation on how to correctly implement NautobotUIViewSet with custom views.
- [#5284](https://github.com/nautobot/nautobot/issues/5284) - Added a quick overview of the most used models.
- [#5311](https://github.com/nautobot/nautobot/issues/5311) - Added documentation on writing custom migrations.
- [#5326](https://github.com/nautobot/nautobot/issues/5326) - Fixed simple typo in creating-location-types-and-locations.md.
- [#5330](https://github.com/nautobot/nautobot/issues/5330) - Updated SSO documentation to include a view for presenting SAML metadata.
- [#5345](https://github.com/nautobot/nautobot/issues/5345) - Added a note to the Nautobot installation documentation about the need to do `pip3 install --no-binary=pyuwsgi` in order to have SSL support in `pyuwsgi`.
- [#5345](https://github.com/nautobot/nautobot/issues/5345) - Added a note to the SSO documentation about the need to do `pip3 install --no-binary=lxml` to avoid incompatibilities between `lxml` and `xmlsec` packages.

## v2.1.5 (2024-02-21)

### Security

- [#5303](https://github.com/nautobot/nautobot/pull/5303) - Updated `cryptography` to 42.0.2 due to CVE-2024-0727. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added

- [#5171](https://github.com/nautobot/nautobot/issues/5171) - Added `latest` and `latest-py<version>` tags to the `nautobot` Docker images published for the latest stable release of Nautobot.
- [#5210](https://github.com/nautobot/nautobot/issues/5210) - Added `METRICS_AUTHENTICATED` setting to control authentication for the HTTP endpoint `/metrics`.
- [#5243](https://github.com/nautobot/nautobot/issues/5243) - Added support for setting display_field on DynamicModelChoiceField to nested values in suggested choices list.

### Changed

- [#5171](https://github.com/nautobot/nautobot/issues/5171) - Changed the tagging of `nautobot-dev` Docker images to reserve the `latest` and `latest-py<version>` tags for the latest stable release of Nautobot, rather than the latest build from the `develop` branch.
- [#5254](https://github.com/nautobot/nautobot/issues/5254) - Changed `TreeQuerySet.ancestors` implementation to a more efficient approach for shallow trees.
- [#5254](https://github.com/nautobot/nautobot/issues/5254) - Changed the location detail view not to annotate tree fields on its queries.
- [#5267](https://github.com/nautobot/nautobot/issues/5267) - Updated navbar user dropdown with chevron.

### Fixed

- [#5058](https://github.com/nautobot/nautobot/issues/5058) - Changed more filter parameters from `location_id` to `location` in `virtualization/forms.py`.
- [#5121](https://github.com/nautobot/nautobot/issues/5121) - Fixed an issue where deleting a git repository resulted in a job result stuck in running state.
- [#5186](https://github.com/nautobot/nautobot/issues/5186) - Fixed a case where an IPAddress created with a `host` and `mask_length` would default to a null `ip_version`.
- [#5267](https://github.com/nautobot/nautobot/issues/5267) - Fixed hover coloring after closing/reopening navbar dropdown.
- [#5267](https://github.com/nautobot/nautobot/issues/5267) - Fixed button spacing when there are multiple buttons in navbar.
- [#5283](https://github.com/nautobot/nautobot/issues/5283) - Fixed inconsistent ordering of IP addresses in various tables.

### Documentation

- [#3349](https://github.com/nautobot/nautobot/issues/3349) - Added annotations to document the importance of keeping the TIME_ZONE setting consistent on Nautobot web servers and Celery Beat servers.
- [#5297](https://github.com/nautobot/nautobot/issues/5297) - Updated the low level application stack diagram to orient user traffic coming from the top.

### Housekeeping

- [#5267](https://github.com/nautobot/nautobot/issues/5267) - Reorganized navbar css rules in `base.css`.

## v2.1.4 (2024-02-08)

### Security

- [#5251](https://github.com/nautobot/nautobot/issues/5251) - Updated `Django` dependency to 3.2.24 due to CVE-2024-24680.

### Fixed

- [#5254](https://github.com/nautobot/nautobot/issues/5254) - Fixed `TypeError` and similar exceptions thrown when rendering certain App data tables in v2.1.3.

### Documentation

- [#4778](https://github.com/nautobot/nautobot/issues/4778) - Added troubleshooting documentation for PostgreSQL databases with unsupported encoding settings.

### Housekeeping

- [#5240](https://github.com/nautobot/nautobot/issues/5240) - Changed test config to use `constance.backends.memory.MemoryBackend` to avoid intermittent failures in parallel tests.

## v2.1.3 (2024-02-05)

### Security

- [#5151](https://github.com/nautobot/nautobot/issues/5151) - Updated `pillow` dependency to 10.2.0 due to CVE-2023-50447.

### Added

- [#4981](https://github.com/nautobot/nautobot/issues/4981) - Add serial types to InterfaceTypeChoices.
- [#5012](https://github.com/nautobot/nautobot/issues/5012) - Added database indexes to the ObjectChange model to improve performance when filtering by `user_name`, `changed_object`, or `related_object`, and also by `changed_object` in combination with `user` or `user_name`.
- [#5169](https://github.com/nautobot/nautobot/issues/5169) - Added support for user session profiling via django-silk.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Added Navbar dropdown arrow rotation on open/close.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Added behavior of resetting navbar state when the "home" link is clicked.

### Changed

- [#5149](https://github.com/nautobot/nautobot/issues/5149) - Updated the Job List to show Job Hook Receiver and Job Button Receiver Jobs, which were previously being hidden from view.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Changed navbar dropdown link behavior to turn orange when active/clicked; state is saved.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Changed navbar dropdown link hover style.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Changed navbar state save to use session storage.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Changed navbar dropdown to use chevron icon instead of carets.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Aligned navbar dropdown icons to the right.

### Removed

- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Removed unneeded tooltip of dropdown title.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Removed navbar dropdown links underlining.

### Fixed

- [#3664](https://github.com/nautobot/nautobot/issues/3664) - Fixed AssertionError when querying Date type custom fields in GraphQL.
- [#4898](https://github.com/nautobot/nautobot/issues/4898) - Improved automatic query optimization when rendering object list views.
- [#4898](https://github.com/nautobot/nautobot/issues/4898) - Optimized database queries to improve performance of `/api/ipam/prefixes/` and `/api/ipam/vrfs/` REST API endpoints.
- [#5067](https://github.com/nautobot/nautobot/issues/5067) - Fixed missing search filter on ExternalIntegration.
- [#5146](https://github.com/nautobot/nautobot/issues/5146) - Changed nav menu items to collapse in a smooth animated way, rather than jumping 100% open immediately and covering menu items below. Previously opened menu items now collapse smoothly as well.
- [#5146](https://github.com/nautobot/nautobot/issues/5146) - Changed nav menu so that menu expansion now pushes other menus below it downward rather than covering them (z axis).
- [#5146](https://github.com/nautobot/nautobot/issues/5146) - Changed nav menu headers to not lose their color after a link was clicked.
- [#5146](https://github.com/nautobot/nautobot/issues/5146) - Added nav menu state (expanded or closed) and scroll position to local storage, allowing it to be maintained on page refresh, link clicked, or page reload.
- [#5174](https://github.com/nautobot/nautobot/issues/5174) - Added missing postgresql public schema permission grant command.
- [#5178](https://github.com/nautobot/nautobot/issues/5178) - Fixed navbar dropdown links alignment and spacing.
- [#5198](https://github.com/nautobot/nautobot/issues/5198) - Fixed error in device and rack dropdowns when attempting to add an Interface to an InterfaceRedundancyGroup.

### Dependencies

- [#4821](https://github.com/nautobot/nautobot/issues/4821) - Updated `MarkupSafe` dependency to 2.1.5.
- [#4821](https://github.com/nautobot/nautobot/issues/4821) - Updated `mysqlclient` dependency to 2.2.3.
- [#4821](https://github.com/nautobot/nautobot/issues/4821) - Updated `python-slugify` dependency to 8.0.3.
- [#4821](https://github.com/nautobot/nautobot/issues/4821) - Updated `pyuwsgi` dependency to 2.0.23.

### Housekeeping

- [#4821](https://github.com/nautobot/nautobot/issues/4821) - Updated `mkdocs-section-index` documentation dependency to 0.3.8.
- [#4821](https://github.com/nautobot/nautobot/issues/4821) - Updated `ruff` development dependency to 0.1.15.
- [#5130](https://github.com/nautobot/nautobot/issues/5130) - Added experimental `--parallel` option to `invoke unittest`.
- [#5163](https://github.com/nautobot/nautobot/issues/5163) - Added `--parallel` flag to `invoke unittest` in CI.
- [#5163](https://github.com/nautobot/nautobot/issues/5163) - Fixed code coverage calculation when running `invoke unittest --parallel`.
- [#5163](https://github.com/nautobot/nautobot/issues/5163) - Changed `invoke unittest` and `invoke integration-test` to automatically report code coverage on successful completion.
- [#5163](https://github.com/nautobot/nautobot/issues/5163) - Changed test code coverage analysis to exclude the test code itself from the analysis.
- [#5206](https://github.com/nautobot/nautobot/issues/5206) - Added q filter test for ExternalIntegration.

## v2.1.2 (2024-01-22)

### Security

- [#5054](https://github.com/nautobot/nautobot/issues/5054) - Added validation of redirect URLs to the "Add a new IP Address" and "Assign an IP Address" views.
- [#5109](https://github.com/nautobot/nautobot/issues/5109) - Removed `/files/get/` URL endpoint (for viewing FileAttachment files in the browser), as it was unused and could potentially pose security issues.
- [#5133](https://github.com/nautobot/nautobot/issues/5133) - Fixed an XSS vulnerability ([GHSA-v4xv-795h-rv4h](https://github.com/nautobot/nautobot/security/advisories/GHSA-v4xv-795h-rv4h)) in the `render_markdown()` utility function used to render comments, notes, job log entries, etc.

### Added

- [#3877](https://github.com/nautobot/nautobot/issues/3877) - Added global filtering to Job Result log table, enabling search across all pages.
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Enhanced the `sanitize` function to also handle sanitization of lists and tuples of strings.
- [#5133](https://github.com/nautobot/nautobot/issues/5133) - Enhanced Markdown-supporting fields (`comments`, `description`, Notes, Job log entries, etc.) to also permit the use of a limited subset of "safe" HTML tags and attributes.

### Changed

- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Changed the `nautobot-server runjob` management command to check whether the requested user has permission to run the requested job.
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Changed the `nautobot-server runjob` management command to check whether the requested job is installed and enabled.
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Changed the `nautobot-server runjob` management command to check whether a Celery worker is running when invoked without the `--local` flag.
- [#5131](https://github.com/nautobot/nautobot/issues/5131) - Improved the performance of the `/api/dcim/locations/` REST API.

### Removed

- [#5078](https://github.com/nautobot/nautobot/issues/5078) - Removed `nautobot-server startplugin` management command.

### Fixed

- [#4075](https://github.com/nautobot/nautobot/issues/4075) - Fixed sorting of Device Bays list view by installed device status.
- [#4444](https://github.com/nautobot/nautobot/issues/4444) - Fixed Sync Git Repository requires non-matching permissions for UI vs API.
- [#4998](https://github.com/nautobot/nautobot/issues/4998) - Fixed inability to import CSVs where later rows include references to records defined by earlier rows.
- [#5024](https://github.com/nautobot/nautobot/issues/5024) - Improved performance of the Job Result list view by optimizing the way JobLogEntry records are queried.
- [#5024](https://github.com/nautobot/nautobot/issues/5024) - Improved performance of the Device list view by including the manufacturer name in the table queryset.
- [#5024](https://github.com/nautobot/nautobot/issues/5024) - Improved performance of most ObjectListViews by optimizing how Custom fields, Computed fields, and Relationships are queried.
- [#5024](https://github.com/nautobot/nautobot/issues/5024) - Fixed a bug that caused IPAddress objects to query their parent Prefix and Namespace every time they were instantiated.
- [#5024](https://github.com/nautobot/nautobot/issues/5024) - Improved performance of the IPAddress list view by including the namespace in the table queryset.
- [#5024](https://github.com/nautobot/nautobot/issues/5024) - Updated bulk-edit and bulk-delete views to auto-hide any "actions" column in the table of objects being edited or deleted.
- [#5031](https://github.com/nautobot/nautobot/issues/5031) - Updated the default sanitizer pattern to include secret(s) and to be flexible with python dictionaries.
- [#5043](https://github.com/nautobot/nautobot/issues/5043) - Fixed early return conditional in `ensure_git_repository`.
- [#5045](https://github.com/nautobot/nautobot/issues/5045) - Adjusted Bootstrap grid breakpoints to account for the space occupied by the sidebar, fixing various page rendering.
- [#5054](https://github.com/nautobot/nautobot/issues/5054) - Fixed missing search logic on the "Assign an IP Address" view.
- [#5058](https://github.com/nautobot/nautobot/issues/5058) - Changed filter query parameters from `location_id` to `location` in `virtualization/forms.py`.
- [#5081](https://github.com/nautobot/nautobot/issues/5081) - Fixed core.tables.BaseTable to terminate dynamic queryset's building of pre-fetched fields upon first non-RelatedField of a column.
- [#5095](https://github.com/nautobot/nautobot/issues/5095) - Fixed a couple of potential `KeyError` when refreshing Git repository Jobs.
- [#5095](https://github.com/nautobot/nautobot/issues/5095) - Fixed color highlighting of `error` and `critical` log entries when viewing a Job Result.
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Fixed missing log messages when errors occur during `Job.__call__()` initial setup.
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Fixed misleading "Job completed" message from being logged when a Job aborted.
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Fixed an error in `nautobot-server runjob` if a job returned data other than a dict.
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Fixed misleading "SUCCESS" message when `nautobot-server runjob` resulted in any JobResult status other than "FAILED".
- [#5102](https://github.com/nautobot/nautobot/issues/5102) - Fixed incorrect JobResult data when using `nautobot-server runjob --local` or `JobResult.execute_job()`.
- [#5111](https://github.com/nautobot/nautobot/issues/5111) - Fixed rack group and rack filtering by the location selected in the device bulk edit form.

### Dependencies

- [#5083](https://github.com/nautobot/nautobot/issues/5083) - Updated GitPython to version 3.1.41 to address Windows security vulnerability [GHSA-2mqj-m65w-jghx](https://github.com/gitpython-developers/GitPython/security/advisories/GHSA-2mqj-m65w-jghx).
- [#5086](https://github.com/nautobot/nautobot/issues/5086) - Updated Jinja2 to version 3.1.3 to address to address XSS security vulnerability [GHSA-h5c8-rqwp-cp95](https://github.com/pallets/jinja/security/advisories/GHSA-h5c8-rqwp-cp95).
- [#5133](https://github.com/nautobot/nautobot/issues/5133) - Added `nh3` HTML sanitization library as a dependency.

### Documentation

- [#5078](https://github.com/nautobot/nautobot/issues/5078) - Added a link to the `cookiecutter-nautobot-app` project in the App developer documentation.

### Housekeeping

- [#4906](https://github.com/nautobot/nautobot/issues/4906) - Added automatic superuser creation environment variables to docker development environment.
- [#4906](https://github.com/nautobot/nautobot/issues/4906) - Updated VS Code Dev Containers configuration and documentation.
- [#5076](https://github.com/nautobot/nautobot/issues/5076) - Updated `packaging` dependency to permit newer versions since it follows CalVer rather than SemVer.
- [#5079](https://github.com/nautobot/nautobot/issues/5079) - Increased overly-brief `start_period` for development `nautobot` container to allow sufficient time for initial migrations to run.
- [#5079](https://github.com/nautobot/nautobot/issues/5079) - Fixed bug with invoke cli and invoke nbshell.
- [#5118](https://github.com/nautobot/nautobot/issues/5118) - Updated PR template to encourage inclusion of screenshots.

## v2.1.1 (2024-01-08)

### Added

- [#5046](https://github.com/nautobot/nautobot/issues/5046) - Updated the LocationType clone process to pre-populate the original object's parent, nestable and content type fields.

### Changed

- [#4992](https://github.com/nautobot/nautobot/issues/4992) - Added change-logging (ObjectChange support) for the ObjectPermission model.

### Removed

- [#5033](https://github.com/nautobot/nautobot/issues/5033) - Removed alpha UI from the main code base for now (it still exists in a prototype branch) to reduce the burden of maintaining its dependencies in the meantime.
- [#5035](https://github.com/nautobot/nautobot/issues/5035) - Removed nodesource apt repository from Dockerfile.

### Fixed

- [#4606](https://github.com/nautobot/nautobot/issues/4606) - Fixed an error when attempting to "Save Changes" to an existing GraphQL saved query via the GraphiQL UI.
- [#4606](https://github.com/nautobot/nautobot/issues/4606) - Fixed incorrect positioning of the "Save Changes" button in the "Queries" menu in the GraphiQL UI.
- [#4606](https://github.com/nautobot/nautobot/issues/4606) - Fixed incorrect specification of the "variables" field in the GraphQL saved query REST API.
- [#4606](https://github.com/nautobot/nautobot/issues/4606) - Fixed a display glitch in the detail view for GraphQL saved queries.
- [#5005](https://github.com/nautobot/nautobot/issues/5005) - Fixed missing schema field in config context create/edit forms.
- [#5020](https://github.com/nautobot/nautobot/issues/5020) - Fixed display of secrets when editing a SecretsGroup.

### Documentation

- [#5019](https://github.com/nautobot/nautobot/issues/5019) - Updated the documentation on the usage of the `nautobot-server runjob` management command.
- [#5023](https://github.com/nautobot/nautobot/issues/5023) - Fixed some typos in the 2.1.0 release notes.
- [#5027](https://github.com/nautobot/nautobot/issues/5027) - Fixed typo in Device Redundancy Group docs.
- [#5044](https://github.com/nautobot/nautobot/issues/5044) - Updated the documentation on `nautobot_database_ready` signal handlers with a warning.

### Housekeeping

- [#5039](https://github.com/nautobot/nautobot/issues/5039) - Updated `ruff` development dependency to `~0.1.10`.
- [#5039](https://github.com/nautobot/nautobot/issues/5039) - Removed `black` and `flake8` as development dependencies as they're fully replaced by `ruff` now.
- [#5039](https://github.com/nautobot/nautobot/issues/5039) - Removed `black` and `flake8` steps from CI.
- [#5039](https://github.com/nautobot/nautobot/issues/5039) - Enabled `DJ` Ruff rules (`flake8-django`) and addressed all warnings raised.
- [#5039](https://github.com/nautobot/nautobot/issues/5039) - Enabled `PIE` Ruff rules except for `PIE808` (`flake8-pie`) and addressed all warnings raised.
- [#5039](https://github.com/nautobot/nautobot/issues/5039) - Enabled `RUF` Ruff rules except for `RUF012` and addressed all warnings raised.
- [#5039](https://github.com/nautobot/nautobot/issues/5039) - Enabled remaining `S` Ruff rules (`flake8-bandit`) and addressed all warnings raised.
- [#5049](https://github.com/nautobot/nautobot/issues/5049) - Fixed an intermittent timing-related failure in `DynamicGroupModelTest.test_member_caching_enabled` test case.
- [#5053](https://github.com/nautobot/nautobot/issues/5053) - Removed reference to develop-1.6 branch in CI workflow.
- [#5055](https://github.com/nautobot/nautobot/issues/5055) - Enabled `I` Ruff rules (`isort`) and addressed all warnings raised.
- [#5055](https://github.com/nautobot/nautobot/issues/5055) - Removed `isort` as a development dependency as it's fully replaced by `ruff` now.

## v2.1.0 (2023-12-22)

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
