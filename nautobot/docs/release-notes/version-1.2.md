<!-- markdownlint-disable MD024 -->
# Nautobot v1.2

This document describes all new features and changes in Nautobot 1.2.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Admin Configuration UI ([#370](https://github.com/nautobot/nautobot/issues/370))

The Nautobot Admin UI now includes a "Configuration" page that can be used to dynamically customize a number of [optional settings](../configuration/optional-settings.md#administratively-configurable-settings) as an alternative to editing `nautobot_config.py` and restarting the Nautobot processes.

If upgrading from a previous Nautobot version where these settings were defined in your `nautobot_config.py`, you must remove those definitions in order to use this feature, as explicit configuration in `nautobot_config.py` takes precedence over values configured in the Admin UI.

#### Common Base Template for Object Detail Views ([#479](https://github.com/nautobot/nautobot/issues/479), [#585](https://github.com/nautobot/nautobot/issues/585))

All "object detail" views (pages displaying details of a single Nautobot record) now inherit from a common base template, providing improved UI consistency, reducing the amount of boilerplate code needed to create a new detail view, and fixing a number of bugs in various views. Plugin developers are encouraged to make use of this new template (`generic/object_detail.html`) to take advantage of these improvements.

Views based on this template now include a new "Advanced" tab - currently this tab includes the UUID and slug (if any) of the object being viewed, but may be extended in the future to include additional information not relevant to the basic object detail view.

#### Custom Fields are now User Configurable ([#229](https://github.com/nautobot/nautobot/issues/229))

Creation and management of Custom Field definitions can now be performed by any user with appropriate permissions. (Previously, only admin users were able to manage Custom Fields.)

#### Custom Field Webhooks ([#519](https://github.com/nautobot/nautobot/issues/519))

Webhooks can now be triggered when creating/updating/deleting `CustomField` and `CustomFieldChoice` definition records.

#### Database Ready Signal ([#13](https://github.com/nautobot/nautobot/issues/13))

After running `nautobot-server migrate` or `nautobot-server post_upgrade`, Nautobot now emits a custom signal, `nautobot_database_ready`. This signal is designed for plugins to connect to in order to perform automatic database population (such as defining custom fields, relationships, webhooks, etc.) at install/upgrade time. For more details, refer to [the plugin development documentation](../plugins/development.md#populating-extensibility-features).

#### GraphQL Filters at All Levels ([#248](https://github.com/nautobot/nautobot/issues/248))

The GraphQL API now supports query filter parameters at any level of a query. For example:

```graphql
query {
  sites(name: "ams") {
    devices(role: "edge") {
      name
      interfaces(type: "virtual") {
        name
      }
    }
  }
}
```

#### GraphQL Query Optimizations ([#171](https://github.com/nautobot/nautobot/issues/171))

Complex GraphQL queries have been greatly optimized thanks to integration of
[`graphene-django-optimizer`](https://github.com/tfoxy/graphene-django-optimizer) into Nautobot!

In our internal testing and benchmarking the number of SQL queries generated per GraphQL query have been drastically reduced, resulting in much quicker response times and less strain on the database.

For in depth details on our benchmarks, please see the [comment thread on the issue](https://github.com/nautobot/nautobot/issues/171#issuecomment-907483759).

#### Installed Plugins List and Detail Views, Plugin Config and Home Views ([#935](https://github.com/nautobot/nautobot/pull/935))

The `Plugins` menu now includes an "Installed Plugins" menu item which provides a list view of information about all installed and enabled plugins, similar to a formerly administrator-only view.

Additionally, when viewing this list, each plugin can now be clicked on for a detail view, which provides an in-depth look at the capabilities of the plugin, including whether it makes use of each or all of the various Nautobot features available to be used by plugins.

Additionally, plugins now have the option of registering specific "home" and/or "configuration" views, which will be linked and accessible directly from the installed-plugins list and detail views.

Please refer to the [plugin development documentation](../plugins/development.md) for more details about this functionality.

#### IPAM custom lookups for filtering ([#982](https://github.com/nautobot/nautobot/issues/982))

Nautobot now again supports custom lookup filters on the `IPAddress`, `Prefix`, and `Aggregate` models, such as `address__net_contained`, `network__net_contains_or_equals`, etc. Refer to the [REST API filtering documentation](../rest-api/filtering.md#network-and-host-fields) for more specifics and examples.

#### Job Approval ([#125](https://github.com/nautobot/nautobot/issues/125))

Jobs can now be optionally defined as `approval_required = True`, in which case the Job will not be executed immediately upon submission, but will instead be placed into an approval queue; any user *other than the submitter* can approve or deny a queued Job, at which point it will then be executed as normal.

#### Job Scheduling ([#374](https://github.com/nautobot/nautobot/issues/374))

Jobs can now be scheduled for execution at a future date and time (such as during a planned maintenance window), and can also be scheduled for repeated execution on an hourly, daily, or weekly recurring cadence.

!!! note
    Execution of scheduled jobs is dependent on [Celery Beat](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html); enablement of this system service is a new requirement in Nautobot 1.2.

Please see the documentation on enabling the [Celery Beat scheduler service](../installation/services.md#celery-beat-scheduler) to get started!

#### Networking Template Filters ([#1082](https://github.com/nautobot/nautobot/issues/1082))

Template rendering with Django and/or Jinja2 now supports by default all filters provided by the [`netutils`](https://netutils.readthedocs.io/en/latest/index.html) library. These filters can be used in page templates, computed fields, custom links, export templates, etc. For details, please refer to the [filters](../additional-features/template-filters.md) documentation.

#### Organizational Branding ([#859](https://github.com/nautobot/nautobot/issues/859))

Organizations may provide custom branding assets to change the logo, icons, and footer URLs to help Nautobot fit within their environments and user communities. Please see the [configuration documenation](../configuration/optional-settings.md#BRANDING_FILEPATHS) for details on how to specify the location and usage of custom branding assets.

#### Plugin Banners ([#534](https://github.com/nautobot/nautobot/issues/534))

Each plugin is now able to optionally inject a custom banner into any of the Nautobot core views.

Please refer to the [plugin development documentation](../plugins/development.md) for more details about this functionality.

#### Same-Type and Symmetric Relationships ([#157](https://github.com/nautobot/nautobot/issues/157))

The [Relationships](../models/extras/relationship.md) feature has been extended in two ways:

1. Relationships between the same object type (e.g. device-to-device) are now permitted and supported.
2. For same-object-type relationships specifically, *symmetric* (peer-to-peer rather than source-to-destination) relationships are now an option.

For more details, refer to the [Relationships](../models/extras/relationship.md) documentation.

#### Secrets Integration ([#541](https://github.com/nautobot/nautobot/issues/541))

Nautobot can now read secret values (such as device or Git repository access credentials) on demand from a variety of external sources, including environment variables and text files, and extensible via plugins to support additional secrets providers such as Hashicorp Vault and AWS Secrets Manager. Both the [NAPALM device integration](../additional-features/napalm.md) and the [Git repository integration](../models/extras/gitrepository.md) can now make use of these secrets, and plugins and jobs can do so as well.

For more details, please refer to the [Secrets](../core-functionality/secrets.md) documentation.

#### Software-Defined Home Page ([#674](https://github.com/nautobot/nautobot/pull/674), [#716](https://github.com/nautobot/nautobot/pull/716))

Nautobot core applications and plugins can now both define panels, groups, and items to populate the Nautobot home page. The home page now dynamically reflows to accommodate available content. Plugin developers can add to existing panels or groups or define entirely new panels as needed. For more details, see [Populating the Home Page](../development/homepage.md).

### Changed

#### Admin Site Changes ([#900](https://github.com/nautobot/nautobot/pull/900))

The Admin sub-site within Nautobot (`/admin/` and its child pages) has been revamped in appearance and functionality. It has been re-skinned to resemble the rest of the Nautobot UI, and has been slimmed down to only include those models and features that are still exclusive to admin users, such as user/group/permission management.

#### JobLogEntry Data Model ([#1030](https://github.com/nautobot/nautobot/pull/1030))

Job log messages are now stored in a separate database table as a separate `JobLogEntry` data model, instead of being stored as JSON on the `JobResult` model/table. This provides faster and more robust rendering of `JobResult`-related views and lays groundwork for future enhancements of the Jobs feature.

!!! note
    If you are executing Jobs inside your tests, there are some changes you will need to make for your tests to support this feature correctly. Refer to the [Jobs documentation](../additional-features/jobs.md#testing-jobs) for details.

!!! note
    Because `JobLogEntry` records reference their associated `JobResult`, the pattern `job.job_result = JobResult()` (creating only an in-memory `JobResult` object, rather than a database entry) will no longer work. Instead you will need to create a proper JobResult database object `job.job_result = JobResult.objects.create(...)`.

#### Slug fields are now Optional in CSV import, REST API and ORM ([#493](https://github.com/nautobot/nautobot/issues/493))

All models that have `slug` fields now use `AutoSlugField` from the `django-extensions` package. This means that when creating a record via the REST API, CSV import, or direct ORM Python calls, the `slug` field is now fully optional; if unspecified, it will be automatically assigned a unique value, just as how a `slug` is auto-populated in the UI when creating a new record.

Just as with the UI, the `slug` can still always be explicitly set if desired.

## v1.2.11 (2022-04-04)

### Added

- [#1123](https://github.com/nautobot/nautobot/issues/1123) - Add validation for IPAddress assigned_object_type and assigned_object_id.
- [#1146](https://github.com/nautobot/nautobot/issues/1146) - Added change date filtering lookup expressions to GraphQL.
- [#1495](https://github.com/nautobot/nautobot/issues/1495) - Added full coverage of cable termination types to Graphene.
- [#1501](https://github.com/nautobot/nautobot/issues/1501) - Add IP field to CSV export of device.
- [#1529](https://github.com/nautobot/nautobot/pull/1529) - Added list of standard hex colors to the Tags documentation.

### Changed

- [#1536](https://github.com/nautobot/nautobot/pull/1536) - Removed the ServiceUnavailable exception when no `primary_ip` is available for a device, but other connection options are available.
- [#1581](https://github.com/nautobot/nautobot/issues/1581) - Changed MultipleChoiceJSONField to accept choices as a callable, fixing Datasource Contents provided by plugins are not accepted as valid choice by REST API.
- [#1584](https://github.com/nautobot/nautobot/issues/1584) - Replaced links in docs to celeryproject.org with celeryq.dev

### Fixed

- [#1313](https://github.com/nautobot/nautobot/issues/1313) - Fixed GraphQL query error on OneToOneFields such as `IPAddress.primary_ip4_for`
- [#1408](https://github.com/nautobot/nautobot/issues/1408) - Fixed incorrect HTML in the Devices detail views.
- [#1467](https://github.com/nautobot/nautobot/issues/1467) - Fixed an issue where at certain browser widths the nav bar would cover the top of the page content.
- [#1523](https://github.com/nautobot/nautobot/issues/1523) - Fixed primary IP being unset after creating/updating different interface
- [#1548](https://github.com/nautobot/nautobot/issues/1548) - Pin Jinja2 version for mkdocs requirements to fix RTD docs builds related to API deprecation in Jinja2 >= 3.1.0
- [#1583](https://github.com/nautobot/nautobot/issues/1583) - Fixed Nautobot service definition in PostgreSQL-backed development environment.
- [#1599](https://github.com/nautobot/nautobot/pull/1599) - Bump mkdocs version for Snyk report.

## v1.2.10 (2022-03-21)

### Added

- [#1492](https://github.com/nautobot/nautobot/pull/1492) - Added note in the Jobs documentation about the use of `AbortTransaction` to end the job and force rollback.
- [#1517](https://github.com/nautobot/nautobot/pull/1517) - Added password filtering example to advanced logging section in docs.

### Changed

- [#1514](https://github.com/nautobot/nautobot/pull/1514) - Simplified switching between PostgreSQL and MySQL database backends in the developer environment.
- [#1518](https://github.com/nautobot/nautobot/pull/1518) - Updated GitHub Pull Request template to include detail section, todo list.

### Fixed

- [#1511](https://github.com/nautobot/nautobot/issues/1511) - Fixed left column of Read The Docs being cut off.
- [#1522](https://github.com/nautobot/nautobot/pull/1522) - Fixed link name attribute name in developer docs.

## v1.2.9 (2022-03-14)

### Fixed

- [#1431](https://github.com/nautobot/nautobot/issues/1431) - Fixed potential failure of `extras.0017_joblog_data_migration` migration when the job logs contain messages mistakenly logged as object references.
- [#1459](https://github.com/nautobot/nautobot/issues/1459) - Fixed incorrect display of related devices and VMs in the Cluster Type and Cluster Group detail views.
- [#1469](https://github.com/nautobot/nautobot/issues/1469) - Fixed incorrect CSV export for devices

### Security

!!! danger
    It is highly recommended that users of Python 3.6 prioritize upgrading to a newer version of Python. **Nautobot will be removing support for Python 3.6 in a future update.**

!!! important
    For users remaining on Python 3.6, please know that upgrading to Nautobot v1.2.9 **will not resolve these CVEs for your installation**. The only remedy at this time is to upgrade your systems to utilize Python 3.7 or later.

- [#1487](https://github.com/nautobot/nautobot/issues/1487) - Implemented fixes for [CVE-2022-22817](https://github.com/advisories/GHSA-8vj2-vxx3-667w), [CVE-2022-24303](https://github.com/advisories/GHSA-9j59-75qj-795w), and [potential infinite loop](https://github.com/advisories/GHSA-4fx9-vc88-q2xc) by requiring Pillow >=9.0.1 for Python version >=3.7. For Python version <3.7 (e.g. 3.6), it is recommended that you prioritize upgrading your environment to use Python 3.7 or higher. Support for Python 3.6 will be removed in a future update.

## v1.2.8 (2022-03-07)

### Added

- [#839](https://github.com/nautobot/nautobot/issues/839) - Add CODE_OF_CONDUCT.md to repository.
- [#1242](https://github.com/nautobot/nautobot/issues/1242) - Add MAJOR.MINOR tags to Docker images upon release.
- [#1299](https://github.com/nautobot/nautobot/pull/1299) - Add SECURITY.md to repository.
- [#1388](https://github.com/nautobot/nautobot/pull/1388) - Added beta version of GitHub Issue Form style for feature request.
- [#1419](https://github.com/nautobot/nautobot/pull/1419) - Add documentation for specifying a CA cert file for LDAP authentication backend.
- [#1446](https://github.com/nautobot/nautobot/pull/1446) - Apply title labels to Docker images.

### Changed

- [#1348](https://github.com/nautobot/nautobot/pull/1348) - Pin Selenium Grid container version to match Python Client version.
- [#1432](https://github.com/nautobot/nautobot/issues/1432) - Update django-redis to `5.2.x` to address `5.1.x` blocking redis `4.x` versions.
- [#1447](https://github.com/nautobot/nautobot/pull/1447) - Minor `nit` on Github Issue Form styling.
- [#1452](https://github.com/nautobot/nautobot/pull/1452) - Changed GitHub release workflow to not run on prerelease releases.
- [#1453](https://github.com/nautobot/nautobot/pull/1453) - Changed feature request to use GitHub Issue Form.

### Fixed

- [#1301](https://github.com/nautobot/nautobot/issues/1301) - Fixed window history handling for views with tabs in Safari/Firefox.
- [#1302](https://github.com/nautobot/nautobot/issues/1302) - Fixed missing Advanced tab on Virtual Machine detail view.
- [#1398](https://github.com/nautobot/nautobot/issues/1398) - Fixed missing safeguard for removing master from Virtual Chassis via API.
- [#1399](https://github.com/nautobot/nautobot/issues/1399) - Fixed not being able to set master to `null` on Virtual Chassis API.
- [#1405](https://github.com/nautobot/nautobot/issues/1405) - Fixed incorrect import in 'startplugin' template code.
- [#1412](https://github.com/nautobot/nautobot/issues/1412) - Fixed not being able to query for prefix family via GraphQL.
- [#1442](https://github.com/nautobot/nautobot/issues/1442) - Fixed missing Advanced tab on Job Result, Git Repository, and Config Context Schema detail views.

## v1.2.7 (2022-02-22)

### Changed

- [#1403](https://github.com/nautobot/nautobot/issues/1403) - Changes the GitHub Action on Release version template variable name.

## v1.2.6 (2022-02-22)

### Added

- [#1279](https://github.com/nautobot/nautobot/issues/1279) - Circuit terminations now render custom relationships on the circuit detail page.
- [#1353](https://github.com/nautobot/nautobot/issues/1353) - Added UI for deleting previously uploaded images when editing a DeviceType.

### Changed

- [#1386](https://github.com/nautobot/nautobot/issues/1386) - Updated release schedule in docs for patch releases, now every two weeks.

### Fixed

- [#1249](https://github.com/nautobot/nautobot/issues/1249) - Fixed a timing issue where after creating a custom field with a default value and immediately assigning values to this custom field on individual objects, the custom field values could be automatically reverted to the default value.
- [#1280](https://github.com/nautobot/nautobot/pull/1280) - Added missing `get_absolute_url` method to the `CircuitTermination` model, fixing a UI error that could occur when relationships involve CircuitTerminations.
- [#1283](https://github.com/nautobot/nautobot/pull/1283) - Update Sentinel docs to have 3 hosts (minimum per Redis docs), and change `CELERY_BROKER_URL` to a multiline string instead of a Tuple (tuple is invalid, and raises an exception when job completes).
- [#1312](https://github.com/nautobot/nautobot/issues/1312) - Fixed a bug where a Prefix filter matching zero records would instead show all records in the UI.
- [#1327](https://github.com/nautobot/nautobot/pull/1327) - Fixes the broken dependencies from the Release action.
- [#1328](https://github.com/nautobot/nautobot/pull/1328) - Fixed an error in the [Job class-path documentation](../additional-features/jobs.md#jobs-and-class_path).
- [#1332](https://github.com/nautobot/nautobot/pull/1332) - Fixed a regression in which the REST API did not default to pagination based on the configured `PAGINATE_COUNT` setting but instead defaulted to full unpaginated results.
- [#1335](https://github.com/nautobot/nautobot/issues/1335) - Fixed an issue with the Secret create/edit form that caused problems when defining AWS secrets using the `nautobot-secrets-providers` plugin.
- [#1346](https://github.com/nautobot/nautobot/issues/1346) - Fixed an error in the periodic execution of Celery's built-in `celery.backend_cleanup` task.
- [#1360](https://github.com/nautobot/nautobot/issues/1360) - Fixed an issue in the development environment that could cause Selenium integration tests to error out.
- [#1390](https://github.com/nautobot/nautobot/issues/1390) - Pinned transitive dependency `MarkupSafe` to version 2.0.1 as later versions are incompatible with Nautobot's current `Jinja2` dependency.

## v1.2.5 (2022-02-02)

### Changed

- [#1293](https://github.com/nautobot/nautobot/pull/1293) - Reorganized the developer documents somewhat to reduce duplication of information, added diagrams for issue intake process.

### Fixed

- [#371](https://github.com/nautobot/nautobot/issues/371) - Fixed a server error that could occur when importing cables via CSV.
- [#1161](https://github.com/nautobot/nautobot/issues/1161) - The `description` field for device component templates is now correctly propagated to device components created from these templates.
- [#1233](https://github.com/nautobot/nautobot/issues/1233) - Prevented a job aborting when an optional ObjectVar is provided with a value of None
- [#1272](https://github.com/nautobot/nautobot/pull/1272) - Fixed GitHub Actions syntax and Slack payload for `release` CI workflow
- [#1282](https://github.com/nautobot/nautobot/issues/1282) - Fixed a server error when editing User accounts.
- [#1308](https://github.com/nautobot/nautobot/pull/1308) - Fixed another server error that could occur when importing cables via CSV.

## v1.2.4 (2022-01-13)

### Added

- [#1113](https://github.com/nautobot/nautobot/issues/1113) - Added [documentation](../additional-features/caching.md#high-availability-caching) about using Redis Sentinel with Nautobot.
- [#1251](https://github.com/nautobot/nautobot/pull/1251) - Added `workflow_call` to the GitHub Actions CI workflow so that it may be called by other GHA workflows.

### Changed

- [#616](https://github.com/nautobot/nautobot/issues/616) - The REST API now no longer permits setting non-string values for text-type custom fields.
- [#1243](https://github.com/nautobot/nautobot/pull/1243) - Github CI action no longer runs for pull requests that don't impact Nautobot code, such as documentation, examples, etc.

### Fixed

- [#1053](https://github.com/nautobot/nautobot/issues/1053) - Fixed error when removing an IP address from an interface when it was previously the parent device's primary IP.
- [#1140](https://github.com/nautobot/nautobot/issues/1140) - Fixed incorrect UI widgets in the updated Admin UI.
- [#1253](https://github.com/nautobot/nautobot/issues/1253) - Fixed missing code that prevented switching between tabs in the device-type detail view.

### Security

!!! danger
    It is highly recommended that users of Python 3.6 prioritize upgrading to a newer version of Python. **Nautobot will be removing support for Python 3.6 in a future update.**

!!! important
    For users remaining on Python 3.6, please know that upgrading to Nautobot v1.2.4 **will not resolve these CVEs for your installation**. The only remedy at this time is to upgrade your systems utilize Python 3.7 or later.

- [#1267](https://github.com/nautobot/nautobot/issues/1267) - Implemented fixes for [CVE-2022-22815](https://github.com/advisories/GHSA-xrcv-f9gm-v42c), [CVE-2022-22816](https://github.com/advisories/GHSA-xrcv-f9gm-v42c), and [CVE-2022-22817](https://github.com/advisories/GHSA-8vj2-vxx3-667w) to require Pillow >=9.0.0 for Python version >=3.7. For Python version <3.7 (e.g. 3.6), it is recommended that you prioritize upgrading your environment to use Python 3.7 or higher. Support for Python 3.6 will be removed in a future update.

## v1.2.3 (2022-01-07)

### Added

- [#1037](https://github.com/nautobot/nautobot/issues/1037) - Added documentation about how to successfully use the `nautobot-server dumpdata` and `nautobot-server loaddata` commands.

### Fixed

- [#313](https://github.com/nautobot/nautobot/issues/313) - REST API documentation now correctly shows that `status` is a required field.
- [#477](https://github.com/nautobot/nautobot/issues/477) - Model `TextField`s are now correctly mapped to `MultiValueCharFilter` in filter classes.
- [#734](https://github.com/nautobot/nautobot/issues/734) - Requests to nonexistent `/api/` URLs now correctly return a JSON 404 response rather than an HTML 404 response.
- [#1127](https://github.com/nautobot/nautobot/issues/1127) - Fixed incorrect rendering of the navbar at certain browser window sizes.
- [#1203](https://github.com/nautobot/nautobot/issues/1203) - Fixed maximum recursion depth error when filtering GraphQL queries by `device_types`.
- [#1220](https://github.com/nautobot/nautobot/issues/1220) - Fixed an inconsistency in the breadcrumbs seen in various Admin pages.
- [#1228](https://github.com/nautobot/nautobot/issues/1228) - Fixed a case where a GraphQL query for objects associated by Relationships could potentially throw an exception.
- [#1229](https://github.com/nautobot/nautobot/pull/1229) - Fixed a template rendering error in the login page.
- [#1234](https://github.com/nautobot/nautobot/issues/1234) - Fixed missing changelog support for Custom Fields.

### Security

!!! danger
    It is highly recommended that users of Python 3.6 prioritize upgrading to a newer version of Python. **Nautobot will be removing support for Python 3.6 in a future update.**

!!! important
    For users remaining on Python 3.6, please know that upgrading to Nautobot v1.2.3 **will not resolve this CVE for your installation**. The only remedy at this time is to upgrade your systems utilize Python 3.7 or later.

- [#1238](https://github.com/nautobot/nautobot/issues/1238) - Implemented fix for [CVE-2021-23727](https://github.com/advisories/GHSA-q4xr-rc97-m4xx) to require Celery >=5.2.2 for Python version >=3.7. For Python version <3.7 (e.g. 3.6), it is recommended that you prioritize upgrading your environment to use Python 3.7 or higher. Support for Python 3.6 will be removed in a future update.

## v1.2.2 (2021-12-27)

### Added

- [#1152](https://github.com/nautobot/nautobot/pull/1152) - Added REST API and GraphQL for `JobLogEntry` objects.

### Changed

- [#650](https://github.com/nautobot/nautobot/issues/650) - Job Results UI now render job log messages immediately

### Fixed

- [#1181](https://github.com/nautobot/nautobot/pull/1181) - Avoid throwing a 500 error in the case where users have deleted a required Status value. (Preventing the user from doing this will need to be a later fix.)
- [#1186](https://github.com/nautobot/nautobot/pull/1186) - Corrected an error in the docs regarding developing secrets providers in plugins.
- [#1188](https://github.com/nautobot/nautobot/pull/1188) - Corrected some errors in the developer documentation about our branch management approach.
- [#1193](https://github.com/nautobot/nautobot/issues/1193) - Fixed `JobResult` page may fail to list `JobLogEntries` in chronological order
- [#1195](https://github.com/nautobot/nautobot/issues/1195) - Job log entries now again correctly render inline Markdown formatting.

## v1.2.1 (2021-12-16)

### Added

- [#1110](https://github.com/nautobot/nautobot/issues/1110) - Added GraphQL support for the `ObjectChange` model.

### Changed

- [#1106](https://github.com/nautobot/nautobot/issues/1106) - Updating Docker health checks to be more robust and greatly reduce performance impact.

### Fixed

- [#1170](https://github.com/nautobot/nautobot/pull/1170) - Fixed bug in renamed column of `JobResultTable` where rename was not made to the `Meta`.
- [#1173](https://github.com/nautobot/nautobot/issues/1173) - Fixed official Docker image: v1.2.0 tagged images fail to load with `ImportError: libxml2.so.2`.

### Removed

### Security

- [#1077](https://github.com/nautobot/nautobot/issues/1077) - Updated `graphiql` to 1.5.16 as well as updating the associated Javascript libraries used in the GraphiQL UI to address a reported security flaw in older versions of GraphiQL. To the best of our understanding, the Nautobot implementation of GraphiQL was not vulnerable to said flaw.

## v1.2.0 (2021-12-15)

### Added

- [#843](https://github.com/nautobot/nautobot/issues/843) - Added more information about Celery in the Upgrading Nautobot docs.
- [#876](https://github.com/nautobot/nautobot/issues/876) - Added option to apply a validation regex when defining CustomFieldChoices.
- [#965](https://github.com/nautobot/nautobot/pull/965) - Added example script for performing group sync from AzureAD.
- [#982](https://github.com/nautobot/nautobot/issues/982) - Added IPAM custom lookup database functions.
- [#1002](https://github.com/nautobot/nautobot/pull/1002) - Added `URM-P2`, `URM-P4`, and `URM-P8` port types.
- [#1041](https://github.com/nautobot/nautobot/pull/1041) - Add passing of `**kwargs` to Celery tasks when using `JobResult.enqueue_job()` to execute a `Job`.
- [#1080](https://github.com/nautobot/nautobot/pull/1080) - Added documentation around using LDAP with multiple search groups.
- [#1082](https://github.com/nautobot/nautobot/issues/1082) - Added `netutils` template filters for both Django and Jinja2 template rendering.
- [#1104](https://github.com/nautobot/nautobot/issues/1104) - Added documentation and context on filtering execution of unit tests using labels
- [#1124](https://github.com/nautobot/nautobot/issues/1124) - Added documentation on generating `SECRET_KEY` before Nautobot is configured.
- [#1143](https://github.com/nautobot/nautobot/pull/1143) - Added documentation on using LDAP with multiple LDAP servers.
- [#1159](https://github.com/nautobot/nautobot/pull/1159) - Add `family` field to `IPAddressType` for GraphQL API enable filtering of `IPAddress` objects by `family`.

### Changed

- [#1068](https://github.com/nautobot/nautobot/issues/1068) - Docker images now include optional Nautobot dependencies by default.
- [#1095](https://github.com/nautobot/nautobot/issues/1095) - Refined Admin Configuration UI.
- [#1105](https://github.com/nautobot/nautobot/pull/1105) - Reverted minimum Python 3.6 version to 3.6.0 rather than 3.6.2.

### Fixed

- [#453](https://github.com/nautobot/nautobot/issues/453) - Fixed potential `ValueError` when rendering `JobResult` detail view with non-standard `JobResult.data` contents.
- [#864](https://github.com/nautobot/nautobot/issues/864) - Fixed inconsistent `JobResult` detail view page templates.
- [#888](https://github.com/nautobot/nautobot/issues/888) - Addressed FIXME comment in LDAP documentation.
- [#926](https://github.com/nautobot/nautobot/issues/926) - Fixed inability to pass multiple values for a MultiObjectVar as query parameters.
- [#958](https://github.com/nautobot/nautobot/issues/958) - Fixed Job REST API handling of ObjectVars specified by query parameters.
- [#992](https://github.com/nautobot/nautobot/issues/992) - Improved loading/rendering time of the `JobResult` table/list view.
- [#1043](https://github.com/nautobot/nautobot/issues/1043) - Fixed `AttributeError` when bulk-adding interfaces to virtual machines.
- [#1078](https://github.com/nautobot/nautobot/issues/1078) - Fixed missing support for filtering several models by their custom fields and/or created/updated stamps.
- [#1093](https://github.com/nautobot/nautobot/pull/1093) - Improved REST API performance by adding caching of serializer "opt-in fields".
- [#1098](https://github.com/nautobot/nautobot/issues/1098) - Fixed 404 error when creating a circuit termination for circuit and other edge cases resulting in 404 errors
- [#1112](https://github.com/nautobot/nautobot/issues/1112) - Fixed broken single-object GraphQL query endpoints.
- [#1116](https://github.com/nautobot/nautobot/issues/1116) - Fixed UnboundLocalError when using device NAPALM integration
- [#1121](https://github.com/nautobot/nautobot/pull/1121) - Fixed issue with handling of relationships referencing no-longer-present model classes.
- [#1133](https://github.com/nautobot/nautobot/pull/1133) - Fixed some incorrect documentation about the Docker image build/publish process.
- [#1141](https://github.com/nautobot/nautobot/issues/1141) - Improved reloading of changed Job files. (Port of [NetBox #7820](https://github.com/netbox-community/netbox/pull/7820))
- [#1154](https://github.com/nautobot/nautobot/issues/1154) - Fixed inability to save changes in Admin Configuration UI.
- [#1162](https://github.com/nautobot/nautobot/issues/1162) - Fixed error when creating a `NavMenuItem` without specifying the `buttons` argument.

### Removed

- [#1094](https://github.com/nautobot/nautobot/issues/1094) - Removed leftover custom field management views from Admin UI

## v1.2.0b1 (2021-11-19)

### Added

- [#13](https://github.com/nautobot/nautobot/issues/13) - Added `nautobot_database_ready` signal
- [#125](https://github.com/nautobot/nautobot/issues/125) - Added support for `approval_required = True` on Jobs
- [#157](https://github.com/nautobot/nautobot/issues/157) - Added support for same-object-type and symmetric Relationships
- [#171](https://github.com/nautobot/nautobot/issues/171) - GraphQL queries have been greatly optimized by integration with `graphene-django-optimizer`
- [#229](https://github.com/nautobot/nautobot/issues/229) - Added user-facing views for Custom Field management
- [#248](https://github.com/nautobot/nautobot/issues/248) - Added support for filtering GraphQL queries at all levels
- [#370](https://github.com/nautobot/nautobot/issues/370) - Added support for server configuration via the Admin UI.
- [#374](https://github.com/nautobot/nautobot/issues/374) - Added ability to schedule Jobs for future and/or recurring execution
- [#478](https://github.com/nautobot/nautobot/issues/478) - CustomFieldChoice model now supports GraphQL.
- [#479](https://github.com/nautobot/nautobot/issues/479) - Added shared generic template for all object detail views
- [#519](https://github.com/nautobot/nautobot/issues/519) - Added webhook support for `CustomField` and `CustomFieldChoice` models.
- [#534](https://github.com/nautobot/nautobot/issues/534) - Added ability to inject a banner from a plugin
- [#541](https://github.com/nautobot/nautobot/issues/541) - Added Secrets integration
- [#580](https://github.com/nautobot/nautobot/issues/580) - Added ability for plugins to register "home" and "configuration" views.
- [#585](https://github.com/nautobot/nautobot/issues/585) - Added "Advanced" tab to object detail views including UUID and slug information.
- [#642](https://github.com/nautobot/nautobot/issues/642) - Added documentation of the `GIT_SSL_NO_VERIFY` environment variable for using self-signed Git repositories
- [#674](https://github.com/nautobot/nautobot/pull/674) - Plugins can now add items to the Nautobot home page
- [#716](https://github.com/nautobot/nautobot/pull/716) - Nautobot home page content is now dynamically populated based on installed apps and plugins.
- [#866](https://github.com/nautobot/nautobot/pull/859) - Added support for organizational custom branding for the logo and icons
- [#866](https://github.com/nautobot/nautobot/pull/866) - Added documentation for job scheduling and approvals
- [#879](https://github.com/nautobot/nautobot/pull/879) - Added API testing for job scheduling and approvals
- [#908](https://github.com/nautobot/nautobot/pull/908) - Added UI testing for job scheduling and approvals
- [#935](https://github.com/nautobot/nautobot/pull/935) - Added Installed Plugins list view and detail view
- [#937](https://github.com/nautobot/nautobot/issues/937) - Added bulk-delete option for scheduled jobs
- [#938](https://github.com/nautobot/nautobot/issues/938) - Added titles to job approval UI buttons
- [#947](https://github.com/nautobot/nautobot/pull/947) - Added `DISABLE_PREFIX_LIST_HIERARCHY` setting to render IPAM Prefix list view as a flat list
- [#953](https://github.com/nautobot/nautobot/pull/953) - Added option to use MySQL in docker-compose development environment

### Changed

- [#222](https://github.com/nautobot/nautobot/issues/222) - Changed wildcard imports to explicitly enumerated imports and enabled associated Flake8 linter rules.
- [#472](https://github.com/nautobot/nautobot/issues/472) - `JobResult` lists now show the associated Job's name (if available) instead of the Job's `class_path`.
- [#493](https://github.com/nautobot/nautobot/issues/493) - All `slug` fields are now optional when creating records via the REST API, ORM, or CSV import. Slugs will be automatically assigned if unspecified.
- [#877](https://github.com/nautobot/nautobot/pull/877) - Hid unused "Social Auth" section from Django admin page.
- [#900](https://github.com/nautobot/nautobot/pull/900) - Admin site has been revised and re-skinned to more closely match the core Nautobot UI.

### Fixed

- [#852](https://github.com/nautobot/nautobot/issues/852) - Fixed missing "Change Log" tab on certain object detail views
- [#853](https://github.com/nautobot/nautobot/issues/853) - Fixed `AttributeError` on certain object detail views
- [#891](https://github.com/nautobot/nautobot/issues/891) - Fixed custom field select/multiselect not handled by new UI and added integration tests
- [#966](https://github.com/nautobot/nautobot/issues/966) - Fixed missing "Advanced" tab on Device detail views
- [#1060](https://github.com/nautobot/nautobot/issues/1060) - Fixed documentation incorrectly indicating that the Admin UI was the only way to manage custom field definitions.

### Security

- [#1017](https://github.com/nautobot/nautobot/issues/1017) - Custom field descriptions no longer potentially render as arbitrary HTML in object edit forms; Markdown format is now supported as a less dangerous option.
