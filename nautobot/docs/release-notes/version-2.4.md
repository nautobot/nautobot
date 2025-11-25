# Nautobot v2.4

This document describes all new features and changes in Nautobot 2.4.

## Upgrade Actions

### Administrators

- Nautobot 2.4 [drops support for Python 3.8](#removed-python-38-support), so any existing Nautobot deployment using Python 3.8 will need upgrade to a newer Python version **before** upgrading to Nautobot v2.4 or later.
- Administrators should familiarize themselves with the new [Event Publication Framework](#event-publication-framework) and the possibilities it enables for improved monitoring of Nautobot operations and integration with distributed automation platforms.
- Administrators of Kubernetes-based Nautobot deployments should familiarize themselves with the new [capabilities](#kubernetes-job-execution-and-job-queue-data-model-experimental) that Nautobot v2.4 provides for Job execution in such environments and may wish to update their Nautobot configuration to take advantage of these capabilities. Please note that this feature set is considered Experimental in v2.4.0 and is subject to change in future releases.
- Nautobot 2.4 includes an About page which is capable of displaying the status of Network to Code support contracts, dictated by the [`NTC_SUPPORT_CONTRACT_EXPIRATION_DATE`](../user-guide/administration/configuration/settings.md#ntc_support_contract_expiration_date) configuration setting.

### Job Authors & App Developers

- App developers should begin to adopt the [UI Component Framework](#ui-component-framework) introduced in Nautobot v2.4, as this will reduce the amount of boilerplate HTML/CSS content that they need to develop and maintain, and will help insulate Apps from future CSS and layout design changes planned for Nautobot v3.
- Additionally, App developers should familiarize themselves with the new [Event Publication Framework](#event-publication-framework) and the possibilities it enables for Apps to publish their own relevant events to configured message brokers.
- As a side benefit of adding [REST API `exclude_m2m` support](#rest-api-exclude_m2m-support), the Nautobot REST API `ViewSet` classes now attempt to intelligently apply `select_related()` and/or `prefetch_related()` optimizations to the `queryset` associated to a given REST API viewset. Apps defining their own REST API viewsets (and requiring Nautobot v2.4.0 or later) can typically remove most explicit calls to `select_related()` and `prefetch_related()`; furthermore, in order to benefit most from the `exclude_m2m=true` query parameter, apps in Nautobot v2.4.0 and later **should not** explicitly `prefetch_related()` many-to-many related fields any longer. (Explicit calls to `select_related()` and `prefetch_related()` may still be necessary and appropriate if your API serializer needs to perform nested lookups, as the automatic optimization here currently only understands directly related object lookups.)
- Job authors should be aware of the ability to log [`success`](#job-success-log-level) messages in Nautobot v2.4.0 and later and should adopt this log level as appropriate.
- Job authors should be aware of the introduction of [Job Queues](#kubernetes-job-execution-and-job-queue-data-model-experimental) as a general-purpose replacement for the Celery-specific `Job.task_queues` attribute, and if a Job specifies its preferred `task_queues`, should verify that the queue selected as its `default_job_queue` after the Nautobot upgrade is correct.

## Release Overview

### Added

#### Virtual Device Context Data Models

Nautobot 2.4 adds a [`VirtualDeviceContext`](../user-guide/core-data-model/dcim/virtualdevicecontext.md) data model to support modeling of logical partitions of physical network devices, such as Cisco Nexus Virtual Device Contexts, Juniper Logical Systems, Arista Multi-instance EOS, and so forth. Device Interfaces can be associated to Virtual Device Contexts via the new `InterfaceVDCAssignment` model as well.

#### Wireless Data Models

Nautobot 2.4 adds the data models [`WirelessNetwork`](../user-guide/core-data-model/wireless/wirelessnetwork.md), [`RadioProfile`](../user-guide/core-data-model/wireless/radioprofile.md), and [`SupportedDataRate`](../user-guide/core-data-model/wireless/supporteddatarate.md), enabling Nautobot to model campus wireless networks. In support of this functionality, the [`Controller`](../user-guide/core-data-model/dcim/controller.md) and [`ControllerManagedDeviceGroup`](../user-guide/core-data-model/dcim/controllermanageddevicegroup.md) models have been enhanced with additional capabilities as well.

Refer to the [Wireless](../user-guide/core-data-model/wireless/index.md) documentation for more details.

#### Apps Marketplace Page and Installed Apps Page Tile View

Nautobot v2.4 introduces the Apps Marketplace, containing information about available Nautobot Apps. In addition to that, the Installed Apps page has added a tile-view option, similar to the Apps Marketplace.

#### Event Publication Framework

Nautobot now includes a general-purpose, extensible [event publication framework](../user-guide/platform-functionality/events.md) for publication of event notifications to other systems such as Redis publish/subscribe, Kafka, syslog, and others. An abstract `EventBroker` API can be implemented and extended with system-specific functionality to enable publication of Nautobot events to any desired message broker.

As of v2.4.0, Nautobot publishes events with the following topics:

Data model manipulation:
- `nautobot.create.<app>.<model>`
- `nautobot.update.<app>.<model>`
- `nautobot.delete.<app>.<model>`

User interaction:
- `nautobot.users.user.login`
- `nautobot.users.user.logout`
- `nautobot.users.user.change_password`
- `nautobot.admin.user.change_password`

Jobs:
- `nautobot.jobs.job.started`
- `nautobot.jobs.job.completed`
- `nautobot.jobs.approval.approved`
- `nautobot.jobs.approval.denied`

The payload of each topic is a data representaton of the corresponding event, such as the object created, or the Job that started execution. Events are published to configured event brokers, and may be filtered.

Nautobot Apps can also make use of this framework to publish additional event topics, specific to the App's functionality as desired.

#### Jinja2 Template Rendering Tool

Nautobot v2.4 adds a new tool to render Jinja2 templates directly from the UI. Users may supply their own template body and context data to be rendered, with access to to Nautobot's built-in Jinja2 tags and filters. Additionally, a new REST API endpoint `/api/core/render-jinja-template/` has been added to achieve the same functionaly. This can be used by users and Apps such as [Nautobot Golden Config](https://docs.nautobot.com/projects/golden-config/en/latest/) to assist with the development and validation of Jinja2 template content. This functionality will be extended in the future to more easily access context aware data in Nautobot such as Devices and Config Contexts.

#### Job `success` Log Level

Jobs can now log `success` messages as a new logging level which will be appropriately labeled and colorized in Job Result views.

```python
self.logger.success("All data is valid.")
```

+++ 2.4.5

In Nautobot v2.4.5 and later, Jobs can now log `failure` messages as well:

```python
self.logger.failure("Something went wrong.")
```

In Nautobot v2.4.5 and later, Jobs can also mark their result as failed without raising an uncaught exception by calling the new `Job.fail(message)` API:

```python
self.fail("Something went wrong, and we'll fail in the end, but we can continue for now.")
self.logger.info("Continuing...")
```

#### Kubernetes Job Execution and Job Queue Data Model (Experimental)

*Please note that this functionality is considered Experimental in the v2.4.0 release and is subject to change in the future.*

When running in a Kubernetes (k8s) deployment, such as with Nautobot's [Helm chart](https://docs.nautobot.com/projects/helm-charts/en/stable/), Nautobot now supports an alternative method of running Nautobot Jobs - instead of (or in addition to) running one or more Celery Workers as long-lived persistent pods, Nautobot can dispatch Nautobot Jobs to be executed as short-lived [Kubernetes Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/) pods.

In support of this functionality, Nautobot now supports the definition of [`JobQueue` records](../user-guide/platform-functionality/jobs/jobqueue.md), which represent either a Celery task queue **or** a Kubernetes Job queue. Nautobot Jobs can be associated to queues of either or both types, and the Job Queue selected when submitting a Job will dictate whether it is executed via Celery or via Kubernetes.

Nautobot Jobs support the same feature sets, regardless if they are executed on Celery Job queues or Kubernetes Job queues.

Refer to the [Jobs documentation](../user-guide/platform-functionality/jobs/index.md) for more details.

#### Singleton Jobs

Job authors can now set their jobs to only allow a single concurrent execution across all workers, preventing mistakes where, e.g., data synchronization jobs accidentally run twice and create multiple instances of the same data. This functionality and the corresponding setting are documented in [the section on developing Jobs](../development/jobs/index.md).

#### Per-user Time Zone Support

Users can now configure their preferred display time zone via the User Preferences UI under their user profile and Nautobot will display dates and times in the configured time zone for each user.

#### REST API `exclude_m2m` Support

Added REST API support for an `?exclude_m2m=true` query parameter. Specifying this parameter prevents the API from retrieving and serializing many-to-many relations on the requested object(s) (for example, the list of all Prefixes associated with a given VRF), which can in some cases greatly improve the performance of the API and reduce memory and network overhead substantially.

A future Nautobot major release may change the REST API behavior to make `exclude_m2m=true` the default behavior.

Additionally, the `DynamicModelChoiceField` and related form fields have been enhanced to use `exclude_m2m=true` when querying the REST API to populate their options, which can in some cases significantly improve the responsiveness of these fields.

#### UI Component Framework

Nautobot's new [UI Component Framework](../development/core/ui-component-framework.md) provides a set of Python APIs for defining parts of the Nautobot UI without needing, in many cases, to write custom HTML templates. In v2.4.0, the focus is primarily on the definition of object "detail" views as those were the most common cases where custom templates have been required in the past.

[Adoption of this framework](../development/apps/migration/ui-component-framework/index.md) significantly reduces the amount of boilerplate needed to define an object detail view, drives increased self-consistency across views, and encourages code reuse. It also insulates Apps from the details of Nautobot's CSS and layout (Bootstrap 3 framework), smoothing the way for Nautobot to adopt UI changes in the future with minimal impact to compliant apps.

App [template extensions](../development/apps/api/ui-extensions/object-views.md)--which are used to inject App content into Nautobot Core views--offer new implementation patterns using the UI Component Framework and it is highly recomended that App developers take this opportunity to adopt, as old methods have been deprecated in some cases (see below).

As of Nautobot 2.4.0, the following detail views have been migrated to use the UI Component Framework, and any app template extensions targeting these models should adopt:

- Circuit
- Cluster Type
- Device ("Add Components" buttons only)
- External Integration
- Location Type
- Provider
- Route Target
- Secret
- Tenant
- VRF

### Deprecated

#### `FilterTestCases.NameOnlyFilterTestCase` and `FilterTestCases.NameSlugFilterTestCase`

These two generic base test classes are deprecated. Apps should migrate to using `FilterTestCases.FilterTestCase` with an appropriately defined list of `generic_filter_tests` instead.

#### Job `task_queues` and `ScheduledJob.queue`

The `Job.task_queues` field (a list of queue name strings) is deprecated in favor of the new `Job.job_queues` relationship to the [`JobQueue` model](../user-guide/platform-functionality/jobs/jobqueue.md). `task_queues` is still readable and settable for backward compatibility purposes but code using this attribute should migrate to using `job_queues` instead.

Similarly, `ScheduledJob.queue` is deprecated in favor of `ScheduledJob.job_queue`.

#### `TemplateExtension.detail_tabs()`, `TemplateExtension.left_page()` and others

With the introduction of the UI Component Framework (described [above](#ui-component-framework)), new APIs are available for Apps to extend core Nautobot views with additional content using this framework. A number of new APIs have been added to the `TemplateExtension` base class in support of this functionality, and several existing `TemplateExtension` APIs have been deprecated in favor of these new APIs. Refer to the [App development documentation](../development/apps/api/ui-extensions/object-views.md) for details.

### Dependencies

#### Removed Python 3.8 Support

As Python 3.8 has reached end-of-life, Nautobot 2.4 requires a minimum of Python 3.9, and Nautobot 2.4.6 and later specifically require a minimum of Python 3.9.2. Note that existing installs using older Python versions will need to upgrade their Python version prior to initiating the Nautobot v2.4 upgrade.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->

## v2.4.23 (2025-11-24)

### Added in v2.4.23

- [#1629](https://github.com/nautobot/nautobot/issues/1629) - Added additional Celery worker metrics.

### Fixed in v2.4.23

- [#7848](https://github.com/nautobot/nautobot/issues/7848) - Fixed the Logs Cleanup job to skip records with a protected relationship instead of raising an error.
- [#8025](https://github.com/nautobot/nautobot/issues/8025) - Fixed a `KeyError` when viewing a record with a symmetric one-to-one `Relationship` defined.
- [#8164](https://github.com/nautobot/nautobot/issues/8164) - Fixed insertion order of middleware for `nautobot.core.settings_funcs.setup_structlog_logging`.
- [#8178](https://github.com/nautobot/nautobot/issues/8178) - Fixed "Create and Add Another" behavior for UIViewSet-derived views.
- [#8202](https://github.com/nautobot/nautobot/issues/8202) - Fixed Bulk operations when using Saved View and selecting all.

### Documentation in v2.4.23

- [#1629](https://github.com/nautobot/nautobot/issues/1629) - Updated prometheus metrics documentation.

### Housekeeping in v2.4.23

- [#8162](https://github.com/nautobot/nautobot/issues/8162) - Updated GitHub Actions definitions for ltm-2.4 branch.

## v2.4.22 (2025-11-10)

### Security in v2.4.22

- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated dependency `Django` to `~4.2.26` to mitigate CVE-2025-64459.

### Added in v2.4.22

- [#6979](https://github.com/nautobot/nautobot/issues/6979) - Added support for speed and duplex on `Interface` objects.
- [#8048](https://github.com/nautobot/nautobot/issues/8048) - Added Constance configuration setting `RACK_DEFAULT_U_HEIGHT` to configure the default height (in rack units) displayed in the Rack creation form.
- [#8135](https://github.com/nautobot/nautobot/issues/8135) - Added `get_detail_view_components_context_for_model()` helper API for use by apps implementing DistinctViewTabs.

### Changed in v2.4.22

- [#6979](https://github.com/nautobot/nautobot/issues/6979) - Changed the `humanize_speed` template filter to now return a decimalized value instead of finding an integer value (e.g. 2.5 Gbps instead of 2500 Mbps).

### Fixed in v2.4.22

- [#6852](https://github.com/nautobot/nautobot/issues/6852) - Fixed unintended dependency on `django-debug-toolbar` when enabling the `theme-preview/` view.
- [#8039](https://github.com/nautobot/nautobot/issues/8039) - Fixed issue where device components added via table footer button did not return to the same page.
- [#8042](https://github.com/nautobot/nautobot/issues/8042) - Fixed incorrect `base_template` on Git Repository Synchronization Status page.
- [#8059](https://github.com/nautobot/nautobot/issues/8059) - Fixed the Wireless Networks tab on the Controller detail page.
- [#8073](https://github.com/nautobot/nautobot/issues/8073) - Added missing call to `super().get_extra_context()` in `LocationUIViewSet`, `ModuleTypeUIViewSet`.
- [#8077](https://github.com/nautobot/nautobot/issues/8077) - Fixed the rendering of the min and max version fields in the App detail view when they are not set.
- [#8126](https://github.com/nautobot/nautobot/issues/8126) - Fixed incorrect permissions requirement to view Virtual Machine config context tab.
- [#8126](https://github.com/nautobot/nautobot/issues/8126) - Fixed incorrect field name in Config Context filter form.
- [#8126](https://github.com/nautobot/nautobot/issues/8126) - Fixed leftover use of legacy views in Relationship "notes" and "changelog" tabs.

### Dependencies in v2.4.22

- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated dependency `django-constance` to `~4.3.3`.
- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated dependency `nh3` to `~0.3.2`.

### Documentation in v2.4.22

- [#8068](https://github.com/nautobot/nautobot/issues/8068) - Updated documentation to include information about the latest deprecated HTML templates in v3.0.

### Housekeeping in v2.4.22

- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated documentation dependency `mkdocs-glightbox` to `~0.5.2`.
- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated documentation dependency `mkdocs-macros-plugin` to `~1.4.1`.
- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated documentation dependency `mkdocs-material` to `~9.6.23`.
- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated development dependency `pymarkdownlnt` to `~0.9.33`.
- [#7981](https://github.com/nautobot/nautobot/issues/7981) - Updated development dependency `ruff` to `~0.14.3`.
- [#8047](https://github.com/nautobot/nautobot/issues/8047) - Fixed incorrect logic in `nautobot.virtualization.tests.test_models.VMInterfaceTestCase` that could lead to test failures.
- [#8068](https://github.com/nautobot/nautobot/issues/8068) - Updated deprecated HTML templates migration script to handle more cases.
- [#8113](https://github.com/nautobot/nautobot/issues/8113) - Fixed live reloading when serving development documentation with mkdocs.
- [#8114](https://github.com/nautobot/nautobot/issues/8114) - Set `INSTALLATION_METRICS_ENABLED=False` explicitly in the testing `nautobot_config.py` to avoid inadvertently sending metrics when running tests.

## v2.4.21 (2025-10-27)

### Added in v2.4.21

- [#7282](https://github.com/nautobot/nautobot/issues/7282) - Added individual and bulk delete methods to the `/extras/scheduled-jobs/` API endpoint.
- [#7834](https://github.com/nautobot/nautobot/issues/7834) - Added `Refresh Dynamic Group Members Cache` system Job Button Receiver; a corresponding Job Button for Dynamic Groups will be automatically created after running `nautobot-server post_upgrade`.
- [#7834](https://github.com/nautobot/nautobot/issues/7834) - Added `update_cached_members` optional parameter to `DynamicGroup.save()` and `DynamicGroupMembership.save()` methods, which can be set to `False` to defer the potentially costly synchronous (re)calculation of the group members at save time. This parameter presently defaults to `True` for backwards compatibility reasons, but may change to a default of `False` in a future major release.
- [#7996](https://github.com/nautobot/nautobot/issues/7996) - Added a script to help app developers migrate deprecated HTML templates to the new ones.

### Changed in v2.4.21

- [#7834](https://github.com/nautobot/nautobot/issues/7834) - Changed UI behavior when creating/editing Dynamic Groups to no longer synchronously (re)calculate the members of the group on form submission, as this could cause page timeouts when a large number of members need to be added or removed. This functionality is replaced by a Job Button on the detail view that can be clicked to asynchronously refresh the members cache on demand instead.
- [#7834](https://github.com/nautobot/nautobot/issues/7834) - Changed UI behavior when rendering a Dynamic Group detail view to no longer synchronously (re)calculate the members of the group at render time, as this could cause page timeouts when a large number of members need to be added or removed. This functionality is replaced by a Job Button that can be clicked to asynchronously refresh the members cache on demand instead.

### Fixed in v2.4.21

- [#5379](https://github.com/nautobot/nautobot/issues/5379) - Fixed exception when filtering Location Types by associated Content Types.
- [#5638](https://github.com/nautobot/nautobot/issues/5638) - Added missing logic to allow mapping model names to feature names for all FilterSets.
- [#7728](https://github.com/nautobot/nautobot/issues/7728) - Fixed bug in which `m2m_changed` signals were not being sent when adding IPs to interfaces.
- [#7952](https://github.com/nautobot/nautobot/issues/7952) - Fixed changelog list view not working when there was data referencing `ContentTypes` in the database but not installed.
- [#7955](https://github.com/nautobot/nautobot/issues/7955) - Fixed custom `ancestors` method in tree queries to forgo tree fields, yielding performance improvements in checking for loops in the tree structure.
- [#7955](https://github.com/nautobot/nautobot/issues/7955) - Fixed `invalidate_max_depth_cache` signal to forgo cache invalidation when a TreeModel has siblings.
- [#7958](https://github.com/nautobot/nautobot/issues/7958) - Fixed title & breadcrumbs rendering on Git Repositories - Synchronization Status view
- [#7987](https://github.com/nautobot/nautobot/issues/7987) - Fixed filtering of select- and multiselect-type custom fields in Dynamic Groups.
- [#7988](https://github.com/nautobot/nautobot/issues/7988) - Fixed device detail object view failing when a power poert is connected to a power outlet.

### Dependencies in v2.4.21

- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated dependency `django-cors-headers` to `~4.9.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated dependency `django-tree-queries` to `~0.21.2`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated dependency `emoji` to `~2.15.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated dependency `prometheus-client` to `~0.23.1`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated dependency `social-auth-core` to `~4.8.1`.
- [#8030](https://github.com/nautobot/nautobot/issues/8030) - Updated dependency `cryptography` to `~46.0.3`.
- [#8030](https://github.com/nautobot/nautobot/issues/8030) - Updated dependency `django-structlog` to `~10.0.0`.
- [#8030](https://github.com/nautobot/nautobot/issues/8030) - Updated dependency `Pillow` to `~12.0.0`.

### Documentation in v2.4.21

- [#7968](https://github.com/nautobot/nautobot/issues/7968) - Add a note for how to retrieve computed fields in an Export Template.

### Housekeeping in v2.4.21

- [#2288](https://github.com/nautobot/nautobot/issues/2288) - Added `docs` step to pull request CI to validate that Nautobot docs build successfully and contain valid hyperlinks.
- [#7530](https://github.com/nautobot/nautobot/issues/7530) - Refactored Location model related UI views to use `UI component framework`.
- [#7661](https://github.com/nautobot/nautobot/issues/7661) - Refactored GraphQLQuery model related UI views to use `UI component framework`.
- [#7972](https://github.com/nautobot/nautobot/issues/7972) - Updated Renovate configuration to open separate PRs for NPM dependency updates versus Python dependency updates.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `django-test-migrations` to `~1.5.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `faker` to `^37.11.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `invoke` to `2.2.1`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `rich` to `~14.2.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `ruff` to `~0.14.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `selenium` to `~4.36.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `time-machine` to `~2.19.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated development dependency `towncrier` to `~25.8.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated documentation dependency `mkdocs-glightbox` to `~0.5.1`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated documentation dependency `mkdocs-macros-plugin` to `~1.4.0`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated documentation dependency `mkdocs-material` to `~9.6.22`.
- [#7973](https://github.com/nautobot/nautobot/issues/7973) - Updated documentation dependency `mkdocstrings-python` to `~1.18.2`.
- [#7977](https://github.com/nautobot/nautobot/issues/7977) - Restored tagging of `latest` Docker images inadvertently untagged in 2.4.20.
- [#8022](https://github.com/nautobot/nautobot/issues/8022) - Added support for `.breaking` change fragments and corresponding "Breaking Changes" section in release-notes.

## v2.4.20 (2025-10-14)

### Security in v2.4.20

- [#7908](https://github.com/nautobot/nautobot/issues/7908) - Updated dependency `Django` to `~4.2.25` to mitigate CVE-2025-59681 and CVE-2025-59682.
- [#7949](https://github.com/nautobot/nautobot/issues/7949) - Patched logic in `social-auth-app-django` to prevent account takeover vulnerability risk from CVE-2025-61783 until we can upgrade to a version of `social-auth-app-django` that includes the fix (5.6.0 or later).
- [#7950](https://github.com/nautobot/nautobot/issues/7950) - Updated dependency `python-ldap` to `3.4.5` to mitigate CVE-2025-61911 and CVE-2025-61912. As this is not a direct dependency, it will not auto-update when upgrading; please be sure to upgrade your local environment.

### Added in v2.4.20

- [#7914](https://github.com/nautobot/nautobot/issues/7914) - Added a link to the module detail view from the module list view.

### Changed in v2.4.20

- [#7892](https://github.com/nautobot/nautobot/issues/7892) - Removed unnecessary and error-prone cache logic from the `PathEndpoint.connected_endpoint` property.

### Fixed in v2.4.20

- [#7859](https://github.com/nautobot/nautobot/issues/7859) - Fixed timezone management in Scheduled Job detail page.
- [#7907](https://github.com/nautobot/nautobot/issues/7907) - Fixed exclude filtering of text-type custom fields in UI/API Filters and Dynamic Groups.
- [#7907](https://github.com/nautobot/nautobot/issues/7907) - Fixed exact filtering by null values for custom fields.
- [#7914](https://github.com/nautobot/nautobot/issues/7914) - Fixed interface filtering on `VirtualMachine` and `Device` detail views.
- [#7914](https://github.com/nautobot/nautobot/issues/7914) - Fixed `DeviceType` add components views to correctly add the `DeviceType` to form.
- [#7919](https://github.com/nautobot/nautobot/issues/7919) - Fixed bulk action buttons missing from Device/DeviceType tabs.
- [#7920](https://github.com/nautobot/nautobot/issues/7920) - Fixed various bespoke buttons from not showing up on tabs.

### Dependencies in v2.4.20

- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated dependency `celery` to `~5.5.3` and removed explicit direct dependency on `kombu` as a side effect.
- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated dependency `djangorestframework` to `~3.16.1`.
- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated dependency `nh3` to `~0.3.1`.
- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated dependency `psycopg2-binary` to `~2.9.11`.
- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated dependency `PyYAML` to `~6.0.3`.
- [#7915](https://github.com/nautobot/nautobot/issues/7915) - Dropped support for Python 3.9. Python 3.10 is now the minimum version required by Nautobot.

### Documentation in v2.4.20

- [#7891](https://github.com/nautobot/nautobot/issues/7891) - Fixed a dead link to the Django documentation.

### Housekeeping in v2.4.20

- [#7262](https://github.com/nautobot/nautobot/issues/7262) - Refactored Cable model related UI views to use `NautobotUIViewSet`.
- [#7836](https://github.com/nautobot/nautobot/issues/7836) - Fixed the test `ControllerTestCase.test_controller_bulk_edit` from failing on a race condition.
- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated documentation dependency `mkdocs-material` to `~9.6.21`.
- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated development dependency `djhtml` to `~3.0.10`.
- [#7870](https://github.com/nautobot/nautobot/issues/7870) - Updated development dependency `pylint` to `~3.3.9`.
- [#7885](https://github.com/nautobot/nautobot/issues/7885) - Removed documentation dependency `mkdocs-include-markdown-plugin` as older versions have a security vulnerability and Nautobot core hasn't actually needed this dependency since v2.0.
- [#7901](https://github.com/nautobot/nautobot/issues/7901) - Fixed `invoke djhtml` task not working correctly in Docker compose.
- [#7929](https://github.com/nautobot/nautobot/issues/7929) - Fixed autogenerated release note entries failing markdownlint due to a whitespace issue.
- [#7930](https://github.com/nautobot/nautobot/issues/7930) - Enhanced the `release` GitHub Actions workflow to include prereleases and removed outdated `prerelease` workflow.
- [#7930](https://github.com/nautobot/nautobot/issues/7930) - Removed requirement of (re)running the `ci_integration` workflow as a part of the `release` workflow.
- [#7932](https://github.com/nautobot/nautobot/issues/7932) - Added better logging when a form raises a `NotImplementedError`.

## v2.4.19 (2025-09-29)

### Added in v2.4.19

- [#7471](https://github.com/nautobot/nautobot/issues/7471) - Added support for `distinct` optional parameter when defining an `ObjectsTablePanel` UI component.
- [#7809](https://github.com/nautobot/nautobot/issues/7809) - Added `description` filter for the VRF and IPAddress models.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Added support for disabling a `DistinctViewTab` without hiding it by providing a `disabled_message` in the render context.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Added support for `hide_if_empty` optional parameter on `DistinctViewTab`.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Added support for optional `required_permissions` on all `Component` subclasses to hide components when the user lacks appropriate permissions.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Added special-case support for rendering a related Cluster (including its Cluster Group) and related Rack (including its Rack Group) in `KeyValueTablePanel`.
- [#7862](https://github.com/nautobot/nautobot/issues/7862) - Added support for `Button.render_on_tab_id` parameter to scope UI Component buttons to a specific view tab.
- [#7862](https://github.com/nautobot/nautobot/issues/7862) - Added `should_render_content()` API to `Tab` and `DistinctViewTab` to avoid rendering tab contents unnecessarily when a different tab or set of tabs is displayed.

### Changed in v2.4.19

- [#7471](https://github.com/nautobot/nautobot/issues/7471) - Changed UI `ObjectsTablePanel` to only apply `.distinct()` to queries when explicitly requested, instead of unconditionally. Improves performance of rendering these tables in most cases.
- [#7471](https://github.com/nautobot/nautobot/issues/7471) - Changed `DeviceType` detail view to apply proper ordering to the table of related `SoftwareImageFile` records.
- [#7606](https://github.com/nautobot/nautobot/issues/7606) - Changed "Side A" and "Side Z" column in circuit table to show shorter `location.name` instead of `location.display`.
- [#7809](https://github.com/nautobot/nautobot/issues/7809) - Changed the jobs `BulkDeleteObjects` and `BulkEditObjects` to be hidden by default.
- [#7821](https://github.com/nautobot/nautobot/issues/7821) - Changed the maximum allowed value for rack height from 100 to 500.
- [#7844](https://github.com/nautobot/nautobot/issues/7844) - Implemented UI Component Framework `breadcrumbs` for core views that were previously using `extra_breadcrumbs` template block overrides.
- [#7844](https://github.com/nautobot/nautobot/issues/7844) - Refactored `JobResultUIViewSet` to use UI Component Framework `breadcrumbs`.
- [#7849](https://github.com/nautobot/nautobot/issues/7849) - Changed the form field `software_version` on `SoftwareImageFileForm` form to be a dynamic dropdown.
- [#7849](https://github.com/nautobot/nautobot/issues/7849) - Changed the form field `platform` on `SoftwareVersionForm` form to be a dynamic dropdown.

### Fixed in v2.4.19

- [#7651](https://github.com/nautobot/nautobot/issues/7651) - Improved GraphQL query performance when querying many-to-many and many-to-one related objects such as `{ tenant_groups { tenants { name }}}`.
- [#7763](https://github.com/nautobot/nautobot/issues/7763) - Fixed an intermittent test failure for `test_anonymous_user_get_shared_views_only`.
- [#7809](https://github.com/nautobot/nautobot/issues/7809) - Fixed bulk object edit and bulk delete not considering filtering of saved views.
- [#7809](https://github.com/nautobot/nautobot/issues/7809) - Fixed buttons on bulk views not adhering to the "all" toggle.
- [#7809](https://github.com/nautobot/nautobot/issues/7809) - Fixed circular import error by lazy importing job based classes into core views.
- [#7810](https://github.com/nautobot/nautobot/issues/7810) - Improved performance for device detail view by avoiding to calculate the location tree more often than needed.
- [#7812](https://github.com/nautobot/nautobot/issues/7812) - Fixed prefix/circuit count for location detail view stats panel.
- [#7818](https://github.com/nautobot/nautobot/issues/7818) - Fixed incorrect closing HTML tag in `body_content_data_table.html`.
- [#7818](https://github.com/nautobot/nautobot/issues/7818) - Added call to `mark_safe()` on rendered HTML captured by `captureas` template-tag.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Fixed rendering of table-panel footers when both `footer_buttons` and a `body_content_table_add_url` are defined.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Fixed incorrect URL paths for actions under `DeviceType`, for example `/dcim/device-types/<pk>/consoleports/` is now corrected to `/dcim/device-types/<pk>/console-ports/`.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Enhanced `NautobotUIViewSetMixin` to correctly set the `active_tab` when rendering a detail action other than the default `"retrieve"`.
- [#7833](https://github.com/nautobot/nautobot/issues/7833) - Fixed an exception when rendering an object detail view with no corresponding list view.
- [#7835](https://github.com/nautobot/nautobot/issues/7835) - Fixed an MRO error in generic views by consistently placing `UIComponentsMixin` at the beginning of base classes.
- [#7855](https://github.com/nautobot/nautobot/issues/7855) - Fixed NoteUIViewSet to correctly populate `user` and `user_name` fields on Note creation.
- [#7858](https://github.com/nautobot/nautobot/issues/7858) - Fixed the `InstanceBreadcrumbsItem` and `InstanceParentBreadcrumbsItem` to not format label with title-casing.
- [#7858](https://github.com/nautobot/nautobot/issues/7858) - Fixed the Breadcrumbs Items classes to not format label with title-casing for custom labels.
- [#7863](https://github.com/nautobot/nautobot/issues/7863) - Fixed a circular-import issue seen in some Apps following #7825.
- [#7877](https://github.com/nautobot/nautobot/issues/7877) - Fixed an error in rendering the Device detail view when the device has a controller-managed device group with null `capabilities`.
- [#7877](https://github.com/nautobot/nautobot/issues/7877) - Fixed inability to specify null `capabilities` when editing a Controller or Controller Managed Device Group via the REST API.

### Documentation in v2.4.19

- [#7845](https://github.com/nautobot/nautobot/issues/7845) - Documented options for controlling Celery worker prefetching behavior in the "Task Queues" guide.

### Housekeeping in v2.4.19

- [#7627](https://github.com/nautobot/nautobot/issues/7627) - Refactored ObjectChange model related UI views to use `NautobotUIViewSet`.
- [#7794](https://github.com/nautobot/nautobot/issues/7794) - Refactored Prefix model related UI views to use `UI component framework` and `NautobotUIViewSet`.
- [#7797](https://github.com/nautobot/nautobot/issues/7797) - Updated documentation dependency `mkdocs-material` to `~9.6.20`.
- [#7797](https://github.com/nautobot/nautobot/issues/7797) - Updated documentation dependency `mkdocstrings` to `~0.30.1`.
- [#7797](https://github.com/nautobot/nautobot/issues/7797) - Updated development dependency `djhtml` to `>=3.0.9,<4.0.0`.
- [#7810](https://github.com/nautobot/nautobot/issues/7810) - Added CTE query count tracking to GetObjectViewTestCase test cases to keep track of and minimize the query count.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Refactored Device model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#7825](https://github.com/nautobot/nautobot/issues/7825) - Refactored VirtualMachine model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#7854](https://github.com/nautobot/nautobot/issues/7854) - Add DjHTML and djLint to the project and run it against all Django template files. Include this additional check in pre-commit script and pull request CI workflow.
- [#7864](https://github.com/nautobot/nautobot/issues/7864) - Updated the recursive query failure message for the `GetObjectViewTestCase.test_get_object_with_permission` generic test.
- [#7877](https://github.com/nautobot/nautobot/issues/7877) - Updated the `ControllerFactory` and `ControllerManagedDeviceGroupFactory` to potentially create records with a null `capabilities` field.

## v2.4.18 (2025-09-15)

### Security in v2.4.18

- [#7764](https://github.com/nautobot/nautobot/issues/7764) - Updated dependency `Django` to `~4.2.24` to mitigate `CVE-2025-57833`.

### Added in v2.4.18

- [#7614](https://github.com/nautobot/nautobot/issues/7614) - Added Bulk Edit functionality for the DynamicGroup model.
- [#7687](https://github.com/nautobot/nautobot/issues/7687) - Added usage of `{% render_title %}` and `{% render_breadcrumbs %}` in `object_list.html` and `object_retrieve.html` templates.
- [#7727](https://github.com/nautobot/nautobot/issues/7727) - EXPERIMENTAL: Enabled caching of App-generated Prometheus metrics. This is an experimental feature and may be removed or changed in future releases.
- [#7758](https://github.com/nautobot/nautobot/issues/7758) - Added SavedView capability to JobResults model.
- [#7784](https://github.com/nautobot/nautobot/issues/7784) - Added support for `ObjectFieldsPanel(...fields="__all__", additional_fields=[...])` to allow inclusion of properties, reverse relations, nested lookups, and other attributes not normally included in `__all__`.
- [#7784](https://github.com/nautobot/nautobot/issues/7784) - Enhanced `ObjectFieldsPanel` to support nested lookup of object fields, such as `fields=["rack__rack_group"]`.

### Changed in v2.4.18

- [#7687](https://github.com/nautobot/nautobot/issues/7687) - Updated Devices, Prefixes, Plugins, Circuits views to use UI Component Framework Breadcrumbs.
- [#7687](https://github.com/nautobot/nautobot/issues/7687) - Updated `ObjectView` to instantiate default `Breadcrumbs` and `Titles` and pass it in context.
- [#7687](https://github.com/nautobot/nautobot/issues/7687) - Updated `ObjectListView` to instantiate default `Breadcrumbs` and `Titles` and pass it in context along with `verbose_name_plural` and `view_action`.
- [#7784](https://github.com/nautobot/nautobot/issues/7784) - Changed `ObjectFieldsPanel.__init__` behavior to raise an error if `exclude_fields` is specified in combination with any value of `fields` other than `"__all__"`.
- [#7795](https://github.com/nautobot/nautobot/issues/7795) - Changed CircuitTermination UI `Port Speed` and `Upstream Speed` fields back to single field `Speed` with arrows.
- [#7801](https://github.com/nautobot/nautobot/issues/7801) - Updated Breadcrumbs docs and `UIComponentsMixin` order in some classes.

### Fixed in v2.4.18

- [#7330](https://github.com/nautobot/nautobot/issues/7330) - Fixed a `FieldError` exception when sorting tree-model (Location, LocationType, RackGroup, etc.) tables by a custom field column.
- [#7330](https://github.com/nautobot/nautobot/issues/7330) - Fixed removal of list-view filters when reverting the table sorting to default.
- [#7631](https://github.com/nautobot/nautobot/issues/7631) - Fixed duplicate records returned in some cases by `DynamicGroup.update_cached_members()`.
- [#7723](https://github.com/nautobot/nautobot/issues/7723) - Fixed bug in which `Device` objects could be saved when they didn't have to be.
- [#7748](https://github.com/nautobot/nautobot/issues/7748) - Updated `last_run` column in `JobTable` to avoid referencing settings directly inside TemplateColumn. Since `django-tables2` does not include context processors when rendering column templates, using `settings.SHORT_DATETIME_FORMAT` caused lookup errors or pickling issues. Now the required format `settings.SHORT_DATETIME_FORMAT` is passed explicitly via `extra_context`, ensuring correct rendering in both views and table contexts.
- [#7753](https://github.com/nautobot/nautobot/issues/7753) - Fixed a bug in which IPv4 /31 Prefix records might be assigned the wrong `parent` Prefix.
- [#7753](https://github.com/nautobot/nautobot/issues/7753) - Fixed a bug in which IPv6 records such as `::1/128` might be assigned the wrong `parent` Prefix.
- [#7754](https://github.com/nautobot/nautobot/issues/7754) - Fixed issue with `FilterTestCases.test_tenant_group` where the filter query could return the same `TenantGroup` object multiple times.
- [#7765](https://github.com/nautobot/nautobot/issues/7765) - Fixed column ordering issue by disabling `orderable` for `PowerFeedTable.occupied_positions`, `PowerFeedTable.phase_designation`, and `JobResultTable.duration`.
- [#7765](https://github.com/nautobot/nautobot/issues/7765) - Fixed `ObjectMetadataTable.value` column ordering issue by adding missing `order_by` attribute.
- [#7774](https://github.com/nautobot/nautobot/issues/7774) - Fixed incorrect rendering of Nautobot `n` icon in some browsers.
- [#7783](https://github.com/nautobot/nautobot/issues/7783) - Fixed an issue where you could not set the virtual chassis master.
- [#7789](https://github.com/nautobot/nautobot/issues/7789) - Changed certain filter fields to prevent unnecessary SELECT DISTINCT queries.
- [#7803](https://github.com/nautobot/nautobot/issues/7803) - Fixed a regression in the handling of `ObjectFieldsPanel(ignore_nonexistent_fields=True)` introduced by #7784.
- [#7808](https://github.com/nautobot/nautobot/issues/7808) - Fixed double `Notes` or `Change Log` added in title.

### Dependencies in v2.4.18

- [#7764](https://github.com/nautobot/nautobot/issues/7764) - Updated dependency `cryptography` to `~45.0.7`.
- [#7793](https://github.com/nautobot/nautobot/issues/7793) - Updated dependency `django-silk` to `~5.4.3`.

### Documentation in v2.4.18

- [#7787](https://github.com/nautobot/nautobot/issues/7787) - Updated NautobotAppConfig docs to add `searchable_models` link.

### Housekeeping in v2.4.18

- [#7614](https://github.com/nautobot/nautobot/issues/7614) - Refactored DynamicGroup model related UI views to use `NautobotUIViewSet`.
- [#7632](https://github.com/nautobot/nautobot/issues/7632) - Refactored GitRepository model related UI views to use `NautobotUIViewSet`.
- [#7669](https://github.com/nautobot/nautobot/issues/7669) - Refactored Note model related UI views to use `UI component framework`.
- [#7689](https://github.com/nautobot/nautobot/issues/7689) - Refactored CustomField model related UI views to use `UI component framework`.
- [#7700](https://github.com/nautobot/nautobot/issues/7700) - Refactored VirtualChassis model related UI views to use `UI component framework`.
- [#7760](https://github.com/nautobot/nautobot/issues/7760) - Updated Prefix API test to avoid a potential spurious failure.
- [#7764](https://github.com/nautobot/nautobot/issues/7764) - Updated development dependency `ruff` to `~0.12.12`.
- [#7765](https://github.com/nautobot/nautobot/issues/7765) - Added a test to ensure model properties are not orderable.
- [#7767](https://github.com/nautobot/nautobot/issues/7767) - Updated CI workflows and Docker image build to use Poetry 2.1.4.
- [#7778](https://github.com/nautobot/nautobot/issues/7778) - Fixed unintended carry-over of data changes between subsequent subtests in `FilterTestCase.test_q_filter_valid`.
- [#7786](https://github.com/nautobot/nautobot/issues/7786) - Updated ReadTheDocs build to use poetry instead of pip.
- [#7804](https://github.com/nautobot/nautobot/issues/7804) - Changed development docker-compose environment to not start the `selenium` container by default.
- [#7804](https://github.com/nautobot/nautobot/issues/7804) - Changed `invoke tests` to auto-start the `selenium` container as needed when running integration tests.

## v2.4.17 (2025-09-02)

### Security in v2.4.17

- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Removed obsolete package `future` from the `poetry.lock` and hence from the Docker images, eliminating Nautobot's exposure to vulnerability CVE-2025-50817 in that package.

### Added in v2.4.17

- [#3547](https://github.com/nautobot/nautobot/issues/3547) - Added support for using shift+click to select one or more ranges of objects from list views.
- [#6151](https://github.com/nautobot/nautobot/issues/6151) - Added `Check/Fix IPAM Parents` system Job that can be run if IP Address and/or Prefix `parent` values are incorrectly set.
- [#6151](https://github.com/nautobot/nautobot/issues/6151) - Added logic in IPAddress and Prefix detail views to detect an incorrect `parent` value on the record being viewed and display a banner recommending to run the aforementioned system Job if so.
- [#7685](https://github.com/nautobot/nautobot/issues/7685) - Added Jinja2 validation to `ComputedField` model to catch template syntax errors at save time.
- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Added `django_querystring`, copied from `querystring` templatetag in Django 5.1 and above.
- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Added `legacy_querystring`, copied from `querystring` templatetag in Nautobot 2.4 and below.

### Changed in v2.4.17

- [#6151](https://github.com/nautobot/nautobot/issues/6151) - Changed Prefix update logic so that moving a Prefix to a different Namespace now carries along its descendant Prefixes and their associated IP Addresses as well, instead of only carrying along its direct child IP Addresses and leaving behind the other descendants in the original Namespace.
- [#7670](https://github.com/nautobot/nautobot/issues/7670) - Disable default pagination in ObjectsTablePanel.

### Deprecated in v2.4.17

- [#8000](https://github.com/nautobot/nautobot/issues/8000) - Deprecate the `querystring` templatetag as it overlaps with Django 5.1.

### Removed in v2.4.17

- [#6151](https://github.com/nautobot/nautobot/issues/6151) - Removed UI warnings about various combinations of Prefix types (container versus network versus pool) and IP addresses, as time has shown that there are valid use cases for many of these combinations.

### Fixed in v2.4.17

- [#6151](https://github.com/nautobot/nautobot/issues/6151) - Fixed incorrect data after editing a Prefix's `prefix`/`network`/`prefix_length` fields by adding a `clean()` check to detect and block cases where it could result in orphaned IPAddress records.
- [#6151](https://github.com/nautobot/nautobot/issues/6151) - Fixed incorrect data after editing a Prefix's `prefix`/`network`/`prefix_length` fields by adding logic in `save()` to correctly reparent existing child Prefix and IPAddress records.
- [#6151](https://github.com/nautobot/nautobot/issues/6151) - Fixed potential for incorrect data when moving a VRF-associated Prefix between Namespaces by adding a `clean()` check to detect and block this scenario.
- [#7496](https://github.com/nautobot/nautobot/issues/7496) - Fixed issue with removed Prefix column in VLANs table.
- [#7708](https://github.com/nautobot/nautobot/issues/7708) - Hide the 'select all matching query' UI element when the 'select all' checkbox in an object list view is unchecked.
- [#7720](https://github.com/nautobot/nautobot/issues/7720) - Fixed a Django REST Framework warning related to the `power_factor` attribute on a `DecimalField`.

### Dependencies in v2.4.17

- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated dependency `django-constance` to `~4.3.2`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated dependency `prometheus-client` to `~0.22.1`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated dependency `python-slugify` to `~8.0.4`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated dependency `svgwrite` to `~1.4.3`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Regenerated `poetry.lock` to bring latest version of indirect dependencies into the Docker images and development environment.
- [#7715](https://github.com/nautobot/nautobot/issues/7715) - Updated dependency `django-silk` to `~5.4.2`.

### Documentation in v2.4.17

- [#6671](https://github.com/nautobot/nautobot/issues/6671) - Documented different approaches for initial population of data.

### Housekeeping in v2.4.17

- [#7124](https://github.com/nautobot/nautobot/issues/7124) - Fixed developer docker flow when override files drop ancillary containers.
- [#7496](https://github.com/nautobot/nautobot/issues/7496) - Refactored VLAN model related UI views to use `UI component framework`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated development dependency `pylint` to `~3.3.8`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated development dependency `pymarkdownlnt` to `~0.9.32`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated development dependency `ruff` to `~0.12.9`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated documentation dependency `mkdocs-macros-plugin` to `~1.3.9`.
- [#7682](https://github.com/nautobot/nautobot/issues/7682) - Updated documentation dependency `mkdocs-material` to `~9.6.17`.
- [#7703](https://github.com/nautobot/nautobot/issues/7703) - Made sure line endings were consistently Unix-style (`\n` rather than `\r\n`) in project source files.
- [#7715](https://github.com/nautobot/nautobot/issues/7715) - Updated documentation dependency `mkdocs-material` to `9.6.18`.
- [#7715](https://github.com/nautobot/nautobot/issues/7715) - Updated development dependency `faker` to `^37.6.0`.
- [#7715](https://github.com/nautobot/nautobot/issues/7715) - Updated development dependency `ruff` to `~0.12.11`.
- [#7715](https://github.com/nautobot/nautobot/issues/7715) - Updated test dependency `requests` to `~2.32.5`.
- [#7732](https://github.com/nautobot/nautobot/issues/7732) - Added code coverage reporting to pull request CI workflow.
- [#7734](https://github.com/nautobot/nautobot/issues/7734) - Added `--diff` option to `invoke ruff` command.

## v2.4.16 (2025-08-19)

### Fixed in v2.4.16

- [#7699](https://github.com/nautobot/nautobot/issues/7699) - Fixed breakage of the "Apps Marketplace" view in Nautobot v2.4.15.

### Housekeeping in v2.4.16

- [#7643](https://github.com/nautobot/nautobot/issues/7643) - Refactored SecretsGroup model related UI views to use `UI component framework`.

## v2.4.15 (2025-08-18)

### Added in v2.4.15

- [#7315](https://github.com/nautobot/nautobot/issues/7315) - Added Bulk Update functionality for the CustomField model.
- [#7364](https://github.com/nautobot/nautobot/issues/7364) - Added new management command `check_job_approval_status` to detect scheduled jobs and jobs that still require approval. This command helps during upgrade to Nautobot 3.x.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `power_factor` field to PowerPort and PowerPortTemplate models to track the power factor ratio for electrical devices.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `panel_type` and `breaker_position_count` fields to PowerPanel model to specify panel type and total number of breaker positions.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `power_path` field to PowerPanel model to track physical power distribution redundancy path.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `destination_panel` field to PowerFeed model to specify destination panel that receives power from the feed.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `power_path` field to PowerFeed model to track physical power distribution redundancy path.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `breaker_position` and `breaker_pole_count` fields to PowerFeed model to specify circuit breaker position and pole count.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `occupied_positions` and `phase_designation` properties to PowerFeed model to display breaker positions and calculate phase designation.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Added `paginate` and `show_table_config_button` bools to ObjectsTablePanel to provide an option to hide the paginator and configure button UI.
- [#7573](https://github.com/nautobot/nautobot/issues/7573) - Added support for page heading, document title and breadcrumbs in Nautobot UI Framework.
- [#7609](https://github.com/nautobot/nautobot/issues/7609) - Added `context_object_key` optional parameter to the `Button` class.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Added `JobResult.date_started` field, corresponding to the feature enhancement in `django-celery-results` 2.6.0.

### Changed in v2.4.15

- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Changed PowerFeed model validation to enforce mutual exclusivity between cable connections and destination panel connections.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Changed PowerFeed model to validate breaker position conflicts and panel capacity constraints.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Changed PowerFeed rack location validation to use location hierarchy instead of exact location match.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Changed PowerFeed `clone_fields` to include `destination_panel`, `breaker_position`, and `breaker_pole_count` fields.
- [#7613](https://github.com/nautobot/nautobot/issues/7613) - Improved object change list view performance.
- [#7645](https://github.com/nautobot/nautobot/issues/7645) - Implemented custom TreeQuerySet.count method. Note that this impacts all tree models calling count everywhere, but should be transparent.

### Fixed in v2.4.15

- [#6145](https://github.com/nautobot/nautobot/issues/6145) - Fixed a regression in which the `contacts__n`, `dynamic_groups__n`, `role__n`, `status__n`, and `teams__n` filterset filters would not accept multiple values or names, instead only accepting a single UUID.
- [#6748](https://github.com/nautobot/nautobot/issues/6748) - Fixed `PowerPort.get_power_draw()` and `Rack.get_power_utilization()` calculations to use power factor for Watts (W) to volt-amps (VA) conversion.
- [#7084](https://github.com/nautobot/nautobot/issues/7084) - Fixed incorrect labels for negated custom-field filters in object list views.
- [#7321](https://github.com/nautobot/nautobot/issues/7321) - Fixed missing support for "exclude" filters in `ContentTypeFilter`, `ContentTypeChoiceFilter`, and `ContentTypeMultipleChoiceFilter`. This allows filters like `/extras/roles/?content_types__n=ipam.ipaddress` to work properly.
- [#7321](https://github.com/nautobot/nautobot/issues/7321) - Fixed incorrect extended filter types presented for `ContentTypeFilter`, `ContentTypeChoiceFilter`, and `ContentTypeMultipleChoiceFilter`. These filters only support the `__n` filter extension at present, not various character-based extensions like `__ic`, `__nic`, etc.
- [#7511](https://github.com/nautobot/nautobot/issues/7511) - Fixed bug in device detail template where `object.powerports` and `object.poweroutlets` were incorrectly referenced instead of `object.power_ports` and `object.power_outlets`, preventing the Power Utilization panel from being displayed on the device detail page.
- [#7519](https://github.com/nautobot/nautobot/issues/7519) - Hide the actions column in BulkDelete/BulkEdit views supported by NautobotUIViewSet.
- [#7594](https://github.com/nautobot/nautobot/issues/7594) - Fixed a bug in `NoteFilterSet` where the `assigned_object_id` filter did not properly convert values to UUIDs, causing failed lookups when filtering by this field. Now applies a `UUID` preprocessor to ensure correct filtering.
- [#7662](https://github.com/nautobot/nautobot/issues/7662) - Fixed the Children section in `location_retrieve.html` to properly display child locations of the same Location Type (e.g., sites within sites, rooms within rooms).
- [#7663](https://github.com/nautobot/nautobot/issues/7663) - Fixed namespace issues when using bulk edit form was auto setting a bulk edit field based on a filter param that was carried over.

### Dependencies in v2.4.15

- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `cryptography` to `~45.0.6`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated optional dependency `django-auth-ldap` to `~5.2.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-celery-beat` to `~2.7.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-celery-results` to `~2.6.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-cors-headers` to `~4.7.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-extensions` to `~4.1`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-health-check` to `~3.20.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-prometheus` to `~2.4.1`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-redis` to `~6.0.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-silk` to `~5.4.1`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-storages` to `~1.14.6`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-structlog` to `~9.1.1`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-timezone-field` to `~7.1`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `django-tree-queries` to `~0.20.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Widened range of permitted versions for dependency `djangorestframework` to also permit `3.16.x` versions. Note that depending on your environment this may result in either version 3.15.2 or 3.16.1 being installed after upgrading Nautobot.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `drf-spectacular` to `~0.28.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `emoji` to `~2.14.1`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `kubernetes` to `~33.1.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `Markdown` to `~3.8.2`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `nh3` to `~0.3.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Widened range of permitted versions for dependency `Pillow` to permit any `11.x.y` versions.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `prometheus-client` to `~0.22.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated dependency `social-auth-core` to `~4.7.0`.
- [#7672](https://github.com/nautobot/nautobot/issues/7672) - Pinned the Docker image to Debian 12 `bookworm` LTS to prevent unintended upgrades to Debian 13 `trixie`.

### Housekeeping in v2.4.15

- [#7315](https://github.com/nautobot/nautobot/issues/7315) - Refactored CustomField model related UI views to use `NautobotUIViewSet`.
- [#7324](https://github.com/nautobot/nautobot/issues/7324) - Refactored DeviceType model related UI views to use `UI component framework`.
- [#7513](https://github.com/nautobot/nautobot/issues/7513) - Refactored VirtualMachine model related UI views to use `NautobotUIViewSet`.
- [#7519](https://github.com/nautobot/nautobot/issues/7519) - Refactored JobResult model related UI views to use `NautobotUIViewSet`.
- [#7594](https://github.com/nautobot/nautobot/issues/7594) - Refactored Note model related UI views to use `NautobotUIViewSet`.
- [#7648](https://github.com/nautobot/nautobot/issues/7648) - Adjusted Renovate configuration for `develop` and `next`.
- [#7648](https://github.com/nautobot/nautobot/issues/7648) - Added management of `npm` dependencies via Renovate.
- [#7648](https://github.com/nautobot/nautobot/issues/7648) - Added automatic refresh of `poetry.lock` and `package-lock.json` to Renovate configuration.
- [#7654](https://github.com/nautobot/nautobot/issues/7654) - Updated `renovate.json` to newer standards and removed some obsolete configuration thereof.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `django-debug-toolbar` to `~5.2.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `faker` to `^37.5.3`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `rich` to `~14.1.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `ruff` to `~0.12.8` and applied its recommendations.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `selenium` to `~4.34.2`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `tblib` to `~3.1.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `time-machine` to `~2.17.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated development dependency `yamllint` to `~1.37.1`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated documentation dependency `mkdocstrings` to `~0.30.0`.
- [#7655](https://github.com/nautobot/nautobot/issues/7655) - Updated documentation dependency `mkdocstrings-python` to `~1.16.12`.

## v2.4.14 (2025-08-04)

### Added in v2.4.14

- [#7278](https://github.com/nautobot/nautobot/issues/7278) - Added `range_start` and `range_end` parameters for `/api/ipam/prefixes/<id>/available-ips/`. This replaces the use of the `offset` parameter in this particular case.
- [#7479](https://github.com/nautobot/nautobot/issues/7479) - Added Bulk Edit functionality for the SecretsGroup model.
- [#7566](https://github.com/nautobot/nautobot/issues/7566) - Added Eaton and Raritan C39 power outlet type.
- [#7574](https://github.com/nautobot/nautobot/issues/7574) - Added 4 new choices in the Secret Type category of Secret Groups: "Authentication Key", "Authentication Protocol", "Private Key" and "Private Algorithm".
- [#7625](https://github.com/nautobot/nautobot/issues/7625) - Added an index to JobLogEntry to improve performance of Job Result logs.
- [#7633](https://github.com/nautobot/nautobot/issues/7633) - Added support for optional `get_queryset` boolean parameter to `CustomField.objects.get_for_model()`, `ComputedField.objects.get_for_model()`, and `Relationship.objects.get_for_model()` APIs. If set to `False` these APIs will return a (potentially cached) list of records instead of a QuerySet.
- [#7633](https://github.com/nautobot/nautobot/issues/7633) - Added `populate_list_caches()` method to `CustomField.objects`, `ComputedField.objects`, and `Relationship.objects`, which can be called to efficiently populate the caches used by the `get_for_model()` methods when `get_queryset=False` for all content-types.
- [#7633](https://github.com/nautobot/nautobot/issues/7633) - Added `feature_models` dict to the Nautobot registry for more efficient GraphQL schema generation.
- [#7633](https://github.com/nautobot/nautobot/issues/7633) - Added caching of generated search parameters for more efficient GraphQL schema generation.

### Changed in v2.4.14

- [#7601](https://github.com/nautobot/nautobot/issues/7601) - Made network driver mappings dynamically find network driver keys.
- [#7611](https://github.com/nautobot/nautobot/issues/7611) - Added more verbose default output to `nautobot-server migrate` command.

### Fixed in v2.4.14

- [#3609](https://github.com/nautobot/nautobot/issues/3609) - Fixed `cluster_count` not showing up on the API of `/tenancy/tenants/`.
- [#7577](https://github.com/nautobot/nautobot/issues/7577) - Fixed incorrect reference to Inventory Items under the Module documentation.
- [#7616](https://github.com/nautobot/nautobot/issues/7616) - Fixed a data-loss bug in the v1.x-to-v2.0 migration `extras.0062_collect_roles_from_related_apps_roles` in which custom-field data on `dcim.DeviceRole`, `dcim.RackRole`, and `ipam.Role` records was not correctly copied to the corresponding created `extras.Role` records.
- [#7633](https://github.com/nautobot/nautobot/issues/7633) - Greatly reduced the number of database queries made when generating the GraphQL schema.

### Dependencies in v2.4.14

- [#7584](https://github.com/nautobot/nautobot/issues/7584) - Updated `GitPython` dependency to `~3.1.45`.
- [#7584](https://github.com/nautobot/nautobot/issues/7584) - Updated `nh3` dependency to `~0.2.22`.
- [#7584](https://github.com/nautobot/nautobot/issues/7584) - Updated `pyuwsgi` dependency to `2.0.30`.
- [#7601](https://github.com/nautobot/nautobot/issues/7601) - Updated dependency `netutils` minimum version to support ability for dynamic network driver mappings.

### Housekeeping in v2.4.14

- [#7419](https://github.com/nautobot/nautobot/issues/7419) - Refactored GraphQLQuery model related UI views to use `NautobotUIViewSet`.
- [#7479](https://github.com/nautobot/nautobot/issues/7479) - Refactored SecretsGroup model related UI views to use `NautobotUIViewSet`.
- [#7500](https://github.com/nautobot/nautobot/issues/7500) - Refactored Rack model related UI views to use `NautobotUIViewSet`.
- [#7584](https://github.com/nautobot/nautobot/issues/7584) - Updated development dependency `pymarkdownlnt` to `~0.9.31`.
- [#7584](https://github.com/nautobot/nautobot/issues/7584) - Updated documentation dependency `mkdocs-material` to `~9.6.16`.

## v2.4.13 (2025-07-21)

### Added in v2.4.13

- [#6594](https://github.com/nautobot/nautobot/issues/6594) - Added additional database indices to `IPAddress`, `Prefix`, and `VRF` models to improve the default list view performance for these models.

### Changed in v2.4.13

- [#6608](https://github.com/nautobot/nautobot/issues/6608) - Updated branding hyperlinks on bottom of UI to open in new tab.
- [#7484](https://github.com/nautobot/nautobot/issues/7484) - Add the Show Device Full Name button to the `Elevations` list view.

### Fixed in v2.4.13

- [#6594](https://github.com/nautobot/nautobot/issues/6594) - Changed the default `ordering` of `Interface` (and similar device components) to a less expensive query to improve performance of default list views of these components.
- [#6594](https://github.com/nautobot/nautobot/issues/6594) - Improved the performance of `Device.all_interfaces`, `.all_console_ports`, etc. in the case where the Device has no module bays.
- [#7590](https://github.com/nautobot/nautobot/issues/7590) - Improved performance of Device detail view when many devices belong to many dynamic-groups.

## v2.4.12 (2025-07-17)

### Changed in v2.4.12

- [#7194](https://github.com/nautobot/nautobot/issues/7194) - Moved `job_results` field from Job Panel to a separate `JobResults` table panel using ObjectsTablePanel from UI framework.

### Fixed in v2.4.12

- [#5056](https://github.com/nautobot/nautobot/issues/5056) - Fixed broken link pointing to Nautobot Golden Config Git Settings.
- [#7143](https://github.com/nautobot/nautobot/issues/7143) - Fixed filtering on custom relationships for component models.
- [#7547](https://github.com/nautobot/nautobot/issues/7547) - Fixed worker-status page failing with a KeyError.
- [#7552](https://github.com/nautobot/nautobot/issues/7552) - Fixed formatting issue in rendering Config Context data.
- [#7556](https://github.com/nautobot/nautobot/issues/7556) - Fixed Cloud, Devices, and Wireless NavMenuTabs all had the same weight of 200. Updated the Cloud weight to 150 and the Wireless weight to 250.
- [#7558](https://github.com/nautobot/nautobot/issues/7558) - Improved logic in `LogsCleanup` system Job to avoid an infinite recursion possibility.
- [#7559](https://github.com/nautobot/nautobot/issues/7559) - Reverted some of the changes introduced in v2.4.11 to Job loading from `JOBS_ROOT` and Git repositories, due to reports of regressions in behavior.

### Housekeeping in v2.4.12

- [#7194](https://github.com/nautobot/nautobot/issues/7194) - Refactored Jobs detail view to use `UI component framework`.
- [#7194](https://github.com/nautobot/nautobot/issues/7194) - Added `jobs_ui.py` to `nautobot.extras.views` with classes: `JobRunScheduleButton`, `JobKeyValueOverrideValueTablePanel` and `JobObjectFieldsPanel`.
- [#7217](https://github.com/nautobot/nautobot/issues/7217) - Refactored Controller model related UI views to use `UI component framework`.
- [#7291](https://github.com/nautobot/nautobot/issues/7291) - Refactored VirtualChassis model related UI views to use `NautobotUIViewSet`.
- [#7323](https://github.com/nautobot/nautobot/issues/7323) - Refactored CircuitTermination model related UI views to use `UI component framework`.
- [#7490](https://github.com/nautobot/nautobot/issues/7490) - Refactored Tag model related UI views to use `UI component framework`.
- [#7537](https://github.com/nautobot/nautobot/issues/7537) - Updated documentation dependency `mkdocs-material` to `~9.6.15`.

## v2.4.11 (2025-07-07)

### Security in v2.4.11

- [#7440](https://github.com/nautobot/nautobot/issues/7440) - Updated `requests` to `2.32.4` to address `CVE-2024-47081`. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#7461](https://github.com/nautobot/nautobot/issues/7461) - Updated `Django` to 4.2.23 to further address `CVE-2025-48432`.
- [#7487](https://github.com/nautobot/nautobot/issues/7487) - Updated `urllib3` to 2.5.0 due to `CVE-2025-50181` and `CVE-2025-50182`. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added in v2.4.11

- [#6941](https://github.com/nautobot/nautobot/issues/6941) - `ModuleTypes` can now be classified into a new `ModuleFamily` model. `ModuleBay` and `ModuleBayTemplates` can define a `ModuleFamily` they will accept.
- [#7007](https://github.com/nautobot/nautobot/issues/7007) - Added support for bulk-editing Webhook `additional_headers` and `body_template` fields.
- [#7298](https://github.com/nautobot/nautobot/issues/7298) - Added a `provides_dynamic_jobs` setting to NautobotAppConfig and associated logic to reload app-provided jobs similar to Git repo jobs.

### Changed in v2.4.11

- [#7178](https://github.com/nautobot/nautobot/issues/7178) - Changed JobResult list view default configuration to not calculate and show "summary" of log entries by default, as it is not performant at scale.

### Fixed in v2.4.11

- [#6933](https://github.com/nautobot/nautobot/issues/6933) - Fixed Cable deleting via API.
- [#7007](https://github.com/nautobot/nautobot/issues/7007) - Fixed an exception when bulk-editing Location `time_zone` values.
- [#7038](https://github.com/nautobot/nautobot/issues/7038) - Fixed issue where approved scheduled jobs set to run "immediately" were not executed, by changing the `create_schedule` method in `ScheduledJob`.
- [#7149](https://github.com/nautobot/nautobot/issues/7149) - Fixed `EXEMPT_VIEW_PERMISSIONS` causing an exception.
- [#7307](https://github.com/nautobot/nautobot/issues/7307) - Fixed incorrect bulk-edit job and view logic around nulling out fields.
- [#7307](https://github.com/nautobot/nautobot/issues/7307) - Fixed a number of incorrect `nullable_fields` entries on various bulk-edit forms.
- [#7361](https://github.com/nautobot/nautobot/issues/7361) - Added a check in `refresh_job_code_from_repository()` to cause it to abort early if given a `repository_slug` that is invalid or conflicts with an installed Python package or Python built-in.
- [#7361](https://github.com/nautobot/nautobot/issues/7361) - Fixed the code for loading Jobs from a GitRepository to only auto-import the `<repository_slug>` and `<repository_slug>.jobs` modules from `GIT_ROOT`, rather than loading all Python packages present in `GIT_ROOT`.
- [#7361](https://github.com/nautobot/nautobot/issues/7361) - Fixed the code for loading Jobs from `JOBS_ROOT` and Git repositories to not import discovered packages/modules whose names are invalid as Python module names or whose names conflict with installed Python packages or Python built-ins. **This fix prevents some improper-but-previously-permitted names (e.g. `pass.py`, `nautobot.py`) from being imported.**
- [#7361](https://github.com/nautobot/nautobot/issues/7361) - Added additional validation constraints on GitRepository `slug` to disallow values that would conflict with Python built-ins and keywords. **This fix will disallow some improper-but-previously-permitted slugs (e.g. `sys`, `pass`); you can run `nautobot-server validate_models extras.GitRepository` after upgrading to identify entries that should be deleted and recreated with a different slug.**
- [#7427](https://github.com/nautobot/nautobot/issues/7427) - Fixed return URL for single "Remove cable" operations.
- [#7460](https://github.com/nautobot/nautobot/issues/7460) - Added missing permission enforcement for custom actions in NautobotUIViewSet supported models.
- [#7464](https://github.com/nautobot/nautobot/issues/7464) - Fixed issue where network driver help text and choices modal were missing in `Platform`.
- [#7489](https://github.com/nautobot/nautobot/issues/7489) - Fixed broken Relationship "Move to advanced tab" functionality.
- [#7503](https://github.com/nautobot/nautobot/issues/7503) - Fixed issue where retrieving the username of the latest change log entry loaded large unrelated fields.
- [#7518](https://github.com/nautobot/nautobot/issues/7518) - Improved performance for the "utilization" column of the Prefix list view.
- [#7528](https://github.com/nautobot/nautobot/issues/7528) - Fixed a typo in the RadioProfile model.

### Dependencies in v2.4.11

- [#7444](https://github.com/nautobot/nautobot/issues/7444) - Updated dependency `celery` to permit versions up to 5.5.x and `kombu` to permit versions up to 5.5.x as well. Due to concern about potential impacts of the upgrade, we have *not* yet updated the minimum Celery and Kombu versions required by Nautobot. This minimum version will likely be raised in a future release; in the interim, please upgrade Celery and Kombu and verify their operation in your local environment as befits your risk tolerance.

### Documentation in v2.4.11

- [#7469](https://github.com/nautobot/nautobot/issues/7469) - Updated sample Device Redundancy Group GraphQL queries with correct v2 field names.
- [#7514](https://github.com/nautobot/nautobot/issues/7514) - Updated BootstrapMixin import location in secrets provider example docs.
- [#7527](https://github.com/nautobot/nautobot/issues/7527) - Added Analytics GTM template override only to the public ReadTheDocs build.

### Housekeeping in v2.4.11

- [#7007](https://github.com/nautobot/nautobot/issues/7007) - Enhanced `test_bulk_edit_objects_with_permission` generic view test case to include validation that the provided `bulk_edit_data` was processed correctly and correctly passed through to the BulkEditObjects job.
- [#7007](https://github.com/nautobot/nautobot/issues/7007) - Added `test_bulk_edit_objects_nullable_fields` generic view test case to verify correct definition and operation of `nullable_fields` on bulk edit forms.
- [#7238](https://github.com/nautobot/nautobot/issues/7238) - Refactored InterfaceRedundancyGroup model related UI views to use `UI component framework`.
- [#7258](https://github.com/nautobot/nautobot/issues/7258) - Refactored ControllerManagedDeviceGroup model related UI views to use `UI component framework`.
- [#7303](https://github.com/nautobot/nautobot/issues/7303) - Refactored PowerFeed model related UI views to use `UI component framework`.
- [#7346](https://github.com/nautobot/nautobot/issues/7346) - Refactored Location model related UI views to use `NautobotUIViewSet`.
- [#7347](https://github.com/nautobot/nautobot/issues/7347) - Refactored RelationshipAssociation model related UI views to use `NautobotUIViewSet`.
- [#7357](https://github.com/nautobot/nautobot/issues/7357) - Refactored Tag model related UI views to use `NautobotUIViewSet`.
- [#7361](https://github.com/nautobot/nautobot/issues/7361) - Added unit tests for `import_modules_privately` utility method.
- [#7409](https://github.com/nautobot/nautobot/issues/7409) - Refactored ConfigContext model related UI views to use `NautobotUIViewSet`.
- [#7413](https://github.com/nautobot/nautobot/issues/7413) - Refactored VLAN model related UI views to use `NautobotUIViewSet`.
- [#7421](https://github.com/nautobot/nautobot/issues/7421) - Refactored ConfigContextSchema model related UI views to use `NautobotUIViewSet`.
- [#7450](https://github.com/nautobot/nautobot/issues/7450) - Removed deprecated sandbox deployment workflow.
- [#7461](https://github.com/nautobot/nautobot/issues/7461) - Updated testing dependency `openapi-spec-validator` to `~0.7.2`.
- [#7483](https://github.com/nautobot/nautobot/issues/7483) - Refactored ConfigContext model related UI views to use `UI component framework`.

## v2.4.10 (2025-06-09)

### Security in v2.4.10

- [#6672](https://github.com/nautobot/nautobot/issues/6672) - Added enforcement of user authentication when serving uploaded media files ([GHSA-rh67-4c8j-hjjh](https://github.com/nautobot/nautobot/security/advisories/GHSA-rh67-4c8j-hjjh)).
- [#7417](https://github.com/nautobot/nautobot/issues/7417) - Added protections against access of various security-related and/or data-altering methods of various Nautobot models from within a Jinja2 sandboxed environment or the Django template renderer ([GHSA-wjw6-95h5-4jpx](https://github.com/nautobot/nautobot/security/advisories/GHSA-wjw6-95h5-4jpx)).
- [#7425](https://github.com/nautobot/nautobot/issues/7425) - Updated `Django` to 4.2.22 to address `CVE-2025-48432`.

### Fixed in v2.4.10

- [#7358](https://github.com/nautobot/nautobot/issues/7358) - Fixed `web_request_context` faulty logic in its `try/finally` block.
- [#7362](https://github.com/nautobot/nautobot/issues/7362) - Fixed NautobotCSVParser incorrect parsing of many-to-many fields.

### Documentation in v2.4.10

- [#7430](https://github.com/nautobot/nautobot/issues/7430) - Added latest security disclosures to the documentation.
- [#7430](https://github.com/nautobot/nautobot/issues/7430) - Removed John Anderson as a point of contact for Nautobot security issues.

## v2.4.9 (2025-05-27)

### Security in v2.4.9

- [#7317](https://github.com/nautobot/nautobot/issues/7317) - Updated `setuptools` to `78.1.1` to address `CVE-2025-47273`. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added in v2.4.9

- [#7043](https://github.com/nautobot/nautobot/issues/7043) - Added support for `job_queue` parameter to `JobResult.execute_job()`, `JobResult.enqueue_job()`, and `ScheduledJob.create_schedule()`.

### Changed in v2.4.9

- [#7043](https://github.com/nautobot/nautobot/issues/7043) - Changed "Run Job" form to display a warning when submitting a Job against a Celery queue that has no active workers, but allow the job to be submitted, instead of blocking the Job altogether.

### Fixed in v2.4.9

- [#7043](https://github.com/nautobot/nautobot/issues/7043) - Fixed regression introduced in 2.4.0 involving inability to specify a non-default job queue when scheduling a Job.
- [#7172](https://github.com/nautobot/nautobot/issues/7172) - Restored missing `rd` column in `VRFTable`.
- [#7245](https://github.com/nautobot/nautobot/issues/7245) - Fixed `ExportObjectList` job now initializes `filter_params` from the selected SavedView's config when `?saved_view` is present and filters haven't been cleared. If additional query parameters are included, they override matching filters from the saved view.
- [#7250](https://github.com/nautobot/nautobot/issues/7250) - Fixed MULTISELECT custom field representation in GraphQL to be a JSON array instead of a string.
- [#7308](https://github.com/nautobot/nautobot/issues/7308) - Fixed incorrect form buttons rendered in create/update views provided by NautobotUIViewSet.
- [#7309](https://github.com/nautobot/nautobot/issues/7309) - Fixed Content-Type filtering on ObjectMetaData.
- [#7311](https://github.com/nautobot/nautobot/issues/7311) - Added f-strings to 2 places where they were missing (`nautobot/core/utils/filtering.py` in `generate_query` method and in migration file `nautobot/extras/migrations/0024_job_data_migration.py`).
- [#7318](https://github.com/nautobot/nautobot/issues/7318) - Fixed an AttributeError exception when rendering a table column describing a Relationship association to an unknown content-type.
- [#7328](https://github.com/nautobot/nautobot/issues/7328) - Fixed an issue in the Golden Config App where clicking a Configuration Compliance Feature Navigation link or loading a page with a hash would not scroll to the correct section due to conflicting legacy scroll offset logic.
- [#7340](https://github.com/nautobot/nautobot/issues/7340) - Fixed incorrect rendering of "Last run" column in Job list view.

### Dependencies in v2.4.9

- [#7277](https://github.com/nautobot/nautobot/issues/7277) - Updated `cryptography` dependency to `~44.0.3`.
- [#7277](https://github.com/nautobot/nautobot/issues/7277) - Updated `pyuwsgi` dependency to `~2.0.29`.

### Housekeeping in v2.4.9

- [#7104](https://github.com/nautobot/nautobot/issues/7104) - Resolved bug in VS Code devcontainer workflow.
- [#7163](https://github.com/nautobot/nautobot/issues/7163) - Refactored CloudResourceType model related UI views to use `UI component framework`.
- [#7231](https://github.com/nautobot/nautobot/issues/7231) - Refactored DeviceFamily model related UI views to use `UI component framework`.
- [#7237](https://github.com/nautobot/nautobot/issues/7237) - Refactored DeviceRedundancyGroup model related UI views to use `UI component framework`.
- [#7243](https://github.com/nautobot/nautobot/issues/7243) - Refactored DeviceType model related UI views to use `NautobotUIViewSet`.
- [#7246](https://github.com/nautobot/nautobot/issues/7246) - Refactored WirelessNetwork model related UI views to use `UI component framework`.
- [#7248](https://github.com/nautobot/nautobot/issues/7248) - Refactored ModuleBayUIViewSet model related UI views to use `UI component framework`.
- [#7265](https://github.com/nautobot/nautobot/issues/7265) - Refactored MetadataType model related UI views to use `UI component framework`.
- [#7271](https://github.com/nautobot/nautobot/issues/7271) - Refactored ComputedField model related UI views to use `UI component framework`.
- [#7277](https://github.com/nautobot/nautobot/issues/7277) - Updated documentation dependency `mkdocs-material` to `~9.6.14`.
- [#7277](https://github.com/nautobot/nautobot/issues/7277) - Updated development dependency `pylint` to `~3.3.7`.
- [#7277](https://github.com/nautobot/nautobot/issues/7277) - Updated development dependency `pymarkdownlnt` to `~0.9.30`.
- [#7287](https://github.com/nautobot/nautobot/issues/7287) - Refactored CircuitTypeUIViewSet model related UI views to use `UI component framework`.
- [#7300](https://github.com/nautobot/nautobot/issues/7300) - Refactored RackReservation model related UI views to use `UI component framework`.

## v2.4.8 (2025-05-12)

### Security in v2.4.8

- [#7223](https://github.com/nautobot/nautobot/issues/7223) - Updated dependency `h11` to `0.16.0` to address `CVE-2025-43859`. This is a development dependency and will not auto-update when upgrading Nautobot. Please be sure to update your local environment.
- [#7273](https://github.com/nautobot/nautobot/issues/7273) - Updated `Django` to 4.2.21 to address `CVE-2025-32873`.

### Added in v2.4.8

- [#6053](https://github.com/nautobot/nautobot/issues/6053) - Added `primary_ip` property to GraphQL `DeviceType` to simplify lookup of primary IPs when a mixture of IPv4 and IPv6 are involved.
- [#6053](https://github.com/nautobot/nautobot/issues/6053) - Added `device` property to GraphQL `ModuleType` to simplify lookup of the Device containing a given Module.
- [#7048](https://github.com/nautobot/nautobot/issues/7048) - Added Bulk Edit functionality for the Platform model.
- [#7075](https://github.com/nautobot/nautobot/issues/7075) - Added Bulk Edit functionality for the Webhook model.
- [#7107](https://github.com/nautobot/nautobot/issues/7107) - Added Bulk Edit functionality for the JobHook model.
- [#7126](https://github.com/nautobot/nautobot/issues/7126) - Added Bulk Edit functionality for the CustomLink model.
- [#7148](https://github.com/nautobot/nautobot/issues/7148) - Added Bulk Edit functionality for the RackGroup model.
- [#7154](https://github.com/nautobot/nautobot/issues/7154) - Added index to `created` field in `JobLogEntry`.
- [#7159](https://github.com/nautobot/nautobot/issues/7159) - Added Bulk Edit functionality for the ComputedField model.
- [#7232](https://github.com/nautobot/nautobot/issues/7232) - Added Bulk Edit functionality for the CircuitType model.
- [#7234](https://github.com/nautobot/nautobot/issues/7234) - Added Bulk Edit functionality for the CircuitTermination model.

### Changed in v2.4.8

- [#7219](https://github.com/nautobot/nautobot/issues/7219) - Enhanced Contact and Team search to include matching by email and phone number.
- [#7224](https://github.com/nautobot/nautobot/issues/7224) - Changed `ObjectsTablePanel.__init__()` to enforce that a `related_field_name` is required when specifying a `table_attribute`.
- [#7267](https://github.com/nautobot/nautobot/issues/7267) - Changed the `contacts` tab in object detail views to not render if users do not have permission to view contact-associations.

### Fixed in v2.4.8

- [#6053](https://github.com/nautobot/nautobot/issues/6053) - Added `all_interfaces`, `all_modules`, etc. properties to GraphQL `DeviceType` to facilitate lookup of components belonging to descendant modules.
- [#6053](https://github.com/nautobot/nautobot/issues/6053) - Added `common_vc_interfaces`, `vc_interfaces` properties to GraphQL `DeviceType` to facilitate lookup of components when VirtualChassis are involved.
- [#6157](https://github.com/nautobot/nautobot/issues/6157) - Fixed invalid specs for ChoiceFields and EmailFields in the swagger schema.
- [#6985](https://github.com/nautobot/nautobot/issues/6985) - Added `filterset_form` to `RackElevationListView`.
- [#7026](https://github.com/nautobot/nautobot/issues/7026) - Fixed collapsing/expanding on the jobs page.
- [#7102](https://github.com/nautobot/nautobot/issues/7102) - Fixed that event payload's `prechange` field is empty when relevant object's previous changelog entries do not exist.
- [#7154](https://github.com/nautobot/nautobot/issues/7154) - Fixed memory issue in cleanup Job Results by changing `delete` to `_raw_delete` in `recursive_delete_with_cascade` method.
- [#7184](https://github.com/nautobot/nautobot/issues/7184) - Fixed missing support for `value_transforms` with certain model field types in `ObjectFieldsPanel`.
- [#7188](https://github.com/nautobot/nautobot/issues/7188) - Fixed broken advanced filters in Nautobot v2.4.7
- [#7224](https://github.com/nautobot/nautobot/issues/7224) - Fixed table filter issues in CloudNetwork model related UI component.

### Documentation in v2.4.8

- [#7140](https://github.com/nautobot/nautobot/issues/7140) - Fixed a typo in front port documentation.
- [#7240](https://github.com/nautobot/nautobot/issues/7240) - Reorganized and expanded the Nautobot Jobs documentation across both the User Guide and the Development Guide. The goals of this update are to improve navigation, reduce page length for easier readability, standardize examples, and align the documentation with Nautobot 2.4.x behavior.

### Housekeeping in v2.4.8

- [#6157](https://github.com/nautobot/nautobot/issues/6157) - Added a unit test to validate the generated OpenAPI spec.
- [#7047](https://github.com/nautobot/nautobot/issues/7047) - Refactored VLANGroup model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#7048](https://github.com/nautobot/nautobot/issues/7048) - Refactored Platform model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#7056](https://github.com/nautobot/nautobot/issues/7056) - Refactored Cluster model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7075](https://github.com/nautobot/nautobot/issues/7075) - Refactored webhook model related UI views to use `NautobotUIViewSet` and `UI Component Framework`.
- [#7107](https://github.com/nautobot/nautobot/issues/7107) - Refactored JobHook model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7126](https://github.com/nautobot/nautobot/issues/7126) - Refactored CustomLink model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7141](https://github.com/nautobot/nautobot/issues/7141) - Refactored PowerPanel model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7148](https://github.com/nautobot/nautobot/issues/7148) - Refactored RackGroup model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7153](https://github.com/nautobot/nautobot/issues/7153) - Refactored SupportedDataRate model related UI views to use `UI component framework`.
- [#7155](https://github.com/nautobot/nautobot/issues/7155) - Refactored RackReservation model related UI views to use `NautobotUIViewSet`.
- [#7158](https://github.com/nautobot/nautobot/issues/7158) - Refactored CloudNetwork model related UI views to use `UI component framework`.
- [#7159](https://github.com/nautobot/nautobot/issues/7159) - Refactored ComputedField model related UI views to use `NautobotUIViewSet`.
- [#7162](https://github.com/nautobot/nautobot/issues/7162) - Refactored CloudService model related UI views to use `UI component framework`.
- [#7172](https://github.com/nautobot/nautobot/issues/7172) - Refactored PowerFeed model related UI views to use `NautobotUIViewSet`.
- [#7173](https://github.com/nautobot/nautobot/issues/7173) - Refactored JobQueue model related UI views to use `UI component framework`.
- [#7175](https://github.com/nautobot/nautobot/issues/7175) - Refactored JobButton model related UI views to use `UI component framework`.
- [#7184](https://github.com/nautobot/nautobot/issues/7184) - Refactored RadioProfile model related UI views to use `UI component framework`.
- [#7187](https://github.com/nautobot/nautobot/issues/7187) - Added upstream testing for next/next-3.0 in Apps.
- [#7187](https://github.com/nautobot/nautobot/issues/7187) - Removed upstream testing for ltm-1.6.
- [#7189](https://github.com/nautobot/nautobot/issues/7189) - Updated `mkdocs-material` documentation dependency to `~9.6.12`.
- [#7189](https://github.com/nautobot/nautobot/issues/7189) - Updated `mkdocs-section-index` documentation dependency to `~0.3.10`.
- [#7204](https://github.com/nautobot/nautobot/issues/7204) - Refactored SoftwareVersion model related UI views to use `UI component framework`.
- [#7212](https://github.com/nautobot/nautobot/issues/7212) - Refactored SoftwareImageFile model related UI views to use `UI component framework`.

## v2.4.7 (2025-04-14)

### Added in v2.4.7

- [#4171](https://github.com/nautobot/nautobot/issues/4171) - Added `TYPE_NOTES` and `TYPE_URL` to SecretsGroupSecretTypeChoices.
- [#6923](https://github.com/nautobot/nautobot/issues/6923) - Added `AutoPopulateWidget` to support form fields with auto-population logic.
- [#6998](https://github.com/nautobot/nautobot/issues/6998) - Added browser and backend caching for `/api/swagger` OpenAPI endpoint to speed up Swagger and Redoc loading time.
- [#7115](https://github.com/nautobot/nautobot/issues/7115) - Added Bulk Edit functionality for the Relationship model.
- [#7127](https://github.com/nautobot/nautobot/issues/7127) - Added Bulk Edit functionality for the ExportTemplate model.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Added Bulk Edit functionality for the Manufacturer model.

### Changed in v2.4.7

- [#6753](https://github.com/nautobot/nautobot/issues/6753) - Removed indentation of child locations on location details page.
- [#7114](https://github.com/nautobot/nautobot/issues/7114) - Changed "Locations" column in VLAN table to show `location.name` instead of `location.display` to avoid verbose location hierarchy.

### Fixed in v2.4.7

- [#5287](https://github.com/nautobot/nautobot/issues/5287) - Fixed text to be selectable on homepage panels.
- [#6923](https://github.com/nautobot/nautobot/issues/6923) - Fixed auto populating position field when creating Module Bay from Device Type details and bulk creating from Devices or Modules list.
- [#7101](https://github.com/nautobot/nautobot/issues/7101) - Fixed saving a new rack elevation view.
- [#7108](https://github.com/nautobot/nautobot/issues/7108) - Fixed various cases where CustomField-related `provision_field` and `delete_custom_field_data` background tasks were unnecessarily triggered.
- [#7108](https://github.com/nautobot/nautobot/issues/7108) - Added missing signal handler to remove custom field data from affected objects when `CustomField.content_types.clear()` is called.
- [#7152](https://github.com/nautobot/nautobot/issues/7152) - Changed `Location.display` to honor `LOCATION_NAME_AS_NATURAL_KEY` - meaning the display of location names will not render the full hierarchy, in places where only the name is relevant.

### Housekeeping in v2.4.7

- [#6923](https://github.com/nautobot/nautobot/issues/6923) - Refactored `initializeSlugField` to use common logic with other auto populated field like Module Bay position.
- [#7099](https://github.com/nautobot/nautobot/issues/7099) - Removed jQuery from documentation builds as it's not needed anymore for the ReadTheDocs version selection flyout menu.
- [#7103](https://github.com/nautobot/nautobot/issues/7103) - Refactored ProviderNetwork model related UI views to use `UI component framework`.
- [#7111](https://github.com/nautobot/nautobot/issues/7111) - Refactored Team model related UI views to use `UI component framework`.
- [#7115](https://github.com/nautobot/nautobot/issues/7115) - Refactored Relationship model related UI views to use `NautobotUIViewSet`.
- [#7127](https://github.com/nautobot/nautobot/issues/7127) - Refactored ExportTemplate model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7130](https://github.com/nautobot/nautobot/issues/7130) - Refactored Contact model related UI views to use `UI component framework`.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Refactored Manufacturer model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7144](https://github.com/nautobot/nautobot/issues/7144) - Refactored CloudAccount model related UI views to use `UI component framework`.

## v2.4.6 (2025-03-31)

### Security in v2.4.6

- [#7039](https://github.com/nautobot/nautobot/issues/7039) - Updated `cryptography` to `44.0.2` to address `CVE-2024-12797`.

### Added in v2.4.6

- [#4181](https://github.com/nautobot/nautobot/issues/4181) - Added `last_updated` column to Note table.
- [#4181](https://github.com/nautobot/nautobot/issues/4181) - Added display for number of notes attached to each object on the Notes tab header in Object Detail View.
- [#5780](https://github.com/nautobot/nautobot/issues/5780) - Added object permission enforcement to related objects when modifying records through the REST API.
- [#6957](https://github.com/nautobot/nautobot/issues/6957) - Added optional `display_field` parameter to `LinkedCountColumn`.
- [#7003](https://github.com/nautobot/nautobot/issues/7003) - Added `external_integration` foreign key field to `SoftwareImageFile` model, which allows the enrichment of file data to include download options, secrets, etc.
- [#7041](https://github.com/nautobot/nautobot/issues/7041) - Added Bulk Edit functionality for the ClusterType model.
- [#7044](https://github.com/nautobot/nautobot/issues/7044) - Added Bulk Edit functionality for the ClusterGroup model.
- [#7088](https://github.com/nautobot/nautobot/issues/7088) - Added support for removing content types in Status bulk-edit and Role bulk-edit.
- [#7091](https://github.com/nautobot/nautobot/issues/7091) - Added Nautobot DNS Models app to the Apps Marketplace.

### Changed in v2.4.6

- [#4181](https://github.com/nautobot/nautobot/issues/4181) - Changed the default column ordering of Note table.
- [#6379](https://github.com/nautobot/nautobot/issues/6379) - Changed `SoftwareImageFile.download_url` to allow additional URI Schemas, such as `sftp://`, `tftp://`.
- [#6957](https://github.com/nautobot/nautobot/issues/6957) - Changed "Locations" column in Prefix table to show `location.name` instead of `location.display` to avoid verbose location hierarchy in tables.

### Fixed in v2.4.6

- [#6902](https://github.com/nautobot/nautobot/issues/6902) - Fixed bug with formatting date in templates.
- [#6962](https://github.com/nautobot/nautobot/issues/6962) - Fixed a Validation error with empty ports field in Service Bulk Edit Form.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Improved speed of IPAM 1.x-to-2.x data migration `0031_ipam___data_migrations` by about 20% when working with large data sets.
- [#7088](https://github.com/nautobot/nautobot/issues/7088) - Fixed bulk assignment and bulk removal of content types.
- [#7092](https://github.com/nautobot/nautobot/issues/7092) - Added graceful handling for route-lookup errors when constructing a DynamicModelChoiceField or a DynamicModelMultipleChoiceField.

### Dependencies in v2.4.6

- [#6993](https://github.com/nautobot/nautobot/issues/6993) - Update dependency `kubernetes` to `^32.0.1`.
- [#6993](https://github.com/nautobot/nautobot/issues/6993) - Update dependency `nh3` to `~0.2.21`.
- [#7019](https://github.com/nautobot/nautobot/issues/7019) - Added `cryptography` as a directly specified dependency of Nautobot to make it easier to protect against various security issues in older versions of `cryptography`.
- [#7019](https://github.com/nautobot/nautobot/issues/7019) - Removed support for Python 3.9.0 and 3.9.1 due to dependencies such as `cryptography` requiring newer Python versions.

### Documentation in v2.4.6

- [#6944](https://github.com/nautobot/nautobot/issues/6944) - Updated the "Installation" section of the documentation to more clearly describe the various deployment approaches recommended for Nautobot and their respective pros and cons.
- [#6995](https://github.com/nautobot/nautobot/issues/6995) - Added content to User Guide `index.md` to give overview of options in the documentation of the guide.
- [#7014](https://github.com/nautobot/nautobot/issues/7014) - Added "Recipe" section to permissions documentation with an "Export" example.
- [#7020](https://github.com/nautobot/nautobot/issues/7020) - Improving issues found in various User Guide Getting Started typos and unclear references.
- [#7030](https://github.com/nautobot/nautobot/issues/7030) - Improved Nautobot Webhooks documentation with additional context and examples.
- [#7051](https://github.com/nautobot/nautobot/issues/7051) - Clarified developer "best practices" documentation regarding base classes for forms in Nautobot.

### Housekeeping in v2.4.6

- [#6962](https://github.com/nautobot/nautobot/issues/6962) - Refactored Service model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#6970](https://github.com/nautobot/nautobot/issues/6970) - Added selenium helper. Fixed selenium VNC port bug.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Added `django-test-migrations` as a testing dependency.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Added `nautobot.ipam.tests.test_migrations.IPAMDataMigration0031TestCase` that can be run to reproducibly test IPAM data migration `0031_ipam___data_migrations` for correctness and performance.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Renamed `invoke tests` task to `invoke lint` and renamed `invoke unittest` task to `invoke tests`.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Changed `invoke tests` task to default to _not_ measuring and reporting code coverage by default, since doing so slows test performance.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Removed `django-slowtests` as a development dependency and removed associated test-performance-measuring functionality.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Removed distinct `invoke integration-test`, `invoke performance-test`, and `invoke unittest-coverage` tasks; integration tests should now be run with `invoke tests --tag integration` and test coverage is reported when running `invoke tests --coverage`.
- [#6987](https://github.com/nautobot/nautobot/issues/6987) - Refactored `nautobot.ipam.tests.test_migrations.AggregateToPrefixMigrationTestCase` to use `django-test-migrations` and be runnable.
- [#7013](https://github.com/nautobot/nautobot/issues/7013) - Refactored Namespace model related UI views to use `UI component framework`.
- [#7017](https://github.com/nautobot/nautobot/issues/7017) - Fixed conflicts between factory data and bespoke test data involving VRF assignments to Virtual Device Contexts.
- [#7017](https://github.com/nautobot/nautobot/issues/7017) - Fixed state leakage from custom-validation test cases potentially causing failures of other test cases.
- [#7037](https://github.com/nautobot/nautobot/issues/7037) - Adds github action linter to CI.
- [#7041](https://github.com/nautobot/nautobot/issues/7041) - Refactored ClusterType model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7044](https://github.com/nautobot/nautobot/issues/7044) - Refactored ClusterGroup model related UI views to use `NautobotUIViewSet` and `UI component framework`.
- [#7055](https://github.com/nautobot/nautobot/issues/7055) - Updated development dependencies `pylint` to `~3.3.6` and `pymarkdownlnt` to `~0.9.29`.
- [#7064](https://github.com/nautobot/nautobot/issues/7064) - Updated CI to use Poetry 1.8.5.
- [#7064](https://github.com/nautobot/nautobot/issues/7064) - Updated "upstream testing" CI to use Python 3.11.
- [#7071](https://github.com/nautobot/nautobot/issues/7071) - Refactored Status model related UI views to use `NautobotUIViewSet` and `UI component framework`.

## v2.4.5 (2025-03-10)

### Security in v2.4.5

- [#6983](https://github.com/nautobot/nautobot/issues/6983) - Updated dependency `Jinja2` to `~3.1.6` to address `CVE-2025-27516`.
- [#7000](https://github.com/nautobot/nautobot/issues/7000) - Updated dependency `Django` to `~4.2.20` to address `CVE-2025-26699`.

### Added in v2.4.5

- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Added `Job.logger.failure()` API for Job logging, using custom `FAILURE` log level (between `WARNING` and `ERROR`).
- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Added `Job.fail()` API, which can be used to fail a Job more gracefully than by raising an uncaught exception.
- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Added `NautobotTestCaseMixin.assertJobResultStatus()` testing helper API.
- [#7001](https://github.com/nautobot/nautobot/issues/7001) - Added Bulk Edit functionality for the RIR model.

### Changed in v2.4.5

- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Changed output of `nautobot-server runjob` command to include the traceback (if any) and count of `success`/`failure` log messages.

### Removed in v2.4.5

- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Removed the (undocumented) requirement for Jobs that implement a custom `before_start()` or `after_return()` method to call `super()` for the Job to execute successfully.

### Fixed in v2.4.5

- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Fixed rendering of "actions" column in the JobResult table view.
- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Fixed incorrect `stacklevel` default value in Job `logger.success()` API.
- [#6906](https://github.com/nautobot/nautobot/issues/6906) - `GitRepository.clone_to_directory` now uses configured Secrets for Repository to prepare correct `from_url`.
- [#6972](https://github.com/nautobot/nautobot/issues/6972) - Fixed IPAddress get_or_create not working with the address argument.

### Housekeeping in v2.4.5

- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Added `init: true` to development `docker-compose.yml` to avoid failed health-checks from remaining as zombie processes.
- [#6384](https://github.com/nautobot/nautobot/issues/6384) - Added `ExampleFailingJob` to example app to demonstrate the two different ways to fail a Job.
- [#6971](https://github.com/nautobot/nautobot/issues/6971) - Fixed invoke commands requiring pyyaml.
- [#7001](https://github.com/nautobot/nautobot/issues/7001) - Refactored RIR model related UI views to use `NautobotUIViewSet` and `UI component framework`.

## v2.4.4 (2025-03-03)

### Added in v2.4.4

- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Added `PrefixFilter` helper class to `nautobot.apps.filters`.
- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Enhanced `prefixes` filter on `CloudNetwork` and `Tenant` filtersets to support filtering by literal prefix string (`10.0.0.0/8`) as an alternative to filtering by primary key.
- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Enhanced `prefix` filter on `CloudNetworkPrefixAssignment`, `VRF`, and `VRFPrefixAssignment` filtersets to support filtering by literal prefix string (`10.0.0.0/8`) as an alternative to filtering by primary key.
- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Enhanced `parent` filter on `Prefix` filtersets to support filtering by literal prefix string (`10.0.0.0/8`) as an alternative to filtering by primary key.
- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Enhanced `prefix` filter on `PrefixLocationAssignment` filtersets to support filtering by primary key as an alternative to filtering by literal prefix string.
- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Added `q` search filter to `VRFPrefixAssignment` filterset.
- [#6635](https://github.com/nautobot/nautobot/issues/6635) - Added Monaco Editor integration to object change view for improved visualization of structured data differences including JSON, YAML, XML, tags, custom fields, and config contexts.
- [#6924](https://github.com/nautobot/nautobot/issues/6924) - Added optional VRF relationship to Virtual Device Context.
- [#6925](https://github.com/nautobot/nautobot/issues/6925) - Added colors next to Devices to indicate Device status in Rack Elevation view.
- [#6966](https://github.com/nautobot/nautobot/issues/6966) - Added support for accessing the current user within Custom Validators via `self.context["user"]`.

### Changed in v2.4.4

- [#6829](https://github.com/nautobot/nautobot/issues/6829) - Enabled assignment of a Device to a Rack that belongs to a child Location of the device's location; for example, a Device located in a "Building" can now be assigned to a Rack located in a "Room" within that building.

### Fixed in v2.4.4

- [#3041](https://github.com/nautobot/nautobot/issues/3041) - Fixed inability to assign a parent bay when creating a Device via the REST API.
- [#5006](https://github.com/nautobot/nautobot/issues/5006) - Added a validation check to prevent removing an in-use content type from a LocationType.
- [#5193](https://github.com/nautobot/nautobot/issues/5193) - Fixed an erroneous `ValidationError` when attempting to apply Tags to an object via the REST API.
- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Fixed `VRFPrefixAssignment` REST API endpoint incorrectly advertising support for Notes.
- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Fixed incorrect `Meta.model` value on `ControllerManagedDeviceGroupWirelessNetworkAssignmentTable` and `ControllerManagedDeviceGroupRadioProfileAssignmentTable`.
- [#6848](https://github.com/nautobot/nautobot/issues/6848) - Fixed a `DoesNotExist` error in the GUI at `/extras/git-repositories/X/result/` when a Git repository was created via API and not yet synced.
- [#6861](https://github.com/nautobot/nautobot/issues/6861) - Fixed the data population of the Rack Group dropdown to include Rack Groups from the Rack's parent locations in Rack Edit View.
- [#6910](https://github.com/nautobot/nautobot/issues/6910) - Fixed CSV export job to add a UTF-8 BOM (byte order mark) to the created file to ensure Excel will correctly handle any Unicode data.
- [#6920](https://github.com/nautobot/nautobot/issues/6920) - Added log messages to help troubleshoot failures when rendering UI Component Framework `extra_buttons`.
- [#6920](https://github.com/nautobot/nautobot/issues/6920) - Fixed logic in UI Component Framework `StatsPanel` that incorrectly disallowed use of FilterSet filters implicitly defined through `fields = "__all__"`.
- [#6920](https://github.com/nautobot/nautobot/issues/6920) - Fixed logic in generic `FormTestCase` class that would incorrectly fail if form fields used FilterSet filters implicitly defined through `fields = "__all__"`.
- [#6939](https://github.com/nautobot/nautobot/issues/6939) - Fixed an error in testing Jobs in `JOBS_ROOT` by forcing registration of `taggit` and `social_django` models before unregistering them from the admin site.
- [#6950](https://github.com/nautobot/nautobot/issues/6950) - Added missing `job_queues` filter field to `JobFilterSet`.
- [#6952](https://github.com/nautobot/nautobot/issues/6952) - Fixed an `AttributeError` exception when upgrading from v1.x to v2.x with certain existing data in the database.

### Dependencies in v2.4.4

- [#6927](https://github.com/nautobot/nautobot/issues/6927) - Updated dependency `django-filter` to `~25.1`.

### Documentation in v2.4.4

- [#6903](https://github.com/nautobot/nautobot/issues/6903) - Removed documentation references to Nautobot 1.x behavior and feature changes within the 1.x release series.
- [#6951](https://github.com/nautobot/nautobot/issues/6951) - Fixed typo in v2 migration documentation.

### Housekeeping in v2.4.4

- [#5851](https://github.com/nautobot/nautobot/issues/5851) - Enhanced `PrefixFactory` and `VRFFactory` test helpers to automatically create appropriate `VRFPrefixAssignment` records.
- [#6857](https://github.com/nautobot/nautobot/issues/6857) - Added `.yarn` directory to `.gitignore`.
- [#6857](https://github.com/nautobot/nautobot/issues/6857) - Changed CI for integration tests to use `--no-keepdb`.
- [#6858](https://github.com/nautobot/nautobot/issues/6858) - Fixed generation of performance test endpoints for Nautobot apps.
- [#6893](https://github.com/nautobot/nautobot/issues/6893) - Added an option for ephemeral ports, and streamlined debug settings for VSCode developers.
- [#6943](https://github.com/nautobot/nautobot/issues/6943) - Updated `debug` invoke task to restore previous behavior.

## v2.4.3 (2025-02-18)

### Added in v2.4.3

- [#6836](https://github.com/nautobot/nautobot/issues/6836) - Added management command `generate_performance_test_endpoints` to generate performance test endpoints.
- [#6865](https://github.com/nautobot/nautobot/issues/6865) - Added Bulk Edit functionality for the Tenant Group model.

### Changed in v2.4.3

- [#5568](https://github.com/nautobot/nautobot/issues/5568) - Added hyperlink to the total device count number under device family.

### Fixed in v2.4.3

- [#5539](https://github.com/nautobot/nautobot/issues/5539) - Fixed incorrect error message in Controller `clean()` method.
- [#6113](https://github.com/nautobot/nautobot/issues/6113) - Menus inside responsive tables are fixed to be visible by dynamically mounting them to the body and positioning them absolutely.
- [#6667](https://github.com/nautobot/nautobot/issues/6667) - Adds custom clearable file input form widget.
- [#6764](https://github.com/nautobot/nautobot/issues/6764) - Fixed global and user default saved views incorrectly overriding filtered views.
- [#6785](https://github.com/nautobot/nautobot/issues/6785) - Fixed Saved Views throwing an unexpected error when they contain boolean filter parameters.
- [#6805](https://github.com/nautobot/nautobot/issues/6805) - Fixed an exception when saving a Dynamic Group of IP Addresses.
- [#6806](https://github.com/nautobot/nautobot/issues/6806) - Fixed a bug that prevented users from accessing the detail views of Location related Dynamic Groups.
- [#6836](https://github.com/nautobot/nautobot/issues/6836) - Fixed various Component Template models incorrectly assume `Notes` support in the API.
- [#6836](https://github.com/nautobot/nautobot/issues/6836) - Fixed CloudNetworkPrefixAssignment, CloudServiceNetworkAssignment, InterfaceVDCAssignment, JobQueueAssignment, ObjectMetadata, PrefixLocationAssignment, VLANLocationAssignment, ControllerManagedDeviceGroupWirelessNetworkAssignment, and ControllerManagedDeviceGroupRadioProfileAssignment models incorrectly assume `Notes` support in the API.
- [#6841](https://github.com/nautobot/nautobot/issues/6841) - Fixed missing termination side when creating from Circuit detail page.
- [#6860](https://github.com/nautobot/nautobot/issues/6860) - Fixed incorrect marking of `channel_width` and `allowed_channel_list` as required fields in the Wireless Radio Profile REST API.
- [#6901](https://github.com/nautobot/nautobot/issues/6901) - Fixed incorrect rendering of cable traces in the case where Modules are part of the hardware definition.
- [#6901](https://github.com/nautobot/nautobot/issues/6901) - Fixed incorrect rendering of device-component (Interface, Front Port, etc.) detail views when Modules are involved.

### Dependencies in v2.4.3

- [#6658](https://github.com/nautobot/nautobot/issues/6658) - Updated dependency `django-constance` to `~4.3.0`.
- [#6658](https://github.com/nautobot/nautobot/issues/6658) - Updated dependency `kubernetes` to `^32.0.0`.
- [#6869](https://github.com/nautobot/nautobot/issues/6869) - Updated dependency `Django` to `~4.2.19`.
- [#6869](https://github.com/nautobot/nautobot/issues/6869) - Updated dependency `django-structlog` to `^9.0.1`.
- [#6894](https://github.com/nautobot/nautobot/issues/6894) - Updated dependency `social-auth-app-django` to `~5.4.3`.
- [#6894](https://github.com/nautobot/nautobot/issues/6894) - Updated dependency `social-auth-core` to `~4.5.6`.

### Documentation in v2.4.3

- [#6894](https://github.com/nautobot/nautobot/issues/6894) - Enabled PyMarkdown `proper-names` checking for some relevant proper nouns and corrected documentation accordingly.

### Housekeeping in v2.4.3

- [#6618](https://github.com/nautobot/nautobot/issues/6618) - Updated GitHub Actions to use ubuntu-24.04 since ubuntu-20.04 is deprecated.
- [#6658](https://github.com/nautobot/nautobot/issues/6658) - Updated development dependency `faker` to `~36.1.0`.
- [#6658](https://github.com/nautobot/nautobot/issues/6658) - Updated development dependency `django-debug-toolbar` to `~5.0.1`.
- [#6846](https://github.com/nautobot/nautobot/issues/6846) - Fixed integration test task to allow passing in pattern match.
- [#6865](https://github.com/nautobot/nautobot/issues/6865) - Refactored `tenancy` app to use `NautobotUIViewSet` and UI component framework.
- [#6869](https://github.com/nautobot/nautobot/issues/6869) - Updated development dependency `factory-boy` to `~3.3.3`.
- [#6894](https://github.com/nautobot/nautobot/issues/6894) - Updated development dependency `faker` to `~36.1.1`.
- [#6894](https://github.com/nautobot/nautobot/issues/6894) - Updated linting dependency `pymarkdownlnt` to `~0.9.28`.

## v2.4.2 (2025-02-03)

### Added in v2.4.2

- [#3319](https://github.com/nautobot/nautobot/issues/3319) - Added the appropriate Namespace to the link for adding a new IP address from an existing Prefix's detail view.
- [#4702](https://github.com/nautobot/nautobot/issues/4702) - Added support for loading GraphQL queries from a Git repository.
- [#5622](https://github.com/nautobot/nautobot/issues/5622) - Added `tags` field on `DeviceFamilyForm`.
- [#6347](https://github.com/nautobot/nautobot/issues/6347) - Added Bulk Edit functionality for LocationType model.
- [#6487](https://github.com/nautobot/nautobot/issues/6487) - Added the ability to perform a shallow copy of a GitRepository instance and to optionally checkout a different branch and/or a specific commit hash.
- [#6767](https://github.com/nautobot/nautobot/issues/6767) - Added cacheable `CustomField.choices` property for retrieving the list of permissible values for a select/multiselect Custom Field.

### Changed in v2.4.2

- [#5781](https://github.com/nautobot/nautobot/issues/5781) - Removed unnecessary `import_jobs()` call during system startup.
- [#6650](https://github.com/nautobot/nautobot/issues/6650) - Changed the `nautobot.apps.utils.get_base_template()` function's fallback behavior to return `"generic/object_retrieve.html"` instead of `"base.html"` in order to more correctly align with its usage throughout Nautobot core.
- [#6650](https://github.com/nautobot/nautobot/issues/6650) - Replaced references to `generic/object_detail.html` with `generic/object_retrieve.html` throughout the code and docs, as `generic/object_detail.html` has been a deprecated alias since v1.4.0.
- [#6808](https://github.com/nautobot/nautobot/issues/6808) - Improved returned data when syncing a Git repository via the REST API.

### Fixed in v2.4.2

- [#3319](https://github.com/nautobot/nautobot/issues/3319) - Fixed an exception when retrieving available IP addresses within a Prefix for certain IPv6 networks.
- [#3319](https://github.com/nautobot/nautobot/issues/3319) - Fixed incorrect potential inclusion of IPv4 IP addresses from the same Namespace when calling `.get_all_ips()` or `.get_utilization()` on an IPv6 Prefix.
- [#6650](https://github.com/nautobot/nautobot/issues/6650) - Fixed rendering of "notes" and "changelog" tabs for object detail views that do not provide a custom HTML template.
- [#6767](https://github.com/nautobot/nautobot/issues/6767) - Improved performance of object detail views when a large number of select/multiselect Custom Fields and also filtered Relationships are defined on the model class.
- [#6767](https://github.com/nautobot/nautobot/issues/6767) - Improved performance of Device detail view by adding appropriate `select_related`/`prefetch_related` calls.
- [#6767](https://github.com/nautobot/nautobot/issues/6767) - Fixed display of Cluster Group in Device detail view.
- [#6810](https://github.com/nautobot/nautobot/issues/6810) - Fixed Bulk Edit Objects job failure when passing a single value to `add_*`/`remove_*` fields.
- [#6812](https://github.com/nautobot/nautobot/issues/6812) - Fixed the incorrect rendering of the Relationship panel in Object Detail View.
- [#6821](https://github.com/nautobot/nautobot/issues/6821) - Fixed the rendering of `Location` in the `RackReservation` detail page.
- [#6825](https://github.com/nautobot/nautobot/issues/6825) - Added links to the `manufacturer` column of the Platform table.
- [#6838](https://github.com/nautobot/nautobot/issues/6838) - Added missing `key` and `label` fields to Relationship Detail View.

### Dependencies in v2.4.2

- [#6717](https://github.com/nautobot/nautobot/issues/6717) - Updated `GitPython` dependency to `~3.1.44`.
- [#6717](https://github.com/nautobot/nautobot/issues/6717) - Updated `django-silk` dependency to `~5.3.2`.
- [#6717](https://github.com/nautobot/nautobot/issues/6717) - Updated `django-tables2` dependency to `~2.7.5`.
- [#6717](https://github.com/nautobot/nautobot/issues/6717) - Updated `mysqlclient` optional dependency to `~2.2.7`.

### Documentation in v2.4.2

- [#346](https://github.com/nautobot/nautobot/issues/346) - Added documentation about Git repository REST API.
- [#6621](https://github.com/nautobot/nautobot/issues/6621) - Added "Security Notices" document to the documentation under **User Guide --> Administration**.

### Housekeeping in v2.4.2

- [#6717](https://github.com/nautobot/nautobot/issues/6717) - Updated `mkdocs-material` documentation dependency to `9.5.50`.
- [#6717](https://github.com/nautobot/nautobot/issues/6717) - Updated `faker` development dependency to `~33.3.1`.
- [#6717](https://github.com/nautobot/nautobot/issues/6717) - Updated `pylint` development dependency to `~3.3.4`.
- [#6779](https://github.com/nautobot/nautobot/issues/6779) - Added integration tests for bulk edit/delete operations for Devices and Locations.
- [#6779](https://github.com/nautobot/nautobot/issues/6779) - Added `BulkOperationsTestCases` class with built-in standard test cases for testing bulk operations.
- [#6842](https://github.com/nautobot/nautobot/issues/6842) - Fix `invoke integration-test` to run standalone, without running the `invoke start` first.

## v2.4.1 (2025-01-21)

### Security in v2.4.1

- [#6780](https://github.com/nautobot/nautobot/issues/6780) - Updated `Django` to `4.2.18` to address `CVE-2024-56374`.

### Fixed in v2.4.1

- [#6427](https://github.com/nautobot/nautobot/issues/6427) - Fixed a bug which allowed several wireless interface types to accept cables.
- [#6489](https://github.com/nautobot/nautobot/issues/6489) - Fixed partial-match filters (such as `__ic` and `__isw`) on fields that have restricted choices (`Prefix.type`, `Interface.type`, etc.) so that partial values are no longer rejected.
- [#6763](https://github.com/nautobot/nautobot/issues/6763) - Fixed the issue where the Wireless Network detail view fails to render when any record in the Controller Managed Device Groups table is missing a VLAN.
- [#6770](https://github.com/nautobot/nautobot/issues/6770) - Fixed breakage of JobButton functionality.
- [#6771](https://github.com/nautobot/nautobot/issues/6771) - Reverted breaking changes to various generic View base class attributes.
- [#6773](https://github.com/nautobot/nautobot/issues/6773) - Fixed an exception when trying to render a Job class to a form when no corresponding Job database record exists.
- [#6776](https://github.com/nautobot/nautobot/issues/6776) - Fixed `FilterTestCase.generic_filter_tests` to again be optional as intended.
- [#6779](https://github.com/nautobot/nautobot/issues/6779) - Fixed Object Bulk Delete and Object Bulk Edit functionalities.
- [#6783](https://github.com/nautobot/nautobot/issues/6783) - Fixed `NautobotDataBaseScheduler` unable to run Scheduled Jobs without job queues assigned.
- [#6786](https://github.com/nautobot/nautobot/issues/6786) - Fixed incorrect marking of `capabilities` field as required on Controller and ControllerManagedDeviceGroup REST APIs.
- [#6792](https://github.com/nautobot/nautobot/issues/6792) - Fixed `natural_key_field_lookups` for proxy models.

### Housekeeping in v2.4.1

- [#6768](https://github.com/nautobot/nautobot/issues/6768) - Fixed link to changelog fragment documentation.
- [#6794](https://github.com/nautobot/nautobot/issues/6794) - Fixed Device factory to ensure that it only selects SoftwareImageFiles that are permitted for a given Device.

## v2.4.0 (2025-01-10)

### Added in v2.4.0

- [#1004](https://github.com/nautobot/nautobot/issues/1004) - Added singleton job functionality to limit specified jobs to one concurrent execution.
- [#6353](https://github.com/nautobot/nautobot/issues/6353) - Added "Bulk Delete Objects" system Job.
- [#6354](https://github.com/nautobot/nautobot/issues/6354) - Added "Bulk Edit Objects" system job.
- [#6462](https://github.com/nautobot/nautobot/issues/6462) - Added tenant relationship to the `ControllerManagedDeviceGroup`
- [#6462](https://github.com/nautobot/nautobot/issues/6462) - Added `tenant` and `description` fields to forms, filtersets and tables for `Controller` and `ControllerManagedDeviceGroup`
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Added REST API support for an `?exclude_m2m=true` query parameter. Specifying this parameter prevents the API from retrieving and serializing many-to-many relations on the requested object(s) (for example, the list of all Prefixes associated with a given VRF), which can in some cases greatly improve the performance of the API and reduce memory and network overhead substantially.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Added automatic optimization of REST API querysets via appropriate `select_related` and `prefetch_related` calls.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Enhanced generic REST API test methods `ListObjectsViewTestCase.test_list_objects_depth_0` and `ListObjectsViewTestCase.test_list_objects_depth_1` to test the `?exclude_m2m=true` query parameter. This enhancement includes checks for missing related fields in the serialized data, which may result in new test failures being seen in Apps using this test class.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Enhanced generic REST API test method `UpdateObjectViewTestCase.test_update_object` to include an idempotency test in combination with the `?exclude_m2m=true` query parameter. This may result in new test failures being seen in Apps using this test class.
- [#6597](https://github.com/nautobot/nautobot/issues/6597) - Added an about page that displays Nautobot and support contract information.
- [#6597](https://github.com/nautobot/nautobot/issues/6597) - Added `NTC_SUPPORT_CONTRACT_EXPIRATION_DATE` configuration setting.
- [#6684](https://github.com/nautobot/nautobot/issues/6684) - Added support for `label-transparent` CSS class.
- [#6684](https://github.com/nautobot/nautobot/issues/6684) - Added "success" log entry counts to the Job Result table.
- [#6751](https://github.com/nautobot/nautobot/issues/6751) - Added NetObs and Load Balancer to Apps Marketplace.

### Changed in v2.4.0

- [#6463](https://github.com/nautobot/nautobot/issues/6463) - Reorganized parts of the Device and VirtualMachine create/edit forms for consistency and clarity.
- [#6529](https://github.com/nautobot/nautobot/issues/6529) - Added VRF's to the Prefixes API.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Changed `DynamicModelChoiceField`, `DynamicModelMultipleChoiceField`, and `MultiMatchModelMultipleChoiceField` default behavior to include `?exclude_m2m=true` as a query parameter to the REST API, improving the typical performance of populating such fields with options.
- [#6652](https://github.com/nautobot/nautobot/issues/6652) - Refined the App Marketplace and Installed Apps views based on stakeholder feedback.
- [#6684](https://github.com/nautobot/nautobot/issues/6684) - Changed the `add` navigation menu buttons to be styled as `primary` (light blue) rather than `info` (darker blue).
- [#6684](https://github.com/nautobot/nautobot/issues/6684) - Updated the "author" and "availability" text in App Marketplace data for clarity.
- [#6684](https://github.com/nautobot/nautobot/issues/6684) - Adjusted the layout and rendering of the App Marketplace and Installed Apps views based on stakeholder feedback.

### Fixed in v2.4.0

- [#6461](https://github.com/nautobot/nautobot/issues/6461) - Fixed inconsistent rendering of DynamicModelChoiceField throughout the UI.
- [#6462](https://github.com/nautobot/nautobot/issues/6462) - Fixed `JSONArrayFormField` error that field is required when default value is used.
- [#6526](https://github.com/nautobot/nautobot/issues/6526) - Fixed an AttributeError that occurred in the UI when editing a `DynamicGroup` with `ipam|prefix` as its content-type and changing the value of the "Present in VRF" field.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Added missing `tags` field to `CircuitTermination`, `Contact`, `DeviceFamily`, `GitRepository`, `MetadataType`, `Team`, `VirtualDeviceContext` REST APIs.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Fixed incorrect field identification logic in REST API testing helper method `ListObjectsViewTestCase.get_depth_fields()`. This may result in new detection of latent issues in Apps by this test case.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Fixed incorrect test logic in REST API generic test case `UpdateObjectViewTestCase.test_update_object()`. This may result in new detection of latent issues in Apps by this test case.
- [#6556](https://github.com/nautobot/nautobot/issues/6556) - Fixed `?depth` query parameter support in `Contact` and `Team` REST APIs.
- [#6601](https://github.com/nautobot/nautobot/issues/6601) - Fixed whitespace in Jinja template renderer.
- [#6602](https://github.com/nautobot/nautobot/issues/6602) - Fixed incorrect naming of `controller_managed_device_groups` filter on the RadioProfile and WirelessNetwork filtersets.
- [#6629](https://github.com/nautobot/nautobot/issues/6629) - Fixed an `AttributeError` that could be raised if a `DynamicModelChoiceField` uses a non-standard `widget`.
- [#6661](https://github.com/nautobot/nautobot/issues/6661) - Fixed the rendering of the dynamic group associable model list tables.
- [#6663](https://github.com/nautobot/nautobot/issues/6663) - Fixed `test_cable_cannot_terminate_to_a_virtual_interface` and `test_cable_cannot_terminate_to_a_wireless_interface` tests so they fail properly.
- [#6738](https://github.com/nautobot/nautobot/issues/6738) - Fixed an exception when cleaning a Prefix that was defined by specifying `network` and `prefix_length`.
- [#6743](https://github.com/nautobot/nautobot/issues/6743) - Fixed incorrect rendering of the "Assigned" column in the IPAddress list view.
- [#6745](https://github.com/nautobot/nautobot/issues/6745) - Restored indentation of child prefixes in Prefix detail view.
- [#6745](https://github.com/nautobot/nautobot/issues/6745) - Improved logic for generation of "available" child prefixes in Prefix detail view.

### Dependencies in v2.4.0

- [#6424](https://github.com/nautobot/nautobot/issues/6424) - Updated `django-structlog` dependency to `^9.0.0`.

### Documentation in v2.4.0

- [#6436](https://github.com/nautobot/nautobot/issues/6436) - Clarified NGINX user in installation documentation.
- [#6480](https://github.com/nautobot/nautobot/issues/6480) - Added kubernetes-related job documentation and removed kubernetes-kind-related documentation.
- [#6512](https://github.com/nautobot/nautobot/issues/6512) - Improved screenshots of UI Component Framework examples.
- [#6512](https://github.com/nautobot/nautobot/issues/6512) - Added before/after example in Migration guide for UI Component Framework.
- [#6639](https://github.com/nautobot/nautobot/issues/6639) - Added User Guide for Wireless Networks.
- [#6654](https://github.com/nautobot/nautobot/issues/6654) - Improved REST API documentation about query parameters and filtering of fields.

### Housekeeping in v2.4.0

- [#6424](https://github.com/nautobot/nautobot/issues/6424) - Updated development dependencies `faker` to `>=33.1.0,<33.2.0` and `watchdog` to `~6.0.0`.
- [#6612](https://github.com/nautobot/nautobot/issues/6612) - Replaced `markdownlint-cli` development dependency with Python package `pymarkdownlnt` and removed Node.js and `npm` from the development Docker images.
- [#6659](https://github.com/nautobot/nautobot/issues/6659) - Enhanced development environment and associated `invoke` tasks to be Nautobot major/minor version aware, such that a different Docker compose `project-name` (and different local Docker image label) will be used for containers in a `develop`-based branch versus a `next`-based branch.
- [#6715](https://github.com/nautobot/nautobot/issues/6715) - Updated development dependency `ruff` to `~0.8.5` and addressed new rules added in that version.
- [#6742](https://github.com/nautobot/nautobot/issues/6742) - Updated various development dependencies to the latest versions available as of January 7.

## v2.4.0b1 (2024-11-25)

### Added in v2.4.0b1

- [#3263](https://github.com/nautobot/nautobot/issues/3263) - Added support for users to specify their timezone from the user Preferences UI.
- [#6087](https://github.com/nautobot/nautobot/issues/6087) - Added JobQueue and JobQueueAssignment models, GraphQL, UI and API.
- [#6087](https://github.com/nautobot/nautobot/issues/6087) - Added a data migration to replace `Job.task_queues` with `JobQueue` instances.
- [#6087](https://github.com/nautobot/nautobot/issues/6087) - Added a data migration to replace `ScheduledJob.queue` with a `JobQueue` instance.
- [#6089](https://github.com/nautobot/nautobot/issues/6089) - Added enforcement of the Job execution soft time limit to the `nautobot-server runjob --local ...` management command.
- [#6089](https://github.com/nautobot/nautobot/issues/6089) - Added automatic refreshing of Git repository Jobs to the `nautobot-server runjob` management command.
- [#6133](https://github.com/nautobot/nautobot/issues/6133) - Added `ObjectDetailContent`, `Tab`, and `Panel` UI component Python classes.
- [#6133](https://github.com/nautobot/nautobot/issues/6133) - Added support for defining an `object_detail_content` attribute on object detail view classes to use the new UI framework.
- [#6134](https://github.com/nautobot/nautobot/issues/6134) - Added support for ordering `Tab` and `Panel` instances by `weight` in code-defined detail views.
- [#6134](https://github.com/nautobot/nautobot/issues/6134) - Added `ObjectsTablePanel` class for rendering related-object tables in code-defined detail views.
- [#6135](https://github.com/nautobot/nautobot/issues/6135) - Enhanced ObjectFieldsPanel: Include TreeModel Hierarchy display, copy button at row level and url fields automatically hyperlinked features.
- [#6136](https://github.com/nautobot/nautobot/issues/6136) - Enhanced `ObjectsTablePanel`: Include features like `include/exclude columns`, set limits of rows, change table panel header title.
- [#6137](https://github.com/nautobot/nautobot/issues/6137) - Added `DataTablePanel` UI component.
- [#6137](https://github.com/nautobot/nautobot/issues/6137) - Added support for `context_table_key` parameter to `ObjectsTablePanel.__init__()`.
- [#6137](https://github.com/nautobot/nautobot/issues/6137) - Added automatic formatting of `JSONField` in `ObjectFieldsPanel`.
- [#6138](https://github.com/nautobot/nautobot/issues/6138) - Added `BaseTextPanel.RenderOptions.CODE` option to render values inside `<pre>` tags using the `TextPanel` and `ObjectTextPanel`.
- [#6139](https://github.com/nautobot/nautobot/issues/6139) - Added `ObjectTextPanel` for rendering text with markdown/json/yaml from given object field.
- [#6139](https://github.com/nautobot/nautobot/issues/6139) - Added `TextPanel` for rendering text with markdown/json/yaml from given value in the context.
- [#6140](https://github.com/nautobot/nautobot/issues/6140) - Added `StatsPanel` UI component Python class.
- [#6141](https://github.com/nautobot/nautobot/issues/6141) - Added `KeyValueTablePanel` and `GroupedKeyValueTablePanel` generic panel classes to Python UI framework.
- [#6141](https://github.com/nautobot/nautobot/issues/6141) - Added `RelationshipModel.get_relationships_with_related_objects()` API allowing direct querying for all objects related to a given object by Relationships.
- [#6141](https://github.com/nautobot/nautobot/issues/6141) - Added object `tags` display to detail views using the Python UI framework.
- [#6142](https://github.com/nautobot/nautobot/issues/6142) - Added `Button` UI framework class and `ObjectDetailContent.extra_buttons` attribute, enabling declarative specification of custom buttons in an object detail view.
- [#6142](https://github.com/nautobot/nautobot/issues/6142) - Added support for App `TemplateExtension` implementations to define `object_detail_buttons`.
- [#6144](https://github.com/nautobot/nautobot/issues/6144) - Added Virtual Device Context Model, API, UI.
- [#6196](https://github.com/nautobot/nautobot/issues/6196) - Added Wireless Models.
- [#6208](https://github.com/nautobot/nautobot/issues/6208) - Added `nautobot.core.events` module, Redis and syslog event brokers, and event publication of CRUD events.
- [#6211](https://github.com/nautobot/nautobot/issues/6211) - Added InterfaceVDCAssignment model and API.
- [#6241](https://github.com/nautobot/nautobot/issues/6241) - Added REST API for Wireless models.
- [#6255](https://github.com/nautobot/nautobot/issues/6255) - Added `KUBERNETES_DEFAULT_SERVICE_ADDRESS`, `KUBERNETES_JOB_MANIFEST`, `KUBERNETES_JOB_POD_NAME`, `KUBERNETES_JOB_POD_NAMESPACE`, `KUBERNETES_SSL_CA_CERT_PATH` and `KUBERNETES_TOKEN_PATH` settings variables to support Kubernetes Job execution.
- [#6258](https://github.com/nautobot/nautobot/issues/6258) - Added optional `role` field to `VirtualDeviceContext`.
- [#6259](https://github.com/nautobot/nautobot/issues/6259) - Added `default_job_queue` field to the Job Model.
- [#6276](https://github.com/nautobot/nautobot/issues/6276) - Added support for Apps to define `object_detail_panels` and `object_detail_tabs` in their `TemplateExtension` classes.
- [#6276](https://github.com/nautobot/nautobot/issues/6276) - Added `nautobot.apps.ui.DistinctViewTab` class for defining detail-view tabs that exist as a distinct view.
- [#6276](https://github.com/nautobot/nautobot/issues/6276) - Added `nautobot.apps.ui.render_component_template` helper function.
- [#6323](https://github.com/nautobot/nautobot/issues/6323) - Added Scheduled Job support for Kubernetes Job Execution.
- [#6324](https://github.com/nautobot/nautobot/issues/6324) - Added Event Broker Config
- [#6325](https://github.com/nautobot/nautobot/issues/6325) - Added event publishing for events: user login, user logout, job failed, user changed password and admin changes user's password.
- [#6326](https://github.com/nautobot/nautobot/issues/6326) - Added event publishing for events: job started, job completed, job failed, schedule job approved and scheduled job denied.
- [#6338](https://github.com/nautobot/nautobot/issues/6338) - Added UI Components for Wireless models.
- [#6348](https://github.com/nautobot/nautobot/issues/6348) - Added "Add virtual device contexts" to the Virtual Device Contexts panel in Device detail view.
- [#6377](https://github.com/nautobot/nautobot/issues/6377) - Added support for `hide_hierarchy_ui` option in `ObjectsTablePanel`.
- [#6387](https://github.com/nautobot/nautobot/issues/6387) - Added a custom SUCCESS log level for use in Nautobot and Nautobot Jobs.
- [#6446](https://github.com/nautobot/nautobot/issues/6446) - Added support for `query_params` to NavMenuItem and NavMenuButton.
- [#6446](https://github.com/nautobot/nautobot/issues/6446) - Added `capabilities` field to Controller and ControllerManagedDeviceGroup.
- [#6488](https://github.com/nautobot/nautobot/issues/6488) - Added a REST API endpoint for rendering Jinja2 templates.
- [#6504](https://github.com/nautobot/nautobot/issues/6504) - Added Apps Marketplace page.
- [#6513](https://github.com/nautobot/nautobot/issues/6513) - Added `pre_tag` helper/filter method to wrap content within `<pre>` tags.
- [#6537](https://github.com/nautobot/nautobot/issues/6537) - Added logic to prevent users from modifying device on Virtual Device Contexts.
- [#6539](https://github.com/nautobot/nautobot/issues/6539) - Added Installed Apps page tile view.
- [#6555](https://github.com/nautobot/nautobot/issues/6555) - Added a Jinja template renderer to the UI.

### Changed in v2.4.0b1

- [#6125](https://github.com/nautobot/nautobot/issues/6125) - Refactored Job run related code to be able to use Job Queues.
- [#6133](https://github.com/nautobot/nautobot/issues/6133) - Converted `Circuit` detail view to use the new UI framework.
- [#6137](https://github.com/nautobot/nautobot/issues/6137) - Converted example app `ExampleModel` detail view to use UI component framework.
- [#6137](https://github.com/nautobot/nautobot/issues/6137) - Converted `ExternalIntegration` detail view to use UI component framework.
- [#6138](https://github.com/nautobot/nautobot/issues/6138) - Changed `ExampleModelUIViewSet` with added example of `TextPanel` usage.
- [#6139](https://github.com/nautobot/nautobot/issues/6139) - Changed `_ObjectCommentPanel` to be subclass of `ObjectTextPanel` and use newly created text panel component.
- [#6140](https://github.com/nautobot/nautobot/issues/6140) - Refactored Tenant detail view to use UI component Python classes.
- [#6142](https://github.com/nautobot/nautobot/issues/6142) - Converted `Secret` related views to use NautobotUIViewSet and UI Framework.
- [#6142](https://github.com/nautobot/nautobot/issues/6142) - Converted `Device` detail view to use UI Framework to define the "Add Components" dropdown.
- [#6196](https://github.com/nautobot/nautobot/issues/6196) - `JSONArrayField` now allows `choices` to be provided in the `base_field` declaration.
- [#6205](https://github.com/nautobot/nautobot/issues/6205) - Changed initial `Nautobot initialized!` message logged on startup to include the Nautobot version number.
- [#6330](https://github.com/nautobot/nautobot/issues/6330) - Refactored `ObjectsTablePanel` to accept either a table class and a queryset or an already initialized table.
- [#6377](https://github.com/nautobot/nautobot/issues/6377) - Converted VRF and RouteTarget UI views to use `NautobotUIViewSet` and `object_detail_content`.
- [#6476](https://github.com/nautobot/nautobot/issues/6476) - Converted `ClusterType` detail view to use UI framework.
- [#6503](https://github.com/nautobot/nautobot/issues/6503) - Addressed Wireless models UI Feedback.

### Deprecated in v2.4.0b1

- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Deprecated the `FilterTestCases.NameOnlyFilterTestCase` and `FilterTestCases.NameSlugFilterTestCase` generic test classes. Apps should migrate to `FilterTestCases.FilterTestCase` with an appropriately defined list of `generic_filter_tests` instead.
- [#6142](https://github.com/nautobot/nautobot/issues/6142) - Deprecated the `TemplateExtension.buttons()` API in favor of `TemplateExtension.object_detail_buttons` implementation based around the UI Component Framework.
- [#6276](https://github.com/nautobot/nautobot/issues/6276) - Deprecated the `TemplateExtension.left_page()`, `TemplateExtension.right_page()`, and `TemplateExtension.full_width_page()` APIs in favor of `TemplateExtension.object_detail_panels` implementation based around the UI Component Framework.

### Removed in v2.4.0b1

- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Removed the previously deprecated `ViewTestCases.BulkImportObjectsViewTestCase` generic test class as obsolete.
- [#6342](https://github.com/nautobot/nautobot/issues/6342) - Removed remnants of the React UI prototype - `NavContext`, `NavGrouping`, `NavItem`, `GetMenuAPIView`, `GetObjectCountsView`, `ViewConfigException`, `get_all_new_ui_ready_routes()`, `get_only_new_ui_ready_routes()`, `is_route_new_ui_ready()`.

### Fixed in v2.4.0b1

- [#6089](https://github.com/nautobot/nautobot/issues/6089) - Fixed warning message `No sanitizer support for <class 'NoneType'> data` emitted by the `nautobot-server runjob --local ...` command.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Fixed incorrect definition of `VirtualMachineFilterSet.cluster` filter.
- [#6137](https://github.com/nautobot/nautobot/issues/6137) - Fixed `ObjectsTablePanel.related_field_name` fallback logic to be more correct.
- [#6137](https://github.com/nautobot/nautobot/issues/6137) - Fixed incorrect configuration of "Contacts", "Dynamic Groups", and "Object Metadata" tables in component-based views.
- [#6139](https://github.com/nautobot/nautobot/issues/6139) - Fixed `body_content_text.html` to properly render different formats like json, yaml or markdown.
- [#6208](https://github.com/nautobot/nautobot/issues/6208) - Fixed duplicate loading of `nautobot_config.py` during Nautobot startup.
- [#6246](https://github.com/nautobot/nautobot/issues/6246) - Fixed accordion collapse/expand behavior when grouped computed fields and/or custom fields are present in a detail view.
- [#6331](https://github.com/nautobot/nautobot/issues/6331) - Added missing `role` field in Virtual Device Context detail view and edit view.
- [#6331](https://github.com/nautobot/nautobot/issues/6331) - Fixed Virtual Device Context edit view layout.
- [#6337](https://github.com/nautobot/nautobot/issues/6337) - Added exception handling and fallback logic for Constance config lookups as `django-constance` 4.x removed some built-in exception handling.
- [#6338](https://github.com/nautobot/nautobot/issues/6338) - Fixed NumericArrayField not respecting numerical order.
- [#6377](https://github.com/nautobot/nautobot/issues/6377) - Fixed Panel rendering to not include the header or footer if the content is only whitespace.
- [#6377](https://github.com/nautobot/nautobot/issues/6377) - Fixed incorrect/unnecessary rendering of many-to-many fields in ObjectFieldsPanel.
- [#6377](https://github.com/nautobot/nautobot/issues/6377) - Fixed various references to `context["object"]` to use `get_obj_from_context()` appropriately.
- [#6394](https://github.com/nautobot/nautobot/issues/6394) - Fixed unexpected error `{'default_job_queue': ['This field cannot be null.']}` on Job Bulk Update.
- [#6394](https://github.com/nautobot/nautobot/issues/6394) - Fixed overriding custom `job_queues` on Job Bulk Update when no changes made on this field.
- [#6395](https://github.com/nautobot/nautobot/issues/6395) - Corrected name of IPAM migration 0050 to match the one released in v2.3.6.
- [#6397](https://github.com/nautobot/nautobot/issues/6397) - Fixed incorrect handling of JobQueue objects in `get_worker_count()`.
- [#6403](https://github.com/nautobot/nautobot/issues/6403) - Fixed wrong Primary IPv6 field label on VirtualDeviceContextForm.
- [#6428](https://github.com/nautobot/nautobot/issues/6428) - Fixed some issues causing failures with reverse migrations.
- [#6537](https://github.com/nautobot/nautobot/issues/6537) - Fixed unexpected failure when adding an interface component to a device from the Device detail view.
- [#6546](https://github.com/nautobot/nautobot/issues/6546) - Fixed inconsistent rendering of the Role column on the Virtual Device Context list table.
- [#6549](https://github.com/nautobot/nautobot/issues/6549) - Added missing `/` to `/api/core/render-jinja-template/` URL.

### Dependencies in v2.4.0b1

- [#5963](https://github.com/nautobot/nautobot/issues/5963) - Updated `django-taggit` to `~6.1.0`.
- [#6252](https://github.com/nautobot/nautobot/issues/6252) - Dropped support for Python 3.8. Python 3.9 is now the minimum version required by Nautobot.
- [#6254](https://github.com/nautobot/nautobot/issues/6254) - Added `kubernetes==31.0.0` development dependency.
- [#6342](https://github.com/nautobot/nautobot/issues/6342) - Removed dependency on `drf-react-template-framework`.
- [#6363](https://github.com/nautobot/nautobot/issues/6363) - Removed direct dependency on `MarkupSafe` as Nautobot does not use it directly, only through the `Jinja2` dependency.
- [#6363](https://github.com/nautobot/nautobot/issues/6363) - Updated dependency `Pillow` to `~11.0.0`.
- [#6363](https://github.com/nautobot/nautobot/issues/6363) - Updated dependency `django-auth-ldap` to `~5.1.0`.
- [#6469](https://github.com/nautobot/nautobot/issues/6469) - Updated dependency `django-silk` to `~5.3.0`.
- [#6549](https://github.com/nautobot/nautobot/issues/6549) - Moved `kubernetes` from a development-only dependency to a required dependency.

### Documentation in v2.4.0b1

- [#6144](https://github.com/nautobot/nautobot/issues/6144) - Added documentation for Virtual Device Contexts.
- [#6254](https://github.com/nautobot/nautobot/issues/6254) - Added documentation of how to use K8s Kind cluster for local K8s integrations development.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Added documentation about migration from template-based views into UI Component Framework.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Added UI Component Framework documentation.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Updated documentation of `development/apps/api/views/` to inform users about preferred usage of UI Component Framework.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Updated docstrings for some of UI related classes to improve auto-generated docs.
- [#6381](https://github.com/nautobot/nautobot/issues/6381) - Added Wireless Model documentation.
- [#6549](https://github.com/nautobot/nautobot/issues/6549) - Added 2.4 release overview.

### Housekeeping in v2.4.0b1

- [#5963](https://github.com/nautobot/nautobot/issues/5963) - Updated development dependency `faker` to `>=30.1.0,<30.2.0`.
- [#5963](https://github.com/nautobot/nautobot/issues/5963) - Updated documentation dependency `towncrier` to `~24.8.0`.
- [#5963](https://github.com/nautobot/nautobot/issues/5963) - Updated `watchdog` to `~5.0.0`.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Removed roughly 800 redundant and/or obsolete test cases.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Merged the `APIViewTestCases.NotesURLViewTestCase.test_notes_url_on_object` generic test function into `APIViewTestCases.GetObjectViewTestCase.test_get_object` generic test function to reduce redundant code and improve test speed.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Merged the `FilterTestCases.FilterTestCase.test_id` generic test function into `FilterTestCases.FilterTestCase.test_filters_generic` generic test function to reduce redundant code and improve test speed.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Removed the `FilterTestCases.FilterTestCase.test_q_filter_exists` generic test function as redundant.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Merged the `ViewTestCases.GetObjectViewTestCase.test_has_advanced_tab` generic test function into `ViewTestCases.GetObjectViewTestCase.test_get_object_with_permission` generic test function to reduce redundant code and improve test speed.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Removed the `ViewTestCases.CreateObjectViewTestCase.test_slug_autocreation` and `test_slug_not_modified` generic test functions as obsolete.
- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Merged the `ViewTestCases.ListObjectsViewTestCase.test_list_view_app_banner` generic test function into `ViewTestCases.ListObjectsViewTestCase.test_list_objects_with_permission` generic test function to reduce redundant code and improve test speed.
- [#6133](https://github.com/nautobot/nautobot/issues/6133) - Moved definition of nav and homepage base classes from `nautobot.core.apps` to new `nautobot.core.ui` module. (These classes are still available to App authors via the same `nautobot.apps.ui` import aliases as previously).
- [#6133](https://github.com/nautobot/nautobot/issues/6133) - Added support for `--quiet` option to `invoke nbshell` task.
- [#6250](https://github.com/nautobot/nautobot/issues/6250) - Improved speed of `JobQueueFactory` when a large number of Jobs are installed.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Added parameter `--fix` to `invoke markdownlint`.
- [#6320](https://github.com/nautobot/nautobot/issues/6320) - Fixed an error when rerunning a test with cached test fixtures that included default job queues.
- [#6493](https://github.com/nautobot/nautobot/issues/6493) - Moved runjob helper functions from `nautobot.extras.management.__init__.py` to `nautobot.extras.management.utils.py`.
