<!-- markdownlint-disable MD024 -->

# Nautobot v1.5

This document describes all new features and changes in Nautobot 1.5.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Required Relationships ([#873](https://github.com/nautobot/nautobot/issues/873))

Relationships can be marked as being required. By default, relationships are not marked as being required.

To mark a relationship as being required, select "Source objects MUST implement this relationship" or conversely "
Destination objects MUST implement this relationship" from the "Required on" field when editing or creating a
relationship:

* If "Destination objects MUST implement this relationship" is selected, objects of the type selected in "Destination Type" will enforce this relationship when they are created or edited.
* If "Source objects MUST implement this relationship" is selected, objects of the type selected in "Source Type" will enforce this relationship when they are created or edited.

#### Custom Celery Task Queues

A new optional job property `task_queues` has been introduced to allow Nautobot to leverage custom celery queues for jobs. This will allow you to send jobs to specific workers based on which queue is selected. This property can be set on the job class and overridden in the Job model, similar to other overridable job fields. If `task_queues` is not defined on the job class or Job model, the job will only be able to use the default queue. A new field has been added to the job run form to allow you to select a queue when you run the job and  an optional field `task_queue` has been added to the REST API [job run endpoint](../additional-features/jobs.md#via-the-api) for the same purpose.

!!! important
    The default celery queue name has been changed from `celery` to `default`. If you have any workers or tasks hard coded to use `celery` you will need to update those workers/tasks or change the [`CELERY_TASK_DEFAULT_QUEUE`](../configuration/optional-settings.md#celery_task_default_queue) setting in your `nautobot_config.py`.

#### Nestable LocationTypes ([#2608](https://github.com/nautobot/nautobot/issues/2608))

`LocationType` definitions can now be flagged as `nestable`. When this flag is set, Locations of this type may nest within one another, similar to how Regions work at present. This allows you to have a variable-depth hierarchy of Locations, for example:

* Main Campus ("Building Group" location type)
    * West Campus (Building Group)
        * Building A ("Building" location type)
        * Building B (Building)
    * East Campus (Building Group)
        * Building C (Building)
        * Building D (Building)
    * South Campus (Building Group)
        * Western South Campus (Building Group)
            * Building G (Building)
* Satellite Campus (Building Group)
    * Building Z (Building)

In the above example, only two LocationTypes are defined ("Building Group" and "Building") but the "Building Group" type is flagged as nestable, so one Building Group may contain another Building Group.

### Changed

#### Database Query Caching is now Disabled by Default

In prior versions of Nautobot, database query caching using the [`django-cacheops`](https://github.com/Suor/django-cacheops) application (aka Cacheops) was enabled by default. This is determined by the default value of the [`CACHEOPS_ENABLED`](../configuration/optional-settings.md#cacheops_enabled) setting being set to `True`.

Through much trial and error we ultimately decided that this feature is more trouble than it is worth and we have begun to put more emphasis on improving performance of complex database queries over continuing to rely upon the various benefits and pitfalls of utilizing Cacheops.

As a result, the value of this setting now defaults to `False`, disabling database query caching entirely for new deployments. Cacheops will be removed entirely in a future release.

!!! important
    Users with existing `nautobot_config.py` files generated from earlier versions of Nautobot will still have `CACHEOPS_ENABLED = True` unless they modify or regenerate their configuration. If users no longer desire caching, please be sure to explicitly toggle the value of this setting to `False` and restart your Nautobot services.

#### Redesigned List Filtering UI

Added a dynamic filter form that allows users to filter object tables/lists by any field and lookup expression combination supported by the corresponding FilterSet and API.

### Fixed

### Removed

<!-- towncrier release notes start -->
