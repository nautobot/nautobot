<!-- markdownlint-disable MD024 -->
# Nautobot v1.3

This document describes all new features and changes in Nautobot 1.3.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Dynamic Group Model ([#896](https://github.com/nautobot/nautobot/issues/896))

A new data model for representing [dynamic groups](../models/extras/dynamicgroup.md) of objects has been implemented. Dynamic groups can be used to organize objects together by matching criteria such as their site location or region, for example, and are dynamically updated whenever new matching objects are created, or existing objects are updated.

For the initial release only dynamic groups of `Device` and `VirtualMachine` objects are supported.

#### Extend FilterSets and Filter Forms via Plugins ([#1470](https://github.com/nautobot/nautobot/issues/1470))

Plugins can now extend existing FilterSets and Filter Forms. This allows plugins to provide alternative lookup methods or custom queries in the UI or API that may not already exist today.

You can refer to the [plugin development guide](../plugins/development.md#extending-filters) on how to create new filters and fields.

#### GraphQL Pagination ([#1109](https://github.com/nautobot/nautobot/issues/1109))

GraphQL list queries can now be paginated by specifying the filter parameters `limit` and `offset`. Refer to the [GraphQL user guide](../user-guides/graphql.md#filtering-queries) for examples.

#### Job Database Model ([#1001](https://github.com/nautobot/nautobot/issues/1001))

Installed Jobs are now represented by a data model in the Nautobot database. This allows for new functionality including:

- The Jobs listing UI view can now be filtered and searched like most other Nautobot table/list views.
- Job attributes (name, description, approval requirements, etc.) can now be managed via the Nautobot UI by an administrator or user with appropriate permissions to customize or override the attributes defined in the Job source code.
- Jobs can now be identified by a `slug` as well as by their `class_path`.
- A new set of REST API endpoints have been added to `/api/extras/jobs/<uuid>/`. The existing `/api/extras/jobs/<class_path>/` REST API endpoints continue to work but should be considered as deprecated.
    - A new version of the REST API `/api/extras/jobs/` list endpoint has been implemented as well, but by default this endpoint continues to demonstrate the pre-1.3 behavior unless the REST API client explicitly requests API `version=1.3`. See the section on REST API versioning, below, for more details.
- As a minor security measure, newly installed Jobs default to `enabled = False`, preventing them from being run until an administrator or user with appropriate permissions updates them to be enabled for running.

!!! note
    As a convenience measure, when initially upgrading to Nautobot 1.3.x, any existing Jobs that have been run or scheduled previously (i.e., have at least one associated JobResult and/or ScheduledJob record) will instead default to `enabled = True` so that they may continue to be run without requiring changes.

For more details please refer to the [Jobs feature documentation](../additional-features/jobs.md) as well as the [Job data model documentation](../models/extras/job.md).

#### Jobs With Sensitive Parameters ([#2091](https://github.com/nautobot/nautobot/issues/2091))

Jobs model now includes a [`has_sensitive_variables`](../additional-features/jobs.md#has_sensitive_variables) field which by default prevents the job's input parameters from being saved to the database. Review whether each job's input parameters include sensitive data such as passwords or other user credentials before setting this to `False` for any given job.

#### JSON Type for Custom Fields ([#897](https://github.com/nautobot/nautobot/issues/897))

Custom fields can now have a type of "json". Fields of this type can be used to store arbitrary JSON data.

#### Natural Indexing for Common Lookups ([#1638](https://github.com/nautobot/nautobot/issues/1638))

Many fields have had indexing added to them as well as index togethers on `ObjectChange` fields. This should provide a noticeable performance improvement when filtering and doing lookups.

!!! note
    This is going to perform several migrations to add all of the indexes. On MySQL databases and tables with 1M+ records this can take a few minutes. Every environment is different but it should be expected for this upgrade to take some time.

#### Overlapping/Multiple NAT Support ([#630](https://github.com/nautobot/nautobot/issues/630))

IP addresses can now be associated with multiple outside NAT IP addresses. To do this, set more than one IP Address to have the same NAT inside IP address.

A new version of the REST API `/api/ipam/ip-addresses/*` endpoints have been implemented as well, but by default this endpoint continues to demonstrate the pre-1.3 behavior unless the REST API client explicitly requests API `version=1.3`. See the section on REST API versioning, below, for more details.

!!! note
    There are some guardrails on this feature to support backwards compatibility. If you consume the REST API without specifying the version header or query argument and start associating multiple IPs to have the same NAT inside IP address, an error will be reported, because the existing REST API schema returns `nat_outside` as a single object, where as 1.3 and beyond will return this as a list.

#### Provider Network Model ([#724](https://github.com/nautobot/nautobot/issues/724))

A [data model](../models/circuits/providernetwork.md) has been added to support representing the termination of a circuit to an external provider's network.

#### Python 3.10 Support ([#1255](https://github.com/nautobot/nautobot/pull/1255))

Python 3.10 is officially supported by Nautobot now, and we are building and publishing Docker images with Python 3.10 now.

#### Regular Expression Support in API Filtering ([#1525](https://github.com/nautobot/nautobot/issues/1525))

[New lookup expressions for using regular expressions](../rest-api/filtering.md#string-fields) to filter objects by string (char) fields in the API have been added to all core filters.

The expressions `re` (regex), `nre` (negated regex), `ire` (case-insensitive regex), and `nire` (negated case-insensitive regex) lookup expressions are now dynamically-generated for filter fields inherited by subclasses of `nautobot.utilities.filters.BaseFilterSet`.

#### Remove Stale Scheduled Jobs ([#2091](https://github.com/nautobot/nautobot/issues/2091))

[remove_stale_scheduled_jobs](../administration/nautobot-server.md#remove_stale_scheduled_jobs) management command has been added to delete non-recurring scheduled jobs that were scheduled to run more than a specified days ago.

#### REST API Token Provisioning ([#1374](https://github.com/nautobot/nautobot/issues/1374))

Nautobot now has an `/api/users/tokens/` REST API endpoint where a user can provision a new REST API token. This allows a user to gain REST API access without needing to first create a token via the web UI.

```bash
curl -X POST \
-H "Accept: application/json; indent=4" \
-u "hankhill:I<3C3H8" \
https://nautobot/api/users/tokens/
```

This endpoint specifically supports Basic Authentication in addition to the other REST API authentication methods.

#### REST API Versioning ([#1465](https://github.com/nautobot/nautobot/issues/1465))

Nautobot's REST API now supports multiple versions, which may be requested by modifying the HTTP Accept header on any requests sent by a REST API client. Details are in the [REST API documentation](../rest-api/overview.md#versioning), but in brief:

- The REST API endpoints that are versioned in the 1.3.0 release are
    - `/api/extras/jobs/` listing endpoint
    - `/api/extras/tags/` create/put/patch endpoints
    - all `/api/ipam/ip-addresses/` endpoints
- All other REST API endpoints are currently non-versioned. However, over time more versioned REST APIs will be developed, so this is important to understand for all REST API consumers.
- If a REST API client does not request a specific REST API version (in other words, requests `Accept: application/json` rather than `Accept: application/json; version=1.3`) the API behavior will be compatible with Nautobot 1.2, at a minimum for the remainder of the Nautobot 1.x release cycle.
- The API behavior may change to a newer default version in a Nautobot major release (such as 2.0).
- To request an updated (non-backwards-compatible) API endpoint, an API version must be requested corresponding at a minimum to the Nautobot `major.minor` version where the updated API endpoint was introduced (so to interact with the updated REST API endpoints mentioned above, `Accept: application/json; version=1.3`).

!!! tip
    As a best practice, when developing a Nautobot REST API integration, your client should _always_ request the current API version it is being developed against, rather than relying on the default API behavior (which may change with a new Nautobot major release, as noted, and which also may not include the latest and greatest API endpoints already available but not yet made default in the current release).

#### Webhook Pre/Post-change Data Added to Request Body ([#330](https://github.com/nautobot/nautobot/issues/330))

Webhooks now provide a snapshot of data before and after a change, as well as the differences between the old and new data. See the default request body section in the [webhook docs](../models/extras/webhook.md#default-request-body).

### Changed

#### Docker Images Now Default to Python 3.7 ([#1252](https://github.com/nautobot/nautobot/pull/1252))

As Python 3.6 has reached end-of-life, the default Docker images published for this release (i.e. `1.3.0`, `stable`, `latest`) have been updated to use Python 3.7 instead.

#### Job Approval Now Controlled By `extras.approve_job` Permission ([#1490](https://github.com/nautobot/nautobot/pull/1490))

Similar to the existing `extras.run_job` permission, a new `extras.approve_job` permission is now enforced by the UI and the REST API when approving scheduled jobs. Only users with this permission can approve or deny approval requests; additionally such users also now require the `extras.view_scheduledjob`, `extras.change_scheduledjob`, and `extras.delete_scheduledjob` permissions as well.

#### OpenAPI 3.0 REST API documentation ([#595](https://github.com/nautobot/nautobot/issues/595))

The online REST API Swagger documentation (`/api/docs/`) has been updated from OpenAPI 2.0 format to OpenAPI 3.0 format and now supports Nautobot's [REST API versioning](#rest-api-versioning-1465) as described above. Try `/api/docs/?api_version=1.3` as an example.

#### Tag restriction by content-type ([#872](https://github.com/nautobot/nautobot/issues/872))

When created, a `Tag` can be associated to one or more model content-types using a many-to-many relationship. The tag will then apply only to models belonging to those associated content-types.

For users migrating from an earlier Nautobot release, any existing tags will default to being enabled for all content-types for compatibility purposes. Individual tags may subsequently edited to remove any content-types that they do not need to apply to.

Note that a Tag created programmatically via the ORM without assigning any `content_types` will not be applicable to any model until content-types are assigned to it.

#### Update Jinja2 to 3.x ([#1474](https://github.com/nautobot/nautobot/pull/1474))

We've updated the Jinja2 dependency from version 2.11 to version 3.0.3. This may affect the syntax of any `nautobot.extras.models.ComputedField` objects in your database... Specifically, the `template` attribute, which is parsed as a Jinja2 template. Please refer to [Jinja2 3.0.x's release notes](https://jinja.palletsprojects.com/en/3.0.x/changes/) to check if any changes might be required in your computed fields' templates.

#### Virtual Chassis Master Device Interfaces List

The device column will now show on a device's interfaces list if this device is the master in a virtual chassis. And will conversely not appear if the device is not a master on a virtual chassis.

It is no longer possible to connect an interface to itself in the cable connect form.

### Removed

#### Python 3.6 No Longer Supported ([#1268](https://github.com/nautobot/nautobot/issues/1268))

As Python 3.6 has reached end-of-life, and many of Nautobot's dependencies have already dropped support for Python 3.6 as a consequence, Nautobot 1.3 and later do not support installation under Python 3.6.

## v1.3.10 (2022-08-08)

### Added

- [#1226](https://github.com/nautobot/nautobot/issues/1226) - Added custom job intervals package management.
- [#2073](https://github.com/nautobot/nautobot/pull/2073) - Added `--local` option to `nautobot-server runjob` command.
- [#2080](https://github.com/nautobot/nautobot/pull/2080) - Added `--data` parameter to `nautobot-server runjob` command.
- [#2091](https://github.com/nautobot/nautobot/issues/2091) - Added `remove_stale_scheduled_jobs` management command which removes all stale scheduled jobs and also added `has_sensitive_variables` field to Job model which prevents the job's input parameters from being saved to the database.
- [#2143](https://github.com/nautobot/nautobot/pull/2143) - Scheduled Job detail view now includes details of any custom interval.

### Changed

- [#2025](https://github.com/nautobot/nautobot/pull/2025) - Tweak Renovate config for automated package management.
- [#2114](https://github.com/nautobot/nautobot/issues/2114) - Home page now redirects to the login page when `HIDE_RESTRICTED_UI` is enabled and user is not authenticated.
- [#2115](https://github.com/nautobot/nautobot/pull/2115) - Patch updates to `mkdocs`, `svgwrite`.

### Fixed

- [#1739](https://github.com/nautobot/nautobot/issues/1739) - Fixed paginator not enforcing max_page_size setting in web ui views.
- [#2060](https://github.com/nautobot/nautobot/issues/2060) - Fixed relationship peer_id filter non-existent error on relationship association page.
- [#2095](https://github.com/nautobot/nautobot/issues/2095) - Fixed health check failing with Redis Sentinel, TLS configuration.
- [#2119](https://github.com/nautobot/nautobot/pull/2119) - Fixed flaky integration test for cable connection UI.

### Security

!!! important
    With introducing the `has_sensitive_variables` flag on Job classes and model (see: [#2091](https://github.com/nautobot/nautobot/issues/2091)), jobs can be prevented from storing their inputs in the database. Due to the nature of queuing or scheduling jobs, the desired inputs must be stored for future use.

    New safe-default behavior will only permit jobs to be executed immediately, as `has_sensitive_variables` defaults to `True`. This value can be overridden by the Job class itself or the Job model edit page. Values entered for jobs executing immediately go straight to the Celery message bus and are cleaned up on completion of execution.

    Scheduling jobs or requiring approval necessitates those values to be stored in the database until they have been sent to the Celery message bus for execution.

    During installation of `v1.3.10`, a migration is applied to set the `has_sensitive_variables` value to `True` to all existing Jobs. However to maintain backwards-compatibility, past scheduled jobs are permitted to keep their schedule. New schedules cannot be made until an administrator has overridden the `has_sensitive_variables` for the desired Job.

    A new management command exists (`remove_stale_scheduled_jobs`) which will aid in cleaning up schedules to past jobs which may still have sensitive data stored in the database. This command is not exhaustive nor intended to clean up sensitive values stored in the database. You should review the `extras_scheduledjob` table for any further cleanup.

    **Note:** Leveraging the Secrets and Secret Groups features in Jobs does not need to be considered a sensitive variable. Secrets are retrieved by reference at run time, which means no secret value is stored directly in the database.

## v1.3.9 (2022-07-25)

### Added

- [#860](https://github.com/nautobot/nautobot/issues/860) - Added documentation that adding device component to device type does not modify existing device instances
- [#1595](https://github.com/nautobot/nautobot/issues/1595) - Add ability to specify uWSGI buffer size via environment variable.
- [#1757](https://github.com/nautobot/nautobot/issues/1757) - Added nullable face, position to Device bulk edit form to provided desired behavior to bulk assigning to a new rack.

### Changed

- [#386](https://github.com/nautobot/nautobot/issues/386) - Clarified messaging in API for rack position occupied.
- [#1356](https://github.com/nautobot/nautobot/issues/1356) - Virtual chassis master device interface list is less confusing.
- [#2045](https://github.com/nautobot/nautobot/pull/2045) - Clarified Job authoring around proper class inheritance.

### Fixed

- [#1035](https://github.com/nautobot/nautobot/issues/1035) - Fix assertion raised if SLAAC Status is missing when creating `IPAddress` objects
- [#1694](https://github.com/nautobot/nautobot/issues/1694) - Fixed CablePath not found error when disconnects/delete action performed on a cable
- [#1795](https://github.com/nautobot/nautobot/issues/1795) - Corrected relationship source/destination filter help text from queryset Filter to filterset Filter and updated documentations.
- [#1839](https://github.com/nautobot/nautobot/issues/1795) - Fixed staff users with auth > group permissions unable to view groups in admin UI.
- [#1937](https://github.com/nautobot/nautobot/issues/1937) - Solved `_custom_field_data` do not fully delete when using CustomFieldBulkDeleteView.
- [#1947](https://github.com/nautobot/nautobot/issues/1947) - Fixed unbound local error by initializing template variable before conditional logic statements.
- [#2036](https://github.com/nautobot/nautobot/pull/2036) - Fixed outdated UI navigation references in documentation.
- [#2039](https://github.com/nautobot/nautobot/issues/2039) - Fixed IntegerVar with default set to 0 on Job evaluating to False.
- [#2057](https://github.com/nautobot/nautobot/issues/2057) - Fixed RIR changelog route being in VRF name prefix.
- [#2077](https://github.com/nautobot/nautobot/issues/2077) - Fixed an error when viewing object detail pages after uninstalling a plugin but still having RelationshipAssociations involving the plugin's models.
- [#2081](https://github.com/nautobot/nautobot/issues/2081) - Fixed error raised if status connected not found when creating a cable

## v1.3.8 (2022-07-11)

### Added

- [#1464](https://github.com/nautobot/nautobot/issues/1464) - Added "Continue with SSO" link on login page.

### Changed

- [#1407](https://github.com/nautobot/nautobot/issues/1407) - Changed custom field export column headings to prefix with `cf_`.
- [#1603](https://github.com/nautobot/nautobot/issues/1603) - Changed GraphQL schema generation to call time for GraphQL API.
- [#1977](https://github.com/nautobot/nautobot/pull/1977) - Updated Renovate config to batch updates (additional PRs included to further refine config).
- [#2020](https://github.com/nautobot/nautobot/pull/2020) - Updated `celery >= 5.2.7`, `django-jinja >= 2.10.2`, and `mysqlclient >= 2.1.1` versions in lock file (patch updates).

### Fixed

- [#1838](https://github.com/nautobot/nautobot/issues/1838) - Fixed job result to show latest not oldest.
- [#1874](https://github.com/nautobot/nautobot/issues/1874) - Fixed Git repo sync issue with Sentinel with deprecated rq_count check.

### Security

!!! important
    CVE in Django versions `>= 3.2, < 3.2.14`. This update upgrades Django to `3.2.14`.

- [#2004](https://github.com/nautobot/nautobot/pull/2004) - Bump Django from 3.2.13 to 3.2.14 for for [CVE-2022-34265](https://github.com/advisories/GHSA-p64x-8rxx-wf6q).

## v1.3.7 (2022-06-27)

### Added

- [#1896](https://github.com/nautobot/nautobot/pull/1856) - Added Renovate Bot configuration, targeting `next`.
- [#1900](https://github.com/nautobot/nautobot/issues/1900) - Added ability to filter Git repository table based on provided contents.

### Changed

- [#1645](https://github.com/nautobot/nautobot/issues/1645) - Hide search bar for unauthenticated users if `HIDE_RESTRICTED_UI` is True
- [#1946](https://github.com/nautobot/nautobot/pull/1946) - Increase character limit on `FileAttachment.mimetype` to 255 to allow for all mime types to be used.
- [#1948](https://github.com/nautobot/nautobot/issues/1948) - Switched Renovate Bot configuration to bump lock-file only on patch releases instead of bumping in `pyproject.toml`.

### Fixed

- [#1677](https://github.com/nautobot/nautobot/issues/1677) - Fixed default values of custom fields on device components (such as Interface) not being applied upon Device creation.
- [#1769](https://github.com/nautobot/nautobot/issues/1769) - Resolve missing menu 'General / Installed Plugins' in navbar if `HIDE_RESTRICTED_UI` is activated
- [#1836](https://github.com/nautobot/nautobot/issues/1836) - Fixed incorrect pre-population of custom field filters in table views.
- [#1870](https://github.com/nautobot/nautobot/issues/1870) - Fixed cable `_abs_length` validation error.
- [#1941](https://github.com/nautobot/nautobot/pull/1941) - Fixes uWSGI config example, development environment links in Docker section of docs.

## v1.3.6 (2022-06-13)

### Changed

- [#207](https://github.com/nautobot/nautobot/issues/207) - Update permissions documentation to add assigning permissions section.
- [#1763](https://github.com/nautobot/nautobot/issues/1763) - Job testing documentation updated to include details around enabling jobs. Job logs database added to `TransactionTestCase`.
- [#1829](https://github.com/nautobot/nautobot/pull/1829) - Change Docker build GitHub Action to cache with matrix awareness.
- [#1856](https://github.com/nautobot/nautobot/pull/1856) - Updated links to Slack community.

### Fixed

- [#1409](https://github.com/nautobot/nautobot/issues/1409) - Fixed page title on device status (NAPALM) page template.
- [#1524](https://github.com/nautobot/nautobot/issues/1524) - Fixed valid "None" option removed from search field upon display.
- [#1649](https://github.com/nautobot/nautobot/issues/1649) - Changed the incorrect view permission (`circuits.view_vrf` to `ipam.view_vrf`)
- [#1750](https://github.com/nautobot/nautobot/issues/1750) - Fixed incorrect display of boolean value in Virtual Chassis display.
- [#1759](https://github.com/nautobot/nautobot/issues/1759) - Fixed TypeError on webhook REST API PATCH.
- [#1787](https://github.com/nautobot/nautobot/issues/1787) - Fix scheduled jobs failing when scheduled from REST API.
- [#1841](https://github.com/nautobot/nautobot/issues/1841) - Fixed incorrect display of boolean values in Git Repository view.
- [#1848](https://github.com/nautobot/nautobot/pull/1848) - Fix Poetry cache issue in CI causing version tests to fail in `next`.
- [#1850](https://github.com/nautobot/nautobot/pull/1850) - Added `{{block.super}}` to negate the override from the js block in rack.html. This change fixed the issue of unable to navigate away from rack changelog tab.
- [#1868](https://github.com/nautobot/nautobot/pull/1868) - Updated link to advanced Docker compose use in getting started guide.

## v1.3.5 (2022-05-30)

### Added

- [#1606](https://github.com/nautobot/nautobot/issues/1606) - Added best practices for working with FilterSet classes to developer documentation.
- [#1796](https://github.com/nautobot/nautobot/issues/1796) - Added documentation for using Git Repositories behind/via proxies.
- [#1811](https://github.com/nautobot/nautobot/pull/1811) - Added developer Docker container for running mkdocs instead of locally.

### Changed

- [#1818](https://github.com/nautobot/nautobot/pull/1818) - Changed README.md to link to correct build status workflows.

### Fixed

- [#895](https://github.com/nautobot/nautobot/issues/895) - Fixed validation when creating `Interface` and `VMInterface` objects via the REST API while specifying `untagged_vlan` without `mode` also set in the payload. A 400 error will now be raised as expected.
- [#1289](https://github.com/nautobot/nautobot/issues/1289) - Fixed issue where job result live pagination would reset to page 1 on refresh. The currently selected page will now persist until the job run completes.
- [#1290](https://github.com/nautobot/nautobot/issues/1290) - Fix NAPALM enable password argument for devices using the eos NAPALM driver.
- [#1427](https://github.com/nautobot/nautobot/issues/1427) - Fix NoReverseMatch exception when related views for action_buttons don't exist.
- [#1428](https://github.com/nautobot/nautobot/issues/1428) - Fix IPAM prefix utilization sometimes showing greater than 100 percent for IPv4 prefixes.
- [#1604](https://github.com/nautobot/nautobot/issues/1604) - Fix missing filter restriction enforcement on relationship association.
- [#1771](https://github.com/nautobot/nautobot/issues/1771) - Fix exception raised for RelationshipAssociation when updating source.
- [#1772](https://github.com/nautobot/nautobot/issues/1772) - Fix RelationshipAssociationSerializer not triggering model clean method.
- [#1784](https://github.com/nautobot/nautobot/issues/1784) - Fix `nautobot-server dumpdata` not working due to `django_rq` update. Updated documentation.
- [#1805](https://github.com/nautobot/nautobot/pull/1805) - Fix git pre-commit hook incompatibility with dash shell and add warning on skipped tests.

### Security

!!! attention
    `PyJWT` - Nautobot does not directly depend on `PyJWT` so your upgrading Nautobot via `pip` or other package management tools may not pick up the patched version (we are not pinning this dependency). However some tools support an "eager" upgrade policy as an option. For example, `pip install --upgrade --upgrade-strategy eager nautobot` will upgrade Nautobot and all it's dependencies to their latest compatible version. This may not work for all use cases so it may be safer to update Nautobot then perform `pip install --upgrade PyJWT`.

    Docker containers published with this build will have PyJWT upgraded.

- [#1808](https://github.com/nautobot/nautobot/pull/1808) - Bump PyJWT from 2.3.0 to 2.4.0

## v1.3.4 (2022-05-16)

### Added

- [#1766](https://github.com/nautobot/nautobot/pull/1766) - Added configuration for downloaded filename branding.
- [#1752](https://github.com/nautobot/nautobot/pull/1752) - Added a new `SearchFilter` that is now used on all core filtersets to provide the `q=` search parameter for basic searching in list view of objects.

### Changed

- [#1744](https://github.com/nautobot/nautobot/issues/1744) - Updated REST API token provisioning docs to include added in version.
- [#1751](https://github.com/nautobot/nautobot/pull/1751) - Updated secrets documentation advisory notes.

### Fixed

- [#1263](https://github.com/nautobot/nautobot/issues/1263) - Rack device image toggle added back to detail UI.
- [#1449](https://github.com/nautobot/nautobot/issues/1449) - Fixed a performance bug in `/api/dcim/devices/` and `/api/virtualization/virtual-machines/` relating to configuration contexts.
- [#1652](https://github.com/nautobot/nautobot/issues/1652) - Unicode now renders correctly on uses of json.dumps and yaml.dump throughout the code base.
- [#1712](https://github.com/nautobot/nautobot/issues/1712) - Fixed circuit termination detail view getting 500 response when it's a provider network.
- [#1755](https://github.com/nautobot/nautobot/issues/1755) - Fixed "Select All" helper widget from taking full UI height.
- [#1761](https://github.com/nautobot/nautobot/pull/1761) - Fixed typo in upgrading documentation.

### Security

- [#1715](https://github.com/nautobot/nautobot/issues/1715) - Add [`SANITIZER_PATTERNS` optional setting](../configuration/optional-settings.md#sanitizer_patterns) and `nautobot.utilities.logging.sanitize` function and use it for redaction of Job log entries.

## v1.3.3 (2022-05-02)

### Added

- [#1481](https://github.com/nautobot/nautobot/issues/1481) - Pre-Generate Docs, Add Support for Plugin-Provided Docs
- [#1617](https://github.com/nautobot/nautobot/pull/1617) - Added `run_job_for_testing` helper method for testing Jobs in plugins, internally.

### Changed

- [#1481](https://github.com/nautobot/nautobot/issues/1481) - Docs link in footer now opens link to bundled documentation instead of Read the Docs.
- [#1680](https://github.com/nautobot/nautobot/pull/1680) - Bump netutils dependency to 1.1.0.
- [#1700](https://github.com/nautobot/nautobot/pull/1700) - Revert vendoring `drf-spectacular`.

### Fixed

- [#473](https://github.com/nautobot/nautobot/issues/473) - Fix `get_return_url` for plugin reverse URLs.
- [#1430](https://github.com/nautobot/nautobot/issues/1430) - Fix not being able to print Job results, related IPs.
- [#1503](https://github.com/nautobot/nautobot/issues/1503) - SSO users can no longer interact with or see the change password form.
- [#1515](https://github.com/nautobot/nautobot/issues/1515) - Further fixes for slow/unresponsive jobs results display.
- [#1538](https://github.com/nautobot/nautobot/issues/1538) - Fix incorrect page title alignment on the "Device Type Import" page.
- [#1678](https://github.com/nautobot/nautobot/issues/1678) - Custom fields with 'json' type no longer raise TypeError when filtering on an object list URL
- [#1679](https://github.com/nautobot/nautobot/issues/1679) - Fix a data migration error when upgrading to 1.3.x with pre-existing JobResults that reference Jobs with names exceeding 100 characters in length.
- [#1685](https://github.com/nautobot/nautobot/issues/1685) - Fix Hadolint issue of `docker/Dockerfile`.
- [#1692](https://github.com/nautobot/nautobot/issues/1692) - Fix duplicate tags in search list results.
- [#1697](https://github.com/nautobot/nautobot/pull/1697) - Fix docs incorrectly stating Celerey Redis URLs defaulting from CACHES.
- [#1701](https://github.com/nautobot/nautobot/pull/1701) - Fix static file serving of drf-spectacular-sidecar assets when using alternative `STATICFILES_STORAGE` settings.
- [#1705](https://github.com/nautobot/nautobot/pull/1705) - Fix `NestedVMInterfaceSerializer` referencing the wrong model.

## v1.3.2 (2022-04-22)

### Added

- [#1219](https://github.com/nautobot/nautobot/pull/1219) - Add ARM64 support (alpha).
- [#1426](https://github.com/nautobot/nautobot/issues/1426) - Added plugin development documentation around using ObjectListView.
- [#1674](https://github.com/nautobot/nautobot/pull/1674) - Added flag in Dockerfile, tasks.py to enable Poetry install parallelization.

### Changed

- [#1667](https://github.com/nautobot/nautobot/issues/1667) - Updated README.md screenshots.
- [#1670](https://github.com/nautobot/nautobot/pull/1670) - Configure drf-spectacular schema to more closely match drf-yasg (related to: [nautobot-ansible#135](https://github.com/nautobot/nautobot-ansible/pull/135)).

### Fixed

- [#1659](https://github.com/nautobot/nautobot/pull/1659) - Added some missing test/lint commands to the [development getting-started](../development/getting-started.md) documentation, and made `invoke cli` parameters match `invoke start/stop`.
- [#1666](https://github.com/nautobot/nautobot/pull/1666) - Fixed errors in documentation with incomplete import statements.
- [#1682](https://github.com/nautobot/nautobot/issues/1682) - Fixed Nautobot health checks failing if Redis Sentinel password is required.

### Security

!!! important
    Critical CVEs in Django versions `>= 3.2, < 3.2.13`. This update upgrades Django to `3.2.13`.

- [#1686](https://github.com/nautobot/nautobot/pull/1686) - Implemented fixes for [CVE-2022-28347](https://github.com/advisories/GHSA-w24h-v9qh-8gxj) and [CVE-2022-28346](https://github.com/advisories/GHSA-2gwj-7jmv-h26r) to require Django >=3.2.13.

## v1.3.1 (2022-04-19)

### Changed

- [#1647](https://github.com/nautobot/nautobot/pull/1647) - Changed class inheritance of JobViewSet to be simpler and more self-consistent.

### Fixed

- [#1278](https://github.com/nautobot/nautobot/issues/1278) - Fixed several different errors that could be raised when working with RelationshipAssociations.
- [#1662](https://github.com/nautobot/nautobot/issues/1662) - Fixed nat_outside prefetch on Device API view, and displaying multiple nat_outside entries on VM detail view.

## v1.3.0 (2022-04-18)

### Added

- [#630](https://github.com/nautobot/nautobot/issues/630) - Added support for multiple NAT outside IP addresses.
- [#872](https://github.com/nautobot/nautobot/issues/872) - Added ability to scope tags to content types.
- [#896](https://github.com/nautobot/nautobot/issues/896) - Implemented support for Dynamic Groups objects.
- [#897](https://github.com/nautobot/nautobot/issues/897) - Added JSON type for custom fields.
- [#1374](https://github.com/nautobot/nautobot/issues/1374) - Added REST API Token Provisioning. (Port of [NetBox #6592](https://github.com/netbox-community/netbox/pull/6592) and subsequent fixes)
- [#1385](https://github.com/nautobot/nautobot/issues/1385) - Added MarkdownLint validation and enforcement to CI.
- [#1465](https://github.com/nautobot/nautobot/issues/1465) - Implemented REST API versioning.
- [#1525](https://github.com/nautobot/nautobot/issues/1525) - Implemented support for regex lookup expressions for `BaseFilterSet` filter fields in the API.
- [#1638](https://github.com/nautobot/nautobot/issues/1638) - Implemented numerous indexes on models natural lookup fields as well as some index togethers for `ObjectChange`.

### Changed

- [#595](https://github.com/nautobot/nautobot/issues/595) - Migrated from `drf-yasg` (OpenAPI 2.0) to `drf-spectacular` (OpenAPI 3.0) for REST API interactive Swagger documentation.
- [#792](https://github.com/nautobot/nautobot/issues/792) - Poetry-installed dependencies are now identical between `dev` and `final` images.
- [#814](https://github.com/nautobot/nautobot/issues/814) - Extended documentation for configuring Celery for use Redis Sentinel clustering.
- [#1225](https://github.com/nautobot/nautobot/issues/1225) - Relaxed uniqueness constraint on Webhook creation, allowing multiple webhooks to send to the same target address so long as their content-type(s) and action(s) do not overlap.
- [#1417](https://github.com/nautobot/nautobot/issues/1417) - CI scope improvements for streamlined performance.
- [#1478](https://github.com/nautobot/nautobot/issues/1478) - ScheduledJob REST API endpoints now enforce `extras.approve_job` permissions as appropriate.
- [#1479](https://github.com/nautobot/nautobot/issues/1479) - Updated Jobs documentation regarding the concrete Job database model.
- [#1502](https://github.com/nautobot/nautobot/issues/1502) Finalized Dynamic Groups implementation for 1.3 release (including documentation and integration tests).
- [#1521](https://github.com/nautobot/nautobot/pull/1521) - Consolidated Job REST API endpoints, taking advantage of REST API versioning.
- [#1556](https://github.com/nautobot/nautobot/issues/1556) - Cleaned up typos and formatting issues across docs, few code spots.

### Fixed

- [#794](https://github.com/nautobot/nautobot/issues/794) - Fixed health check issue when using Redis Sentinel for caching with Cacheops. The Redis health check backend is now aware of Redis Sentinel.
- [#1311](https://github.com/nautobot/nautobot/issues/1311) - Fixed a where it was not possible to set the rack height to `0` when performing a bulk edit of device types.
- [#1476](https://github.com/nautobot/nautobot/issues/1476) - Fixed a bug wherein a Job run via the REST API with a missing `schedule` would allow `approval_required` to be bypassed.
- [#1504](https://github.com/nautobot/nautobot/issues/1504) - Fixed an error that could be encountered when migrating from Nautobot 1.1 or earlier with JobResults with very long log entries.
- [#1515](https://github.com/nautobot/nautobot/issues/1515) - Fix Job Result rendering performance issue causing Bad Gateway errors.
- [#1516](https://github.com/nautobot/nautobot/issues/1516) - Fixed MySQL unit tests running in Docker environment and revised recommended MySQL encoding settings
- [#1562](https://github.com/nautobot/nautobot/issues/1562) - Fixed JobResult filter form UI pointing to the wrong endpoint.
- [#1563](https://github.com/nautobot/nautobot/issues/1563) - Fixed UI crash when trying to execute Jobs provided by disabled plugins. A friendly error message will now be displayed.
- [#1582](https://github.com/nautobot/nautobot/issues/1582) - Fixed a timing issue with editing a record while its custom field(s) are in the process of being cleaned up by a background task.
- [#1632](https://github.com/nautobot/nautobot/pull/1632) - Fixed issue accessing request attributes when request may be None.
- [#1637](https://github.com/nautobot/nautobot/pull/1637) - Fixed warnings logged during REST API schema generation.

## v1.3.0b1 (2022-03-11)

### Added

- [#5](https://github.com/nautobot/nautobot/issues/5) - Added the option to perform a "dry run" of Git repository syncing.
- [#330](https://github.com/nautobot/nautobot/issues/330) - Added pre-/post-change data to WebHooks leveraging snapshots.
- [#498](https://github.com/nautobot/nautobot/issues/498) - Added custom-validator support to the RelationshipAssociation model.
- [#724](https://github.com/nautobot/nautobot/issues/724) - Added Provider Network data model. (Partially based on [NetBox #5986](https://github.com/netbox-community/netbox/issues/5986).)
- [#795](https://github.com/nautobot/nautobot/issues/795) - Added ability to filter objects missing custom field values by using `null`.
- [#803](https://github.com/nautobot/nautobot/issues/803) - Added a `render_boolean` template filter, which renders computed boolean values as HTML in a consistent manner.
- [#863](https://github.com/nautobot/nautobot/issues/863) - Added the ability to hide a job in the UI by setting `hidden = True` in the Job's inner `Meta` class.
- [#881](https://github.com/nautobot/nautobot/issues/881) - Improved the UX of the main Jobs list by adding accordion style interface that can collapse/expand jobs provided by each module.
- [#885](https://github.com/nautobot/nautobot/issues/885) - Added the ability to define a `soft_time_limit` and `time_limit` in seconds as attributes of a Job's `Meta`.
- [#894](https://github.com/nautobot/nautobot/issues/894) - Added the ability to view computed fields in an object list.
- [#898](https://github.com/nautobot/nautobot/issues/898) - Added support for moving a CustomField, Relationship or ComputedField from the main tab of an object's detail page in the UI to the "Advanced" tab.
- [#1001](https://github.com/nautobot/nautobot/issues/1001) - Added Job database model and associated functionality.
- [#1109](https://github.com/nautobot/nautobot/issues/1109) - Added pagination support for GraphQL list queries.
- [#1255](https://github.com/nautobot/nautobot/pull/1255) - Added Python 3.10 support.
- [#1350](https://github.com/nautobot/nautobot/issues/1350) - Added missing methods on Circuit Termination detail view.
- [#1411](https://github.com/nautobot/nautobot/pull/1411) - Added concrete Job database model; added database signals to populate Job records in the database; added detail, edit, and delete views for Job records.
- [#1457](https://github.com/nautobot/nautobot/pull/1457) - Added new Jobs REST API, added control logic to use JobModel rather than JobClass where appropriate; improved permissions enforcement for Jobs.
- [#1470](https://github.com/nautobot/nautobot/issues/1470) - Added plugin framework for extending FilterSets and Filter Forms.

### Changed

- [#368](https://github.com/nautobot/nautobot/issues/368) - Added `nautobot.extras.forms.NautobotModelForm` and `nautobot.extras.filters.NautobotFilterSet` base classes. All form classes which inherited from all three of (`BootstrapMixin`, `CustomFieldModelForm`, and `RelationshipModelForm`) now inherit from `NautobotModelForm` as their base class. All filterset classes which inherited from all three of (`BaseFilterSet`, `CreatedUpdatedFilterSet`, and `CustomFieldModelFilterSet`) now inherit from `NautobotFilterSet` as their base class.
- [#443](https://github.com/nautobot/nautobot/issues/443) - The provided "Dummy Plugin" has been renamed to "Example Plugin".
- [#591](https://github.com/nautobot/nautobot/issues/591) - All uses of `type()` are now refactored to use `isinstance()` where applicable.
- [#880](https://github.com/nautobot/nautobot/issues/880) - Jobs menu items now form their own top-level menu instead of a sub-section under the Extensibility menu.
- [#909](https://github.com/nautobot/nautobot/issues/909) - Device, InventoryItem, and Rack serial numbers can now be up to 255 characters in length.
- [#916](https://github.com/nautobot/nautobot/issues/916) - A `Job.Meta.description` can now contain markdown-formatted multi-line text.
- [#1107](https://github.com/nautobot/nautobot/issues/1107) - Circuit Provider account numbers can now be up to 100 characters in length.
- [#1252](https://github.com/nautobot/nautobot/pull/1252) - As Python 3.6 has reached end-of-life, the default Docker images published for this release (i.e. `1.3.0`, `stable`, `latest`) have been updated to use Python 3.7 instead.
- [#1277](https://github.com/nautobot/nautobot/issues/1277) - Updated Django dependency to 3.2.X LTS.
- [#1307](https://github.com/nautobot/nautobot/pull/1307) - Updated various Python package dependencies to their latest compatible versions.
- [#1314](https://github.com/nautobot/nautobot/pull/1314) - Updated various development-only Python package dependencies to their latest compatible versions.
- [#1321](https://github.com/nautobot/nautobot/pull/1321) - Updates to various browser package dependencies. This includes updating from Material Design Icons 5.x to 6.x, which has a potential impact on plugins: a [small number of icons have been removed or renamed](https://dev.materialdesignicons.com/upgrade#5.9.55-to-6.1.95) as a result of this change.
- [#1367](https://github.com/nautobot/nautobot/pull/1367) - Extracted Job-related models to submodule `nautobot.extras.models.jobs`; refined Job testing best practices.
- [#1391](https://github.com/nautobot/nautobot/issues/1391) - Updated Jinja2 dependency to 3.0.X.
- [#1435](https://github.com/nautobot/nautobot/issues/1435) - Update to Selenium 4.X.

### Fixed

- [#1440](https://github.com/nautobot/nautobot/issues/1440) - Handle models missing serializer methods, dependent from adding pre-/post-change data to WebHooks.

### Removed

- [#1268](https://github.com/nautobot/nautobot/issues/1268) - Drop Support for Python 3.6.
