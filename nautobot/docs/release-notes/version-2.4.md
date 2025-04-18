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

## v2.4.7 (2025-04-14)

### Added in v2.4.7

- [#4171](https://github.com/nautobot/nautobot/issues/4171) - Added `TYPE_NOTES` and `TYPE_URL` to SecretsGroupSecretTypeChoices.
- [#6923](https://github.com/nautobot/nautobot/issues/6923) - Added `AutoPopulateWidget` to support form fields with auto-population logic.
- [#6998](https://github.com/nautobot/nautobot/issues/6998) - Added browser and backend caching for `/api/swagger` OpenAPI endpoint to speed up Swagger and Redoc loading time.
- [#7115](https://github.com/nautobot/nautobot/issues/7115) - Added bulk-edit support for the Relationship model.
- [#7127](https://github.com/nautobot/nautobot/issues/7127) - Added bulk-edit support for the ExportTemplate model.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Added bulk-edit support for the Manufacturer model.

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
- [#7041](https://github.com/nautobot/nautobot/issues/7041) - Added bulk-edit support for the ClusterType model.
- [#7044](https://github.com/nautobot/nautobot/issues/7044) - Added bulk-edit support for the ClusterGroup model.
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
- [#7001](https://github.com/nautobot/nautobot/issues/7001) - Added bulk-edit support for the RIR model.

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
