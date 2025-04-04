# Nautobot v2.3

This document describes all new features and changes in Nautobot 2.3.

## Upgrade Actions

### Administrators

Administrators should plan to take these actions during or immediately after upgrade from a previous version. New installations should also take note of these actions where appropriate.

- Python 3.12 is now the default recommended version of Python.

!!! warning "Python 3.12"
    Because Nautobot prior to 2.3.0 did not declare support for Python 3.12, most Apps similarly needed to previously declare an upper bound of Python 3.11 for their own compatibility. Therefore, older versions of most Apps **will not be installable** under Python 3.12. Before migrating your Nautobot environment to Python 3.12, it is your responsibility to confirm that all relevant Apps in your environment are also compatible and installable.

    There is a minor "chicken-and-egg" problem here in that Apps generally cannot declare support for a new Python version before Nautobot itself publishes a release that does so; therefore, as of the 2.3.0 Nautobot release day, most Apps have not yet been updated to declare support for Python 3.12. We'll be working in the following days to promptly update our supported Apps as needed, so stay tuned.

!!! warning "Docker images"
    As has been Nautobot's policy since version 1.6.1, our published Docker images _that are not tagged with a specific Python version_ implicitly always include the _latest_ supported version of Python. This means that as of the release of Nautobot 2.3.0, the tags `latest`, `stable`, `2.3`, and `2.3.0` will all indicate Docker images that include Python 3.12, whereas previously these indicated Python 3.11 images. As noted above and below, updating to Python 3.12 may not be immediately desirable (or even possible, depending on the status of your Apps) as a "day one" action.

    If you need to stay with a given Python version for the time being, you must make sure that you're relying on an appropriately specific image tag, such as `2.3-py3.11`, `stable-py3.10`, etc.

- As noted [below](#dynamic-group-cache-changes-5473), a new system job is provided for automated Dynamic Group cache updates. Administrators should schedule this system job to run on a recurring basis within the Jobs UI, after the upgrade, or on new install. Configuration referencing the `DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT` setting can be safely removed, as it is no longer used. If this setting was being used previously, it is recommended to set the new scheduled job's interval to the same value.
- As noted [below](#log-cleanup-as-system-job-3749), change logging retention cleanup is now handled via a system job. Administrators should schedule this job to run on a recurring basis to meet their needs. The `CHANGELOG_RETENTION` setting is still used to define the retention period, but the scheduled system job will perform the actual cleanup, if any needed.

### Job Authors & App Developers

Job Authors and App Developers should take these actions to ensure compatibility with their Jobs and Apps.

- Job Authors and App Developers should carefully consider the [updates to the DynamicGroup API](#dynamic-group-cache-changes-5473) and decide if their use cases dictate changing their group membership access patterns to use `DynamicGroup.update_cached_members()` to find the correct balance between Dynamic Group performance and membership updates.
- Job Authors and App Developers should carefully consider the [updates to the TreeManager default behavior](#changed-treemanager-default-behavior-5786) and make necessary changes to their access of Tree based models.
- Django 4.2 is now required by Nautobot, replacing the previous Django 3.2 dependency. Job Authors and App Developers should carefully consider the updates and changes in the Django release-notes ([4.0](https://docs.djangoproject.com/en/4.2/releases/4.0/), [4.1](https://docs.djangoproject.com/en/4.2/releases/4.1/), [4.2](https://docs.djangoproject.com/en/4.2/releases/4.2/)), especially the relevant "Backwards incompatible changes" sections, to proactively identify any impact to their Apps.

!!! warning "Django 4"
    Django 4 includes a small number of breaking changes compared to Django 3. In our experience, most Apps have required few (or zero) updates to be Django 4 compatible, but your mileage may vary.

- Python 3.12 is now supported by Nautobot and is now the default recommended version of Python. Apps will likely need to update their packaging in order to explicitly declare support for Python 3.12.
- App Developers should review the feature set of their data models and consider whether their models should opt into or out of inclusion in Dynamic Groups, Contacts/Teams, Object Metadata, and Saved Views via the inclusion or omission of appropriate model mixins and flag variables. Refer to the [developer documentation](../development/apps/api/models/index.md#adding-database-models) for details.

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

Added [a set of functionality](../user-guide/platform-functionality/objectmetadata.md) for defining and managing object metadata, that is to say, data _about_ the network data managed in Nautobot, such as data provenance, data ownership, and data classification. For more details, refer to the linked documentation.

#### Python 3.12 Support ([#5429](https://github.com/nautobot/nautobot/issues/5429))

Nautobot now supports Python 3.12, and Python 3.12 is now the default Python version included in the `nautobot` Docker images.

#### VLANGroup Model Enhancement ([#6309](https://github.com/nautobot/nautobot/issues/6309))

+++ 2.3.6

Added a `range` field on the `VLANGroup` model with a default value of `1-4094`. `VLANGroup` model now also supports `custom_links`, `export_templates`, `tags`, and `webhooks`.

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
    Setting [`CHANGELOG_RETENTION`](../user-guide/administration/configuration/settings.md#changelog_retention) in your Nautobot configuration by itself no longer directly results in periodic cleanup of `ObjectChange` records. You must run (or schedule to periodically run) the `LogsCleanup` Job for this to occur.

As an additional enhancement, the `LogsCleanup` Job can also be used to cleanup `JobResult` records if desired as well.

#### UI Button Consolidation ([#5869](https://github.com/nautobot/nautobot/issues/5869), [#5870](https://github.com/nautobot/nautobot/issues/5870), [#5871](https://github.com/nautobot/nautobot/issues/5871))

Various button groups in the "object list" and "object detail" views have been consolidated following a common UI pattern of a single button for the most common action plus a popup menu for less common actions.

### Dependencies

#### Updated to Django 4.2 ([#3581](https://github.com/nautobot/nautobot/issues/3581))

As Django 3.2 has reached end-of-life, Nautobot 2.3 requires Django 4.2, the next long-term-support (LTS) version of Django. There are a number of changes in Django itself as a result of this upgrade; Nautobot App maintainers are urged to review the Django release-notes ([4.0](https://docs.djangoproject.com/en/4.2/releases/4.0/), [4.1](https://docs.djangoproject.com/en/4.2/releases/4.1/), [4.2](https://docs.djangoproject.com/en/4.2/releases/4.2/)), especially the relevant "Backwards incompatible changes" sections, to proactively identify any impact to their Apps.

<!-- pyml disable-num-lines 2 blanks-around-headers -->
<!-- towncrier release notes start -->
## v2.3.16 (2025-01-06)

### Fixed in v2.3.16

- [#5805](https://github.com/nautobot/nautobot/issues/5805) - Enabled extended filter lookup expressions of the `serial` filter for Device, Rack, and InventoryItem.
- [#5831](https://github.com/nautobot/nautobot/issues/5831) - Fixed an issue where the error message for missing custom job templates incorrectly reported "extras/job.html" instead of the actual missing template name.
- [#5882](https://github.com/nautobot/nautobot/issues/5882) - Fixed `PowerOutletTemplateTable` to use `power_port_template` instead of the incorrect field `power_port`.
- [#5882](https://github.com/nautobot/nautobot/issues/5882) - Fixed `FrontPortTemplateTable` to use `rear_port_template` instead of the incorrect field `rear_port`.
- [#6527](https://github.com/nautobot/nautobot/issues/6527) - Disabled (unsupported) sorting by the `Device` column in Console Connections, Power Connections, and Interface Connections list views.
- [#6669](https://github.com/nautobot/nautobot/issues/6669) - Removed the need for `available-prefixes`, `available-ips`, and `available-vlans` API endpoints to run validation multiple times.
- [#6676](https://github.com/nautobot/nautobot/issues/6676) - Resolved issue with IPAddressQuerySet `get_or_create` method signature not matching the base method signature.

### Housekeeping in v2.3.16

- [#6714](https://github.com/nautobot/nautobot/issues/6714) - Enabled and addressed Pylint checkers `arguments-differ`, `arguments-renamed`, `exec-used`, `hard-coded-auth-user`, `super-init-not-called`.
- [#6722](https://github.com/nautobot/nautobot/issues/6722) - Enabled Pylint `not-callable` and `no-member` checkers and addressed issues reported thereby.

## v2.3.15 (2025-01-02)

### Security in v2.3.15

- [#6695](https://github.com/nautobot/nautobot/issues/6695) - Updated dependency `Jinja2` to `~3.1.5` to address `CVE-2024-56201` and `CVE-2024-56326`.

### Added in v2.3.15

- [#6410](https://github.com/nautobot/nautobot/issues/6410) - Added `settings.PUBLISH_ROBOTS_TXT` configuration option, defaulting to `True`.

### Changed in v2.3.15

- [#6583](https://github.com/nautobot/nautobot/issues/6583) - Changed `available-vlans` API endpoint to additionally require `ipam.view_vlan` permission to view available VLANs under VLAN Group.

### Fixed in v2.3.15

- [#5545](https://github.com/nautobot/nautobot/issues/5545) - Fixed an issue in Dynamic Group Edit View where saving a valid choice in a Select-type CustomField triggered an error.
- [#6583](https://github.com/nautobot/nautobot/issues/6583) - Fixed `available-vlans`, `available-ips`, `available-prefixes` API endpoints to check object-level constrained permissions.
- [#6702](https://github.com/nautobot/nautobot/issues/6702) - Resolved issue with TagsBulkEditFormMixin missing self.model.

### Dependencies in v2.3.15

- [#6689](https://github.com/nautobot/nautobot/issues/6689) - Updated `nh3` dependency to `~0.2.20`.
- [#6689](https://github.com/nautobot/nautobot/issues/6689) - Updated `django-tables2` dependency to `~2.7.4` in Python 3.9 and later, and pinned it to `==2.7.0` under Python 3.8.

### Housekeeping in v2.3.15

- [#6688](https://github.com/nautobot/nautobot/issues/6688) - Cleaned-up documentation, misc fixes for VSCode DevContainer workflow.
- [#6689](https://github.com/nautobot/nautobot/issues/6689) - Updated documentation dependency `mkdocs-material` to `~9.5.49`.
- [#6693](https://github.com/nautobot/nautobot/issues/6693) - Changed `poetry install` in prerelease and release workflows from parallel mode to serial mode.
- [#6706](https://github.com/nautobot/nautobot/issues/6706) - Removed unnecessary `user-data.json` integration-test fixture file.

## v2.3.14 (2024-12-19)

### Added in v2.3.14

- [#6548](https://github.com/nautobot/nautobot/issues/6548) - Added logic to set the `parent` in the `clean()` method of the Prefix model, ensuring correct assignment during validation.

### Changed in v2.3.14

- [#6518](https://github.com/nautobot/nautobot/issues/6518) - Added VRFs column to Prefixes and Child Prefixes tables.
- [#6531](https://github.com/nautobot/nautobot/issues/6531) - Restrict the `id` filter field to use to only the `__n` (negation) lookup filter.
- [#6548](https://github.com/nautobot/nautobot/issues/6548) - Changed the save method of the `Prefix` model to reparent subnets and IPs only when the `network`, `namespace`, or `prefix_length` fields are updated.

### Fixed in v2.3.14

- [#4056](https://github.com/nautobot/nautobot/issues/4056) - Fixed filter of add_tags and remove_tags of bulkedit based on content type
- [#6204](https://github.com/nautobot/nautobot/issues/6204) - Fixed out-of-memory errors when `LogsCleanup` system job resulted in cascade deletion of many related objects (such as `JobLogEntry` or `nautobot_ssot.SyncLogEntry` records).
- [#6470](https://github.com/nautobot/nautobot/issues/6470) - Fixed untagged VLAN dropdown options mismatch in InterfaceEditForm and in InterfaceBulkEditForm.
- [#6496](https://github.com/nautobot/nautobot/issues/6496) - Fixed `/ipam/prefixes/<UUID>/available-ips/` to correctly consider IPs under child Prefixes.
- [#6496](https://github.com/nautobot/nautobot/issues/6496) - Fixed `Prefix.get_first_available_ip()` method to not return IP taken by child Prefixes.
- [#6664](https://github.com/nautobot/nautobot/issues/6664) - Fixed `circuit_type` column not included correctly in CircuitTable default columns.
- [#6678](https://github.com/nautobot/nautobot/issues/6678) - Fixed incorrect copy button behavior on global search page.

### Documentation in v2.3.14

- [#6590](https://github.com/nautobot/nautobot/issues/6590) - Added an `ExampleEverythingJob` to the Example App and updated Job developer documentation to reference it as an example.

### Housekeeping in v2.3.14

- [#6657](https://github.com/nautobot/nautobot/issues/6657) - Updated documentation dependency `mkdocs-material` to `~9.5.48`.
- [#6659](https://github.com/nautobot/nautobot/issues/6659) - Enhanced development environment and associated `invoke` tasks to be Nautobot major/minor version aware, such that a different Docker compose `project-name` (and different local Docker image label) will be used for containers in a `develop`-based branch versus a `next`-based branch.
- [#6679](https://github.com/nautobot/nautobot/issues/6679) - Added `logs` task to `tasks.py` to view the logs of a docker compose service.

## v2.3.13 (2024-12-10)

### Security in v2.3.13

- [#6615](https://github.com/nautobot/nautobot/issues/6615) - Updated `Django` to `~4.2.17` due to `CVE-2024-53907` and `CVE-2024-53908`.

### Added in v2.3.13

- [#4817](https://github.com/nautobot/nautobot/issues/4817) - Added `Cluster` field on DeviceBulkEditForm.
- [#5333](https://github.com/nautobot/nautobot/issues/5333) - Added `Comments` field on DeviceBulkEditForm.
- [#6498](https://github.com/nautobot/nautobot/issues/6498) - Added support for an additional `suffix` when utilizing TableExtension to support tables like IPAddressDetailTable.
- [#6586](https://github.com/nautobot/nautobot/issues/6586) - Added description and weight on RoleBulkEditForm.
- [#6605](https://github.com/nautobot/nautobot/issues/6605) - Added `BaseTable` support for a `data_transform_callback` function that can be used to modify the table data after performing automatic QuerySet optimizations. (Several IPAM tables now use this functionality).
- [#6605](https://github.com/nautobot/nautobot/issues/6605) - Enhanced `LinkedCountColumn` to support a `distinct` parameter to handle cases where counts may otherwise be incorrect.
- [#6605](https://github.com/nautobot/nautobot/issues/6605) - Added `ip_addresses` and `has_ip_addresses` filter support to Device, Interface, and VirtualMachine FilterSets.
- [#6613](https://github.com/nautobot/nautobot/issues/6613) - Enhanced Prefix detail view "Child Prefixes" table to render associated Locations more intelligently.
- [#6614](https://github.com/nautobot/nautobot/issues/6614) - Enhanced IP Address tables to show the name of the associated Interface or VM Interface if only a single such association is present for a given IP Address.

### Changed in v2.3.13

- [#6166](https://github.com/nautobot/nautobot/issues/6166) - Enhanced the REST API to generally make it possible to create objects with known ids on request.

### Fixed in v2.3.13

- [#3124](https://github.com/nautobot/nautobot/issues/3124) - Fixed inability of ImageAttachment and DeviceType API endpoints to accept `multipart/form-data` file uploads.
- [#5166](https://github.com/nautobot/nautobot/issues/5166) - Fixed a `ProgrammingError` when applying permissions containing network-address-based constraints.
- [#6466](https://github.com/nautobot/nautobot/issues/6466) - Fixed `table_config` field not showing up correctly in the Saved View modal.
- [#6498](https://github.com/nautobot/nautobot/issues/6498) - Fixed error when using TableExtension when the table is missing `Meta.default_columns`.
- [#6605](https://github.com/nautobot/nautobot/issues/6605) - Improved rendering performance of the IPAddress list view in cases where the `Interfaces`, `Devices`, `VM Interfaces`, `Virtual Machines`, and/or `Assigned` columns are not shown.
- [#6605](https://github.com/nautobot/nautobot/issues/6605) - Improved performance of `TreeModel.display` calculation by making better use of the cache.
- [#6609](https://github.com/nautobot/nautobot/issues/6609) - Fixed unnecessary call to the database when logging from a Job with the parameter `extra={"skip_db_logging": True}`.
- [#6624](https://github.com/nautobot/nautobot/issues/6624) - Fixed issue with `group_sync.py` where it was accessing the settings using environment variable name vs the actual settings name.
- [#6624](https://github.com/nautobot/nautobot/issues/6624) - Fixed the `SOCIAL_AUTH_PIPELINE` settings to include the entire path of the `group_sync` function.

### Dependencies in v2.3.13

- [#6615](https://github.com/nautobot/nautobot/issues/6615) - Updated `nh3` to `~0.2.19`.

### Documentation in v2.3.13

- [#6622](https://github.com/nautobot/nautobot/issues/6622) - Fixed AzureAD documentation for custom_module logging example.
- [#6636](https://github.com/nautobot/nautobot/issues/6636) - Fixed `group_sync` path in the SSO documentation.

### Housekeeping in v2.3.13

- [#6615](https://github.com/nautobot/nautobot/issues/6615) - Updated documentation dependency `mkdocs-material` to `~9.5.47`.

## v2.3.12 (2024-11-25)

### Added in v2.3.12

- [#6532](https://github.com/nautobot/nautobot/issues/6532) - Added a keyboard shortcut (⌘+enter or ctrl+enter) to submit forms when typing in a textarea.
- [#6543](https://github.com/nautobot/nautobot/issues/6543) - Defined a generic SSO group authentication module that can be shared by any OAuth2/OIDC backend.
- [#6550](https://github.com/nautobot/nautobot/issues/6550) - Added OSFP-XD (800GE and 1600GE) and OSFP1600 interface types.

### Fixed in v2.3.12

- [#6242](https://github.com/nautobot/nautobot/issues/6242) - Fixed "copy" button on Device tabbed views to now only copy the device name.
- [#6478](https://github.com/nautobot/nautobot/issues/6478) - Fixed inconsistent rendering of the Role field.
- [#6509](https://github.com/nautobot/nautobot/issues/6509) - Disallowed association of `ObjectMetadata` as metadata to other `ObjectMetadata` records.
- [#6509](https://github.com/nautobot/nautobot/issues/6509) - Removed unused object-detail view for `ObjectMetadata` records.
- [#6519](https://github.com/nautobot/nautobot/issues/6519) - Fixed `vrf` field options not loading in VMInterfaceBulkEditForm, VMInterfaceForm, and VMInterfaceCreateForm.
- [#6519](https://github.com/nautobot/nautobot/issues/6519) - Added missing `VRF` entry in VMInterface detail view.
- [#6533](https://github.com/nautobot/nautobot/issues/6533) - Fixed an issue where the string representation of the Note model would throw an error if accessed before saving it to the database.
- [#6547](https://github.com/nautobot/nautobot/issues/6547) - Fixed incorrect VRF filter specified on VRF column on Prefix Table.
- [#6564](https://github.com/nautobot/nautobot/issues/6564) - Fixed an `AttributeError` raised when an App overrides a NautobotUIViewSet view.

### Dependencies in v2.3.12

- [#6459](https://github.com/nautobot/nautobot/issues/6459) - Updated `mysqlclient` dependency to `~2.2.6`.

### Documentation in v2.3.12

- [#6516](https://github.com/nautobot/nautobot/issues/6516) - Updated release notes to make it clearer which are model changes.
- [#6524](https://github.com/nautobot/nautobot/issues/6524) - Updated AzureAD authentication documentation.
- [#6567](https://github.com/nautobot/nautobot/issues/6567) - Fixed incorrect example in documentation on using test factories.

### Housekeeping in v2.3.12

- [#6459](https://github.com/nautobot/nautobot/issues/6459) - Updated documentation dependencies `mkdocs-redirects` to `1.2.2` and `mkdocs-material` to `9.5.46`.
- [#6500](https://github.com/nautobot/nautobot/issues/6500) - Added support for `invoke showmigrations` command.

## v2.3.11 (2024-11-12)

### Added in v2.3.11

- [#6231](https://github.com/nautobot/nautobot/issues/6231) - Added `nautobot.apps.utils.get_related_field_for_models()` helper function.
- [#6231](https://github.com/nautobot/nautobot/issues/6231) - Added optional `lookup` parameter to `LinkedCountColumn`.

### Changed in v2.3.11

- [#5321](https://github.com/nautobot/nautobot/issues/5321) - For bulk delete all objects view, only show the confirmation dialog without the table that shows the objects that would be deleted.
- [#6231](https://github.com/nautobot/nautobot/issues/6231) - Changed most related-object-count table columns (e.g. the "Locations" column in a Prefix table) to, if only a single related record is present (e.g. a single Location is associated with a given Prefix), display that related record directly instead of just displaying `1`.
- [#6465](https://github.com/nautobot/nautobot/issues/6465) - For bulk edit all objects view, skip rendering the table of related objects in the confirmation page.

### Fixed in v2.3.11

- [#6414](https://github.com/nautobot/nautobot/issues/6414) - Fixed layout bug in browsable REST API.
- [#6442](https://github.com/nautobot/nautobot/issues/6442) - Fixed an issue where GitLab CI pipelines fail using all versions of official Docker images.
- [#6453](https://github.com/nautobot/nautobot/issues/6453) - Fixed issue where interfaces cannot be removed/deleted from an Interface for Modules.
- [#6472](https://github.com/nautobot/nautobot/issues/6472) - Fixed incorrect placement of buttons in create and edit views.
- [#6472](https://github.com/nautobot/nautobot/issues/6472) - Fixed the panel width in multiple create and edit views.
- [#6490](https://github.com/nautobot/nautobot/issues/6490) - Added missing `vrf_count` column to Prefix table in PrefixListView.
- [#6491](https://github.com/nautobot/nautobot/issues/6491) - Added missing `vrf` field to `VMInterfaceForm` and `VMInterfaceCreateForm`.
- [#6492](https://github.com/nautobot/nautobot/issues/6492) - Fixed `vlan_group` field is not filtered by `locations` field input on VLANForm.

### Documentation in v2.3.11

- [#6485](https://github.com/nautobot/nautobot/issues/6485) - Added additional clarification for enabling request profiling via user profile.

### Housekeeping in v2.3.11

- [#6449](https://github.com/nautobot/nautobot/issues/6449) - Added an integration test to create a Manufacturer, DeviceType, LocationType, Location, Role and Device to test the create forms and select2 api form fields are working correctly.
- [#6449](https://github.com/nautobot/nautobot/issues/6449) - Fixed incorrect assertion in core navbar integration tests.
- [#6449](https://github.com/nautobot/nautobot/issues/6449) - Added helper functions to SeleniumTestCase to perform some common UI actions.
- [#6455](https://github.com/nautobot/nautobot/issues/6455) - Fixed two tests which always passed due to errors in their implementation. Ensured they provide value by checking against the correct results.
- [#6497](https://github.com/nautobot/nautobot/issues/6497) - Added support for `--no-reusedb` option to `invoke integration-test` task.

## v2.3.10 (2024-10-29)

### Added in v2.3.10

- [#6421](https://github.com/nautobot/nautobot/issues/6421) - Added cacheable `CustomField.objects.keys_for_model(model)` API.
- [#6421](https://github.com/nautobot/nautobot/issues/6421) - Added queryset caching in `web_request_context` for more efficient JobHook and Webhook dispatching on bulk requests.
- [#6421](https://github.com/nautobot/nautobot/issues/6421) - Added logging to JobResults for CustomField provisioning background tasks.
- [#6421](https://github.com/nautobot/nautobot/issues/6421) - Added more efficient database calls for most cases of bulk-provisioning CustomField data on model objects.

### Changed in v2.3.10

- [#6421](https://github.com/nautobot/nautobot/issues/6421) - Increased soft/hard time limits on CustomField provisioning background tasks to 1800 and 2000 seconds respectively.

### Fixed in v2.3.10

- [#6421](https://github.com/nautobot/nautobot/issues/6421) - Fixed long-running-at-scale transaction lock on records while adding/removing a CustomField definition.
- [#6441](https://github.com/nautobot/nautobot/issues/6441) - Fixed a regression in 2.3.9 that broke the rendering of the Device create/edit form.

### Dependencies in v2.3.10

- [#6423](https://github.com/nautobot/nautobot/issues/6423) - Updated `mysqlclient` to `~2.2.5`.

### Housekeeping in v2.3.10

- [#6423](https://github.com/nautobot/nautobot/issues/6423) - Updated documentation dependency `mkdocs-material` to `~9.5.42`.

## v2.3.9 (2024-10-28)

### Added in v2.3.9

- [#4899](https://github.com/nautobot/nautobot/issues/4899) - Added TableExtension class to allow app developers to add columns to core tables.
- [#6336](https://github.com/nautobot/nautobot/issues/6336) - Added logic to ModuleBay model to ensure that if the `position` field is empty, its value will be automatically populated from the `name` of the Module Bay instance.
- [#6372](https://github.com/nautobot/nautobot/issues/6372) - Added environment variable support for setting `CSRF_TRUSTED_ORIGINS`.

### Changed in v2.3.9

- [#6336](https://github.com/nautobot/nautobot/issues/6336) - Enhanced `position` fields on ModuleBayCreate/UpdateForms to auto-populate their values from `name` fields.
- [#6386](https://github.com/nautobot/nautobot/issues/6386) - Changed `GitRepositorySync` system Job to run atomically (all-or-nothing), such that any failure in the resync will cause all associated database updates to be reverted.
- [#6386](https://github.com/nautobot/nautobot/issues/6386) - Changed behavior of change logging `web_request_context()` to only reload Job code when a relevant JobHook is found to apply to the change in question.

### Fixed in v2.3.9

- [#6297](https://github.com/nautobot/nautobot/issues/6297) - Fixed overly broad scope of the TreeModel `invalidate_max_depth_cache` signal so that it now correctly only fires for TreeModel instances rather than all models.
- [#6297](https://github.com/nautobot/nautobot/issues/6297) - Improved performance of DynamicGroup membership updates/recalculations when dealing with large numbers of member objects.
- [#6386](https://github.com/nautobot/nautobot/issues/6386) - Fixed reversed chronological ordering of JobHooks and Webhooks sent from a single `web_request_context` session.
- [#6400](https://github.com/nautobot/nautobot/issues/6400) - Removed misleading help text from ModularComponentForm, as the `{module}` auto-substitution in names only applies through component _templates_ at present.
- [#6415](https://github.com/nautobot/nautobot/issues/6415) - Added missing column `software_version` to the Device Table in Device List View.
- [#6425](https://github.com/nautobot/nautobot/issues/6425) - Fixed bug in which ColoredLabelColumn() wasn't being applied to the `role` column on Device/VM interfaces.

### Dependencies in v2.3.9

- [#6362](https://github.com/nautobot/nautobot/issues/6362) - Updated `psycopg2-binary` dependency to `~2.9.10`.

### Housekeeping in v2.3.9

- [#6362](https://github.com/nautobot/nautobot/issues/6362) - Updated documentation dependency `mkdocs-material` to `~9.5.41`.

## v2.3.8 (2024-10-18)

### Fixed in v2.3.8

- [#5050](https://github.com/nautobot/nautobot/issues/5050) - Changed logic to permit VLANs assigned to a device's location's parent locations (including parents of parents, etc.) to be assigned to that device's interfaces.
- [#6297](https://github.com/nautobot/nautobot/issues/6297) - Fixed paginator widget to display the current selected `per_page` value even if it's not one of the `PER_PAGE_DEFAULTS` options.
- [#6297](https://github.com/nautobot/nautobot/issues/6297) - Added pagination of related-object tables to many IPAM views to avoid errors when very large quantities of related records are present.
- [#6380](https://github.com/nautobot/nautobot/issues/6380) - Fixed issue with Installed Apps page trying to render invalid links.
- [#6385](https://github.com/nautobot/nautobot/issues/6385) - Restored `Prefix.get_child_ips()` API mistakenly removed from v2.3.5 through v2.3.7.

## v2.3.7 (2024-10-15)

### Added in v2.3.7

- [#2784](https://github.com/nautobot/nautobot/issues/2784) - Added `assertBodyContains()` test helper API to `NautobotTestCaseMixin`.

### Changed in v2.3.7

- [#6205](https://github.com/nautobot/nautobot/issues/6205) - Changed initial `Nautobot initialized!` message logged on startup to include the Nautobot version number.
- [#6350](https://github.com/nautobot/nautobot/issues/6350) - Changed the way that `ensure_git_repository` logs hashes to include the name of the repository.

### Fixed in v2.3.7

- [#6158](https://github.com/nautobot/nautobot/issues/6158) - Fixed a UI overflow issue with the Tenant Stats panel.
- [#6299](https://github.com/nautobot/nautobot/issues/6299) - Added retry logic and error handling for several cases where an intermittent Redis connection error could cause Celery to throw an exception.
- [#6318](https://github.com/nautobot/nautobot/issues/6318) - Fixed duplicate loading of `nautobot_config.py` during Nautobot startup.
- [#6329](https://github.com/nautobot/nautobot/issues/6329) - Added a data migration to fix DynamicGroup `group_type` values set incorrectly in upgrading to Nautobot 2.3.x.

### Dependencies in v2.3.7

- [#6299](https://github.com/nautobot/nautobot/issues/6299) - Added a direct dependency on `kombu` to guarantee the presence of some essential fixes for this Celery dependency.

### Housekeeping in v2.3.7

- [#2784](https://github.com/nautobot/nautobot/issues/2784) - Added usage of `extract_page_body()` to many view-related test cases in order to make their failure output more readable.
- [#2784](https://github.com/nautobot/nautobot/issues/2784) - Modified many view-related test cases to use new `assertBodyContains()` test helper method for brevity.
- [#6283](https://github.com/nautobot/nautobot/issues/6283) - Updated documentation dependency `mkdocs-material` to `~9.5.39`.
- [#6318](https://github.com/nautobot/nautobot/issues/6318) - Fixed an error when rerunning parallel tests with a cached database and test factories enabled.
- [#6318](https://github.com/nautobot/nautobot/issues/6318) - Fixed a permission-denied error on the `MEDIA_ROOT` volume when running the local development environment with `docker-compose.final.yml`.
- [#6318](https://github.com/nautobot/nautobot/issues/6318) - Increased the healthcheck `start_period` in the local development environment to 10 minutes.
- [#6318](https://github.com/nautobot/nautobot/issues/6318) - Added `--remove-orphans` to the docker compose commands for `invoke stop` and `invoke destroy`.

## v2.3.6 (2024-10-02)

### Added in v2.3.6

- [#5903](https://github.com/nautobot/nautobot/issues/5903) - Added range field on `VLANGroup` model.
- [#5903](https://github.com/nautobot/nautobot/issues/5903) - Added tags on `VLANGroup` model.

### Fixed in v2.3.6

- [#6304](https://github.com/nautobot/nautobot/issues/6304) - Fixed an error during startup when an App included a REST API serializer inheriting from an unexpected base class.
- [#6304](https://github.com/nautobot/nautobot/issues/6304) - Fixed a warning during startup about the `extras.FileAttachment` model.

### Documentation in v2.3.6

- [#6304](https://github.com/nautobot/nautobot/issues/6304) - Added a note to the release overview section for app developers regarding opt-in/opt-out of model features.
- [#6304](https://github.com/nautobot/nautobot/issues/6304) - Updated app model developer documentation with more details about feature opt-out.

### Housekeeping in v2.3.6

- [#6308](https://github.com/nautobot/nautobot/issues/6308) - Increase the minimum number of content-types to three and capped the maximum to five for MetadataType instances created by MetadataTypeFactory.

## v2.3.5 (2024-09-30)

### Added in v2.3.5

- [#6257](https://github.com/nautobot/nautobot/issues/6257) - Added `is_occupied` boolean filter to the Rack elevation API endpoint to allow filtering by occupied or unoccupied units.
- [#6289](https://github.com/nautobot/nautobot/issues/6289) - Added the add button to IPAM Services.

### Changed in v2.3.5

- [#6057](https://github.com/nautobot/nautobot/issues/6057) - Enhanced job delete functions to prevent users from deleting system jobs from the UI and the API.

### Fixed in v2.3.5

- [#5802](https://github.com/nautobot/nautobot/issues/5802) - Override `get_required_permission()` in SavedViewUIViewSet to achieve the intended behavior.
- [#5924](https://github.com/nautobot/nautobot/issues/5924) - Fixed the redirect URL for the Device Bay Populate/Depopulate view to take the user back to the Device Bays tab on the Device page.
- [#6170](https://github.com/nautobot/nautobot/issues/6170) - Fix Prefix IPAddresses not accounting for Child Prefix IPAddresses in the UI.
- [#6217](https://github.com/nautobot/nautobot/issues/6217) - Fixed SavedView functionality not working in Rack Elevation List View.
- [#6233](https://github.com/nautobot/nautobot/issues/6233) - Corrected presentation of rendered Markdown content in Notes table.
- [#6248](https://github.com/nautobot/nautobot/issues/6248) - Fixed Device Type link and count from Device Family Detail View.
- [#6257](https://github.com/nautobot/nautobot/issues/6257) - Fixed the selection options for `position` on the device add/edit form to disable RUs that are currently occupied.
- [#6289](https://github.com/nautobot/nautobot/issues/6289) - Fixed lookup of IP Addresses in the Service form.

### Dependencies in v2.3.5

- [#6247](https://github.com/nautobot/nautobot/issues/6247) - Updated documentation dependency `mkdocs-material` to `~9.5.35`.
- [#6287](https://github.com/nautobot/nautobot/issues/6287) - Replaced incorrect `django-structlog[all]` dependency with `django-structlog[celery]`.

### Documentation in v2.3.5

- [#6264](https://github.com/nautobot/nautobot/issues/6264) - Added to the core developer documentation a warning against the use of data factories within test case code.

### Housekeeping in v2.3.5

- [#5802](https://github.com/nautobot/nautobot/issues/5802) - Override `get_required_permission()` in SavedViewUIViewSet to achieve the intended behavior.
- [#6264](https://github.com/nautobot/nautobot/issues/6264) - Changed `invoke unittest` to default to `--parallel` even when a `--label` value is specified.
- [#6264](https://github.com/nautobot/nautobot/issues/6264) - Added support for `invoke unittest --no-parallel`.
- [#6285](https://github.com/nautobot/nautobot/issues/6285) - Added support for `invoke unittest --no-reusedb` and `nautobot-server test --no-reusedb` to streamline testing when switching frequently between branches.
- [#6292](https://github.com/nautobot/nautobot/issues/6292) - Corrected logic of several VLAN test cases.

## v2.3.4 (2024-09-18)

### Added in v2.3.4

- [#5795](https://github.com/nautobot/nautobot/issues/5795) - Added support for `NAUTOBOT_CACHES_TIMEOUT` environment variable.
- [#6207](https://github.com/nautobot/nautobot/issues/6207) - Added the ability to filter virtual machines by their `cluster` names or IDs.

### Changed in v2.3.4

- [#5795](https://github.com/nautobot/nautobot/issues/5795) - Changed default cache timeout for Constance configuration from 1 day to 300 seconds to match other caches.

### Fixed in v2.3.4

- [#6207](https://github.com/nautobot/nautobot/issues/6207) - Fixed incorrect link in ClusterTable for device count column.
- [#6207](https://github.com/nautobot/nautobot/issues/6207) - Fixed incorrect link in PowerPanelTable for power feed count column.
- [#6230](https://github.com/nautobot/nautobot/issues/6230) - Fixed an issue with Celery Scheduler around datetime imports.

### Documentation in v2.3.4

- [#5795](https://github.com/nautobot/nautobot/issues/5795) - Consolidated "Required Settings" and "Optional Settings" docs into a single unified "Settings" document.
- [#5795](https://github.com/nautobot/nautobot/issues/5795) - Consolidated "Administration: Installation Extras" docs section into the "Administration: Guides" section.
- [#5795](https://github.com/nautobot/nautobot/issues/5795) - Moved "Caching" content from the "Administration: Guides" section into the "Administration: Configuration" section as a new "Redis" document.
- [#5795](https://github.com/nautobot/nautobot/issues/5795) - Added `environment_variables` keys to `settings.yaml` to more accurately document settings that are influenced by multiple environment variables together.
- [#5795](https://github.com/nautobot/nautobot/issues/5795) - Removed `is_required_setting` keys from `settings.yaml` as no longer relevant.

### Housekeeping in v2.3.4

- [#5859](https://github.com/nautobot/nautobot/issues/5859) - Changed `--cache-test-fixtures` and `--keepdb` flags from opt-in to opt-out for `invoke unittest` and `invoke integration-test` commands.
- [#5859](https://github.com/nautobot/nautobot/issues/5859) - Changed `invoke unittest` to automatically include `--parallel` flag when running the entire unit test suite.
- [#6222](https://github.com/nautobot/nautobot/issues/6222) - Fixed `plugin_upstream_testing_base.yml` to work with app cookiecutter v2.3 Dockerfile.
- [#6227](https://github.com/nautobot/nautobot/issues/6227) - Fixed typo in app upstream testing workflow.

## v2.3.3 (2024-09-16)

### Security in v2.3.3

- [#6212](https://github.com/nautobot/nautobot/issues/6212) - Updated `Django` to `~4.2.16` to address `CVE-2024-45230` and `CVE-2024-45231`.

### Fixed in v2.3.3

- [#6184](https://github.com/nautobot/nautobot/issues/6184) - Fixed an exception in `extras.models.groups._map_filter_fields` method when certain App `filter_extensions` were present.
- [#6190](https://github.com/nautobot/nautobot/issues/6190) - Added `display` property to Prefix to display its namespace along with the prefix to allow differentiation between prefixes in the UI.
- [#6197](https://github.com/nautobot/nautobot/issues/6197) - Fixed an exception in `core.utils.lookup.get_model_for_view_name` function when rendering certain App object list views.
- [#6203](https://github.com/nautobot/nautobot/issues/6203) - Fixed a performance regression observed when change logging resulted in a large number of ObjectChange records (such as in an SSOT Job).

### Dependencies in v2.3.3

- [#6084](https://github.com/nautobot/nautobot/issues/6084) - Updated `pyuwsgi` to `~2.0.26` and `PyYAML` to `~6.0.2`.

### Housekeeping in v2.3.3

- [#5376](https://github.com/nautobot/nautobot/issues/5376) - Disabled `coverage` during initial test database setup to improve test performance.
- [#6084](https://github.com/nautobot/nautobot/issues/6084) - Updated development dependencies `factory-boy` to `~3.3.1`, `ruff` to `~0.5.7`, and `watchdog` to `~4.0.2`.
- [#6084](https://github.com/nautobot/nautobot/issues/6084) - Updated documentation dependency `mkdocs-material` to `~9.5.33`.
- [#6155](https://github.com/nautobot/nautobot/issues/6155) - Updated the invoke.yml.example dev file to use latest values.
- [#6212](https://github.com/nautobot/nautobot/issues/6212) - Updated documentation dependencies `mkdocs` to `~1.6.1`, `mkdocs-material` to `~9.5.34`, and `mkdocstrings-python` to `~1.10.9`.
- [#6212](https://github.com/nautobot/nautobot/issues/6212) - Updated development dependency `pylint` to `~3.2.7`.

## v2.3.2 (2024-09-03)

### Security in v2.3.2

- [#6182](https://github.com/nautobot/nautobot/issues/6182) - Updated `cryptography` to `43.0.1` to address `GHSA-h4gh-qq45-vh27`. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added in v2.3.2

- [#5180](https://github.com/nautobot/nautobot/issues/5180) - Add filtering Job Results by Scheduled Job.
- [#5591](https://github.com/nautobot/nautobot/issues/5591) - Added `time_zone` field to `ScheduledJob` model.
- [#6120](https://github.com/nautobot/nautobot/issues/6120) - Added Status Field to VRF model.
- [#6129](https://github.com/nautobot/nautobot/issues/6129) - Added collapsible icon rotation to homepage panels.

### Fixed in v2.3.2

- [#5591](https://github.com/nautobot/nautobot/issues/5591) - Corrected several bugs around handling of `ScheduledJob` execution when `settings.TIME_ZONE` is other than "UTC".
- [#5591](https://github.com/nautobot/nautobot/issues/5591) - Added missing `Meta.ordering` definition to `ScheduledJob` model.
- [#6123](https://github.com/nautobot/nautobot/issues/6123) - Fixed cable status coloring for `DeviceModule*Table` rows in dark mode.
- [#6131](https://github.com/nautobot/nautobot/issues/6131) - Fixed a regression in which IP addresses and prefixes created through the `/api/ipam/prefixes/<uuid>/available-ips/` and `/api/ipam/prefixes/<uuid>/available-prefixes/` REST API endpoints could not be assigned custom field data during their creation.
- [#6146](https://github.com/nautobot/nautobot/issues/6146) - Added missing DynamicGroup content to Device Detail View and Software Image File Detail View.
- [#6175](https://github.com/nautobot/nautobot/issues/6175) - Prevented some `AttributeError` exceptions from being raised when an App contains a model that doesn't inherit from `BaseModel`.

### Housekeeping in v2.3.2

- [#5591](https://github.com/nautobot/nautobot/issues/5591) - Added `watchmedo` to `celery_beat` development container.
- [#5591](https://github.com/nautobot/nautobot/issues/5591) - Added `time-machine` as a development environment (test execution) dependency.
- [#6147](https://github.com/nautobot/nautobot/issues/6147) - Fixed some points of non-determinism in the data generated by `nautobot-server generate_test_data`.
- [#6147](https://github.com/nautobot/nautobot/issues/6147) - Added `development/cleanup_factory_dump.py` helper script to aid in identifying other issues with test data.

## v2.3.1 (2024-08-19)

### Added in v2.3.1

- [#5232](https://github.com/nautobot/nautobot/issues/5232) - Added support for groupings to computed fields.
- [#5494](https://github.com/nautobot/nautobot/issues/5494) - Added validation logic to `DeviceForm` `clean()` method to raise a validation error if there is any invalid software image file specified.
- [#5915](https://github.com/nautobot/nautobot/issues/5915) - Enhanced `IPAddress.objects.get_or_create` method to permit specifying a namespace as an alternative to a parent prefix.

### Changed in v2.3.1

- [#5970](https://github.com/nautobot/nautobot/issues/5970) - Removed indentations for PrefixTable in various locations in the UI.

### Fixed in v2.3.1

- [#5494](https://github.com/nautobot/nautobot/issues/5494) - Fixed `Device` model `clean()` validation logic to allow user to specify a software version on a device without specifying any software image files.
- [#6096](https://github.com/nautobot/nautobot/issues/6096) - Updated CloudAccount UI: Set the `secrets_group` form field to be optional.
- [#6097](https://github.com/nautobot/nautobot/issues/6097) - Updated ContactAssociation API: Set the role field to be required.
- [#6116](https://github.com/nautobot/nautobot/issues/6116) - Added handling for an `OperationalError` that might be raised when running `pylint-nautobot` or similar linters that depend on successfully running `nautobot.setup()`.

### Housekeeping in v2.3.1

- [#6107](https://github.com/nautobot/nautobot/issues/6107) - Updated documentation dependency `mkdocstrings-python` to `~1.10.8`.

## v2.3.0 (2024-08-08)

### Security in v2.3.0

- [#6073](https://github.com/nautobot/nautobot/issues/6073) - Updated `Django` to `~4.2.15` due to `CVE-2024-41989`, `CVE-2024-41990`, `CVE-2024-41991`, and `CVE-2024-42005`.

### Added in v2.3.0

- [#5996](https://github.com/nautobot/nautobot/issues/5996) - Added missing `comments` field to DeviceType bulk edit.
- [#5996](https://github.com/nautobot/nautobot/issues/5996) - Added `comments` field to ModuleType.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Added `Cloud Networks` column to `PrefixTable`.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Added `prefixes` filter to `CloudNetworkFilterSet`.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Added `parent__name` and `parent__description` to `CloudNetworkFilterSet` `q` filter.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Added support for querying `GenericRelation` relationships (reverse of `GenericForeignKey`) in GraphQL.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Added support for filtering an object's `associated_contacts` in GraphQL.

### Changed in v2.3.0

- [#6003](https://github.com/nautobot/nautobot/issues/6003) - Changed rendering of `scoped_fields` column in `ObjectMetadataTable`.
- [#6003](https://github.com/nautobot/nautobot/issues/6003) - Changed default ordering of `ObjectMetadata` list views.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Renamed `associated_object_metadatas` GenericRelation to `associated_object_metadata`.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Renamed `object_metadatas` reverse-relations to `object_metadata`.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Changed `CloudNetwork.parent` foreign-key `on_delete` behavior to `PROTECT`.
- [#6070](https://github.com/nautobot/nautobot/issues/6070) - Marked the `Note` model as `is_metadata_associable_model = False`.

### Removed in v2.3.0

- [#6005](https://github.com/nautobot/nautobot/issues/6005) - Removed "delete" and "bulk-delete" functionalities from the ObjectMetadata views.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Removed unneeded `CloudNetworkPrefixAssignmentTable`.

### Fixed in v2.3.0

- [#5967](https://github.com/nautobot/nautobot/issues/5967) - Fixed a regression in the display of custom fields in object-edit forms.
- [#5996](https://github.com/nautobot/nautobot/issues/5996) - Fixed URL typo in module and module type list views.
- [#6003](https://github.com/nautobot/nautobot/issues/6003) - Added missing `blank=True` to `ObjectMetadata.scoped_fields`.
- [#6019](https://github.com/nautobot/nautobot/issues/6019) - Marked the `JobLogEntry` model as invalid for association of `ObjectMetadata`.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Added missing `Config Schema` display to detail view of `CloudResourceType`.
- [#6039](https://github.com/nautobot/nautobot/issues/6039) - Added missing `Description` display to detail view of `CloudService`.
- [#6045](https://github.com/nautobot/nautobot/issues/6045) - Fixed interfaces of Virtual Chassis Master missing other member's interfaces.
- [#6051](https://github.com/nautobot/nautobot/issues/6051) - Fixed improper escaping of saved-view name in success message.
- [#6051](https://github.com/nautobot/nautobot/issues/6051) - Fixed incorrect ordering of items in Tenant detail view.
- [#6051](https://github.com/nautobot/nautobot/issues/6051) - Fixed query parameters for `CloudNetwork.parent` form field.
- [#6056](https://github.com/nautobot/nautobot/issues/6056) - Fixed the order of object deletion by constructing delete success message before the object is deleted.
- [#6064](https://github.com/nautobot/nautobot/issues/6064) - Reverted an undesired change to `IPAddressFilterSet.device` filter.
- [#6064](https://github.com/nautobot/nautobot/issues/6064) - Reverted an undesired change to `ServiceForm.ip_addresses` valid addresses.

### Documentation in v2.3.0

- [#5920](https://github.com/nautobot/nautobot/issues/5920) - Updated documentation for installation under Ubuntu 24.04 LTS, Fedora 40, AlmaLinux 9, and similar distros.
- [#6019](https://github.com/nautobot/nautobot/issues/6019) - Updated the installation documentation to recommend a more secure set of filesystem permissions.
- [#6050](https://github.com/nautobot/nautobot/issues/6050) - Updated model development docs with information about object metadata and dynamic groups features.
- [#6050](https://github.com/nautobot/nautobot/issues/6050) - Added some crosslinks within the DCIM model documentation.
- [#6062](https://github.com/nautobot/nautobot/issues/6062) - Updated Configuration Context docs with additional examples for dictionary of dictionaries.

### Housekeeping in v2.3.0

- [#5962](https://github.com/nautobot/nautobot/issues/5962) - Updated development dependency `ruff` to `~0.5.6`.
- [#5962](https://github.com/nautobot/nautobot/issues/5962) - Updated documentation dependencies: `mkdocs-material` to `~9.5.31`, `mkdocstrings` to `~0.25.2`, and `mkdocstrings-python` to `~1.10.7`.
- [#6003](https://github.com/nautobot/nautobot/issues/6003) - Updated `ObjectMetadataFactory` to produce more realistic `scoped_fields` values.
- [#6014](https://github.com/nautobot/nautobot/issues/6014) - Fixed intermittent `ObjectMetadata` factory failures.
- [#6047](https://github.com/nautobot/nautobot/issues/6047) - Made sure that there is a sufficient amount of `Contact` and `Team` instances exist in the database when testing `contacts` and `teams` filters of an object's filterset.
- [#6055](https://github.com/nautobot/nautobot/issues/6055) - Added migrations check to upstream testing workflow.
- [#6071](https://github.com/nautobot/nautobot/issues/6071) - Fixed incorrect generic-test logic in `FilterTestCase.test_q_filter_valid` for `q` filters containing `iexact` lookups.

## v2.3.0-beta.1 (2024-07-25)

### Security in v2.3.0-beta.1

- [#5889](https://github.com/nautobot/nautobot/issues/5889) - Updated `Django` to `~4.2.14` due to `CVE-2024-38875`, `CVE-2024-39329`, `CVE-2024-39330`, and `CVE-2024-39614`.

### Added in v2.3.0-beta.1

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
- [#5721](https://github.com/nautobot/nautobot/issues/5721) - Added ~~`CloudType`~~ `CloudResourceType` Model, UI, GraphQL and REST API.
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

### Changed in v2.3.0-beta.1

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

### Deprecated in v2.3.0-beta.1

- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Deprecated the properties `DynamicGroup.members_cached`, `DynamicGroup.members_cache_key`, `DynamicGroupMixin.dynamic_groups_cached`, `DynamicGroupMixin.dynamic_groups_list`, and `DynamicGroupMixin.dynamic_groups_list_cached`.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Deprecated the `DynamicGroupMixin` model mixin class. Models supporting Dynamic Groups should use `DynamicGroupsModelMixin` instead.
- [#5870](https://github.com/nautobot/nautobot/issues/5870) - Deprecated the blocks `block export_button` and `block import_button` in `generic/object_list.html`. Apps and templates should migrate to using `block export_list_element` and `block import_list_element` respectively.

### Removed in v2.3.0-beta.1

- [#3749](https://github.com/nautobot/nautobot/issues/3749) - Removed automatic random cleanup of ObjectChange records when processing requests and signals.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Removed `DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT` setting as it is no longer relevant after refactoring the Dynamic Group membership caching implementation.
- [#5786](https://github.com/nautobot/nautobot/issues/5786) - Removed the `StaticGroup` model added in #5472, replacing it with a subtype of the `DynamicGroup` model.

### Fixed in v2.3.0-beta.1

- [#2352](https://github.com/nautobot/nautobot/issues/2352) - Fixed random deadlocks in long-running Jobs resulting from the ObjectChange automatic cleanup signal.
- [#5123](https://github.com/nautobot/nautobot/issues/5123) - Fixed an unhandled `ValueError` when filtering on `vlans` by their UUID rather than their VLAN ID.
- [#5442](https://github.com/nautobot/nautobot/issues/5442) - Replaced overly broad `invalidate_models_cache` signal handler with two more narrowly scoped handlers, preventing the signal handler from being invoked for operations on irrelevant models.
- [#5442](https://github.com/nautobot/nautobot/issues/5442) - Fixed incorrect linkification of JobLogEntry table rows when a record had a `log_object` but no `absolute_url`.
- [#5473](https://github.com/nautobot/nautobot/issues/5473) - Significantly improved performance of Dynamic Group UI views.
- [#5774](https://github.com/nautobot/nautobot/issues/5774) - Fixed the bug that required users and administrators to manage additional permission to be able to use saved views.
- [#5814](https://github.com/nautobot/nautobot/issues/5814) - Fixed style issues with Saved Views and other language code blocks.
- [#5818](https://github.com/nautobot/nautobot/issues/5818) - Fixed broken table configure buttons in device and module component tabs.
- [#5842](https://github.com/nautobot/nautobot/issues/5842) - Fixed missing classes when importing `*` from `nautobot.ipam.models`.
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

### Dependencies in v2.3.0-beta.1

- [#1758](https://github.com/nautobot/nautobot/issues/1758) - Updated `materialdesignicons` to version 7.4.47.
- [#4616](https://github.com/nautobot/nautobot/issues/4616) - Updated `django-taggit` to `~5.0.0`.
- [#4616](https://github.com/nautobot/nautobot/issues/4616) - Updated `netaddr` to `~1.3.0`.
- [#5160](https://github.com/nautobot/nautobot/issues/5160) - Updated `Django` to version `~4.2.13`.
- [#5160](https://github.com/nautobot/nautobot/issues/5160) - Updated `django-db-file-storage` to version `~0.5.6.1`.
- [#5160](https://github.com/nautobot/nautobot/issues/5160) - Updated `django-timezone-field` to version `~6.1.0`.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Updated Docker build and CI to use `poetry` `1.8.2`.
- [#5429](https://github.com/nautobot/nautobot/issues/5429) - Removed development dependency on `mkdocs-include-markdown-plugin` as it's no longer used in Nautobot's documentation.
- [#5518](https://github.com/nautobot/nautobot/issues/5518) - Updated `drf-spectacular` to version `0.27.2`.
- [#5687](https://github.com/nautobot/nautobot/issues/5687) - Added [`django-structlog`](https://django-structlog.readthedocs.io/en/latest/) dependency.
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

### Documentation in v2.3.0-beta.1

- [#5699](https://github.com/nautobot/nautobot/issues/5699) - Fixed a number of broken links within the documentation.
- [#5895](https://github.com/nautobot/nautobot/issues/5895) - Added missing model documentation for `CloudNetwork`, `CloudNetworkPrefixAssignment`, `CloudService` and ~~`CloudType`~~ `CloudResourceType`.
- [#5934](https://github.com/nautobot/nautobot/issues/5934) - Add Cloud Model Example and Entity Diagram.

### Housekeeping in v2.3.0-beta.1

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
