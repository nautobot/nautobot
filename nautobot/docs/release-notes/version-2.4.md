<!-- markdownlint-disable MD024 -->

# Nautobot v2.4

This document describes all new features and changes in Nautobot 2.4.

## Upgrade Actions

### Administrators

- Nautobot 2.4 [drops support for Python 3.8](#removed-python-38-support), so any existing Nautobot deployment in Python 3.8 will need to be replaced with a new deployment using a newer Python version before upgrading to Nautobot v2.4 or later.
- Administrators should familiarize themselves with the new [Event Publication Framework](#event-publication-framework) and the possibilities it enables for improved monitoring of Nautobot operations.
- Administrators of Kubernetes-based Nautobot deployments should familiarize themselves with the new [capabilities](#kubernetes-job-execution-and-job-queue-data-model) that Nautobot 2.4 provides for Job execution in such environments and may wish to update their Nautobot configuration to take advantage of these capabilities.

### Job Authors & App Developers

- App developers should begin to adopt the [UI Component Framework](#ui-component-framework) introduced in Nautobot 2.4, as this will reduce the amount of boilerplate HTML/CSS content that they need to develop and maintain, and will insulate Apps from future CSS changes planned for Nautobot v3.
- Additionally, App developers should familiarize themselves with the new [Event Publication Framework](#event-publication-framework) and the possibilities it enables for Apps to publish their own relevant events.
- As a side benefit of adding [REST API `exclude_m2m` support](#rest-api-exclude_m2m-support), the Nautobot REST API `ViewSet` classes now attempt to intelligently apply `select_related()` and/or `prefetch_related()` optimizations to the `queryset` associated to a given REST API viewset. Apps defining their own REST API viewsets (and requiring Nautobot 2.4.0 or later) can typically remove most explicit calls to `select_related()` and `prefetch_related()`; furthermore, in order to benefit most from the `exclude_m2m=true` query parameter, apps in Nautobot 2.4.0 and later **should not** explicitly `prefetch_related()` many-to-many related fields any longer. (Explicit calls to `select_related()` and `prefetch_related()` may still be necessary and appropriate if your API serializer needs to perform nested lookups, as the automatic optimization here currently only understands directly related object lookups.)
- Job authors should be aware of the ability to log [`success`](#job-success-log-level) messages in Nautobot v2.4 and later and should adopt this log level as appropriate.
- Job authors should be aware of the introduction of [Job Queues](#kubernetes-job-execution-and-job-queue-data-model) as a general-purpose replacement for the Celery-specific `Job.task_queues` attribute, and if a Job specifies its preferred `task_queues`, should verify that the queue selected as its `default_job_queue` after the Nautobot upgrade is correct.

## Release Overview

### Added

#### Apps Marketplace Page and Installed Apps Page Tile View

Nautobot 2.4 introduces Apps Marketplace page containing information about available but not installed Nautobot Apps. In addition to that, Installed Apps page is getting a brand-new tile view as an alternative to already existing list view.

#### Event Publication Framework

Nautobot now includes a general-purpose, extensible [event publication framework](../user-guide/platform-functionality/events.md) for publication of system event notifications to other systems such as Redis publish/subscribe, syslog, Kafka, and others. An abstract `EventBroker` API can be implemented and extended with system-specific functionality to enable publication of Nautobot events to any desired system.

As of Nautobot 2.4.0, Nautobot publishes events with the following topics:

- `nautobot.create.<app>.<model>`
- `nautobot.update.<app>.<model>`
- `nautobot.delete.<app>.<model>`
- `nautobot.users.user.login`
- `nautobot.users.user.logout`
- `nautobot.users.user.change_password`
- `nautobot.admin.user.change_password`
- `nautobot.jobs.job.started`
- `nautobot.jobs.job.completed`
- `nautobot.jobs.approval.approved`
- `nautobot.jobs.approval.denied`

Nautobot Apps can also make use of this framework to publish additional events specific to the App's functionality as desired.

#### Jinja2 Template Rendering Tool

Nautobot 2.4 adds a new REST API endpoint `/api/core/render-jinja-template/` that can be called to [render a user-provided Jinja2 template](../user-guide/platform-functionality/rendering-jinja-templates.md) with user-provided context data and access to Nautobot's built-in Jinja2 tags and filters. This can be used by users and Apps such as [Nautobot Golden Config](https://docs.nautobot.com/projects/golden-config/en/latest/) to assist with the development and validation of Jinja2 template content. There is a UI at `/render-jinja-template/` that provides a form for entering template content and context data to render a template. This UI can also be accessed from a link in the footer of any Nautobot page.

#### Job `success` Log Level

Jobs can now once again log `success` messages as a new logging level which will be appropriately labeled and colorized in Job Result views.

```python
self.logger.success("All data is valid.")
```

#### Kubernetes Job Execution and Job Queue Data Model

When running in a Kubernetes (k8s) deployment, such as with Nautobot's [Helm chart](https://docs.nautobot.com/projects/helm-charts/en/stable/), Nautobot now supports an alternative method of running Nautobot Jobs - instead of (or in addition to) running one or more Celery Workers as long-lived persistent pods, Nautobot can dispatch Nautobot Jobs to be executed as short-lived [Kubernetes Job](https://kubernetes.io/docs/concepts/workloads/controllers/job/) task pods.

In support of this functionality, Nautobot now supports the definition of [`JobQueue` records](../user-guide/platform-functionality/jobs/jobqueue.md), which represent either a Celery task queue **or** a Kubernetes job queue. Nautobot Jobs can be associated to queues of either or both types, and the Job Queue selected when submitting a Job will dictate whether it is executed via Celery or via Kubernetes.

Refer to the [Jobs documentation](../user-guide/platform-functionality/jobs/index.md) for more details.

#### Per-user Time Zone Support

Users can now configure their preferred display time zone via the User Preferences UI and Nautobot will display dates and times in the configured time zone for each user.

#### REST API `exclude_m2m` Support

Added REST API support for an `?exclude_m2m=true` query parameter. Specifying this parameter prevents the API from retrieving and serializing many-to-many relations on the requested object(s) (for example, the list of all Prefixes associated with a given VRF), which can in some cases greatly improve the performance of the API and reduce memory and network overhead substantially.

A future Nautobot major release may change the REST API behavior to make `exclude_m2m=true` the default behavior.

Additionally, the `DynamicModelChoiceField` and related form fields have been enhanced to use `exclude_m2m=true` when querying the REST API to populate their options, which can in some cases significantly improve the responsiveness of these fields.

#### Singleton Jobs

Job authors can now set their jobs to only allow a single concurrent execution across all workers, preventing mistakes where, e.g., data synchronization jobs accidentally run twice and create multiple instances of the same data. This functionality and the corresponding setting are documented in [the section on developing Jobs](../development/jobs/index.md).

#### UI Component Framework

Nautobot's new [UI Component Framework](../development/core/ui-component-framework.md) provides a set of Python APIs for defining parts of the Nautobot UI without needing, in many cases, to write custom HTML templates. In this release of Nautobot, the focus is primarily on the definition of object "detail" views as those were the most common cases where custom templates have been required in the past.

[Adoption of this framework](../development/apps/migration/ui-component-framework/index.md) significantly reduces the amount of boilerplate needed to define an object detail view, drives increased self-consistency across views, and encourages code reuse. It also insulates Apps from the details of Nautobot's CSS (Bootstrap 3 framework), smoothing the way for Nautobot to adopt a new CSS framework in the future with minimal impact to compliant apps.

App [template extensions](../development/apps/api/ui-extensions/object-views.md) of Nautobot core views can also be reimplemented using the UI Component Framework and are recommended to do so.

As of Nautobot 2.4.0, the following detail views have been migrated to use the UI Component Framework:

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

#### Virtual Device Context Data Models

Nautobot 2.4 adds a [`VirtualDeviceContext`](../user-guide/core-data-model/dcim/virtualdevicecontext.md) data model to support modeling of logical partitions of physical network devices, such as Cisco Nexus Virtual Device Contexts, Juniper Logical Systems, Arista Multi-instance EOS, and so forth. Device Interfaces can be associated to Virtual Device Contexts via the new `InterfaceVDCAssignment` model as well.

#### Wireless Data Models

Nautobot 2.4 adds the data models [`WirelessNetwork`](../user-guide/core-data-model/wireless/wirelessnetwork.md), [`RadioProfile`](../user-guide/core-data-model/wireless/radioprofile.md), and [`SupportedDataRate`](../user-guide/core-data-model/wireless/supporteddatarate.md), enabling Nautobot to model campus wireless networks. In support of this functionality, the [`Controller`](../user-guide/core-data-model/dcim/controller.md) and [`ControllerManagedDeviceGroup`](../user-guide/core-data-model/dcim/controllermanageddevicegroup.md) models have been enhanced with additional capabilities as well.

Refer to the [Wireless](../user-guide/core-data-model/wireless/index.md) documentation for more details.

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

As Python 3.8 has reached end-of-life, Nautobot 2.4 requires a minimum of Python 3.9.

<!-- towncrier release notes start -->
## v2.4.0b1 (2024-11-25)

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

### Changed

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

### Deprecated

- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Deprecated the `FilterTestCases.NameOnlyFilterTestCase` and `FilterTestCases.NameSlugFilterTestCase` generic test classes. Apps should migrate to `FilterTestCases.FilterTestCase` with an appropriately defined list of `generic_filter_tests` instead.
- [#6142](https://github.com/nautobot/nautobot/issues/6142) - Deprecated the `TemplateExtension.buttons()` API in favor of `TemplateExtension.object_detail_buttons` implementation based around the UI Component Framework.
- [#6276](https://github.com/nautobot/nautobot/issues/6276) - Deprecated the `TemplateExtension.left_page()`, `TemplateExtension.right_page()`, and `TemplateExtension.full_width_page()` APIs in favor of `TemplateExtension.object_detail_panels` implementation based around the UI Component Framework.

### Removed

- [#6108](https://github.com/nautobot/nautobot/issues/6108) - Removed the previously deprecated `ViewTestCases.BulkImportObjectsViewTestCase` generic test class as obsolete.
- [#6342](https://github.com/nautobot/nautobot/issues/6342) - Removed remnants of the React UI prototype - `NavContext`, `NavGrouping`, `NavItem`, `GetMenuAPIView`, `GetObjectCountsView`, `ViewConfigException`, `get_all_new_ui_ready_routes()`, `get_only_new_ui_ready_routes()`, `is_route_new_ui_ready()`.

### Fixed

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

### Dependencies

- [#5963](https://github.com/nautobot/nautobot/issues/5963) - Updated `django-taggit` to `~6.1.0`.
- [#6252](https://github.com/nautobot/nautobot/issues/6252) - Dropped support for Python 3.8. Python 3.9 is now the minimum version required by Nautobot.
- [#6254](https://github.com/nautobot/nautobot/issues/6254) - Added `kubernetes==31.0.0` development dependency.
- [#6342](https://github.com/nautobot/nautobot/issues/6342) - Removed dependency on `drf-react-template-framework`.
- [#6363](https://github.com/nautobot/nautobot/issues/6363) - Removed direct dependency on `MarkupSafe` as Nautobot does not use it directly, only through the `Jinja2` dependency.
- [#6363](https://github.com/nautobot/nautobot/issues/6363) - Updated dependency `Pillow` to `~11.0.0`.
- [#6363](https://github.com/nautobot/nautobot/issues/6363) - Updated dependency `django-auth-ldap` to `~5.1.0`.
- [#6469](https://github.com/nautobot/nautobot/issues/6469) - Updated dependency `django-silk` to `~5.3.0`.
- [#6549](https://github.com/nautobot/nautobot/issues/6549) - Moved `kubernetes` from a development-only dependency to a required dependency.

### Documentation

- [#6144](https://github.com/nautobot/nautobot/issues/6144) - Added documentation for Virtual Device Contexts.
- [#6254](https://github.com/nautobot/nautobot/issues/6254) - Added documentation of how to use K8s Kind cluster for local K8s integrations development.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Added documentation about migration from template-based views into UI Component Framework.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Added UI Component Framework documentation.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Updated documentation of `development/apps/api/views/` to inform users about preferred usage of UI Component Framework.
- [#6275](https://github.com/nautobot/nautobot/issues/6275) - Updated docstrings for some of UI related classes to improve auto-generated docs.
- [#6381](https://github.com/nautobot/nautobot/issues/6381) - Added Wireless Model documentation.
- [#6549](https://github.com/nautobot/nautobot/issues/6549) - Added 2.4 release overview.

### Housekeeping

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
