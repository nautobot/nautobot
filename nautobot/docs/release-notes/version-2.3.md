<!-- markdownlint-disable MD024 -->

# Nautobot v2.3

This document describes all new features and changes in Nautobot 2.3.

## Release Overview

### Added

#### Cloud Models ([#5716](https://github.com/nautobot/nautobot/issues/5716), [#5719](https://github.com/nautobot/nautobot/issues/5719), [#5721](https://github.com/nautobot/nautobot/issues/5721), [#5872](https://github.com/nautobot/nautobot/issues/5872))

Added the new models `CloudAccount`, `CloudResourceType`, `CloudNetwork`, and `CloudService` to support recording of cloud provider accounts (AWS, Azure, GCP, DigitalOcean, etc.), cloud resource types (AWS EC2, Azure Virtual Machine Service, Google App Engine, etc.), cloud services (specific instances of services described by cloud resource types) and cloud network objects (such as VPCs) in Nautobot.

#### Device Modules ([#2101](https://github.com/nautobot/nautobot/issues/2101))

Added new models for `ModuleBay`, `Module`, `ModuleType`, and `ModuleBayTemplate` to support modeling line cards and other modular components of a device. These models allow you to define a hierarchy of module bays and modules within a device, and to assign components (such as interfaces, power ports, etc.) to specific modules.

#### Dynamic Group Enhancements ([#5472](https://github.com/nautobot/nautobot/issues/5472), [#5786](https://github.com/nautobot/nautobot/issues/5786))

Dynamic Groups now have a `group_type` field, which specifies whether this group is defined by an object filter, defined by aggregating other groups via set operations, or defined via static assignment of objects as group members (this third type is new in Nautobot 2.3). Additionally, you can now assign a tenant and/or tags to each Dynamic Group, and many more models now can be included in Dynamic Groups.

A new model, `StaticGroupAssociation`, and associated REST API, have been added in support of the new "static" group type. See also "[Dynamic Group Cache Changes](#dynamic-group-cache-changes-5473)" below.

For more details, refer to the [Dynamic Group](../user-guide/platform-functionality/dynamicgroup.md) documentation.

#### Interface and VMInterface Roles ([#4406](https://github.com/nautobot/nautobot/issues/4406))

Added an optional `role` field to Interface and VMInterface models to track common interface configurations. Now the users can create [Role](../user-guide/platform-functionality/role.md) instances that can be assigned to [interfaces](../user-guide/core-data-model/dcim/interface.md) and [vminterfaces](../user-guide/core-data-model/virtualization/vminterface.md).

#### Object Metadata Models ([#5663](https://github.com/nautobot/nautobot/issues/5663))

Added [a set of functionality](../user-guide/platform-functionality/metadata.md) for defining and managing object metadata, that is to say, data _about_ the network data managed in Nautobot, such as data provenance, data ownership, and data classification. For more details, refer to the linked documentation.

#### Python 3.12 Support ([#5429](https://github.com/nautobot/nautobot/issues/5429))

Nautobot now supports Python 3.12, and Python 3.12 is now the default Python version included in the `nautobot` Docker images.

#### Saved Views ([#1758](https://github.com/nautobot/nautobot/issues/1758))

Added the ability for users to save multiple configurations of list views (table columns, filtering, pagination and sorting) for ease of later use and reuse. Refer to the [Saved View](../user-guide/platform-functionality/savedview.md) documentation for more details and on how to use saved views.

#### Worker Status Page ([#5873](https://github.com/nautobot/nautobot/issues/5873))

User accounts with the `is_staff` flag set can access a new worker status page at `/worker-status/` to view the status of the Celery worker(s) and the configured queues. The link to this page appears in the "User" dropdown at the bottom of the navigation menu, under the link to the "Profile" page. Use this page with caution as it runs a live query against the Celery worker(s) and may impact performance of your web service.

### Changed

#### Changed TreeManager Default Behavior ([#5786](https://github.com/nautobot/nautobot/issues/5786))

The `TreeManager` class (used for tree-models such as Location, RackGroup, and TenantGroup) default behavior has changed from `with_tree_fields` to `without_tree_fields`. This should improve performance in many cases but may impact Apps or Jobs that were relying on the old default; such code should be updated to explicitly call `.with_tree_fields()` where appropriate.

#### Dynamic Group Cache Changes ([#5473](https://github.com/nautobot/nautobot/issues/5473))

To improve performance of the Dynamic Groups feature, a number of changes have been made:

- Dynamic Groups now always use `StaticGroupAssociation` records as a database cache of their member objects, rather than optionally caching their members in Redis for a limited time period. For Dynamic Groups of types other than the new "static" group type, these `StaticGroupAssociation` records are hidden by default from the UI and REST API.
- The `DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT` setting variable is deprecated, as it no longer influences Dynamic Group cache behavior.
- The APIs `DynamicGroup.members`, `DynamicGroup.count`, `DynamicGroup.has_member()`, and `object.dynamic_groups` now always use the database cache rather than being recalculated on the fly.
- The APIs `DynamicGroup.members_cached`, `DynamicGroup.members_cache_key`, `object.dynamic_groups_cached`, `object.dynamic_groups_list`, and `object.dynamic_groups_list_cached` are now deprecated.
- Editing a Dynamic Group definition refreshes its cached members and those of any "parent" groups that use it.
- Viewing a Dynamic Group detail view in the UI refreshes its cached members (only).
- A new System Job, `Refresh Dynamic Group Caches`, can be run or scheduled as appropriate to refresh Dynamic Group member caches on demand.
- The existing API `DynamicGroup.update_cached_members()` can be called by Apps or Jobs needing to ensure that the cache is up-to-date for any given Dynamic Group.

#### Log Cleanup as System Job ([#3749](https://github.com/nautobot/nautobot/issues/3749))

Cleanup of the change log (deletion of `ObjectChange` records older than a given cutoff) is now handled by the new `LogsCleanup` system Job, rather than occurring at random as a side effect of new change log records being created. Admins desiring automatic cleanup are encouraged to schedule this job to run at an appropriate interval suitable to your deployment's needs.

!!! info
    Setting [`CHANGELOG_RETENTION`](../user-guide/administration/configuration/optional-settings.md#changelog_retention) in your Nautobot configuration by itself no longer directly results in periodic cleanup of `ObjectChange` records. You must run (or schedule to periodically run) the `LogsCleanup` Job for this to occur.

As an additional enhancement, the `LogsCleanup` Job can also be used to cleanup `JobResult` records if desired as well.

#### UI Button Consolidation ([#5869](https://github.com/nautobot/nautobot/issues/5869), [#5870](https://github.com/nautobot/nautobot/issues/5870), [#5871](https://github.com/nautobot/nautobot/issues/5871))

Various button groups in the "object list" and "object detail" views have been consolidated following a common UI pattern of a single button for the most common action plus a popup menu for less common actions.

### Dependencies

#### Updated to Django 4.2 ([#3581](https://github.com/nautobot/nautobot/issues/3581))

As Django 3.2 has reached end-of-life, Nautobot 2.3 requires Django 4.2, the next long-term-support (LTS) version of Django. There are a number of changes in Django itself as a result of this upgrade; Nautobot App maintainers are urged to review the Django release-notes ([4.0](https://docs.djangoproject.com/en/4.2/releases/4.0/), [4.1](https://docs.djangoproject.com/en/4.2/releases/4.1/), [4.2](https://docs.djangoproject.com/en/4.2/releases/4.2/)), especially the relevant "Backwards incompatible changes" sections, to proactively identify any impact to their Apps.

<!-- towncrier release notes start -->
## v2.3.0-beta.1 (2024-07-25)

### Security

- [#5889](https://github.com/nautobot/nautobot/issues/5889) - Updated `Django` to `~4.2.14` due to `CVE-2024-38875`, `CVE-2024-39329`, `CVE-2024-39330`, and `CVE-2024-39614`.

### Added

- [#1758](https://github.com/nautobot/nautobot/issues/1758) - Implemented SavedView model.
- [#2101](https://github.com/nautobot/nautobot/issues/2101) - Added ModuleBay, Module, ModuleType and ModuleBayTemplate models to support modeling line cards and other modular components of a device.
- [#3749](https://github.com/nautobot/nautobot/issues/3749) - Added "Logs Cleanup" system Job, which can be run to delete ObjectChange and/or JobResult records older than a given cutoff.
- [#4406](https://github.com/nautobot/nautobot/issues/4406) - Added `role` field to `Interface` and `VMInterface` models.
- [#5212](https://github.com/nautobot/nautobot/issues/5212) - Added `contacts` and `teams` filters to appropriate FilterSets and filter forms.
- [#5348](https://github.com/nautobot/nautobot/issues/5348) - Enhanced UI to include arrow indicators for sorted table columns.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Added Python 3.12 support.
- [#5442](https://github.com/nautobot/nautobot/issues/5442) - Added `JobResultFactory`, `JobLogEntryFactory`, and `ObjectChangeFactory` classes and added creation of fake `JobResult`, `JobLogEntry`, and `ObjectChange` records to the `nautobot-server generate_test_data` command.
- [#5471](https://github.com/nautobot/nautobot/issues/5471) - Added the ability to set Global and User default saved view.
- [#5471](https://github.com/nautobot/nautobot/issues/5471) - Added the ability to set public and private saved view.
- [#5472](https://github.com/nautobot/nautobot/issues/5472) - Added `StaticGroup` and `StaticGroupAssociation` data models, used for statically defining groups of Nautobot objects.
- [#5472](https://github.com/nautobot/nautobot/issues/5472) - Added `feature` filter to `/api/extras/content-types/`.
- [#5472](https://github.com/nautobot/nautobot/issues/5472) - Added `static_groups` filter to all applicable models via the `BaseFilterSet` class.
- [#5472](https://github.com/nautobot/nautobot/issues/5472) - Added `static_groups` field to applicable model create/edit forms via the `StaticGroupModelFormMixin` class (included in `NautobotModelForm` class automatically).
- [#5472](https://github.com/nautobot/nautobot/issues/5472) - Added `Static Groups` column to applicable model tables.
- [#5472](https://github.com/nautobot/nautobot/issues/5472) - Added `static_groups` and `associated_contacts` to applicable GraphQL types.
- [#5472](https://github.com/nautobot/nautobot/issues/5472) - Enhanced `BaseTable` class to automatically apply appropriate `count_related` annotations for any `LinkedCountColumn`.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Added support for objects to "opt out" of change logging by returning `None` from their `to_objectchange()` method.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Added `description` strings to all system Jobs.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Added `Refresh Dynamic Group Caches` system Job.
- [#5631](https://github.com/nautobot/nautobot/issues/5631) - Added `ContactMixin` and `StaticGroupMixin` abstract model mixin classes. Models that inherit from `OrganizationalModel` or `PrimaryModel` will automatically include these mixins.
- [#5663](https://github.com/nautobot/nautobot/issues/5663) - Added `MetadataType` and `MetadataChoice` data models, REST API, and UI.
- [#5664](https://github.com/nautobot/nautobot/issues/5664) - Added `ObjectMetadata` data models, UI and REST API.
- [#5687](https://github.com/nautobot/nautobot/issues/5687) - Added `setup_structlog_logging()` to allow using structlog from `nautobot_config.py` file.
- [#5716](https://github.com/nautobot/nautobot/issues/5716) - Added CloudNetwork model, UI, GraphQL and REST API.
- [#5716](https://github.com/nautobot/nautobot/issues/5716) - Added CloudNetwork to CircuitTermination model, UI, and REST API.
- [#5716](https://github.com/nautobot/nautobot/issues/5716) - Added CloudNetwork to Prefix View.
- [#5719](https://github.com/nautobot/nautobot/issues/5719) - Added CloudAccount Model, UI, GraphQL and REST API.
- [#5721](https://github.com/nautobot/nautobot/issues/5721) - Added ~`CloudType`~ `CloudResourceType` Model, UI, GraphQL and REST API.
- [#5730](https://github.com/nautobot/nautobot/issues/5730) - Added a feature that replaces `{module}`, `{module.parent}`, `{module.parent.parent}`, etc. with the selected module's `parent_module_bay` `position` when creating a component in a module.
- [#5732](https://github.com/nautobot/nautobot/issues/5732) - Added indices on `StaticGroupAssociation` table for common lookup patterns.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Added `DynamicGroup.group_type` field with options `dynamic-filter`, `dynamic-set`, and `static`. Existing DynamicGroups will automatically be set to either `dynamic-filter` or `dynamic-set` as befits their definitions.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Added `DynamicGroup.tenant` and `DynamicGroup.tags` fields.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Added Dynamic Group support to many more Nautobot models.
- [#5791](https://github.com/nautobot/nautobot/issues/5791) - Added support for specifying a Device's Primary IP from an interface on a child Module.
- [#5792](https://github.com/nautobot/nautobot/issues/5792) - Added display of components from installed modules to the Device Component tabs.
- [#5817](https://github.com/nautobot/nautobot/issues/5817) - Added Celery Worker details to the Job Result Advanced Tab.
- [#5817](https://github.com/nautobot/nautobot/issues/5817) - Added `advanced_content_left_page` block to the Advanced Tab.
- [#5872](https://github.com/nautobot/nautobot/issues/5872) - Added CloudService Model, UI, GraphQL and REST API.
- [#5873](https://github.com/nautobot/nautobot/issues/5873) - Added worker status page for staff users.
- [#5890](https://github.com/nautobot/nautobot/issues/5890) - Add CSS class to pagination dropdown to resolve issue with color-scheme.
- [#5923](https://github.com/nautobot/nautobot/issues/5923) - Added `prefers_id` keyword argument to NaturalKeyOrPKMultipleChoiceFilter initialization to use the object ID instead of the `to_field_name` when automatically generating a form field for the filter.
- [#5933](https://github.com/nautobot/nautobot/issues/5933) - Added tables of related `CloudService` and/or `CloudNetwork` instances to the `CloudResourceType` detail view.
- [#5933](https://github.com/nautobot/nautobot/issues/5933) - Added `description` field to `CloudService` model.

### Changed

- [#2101](https://github.com/nautobot/nautobot/issues/2101) - Updated device interfaces filter to support filtering by interface name as well as by ID.
- [#3749](https://github.com/nautobot/nautobot/issues/3749) - Changed behavior of the `CHANGELOG_RETENTION` setting; it no longer applies automatically to force cleanup of ObjectChange records over a certain age cutoff, but instead serves as the default cutoff age whenever running the new "Logs Cleanup" system Job.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Changed default Docker image Python version to 3.12.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Changed object "detail" views to only show `Dynamic Groups` tab if the object belongs to at least one such group.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Replaced Redis implementation of Dynamic Group membership caches with a database cache implementation using the StaticGroupAssociation model.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Changed `DynamicGroup.members`, `DynamicGroup.has_member()`, and `DynamicGroupMixin.dynamic_groups` APIs to always use the database cache.
- [#5631](https://github.com/nautobot/nautobot/issues/5631) - Changed behavior of models that inherit directly from `BaseModel` (not `OrganizationalModel` or `PrimaryModel`) to default to `is_contact_associable_model = False`.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Changed `TreeManager` class (used for tree-models such as Location, RackGroup, and TenantGroup) default behavior from `with_tree_fields` to `without_tree_fields`. This should improve performance in many cases but may impact Apps or Jobs that were relying on the old default; such code should be updated to explicitly call `.with_tree_fields()` where appropriate.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Merged the `StaticGroup` model added in [#5472](https://github.com/nautobot/nautobot/issues/5472) into the existing `DynamicGroup` model as a special type of group.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Replaced `static_groups` filter added in [#5472](https://github.com/nautobot/nautobot/issues/5472) with a `dynamic_groups` filter.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Replaced `static_groups` model form field added in [#5472](https://github.com/nautobot/nautobot/issues/5472) with a `dynamic_groups` field.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Replaced `Static Groups` object table column added in [#5472](https://github.com/nautobot/nautobot/issues/5472) with a `Dynamic Groups` column.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Replaced `static_groups` GraphQL field added in [#5472](https://github.com/nautobot/nautobot/issues/5472) with a `dynamic_groups` field.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Replaced `StaticGroupMixin` model mixin class added in [#5631](https://github.com/nautobot/nautobot/pull/5631) with a `DynamicGroupsModelMixin` class. Still included by default in `OrganizationalModel` and `PrimaryModel`.
- [#5790](https://github.com/nautobot/nautobot/issues/5790) - Updated Cable table to display the parent Device of Cables connected to Modules in a Device.
- [#5790](https://github.com/nautobot/nautobot/issues/5790) - Updated device and `device_id` filters for Cables, Interfaces, and other modular device components to recognize components that are nested in Modules in a Device.
- [#5790](https://github.com/nautobot/nautobot/issues/5790) - Updated Cable connect form to allow connecting to Console Ports, Console Server Ports, Interfaces, Power Ports, Power Outlets, Front Ports, and Rear Ports that are nested in Modules in a Device.
- [#5790](https://github.com/nautobot/nautobot/issues/5790) - Updated Interface `device` filter to allow filtering on Device `name` or `id`.
- [#5790](https://github.com/nautobot/nautobot/issues/5790) - Updated `Cable._termination_a_device` and `Cable._termination_b_device` to cache the Device when cables are connected to an Interface or Port of a Module in a Device.
- [#5817](https://github.com/nautobot/nautobot/issues/5817) - Removed Additional Data tab on Job Result view and collapsed the data into Advanced Tab.
- [#5826](https://github.com/nautobot/nautobot/issues/5826) - Moved `SavedView` model from `users` app to `extras` app.
- [#5841](https://github.com/nautobot/nautobot/issues/5841) - Added role field as a default column for Device Interface tab and VirtualMachine VMInterface table.
- [#5869](https://github.com/nautobot/nautobot/issues/5869) - Combined bulk-edit/bulk-delete/bulk-group-update buttons into a single button with a pop-up menu when appropriate.
- [#5870](https://github.com/nautobot/nautobot/issues/5870) - Consolidated List View Action buttons into a single button with a dropdown menu.
- [#5871](https://github.com/nautobot/nautobot/issues/5871) - Consolidated Detail View Action buttons into a single button with a dropdown menu.
- [#5873](https://github.com/nautobot/nautobot/issues/5873) - Updated the job run form to use more of the horizontal whitespace on the page.
- [#5933](https://github.com/nautobot/nautobot/issues/5933) - Renamed `CloudType` model to `CloudResourceType` for improved clarity.
- [#5977](https://github.com/nautobot/nautobot/issues/5977) - Changed the provider field help text of CloudAccount and CloudResourceType model classes and forms.
- [#5978](https://github.com/nautobot/nautobot/issues/5978) - Changed CloudService `cloud_network` field from a ForeignKey to a ManyToMany called `cloud_networks`.

### Deprecated

- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Deprecated the properties `DynamicGroup.members_cached`, `DynamicGroup.members_cache_key`, `DynamicGroupMixin.dynamic_groups_cached`, `DynamicGroupMixin.dynamic_groups_list`, and `DynamicGroupMixin.dynamic_groups_list_cached`.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Deprecated the `DynamicGroupMixin` model mixin class. Models supporting Dynamic Groups should use `DynamicGroupsModelMixin` instead.
- [#5870](https://github.com/nautobot/nautobot/issues/5870) - Deprecated the blocks `block export_button` and `block import_button` in `generic/object_list.html`. Apps and templates should migrate to using `block export_list_element` and `block import_list_element` respectively.

### Removed

- [#3749](https://github.com/nautobot/nautobot/issues/3749) - Removed automatic random cleanup of ObjectChange records when processing requests and signals.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Removed `DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT` setting as it is no longer relevant after refactoring the Dynamic Group membership caching implementation.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Removed the `StaticGroup` model added in #5472, replacing it with a subtype of the `DynamicGroup` model.

### Fixed

- [#2352](https://github.com/nautobot/nautobot/issues/2352) - Fixed random deadlocks in long-running Jobs resulting from the ObjectChange automatic cleanup signal.
- [#5123](https://github.com/nautobot/nautobot/issues/5123) - Fixed an unhandled `ValueError` when filtering on `vlans` by their UUID rather than their VLAN ID.
- [#5442](https://github.com/nautobot/nautobot/issues/5442) - Replaced overly broad `invalidate_models_cache` signal handler with two more narrowly scoped handlers, preventing the signal handler from being invoked for operations on irrelevant models.
- [#5442](https://github.com/nautobot/nautobot/issues/5442) - Fixed incorrect linkification of JobLogEntry table rows when a record had a `log_object` but no `absolute_url`.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Significantly improved performance of Dynamic Group UI views.
- [#5774](https://github.com/nautobot/nautobot/issues/5774) - Fixed the bug that required users and administrators to manage additional permission to be able to use saved views.
- [#5814](https://github.com/nautobot/nautobot/issues/5814) - Fixed style issues with Saved Views and other language code blocks.
- [#5818](https://github.com/nautobot/nautobot/issues/5818) - Fixed broken table configure buttons in device and module component tabs.
- [#5842](https://github.com/nautobot/nautobot/issues/5842) - Fixed missing classes when importing `*` from nautobot.ipam.models.
- [#5877](https://github.com/nautobot/nautobot/issues/5877) - Resolved issue with tags not saving on Dynamic Groups.
- [#5880](https://github.com/nautobot/nautobot/issues/5880) - Fixed overflowing device component tables in device and module component tabs.
- [#5880](https://github.com/nautobot/nautobot/issues/5880) - Fixed an exception when trying to edit an IPAddress that had a NAT Inside IPAddress that was related to a component attached to a module.
- [#5880](https://github.com/nautobot/nautobot/issues/5880) - Fixed incorrect sort order of interfaces in the device and module interface tabs.
- [#5898](https://github.com/nautobot/nautobot/issues/5898) - Replaced `object-metadatas` in UI and REST API urls with `object-metadata`.
- [#5932](https://github.com/nautobot/nautobot/issues/5932) - Fixed visual bug in consolidated action button for list views.
- [#5933](https://github.com/nautobot/nautobot/issues/5933) - Fixed missing `cloud.cloudservice` content-type option on `CloudResourceType` model.
- [#5933](https://github.com/nautobot/nautobot/issues/5933) - Fixed incorrect submenu heading in `Cloud` navigation menu.
- [#5933](https://github.com/nautobot/nautobot/issues/5933) - Fixed incorrect rendering of `Tags` column in Cloud object tables.
- [#5939](https://github.com/nautobot/nautobot/issues/5939) - Fixed the usage of incorrect model in Cloud Service list view action buttons.
- [#5951](https://github.com/nautobot/nautobot/issues/5951) - Removed unused consolidated action button on job list view.
- [#5952](https://github.com/nautobot/nautobot/issues/5952) - Changed generic "Bulk Actions" dropup button styling to match generic "Actions" dropdown button.

### Dependencies

- [#1758](https://github.com/nautobot/nautobot/issues/1758) - Updated `materialdesignicons` to version 7.4.47.
- [#4616](https://github.com/nautobot/nautobot/issues/4616) - Updated `django-taggit` to `~5.0.0`.
- [#4616](https://github.com/nautobot/nautobot/issues/4616) - Updated `netaddr` to `~1.3.0`.
- [#5160](https://github.com/nautobot/nautobot/issues/5160) - Updated `Django` to version `~4.2.13`.
- [#5160](https://github.com/nautobot/nautobot/issues/5160) - Updated `django-db-file-storage` to version `~0.5.6.1`.
- [#5160](https://github.com/nautobot/nautobot/issues/5160) - Updated `django-timezone-field` to version `~6.1.0`.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Updated Docker build and CI to use `poetry` `1.8.2`.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Removed development dependency on `mkdocs-include-markdown-plugin` as it's no longer used in Nautobot's documentation.
- [#5518](https://github.com/nautobot/nautobot/issues/5518) - Updated `drf-spectacular` to version `0.27.2`.
- [#5687](https://github.com/nautobot/nautobot/issues/5687) - Added [django-structlog](https://django-structlog.readthedocs.io/en/latest/) dependency.
- [#5734](https://github.com/nautobot/nautobot/issues/5734) - Updated `django-auth-ldap` dependency to `~4.8`.
- [#5734](https://github.com/nautobot/nautobot/issues/5734) - Updated `django-tree-queries` dependency to `~0.19`.
- [#5734](https://github.com/nautobot/nautobot/issues/5734) - Updated `Markdown` dependency to `~3.6`.
- [#5735](https://github.com/nautobot/nautobot/issues/5735) - Updated `django-constance` dependency to `~3.1.0`
- [#5735](https://github.com/nautobot/nautobot/issues/5735) - Updated `emoji` dependency to `~2.12.1`.
- [#5735](https://github.com/nautobot/nautobot/issues/5735) - Widened `napalm` dependency to permit version 5.x.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `celery` to `~5.3.6`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `django-cors-headers` to `~4.4.0`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `django-health-check` to `~3.18.3`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `django-structlog` to `^8.1.0`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `djangorestframework` to `~3.15.2`.
- [#5889](https://github.com/nautobot/nautobot/issues/5889) - Updated `django-filter` to version `~24.2`.
- [#5889](https://github.com/nautobot/nautobot/issues/5889) - Updated `django-timezone-field` to version `~7.0`.

### Documentation

- [#5699](https://github.com/nautobot/nautobot/issues/5699) - Fixed a number of broken links within the documentation.
- [#5895](https://github.com/nautobot/nautobot/issues/5895) - Added missing model documentation for `CloudNetwork`, `CloudNetworkPrefixAssignment`, `CloudService` and ~`CloudType`~ `CloudResourceType`.
- [#5934](https://github.com/nautobot/nautobot/issues/5934) - Add Cloud Model Example and Entity Diagram.

### Housekeeping

- [#5160](https://github.com/nautobot/nautobot/issues/5160) - Replaced references to `pytz` with `zoneinfo` in keeping with Django 4.
- [#5212](https://github.com/nautobot/nautobot/issues/5212) - Enhanced `nautobot.core.testing.filters.FilterTestCases.BaseFilterTestCase.test_filters_generic()` test case to test for the presence and proper functioning of the `contacts` and `teams` filters on any appropriate model FilterSet.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Added Python 3.12 to CI.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Updated CI to use `poetry` 1.8.2 and use action `networktocode/gh-action-setup-poetry-environment@v6`.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Removed CI workaround for old Poetry versions.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Added `assertApproximateNumQueries` test-case helper method.
- [#5524](https://github.com/nautobot/nautobot/issues/5524) - Deleted unnecessary special case handling for `test_view_with_content_types`.
- [#5663](https://github.com/nautobot/nautobot/issues/5663) - Added support for `django_get_or_create` property in `BaseModelFactory`.
- [#5699](https://github.com/nautobot/nautobot/issues/5699) - Updated to `mkdocs~1.6.0` and `mkdocs-material~9.5.23`.
- [#5725](https://github.com/nautobot/nautobot/issues/5725) - Updated development dependencies `pylint` to `3.2.0`, `ruff` to `0.4.0`, and `selenium` to `4.21`.
- [#5735](https://github.com/nautobot/nautobot/issues/5735) - Updated `mkdocstrings` to `~0.25.1` and `mkdocstrings-python` to `~1.10.2`.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Substantially reduced the setup overhead (time/memory) of `OpenAPISchemaTestCases` tests.
- [#5842](https://github.com/nautobot/nautobot/issues/5842) - Fixed missing mysqldump client when trying to run tests with --parallel on mysql.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `django-debug-toolbar` development dependency to `~4.4.0`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `mkdocs-include-markdown-plugin` documentation dependency to `6.2.1`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `mkdocs-material` documentation dependency to `9.5.27`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `mkdocs-section-index` documentation dependency to `0.3.9`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `mkdocstrings-python` documentation dependency to `1.10.5`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `pylint` development dependency to `~3.2.5`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `ruff` development dependency to `~0.5.0`.
- [#5865](https://github.com/nautobot/nautobot/issues/5865) - Updated `selenium` development dependency to `~4.22.0`.
- [#5986](https://github.com/nautobot/nautobot/issues/5986) - Fixed multiple intermittent failures in unit tests.
