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
- Job authors should be aware of the ability to log [`success`](#job-success-log-level) messages in Nautobot v2.4 and later and should adopt this log level as appropriate.
- Job authors should be aware of the introduction of [Job Queues](#kubernetes-job-execution-and-job-queue-data-model) as a general-purpose replacement for the Celery-specific `Job.task_queues` attribute, and if a Job specifies its preferred `task_queues`, should verify that the queue selected as its `default_job_queue` after the Nautobot upgrade is correct.

## Release Overview

### Added

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

#### Jinja2 Template Rendering REST API

Nautobot 2.4 adds a new REST API endpoint `/api/core/render-jinja-template/` that can be called to [render a user-provided Jinja2 template](../user-guide/platform-functionality/rendering-jinja-templates.md) with user-provided context data and access to Nautobot's built-in Jinja2 tags and filters. This can be used by users and Apps such as [Nautobot Golden Config](https://docs.nautobot.com/projects/golden-config/en/latest/) to assist with the development and validation of Jinja2 template content.

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
