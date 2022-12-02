<!-- markdownlint-disable MD024 -->

# Nautobot v1.5

This document describes all new features and changes in Nautobot 1.5.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Added `nautobot-server generate_test_data` command ([#2536](https://github.com/nautobot/nautobot/issues/2536))

A new management command, [`nautobot-server generate_test_data`](../administration/nautobot-server.md#generate_test_data), has been added that can be used to populate the Nautobot database with various data as a baseline for manual or automated testing. This is now used internally by Nautobot's unit testing suite to create a synthetic data set that looks and feels like real data with randomly-generated values. Most importantly, the objects are created with all of the fields fully and correctly populated, to assert that each object in the database is properly exercising all features.

!!! warning
    Be very cautious about running this command on your server instance. It is not intended to be used in production environments and will result in data loss.

#### Custom Field Grouping ([#899](https://github.com/nautobot/nautobot/issues/899))

Custom fields can now be assigned to a free-text "grouping" to improve usability when a large number of custom fields are defined on a given model. In the UI, fields in the same grouping will be grouped together, and groupings can be expanded/collapsed for display purposes.

#### Custom Celery Task Queues ([#2421](https://github.com/nautobot/nautobot/pull/2421))

A new optional job property `task_queues` has been introduced to allow Nautobot to leverage custom celery queues for jobs. This will allow you to send jobs to specific workers based on which queue is selected. This property can be set on the job class and overridden in the job model, similar to other overridable job fields. If `task_queues` is not defined on the job class or job model, the job will only be able to use the default queue. A new field has been added to the job run form to allow you to select a queue when you run the job and  an optional field `task_queue` has been added to the REST API [job run endpoint](../additional-features/jobs.md#via-the-api) for the same purpose.

!!! important
    The default celery queue name has been changed from `celery` to `default`. If you have any workers or tasks hard coded to use `celery` you will need to update those workers/tasks or change the [`CELERY_TASK_DEFAULT_QUEUE`](../configuration/optional-settings.md#celery_task_default_queue) setting in your `nautobot_config.py`.

#### Device Redundancy Groups ([#1892](https://github.com/nautobot/nautobot/issues/1892))

Device Redundancy Groups have been added to model groups of distinct devices that perform device clustering or failover high availability functions. This may be used to model whole device redundancy strategies across devices with separate control planes (ex: ASA failover), not devices that share a control plane (ex: stackwise switch stacks), or interface specific redundancy strategies (ex: hsrp). Device Redundancy Groups support grouping an arbitrary number of devices and may be assigned an optional secrets group and one or more optional failover strategies.

#### Nautobot Apps API ([#2723](https://github.com/nautobot/nautobot/issues/2723))

+++ 1.5.2

The new `nautobot.apps` module provides a common starting point for app (a.k.a. plugin) developers to find all of the functions and classes that are recommended for use in apps. For example, instead of needing to look through the entire Nautobot codebase to find the appropriate classes, and then write:

```python
from nautobot.extras.forms import NautobotModelForm
from nautobot.utilities.forms import BulkEditForm, CSVModelForm
from nautobot.utilities.forms.fields import DynamicModelChoiceField
```

an app developer can now refer to `nautobot.apps.forms` and then write simply:

```python
from nautobot.apps.forms import (
    BulkEditForm,
    CSVModelForm,
    DynamicModelChoiceField,
    NautobotModelForm,
)
```

For more details, please refer to the updated [app developer documentation](../plugins/development.md).

#### Nestable LocationTypes ([#2608](https://github.com/nautobot/nautobot/issues/2608))

`LocationType` definitions can now be flagged as `nestable`. When this flag is set, Locations of this type may nest within one another, similar to how Regions work at present. This allows you to have a variable-depth hierarchy of Locations, for example:

- Main Campus ("Building Group" location type)
    - West Campus (Building Group)
        - Building A ("Building" location type)
        - Building B (Building)
    - East Campus (Building Group)
        - Building C (Building)
        - Building D (Building)
    - South Campus (Building Group)
        - Western South Campus (Building Group)
            - Building G (Building)
- Satellite Campus (Building Group)
    - Building Z (Building)

In the above example, only two LocationTypes are defined ("Building Group" and "Building") but the "Building Group" type is flagged as nestable, so one Building Group may contain another Building Group.

#### Required Relationships ([#873](https://github.com/nautobot/nautobot/issues/873))

Relationships can be marked as being required. By default, relationships are not marked as being required.

To mark a relationship as being required, select "Source objects MUST implement this relationship" or conversely "
Destination objects MUST implement this relationship" from the "Required on" field when editing or creating a
relationship:

- If "Destination objects MUST implement this relationship" is selected, objects of the type selected in "Destination Type" will enforce this relationship when they are created or edited.
- If "Source objects MUST implement this relationship" is selected, objects of the type selected in "Source Type" will enforce this relationship when they are created or edited.

Required relationships are enforced in the following scenarios:

- Creating or editing an object via the API or the UI
- Bulk creating objects via the API
- Bulk editing objects via the API or the UI

### Changed

#### Database Query Caching is now Disabled by Default ([#1721](https://github.com/nautobot/nautobot/issues/1721))

In prior versions of Nautobot, database query caching using the [`django-cacheops`](https://github.com/Suor/django-cacheops) application (aka Cacheops) was enabled by default. This is determined by the default value of the [`CACHEOPS_ENABLED`](../configuration/optional-settings.md#cacheops_enabled) setting being set to `True`.

Through much trial and error we ultimately decided that this feature is more trouble than it is worth and we have begun to put more emphasis on improving performance of complex database queries over continuing to rely upon the various benefits and pitfalls of utilizing Cacheops.

As a result, the value of this setting now defaults to `False`, disabling database query caching entirely for new deployments. Cacheops will be removed entirely in a future release.

!!! important
    Users with existing `nautobot_config.py` files generated from earlier versions of Nautobot will still have `CACHEOPS_ENABLED = True` unless they modify or regenerate their configuration. If users no longer desire caching, please be sure to explicitly toggle the value of this setting to `False` and restart your Nautobot services.

#### Deprecation Warnings Silenced by Default ([#2798](https://github.com/nautobot/nautobot/pull/2798))

+/- 1.5.2

Deprecation warnings raised by Nautobot itself (such as warnings about upcoming breaking changes in a future release) are no longer logged as `WARNING` log messages by default, but can be enabled by setting the `NAUTOBOT_LOG_DEPRECATION_WARNINGS` environment variable to `True` in your configuration. More information is available under [Optional Settings](../configuration/optional-settings.md#nautobot_log_deprecation_warnings).

!!! caution
    In Nautobot 2.0, deprecation warnings will again be logged by default; a future release of Nautobot 1.5.x will also re-enable default logging of deprecation warnings.

#### Redesigned List Filtering UI ([#1998](https://github.com/nautobot/nautobot/issues/1998))

Added a dynamic filter form that allows users to filter object tables/lists by any field and lookup expression combination supported by the corresponding FilterSet and API.

#### Renamed Mixin Classes ([#2779](https://github.com/nautobot/nautobot/issues/2779))

+/- 1.5.2

A number of mixin classes have been renamed and/or relocated for improved self-consistency and clarity of usage. The former names of these mixins are still available for now as aliases, but inheriting from these aliases will now raise a `DeprecationWarning`, and these aliases wil be removed in a future release.

| Former Name                    | New Name                                     |
| ------------------------------ | -------------------------------------------- |
| `CableTerminationFilterSet`    | `CableTerminationModelFilterSetMixin`        |
| `CableTerminationSerializer`   | `CableTerminationModelSerializerMixin`       |
| `ConnectedEndpointSerializer`  | `PathEndpointModelSerializerMixin`           |
| `ConnectionFilterSet`          | `ConnectionFilterSetMixin`                   |
| `CreatedUpdatedFilterSet`      | `CreatedUpdatedModelFilterSetMixin`          |
| `CustomFieldModelFilterSet`    | `CustomFieldModelFilterSetMixin`             |
| `CustomFieldModelSerializer`   | `CustomFieldModelSerializerMixin`            |
| `DeviceComponentFilterSet`     | `DeviceComponentModelFilterSetMixin`         |
| `DeviceTypeComponentFilterSet` | `DeviceComponentTemplateModelFilterSetMixin` |
| `LocalContextFilterSet`        | `LocalContextModelFilterSetMixin`            |
| `PathEndpointFilterSet`        | `PathEndpointModelFilterSetMixin`            |
| `PluginBanner`                 | `Banner`                                     |
| `PluginConfig`                 | `NautobotAppConfig`                          |
| `PluginCustomValidator`        | `CustomValidator`                            |
| `PluginFilterExtension`        | `FilterExtension`                            |
| `PluginTemplateExtension`      | `TemplateExtension`                          |
| `RelationshipModelFilterSet`   | `RelationshipModelFilterSetMixin`            |
| `TaggedObjectSerializer`       | `TaggedModelSerializerMixin`                 |
| `TenancyFilterSet`             | `TenancyModelFilterSetMixin`                 |

<!-- towncrier release notes start -->
## v1.5.3 (2022-11-29)

### Fixed

- [#2924](https://github.com/nautobot/nautobot/issues/2924) - Fix deprecation warning flag check throwing error on startup with plugins installed.

## v1.5.2 (2022-11-28)

### Added

- [#1273](https://github.com/nautobot/nautobot/issues/1273) - Added section "VS Code Remote Debugging Configuration" to development chapter in documentation.
- [#2473](https://github.com/nautobot/nautobot/issues/2473) - Added `multipart/form-data` support to Job run API.
- [#2723](https://github.com/nautobot/nautobot/issues/2723) - Added `nautobot.apps` module to provide a central location for code that is recommended for use by Nautobot apps (plugins).
- [#2723](https://github.com/nautobot/nautobot/issues/2723) - Added code reference documentation for the `nautobot.apps` module.
- [#2759](https://github.com/nautobot/nautobot/issues/2759) - Add prometheus metrics for health check results
- [#2798](https://github.com/nautobot/nautobot/issues/2798) - Added `LOG_DEPRECATION_WARNINGS` configuration variable and corresponding environment-variable support.

### Changed

- [#2644](https://github.com/nautobot/nautobot/issues/2644) - Changed published accepted content types for REST API to remove unsupported types.
- [#2723](https://github.com/nautobot/nautobot/issues/2723) - Moved app (plugin) development documentation into its own section.
- [#2723](https://github.com/nautobot/nautobot/issues/2723) - Revised "plugin" development documentation to refer to "apps" instead where appropriate.
- [#2779](https://github.com/nautobot/nautobot/issues/2779) - Renamed many mixin classes for clarity and consistency. Aliases remain but will raise `DeprecationWarning`.
- [#2779](https://github.com/nautobot/nautobot/issues/2779) - Reorganized filterset code and created `nautobot.dcim.filters.mixins`, `nautobot.extras.filters.mixins`, and `nautobot.tenancy.filters.mixins` submodules.
- [#2798](https://github.com/nautobot/nautobot/issues/2798) - Changed logging of Nautobot deprecation warnings to be silent by default (can be enabled with `DEBUG` or `LOG_DEPRECATION_WARNINGS` settings).
- [#2814](https://github.com/nautobot/nautobot/issues/2814) - Update dependency `netutils` to `~1.3.0`.
- [#2817](https://github.com/nautobot/nautobot/issues/2817) - Update docs to not indicate prompt, makes for better use of copy code snippet feature of MkDocs
- [#2838](https://github.com/nautobot/nautobot/issues/2838) - Fixed filter selection box colors in dark mode.
- [#2878](https://github.com/nautobot/nautobot/issues/2878) - Changed Upstream Workflow Job to continue on error for group, not each specific job.

### Fixed

- [#1519](https://github.com/nautobot/nautobot/issues/1519) - Extending the model table columns that need to display copy button when hovered over.
- [#2477](https://github.com/nautobot/nautobot/issues/2477) - Fixed last login time being updated during maintenance mode when remote user authentication is used.
- [#2744](https://github.com/nautobot/nautobot/issues/2744) - Enforced required Relationships when bulk editing or creating objects that have required relationships. Bulk edit via API or UI. Bulk create via API.
- [#2774](https://github.com/nautobot/nautobot/issues/2774) - Fixed SiteFactory time_zone attribute to use only `pytz.common_timezones`.
- [#2795](https://github.com/nautobot/nautobot/issues/2795) - Fixed changelog diff data to fall back to `object_data` when `object_data_v2` is not present for both `ObjectChange` instances.
- [#2816](https://github.com/nautobot/nautobot/issues/2816) - Fixed issue where changing the interface mode first required removing tagged_vlans in a different request.
- [#2819](https://github.com/nautobot/nautobot/issues/2819) - Adds appropriate invoke task for running docs locally and adds how to run manually.
- [#2833](https://github.com/nautobot/nautobot/issues/2833) - Fixed plugin banner issue and breadcrumb rendering issue in NautobotHTMLRenderer.
- [#2837](https://github.com/nautobot/nautobot/issues/2837) - Fixed incorrect logic in `nautobot.utilities.utils.is_single_choice_field` that was causing valid filters to report as invalid.

## v1.5.1 (2022-11-14)

### Added

- [#2500](https://github.com/nautobot/nautobot/issues/2500) - Added `try/except` block to catch `NoReverseMatch` exception in NotesSerializerMixin and return helpful message.
- [#2556](https://github.com/nautobot/nautobot/issues/2556) - Revised TODO/FIXME comments for more clarity.
- [#2740](https://github.com/nautobot/nautobot/issues/2740) - Added ObjectChangeLogView and ObjectNotesView Viewset mixins and routes.

### Changed

- [#1813](https://github.com/nautobot/nautobot/issues/1813) - Updated Example_Plugin to use NautobotUIViewSet.

### Fixed

- [#2470](https://github.com/nautobot/nautobot/issues/2470) - Fixed incorrect automatic generation of Location slugs in the UI.
- [#2757](https://github.com/nautobot/nautobot/issues/2757) - Fixed filters on default filter form replaces filters on dynamic filter form on submit
- [#2761](https://github.com/nautobot/nautobot/issues/2761) - Fixed failover strategy not being displayed on Device Redundancy Group page.
- [#2789](https://github.com/nautobot/nautobot/issues/2789) - Fixed web UI footer margin and swagger UI authorization box size.
- [#2824](https://github.com/nautobot/nautobot/issues/2824) - Fixed an issue when filtering on nested related fields for Dynamic Groups.

## v1.5.0 (2022-11-08)

Unchanged from v1.5.0-beta.1.

## v1.5.0-beta.1 (2022-11-07)

### Added

- [#270](https://github.com/nautobot/nautobot/issues/270) - Added custom fields user guide to documentation.
- [#873](https://github.com/nautobot/nautobot/issues/873) - Made it possible to require Relationships to be included when editing or creating the related models.
- [#899](https://github.com/nautobot/nautobot/issues/899) - Added support for grouping of Custom Fields.
- [#1468](https://github.com/nautobot/nautobot/issues/1468) - Added relationship columns to ObjectListTableView and disabled sorting.
- [#1892](https://github.com/nautobot/nautobot/issues/1892) - Added `DeviceRedundancyGroup` model for representing a logical grouping of physical hardware for the purposes of high-availability.
- [#2063](https://github.com/nautobot/nautobot/issues/2063) - Added documentation and initial support for custom celery queues.
- [#2064](https://github.com/nautobot/nautobot/issues/2064) - Added `task_queues` job property to support custom celery queues.
- [#2227](https://github.com/nautobot/nautobot/issues/2227) - Added generating performance report options to 'invoke unittest'.
- [#2227](https://github.com/nautobot/nautobot/issues/2227) - Added `invoke performance-test` to `tasks.py`.
- [#2281](https://github.com/nautobot/nautobot/issues/2281) - Added test database fixtures for Tag and Status models.
- [#2282](https://github.com/nautobot/nautobot/issues/2282) - Added fixture factory for Region, Site, Location, LocationType.
- [#2283](https://github.com/nautobot/nautobot/issues/2283) - Added test fixture factories for Prefix and IPAddress models.
- [#2460](https://github.com/nautobot/nautobot/issues/2460) - Added search box filter form to generic list views.
- [#2479](https://github.com/nautobot/nautobot/issues/2479) - Added `factory-boy` as development dependency. Added factories for Tenant, TenantGroup, RIR, and Aggregate models. Updated test runner global setup to use these factories to pre-populate baseline data.
- [#2514](https://github.com/nautobot/nautobot/issues/2514) - Added test factories for RouteTarget, VRF, Role, VLANGroup, and VLAN models.
- [#2514](https://github.com/nautobot/nautobot/issues/2514) - Added `OrganizationalModelFactory` and `PrimaryModelFactory` base classes.
- [#2514](https://github.com/nautobot/nautobot/issues/2514) - Added `TenancyFilterTestCaseMixin` class.
- [#2518](https://github.com/nautobot/nautobot/issues/2518) - Added `base_site` and `subtree` filters to `LocationFilterSet`, allowing for filtering Locations by their root ancestor or its Site.
- [#2536](https://github.com/nautobot/nautobot/issues/2536) - Added `nautobot-server generate_test_data` command.
- [#2536](https://github.com/nautobot/nautobot/issues/2536) - Added `TEST_USE_FACTORIES` and `TEST_FACTORY_SEED` optional settings.
- [#2593](https://github.com/nautobot/nautobot/issues/2593) - Added StatusFactory and TagFactory classes.
- [#2594](https://github.com/nautobot/nautobot/issues/2594) - Added factories for DCIM `DeviceRole`, `DeviceType`, `Manufacturer`, and `Platform`.
- [#2608](https://github.com/nautobot/nautobot/issues/2608) - Added the option for certain LocationTypes to be nestable (similar to Regions).
- [#2617](https://github.com/nautobot/nautobot/issues/2617) - Added dynamic filter form support to specialized list views.
- [#2686](https://github.com/nautobot/nautobot/issues/2686) - Added test helper method to `FilterTestCases` to find values suitable for testing multiple choice filters.

### Changed

- [#1892](https://github.com/nautobot/nautobot/issues/1892) - Updated `Device` to have `device_redundancy_group` relationship, `device_redundancy_group_priority` numeric property.
- [#1892](https://github.com/nautobot/nautobot/issues/1892) - Updated `ConfigContext` to have `ManyToManyField` to `dcim.DeviceRedundancyGroup` for the purposes of applying a `ConfigContext` based upon a `Device`s `DeviceRedundancyGroup` membership.
- [#1983](https://github.com/nautobot/nautobot/issues/1983) - Updated `django-taggit` dependency to 3.0.0.
- [#1998](https://github.com/nautobot/nautobot/issues/1998) - Added DynamicFilterForm to list views.
- [#2064](https://github.com/nautobot/nautobot/issues/2064) - Changed default celery queue name from `celery` to `default`.
- [#2170](https://github.com/nautobot/nautobot/issues/2170) - Updated `django-constance` dependency to 2.9.1; updated `Jinja2` dependency to 3.1.2; updated `black` development dependency to 22.8.0.
- [#2282](https://github.com/nautobot/nautobot/issues/2282) - Changed unittests to use Site, Region, Location, LocationType fixtures.
- [#2320](https://github.com/nautobot/nautobot/issues/2320) - Removed PKs from Tag test database fixture.
- [#2482](https://github.com/nautobot/nautobot/issues/2482) - Updated `djangorestframework` to `~3.14.0`, `drf-spectacular` to `0.24.2`.
- [#2483](https://github.com/nautobot/nautobot/issues/2483) - Updated `mkdocs` to 1.4.2 and `mkdocs-material` to 8.5.8.
- [#2484](https://github.com/nautobot/nautobot/issues/2484) - Updated `django-debug-toolbar` to `~3.7.0`
- [#2551](https://github.com/nautobot/nautobot/issues/2551) - Updated development dependency on `coverage` to version 6.5.0.
- [#2562](https://github.com/nautobot/nautobot/issues/2562) - Updated `django-mptt` dependency to 0.14.0.
- [#2597](https://github.com/nautobot/nautobot/issues/2597) - Updated `GitPython` dependency from 3.1.27 to 3.1.29.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Changed `ConfigContextFilterForm`s `schema` filter form field to support added filter field on `ConfigContextFilterSet`.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Changed `BaseNetworkQuerySet` and `IPAddressQuerySet` to search both IPv6 and IPv4 when given search string is ambiguous.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Changed `test_slug_not_modified` to ensure no collision on new slug source value as well as changing lookup expression from `__contains` to `__exact`.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Changed `DeleteObjectViewTestCase.get_deletable_object` to throw a helpful failure message when deletable object not found.
- [#2645](https://github.com/nautobot/nautobot/issues/2645) - Updated `psycopg2-binary` dependency from 2.9.3 to 2.9.5.
- [#2710](https://github.com/nautobot/nautobot/issues/2710) - Updated `pyuwsgi` minimum version from 2.0.20 to 2.0.21.
- [#2711](https://github.com/nautobot/nautobot/issues/2711) - Updated `Pillow` package dependency from 9.2.0 to 9.3.0.
- [#2746](https://github.com/nautobot/nautobot/issues/2746) - Changed `LocationType` test case to not attempt to re-parent a `LocationType` with descendant `Locations`.

### Fixed

- [#192](https://github.com/nautobot/nautobot/issues/192) - Eliminated Unit Test noisy output.
- [#2266](https://github.com/nautobot/nautobot/issues/2266) - Fixed navbar floating over main viewport scrollbar.
- [#2388](https://github.com/nautobot/nautobot/issues/2388) - Return "—" instead of "None" when relationship column is empty.
- [#2536](https://github.com/nautobot/nautobot/issues/2536) - Made use of test factories optional when using Nautobot test runner.
- [#2555](https://github.com/nautobot/nautobot/issues/2555) - Fixed broken accordion for Job list view.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `ConfigContextFilterSet` missing `schema` filter but existed on form.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `Device(Form)TestCase` flaky test setup possibly not finding a `DeviceType` with a `Manufacturer` with associated `Platform`s that is full depth and 1U height.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `Location(View)TestCase`, `RouteTarget(View)TestCase` flaky test setup possibly finding names for `csv_data` that might include commas but not escaped.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `PrefixFactory` may randomly decide to create a child of `2.2.2.2/32`.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `BaseNetworkQuerySet` and `IPAddressQuerySet` only searching non-abbreviated first hextet IPv6 addresses.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `DynamicFilterLookupExpressionTest`, `VirtualChassis(Filter)TestCase`, `Cluster(Filter)TestCase`, `VirtualMachine(Filter)TestCase` had too narrow of a region lookup for supported tests.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `RackGroup(Model)Test`, `Prefix(Model)Test`, `VLANGroup(Model)Test` may randomly choose to update to the same site.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `Tenant(View)TestCase`, `RIR(View)TestCase` may not find deletable objects.
- [#2615](https://github.com/nautobot/nautobot/issues/2615) - Fixed `VLAN(View)TestCase` may not find enough `Site`s with `Location`s.
- [#2691](https://github.com/nautobot/nautobot/issues/2691) - Fixed hard coded tests that were failing after factory fixtures were integrated.
- [#2746](https://github.com/nautobot/nautobot/issues/2746) - Fixed Site `latitude`, `longitude` clean method for when valid string value entered.

### Removed

- [#2593](https://github.com/nautobot/nautobot/issues/2593) - Removed static test fixtures since we're using factories now instead.
