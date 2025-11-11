# Nautobot v3.0

This document describes all new features and changes in Nautobot 3.0.

## Upgrade Actions

### Administrators

- Job approval permissions have been updated in the UI and API. Approvers must now be granted the `extras.change_approvalworkflowstage` and `extras.view_approvalworkflowstage` permissions, replacing the previous requirement for `extras.approve_job`. This change aligns with updates to the approval workflow implementation and permissions model.
- The `approval_required` field from `extras.Job` model has been removed. This is a breaking change for any custom Jobs or applications that reference this field. This functionality has been replaced by a new approval workflow system. For more information on how the new approach works, see [approval workflow documentation](../user-guide/platform-functionality/approval-workflow.md)
    - If you're upgrading from Nautobot 2.x, a management command, `nautobot-server check_job_approval_status` is available in 2.x to help identify jobs and scheduled jobs that still have `approval_required=True`. Running this command prior to upgrading can help you detect and address these cases by either clearing scheduled jobs or defining approval workflows for Jobs.
- A small number of breaking [filter field changes](#filter-standardization-improvements-1889) may impact Dynamic Group filter definitions; you are recommended to run `nautobot-server validate_models extras.dynamicgroup` (or the newly added `Validate Model Data` system Job) after the upgrade to identify any impacted Dynamic Groups.

### Job Authors & App Developers

- Apps that provide any user interface will likely require updates to account for the [Bootstrap upgrade from v3.4 to v5.3](#bootstrap-upgrade-from-v34-to-v53) described below.
- The Data Compliance feature set from the Data Validation Engine App has been moved directly into core. Import paths that reference `nautobot_data_validation_engine.custom_validators.DataComplianceRule` or `nautobot_data_validation_engine.custom_validators.ComplianceError` should be updated to `nautobot.apps.models.DataComplianceRule` and `nautobot.apps.models.ComplianceError`, respectively.
- Code that calls the GraphQL `execute_query()` and `execute_saved_query()` functions may need to be updated to account for changes to the response object returned by these APIs. Specifically, the `response.to_dict()` method is no longer supported, but instead the returned data and any errors encountered may now be accessed directly as `response.data` and `response.errors` respectively.

### REST API Users

- Filtering data that supports a `type` filter in the REST API now also supports a corresponding `type` filter in GraphQL. (In Nautobot v2.x and earlier, the filter had to be referenced in GraphQL as `_type` instead.) Filtering by `_type` is still supported where applicable but should be considered deprecated; please update your GraphQL queries accordingly.
- As a part of adding support for associating a [Device to multiple Clusters](#device-to-multiple-clusters-7203), the Device REST API no longer supports a `cluster` field; the field has been renamed to `clusters` and is now a list of related Clusters rather than a single record. See below for more details.
- The REST API now defaults to excluding many-to-many fields (except for `tags`, `content_types`, and `object_types`) by default. Any code that relies on including many-to-many fields in the REST API response must explicitly request them by specifying the `exclude_m2m=False` query parameter. Pynautobot and Nautobot Ansible users should ensure they are on the latest versions to maintain backwards compatibility. See [Many-to-Many Fields in REST API](#many-to-many-fields-in-rest-api-7456) below for more details.

## Release Overview

### Breaking Changes

#### Many-to-Many Fields in REST API ([#7456](https://github.com/nautobot/nautobot/issues/7456))

In order to improve performance at scale, the REST API now defaults to excluding many-to-many fields (except for `tags`, `content_types`, and `object_types`) by default. Any code that relies on including many-to-many fields in the REST API response must explicitly request them by specifying the `exclude_m2m=False` query parameter. See [Filtering Included Fields](../user-guide/platform-functionality/rest-api/filtering.md#filtering-included-fields) for more details.

Pynautobot users should ensure they add `exclude_m2m=False` to an individual request (`nb.dcim.devices.all(exclude_m2m=False)`) or (in pynautobot v3.0.0+) set the default for all requests (`import pynautobot; nb = pynautobot.api(url, token, exclude_m2m=False)`) to maintain prior behavior.

Nautobot Ansible users (using v6.0.0+ and pynautobot v3.0.0+) should see no change required when using module or inventory plugins. When using a lookup plugin, however, they will need to use the `api_filters` parameter to include M2M fields. For example: `api_filters='exclude_m2m=False'`.

#### Removed Python Code

Many previously deprecated classes have been fully removed now (see full table below). The most notable removal is the original `PluginConfig` class, which was replaced by `NautobotAppConfig` in v1.5.2. If your app still imports and inherits from `PluginConfig`, you should migrate to using `NautobotAppConfig` before upgrading to Nautobot 3.0.

To assist with identifying any remaining instances of deprecated code in your codebase, new rules have been added to [`pylint-nautobot`](https://docs.nautobot.com/projects/pylint-nautobot/en/latest/) in version v0.4.3+ that will flag any code that still imports and inherits from any of the deprecated classes.

??? info "Full table of code removals"
    {data-table user-guide/administration/upgrading/from-v2/tables/v3-code-removals.yaml}

#### Removed HTML Templates

Many legacy HTML templates have been removed. The majority of the removed templates are model specific such as `circuits/circuit.html` or `dcim/device/base.html` and have been superseded by generic templates such as `generic/object_retrieve.html`.

In order to ease the transition from these deprecated templates for app developers, we have included a migration script in Nautobot v2.4.21+ that will recursively parse through a directory's html files and replace any extends directives (`{% extends ... %}`) that reference a deprecated template with the replacement template. This script does not require Nautobot to be running and it can be run with the command `nautobot-migrate-deprecated-templates <path> [--dry-run]`. For more details, including a full table of deprecated templates and their replacements, see [Deprecated Templates](../development/apps/migration/code-updates.md#deprecated-templates).

#### Removed Branding Options

Removed support for branding configuration options of `header_bullet`, `nav_bullet`, `javascript`, and `css`. Bullets are no longer used at all in the 3.0 design.

### Added

#### UI Updates

Nautobot 3.0 introduces a refreshed user interface, building on the migration from Bootstrap 3 to Bootstrap 5 with several major enhancements:

##### Search

The search experience has been completely reimagined. A single, always-available search bar is now present throughout the application, accessible via `Ctrl+K` or `Command+K`. Advanced search syntax, such as `in:<model name>`, allows you to target specific models directly. The search results page now provides clearer visibility into active search parameters and makes it easy to distinguish between basic and advanced queries.

##### Saved Views

Saved Views have been improved to display their type more prominently, making it easier to identify when a Saved View is active and to understand the filters or configurations being applied. This streamlines workflows and reduces confusion when working with complex data sets.

##### Navigation Bar

The Navigation Bar has been redesigned for greater efficiency and usability. It now features support for marking items as favorites, incorporates intuitive icons, and uses a modern flyout design to maximize space and accessibility. Navigation is more consolidated, helping users quickly find and access key areas of Nautobot.

#### Load Balancer Models

TODO: Fill in

#### VPN Models

Nautobot 3.0 adds a [`VPN`](../user-guide/core-data-model/vpn/vpn.md) data model to support modeling Virtual Private Networks (VPNs), including reusable profiles, policies, and tunnel endpoints. These models enable you to define IKE (Phase 1) and IPSec (Phase 2) policy parameters, manage tunnel endpoints, and associate VPNs with roles and secrets. Additionally, VPNs may optionally be associated with tenants so that administrators can indicate ownership of related model instances.

Key Use Cases include:

- Site-to-site IPSec VPN tunnel (transport mode)
- Site-to-site IPSec VPN tunnel (tunnel mode)
- Single hub-and-spoke VPN
- Multiple hub-and-spoke VPNs

#### Device Uniqueness Flexibility

Device Uniqueness is now less restrictive. Current behavior of `Location + Tenant + Name` is maintained in migration, but now in addition you can configure to `Device name must be globally unique` and `No enforced uniqueness` as well as you can set `Device name required (cannot be blank or null)`.

#### Approval Workflows

[Approval Workflows](../user-guide/platform-functionality/approval-workflow.md) allows for a multi-stage review and approval of processes before making changes, running or creating specific objects in the system. They are defined in advance and attached to specific models based on certain constraints. Use cases include:

- Preventing accidental deletion of critical data by requiring manager approval before deletion jobs run.
- Requiring security team sign-off before enabling network changes in production.
- Ensuring multiple stakeholders approve large-scale bulk edits.
- Mandating peer review for scheduled jobs that affect multiple systems.

#### Data Validation Engine

The [Nautobot Data Validation Engine](../user-guide/platform-functionality/data-validation.md) functionality previously provided as a separate Nautobot App has been migrated into Nautobot as a core feature.

The data validation engine offers a set of user definable rules which are used to enforce business constraints on the data in Nautobot. These rules are tied to models and each rule is meant to enforce one aspect of a business use case.

Supported rule types include:

- Regular expression
- Min/max value
- Required fields
- Unique values

Additionally Data Compliance allows you to create validations on your data without actually enforcing them and easily convert them to enforcements once all of your data is compliant.

#### ECharts

[ECharts](https://echarts.apache.org/en/index.html) is now included in the base image, with abstractions provided to easily add [custom charts using ECharts](../user-guide/platform-functionality/echarts.md).

#### GraphQL

You will notice a fresh new look for the GraphiQL interface, which has been upgraded to version 2.4.7. This update brings a modernized UI, improved usability, and better alignment with Nautobot's theming. Most user workflows remain unchanged, but you may find enhanced features such as improved query editing, autocompletion, and response formatting.

### Changed

#### Bootstrap upgrade from v3.4 to v5.3

Nautobot now uses Bootstrap v5.3 as its underlying theming and layout engine. The base Nautobot UI has been refreshed accordingly. Apps will generally require corresponding updates for their UI to render properly. The impact of this upgrade will be much reduced if the App has already adopted the [UI Component Framework](../development/apps/migration/ui-component-framework/index.md) introduced previously in Nautobot v2.4. A [migration script](../development/apps/migration/from-v2/upgrading-from-bootstrap-v3-to-v5.md#migration-script) is included in Nautobot 3.x to automate many of the HTML and CSS updates for App developers.

#### Device to Multiple Clusters ([#7203](https://github.com/nautobot/nautobot/issues/7203))

The Device model has replaced its single `cluster` foreign-key field with a many-to-many `clusters` field, allowing multiple Clusters to be associatd with a single Device.

To provide a modicum of backwards-compatibility, the Device model and queryset still support a singular `cluster` property which can be retrieved and (in some cases) set for the case of a single associated Cluster, but App authors, Job Authors, and GraphQL users are encouraged to migrate to using `clusters` as soon as possible. The `cluster` property will raise a `MultipleObjectsReturned` exception if the Device in question has more than one associated Cluster.

Note that due to technical limitations, the Device REST API does *not* support a `cluster` field in Nautobot v3, so users of the REST API *must* migrate to reading the `clusters` field where applicable. Assignment of Devices to Clusters via the REST API is now managed via a dedicated endpoint `/api/dcim/device-cluster-assignments/` similar to other many-to-many fields in Nautobot.

#### Filter Standardization Improvements ([#1889](https://github.com/nautobot/nautobot/issues/1889))

To make Nautobot's UI, REST API, and GraphQL filters more self-consistent and standardized, the default filter type for foreign-key and one-to-one model fields has been changed from a single-value filter (`ModelChoiceFilter`) to a multi-value filter (`ModelMultipleChoiceFilter`). This change affects a small number of filters in Nautobot core, as most such fields were already explicitly covered by a `ModelMultipleChoiceFilter` or one of its derivatives, but the following implicit filters are known to have been affected by this change (in addition to any App model filters on one-to-one and foreign-key fields that also were not explicitly defined otherwise):

- Front Port Templates `rear_port_template` filter
- Power Outlets `power_port` filter
- Module Bays `parent_module` filter
- Job Log Entries `job_result` filter
- Job Results `user` filter
- IP Address to Interface `ip_address` filter

For users of the UI and REST API, this is purely a feature enhancement to the above filters, as specifying single values in the URL query parameters remains supported, but multiple values are also supported now (for example `/api/extras/job-log-entries/?job_result=<uuid1>&job_result=<uuid2>`.)

For users of GraphQL, this is also a feature enhancement, as queries using the above filters can now specify either a single value (`job_log_entries (job_result: "<uuid>") { message }`) as before, or can now be updated to specify a list of values instead (`job_log_entries (job_result: ["<uuid1>", "<uuid2>"]) { message }`) if desired.

!!! warning "Impact to Dynamic Groups"
    For Dynamic Groups using the above filters, the group `filter` will need to be updated to replace the single string value with a list of strings, for example changing:

    ```no-highlight
    {"rear_port_template": "74aac78c-fabb-468c-a036-26c46c56f27a"}
    ```

    to

    ```no-highlight
    {"rear_port_template": ["74aac78c-fabb-468c-a036-26c46c56f27a"]}
    ```

    You can identify impacted Dynamic Groups by running the `nautobot-server validate_models extras.dynamicgroup` management command, or the new `Validate Model Data` system Job; in the above case, the invalid group filter would be reported as below:

    ```no-highlight
    # nautobot-server validate_models extras.dynamicgroup
    Validating 1 models.
    extras.DynamicGroup
    ~~~~~ Model: `extras.DynamicGroup` Instance: `Front Port Template Legacy` Error: `{'rear_port_template': ['Enter a list of values.']}`. ~~~~~
    ```

### Removed

#### Button on Navbar

Buttons were removed from the NavBar as our research indicated they were infrequently used and caused clutter.

#### Job Approval Process

The Job Approval process was removed and replaced by Workflow Approvals.

### Dependencies

#### GraphQL and GraphiQL Updates

The underlying GraphQL libraries (`graphene`, `graphene-django`, `graphene-django-optimizer`) used by Nautobot have been updated to new major versions, including a new major version of the GraphiQL UI. For the most part this upgrade will be seamless to end users, but the response object returned by Nautobot's `execute_query()` and `execute_saved_query()` Python APIs has changed type -- see [Upgrade Actions](#upgrade-actions) above for specifics.

#### Added Python 3.13 Support and Removed Python 3.9 Support

As Python 3.9 has reached end-of-life, Nautobot 3.0 requires a minimum of Python 3.10. Python 3.13 support was added.

#### Added Echarts

Added the JavaScript Library ECharts version 6.0.0.

<!-- pyml disable-num-lines 2 blanks-around-headers -->

<!-- towncrier release notes start -->

## v3.0.0rc1 (2025-11-11)

### Breaking Changes in v3.0.0rc1

- [#8051](https://github.com/nautobot/nautobot/issues/8051) - Removed deprecated HTML templates that are no longer used.
- [#8056](https://github.com/nautobot/nautobot/issues/8056) - `BaseBreadcrumbItem.as_pair` now returns `iterator` instead of `tuple[str, str]` to support dynamic breadcrumb items.
- [#8081](https://github.com/nautobot/nautobot/issues/8081) - Removed support for branding options of `header_bullet`, `nav_bullet`, `javascript`, and `css`.

### Added in v3.0.0rc1

- [#7873](https://github.com/nautobot/nautobot/issues/7873) - Added support for assigning Configuration Contexts to Device Families.
- [#8012](https://github.com/nautobot/nautobot/issues/8012) - Added Version Control and Ansible Automation to marketplace.
- [#8014](https://github.com/nautobot/nautobot/issues/8014) - Added vpn.VPNTunnelEndpoint model constraints
- [#8056](https://github.com/nautobot/nautobot/issues/8056) - Added `BaseModel.page_title` property with preferred object representation for titles.
- [#8064](https://github.com/nautobot/nautobot/issues/8064) - Added `ValidateModelData` system Job.
- [#8091](https://github.com/nautobot/nautobot/issues/8091) - Added dark mode support for `highlight.js`.
- [#8093](https://github.com/nautobot/nautobot/issues/8093) - Added Load Balancer app and data models.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Added the `vrfs` filter to Devices and VirtualMachines.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Added the `secrets_groups` filter to Secrets.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Added the `ancestors` filter to Prefixes.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Added the `services` filter to IPAddresses.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Added the `load_balancer_pool_members` and `virtual_servers` filters to CertificateProfiles.
- [#8125](https://github.com/nautobot/nautobot/issues/8125) - Added `bus-globe`, `bus-shield` and `bus-shield-check` Nautobot icons.
- [#8130](https://github.com/nautobot/nautobot/issues/8130) - Added validation of model constraints when creating/editing an Approval Workflow Definition.
- [#8130](https://github.com/nautobot/nautobot/issues/8130) - Added "Approval State" and "Enabled" filters to Scheduled Job filterset.
- [#8130](https://github.com/nautobot/nautobot/issues/8130) - Added "Approval State" and "Enabled" columns to Scheduled Job table.
- [#8143](https://github.com/nautobot/nautobot/issues/8143) - Merged up latest content and fixes from Nautobot v2.4.22.

### Changed in v3.0.0rc1

- [#7462](https://github.com/nautobot/nautobot/issues/7462) - Changed `Device.device_redundancy_group_priority` and `InterfaceRedundancyGroupAssociation.priority` from `PositiveSmallIntegerField` to `PositiveIntegerField` to allow a wider range of values.
- [#8056](https://github.com/nautobot/nautobot/issues/8056) - Removed last breadcrumb item from custom breadcrumbs implementations.
- [#8057](https://github.com/nautobot/nautobot/issues/8057) - Echart Theme is derived from the browser and not require the Python developer to assign.
- [#8057](https://github.com/nautobot/nautobot/issues/8057) - Added new `LIGHTER_GREEN_AND_RED_ONLY` EChartsThemeColors choice.
- [#8069](https://github.com/nautobot/nautobot/issues/8069) - Set all Select2 placeholders to hyphens: `---------`.
- [#8071](https://github.com/nautobot/nautobot/issues/8071) - Underlined links in blue colored table rows and alerts.
- [#8074](https://github.com/nautobot/nautobot/issues/8074) - Enforced constant width on the first column of attribute tables.
- [#8075](https://github.com/nautobot/nautobot/issues/8075) - Changed Rack list view to not show space utilization and power utilization columns by default.
- [#8080](https://github.com/nautobot/nautobot/issues/8080) - Removed "Log in" item from nav menu. When user is unauthenticated and not on login page the "Log in" button now shows up in the header.
- [#8088](https://github.com/nautobot/nautobot/issues/8088) - Changed nav menu logo and icon size to 32px.
- [#8090](https://github.com/nautobot/nautobot/issues/8090) - Updated titles for Modules and Cable trace.
- [#8090](https://github.com/nautobot/nautobot/issues/8090) - Improved breadcrumbs for Rack Elevations and Software Versions.
- [#8090](https://github.com/nautobot/nautobot/issues/8090) - Improved `helpers.pre_tag` rendering for empty values.
- [#8098](https://github.com/nautobot/nautobot/issues/8098) - When applying filters, use selected advanced filter even if not manually applied by user (i.e. even if not added to the selected filters list with "Add Filter" button).
- [#8099](https://github.com/nautobot/nautobot/issues/8099) - Changed icon for "Rename" buttons from `mdi-pencil` to `mdi-rename`.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Changed the badge color from blue to gray for the ObjectsTablePanel badges without a link.
- [#8125](https://github.com/nautobot/nautobot/issues/8125) - Changed VPN navigation icon from `atom` to `shield-check`.
- [#8130](https://github.com/nautobot/nautobot/issues/8130) - Changed Scheduled Job list view to not hide non-enabled schedules by default.
- [#8131](https://github.com/nautobot/nautobot/issues/8131) - Changed the `nautobot-migrate-bootstrap-v3-to-v5` script to also call the `nautobot-migrate-deprecated-templates` script by default.

### Fixed in v3.0.0rc1

- [#8058](https://github.com/nautobot/nautobot/issues/8058) - Fixed some tests skipped in v3.
- [#8060](https://github.com/nautobot/nautobot/issues/8060) - Fixed dark mode for Rack Elevation view to match Rack view.
- [#8062](https://github.com/nautobot/nautobot/issues/8062) - Fixed pagination of Job Result logs table.
- [#8063](https://github.com/nautobot/nautobot/issues/8063) - Fixed a regression that removed many-to-many fields from change logs and webhook payloads.
- [#8064](https://github.com/nautobot/nautobot/issues/8064) - Fixed style of "Profile job execution" and "Ignore singleton lock" checkboxes in Job forms.
- [#8064](https://github.com/nautobot/nautobot/issues/8064) - Fixed style of checkboxes in user preferences table.
- [#8064](https://github.com/nautobot/nautobot/issues/8064) - Added exception handler for the case where `nautobot-server refresh_dynamic_group_member_caches` encounters an exception with a specific group(s).
- [#8064](https://github.com/nautobot/nautobot/issues/8064) - Fixed rendering of Job `description` in its detail view page.
- [#8065](https://github.com/nautobot/nautobot/issues/8065) - Fixed remaining tests skipped in v3.
- [#8072](https://github.com/nautobot/nautobot/issues/8072) - Fixed job detail view copy buttons.
- [#8086](https://github.com/nautobot/nautobot/issues/8086) - Fixed StatsPanel causing traceback when it includes a filter_extension.
- [#8087](https://github.com/nautobot/nautobot/issues/8087) - Fixed tab and tab panel spacings inside forms.
- [#8088](https://github.com/nautobot/nautobot/issues/8088) - Fixed "Nautobot Powered" link in footer and nav menu branding icon.
- [#8089](https://github.com/nautobot/nautobot/issues/8089) - Fixed ECharts text in dark mode.
- [#8089](https://github.com/nautobot/nautobot/issues/8089) - Fixed ECharts with dynamic data. ECharts data is not overwritten by resolved data.
- [#8089](https://github.com/nautobot/nautobot/issues/8089) - Fixed `combine_with` option.
- [#8090](https://github.com/nautobot/nautobot/issues/8090) - Fixed breadcrumbs rendering on generic views like Notes and Changelog.
- [#8090](https://github.com/nautobot/nautobot/issues/8090) - Fixed status labels on Rack Elevations and Cable Trace.
- [#8092](https://github.com/nautobot/nautobot/issues/8092) - Fixed title being hard-coded on list views instead of using view_titles.
- [#8096](https://github.com/nautobot/nautobot/issues/8096) - Fixed filtering on VPN forms for Dynamic Groups and VPNTunnelEndpoint.
- [#8099](https://github.com/nautobot/nautobot/issues/8099) - Fixed bulk-action buttons not rendering in the footer of object tables on non-default tabs.
- [#8100](https://github.com/nautobot/nautobot/issues/8100) - Fixed tables when boolean field should use BooleanColumn.
- [#8101](https://github.com/nautobot/nautobot/issues/8101) - Fixed Virtual Chassis edit member view.
- [#8102](https://github.com/nautobot/nautobot/issues/8102) - Fixed missing/broken "Data Compliance" tab on Secret views.
- [#8102](https://github.com/nautobot/nautobot/issues/8102) - Added missing Data Compliance support to GraphQLQuery and Note models.
- [#8102](https://github.com/nautobot/nautobot/issues/8102) - Fixed Data Compliance URL patterns from `data_compliance` to `data-compliance`.
- [#8105](https://github.com/nautobot/nautobot/issues/8105) - Fixed detailed view top buttons alignment.
- [#8106](https://github.com/nautobot/nautobot/issues/8106) - Fixed error in rendering Virtual Machine config context tab.
- [#8106](https://github.com/nautobot/nautobot/issues/8106) - Fixed incorrect application of config contexts scoped by device-type or device-redundancy-group to all virtual machines.
- [#8106](https://github.com/nautobot/nautobot/issues/8106) - Fixed incorrect permissions requirements to view various tabs on VPN Profile detail view.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Fixed various ObjectsTablePanel badge links that were invalid or broken.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Fixed the new path for the insourced DVE jobs.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Fixed the creation of Statuses for the insourced Load Balancer app.
- [#8111](https://github.com/nautobot/nautobot/issues/8111) - Allowed space as valid character in Select2 tags.
- [#8112](https://github.com/nautobot/nautobot/issues/8112) - Fixed missing Admin "Add" buttons on list views.
- [#8118](https://github.com/nautobot/nautobot/issues/8118) - Fixed condition in `GetObjectViewTestCase.test_body_content_table_list_url` in which tests failed if it did not have data.
- [#8122](https://github.com/nautobot/nautobot/issues/8122) - Fixed rendering of API version badges in Swagger UI docs.
- [#8124](https://github.com/nautobot/nautobot/issues/8124) - Fixed browseable API dark mode colors on syntax highlighting.
- [#8124](https://github.com/nautobot/nautobot/issues/8124) - Fixed missing icons on browseable API GET button.
- [#8124](https://github.com/nautobot/nautobot/issues/8124) - Fixed redundant header on browseable API pages.
- [#8124](https://github.com/nautobot/nautobot/issues/8124) - Fixed missing theme modal on pages that only import footer.html.
- [#8128](https://github.com/nautobot/nautobot/issues/8128) - Fixed a condition when trying to render a link on a button for an object that doesn't exist.
- [#8130](https://github.com/nautobot/nautobot/issues/8130) - Fixed model constraints on approval workflows not correctly applying to scheduled jobs.

### Documentation in v3.0.0rc1

- [#8081](https://github.com/nautobot/nautobot/issues/8081) - Updated v2 to v3 migration guide.
- [#8108](https://github.com/nautobot/nautobot/issues/8108) - Updated load balancer documentation.

### Housekeeping in v3.0.0rc1

- [#8078](https://github.com/nautobot/nautobot/issues/8078) - Fixed the rendering of the license badge in the App detail page.
- [#8083](https://github.com/nautobot/nautobot/issues/8083) - Bumped `highlight.js` version.
- [#8103](https://github.com/nautobot/nautobot/issues/8103) - Fixed bootstrap v3 to v5 script silently failing on invalid path arguments.
- [#8107](https://github.com/nautobot/nautobot/issues/8107) - Added a unit test to verify all ObjectsTablePanel badges have a valid link.
- [#8116](https://github.com/nautobot/nautobot/issues/8116) - Update navbar choices for icon and weight attributes to support the Nautobot Device Lifecycle App.

## v3.0.0a3 (2025-10-29)

### Added in v3.0.0a3

- [#4499](https://github.com/nautobot/nautobot/issues/4499) - Added new Constance setting `DEVICE_UNIQUENESS` to configure how Device instances are uniquely identified.
- [#4499](https://github.com/nautobot/nautobot/issues/4499) - Introduced a new Device Constraints management view accessible from the Data Validation Engine submenu. This endpoint allows staff users to configure device uniqueness and naming enforcement without accessing the generic Constance admin UI.
- [#6422](https://github.com/nautobot/nautobot/issues/6422) - Added `tenant` attribute to `Namespace`.
- [#7355](https://github.com/nautobot/nautobot/issues/7355) - Added VPN models.
- [#7722](https://github.com/nautobot/nautobot/issues/7722) - Added `DataComplianceModelMixin` and applied to base models.
- [#7722](https://github.com/nautobot/nautobot/issues/7722) - Added `DataComplianceModelMixin` to `nautobot.apps.models`.
- [#7927](https://github.com/nautobot/nautobot/issues/7927) - Added simplified dark theme to Swagger (`/api/docs/`) and Redoc (`/api/redoc/`) views, without using Nautobot color palette, utilizing mostly CSS `filter` property.
- [#7983](https://github.com/nautobot/nautobot/issues/7983) - Added tooltip with help text to column names in Approval Workflow Stage Definitions panel.
- [#7989](https://github.com/nautobot/nautobot/issues/7989) - Implemented a centralized system for managing icons and weights in the navigation bar.
- [#7989](https://github.com/nautobot/nautobot/issues/7989) - Added tests to ensure the navbar is is properly configured.
- [#7997](https://github.com/nautobot/nautobot/issues/7997) - Added logic to `nautobot-migrate-bootstrap-v3-to-v5` script to add missing `class="dropdown-item"` to menu items.
- [#8034](https://github.com/nautobot/nautobot/issues/8034) - Added tooltip for details page timestamp below tabs to indicate type of timestamp: created or last updated.

### Changed in v3.0.0a3

- [#4499](https://github.com/nautobot/nautobot/issues/4499) - Device uniqueness enforcement has been moved from database-level constraints to application-level validation via custom validators.
- [#7456](https://github.com/nautobot/nautobot/issues/7456) - Changed the default behavior of the REST API to exclude many-to-many fields (except for `tags`, `content_types`, and `object_types`) by default.
- [#7722](https://github.com/nautobot/nautobot/issues/7722) - Changed the Data Compliance tab to use a dynamic route pattern.
- [#7856](https://github.com/nautobot/nautobot/issues/7856) - Stored JobLogEntry counts on JobResult for more efficient display of this information in list views.
- [#7903](https://github.com/nautobot/nautobot/issues/7903) - Changed how App documentation is handled - it is now served via a dedicated endpoint whose access is restricted to authenticated users, replacing the previous static public serving.
- [#7926](https://github.com/nautobot/nautobot/issues/7926) - Updated ECharts color palette.
- [#7927](https://github.com/nautobot/nautobot/issues/7927) - Updated GraphiQL dark theme colors.
- [#7944](https://github.com/nautobot/nautobot/issues/7944) - Increased default Bootstrap 5 breakpoints to narrow down view a little bit faster because of sidenav width.
- [#7944](https://github.com/nautobot/nautobot/issues/7944) - Updated login page for better scaling on different screen sizes.
- [#7944](https://github.com/nautobot/nautobot/issues/7944) - Changed forms behavior to wrap input below label on smaller screens.
- [#7974](https://github.com/nautobot/nautobot/issues/7974) - Updated Nautobot icons.
- [#7978](https://github.com/nautobot/nautobot/issues/7978) - Removed `logger.debug()` call from `construct_cache_key()` function as being too noisy.
- [#7982](https://github.com/nautobot/nautobot/issues/7982) - Changed the IPAM and circuit navigation icons.
- [#7983](https://github.com/nautobot/nautobot/issues/7983) - Changed `priority` to `weight` (where highest weight wins) in ApprovalWorkflowDefinition.
- [#7983](https://github.com/nautobot/nautobot/issues/7983) - Changed `weight` to `sequence` (defines the order in which the stages take effect) in ApprovalWorkflowStageDefinition.
- [#7983](https://github.com/nautobot/nautobot/issues/7983) - Changed column name from "Min approvers" to "Minimum approvers".
- [#7989](https://github.com/nautobot/nautobot/issues/7989) - Updated the recommended method for managing the `icon` and `weight` attributes on `NavMenuTab`.
- [#8002](https://github.com/nautobot/nautobot/issues/8002) - Updated CSS filters and sidenav colors to the latest theme color palette.
- [#8005](https://github.com/nautobot/nautobot/issues/8005) - Improved rendering of User profile page.
- [#8008](https://github.com/nautobot/nautobot/issues/8008) - Changed the `DataCompliance` model to not be change-logged and to not support custom fields (as it's not a user-editable model) and updated migrations accordingly.
- [#8011](https://github.com/nautobot/nautobot/issues/8011) - Changed buttons to be more consistent with placement of positive actions before negative actions.
- [#8020](https://github.com/nautobot/nautobot/issues/8020) - Restored form-field label positions to once again be located below field inputs.
- [#8021](https://github.com/nautobot/nautobot/issues/8021) - Changed various "radio-button-like" toggle elements in the UI to be self-consistently styled.
- [#8028](https://github.com/nautobot/nautobot/issues/8028) - Default breadcrumbs are set to display list url on detail view only.
- [#8028](https://github.com/nautobot/nautobot/issues/8028) - Instance detail item is removed from breadcrumbs path.
- [#8029](https://github.com/nautobot/nautobot/issues/8029) - Globally replaced table native checkboxes with their Bootstrap `form-check-input` equivalents.
- [#8040](https://github.com/nautobot/nautobot/issues/8040) - Changed the label of the Collapse/Expand All buttons to specify they are for the groups rather than the panels.
- [#8041](https://github.com/nautobot/nautobot/issues/8041) - Merged in latest content from Nautobot v2.4.21.
- [#8044](https://github.com/nautobot/nautobot/issues/8044) - Moved "Custom Links" and "Job Buttons" to the left of the "default" action buttons on object detail view "main" tabs.
- [#8044](https://github.com/nautobot/nautobot/issues/8044) - Changed default rendering of Component Framework `Button` to only render on the "main" tab of object detail views.

### Removed in v3.0.0a3

- [#2850](https://github.com/nautobot/nautobot/issues/2850) - Removed many previously deprecated class aliases.
- [#4499](https://github.com/nautobot/nautobot/issues/4499) - Removed database-level uniqueness constraints on Device (`location`, `tenant`, `name`).
- [#4499](https://github.com/nautobot/nautobot/issues/4499) - Removed Constance setting `DEVICE_NAME_AS_NATURAL_KEY`.
- [#8044](https://github.com/nautobot/nautobot/issues/8044) - Removed support for `block panel_buttons` in object detail view templates.

### Fixed in v3.0.0a3

- [#7924](https://github.com/nautobot/nautobot/issues/7924) - Standardized boolean fields on tables to use the default theme.
- [#7936](https://github.com/nautobot/nautobot/issues/7936) - Fixed a class of circular-import issues by moving various FilterSet mixin classes from `nautobot.*.filters.mixins` to `nautobot.*.filter_mixins` modules.
- [#7936](https://github.com/nautobot/nautobot/issues/7936) - Fixed suppression of circular-import issues when registering homepage and nav-menu items.
- [#7945](https://github.com/nautobot/nautobot/issues/7945) - Fixed text color on badges with bg-secondary background.
- [#7951](https://github.com/nautobot/nautobot/issues/7951) - Fixed various UI related bugs and inconsistencies with bootstrap 5 migration.
- [#7975](https://github.com/nautobot/nautobot/issues/7975) - Fixed collapsing echarts.
- [#7976](https://github.com/nautobot/nautobot/issues/7976) - Fixed wrapping on error pages, login page, bulk edit form.
- [#7976](https://github.com/nautobot/nautobot/issues/7976) - Fixed col/offset not matching breakpoints - for example offset set for md but col set to lg.
- [#7984](https://github.com/nautobot/nautobot/issues/7984) - Fixed DeviceUniquenessValidator by using `get_settings_or_config` instead of `getattr`.
- [#7985](https://github.com/nautobot/nautobot/issues/7985) - Fixed chart and table cards to no longer require two clicks to collapse.
- [#7992](https://github.com/nautobot/nautobot/issues/7992) - Fixed bunch of CSS issues after UI v3 migration.
- [#7993](https://github.com/nautobot/nautobot/issues/7993) - Added background colors to remaining badges.
- [#7994](https://github.com/nautobot/nautobot/issues/7994) - Fixed colorless table rows.
- [#7995](https://github.com/nautobot/nautobot/issues/7995) - Corrected missing/incorrect marking of various links and buttons as `disabled` in appropriate contexts.
- [#7995](https://github.com/nautobot/nautobot/issues/7995) - Added `aria-disabled="true"` attribute to various disabled links for improved accessibility.
- [#7997](https://github.com/nautobot/nautobot/issues/7997) - Added missing `class="dropdown-item"` to various dropdown menu items.
- [#7997](https://github.com/nautobot/nautobot/issues/7997) - Fixed rendering of Custom Links and Job Buttons in Bootstrap 5.
- [#8001](https://github.com/nautobot/nautobot/issues/8001) - Fixed collapsed sidenav icons invisible after selecting text.
- [#8004](https://github.com/nautobot/nautobot/issues/8004) - Fixed display of related software images when editing a Device, Inventory Item, or Virtual Machine.
- [#8006](https://github.com/nautobot/nautobot/issues/8006) - Removed "Advanced" tab from Change Log detail view.
- [#8007](https://github.com/nautobot/nautobot/issues/8007) - Removed duplicated title/header text from various templates.
- [#8013](https://github.com/nautobot/nautobot/issues/8013) - Fixed `d-none` being overridden by responsive display utility classes (e.g. `d-md-flex`), causing elements meant to be hidden to remain visible.
- [#8013](https://github.com/nautobot/nautobot/issues/8013) - Added the `required` attribute to input fields(`schedule_name`, `schedule_start_time` and `recurrence_custom_time` when visible and applied the `nb-required` class to their corresponding labels.
- [#8016](https://github.com/nautobot/nautobot/issues/8016) - Fixed Job Edit form layout and migrated its script to vanilla JavaScript.
- [#8018](https://github.com/nautobot/nautobot/issues/8018) - Additional wrapping fixes to more templates.
- [#8019](https://github.com/nautobot/nautobot/issues/8019) - Fixed rack elevation display in dark mode.
- [#8020](https://github.com/nautobot/nautobot/issues/8020) - Fixed wrapping fields on narrow viewports.
- [#8021](https://github.com/nautobot/nautobot/issues/8021) - Fixed incorrect logic in `django_querystring` templatetag.
- [#8021](https://github.com/nautobot/nautobot/issues/8021) - Added missing `request` to the render context for rendering NautobotUIViewSet views.
- [#8021](https://github.com/nautobot/nautobot/issues/8021) - Added missing icons to various "Add components" menus for Device, Module, and ModuleType.
- [#8021](https://github.com/nautobot/nautobot/issues/8021) - Added missing chevron when rendering grouped Custom Links or grouped Job Buttons.
- [#8029](https://github.com/nautobot/nautobot/issues/8029) - Fixed job list and bulk edit styles.
- [#8031](https://github.com/nautobot/nautobot/issues/8031) - Fixed missing background in second and subsequent columns in navbar flyouts in Safari.
- [#8033](https://github.com/nautobot/nautobot/issues/8033) - Fixed form field behavior in Job edit form.
- [#8034](https://github.com/nautobot/nautobot/issues/8034) - Fixed tooltips staying open after clicking the footer links or opening the theme modal.
- [#8036](https://github.com/nautobot/nautobot/issues/8036) - Fixed some tests skipped in v3.
- [#8044](https://github.com/nautobot/nautobot/issues/8044) - Fixed vertical misalignment of rendered Job Button and Custom Link grouped buttons.
- [#8046](https://github.com/nautobot/nautobot/issues/8046) - Fixed marking menu item as active when adding to favorite.
- [#8046](https://github.com/nautobot/nautobot/issues/8046) - Fixed redirect after deleting saved view.
- [#8050](https://github.com/nautobot/nautobot/issues/8050) - Fixed some tests skipped in v3.

### Documentation in v3.0.0a3

- [#7934](https://github.com/nautobot/nautobot/issues/7934) - Prepare documentation for Version 3.0 release.
- [#8052](https://github.com/nautobot/nautobot/issues/8052) - Added information to release-note about filter field changes from #1889 and their impacts.

### Housekeeping in v3.0.0a3

- [#7936](https://github.com/nautobot/nautobot/issues/7936) - Added `example_app` and `example_app_with_view_override` tags to unit and integration tests that depend on these Apps.
- [#7936](https://github.com/nautobot/nautobot/issues/7936) - Added support for `--config-file` option to `invoke tests` and added alternative config `nautobot/core/tests/nautobot_config_without_example_apps.py` to run tests without enabling the example Apps.
- [#7936](https://github.com/nautobot/nautobot/issues/7936) - Enhanced Nautobot test runner to automatically exclude tests tagged with `example_app` and/or `example_app_with_view_override` when those Apps are not enabled.
- [#7948](https://github.com/nautobot/nautobot/issues/7948) - Disabled a flaky integration test that has been holding up merges and releases.
- [#7979](https://github.com/nautobot/nautobot/issues/7979) - Increased timeout in integration test `click_navbar_entry` to hopefully reduce spurious CI failures.
- [#7990](https://github.com/nautobot/nautobot/issues/7990) - Corrected static-docs test cases to correctly use `StaticLiveServerTestCase` base class.
- [#7990](https://github.com/nautobot/nautobot/issues/7990) - Added generated example-app docs to `.gitignore`.
- [#7991](https://github.com/nautobot/nautobot/issues/7991) - Added a title to the login view.
- [#8015](https://github.com/nautobot/nautobot/issues/8015) - Added `ssl-verify-server-cert=FALSE` to MySQL/MariaDB dev environment configuration to avoid an exception when running tests locally.
- [#8044](https://github.com/nautobot/nautobot/issues/8044) - Updated some "example app" content to improve its compatibility with the Bootstrap 5 UI.

## v3.0.0a2 (2025-10-07)

!!! note
    v3.0.0a1 was inadvertently not published to PyPI and Docker image registries. v3.0.0a2 does not contain any changes to Nautobot code compared to v3.0.0a1, but should fix the publishing failure.

### Housekeeping in v3.0.0a2

- [#7928](https://github.com/nautobot/nautobot/issues/7928) - Enhanced `release` GitHub Actions workflow to include prereleases and removed outdated `prerelease` workflow.

## v3.0.0a1 (2025-10-06)

### Added in v3.0.0a1

- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Added `nautobot.apps.filters.ModelMultipleChoiceFilter` filterset filter class, which is a subclass of `django_filters.ModelMultipleChoiceFilter` with a few enhancements. This is now the default filter class for foreign-key, many-to-many, and one-to-one fields when defining a FilterSet with `fields = '__all__'`.
- [#6814](https://github.com/nautobot/nautobot/issues/6814) - Implemented base Nautobot Bootstrap 5 theme.
- [#6866](https://github.com/nautobot/nautobot/issues/6866) - Migrated the Nautobot Data Validation Engine App into Nautobot Core.
- [#6876](https://github.com/nautobot/nautobot/issues/6876) - Added `DataValidationFormMixin` to indicate on the forms that fields are required due to `RequiredValidationRule` set.
- [#6946](https://github.com/nautobot/nautobot/issues/6946) - Implemented v3 UI global footer.
- [#6946](https://github.com/nautobot/nautobot/issues/6946) - Implemented v3 UI global header.
- [#6947](https://github.com/nautobot/nautobot/issues/6947) - Implemented base v3 UI sidenav.
- [#6999](https://github.com/nautobot/nautobot/issues/6999) - Added a data migration to update the `module_name` of jobs provided by Nautobot Data Validation Engine.
- [#7063](https://github.com/nautobot/nautobot/issues/7063) - Added initial Approval Workflow related models, UI, and API.
- [#7068](https://github.com/nautobot/nautobot/issues/7068) - Added a possibility to set/unset navbar items as favorite and display them in separate navbar flyout.
- [#7079](https://github.com/nautobot/nautobot/issues/7079) - Implemented v3 UI sidenav flyouts.
- [#7117](https://github.com/nautobot/nautobot/issues/7117) - Added support for running Jobs under branches when the Nautobot Version Control app is installed.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Added support for job approvals via approval workflows.
- [#7135](https://github.com/nautobot/nautobot/issues/7135) - Added state transition logic for Approval Workflow related models.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added callbacks to called when a workflow has been initiated, approved or rejected.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added `begin_approval_workflow` to `ApprovableModelMixin` to can use it in save method of models which inherit from `ApprovableModelMixin`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added ObjectManager with `find_for_model` method in `ApprovalWorkflowDefinition`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Added ApprovalWorkflow table to `ScheduledJobView`.
- [#7142](https://github.com/nautobot/nautobot/issues/7142) - Implemented tabs collapsing behavior.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Added data migration to copy existing Nautobot Data Validation Engine app data into the new core Data Validation tables.
- [#7177](https://github.com/nautobot/nautobot/issues/7177) - Implemented Approval Workflow related UI.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added Redis cache to `ValidationRule.objects.get_for_model()` to improve performance of repeated lookups.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added `ValidationRule.objects.get_enabled_for_model()` lookup method (with associated Redis cache for performance).
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added `GitRepository.objects.get_for_provided_contents()` lookup method (with associated Redis cache for performance).
- [#7186](https://github.com/nautobot/nautobot/issues/7186) - Added ARM64 build target for `nautobot-dev` images under `next` branch CI.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Added support for assigning a Device to more than one Cluster.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Added support for editing reverse many-to-many relations in bulk edit forms where applicable.
- [#7226](https://github.com/nautobot/nautobot/issues/7226) - Added `configurable` table property to toggle table config button visibility.
- [#7239](https://github.com/nautobot/nautobot/issues/7239) - Added `prettier` as JavaScript on demand source code formatter.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Added new API actions under `api/extras/approval-workflow-stages/`: `approve`, `deny`, `comment` and filterset parameter `pending_my_approvals` on the regular list endpoint.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Added `users_that_already_denied` property to `ApprovalWorkflowStage` model.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Added `associated_approval_workflows` to the `ScheduledJobSerializer` as a read-only list.
- [#7281](https://github.com/nautobot/nautobot/issues/7281) - Added missing flatpickr styles for both light and dark modes.
- [#7301](https://github.com/nautobot/nautobot/issues/7301) - Added support for tables in cards, including collapsible cards.
- [#7364](https://github.com/nautobot/nautobot/issues/7364) - Added pre-check migration (`extras.0125_approval_workflow_pre_check`) to validate data consistency before removing the `approval_required flag` from Job models. The migration aborts with a clear error message if any scheduled jobs still have `approval_required=True`. If any jobs (but not scheduled jobs) still have the flag set, a warning is printed advising to migrate them to the new approval workflow after the upgrade is completed.
- [#7411](https://github.com/nautobot/nautobot/issues/7411) - Implement v3 search UI.
- [#7415](https://github.com/nautobot/nautobot/issues/7415) - Added `hide_in_diff_view` flag to hide `ObjectChange`, `JobLogEntry` and `JobResult` diffs in version control app.
- [#7415](https://github.com/nautobot/nautobot/issues/7415) - Marked users app as not version controlled - `is_version_controlled=False`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Added the `runnable` property to the ScheduledJob model.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Added the `has_approval_workflow_definition` method to the ScheduledJob model.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Added support for custom approval templates via a new `get_approval_template()` method on models ScheduledJob. This allows objects to override the default approval UI when specific conditions are met (e.g. one-off jobs scheduled in the past).
- [#7538](https://github.com/nautobot/nautobot/issues/7538) - Improved Select2 styling and implemented Multi-badge component.
- [#7642](https://github.com/nautobot/nautobot/issues/7642) - Added Advanced filters tab indicator that it contains some filters visible only in there.
- [#7668](https://github.com/nautobot/nautobot/issues/7668) - Added Approval Workflow documentation.
- [#7668](https://github.com/nautobot/nautobot/issues/7668) - Added User Groups documentation.
- [#7697](https://github.com/nautobot/nautobot/issues/7697) - Created a small internal Nautobot icon library.
- [#7718](https://github.com/nautobot/nautobot/issues/7718) - Added more icons to `nautobot-icons` library: `refresh-cw`, `sliders-vert` and `sliders-vert-2`.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added EChartsBase class. Base definition for an ECharts chart (no rendering logic). This class transforms input data, applies theme colors, and generates a valid ECharts option config.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added `render_echart` as templatetags.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added EChartsPanel class, thank to that ECharts can be used in UI Component.
- [#7736](https://github.com/nautobot/nautobot/issues/7736) - Implemented sidenav branch picker for version control app.
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Added `nautobot.apps.utils.construct_cache_key()` function for consistent construction of Redis cache keys.
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Added awareness of Version Control active branch to various Redis caches.
- [#7837](https://github.com/nautobot/nautobot/issues/7837) - Persist sidenav state in cookies and browser local storage.
- [#7839](https://github.com/nautobot/nautobot/issues/7839) - Added `block job_form_wrapper` to provide additional customization on Custom Job Forms.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Added `Canceled` Approval Workflow State.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Added `nautobot.apps.choices.ApprovalWorkflowStateChoices`.
- [#7895](https://github.com/nautobot/nautobot/issues/7895) - Added `ObjectApprovalWorkflowView` to `nautobot.apps.views`.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Added `nautobot-migrate-bootstrap-v3-to-v5` helper script that can be run by Apps to streamline their migration to Bootstrap v5.x for Nautobot v3.x compatibility.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Added additional DjLint rules to flag various cases where HTML templates had not yet been migrated to Bootstrap v5.x compatibility.

### Changed in v3.0.0a1

- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Changed default handling in Nautobot filterset classes (`BaseFilterSet` and subclasses) for foreign-key and one-to-one fields such that they now default to generating a multi-value filter instead of a single-value filter. This may impact the definition of filter-based Dynamic Groups and of Object Permissions that were making use of single-value filters.
- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Changed `NaturalKeyOrPKMultipleChoiceFilter` and its subclasses to inherit from Nautobot's new `ModelMultipleChoiceFilter` class. The primary effect of this change is that the autogenerated label for such filters will be more descriptive.
- [#5745](https://github.com/nautobot/nautobot/issues/5745) - Upgraded the GraphiQL UI from version 1.x to version 2.4.7, including application of Nautobot UI colors to GraphiQL.
- [#5745](https://github.com/nautobot/nautobot/issues/5745) - Changed the return type for the `execute_query` and `execute_saved_query` GraphQL-related Python APIs as a consequence of updating the underlying GraphQL libraries.
- [#6815](https://github.com/nautobot/nautobot/issues/6815) - Updated UI component-based detail views to Bootstrap 5.
- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Increased `name` fields' length to 255 for RegularExpressionValidationRule, MinMaxValidationRule, RequiredValidationRule, and UniqueValidationRule.
- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Specified a Generic Relation from BaseModel class to DataCompliance class so that if an object is deleted, its associated data compliance objects will also be deleted.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `post` method in `JobRunView` to support job approvals via approval workflows.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `post` method in `JobViewSetBase` to support job approvals via approval workflows.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Added `approval_workflow` parameter to `on_workflow_approved`, `on_workflow_initiated` and `on_workflow_denied` methods.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `ScheduledJob.on_workflow_initiated` by adding set `approval_required = True` when workflow was initiated.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `ScheduledJob.on_workflow_approved` by adding set `approved_at` and publishing an approval event when workflow was approved.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Changed `ScheduledJob.create_schedule` method to accept an additional `validated_save` argument, allowing the option to skip saving the scheduled job object to the database.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Renamed the new `nautobot.nautobot_data_validation_engine` app to `nautobot.data_validation`.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Regenerated the database schema migrations for `nautobot.data_validation` models.
- [#7183](https://github.com/nautobot/nautobot/issues/7183) - Migrate generic object list view to Bootstrap 5.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Removed bespoke "Add Devices to Cluster" and "Remove Devices from Cluster" forms/views and added this functionality into the base Cluster edit and bulk-edit forms/views.
- [#7209](https://github.com/nautobot/nautobot/issues/7209) - Move filter form modal to flyout.
- [#7226](https://github.com/nautobot/nautobot/issues/7226) - Moved table config button from top buttons row to table header and table config form from modal to drawer.
- [#7227](https://github.com/nautobot/nautobot/issues/7227) - Migrated Saved Views dropdown menu to drawer.
- [#7239](https://github.com/nautobot/nautobot/issues/7239) - Replaced `yarn` with `npm`.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - The `approved_at` field from `extras.ScheduleJob` model has been changed to `decision_date`.
- [#7276](https://github.com/nautobot/nautobot/issues/7276) - Moved table action buttons to dropdown menus.
- [#7276](https://github.com/nautobot/nautobot/issues/7276) - Updated all table action button templates to render as dropdown items rather than flat structure buttons.
- [#7316](https://github.com/nautobot/nautobot/issues/7316) - Make Approval Workflow's active stage clearer in the UI.
- [#7333](https://github.com/nautobot/nautobot/issues/7333) - Migrated homepage to Bootstrap 5.
- [#7333](https://github.com/nautobot/nautobot/issues/7333) - Abstracted out draggable API to a generic and reusable form.
- [#7465](https://github.com/nautobot/nautobot/issues/7465) - Move all form buttons to sticky footers.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Simplified `runnable` property logic in the Job model: removed check for `has_sensitive_variable`s and `approval_required`. Now only depends on `enabled` and `installed` flags.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Changed the `post` method in `JobRunView` and the `run` action in `JobViewSetBase` to check for an approval workflow on the scheduled job instead of using `approval_required`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Changed `extras/job_approval_confirmation.html` to override `extras/approval_workflow/approve.html` for ScheduledJob instances that meet specific conditions, displaying a warning when the job is past its scheduled start time.
- [#7486](https://github.com/nautobot/nautobot/issues/7486) - Changed Prefix table behavior to not show "utilization" by default, as it has significant performance impact when displayed.
- [#7521](https://github.com/nautobot/nautobot/issues/7521) - Updated tabs injected via `{% block extra_tab_content %}` and tabs generated from plugin to match Bootstrap 5 design.
- [#7521](https://github.com/nautobot/nautobot/issues/7521) - Updated `switch_tab` function in integration tests to work with tabs hiding mechanism.
- [#7525](https://github.com/nautobot/nautobot/issues/7525) - Genericize and standardize the way "Collapse/Expand All" buttons work in the app using data-nb-toggle="collapse-all" data attribute.
- [#7551](https://github.com/nautobot/nautobot/issues/7551) - Implement v3 UI design in table filters drawer Basic tab. Refactor some of the existing Select2 forms code.
- [#7587](https://github.com/nautobot/nautobot/issues/7587) - Implemented v3 table advanced filter form,
- [#7602](https://github.com/nautobot/nautobot/issues/7602) - Prefixed following classes with `nb-*`: `table-headings`, `description`, `style-line` and `sidenav-*`.
- [#7619](https://github.com/nautobot/nautobot/issues/7619) - Implemented saved view form new look and feel.
- [#7635](https://github.com/nautobot/nautobot/issues/7635) - Fix sidenav and drawer height to viewport instead of an entire page.
- [#7673](https://github.com/nautobot/nautobot/issues/7673) - Updated table config drawer.
- [#7679](https://github.com/nautobot/nautobot/issues/7679) - Migrated unauthenticated pages to Bootstrap 5.
- [#7738](https://github.com/nautobot/nautobot/issues/7738) - Use Nautobot standard layout (header, sidenav, footer) in special views (Admin, GraphiQL, DRF API docs, Swagger and Redoc).
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Changed a number of Redis cache keys to be more standardized.
- [#7800](https://github.com/nautobot/nautobot/issues/7800) - Separate `page_title` block from `breadcrumbs` in base Django templates.
- [#7823](https://github.com/nautobot/nautobot/issues/7823) - Updated titles and breadcrumbs for new views with added header like API Docs, GraphiQL, template renderer and user settings.
- [#7832](https://github.com/nautobot/nautobot/issues/7832) - Improved active nav menu items determination logic and moved it from template to context processor.
- [#7832](https://github.com/nautobot/nautobot/issues/7832) - Changed Scheduled Jobs URL path from `/extras/jobs/scheduled-jobs/` to `/extras/scheduled-jobs/`.
- [#7832](https://github.com/nautobot/nautobot/issues/7832) - Restricted nav menu to highlight only one active item at a time.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - The `has_approval_workflow_definition` method has been moved to `ApprovableModelMixin` from `ScheduledJob` so that it can be used by any model that will be handled by the approval process.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Replaced `APPROVAL_WORKFLOW_MODELS` constant with `FeatureQuery` and `populate_model_features_registry`.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Changed rendering Approval Workflow tab in ScheduledJob; now renders only when the scheduled job has any associated approval workflows.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Flagged Approval Workflows and their various sub-models as non-versionable.
- [#7872](https://github.com/nautobot/nautobot/issues/7872) - Improved Dropdown and Select2 highlighted items visibility.
- [#7892](https://github.com/nautobot/nautobot/issues/7892) - Removed unnecessary and error-prone cache logic from the `PathEndpoint.connected_endpoint` property.
- [#7898](https://github.com/nautobot/nautobot/issues/7898) - Updated Nautobot theme, most notably dark theme color palette and navbar spacings and colors.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Ran `nautobot-migrate-bootstrap-v3-to-v5` against all core HTML templates to auto-migrate many remaining Bootstrap 3 CSS classes and HTML structure to Bootstrap 5 equivalents, as well as identifying various CSS/HTML that needed manual updates.
- [#7902](https://github.com/nautobot/nautobot/issues/7902) - Ran updated DjLint rules against all core HTML templates and manually addressed any identified issues not already covered by the `nautobot-migrate-bootstrap-v3-to-v5` script.
- [#7904](https://github.com/nautobot/nautobot/issues/7904) - Refined page header and tree hierarchy UI.

### Removed in v3.0.0a1

- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Removed unused job `DeleteOrphanedDataComplianceData`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Removed `ApprovableModelMixin` inheritance from Job.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Removed job from `APPROVAL_WORKFLOW_MODELS`.
- [#7136](https://github.com/nautobot/nautobot/issues/7136) - Removed ApprovalWorkflow table from `JobView`.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Removed `wrap_model_clean_methods` and `custom_validator_clean` methods from the `nautobot.apps` namespace as they should only ever be called by Nautobot itself as part of system startup.
- [#7203](https://github.com/nautobot/nautobot/issues/7203) - Removed `cluster` field from Device REST API serializer. `clusters` is available as a read-only field, and assignment of Devices to Clusters via the REST API is now possible via `/api/dcim/device-cluster-assignments/`.
- [#7226](https://github.com/nautobot/nautobot/issues/7226) - Removed `table_config_button_small` Django template tag.
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Removed actions from `api/extras/scheduled-job/`: approve, deny
- [#7256](https://github.com/nautobot/nautobot/issues/7256) - Removed `approved_by_user` field from `extras.ScheduleJob` model. Now this information is stored in `ApprovalWorkflowStageResponse` model.
- [#7411](https://github.com/nautobot/nautobot/issues/7411) - Remove v2 search.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed `approval_required` and `approval_required_override` flags from the Job model and base implementation class.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed the `validate` method from `JobSerializer` that checked `approval_required` against `has_sensitive_variables`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed logic from the `clean` method in the Job model that validated `approval_required` against `has_sensitive_variables`.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed HTML code related to the `approval_required` field.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Removed `ScheduledJobApprovalQueueListView` and `JobApprovalRequestView` with all relevant files, methods and tests.
- [#7525](https://github.com/nautobot/nautobot/issues/7525) - Removed `accordion-toggle` and `accordion-toggle-all` legacy CSS classes.
- [#7538](https://github.com/nautobot/nautobot/issues/7538) - Removed legacy CSS classes: `filter-container`, `display-inline`, `filter-selection`, `filter-selection-choice`, `filter-selection-choice-remove`, `filter-selection-rendered` and `remove-filter-param`.
- [#7842](https://github.com/nautobot/nautobot/issues/7842) - Removed job specific fields from `ObjectApprovalWorkflowView`.

### Fixed in v3.0.0a1

- [#7117](https://github.com/nautobot/nautobot/issues/7117) - Fixed an exception when rendering Nautobot Version Control app diffs that include GitRepository or JobResult records.
- [#7131](https://github.com/nautobot/nautobot/issues/7131) - Fixed Graphene v3 handling of `description` filters.
- [#7131](https://github.com/nautobot/nautobot/issues/7131) - Restored GraphQL `_type` filters (as aliases of `type` filters) to preserve backwards compatibility with Nautobot v2.x.
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Resolved an issue where approval workflows were not correctly fetched due to querying the wrong relationship (`approval_workflow_instances` instead of `associated_approval_workflows`).
- [#7134](https://github.com/nautobot/nautobot/issues/7134) - Fixed approvalworkflowdefinition_update templates.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Added handling for the ContactAssociation, MetadataType, ObjectMetadata, and Role models to `nautobot.core.utils.migration.migrate_content_type_references_to_new_model`.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Renamed the data-validation model database tables to fit within identifier length limits in Dolt and MySQL.
- [#7171](https://github.com/nautobot/nautobot/issues/7171) - Fixed missing "Data Compliance" tab on relevant models.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Fixed an issue in which data-validation-engine checks would incorrectly run repeatedly when calling model `clean()`, causing significant performance degradation.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Changed data-validation-engine `BaseValidator.clean()` implementation to use cacheable lookup APIs, improving performance of repeated model `clean()` calls.
- [#7259](https://github.com/nautobot/nautobot/issues/7259) - Fixed not working JavaScript build by converting webpack config from CJS to ESM.
- [#7261](https://github.com/nautobot/nautobot/issues/7261) - Fixed JS imports causing Webpack build failures.
- [#7434](https://github.com/nautobot/nautobot/issues/7434) - Fixed Prefix tabs to properly render without HTTP 500.
- [#7434](https://github.com/nautobot/nautobot/issues/7434) - Fixed module bays details to properly render title and breadcrumbs.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Fixed dryrun functionality in post method of JobRunView.
- [#7480](https://github.com/nautobot/nautobot/issues/7480) - Fixed draggable homepage panels on Firefox.
- [#7524](https://github.com/nautobot/nautobot/issues/7524) - Fixed broken theme preview page.
- [#7525](https://github.com/nautobot/nautobot/issues/7525) - Fixed job list view not rendering jobs.
- [#7563](https://github.com/nautobot/nautobot/issues/7563) - Fixed `data_validation.0002` migration to handle a schema difference between the latest Data Validation Engine App and the version in Nautobot core.
- [#7652](https://github.com/nautobot/nautobot/issues/7652) - Fixed missing "Created/Updated" and action buttons on object detail views.
- [#7653](https://github.com/nautobot/nautobot/issues/7653) - Fixed main tab sometimes incorrectly displayed as active in detail view.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in CSV rendering of VarbinaryIPField values on Dolt.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in `settings.py` when using `NAUTOBOT_DB_ENGINE=django_prometheus.db.backends.mysql`.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in Git repository refreshing where a data failure was not correctly detected under Dolt.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed a bug in `get_celery_queues()` caching.
- [#7659](https://github.com/nautobot/nautobot/issues/7659) - Fixed rendering of progress bars under 30%.
- [#7660](https://github.com/nautobot/nautobot/issues/7660) - Fixed a rendering error in `/ipam/prefixes/<uuid>/prefixes/` child-prefixes view.
- [#7707](https://github.com/nautobot/nautobot/issues/7707) - Fixed bug with Job Execution card always fully visible in Run Job form.
- [#7713](https://github.com/nautobot/nautobot/issues/7713) - Fixed broken banner styles.
- [#7719](https://github.com/nautobot/nautobot/issues/7719) - Fixed theme preview example layouts and components.
- [#7721](https://github.com/nautobot/nautobot/issues/7721) - Fixed an issue where the current tab was not highlighted as active.
- [#7740](https://github.com/nautobot/nautobot/issues/7740) - Fixed bug with invalid reference to Nautobot version control branch list URL.
- [#7839](https://github.com/nautobot/nautobot/issues/7839) - Fixed Import Objects form by using `job_form_wrapper` and tabs on the card-header.
- [#7843](https://github.com/nautobot/nautobot/issues/7843) - Fixed white background flash during page load in system dark color mode.
- [#7881](https://github.com/nautobot/nautobot/issues/7881) - Fixed image rendering in echarts and approval workflow md files.
- [#7894](https://github.com/nautobot/nautobot/issues/7894) - Fixed HTML rendering of numbered lists in the approval workflow documentation.
- [#7896](https://github.com/nautobot/nautobot/issues/7896) - Fixed missing action button left border in case when there is only one action button.
- [#7897](https://github.com/nautobot/nautobot/issues/7897) - Fixed non clickable interactive elements in collapsible card headers.
- [#7912](https://github.com/nautobot/nautobot/issues/7912) - Hid sidenav tabs and groups with no items.

### Dependencies in v3.0.0a1

- [#4769](https://github.com/nautobot/nautobot/issues/4769) - Updated GraphiQL UI to version 2.4.7 (the version supported by `graphene-django` 3.2.0).
- [#5745](https://github.com/nautobot/nautobot/issues/5745) - Updated dependencies `graphene-django` to `~3.2.3` and `graphene-django-optimizer` to `~0.10.0`.
- [#7186](https://github.com/nautobot/nautobot/issues/7186) - Updated `netutils` minimum version to 1.12.0 as older versions do not support Python 3.13.
- [#7200](https://github.com/nautobot/nautobot/issues/7200) - Dropped support for Python 3.9. Python 3.10 is now the minimum version required by Nautobot.
- [#7200](https://github.com/nautobot/nautobot/issues/7200) - Added support for Python 3.13. Python 3.13 is now the maximum version required by Nautobot.
- [#7208](https://github.com/nautobot/nautobot/issues/7208) - Updated `select2` dependency to v4.0.13.
- [#7208](https://github.com/nautobot/nautobot/issues/7208) - Added `select2-bootstrap-5-theme` dependency to make `select2` work with `Bootstrap5`
- [#7431](https://github.com/nautobot/nautobot/issues/7431) - Updated dependency `celery` to `~5.5.3`.
- [#7431](https://github.com/nautobot/nautobot/issues/7431) - Removed direct dependency on `kombu` as the newer version of `celery` includes an appropriate dependency.
- [#7675](https://github.com/nautobot/nautobot/issues/7675) - Replaced `mime-support` with `media-types` in Dockerfile dependencies. The `mime-support` package is no longer available in newer Debian-based `python:slim` images (starting with Debian 13 "Trixie"). For the same reason, the `xmlsec` dependency was upgraded to version `1.3.16` to ensure compatibility with the updated build environment.
- [#7680](https://github.com/nautobot/nautobot/issues/7680) - Added dependency on `htmx` npm package.
- [#7680](https://github.com/nautobot/nautobot/issues/7680) - Removed `django-htmx` from the Python dependencies.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added dependency on `echarts` npm package.

### Documentation in v3.0.0a1

- [#7306](https://github.com/nautobot/nautobot/issues/7306) - Create v2.x to v3.0 UI migration guide.
- [#7716](https://github.com/nautobot/nautobot/issues/7716) - Added docs to communicate about configurable columns performance impact.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Added documentation about new feature ECharts.
- [#7730](https://github.com/nautobot/nautobot/issues/7730) - Added Involving Scheduled Job Approval example to Approval Workflow documentation.
- [#7741](https://github.com/nautobot/nautobot/issues/7741) - Corrected formatting of autogenerated docs for various items in `nautobot.apps`.
- [#7811](https://github.com/nautobot/nautobot/issues/7811) - Document UI best practices.
- [#7891](https://github.com/nautobot/nautobot/issues/7891) - Fixed a dead link to the Django documentation.
- [#7899](https://github.com/nautobot/nautobot/issues/7899) - Documented additional HTML changes needed in forms when migrating to Nautobot v3 and Bootstrap 5.

### Housekeeping in v3.0.0a1

- [#1889](https://github.com/nautobot/nautobot/issues/1889) - Removed explicit `label` declarations from many filterset filters where the enhanced automatic labeling should suffice.
- [#6874](https://github.com/nautobot/nautobot/issues/6874) - Refactored Nautobot Data Validation Engine code.
- [#7180](https://github.com/nautobot/nautobot/issues/7180) - Added `--print-sql` option to `invoke nbshell`.
- [#7449](https://github.com/nautobot/nautobot/issues/7449) - Fixed CI failures after the merge of #7433.
- [#7474](https://github.com/nautobot/nautobot/issues/7474) - Cleaned up legacy logic and tests related to deprecated approval flags.
- [#7497](https://github.com/nautobot/nautobot/issues/7497) - Migrate base.css and dark.css files with existing Nautobot styles into new packaging.
- [#7505](https://github.com/nautobot/nautobot/issues/7505) - Added "npm" manager to Renovate configuration.
- [#7523](https://github.com/nautobot/nautobot/issues/7523) - Added `docker-compose.dolt.yml` and supporting files to enable local development and testing against a Dolt database.
- [#7630](https://github.com/nautobot/nautobot/issues/7630) - Added `ui-build-check` step to pull request and integration CI workflows to check UI src and dist files validity and integrity.
- [#7652](https://github.com/nautobot/nautobot/issues/7652) - Added `test_has_timestamps_and_buttons` generic test case to `GetObjectViewTestCase` base test class.
- [#7657](https://github.com/nautobot/nautobot/issues/7657) - Lint JS code.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Refactored Dolt development `Dockerfile-dolt` and `docker-compose.dolt.yml`.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Updated Dolt version in development environment to 1.58.2.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Removed the `doltdb_stuck` tag from test cases previously failing under Dolt.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Updated test and subtest definitions in `nautobot/dcim/tests/test_filters.py` for clarity and efficiency.
- [#7658](https://github.com/nautobot/nautobot/issues/7658) - Fixed an intermittent test failure in `nautobot.extras.tests.test_filters.ObjectMetadataTestCase`.
- [#7659](https://github.com/nautobot/nautobot/issues/7659) - Added UI rebuild and tooling to development Docker Compose for developer convenience.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Updated example app to use related manager names.
- [#7726](https://github.com/nautobot/nautobot/issues/7726) - Updated `UI_COLORS` names to match values in colors.scss.
- [#7739](https://github.com/nautobot/nautobot/issues/7739) - Add `0.3125rem` (`5px`) spacer.
- [#7773](https://github.com/nautobot/nautobot/issues/7773) - Updated development dependency `coverage` to `~7.10.6`.
- [#7785](https://github.com/nautobot/nautobot/issues/7785) - Added `invoke` commands and renamed existing `npm` commands for frontend development.
- [#7799](https://github.com/nautobot/nautobot/issues/7799) - Fix broken `ui-build-check` CI job.
- [#7884](https://github.com/nautobot/nautobot/issues/7884) - Added legacy button templates usage check to action buttons presence unit test on detail view page.
- [#7885](https://github.com/nautobot/nautobot/issues/7885) - Removed documentation dependency `mkdocs-include-markdown-plugin` as older versions have a security vulnerability and Nautobot core hasn't actually needed this dependency since v2.0.
- [#7911](https://github.com/nautobot/nautobot/issues/7911) - Moved UI source files out of `project-static` to its own dedicated `ui` directory.
