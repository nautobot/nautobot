<!-- markdownlint-disable MD024 -->

# Nautobot v2.2

This document describes all new features and changes in Nautobot 2.2.

## Release Overview

### Added

#### Contact and Team Models ([#230](https://github.com/nautobot/nautobot/issues/230))

Contact and Team are models that represent an individual and a group of individuals who can be linked to an object. Contacts and teams store the necessary information (name, phone number, email, and address) to uniquely identify and contact them. They are added to track ownerships of organizational entities and to manage resources more efficiently in Nautobot. Check out the documentation for [Contact](../user-guide/core-data-model/extras/contact.md) and [Team](../user-guide/core-data-model/extras/team.md). There is also a [user guide](../user-guide/feature-guides/contacts-and-teams.md) available on how to utilize these models.

A new management command has been introduced to assist with migrating the Location fields `contact_name`, `contact_phone` and `contact_email` to the new Contact and Team models. This command can be invoked with `nautobot-server migrate_location_contacts` and will present a series of prompts to guide you through migrating Locations that have data in the `contact_name`, `contact_phone`, or `contact_email` fields which are not already associated to a Contact or Team. This command will give you the option to create new Contacts or Teams or, if a similar Contact or Team already exists, to link the Location to the existing Contact or Team. Note that when assigning a Location to an existing Contact or Team that has a blank `phone` or `email` field, the value from the Location will be copied to the Contact/Team. After a Location has been associated to a Contact or Team, the `contact_name`, `contact_phone`, and `contact_email` fields will be cleared from the Location.

#### Controller Model ([#3111](https://github.com/nautobot/nautobot/issues/3111))

Controller models have been added to the `dcim` app. A Controller in Nautobot is an abstraction meant to represent network or SDN (Software-Defined Networking) controllers. These may include, but are not limited to, wireless controllers, cloud-based network management systems, and other forms of central network control mechanisms.

For more details, refer to the user guide for a [`Controller` model](../user-guide/core-data-model/dcim/controller.md), a [`ControllerManagedDeviceGroup` model](../user-guide/core-data-model/dcim/controllermanageddevicegroup.md), or developer documentation for [Controllers](../development/core/controllers.md).

#### DeviceFamily Model ([#3559](https://github.com/nautobot/nautobot/issues/3559))

A [Device Family](../user-guide/core-data-model/dcim/devicefamily.md) represents a group of related [Device Types](../user-guide/core-data-model/dcim/devicetype.md). A Device Type can be optionally assigned to a Device Family. Each Device Family must have a unique name and may have a description assigned to it.

#### Jobs Tile View ([#5129](https://github.com/nautobot/nautobot/issues/5129))

Job list is now available in two display variants: list and tiles. List is a standard table view with no major changes introduced. Tiles is a new type of view displaying jobs in a two-dimensional grid.

#### Prefix and VLAN Many Locations ([#4334](https://github.com/nautobot/nautobot/issues/4334), [#4412](https://github.com/nautobot/nautobot/issues/4412))

The Prefix and VLAN models have replaced their single `location` foreign-key field with a many-to-many `locations` field, allowing multiple Locations to be attached to a single Prefix or VLAN. To ensure backwards compatibility with pre-2.2 code, these models now have a `location` property which can be retrieved or set for the case of a single associated Location, but will raise a `MultipleObjectsReturned` exception if the Prefix or VLAN in question has more than one associated Location. REST API versions 2.0 and 2.1 similarly still have a `location` field, while REST API version 2.2 and later replace this with `locations`.

#### Software Image File and Software Version models ([#1](https://github.com/nautobot/nautobot/issues/1))

New models have been added for Software Image Files and Software Versions. These models are used to track the software versions of Devices, Inventory Items and Virtual Machines and their associated image files. These models have been ported from the [Device Lifecycle Management App](https://github.com/nautobot/nautobot-app-device-lifecycle-mgmt/) and a future update to that app will migrate all existing data from the `nautobot_device_lifecycle_mgmt.SoftwareImageLCM` and `nautobot_device_lifecycle_mgmt.SoftwareLCM` models to the `dcim.SoftwareImageFile` and `dcim.SoftwareVersion` models added here.

Software Versions must be associated to a Platform. Software Image Files must be associated to one Software Version and may be associated to one or more Device Types. Devices, Inventory Items and Virtual Machines may be associated to one Software Version to track their current version. See the documentation for [Software Image File](../user-guide/core-data-model/dcim/softwareimagefile.md) and [Software Version](../user-guide/core-data-model/dcim/softwareversion.md). There is also a [user guide](../user-guide/feature-guides/software-image-files-and-versions.md) with instructions on how to create these models.

#### Syntax Highlighting ([#5098](https://github.com/nautobot/nautobot/issues/5098))

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
## v2.2.7 (2024-07-08)

### Security

- [#5891](https://github.com/nautobot/nautobot/issues/5891) - Updated `certifi` to `2024.7.4` to address `CVE-2024-39689`. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Fixed

- [#4237](https://github.com/nautobot/nautobot/issues/4237) - Fixed display issue with multiple tags filter on dynamic groups. Multiple Tags are now correctly displayed with an AND.
- [#5093](https://github.com/nautobot/nautobot/issues/5093) - Fixed blank page redirect when syncing or running a dry run on a GIT Repo with no workers available; now redirects to the GIT Repo Detail page with an error message.
- [#5804](https://github.com/nautobot/nautobot/issues/5804) - Fixed operation of "Mark planned"/"Mark installed" button in Device component table views.
- [#5832](https://github.com/nautobot/nautobot/issues/5832) - Fixed lack of API versioning of responses to a POST to `/api/ipam/prefixes/<id>/available-prefixes/` to allocate child prefixes of a prefix.
- [#5832](https://github.com/nautobot/nautobot/issues/5832) - Fixed incorrect OpenAPI schema for `/api/ipam/prefixes/<id>/available-prefixes/` and `/api/ipam/prefixes/<id>/available-ips/`.

### Dependencies

- [#5518](https://github.com/nautobot/nautobot/issues/5518) - Updated `drf-spectacular` to version `0.27.2`.
- [#5896](https://github.com/nautobot/nautobot/pull/5896) - Pinned dev dependency `faker` to `>=0.7.0,<26.0.0` to work around breaking change in v26.0.0 ([faker/#2070](https://github.com/joke2k/faker/issues/2070)).

### Housekeeping

- [#5847](https://github.com/nautobot/nautobot/issues/5847) - Updated the term plugin to app within the GitHub templates.
- [#5858](https://github.com/nautobot/nautobot/issues/5858) - Enhanced the test runner to include a hash of applied database migrations as part of the factory dump filename, reducing the likelihood of using the wrong cached data for a given branch.

## v2.2.6 (2024-06-24)

### Security

- [#5821](https://github.com/nautobot/nautobot/issues/5821) - Updated `urllib3` to 2.2.2 due to CVE-2024-37891. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added

- [#5550](https://github.com/nautobot/nautobot/issues/5550) - Added support for specifying a tag or a commit hash as the GitRepository `branch` value.
- [#5550](https://github.com/nautobot/nautobot/issues/5550) - Added an `enabled` flag to the JobButton class; disabled JobButtons will not appear in the UI.
- [#5793](https://github.com/nautobot/nautobot/issues/5793) - Added `--print-hashes` option to `nautobot-server generate_test_data` command.
- [#5807](https://github.com/nautobot/nautobot/issues/5807) - Added the ability to sort and filter the `IPAddress` list view by the `nat_inside` field.

### Changed

- [#5550](https://github.com/nautobot/nautobot/issues/5550) - Changed the behavior on removal of a previously-installed Job class to additionally auto-disable any JobButtons, JobHooks, and ScheduledJobs referencing this class.

### Fixed

- [#5550](https://github.com/nautobot/nautobot/issues/5550) - Fixed an issue where config-contexts and export-templates sourced from a Git repository might not be automatically deleted from Nautobot after removing them from the repository and resyncing it.
- [#5550](https://github.com/nautobot/nautobot/issues/5550) - Fixed an exception that might be raised when performing a Git repository "dry-run" sync if certain types of diffs are present.
- [#5782](https://github.com/nautobot/nautobot/issues/5782) - Fixed an issue with Job code not being fully reloaded after syncing a Git repository.
- [#5809](https://github.com/nautobot/nautobot/issues/5809) - Fixed missing support for the GitRepository model in GraphQL.
- [#5819](https://github.com/nautobot/nautobot/issues/5819) - Fixed inability to use bare (local-DNS) hostnames when specifying a GitRepository remote URL.

### Documentation

- [#5726](https://github.com/nautobot/nautobot/issues/5726) - Updated, cleaned up, and separated out the main landing page for Nautobot docs.
- [#5752](https://github.com/nautobot/nautobot/issues/5752) - Corrected incorrect entry for `nautobot.utilities.ordering` in `v2-code-location-changes` table.
- [#5754](https://github.com/nautobot/nautobot/issues/5754) - Updated `mkdocs-material` to 9.5.25.

### Housekeeping

- [#5754](https://github.com/nautobot/nautobot/issues/5754) - Updated development dependencies `requests` to `~2.32.2` and `watchdog` to `~4.0.1`.
- [#5793](https://github.com/nautobot/nautobot/issues/5793) - Refactored `generate_test_data` implementation for improved debuggability.
- [#5793](https://github.com/nautobot/nautobot/issues/5793) - Fixed a bug in `ControllerManagedDeviceGroupFactory` that could result in nondeterministic test data.

## v2.2.5 (2024-05-28)

### Security

- [#5740](https://github.com/nautobot/nautobot/issues/5740) - Updated `requests` to `2.32.1` to address [GHSA-9wx4-h78v-vm56](https://github.com/psf/requests/security/advisories/GHSA-9wx4-h78v-vm56). This is not a direct dependency so it will not auto-update when upgrading Nautobot. Please be sure to update your local environment.
- [#5757](https://github.com/nautobot/nautobot/issues/5757) - Fixed missing member object permission enforcement (e.g., enforce Device permissions for a Dynamic Group containing Devices) when viewing Dynamic Group member objects in the UI or REST API ([GHSA-qmjf-wc2h-6x3q](https://github.com/nautobot/nautobot/security/advisories/GHSA-qmjf-wc2h-6x3q)).

### Added

- [#5588](https://github.com/nautobot/nautobot/issues/5588) - Added "Add VRFs" and "Remove VRFs" fields to `PrefixBulkEditForm`.
- [#5588](https://github.com/nautobot/nautobot/issues/5588) - Added "Add Prefixes" and "Remove Prefixes" fields to `VRFBulkEditForm`.
- [#5655](https://github.com/nautobot/nautobot/issues/5655) - Added "Device Family" as a configurable column in the Device Types table view.
- [#5690](https://github.com/nautobot/nautobot/issues/5690) - Added a generic test case that asserts that all list views provide an appropriate FilterForm class.
- [#5747](https://github.com/nautobot/nautobot/issues/5747) - Added "Circuit Terminations" navigation menu item.

### Removed

- [#5690](https://github.com/nautobot/nautobot/issues/5690) - Removed deprecated `CustomFieldFilterForm` alias of `CustomFieldModelFilterFormMixin` as this would have caused confusion with the newly added `CustomFieldFilterForm` class providing filtering support for the Custom Fields list view.

### Fixed

- [#5564](https://github.com/nautobot/nautobot/issues/5564) - Fixed `ContactAssociationFilterSet.associated_object_type` not using the right filter field.
- [#5669](https://github.com/nautobot/nautobot/issues/5669) - Fixed `AttributeError` thrown when deleting software versions or images from list views.
- [#5690](https://github.com/nautobot/nautobot/issues/5690) - Fixed a Javascript error when attempting to filter certain list views.
- [#5690](https://github.com/nautobot/nautobot/issues/5690) - Added missing "default" filter forms for a number of list views.
- [#5703](https://github.com/nautobot/nautobot/issues/5703) - Fixed unintended creation of `_custom_field_data` filter on various FilterSets.
- [#5703](https://github.com/nautobot/nautobot/issues/5703) - Fixed `Filter "_custom_field_data" on ... is not GraphQL safe, and will be omitted` warning logs when generating the GraphQL schema.
- [#5707](https://github.com/nautobot/nautobot/issues/5707) - Fixed incorrect installation of `xmlsec` library in the Nautobot Docker images.
- [#5708](https://github.com/nautobot/nautobot/issues/5708) - Fixed integrity error when doing bulk edits that resulted from a delete operation on a related model.
- [#5738](https://github.com/nautobot/nautobot/issues/5738) - Fixed incorrect API query parameters when selecting VLANs to apply to a VM Interface.
- [#5738](https://github.com/nautobot/nautobot/issues/5738) - Fixed incorrect query parameters when accessing or creating Clusters from a Cluster Type detail view.

### Documentation

- [#5699](https://github.com/nautobot/nautobot/issues/5699) - Updated to `mkdocs~1.6.0` and `mkdocs-material~9.5.23`.
- [#5699](https://github.com/nautobot/nautobot/issues/5699) - Fixed a number of broken links within the documentation.

### Housekeeping

- [#5699](https://github.com/nautobot/nautobot/issues/5699) - Updated `pylint` to `~3.1.1`.
- [#5740](https://github.com/nautobot/nautobot/issues/5740) - Updated test dependency `requests` to `~2.32.1`.

## v2.2.4 (2024-05-13)

### Security

- [#1858](https://github.com/nautobot/nautobot/issues/1858) - Added sanitization of HTML tags in the content of `BANNER_TOP`, `BANNER_BOTTOM`, and `BANNER_LOGIN` configuration to prevent against potential injection of malicious scripts (stored XSS) via these features ([GHSA-r2hr-4v48-fjv3](https://github.com/nautobot/nautobot/security/advisories/GHSA-r2hr-4v48-fjv3)).
- [#5672](https://github.com/nautobot/nautobot/issues/5672) - Updated `Jinja2` dependency to `3.1.4` to address `CVE-2024-34064`.

### Added

- [#1858](https://github.com/nautobot/nautobot/issues/1858) - Added support in `BRANDING_FILEPATHS` configuration to specify a custom `css` and/or `javascript` file to be added to Nautobot page content.
- [#1858](https://github.com/nautobot/nautobot/issues/1858) - Added Markdown support to the `BANNER_TOP`, `BANNER_BOTTOM`, and `BANNER_LOGIN` configuration settings.

### Fixed

- [#4986](https://github.com/nautobot/nautobot/issues/4986) - Fixed inconsistent use of super causing `active_tab` context to be missing from several views.
- [#5644](https://github.com/nautobot/nautobot/issues/5644) - Made the uniqueness constraints between the ContactAssociation model and the related API serializer consistent.
- [#5684](https://github.com/nautobot/nautobot/issues/5684) - Fixed standard CSV export when using export templates.
- [#5689](https://github.com/nautobot/nautobot/issues/5689) - Fixed change logging for bulk delete operations so that user is included in the log.

### Documentation

- [#5661](https://github.com/nautobot/nautobot/issues/5661) - Updated documentation to organize installation instructions and provide easier to use functions from mkdocs.

### Housekeeping

- [#5263](https://github.com/nautobot/nautobot/issues/5263) - Updated `nh3` to `0.2.17` in `poetry.lock`.
- [#5637](https://github.com/nautobot/nautobot/issues/5637) - Removed `"version"` from development `docker-compose.yml` files as newer versions of Docker complain about it being obsolete.
- [#5637](https://github.com/nautobot/nautobot/issues/5637) - Fixed behavior of `invoke stop` so that it also stops the optional `mkdocs` container if present.

## v2.2.3 (2024-04-30)

### Security

- [#5624](https://github.com/nautobot/nautobot/issues/5624) - Updated `social-auth-app-django` dependency to `~5.4.1` to address `CVE-2024-32879`.
- [#5646](https://github.com/nautobot/nautobot/issues/5646) - Fixed a reflected-XSS vulnerability ([GHSA-jxgr-gcj5-cqqg](https://github.com/nautobot/nautobot/security/advisories/GHSA-jxgr-gcj5-cqqg)) in object-list view rendering of user-provided query parameters.

### Added

- [#2946](https://github.com/nautobot/nautobot/issues/2946) - Added custom link support for interfaces, console ports, console server ports, power ports, power outlets, front ports, rear ports, device bays, and inventory items.
- [#5034](https://github.com/nautobot/nautobot/issues/5034) - Added a view to convert location contact information to contacts or teams.
- [#5537](https://github.com/nautobot/nautobot/issues/5537) - Re-added `run_job` generic Celery task as a wrapper for execution of all Nautobot Jobs.
- [#5560](https://github.com/nautobot/nautobot/issues/5560) - Added a template tag which creates a hyperlink that opens in a new tab.
- [#5586](https://github.com/nautobot/nautobot/issues/5586) - Added `nautobot.apps.jobs.get_jobs()` API.

### Changed

- [#5498](https://github.com/nautobot/nautobot/issues/5498) - Changed the `nautobot.extras.jobs.Job` class to no longer be a subclass of `celery.tasks.Task`.

### Fixed

- [#5513](https://github.com/nautobot/nautobot/issues/5513) - Fixed missing `location` field in `Prefix` and `VLAN` GraphQL schema.
- [#5513](https://github.com/nautobot/nautobot/issues/5513) - Restored ability to filter Prefix and VLAN objects at the ORM level by `location`.
- [#5565](https://github.com/nautobot/nautobot/issues/5565) - Fixed optional dependency on `social-auth-core` by removing an extras related to `openidconnect` that no longer exists.
- [#5586](https://github.com/nautobot/nautobot/issues/5586) - Fixed incorrect rendering of Job variables in the ScheduledJob detail view.
- [#5594](https://github.com/nautobot/nautobot/issues/5594) - Fixed Job tiles view not understanding the `per_page` and `page` query parameters.
- [#5595](https://github.com/nautobot/nautobot/issues/5595) - Fixed bug where API Extra Actions weren't displaying the proper name.
- [#5603](https://github.com/nautobot/nautobot/issues/5603) - Fixed config contexts loaded from Git repositories not populating Device Redundancy Group information.
- [#5640](https://github.com/nautobot/nautobot/issues/5640) - Fixed bug in generating the URL parameters for cloning objects.
- [#5642](https://github.com/nautobot/nautobot/issues/5642) - Fixed some cases where stale Job code might be present when Jobs are sourced from `JOBS_ROOT` or a Git repository.
- [#5642](https://github.com/nautobot/nautobot/issues/5642) - Fixed incorrect handling of Job `kwargs` when dry-running a job approval request via the REST API.

### Documentation

- [#5094](https://github.com/nautobot/nautobot/issues/5094) - Added "Reserved Attribute Names" section to the Jobs developer documentation.
- [#5608](https://github.com/nautobot/nautobot/issues/5608) - Updated VLAN documentation with a recommendation for modeling of VLANs with respect to Locations.
- [#5626](https://github.com/nautobot/nautobot/issues/5626) - Added extras features docs to core developer new model checklist.
- [#5635](https://github.com/nautobot/nautobot/issues/5635) - Added borders to tabbed sections of mkdocs.

### Housekeeping

- [#4498](https://github.com/nautobot/nautobot/issues/4498) - Removed redundant `nautobot.extras.plugins.register_jobs` function.
- [#5586](https://github.com/nautobot/nautobot/issues/5586) - Fixed an intermittent ImportError when running tests with certain options.
- [#5605](https://github.com/nautobot/nautobot/issues/5605) - Added prerelease and release workflow to deploy sandbox environments automatically.

## v2.2.2 (2024-04-18)

### Security

- [#5579](https://github.com/nautobot/nautobot/issues/5579) - Updated `sqlparse` to `0.5.0` to fix [GHSA-2m57-hf25-phgg](https://github.com/advisories/GHSA-2m57-hf25-phgg). This is not a direct dependency so it will not auto-update when upgrading Nautobot. Please be sure to update your local environment.

### Added

- [#2459](https://github.com/nautobot/nautobot/issues/2459) - Added `nautobot.extras.utils.bulk_delete_with_bulk_change_logging` helper function for improving performance on bulk delete.
- [#2459](https://github.com/nautobot/nautobot/issues/2459) - Added `nautobot.extras.context_managers.deferred_change_logging_for_bulk_operation` context manager for improving performance on bulk update.

### Changed

- [#2459](https://github.com/nautobot/nautobot/issues/2459) - Improved performance of bulk-edit and bulk-delete UI operations by refactoring change logging logic.
- [#5568](https://github.com/nautobot/nautobot/issues/5568) - Added hyperlink to the total device count number under device family.
- [#5589](https://github.com/nautobot/nautobot/issues/5589) - Fixed an invalid Javascript operator in the LLDP neighbor view.

### Fixed

- [#5580](https://github.com/nautobot/nautobot/issues/5580) - Fixed bugs when assigning a VLAN to an Interface related to the recently introduced many-to-many relationship between VLANs and Locations.
- [#5592](https://github.com/nautobot/nautobot/issues/5592) - Fixed plugins not loading when using Gunicorn.

### Documentation

- [#5583](https://github.com/nautobot/nautobot/issues/5583) - Re-added release note content for v1.6.16 through v1.6.18.

### Housekeeping

- [#5590](https://github.com/nautobot/nautobot/issues/5590) - Fixed upstream testing workflows showing successful when one of the steps fail.

## v2.2.1 (2024-04-15)

### Security

- [#5521](https://github.com/nautobot/nautobot/issues/5521) - Updated `Pillow` dependency to `~10.3.0` to address `CVE-2024-28219`.
- [#5543](https://github.com/nautobot/nautobot/issues/5543) - Updated `jquery-ui` to version `1.13.2` due to `CVE-2022-31160`.
- [#5561](https://github.com/nautobot/nautobot/issues/5561) - Updated `idna` to 3.7 due to CVE-2024-3651. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added

- [#1631](https://github.com/nautobot/nautobot/issues/1631) - Added change logging for custom field background tasks.
- [#5009](https://github.com/nautobot/nautobot/issues/5009) - Added the option to filter objects with select/multi-select custom fields based on the UUID of the defined custom field choice(s), for example `/api/dcim/locations/?cf_multiselect=1ea9237c-3ba7-4985-ba7e-6fd9e9bff813` as an alternative to `/api/dcim/locations/?cf_multiselect=some-choice-value`.
- [#5493](https://github.com/nautobot/nautobot/issues/5493) - Added a configuration setting `METRICS_DISABLED_APPS` to disable app metrics for specific apps.
- [#5540](https://github.com/nautobot/nautobot/issues/5540) - Added total devices count to device family detail page.

### Changed

- [#5274](https://github.com/nautobot/nautobot/issues/5274) - Added a setting that changes all rack unit numbers to display a minimum of two digits in rack elevations.

### Fixed

- [#5469](https://github.com/nautobot/nautobot/issues/5469) - Fixed contacts and teams not being included in the global search.
- [#5489](https://github.com/nautobot/nautobot/issues/5489) - Fixed REST API for Contact and Team incorrectly marking the `phone` and `email` fields as mandatory.
- [#5502](https://github.com/nautobot/nautobot/issues/5502) - Fixed off-by-one error in generic filter testing helper `BaseFilterTestCase.get_filterset_test_values`.
- [#5511](https://github.com/nautobot/nautobot/issues/5511) - Fixed contact tab disappearing when accessing dynamic groups tab.
- [#5515](https://github.com/nautobot/nautobot/issues/5515) - Fixed javascript exception thrown in the Device LLDP neighbors view for neighbors without configured devices/interfaces.
- [#5527](https://github.com/nautobot/nautobot/issues/5527) - Fixed incorrect "members" links in Virtual Chassis list view.
- [#5531](https://github.com/nautobot/nautobot/issues/5531) - Re-added `nautobot.setup()` function mistakenly removed in 2.2.0.

### Dependencies

- [#5495](https://github.com/nautobot/nautobot/issues/5495) - Changed jsonschema version constraint from `>=4.7.0,<4.19.0` to `^4.7.0`.
- [#5517](https://github.com/nautobot/nautobot/issues/5517) - Updated `djangorestframework` to `~3.15.1`.
- [#5521](https://github.com/nautobot/nautobot/issues/5521) - Updated most dependencies to the latest versions available as of 2024-04-01.
- [#5543](https://github.com/nautobot/nautobot/issues/5543) - Updated `jquery` to version `3.7.1`.

### Documentation

- [#5189](https://github.com/nautobot/nautobot/issues/5189) - Added "Model Development Checklist" to the core developer documentation.
- [#5189](https://github.com/nautobot/nautobot/issues/5189) - Merged "Extending Models" documentation into the "Model Development Checklist" documentation.
- [#5526](https://github.com/nautobot/nautobot/issues/5526) - Fixed doc reference to job cprofile file location.

### Housekeeping

- [#5531](https://github.com/nautobot/nautobot/issues/5531) - Removed `nautobot-server pylint` management command from the `example_app`, as pylint can be invoked directly with an appropriate `--init-hook` instead.
- [#5547](https://github.com/nautobot/nautobot/issues/5547) - Fixed TransactionTestCase inheritance order so that `test.client` works in test cases using this class.

## v2.2.0 (2024-03-29)

!!! warning
    Upgrading from beta releases to final releases is never recommended for Nautobot; in the case of 2.2.0b1 to 2.2.0 several data models and database migrations have been modified (see [#5454](https://github.com/nautobot/nautobot/issues/5454)) between the two releases, and so upgrading in place from 2.2.0b1 to 2.2.0 **will not work**.

### Added

- [#4811](https://github.com/nautobot/nautobot/issues/4811) - Added a new generic test case (`test_table_with_indentation_is_removed_on_filter_or_sort`) to `ListObjectsViewTestCase` to test that the tree hierarchy is correctly removed on TreeModel list views when sorting or filtering is applied. This test will also run in these subclasses of the `ListObjectsViewTestCase`: `PrimaryObjectViewTestCase`, `OrganizationalObjectViewTestCase`, and `DeviceComponentViewTestCase`.
- [#5034](https://github.com/nautobot/nautobot/issues/5034) - Added a management command (`nautobot-server migrate_location_contacts`) to help migrate the Location `contact_name`, `contact_email` and `contact_phone` fields to Contact and Teams models.

### Changed

- [#5452](https://github.com/nautobot/nautobot/issues/5452) - Changed the behavior of Prefix table: now they are sortable, and after sorting is applied, all hierarchy indentations are removed.
- [#5454](https://github.com/nautobot/nautobot/issues/5454) - Changed one-to-many links from Controller to `PROTECT` against deleting.
- [#5454](https://github.com/nautobot/nautobot/issues/5454) - Renamed `ControllerDeviceGroup` to `ControllerManagedDeviceGroup`.
- [#5454](https://github.com/nautobot/nautobot/issues/5454) - Renamed `Controller.deployed_controller_device` to `Controller.controller_device`.
- [#5454](https://github.com/nautobot/nautobot/issues/5454) - Renamed `Controller.deployed_controller_group` to `Controller.controller_device_redundancy_group`.
- [#5454](https://github.com/nautobot/nautobot/issues/5454) - Renamed `Device.controller_device_group` to `Device.controller_managed_device_group`.
- [#5454](https://github.com/nautobot/nautobot/issues/5454) - Removed ConfigContext from ControllerManagedDeviceGroup.
- [#5454](https://github.com/nautobot/nautobot/issues/5454) - Removed ConfigContext from Controller.
- [#5475](https://github.com/nautobot/nautobot/issues/5475) - Changed the behavior of Prefix table and other Tree Model tables: now after filtering is applied, all hierarchy indentations are removed.
- [#5487](https://github.com/nautobot/nautobot/issues/5487) - Moved some nav menu items around to make better logical sense and to allow quicker access to more commonly accessed features.

### Fixed

- [#5415](https://github.com/nautobot/nautobot/issues/5415) - Fixed Team(s) field not pre-populating when editing a Contact.
- [#5431](https://github.com/nautobot/nautobot/issues/5431) - Fixed Roles API response containing duplicate entries when filtering on more than one `content_types` value.
- [#5431](https://github.com/nautobot/nautobot/issues/5431) - Fixed Providers API response containing duplicate entries when filtering on more than one `location` value.
- [#5440](https://github.com/nautobot/nautobot/issues/5440) - Fixed `Cannot resolve keyword 'task_id' into field` error when calling `nautobot-server celery result <task_id>`.

### Dependencies

- [#4583](https://github.com/nautobot/nautobot/issues/4583) - Updated pinned version of `social-auth-core` to remove dependency on `python-jose` & it's dependency on `ecdsa`.

### Housekeeping

- [#5435](https://github.com/nautobot/nautobot/issues/5435) - Added `--pattern` argument to `invoke unittest`.
- [#5435](https://github.com/nautobot/nautobot/issues/5435) - Added `--parallel-workers` argument to `invoke unittest`.

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
