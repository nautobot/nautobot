# Nautobot v3.0

This document describes all new features and changes in Nautobot 3.0.

## Upgrade Actions

### Administrators

- Job approval permissions have been updated in the UI and API. Approvers must now be granted the `extras.change_approvalworkflowstage` and `extras.view_approvalworkflowstage` permissions, replacing the previous requirement for `extras.approve_job`. This change aligns with updates to the approval workflow implementation and permissions model.

### Job Authors & App Developers

- The Data Compliance feature set from the Data Validation Engine App has been moved directly into core. Import paths that reference `nautobot_data_validation_engine.custom_validators.DataComplianceRule` or `nautobot_data_validation_engine.custom_validators.ComplianceError` should be updated to `nautobot.apps.models.DataComplianceRule` and `nautobot.apps.models.ComplianceError`, respectively.
- Code that calls the GraphQL `execute_query()` and `execute_saved_query()` functions may need to be updated to account for changes to the response object returned by these APIs. Specifically, the `response.to_dict()` method is no longer supported, but instead the returned data and any errors encountered may now be accessed directly as `response.data` and `response.errors` respectively.
- Filtering data that supports a `type` filter in the REST API now also supports a corresponding `type` filter in GraphQL. (In Nautobot v2.x and earlier, the filter had to be referenced in GraphQL as `_type` instead.) Filtering by `_type` is still supported where applicable but should be considered deprecated; please update your GraphQL queries accordingly.
- The `approval_required` field from `extras.Job` model has been removed. This is a breaking change for any custom Jobs or applications that reference this field. This functionality has been replaced by a new approval workflow system. For more information on how the new approach works, see [approval workflow documentation](../user-guide/platform-functionality/approval-workflow.md)
- If you're upgrading from Nautobot 2.x, a management command named `check_job_approval_status` is available in 2.x to help identify jobs and scheduled jobs that still have `approval_required=True`. Running this command prior to upgrading can help you detect and address these cases by either clearing scheduled jobs or defining approval workflows for Jobs.
- As a part of adding support for associating a [Device to multiple Clusters](#device-to-multiple-clusters), the Device REST API no longer supports a `cluster` field; the field has been renamed to `clusters` and is now a list of related Clusters rather than a single record. See below for more details.

## Release Overview

### Added

#### Data Validation Engine

The Nautobot Data Validation Engine functionality previously provided as a separate Nautobot App has been migrated into Nautobot as a core feature. (...TODO provide more details here...)

### Changed

#### Device to Multiple Clusters ([#7203](https://github.com/nautobot/nautobot/issues/7203))

The Device model has replaced its single `cluster` foreign-key field with a many-to-many `clusters` field, allowing multiple Clusters to be associatd with a single Device.

To provide a modicum of backwards-compatibility, the Device model and queryset still support a singular `cluster` property which can be retrieved and (in some cases) set for the case of a single associated Cluster, but App authors, Job Authors, and GraphQL users are encouraged to migrate to using `clusters` as soon as possible. The `cluster` property will raise a `MultipleObjectsReturned` exception if the Device in question has more than one associated Cluster.

Note that due to technical limitations, the Device REST API does *not* support a `cluster` field in Nautobot v3, so users of the REST API *must* migrate to reading the `clusters` field where applicable. Assignment of Devices to Clusters via the REST API is now managed via a dedicated endpoint `/api/dcim/device-cluster-assignments/` similar to other many-to-many fields in Nautobot.

### Dependencies

#### GraphQL and GraphiQL Updates

The underlying GraphQL libraries (`graphene`, `graphene-django`, `graphene-django-optimizer`) used by Nautobot have been updated to new major versions, including a new major version of the GraphiQL UI. For the most part this upgrade will be seamless to end users, but the response object returned by Nautobot's `execute_query()` and `execute_saved_query()` Python APIs has changed type -- see [Upgrade Actions](#upgrade-actions) above for specifics.

#### Added Python 3.13 Support and Removed Python 3.9 Support

As Python 3.9 has reached end-of-life, Nautobot 3.0 requires a minimum of Python 3.10. Python 3.13 support was added.
