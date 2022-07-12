<!-- markdownlint-disable MD024 -->
# Nautobot v1.4

This document describes all new features and changes in Nautobot 1.4.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Dark Mode UI ([#729](https://github.com/nautobot/nautobot/issues/729))

Nautobot's UI now supports dark mode, both explicitly and via browser preference selection.

The "Theme" link in the footer provides a modal popup to select the preferred theme. This preference is saved per browser via `localStorage`.

#### Location Data Model ([#1052](https://github.com/nautobot/nautobot/issues/1052))

To locate network information more precisely than a Site defines, you can now define a hierarchy of Location Types (for example, `Building` ← `Floor` ← `Room`) and then create Locations corresponding to these types within each Site. Data objects such as devices, prefixes, VLAN groups, etc. can thus be mapped or assigned to Location representing a specific building, wing, floor, room, etc. as appropriate to your needs.

!!! info
    At present, Locations fill the conceptual space between the more abstract Region and Site models and the more concrete Rack Group model. In a future Nautobot release, some or all of these other models may be collapsed into Locations. That is to say, in the future you might not deal with Regions and Sites as distinct models, but instead your Location Type hierarchy might include these higher-level categories, becoming something like Country ← City ← Site ← Building ← Floor ← Room.

#### Parent Interfaces and Bridge Interfaces ([#1455](https://github.com/nautobot/nautobot/issues/1455))

Interface and VMInterface models now have `parent_interface` and `bridge` keys. An interface of type `Virtual` can now associate to a parent physical interface on the same device, virtual chassis, or virtual machine, and an interface of any type can specify another interface as its associated bridge interface. (A new `Bridge` interface type has also been added, but the `bridge` interface property is not restricted to interfaces of this type.)

#### Rackview UI - Add Option to Truncate Device Name ([#1119](https://github.com/nautobot/nautobot/issues/1119))

Users can now toggle device full name and truncated name in the rack elevation view. The truncating function is customizable in `nautobot_config.py` via defining `UI_RACK_VIEW_TRUNCATE_FUNCTION`. Default behavior is to split on `.` and return the first item in the list.

"Save SVG" link presents the same view as what is currently displayed on screen

Current preferred toggle state is preserved across tabs (requires refresh) and persists in-browser until local storage is cleared. This presents a consistent behavior when browsing between multiple racks.

#### Status Field on Interface, VMInterface Models ([#984](https://github.com/nautobot/nautobot/issues/984))

Interface and VMInterface models now support a status. Default statuses that are available to be set are: Active, Planned, Maintenance, Failed, and Decommissioned. During migration all existing interfaces will be set to the status of "Active".

A new version of the `/dcim/interfaces/*` REST API endpoints have been implemented. By default this endpoint continues to demonstrate the pre-1.4 behavior unless the REST API client explicitly requests API version=1.4. If you continue to use the pre-1.4 API endpoints, status is defaulted to "Active".

Visit the documentation on [REST API versioning](../rest-api/overview/#versioning) for more information on using the versioned APIs.

#### Object Detail Tabs ([#1000](https://github.com/nautobot/nautobot/issues/1000))

A plugin may now define extra tabs which will be appended to the object view's list of tabs.

You can refer to the [plugin development guide](../plugins/development.md##adding-extra-tabs) on how to add tabs to existing object detail views.

#### Improved Filter Coverage for DCIM models ([#1729](https://github.com/nautobot/nautobot/issues/1729))

The DCIM FilterSets have been updated with 137 new filters, including hybrid filters that support filtering on both `pk` and `slug` (or `pk` and `name` where `slug` is not available). A new filter class `NaturalKeyOrPKMultipleChoiceFilter` was added to `nautobot.utilities.filters` to support filtering on multiple fields of a related object. See the [Best Practices](../development/best-practices/#mapping-model-fields-to-filters) documentation for more information.

### Changed

#### Strict Filter Validation by Default ([#1736](https://github.com/nautobot/nautobot/issues/1736))

Filtering of object lists in the UI and in the REST API will now report an error if an unknown or unrecognized filter parameter is specified. _This is a behavior change from previous Nautobot releases, in which unknown filter parameters would be silently discarded and ignored._

A new configuration setting, [`STRICT_FILTERING`](../configuration/optional-settings.md#strict_filtering) has been added. It defaults to `True`, enabling strict validation of filter parameters, but can be set to `False` to disable this validation.

!!! warning
    Setting `STRICT_FILTERING` to `False` can result in unexpected filtering results in the case of user error, for example a request to `/api/dcim/devices/?has_primry_ip=false` (note the typo `primry`) will result in a list of all devices, rather than the intended list of only devices that lack a primary IP address. In the case of Jobs or external automation making use of such a filter, this could have wide-ranging consequences.

#### Moved Registry Template Context ([#1945](https://github.com/nautobot/nautobot/issues/1945))

The `settings_and_registry` default context processor was changed to purely `settings` - the (large) Nautobot application registry dictionary is no longer provided as part of the render context for all templates by default. Added a new `registry` template tag that can be invoked by specific templates to provide this variable where needed.

## v1.4.0a2 (2022-07-11)

!!! attention
    `next` and `develop` introduced conflicting migration numbers during the release cycle. This necessitates reordering the migration in `next`. If you installed `v1.4.0a1`, you will need to roll back a migration before upgrading/installing `v1.4.0a2` and newer. If you have not installed `v1.4.0a` this will not be an issue.

    Before upgrading, run: `nautobot-server migrate extras 0033_add__optimized_indexing`. This will revert the reordered migration `0034_configcontextschema__remove_name_unique__create_constraint_unique_name_owner`, which is now number `0035`.

    Perform the Nautobot upgrade as usual and proceed with post-installation migration.

    No data loss is expected as the reordered migration only modified indexing on existing fields.

### Added

- [#1000](https://github.com/nautobot/nautobot/issues/1000) - Object detail views can now have extra UI tabs which are defined by a plugin.
- [#1052](https://github.com/nautobot/nautobot/issues/1052) - Initial prototype implementation of Location data model
- [#1318](https://github.com/nautobot/nautobot/issues/1318) - Added `nautobot.extras.forms.NautobotBulkEditForm` base class. All bulk-edit forms for models that support both custom fields and relationships now inherit from this class.
- [#1466](https://github.com/nautobot/nautobot/issues/1466) - Plugins can now override views.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add new filter class `NaturalKeyOrPKMultipleChoiceFilter` to `nautobot.utilities.filters`.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add 137 new filters to `nautobot.dcim.filters` FilterSets.
- [#1729](https://github.com/nautobot/nautobot/issues/1729) - Add `cable_terminations` to the `model_features` registry.
- [#1893](https://github.com/nautobot/nautobot/issues/1893) - Added an object detail view for Relationships.
- [#1949](https://github.com/nautobot/nautobot/issues/1949) - Added TestCaseMixin for Helper Functions across all test case bases.

### Changed

- [#1908](https://github.com/nautobot/nautobot/pull/1908) - Update dependency Markdown to ~3.3.7
- [#1909](https://github.com/nautobot/nautobot/pull/1909) - Update dependency MarkupSafe to ~2.1.1
- [#1912](https://github.com/nautobot/nautobot/pull/1912) - Update dependency celery to ~5.2.7
- [#1913](https://github.com/nautobot/nautobot/pull/1913) - Update dependency django-jinja to ~2.10.2
- [#1915](https://github.com/nautobot/nautobot/pull/1915) - Update dependency invoke to ~1.7.1
- [#1917](https://github.com/nautobot/nautobot/pull/1917) - Update dependency svgwrite to ~1.4.2
- [#1919](https://github.com/nautobot/nautobot/pull/1919) - Update dependency Pillow to ~9.1.1
- [#1920](https://github.com/nautobot/nautobot/pull/1920) - Update dependency coverage to ~6.4.1
- [#1921](https://github.com/nautobot/nautobot/pull/1921) - Update dependency django-auth-ldap to ~4.1.0
- [#1924](https://github.com/nautobot/nautobot/pull/1924) - Update dependency django-cors-headers to ~3.13.0
- [#1925](https://github.com/nautobot/nautobot/pull/1925) - Update dependency django-debug-toolbar to ~3.4.0
- [#1928](https://github.com/nautobot/nautobot/pull/1928) - Update dependency napalm to ~3.4.1
- [#1929](https://github.com/nautobot/nautobot/pull/1929) - Update dependency selenium to ~4.2.0
- [#1945](https://github.com/nautobot/nautobot/issues/1945) - Change the `settings_and_registry` default context processor to purely `settings`, moving registry dictionary to be accessible via `registry` template tag.

### Fixed

- [#1898](https://github.com/nautobot/nautobot/issues/1898) - Browsable API is now properly styled as the rest of the app.

### Removed

- [#1462](https://github.com/nautobot/nautobot/issues/1462) - Removed job source tab from Job and Job Result view.
- [#2002](https://github.com/nautobot/nautobot/issues/2002) - Removed rqworker container from default Docker development environment.

## v1.4.0a1 (2022-06-13)

### Added

- [#729](https://github.com/nautobot/nautobot/issues/729) - Added UI dark mode.
- [#984](https://github.com/nautobot/nautobot/issues/984) - Added status field to Interface, VMInterface models.
- [#1119](https://github.com/nautobot/nautobot/issues/1119) - Added truncated device name functionality to Rackview UI.
- [#1455](https://github.com/nautobot/nautobot/issues/1455) - Added `parent_interface` and `bridge` fields to Interface and VMInterface models.

### Changed

- [#1736](https://github.com/nautobot/nautobot/issues/1736) - `STRICT_FILTERING` setting is added and enabled by default.
- [#1793](https://github.com/nautobot/nautobot/pull/1793) - Added index notes to fields from analysis, relaxed ConfigContextSchema constraint (unique on name, owner_content_type, owner_object_id instead of just name).

### Fixed

- [#1815](https://github.com/nautobot/nautobot/issues/1815) - Fix theme link style in footer.
- [#1831](https://github.com/nautobot/nautobot/issues/1831) - Fixed missing `parent_interface` and `bridge` from 1.4 serializer of Interfaces.
