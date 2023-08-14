<!-- markdownlint-disable MD024 -->

# Nautobot v1.5

This document describes all new features and changes in Nautobot 1.5.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../user-guide/administration/migration/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Added `nautobot-server generate_test_data` command ([#2536](https://github.com/nautobot/nautobot/issues/2536))

A new management command, [`nautobot-server generate_test_data`](../user-guide/administration/tools/nautobot-server.md#generate_test_data), has been added that can be used to populate the Nautobot database with various data as a baseline for manual or automated testing. This is now used internally by Nautobot's unit testing suite to create a synthetic data set that looks and feels like real data with randomly-generated values. Most importantly, the objects are created with all of the fields fully and correctly populated, to assert that each object in the database is properly exercising all features.

!!! warning
    Be very cautious about running this command on your server instance. It is not intended to be used in production environments and will result in data loss.

#### Custom Field Grouping ([#899](https://github.com/nautobot/nautobot/issues/899))

Custom fields can now be assigned to a free-text "grouping" to improve usability when a large number of custom fields are defined on a given model. In the UI, fields in the same grouping will be grouped together, and groupings can be expanded/collapsed for display purposes.

#### Custom Celery Task Queues ([#2421](https://github.com/nautobot/nautobot/pull/2421))

A new optional job property `task_queues` has been introduced to allow Nautobot to leverage custom celery queues for jobs. This will allow you to send jobs to specific workers based on which queue is selected. This property can be set on the job class and overridden in the job model, similar to other overridable job fields. If `task_queues` is not defined on the job class or job model, the job will only be able to use the default queue. A new field has been added to the job run form to allow you to select a queue when you run the job and  an optional field `task_queue` has been added to the REST API [job run endpoint](../user-guide/platform-functionality/jobs/index.md#via-the-api) for the same purpose.

!!! important
    The default celery queue name has been changed from `celery` to `default`. If you have any workers or tasks hard coded to use `celery` you will need to update those workers/tasks or change the [`CELERY_TASK_DEFAULT_QUEUE`](../user-guide/administration/configuration/optional-settings.md#celery_task_default_queue) setting in your `nautobot_config.py`.

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

For more details, please refer to the updated [app developer documentation](../development/apps/index.md).

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

In prior versions of Nautobot, database query caching using the [`django-cacheops`](https://github.com/Suor/django-cacheops) application (aka Cacheops) was enabled by default. This is determined by the default value of the [`CACHEOPS_ENABLED`](../user-guide/administration/configuration/optional-settings.md#cacheops_enabled) setting being set to `True`.

Through much trial and error we ultimately decided that this feature is more trouble than it is worth and we have begun to put more emphasis on improving performance of complex database queries over continuing to rely upon the various benefits and pitfalls of utilizing Cacheops.

As a result, the value of this setting now defaults to `False`, disabling database query caching entirely for new deployments. Cacheops will be removed entirely in a future release.

!!! important
    Users with existing `nautobot_config.py` files generated from earlier versions of Nautobot will still have `CACHEOPS_ENABLED = True` unless they modify or regenerate their configuration. If users no longer desire caching, please be sure to explicitly toggle the value of this setting to `False` and restart your Nautobot services.

#### Deprecation Warnings Silenced by Default ([#2798](https://github.com/nautobot/nautobot/pull/2798))

+/- 1.5.2

Deprecation warnings raised by Nautobot itself (such as warnings about upcoming breaking changes in a future release) are no longer logged as `WARNING` log messages by default, but can be enabled by setting the `NAUTOBOT_LOG_DEPRECATION_WARNINGS` environment variable to `True` in your configuration. More information is available under [Optional Settings](../user-guide/administration/configuration/optional-settings.md#nautobot_log_deprecation_warnings).

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
## v1.5.24 (2023-07-24)

### Fixed

- [#3312](https://github.com/nautobot/nautobot/issues/3312) - Fixed custom fields not auto-populating when creating objects through the ORM.
- [#4127](https://github.com/nautobot/nautobot/issues/4127) - Fixed JavaScript error with 'Check Secret' button introduced in the previous patch release.

### Security

- [#4126](https://github.com/nautobot/nautobot/issues/4126) - Updated `cryptography` to `41.0.2` due to CVE-2023-38325. As this is not a direct dependency of Nautobot, it will not auto-update when upgrading. Please be sure to upgrade your local environment.

## v1.5.23 (2023-07-10)

### Added

- [#3235](https://github.com/nautobot/nautobot/issues/3235) - Added a warning notifying users when the requested `per_page` on a list page exceeds the `MAX_PAGE_SIZE` set.
- [#3937](https://github.com/nautobot/nautobot/issues/3937) - Added a Nautobot 2.0 pre-migration management command aptly named `pre_migrate`.

### Changed

- [#1854](https://github.com/nautobot/nautobot/issues/1854) - When sorting tables for MPTT models, nesting/indentation of the model name display is disabled as it was misleading.
- [#1854](https://github.com/nautobot/nautobot/issues/1854) - Disabled sorting on TreeNode model tables as TreeNode do not support sorting.
- [#4049](https://github.com/nautobot/nautobot/issues/4049) - Restructured non-production dependencies in `pyproject.toml` to comply with latest Poetry expectations.
- [#4050](https://github.com/nautobot/nautobot/issues/4050) - Added `develop-1.6` to list of target branches to run changelog step in pull request CI workflow.

### Dependencies

- [#4049](https://github.com/nautobot/nautobot/issues/4049) - Updated development-only dependencies for documentation rendering: `mkdocstrings` 0.22.0, `mkdocstrings-python` 1.1.2, and `griffe` 0.30.1.
- [#4064](https://github.com/nautobot/nautobot/issues/4064) - Updated `Django` to `3.2.20` to address `CVE-2023-36053`.

### Fixed

- [#2374](https://github.com/nautobot/nautobot/issues/2374) - Revised documentation for recommended parameters to use when running `nautobot-server dumpdata`.
- [#2374](https://github.com/nautobot/nautobot/issues/2374) - Revised documentation around preparing to run `nautobot-server loaddata`.
- [#2374](https://github.com/nautobot/nautobot/issues/2374) - Added documentation to run `nautobot-server trace_paths` after `nautobot-server loaddata`.
- [#2374](https://github.com/nautobot/nautobot/issues/2374) - Fixed a signal handler that could cause `nautobot-server loaddata` to abort if certain data is present.
- [#3109](https://github.com/nautobot/nautobot/issues/3109) - Fixed missing trailing slash in NautobotUIViewSet urls.
- [#3422](https://github.com/nautobot/nautobot/issues/3422) - Fixed postgres database healthcheck error message in development environment.
- [#3524](https://github.com/nautobot/nautobot/issues/3524) - Fixed the unhandled exception brought on by updating Rack to a new site with a similar device sharing the same name and tenant by catching error in 'RackForm.clean`.
- [#4021](https://github.com/nautobot/nautobot/issues/4021) - Fixed erroneous warning banner on list views when `MAX_PAGE_SIZE` is set to zero.
- [#4048](https://github.com/nautobot/nautobot/issues/4048) - Fixed broken tab navigation in secrets.

### Security

- [#4064](https://github.com/nautobot/nautobot/issues/4064) - Updated `Django` to `3.2.20` to address `CVE-2023-36053`.

## v1.5.22 (2023-06-26)

### Added

- [#3534](https://github.com/nautobot/nautobot/issues/3534) - Added optional args and kwargs to `BaseModel.validated_save()` that pass through to the model's `save` method.
- [#3946](https://github.com/nautobot/nautobot/issues/3946) - Added warning note to job scheduling documentation for the attributes that can prevent scheduling.

### Fixed

- [#3534](https://github.com/nautobot/nautobot/issues/3534) - Fixed confusing unit test failure message when trying to run a non-existent test.
- [#3534](https://github.com/nautobot/nautobot/issues/3534) - Fixed unit tests sometimes clearing out the default database.
- [#3658](https://github.com/nautobot/nautobot/issues/3658) - Fixed a typo in the success message when removing a child Device from a Device Bay.
- [#3739](https://github.com/nautobot/nautobot/issues/3739) - Fixed change log entries not being created for some long running requests.
- [#3891](https://github.com/nautobot/nautobot/issues/3891) - Fixed a bug preventing Job buttons from supporting the `FORCE_SCRIPT_NAME` setting due to hard-coded URLs.
- [#3924](https://github.com/nautobot/nautobot/issues/3924) - Fixed a potential server hang at startup when a misconfigured GitRepository is present.
- [#3948](https://github.com/nautobot/nautobot/issues/3948) - Fixed device name copy button adding an extra space/return.
- [#3987](https://github.com/nautobot/nautobot/issues/3987) - Fixed issue where download SVG download did not actually download.

### Security

- [#3796](https://github.com/nautobot/nautobot/issues/3796) - Updated `requests` to 2.31.0 to address CVE-2023-32681. This is a development dependency and will not auto-update when upgrading Nautobot. Please be sure to update your local environment.
- [#3843](https://github.com/nautobot/nautobot/issues/3843) - Updated `cryptography` to 41.0.0 due to a statically linked version of OpenSSL which contained vulnerability CVE-2023-2650. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

## v1.5.21 (2023-06-12)

### Added

- [#3806](https://github.com/nautobot/nautobot/issues/3806) - Added instructions and examples for SAML SSO using Okta as the IdP.
- [#3811](https://github.com/nautobot/nautobot/issues/3811) - Added a note that addresses UWSGI buffer size concerns with Azure SSO in `nautobot/docs/user-guide/administration/configuration/authentication/sso.md`.
- [#3897](https://github.com/nautobot/nautobot/issues/3897) - Adds log message when a secrets group for a git repository doesn't yield a token.

### Changed

- [#3888](https://github.com/nautobot/nautobot/issues/3888) - Changed note for celery concurrency in the docs.

### Fixed

- [#3809](https://github.com/nautobot/nautobot/issues/3809) - Fixed a bug that prevented  `__init__()` function of `bulk_create_form_class` being overridden in NautobotUIViewSet.
- [#3882](https://github.com/nautobot/nautobot/issues/3882) - Removed deprecated distutils dependency.

## v1.5.20 (2023-05-30)

### Added

- [#3400](https://github.com/nautobot/nautobot/issues/3400) - Added documentation on how to enable Jobs and Job hooks.
- [#3766](https://github.com/nautobot/nautobot/issues/3766) - Add troubleshooting steps for Azure AD SSO Group Sync example.

### Changed

- [#3680](https://github.com/nautobot/nautobot/issues/3680) - Changed device component instantiation to be a separate method.

### Fixed

- [#3503](https://github.com/nautobot/nautobot/issues/3503) - Fixed FieldError when sorting VMs list by primary IP.
- [#3616](https://github.com/nautobot/nautobot/issues/3616) - Fixed `location` filter on `CircuitFilterSet` and `ProviderFilterSet`.
- [#3787](https://github.com/nautobot/nautobot/issues/3787) - Fixed MySQL `Out of sort memory` error on `JobListView` and `JobResultListView`.
- [#3789](https://github.com/nautobot/nautobot/issues/3789) - Fixed Exception `unsupported operand type(s) for -: 'list' and 'list'` for MultiObjectVar with missing UUID.

## v1.5.19 (2023-05-16)

### Added

- [#3695](https://github.com/nautobot/nautobot/issues/3695) - Added note to documentation about using `{{ obj.cf }}` to access custom fields in jinja templates.

### Changed

- [#3617](https://github.com/nautobot/nautobot/issues/3617) - SearchForms on Nautobot homepage now redirect users to login page when they are not authenticated.
- [#3663](https://github.com/nautobot/nautobot/issues/3663) - Modified `delete_button` and `edit_button` template tags to lookup `pk` and `slug` without the need to specify the lookup key.
- [#3703](https://github.com/nautobot/nautobot/issues/3703) - Added generic views documentation to navigation panel.

### Dependencies

- [#3549](https://github.com/nautobot/nautobot/issues/3549) - Updated `django` to `~3.2.19` to address `CVE-2023-31047`.
- [#3549](https://github.com/nautobot/nautobot/issues/3549) - Updated `mkdocs` to `~1.4.3`.
- [#3549](https://github.com/nautobot/nautobot/issues/3549) - Updated `psycopg2-binary` to `~2.9.6`.
- [#3698](https://github.com/nautobot/nautobot/issues/3698) - Updated `social-auth-core` to `~4.4.0` to permit addressing `CVE-2022-2309`.
- [#3753](https://github.com/nautobot/nautobot/issues/3753) - Updated indirect dev dependency `pymdown-extensions` to `10.0` to address `CVE-2023-32309`.

### Fixed

- [#3704](https://github.com/nautobot/nautobot/issues/3704) - Fixed GitRepository fetching on Home Page when getting repo-based Job's name.
- [#3726](https://github.com/nautobot/nautobot/issues/3726) - Fixed a `KeyError` when filtering Cables in the UI by `termination_a_type` or `termination_b_type`.

### Security

- [#3698](https://github.com/nautobot/nautobot/issues/3698) - Updated `lxml` to `~4.9.2` to address `CVE-2022-2309`. This is not a direct dependency so it will not auto-update when upgrading Nautobot. Please be sure to update your local environment.
- [#3724](https://github.com/nautobot/nautobot/issues/3724) - Updated `django` to `~3.2.19` due to `CVE-2023-31047`.
- [#3753](https://github.com/nautobot/nautobot/issues/3753) - Updated indirect dev dependency `pymdown-extensions` to `10.0` to address `CVE-2023-32309`. This should not be installed in a production environment by default but should be updated if you have installed it.

## v1.5.18 (2023-05-01)

### Added

- [#1526](https://github.com/nautobot/nautobot/issues/1526) - Added UI button and REST API to validate a `Secret` can be retrieved.
- [#3669](https://github.com/nautobot/nautobot/issues/3669) - Added indexes to `JobResult` across common fields: `created`, `completed`, and `status`.

### Changed

- [#2800](https://github.com/nautobot/nautobot/issues/2800) - Add model documentation to navigation panel.
- [#3440](https://github.com/nautobot/nautobot/issues/3440) - Added warning admonitions for Job Hooks and Job Approvals documentation that setting `Meta.approval_required` is ignored on `JobHookReceiver` classes.
- [#3602](https://github.com/nautobot/nautobot/issues/3602) - Updated `.gitignore` to not track new UI non-source files.
- [#3621](https://github.com/nautobot/nautobot/issues/3621) - Changed development Docker compose commands to not leave temporary containers behind.
- [#3633](https://github.com/nautobot/nautobot/issues/3633) - Changed Custom Validator applicator to not require DB query.

### Fixed

- [#3083](https://github.com/nautobot/nautobot/issues/3083) - Fixed an issue where unit tests might fail erroneously when dealing with objects whose name/display contains characters like `"<>`.
- [#3533](https://github.com/nautobot/nautobot/issues/3533) - Fixed an issue where sending a PATCH to `/api/dcim/interfaces/(uuid)/` might inadvertently reset the interface's status to `Active`.
- [#3533](https://github.com/nautobot/nautobot/issues/3533) - Fixed an issue where sending a PATCH to `/api/users/tokens/(uuid)/` might inadvertently change the token's value.
- [#3612](https://github.com/nautobot/nautobot/issues/3612) - Fixed a 500 error when filtering by `content_type` in Dynamic Groups list view.
- [#3660](https://github.com/nautobot/nautobot/issues/3660) - Fixed an issue where grouped job buttons would always be disabled due to a template rendering issue.

### Security

- [#3642](https://github.com/nautobot/nautobot/issues/3642) - Updated `sqlparse` to `0.4.4` due to CVE-2023-30608. This is not a direct dependency so it will not auto-update when upgrading Nautobot. Please be sure to update your local environment.

## v1.5.17 (2023-04-17)

### Added

- [#3484](https://github.com/nautobot/nautobot/issues/3484) - Added job profiling option to job execution when in DEBUG mode.
- [#3544](https://github.com/nautobot/nautobot/issues/3544) - Added the ability to change the `CACHES["default"]["BACKEND"]` via an environment variable `NAUTOBOT_CACHES_BACKEND`

### Changed

- [#3544](https://github.com/nautobot/nautobot/issues/3544) - The default database backend if `METRICS_ENABLED` is `True` is now "django_prometheus.db.backends.postgresql"
- [#3544](https://github.com/nautobot/nautobot/issues/3544) - The default CACHES backend if `METRICS_ENABLED` is `True` is now "django_prometheus.cache.backends.redis.RedisCache"
- [#3548](https://github.com/nautobot/nautobot/issues/3548) - Changed Git Repository docs to include admonition about Github Apps.
- [#3595](https://github.com/nautobot/nautobot/issues/3595) - Update the warning provided when a bad reverse entry is not found in serializer to point to correct import location.

### Dependencies

- [#3525](https://github.com/nautobot/nautobot/issues/3525) - Added explicit dependency on `packaging` that had been inadvertently omitted.

### Fixed

- [#3116](https://github.com/nautobot/nautobot/issues/3116) - Fixed JSON comparison of `data_scheme` keys in `assertInstanceEqual` tests.
- [#3573](https://github.com/nautobot/nautobot/issues/3573) - Fixed advanced filtering on interface UI list page not working.
- [#3577](https://github.com/nautobot/nautobot/issues/3577) - Fixed `NautobotUIViewSet` documentation example for case sensitive typos.
- [#3577](https://github.com/nautobot/nautobot/issues/3577) - Fixed `NautobotUIViewSet` documentation example not including imports.
- [#3598](https://github.com/nautobot/nautobot/issues/3598) - Fixed default sanitizer patterns to account for strings beginning with `i` or `is`.

## v1.5.16 (2023-04-10)

### Added

- [#3557](https://github.com/nautobot/nautobot/issues/3557) - Added docs page for Circuit Maintenance.

### Fixed

- [#2944](https://github.com/nautobot/nautobot/issues/2944) - Fixed slow performance of relationships on ObjectListView.
- [#3345](https://github.com/nautobot/nautobot/issues/3345) - Fixed missing Relationships in DynamicFilterForm.
- [#3477](https://github.com/nautobot/nautobot/issues/3477) - Added a note under heading Setting ViewSet Attributes to mention the caveat of not using `slug` or `pk`.
- [#3502](https://github.com/nautobot/nautobot/issues/3502) - Updated upstream workflow to support testing apps `next-2.0` branches against `next`.
- [#3550](https://github.com/nautobot/nautobot/issues/3550) - Fixed display name of filtered relationships on ObjectListView.

## v1.5.15 (2023-04-04)

### Added

- [#3446](https://github.com/nautobot/nautobot/issues/3446) - Added documentation links for Device Onboarding and LifeCycle Management plugins to docs.nautobot.com menu.

### Changed

- [#3384](https://github.com/nautobot/nautobot/issues/3384) - Moved extra information stored previously in `block sidebar` to `block header_extra` in page templates (`aggregate_list.html` and `objectchange_list.html`).
- [#3384](https://github.com/nautobot/nautobot/issues/3384) - Documented `block header_extra` in `docs/development/templates.md`.

### Dependencies

- [#3499](https://github.com/nautobot/nautobot/issues/3499) - Updated `redis` to 4.5.4. This is not a direct dependency of Nautobot so it will not auto-update when upgrading. Please update your local environment as needed.

### Fixed

- [#3206](https://github.com/nautobot/nautobot/issues/3206) - Fixed Docker tag syntax on prerelease workflow.
- [#3480](https://github.com/nautobot/nautobot/issues/3480) - Fixed an error that could be seen in certain cases with IPAddress records.

### Removed

- [#3384](https://github.com/nautobot/nautobot/issues/3384) - Removed all remaining instances of `block sidebar` from page templates (`aggregate_list.html` and `objectchange_list.html`).
- [#3384](https://github.com/nautobot/nautobot/issues/3384) - Removed documentation about `block sidebar` from `docs/development/templates.md`.

### Security

- [#3499](https://github.com/nautobot/nautobot/issues/3499) - Updated `redis` to 4.5.4 due to CVE-2023-28858 and CVE-2023-28859. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

## v1.5.14 (2023-03-20)

### Added

- [#2618](https://github.com/nautobot/nautobot/issues/2618) - Added the ability to stand up a local dev env for SSO using Keycloak.
- [#3033](https://github.com/nautobot/nautobot/issues/3033) - Added `JobButton` model to create single click execution buttons in the web UI to run jobs based on a single object.
- [#3377](https://github.com/nautobot/nautobot/issues/3377) - Added additional choices for many data types in `nautobot.dcim`.

### Changed

- [#3434](https://github.com/nautobot/nautobot/issues/3434) - Changed the recommended exception to raise to end jobs early.

### Fixed

- [#3419](https://github.com/nautobot/nautobot/issues/3419) - Fixed `test_queryset_to_csv` to format data fetched from the model.

## v1.5.13 (2023-03-14)

### Added

- [#766](https://github.com/nautobot/nautobot/issues/766) - Added option for apps to extend Nautobot's Prometheus metrics, based on `nautobot_capacity_metrics`.
- [#3410](https://github.com/nautobot/nautobot/issues/3410) - Added `-time` index for ObjectChange records.

### Changed

- [#3410](https://github.com/nautobot/nautobot/issues/3410) - Changed Homepage ObjectChange query to not join User or Content Type tables, use record cache for user entries instead.
- [#3416](https://github.com/nautobot/nautobot/issues/3416) - Updated Windows development documentation.

### Dependencies

- [#3405](https://github.com/nautobot/nautobot/issues/3405) - Updated version of `pyopenssl` in Nautobot dev environment and Docker images to 23.0.0 due to an incompatibility between older versions of `pyopenssl` and version 39.x of `cryptography`. This is not a direct dependency of Nautobot so it will not auto-update when upgrading. Please update your local environment as needed.
- [#3405](https://github.com/nautobot/nautobot/issues/3405) - Updated `cryptography` to 39.0.2. This is not a direct dependency of Nautobot so it will not auto-update when upgrading. Please update your local environment as needed.

### Fixed

- [#3347](https://github.com/nautobot/nautobot/issues/3347) - Fixed (again) `Location.parent` not populating correctly in the form when editing an existing Location.

### Removed

- [#3407](https://github.com/nautobot/nautobot/issues/3407) - Removed permission checks for ContentTypeAPIViewSet.

## v1.5.12 (2023-03-03)

### Added

- [#3182](https://github.com/nautobot/nautobot/issues/3182) - Added support for assigning Config Context objects via Dynamic Groups.
- [#3219](https://github.com/nautobot/nautobot/issues/3219) - Added support for custom fields to Dynamic Groups.
- [#3220](https://github.com/nautobot/nautobot/issues/3220) - Added support for relationships to Dynamic Groups.

### Changed

- [#3369](https://github.com/nautobot/nautobot/issues/3369) - Changed `RelationshipModelFilterSetMixin` to perform a single OR query including `select_related` for `source_type` and `destination_type` vs. two single queries for each source/destination types.

### Dependencies

- [#3388](https://github.com/nautobot/nautobot/issues/3388) - Updated `GitPython` to 3.1.31.
- [#3388](https://github.com/nautobot/nautobot/issues/3388) - Updated `drf-yasg` to 1.21.5. Note: this is automatic for the Nautobot-provided containers, but because our dependency on it goes away in 2.0, it's an optional update for other installations.
- [#3388](https://github.com/nautobot/nautobot/issues/3388) - Updated `netutils` to 1.4.1.

### Fixed

- [#3295](https://github.com/nautobot/nautobot/issues/3295) - Fixed kombu serialization error on `User` object that arose when `CELERY_RESULT_EXTENDED == True` or when `enqueue_job` was called from within an existing `Job`.
- [#3318](https://github.com/nautobot/nautobot/issues/3318) - Fixed a bug in prefix factory when a /0 ipv6 network is generated by faker.
- [#3341](https://github.com/nautobot/nautobot/issues/3341) - Fixed missing `get_route_for_model()` logic for the `ContentType` and `Group` models.
- [#3353](https://github.com/nautobot/nautobot/issues/3353) - Fixed a bug in `nautobot.extras.forms.mixins.CustomFieldModelFilterFormMixin` where the list of custom field names were not being stored on `self.custom_fields`.
- [#3353](https://github.com/nautobot/nautobot/issues/3353) - Fixed a bug in `nautobot.utilities.filters.MappedPredicatesFilterMixin` (from which `SearchFilter` inherits) that was preventing `q` fields from being used in Dynamic Group filters.

## v1.5.11 (2023-02-18)

### Added

- [#3168](https://github.com/nautobot/nautobot/issues/3168) - Add device name to bulk interface rename header.
- [#3184](https://github.com/nautobot/nautobot/issues/3184) - Added Git 2.0+ as a mandatory dependency in the installation instructions.
- [#3255](https://github.com/nautobot/nautobot/issues/3255) - Added `--cache-test-fixtures` command line argument to Nautobot unit and integration tests.

### Changed

- [#3134](https://github.com/nautobot/nautobot/issues/3134) - Migrate ModelMultipleChoiceFilters to NaturalKeyOrPKMultipleChoiceFilter.
- [#3224](https://github.com/nautobot/nautobot/issues/3224) - Updates to our deprecation policy: Prior-major REST API versions will be dropped upon next-major release.
- [#3264](https://github.com/nautobot/nautobot/issues/3264) - Changed `DynamicGroup.objects.get_for_object()` to be a little more efficient.
- [#3311](https://github.com/nautobot/nautobot/issues/3311) - Add Links to Branch Names to README.md.
- [#3314](https://github.com/nautobot/nautobot/issues/3314) - Updated developer documentation for user and prototype branching conventions.
- [#3314](https://github.com/nautobot/nautobot/issues/3314) - Updated pre-commit hook to validate user namespace prefix on branch name.

### Dependencies

- [#3251](https://github.com/nautobot/nautobot/issues/3251) - Updated `oauthlib` to 3.2.2.
- [#3258](https://github.com/nautobot/nautobot/issues/3258) - Updated `cryptography` to 39.0.1.
- [#3320](https://github.com/nautobot/nautobot/issues/3320) - Updated `django` to 3.2.18.
- [#3333](https://github.com/nautobot/nautobot/issues/3333) - Updated `netutils` constraint from ~1.4.0 to ^1.4.0 to permit semver upgrades.

### Fixed

- [#2580](https://github.com/nautobot/nautobot/issues/2580) - Fixed fragile generic view test.
- [#3187](https://github.com/nautobot/nautobot/issues/3187) - Fixed `DynamicModelChoiceField`s having a generic default label when one is provided.
- [#3274](https://github.com/nautobot/nautobot/issues/3274) - Fixed ObjectListViewMixin's filtering when exporting objects in NautobotUIViewSet.
- [#3277](https://github.com/nautobot/nautobot/issues/3277) - Fixed incorrect test data in `nautobot.extras.tests.test_api.NoteTest`.
- [#3278](https://github.com/nautobot/nautobot/issues/3278) - Fixed docker development environment error when the Nautobot container tries to start before the database is ready.
- [#3290](https://github.com/nautobot/nautobot/issues/3290) - Fixed an issue preventing the inclusion of `netutils` functions in Django templates.
- [#3308](https://github.com/nautobot/nautobot/issues/3308) - Fixed incorrect documentation for object permissions.
- [#3327](https://github.com/nautobot/nautobot/issues/3327) - Fixed Azure AD tenant configuration documentation.
- [#3332](https://github.com/nautobot/nautobot/issues/3332) - Fixed missing imports in Secrets Providers plugin development documentation.
- [#3335](https://github.com/nautobot/nautobot/issues/3335) - Fixed inability to change filtering on custom field (selection) once filter is configured.

### Security

- [#3251](https://github.com/nautobot/nautobot/issues/3251) - Updated `oauthlib` to 3.2.2 due to CVE-2022-36087. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#3258](https://github.com/nautobot/nautobot/issues/3258) - Updated `cryptography` to 39.0.1 due to CVE-2023-0286, CVE-2023-23931. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#3320](https://github.com/nautobot/nautobot/issues/3320) - Updated `django` to 3.2.18 due to CVE-2023-24580.

## v1.5.10 (2023-02-06)

### Added

- [#3013](https://github.com/nautobot/nautobot/issues/3013) - Added `CELERY_WORKER_PROMETHEUS_PORTS` configuration setting
- [#3013](https://github.com/nautobot/nautobot/issues/3013) - Added prometheus HTTP server listening on the worker to expose worker metrics
- [#3013](https://github.com/nautobot/nautobot/issues/3013) - Added `nautobot_job_duration_seconds` counter metric that reports on job execution

### Changed

- [#3177](https://github.com/nautobot/nautobot/issues/3177) - Updated VLANFactory to generate longer and more "realistic" VLAN names.
- [#3198](https://github.com/nautobot/nautobot/issues/3198) - Added dependencies towncrier section, removed extra newline.

### Dependencies

- [#3227](https://github.com/nautobot/nautobot/issues/3227) - Updated `django` to 3.2.17.

### Fixed

- [#3126](https://github.com/nautobot/nautobot/issues/3126) - Fixed interface not raising exception when adding a VLAN from a different site in tagged_vlans.
- [#3153](https://github.com/nautobot/nautobot/issues/3153) - Made integration test `CableConnectFormTestCase.test_js_functionality` more resilient and less prone to erroneous failures.
- [#3177](https://github.com/nautobot/nautobot/issues/3177) - Fixed a spurious failure in BulkEditObjectsViewTestCase.test_bulk_edit_objects_with_constrained_permission.
- [#3200](https://github.com/nautobot/nautobot/issues/3200) - Added `dependencies` to the list of valid change fragment types in the documentation.

### Security

- [#3227](https://github.com/nautobot/nautobot/issues/3227) - Updated `django` to 3.2.17 due to CVE-2023-23969.

## v1.5.9 (2023-01-26)

### Changed

- [#3117](https://github.com/nautobot/nautobot/issues/3117) - Update Renovate config to batch lockfile updates to next.
- [#3144](https://github.com/nautobot/nautobot/issues/3144) - Updated `netutils` to `~1.4.0`
- [#3171](https://github.com/nautobot/nautobot/issues/3171) - Increased maximum VLAN name length from 64 characters to 255 characters.

### Fixed

- [#3114](https://github.com/nautobot/nautobot/issues/3114) - Fixed Navbar scroll through top-level menu in low resolution desktop screens.
- [#3155](https://github.com/nautobot/nautobot/issues/3155) - Aligned buttons on device component create page.
- [#3169](https://github.com/nautobot/nautobot/issues/3169) - Fixed data mismatch in `ScheduledJob` causing celery workers to fail when running scheduled jobs created in versions prior to `v1.5.8`. ⚠ **NOTE**: If your celery workers are failing on startup after upgrading to `v1.5.8`, you may need to purge the celery queue with `nautobot-server celery purge` or `nautobot-server celery purge -Q <queues>` to purge custom queues.

## v1.5.8 (2023-01-23)

### Added

- [#3103](https://github.com/nautobot/nautobot/issues/3103) - Added Redis troubleshooting section to installation docs.

### Changed

- [#3072](https://github.com/nautobot/nautobot/issues/3072) - In Nautobot's unit tests, all HTTP requests are now sent with SERVER_NAME set to `nautobot.example.com` instead of `testserver` (Django's default) and the test configuration for Nautobot itself sets `ALLOWED_HOSTS` to expect `nautobot.example.com`. This is intended to protect against issues such as #3065.
- [#3077](https://github.com/nautobot/nautobot/issues/3077) - Updated Nautobot release checklist to reflect current branching and pull request process.
- [#3112](https://github.com/nautobot/nautobot/issues/3112) - Converted eligible `prefetch_related()` to `select_related()` queries. Users should note a performance gain from this change, but note that cacheops is no longer recommended in v1.5 and this change will likely result in invalid data responses if cacheops remains enabled in your environment. Cacheops will be removed entirely in a future release.
- [#3121](https://github.com/nautobot/nautobot/issues/3121) - Updated Config Contexts documentation to denote support for associating by Device Redundancy Group membership.

### Fixed

- [#2244](https://github.com/nautobot/nautobot/issues/2244) - Fixed an unnecessary and sometimes problematic database access from the Celery worker before it forks off to execute an individual job.
- [#3097](https://github.com/nautobot/nautobot/issues/3097) - Fixed scrolling past select dropdown in modals.
- [#3104](https://github.com/nautobot/nautobot/issues/3104) - Fixed bug preventing filters from being removed from list views.

### Security

- [#3055](https://github.com/nautobot/nautobot/issues/3055) - Updated `setuptools` to `65.5.1` to address `CVE-2022-40897`. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#3082](https://github.com/nautobot/nautobot/issues/3082) - Updated `gitpython` to `~3.1.30` to address `CVE-2022-24439`.
- [#3119](https://github.com/nautobot/nautobot/issues/3119) - Updated `future` to `0.18.3` due to `CVE-2022-40899`. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

## v1.5.7 (2023-01-04)

### Fixed

- [#3065](https://github.com/nautobot/nautobot/issues/3065) - Rolled back the changes made in 1.5.6 by #3016 to fix a breaking issue with `ALLOWED_HOSTS` and change-logging.

### Security

- [#3074](https://github.com/nautobot/nautobot/issues/3074) - Sandboxed rendering of Jinja2 templates is now enforced by default in keeping with [Jinja2 best practices](https://jinja.palletsprojects.com/en/3.0.x/sandbox/#sandbox). To enable template sandboxing in a Nautobot instance without needing to upgrade, add the following value to your `nautobot_config.py` and restart your Nautobot services: `TEMPLATES[1]["OPTIONS"]["environment"] = "jinja2.sandbox.SandboxedEnvironment"`

## v1.5.6 (2022-12-23)

### Added

- [#1768](https://github.com/nautobot/nautobot/issues/1768) - Added the display of half-depth rack items from the rear face.
- [#2481](https://github.com/nautobot/nautobot/issues/2481) - Added `clone_fields` definition to Custom Field class.
- [#2511](https://github.com/nautobot/nautobot/issues/2511) - Added mouseover help text for cable connect buttons on DeviceConsolePortTable, DeviceConsoleServerPortTable, DevicePowerPortTable, DeviceInterfaceTable, DeviceFrontPortTable, DeviceRearPortTable.
- [#2951](https://github.com/nautobot/nautobot/issues/2951) - Added change logging when relationships are changed.
- [#2966](https://github.com/nautobot/nautobot/issues/2966) - Added device name to rack elevation with images.
- [#3014](https://github.com/nautobot/nautobot/issues/3014) - Added support for Git repositories to provide config contexts filtered by Location.
- [#3025](https://github.com/nautobot/nautobot/issues/3025) - Added plugin banner test back to ListObjectsViewTestCase and ensured `example_plugin` installation before running it.

### Changed

- [#2589](https://github.com/nautobot/nautobot/issues/2589) - Updated all screenshots on the README.md to gifs.
- [#2970](https://github.com/nautobot/nautobot/issues/2970) - Updated `certifi` to `2022.12.7` for `CVE-2022-23491`. This is a nested dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#2994](https://github.com/nautobot/nautobot/issues/2994) - Updated `mkdocs-material` to `8.5.11`.
- [#2995](https://github.com/nautobot/nautobot/issues/2995) - Updated `Poetry` lockfile to use new v2 version format (requiring `Poetry>=1.3`).
- [#2995](https://github.com/nautobot/nautobot/issues/2995) - Updated included `poetry` version in `nautobot-dev` container to `1.3.1`.

### Fixed

- [#2898](https://github.com/nautobot/nautobot/issues/2898) - Disabled sorting on Computed Field column.
- [#2967](https://github.com/nautobot/nautobot/issues/2967) - Fixed inverted device images in dark mode.
- [#2989](https://github.com/nautobot/nautobot/issues/2989) - Fixed legacy filters displaying UUIDs instead of user-friendly display names.
- [#2999](https://github.com/nautobot/nautobot/issues/2999) - Fixed several missing fields in the UI when bulk-adding components to a list of devices.
- [#3018](https://github.com/nautobot/nautobot/issues/3018) - Fixed rendering of Select2 widgets in modal dialogs.
- [#3028](https://github.com/nautobot/nautobot/issues/3028) - Fixed filter fields on advanced filter form not being alpha-sorted.
- [#3036](https://github.com/nautobot/nautobot/issues/3036) - Fixed MultiValueUUIDFilter's value input field in ObjectListView Advanced FilterSet Form.

## v1.5.5 (2022-12-12)

### Changed

- [#2663](https://github.com/nautobot/nautobot/issues/2663) - Changed `tags` field in ConfigContextForm to `DynamicModelMultipleChoiceField`.

### Fixed

- [#2948](https://github.com/nautobot/nautobot/issues/2948) - Fixed incorrect assumption in test base that `example_plugin` would always be installed.
- [#2962](https://github.com/nautobot/nautobot/issues/2962) - Fixed an error raised when logging errors about a `Secret` with an invalid `provider`.
- [#2963](https://github.com/nautobot/nautobot/issues/2963) - Fixed 500 error when combining filtering on relationships with concrete fields.

## v1.5.4 (2022-12-02)

### Added

- [#86](https://github.com/nautobot/nautobot/issues/86) - Added user-guide for relationships and S3 storage backends.

### Fixed

- [#2154](https://github.com/nautobot/nautobot/issues/2154) - Fixed SwaggerUI use of Authorization Token, API calls in SwaggerUI now use appropriate token pattern and curl command match the correct pattern.
- [#2931](https://github.com/nautobot/nautobot/issues/2931) - Fixed title and breadcrumb rendering in NautobotUIViewSet list views.
- [#2936](https://github.com/nautobot/nautobot/issues/2936) - Fixed NautobotUIViewSet views not being able to delete objects.

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
