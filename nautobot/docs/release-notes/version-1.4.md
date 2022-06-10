<!-- markdownlint-disable MD024 -->
# Nautobot v1.4

This document describes all new features and changes in Nautobot 1.4.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Dark Mode UI ([#729](https://github.com/nautobot/nautobot/issues/729))

Nautobot's UI now supports dark mode, both explicitly and via browser preference selection.

The "Theme" link in the footer provides a modal popup to select the preferred theme. This preference is saved per browser via `localStorage`.

#### Parent Interfaces and Bridge Interfaces ([#1455](https://github.com/nautobot/nautobot/issues/1455))

Interface and VMInterface models now have `parent_interface` and `bridge` keys. An interface of type `Virtual` can now associate to a parent physical interface on the same device, virtual chassis, or virtual machine, and an interface of any type can specify another interface as its associated bridge interface. (A new `Bridge` interface type has also been added, but the `bridge` interface property is not restricted to interfaces of this type.)

#### Status Field on Interface, VMInterface Models ([#984](https://github.com/nautobot/nautobot/issues/984))

Interface and VMInterface models now support a status. Default statuses that are available to be set are: Active, Planned, Maintenance, Failed, and Decommissioned. During migration all existing interfaces will be set to the status of "Active".

A new version of the `/dcim/interfaces/*` REST API endpoints have been implemented. By default this endpoint continues to demonstrate the pre-1.4 behavior unless the REST API client explicitly requests API version=1.4. If you continue to use the pre-1.4 API endpoints, status is defaulted to "Active".

Visit the documentation on [REST API versioning](../rest-api/overview/#versioning) for more information on using the versioned APIs.

### Changed

#### Strict Filter Validation by Default ([#1736](https://github.com/nautobot/nautobot/issues/1736))

Filtering of object lists in the UI and in the REST API will now report an error if an unknown or unrecognized filter parameter is specified. _This is a behavior change from previous Nautobot releases, in which unknown filter parameters would be silently discarded and ignored._

A new configuration setting, [`STRICT_FILTERING`](../configuration/optional-settings.md#strict_filtering) has been added. It defaults to `True`, enabling strict validation of filter parameters, but can be set to `False` to disable this validation.

!!! warning
    Setting `STRICT_FILTERING` to `False` can result in unexpected filtering results in the case of user error, for example a request to `/api/dcim/devices/?has_primry_ip=false` (note the typo `primry`) will result in a list of all devices, rather than the intended list of only devices that lack a primary IP address. In the case of Jobs or external automation making use of such a filter, this could have wide-ranging consequences.

### Fixed

### Removed

## v1.4.0a1 (2022-MM-DD)

### Added

- [#729](https://github.com/nautobot/nautobot/issues/729) - Added UI dark mode.
- [#984](https://github.com/nautobot/nautobot/issues/984) - Added status field to Interface, VMInterface models.
- [#1455](https://github.com/nautobot/nautobot/issues/1455) - Added `parent_interface` and `bridge` fields to Interface and VMInterface models.

### Changed

- [#1736](https://github.com/nautobot/nautobot/issues/1736) - `STRICT_FILTERING` setting is added and enabled by default.
- [#1793](https://github.com/nautobot/nautobot/pull/1793) - Added index notes to fields from analysis, relaxed ConfigContextSchema constraint (unique on name, owner_content_type, owner_object_id instead of just name).

### Fixed

- [#1815](https://github.com/nautobot/nautobot/issues/1815) - Fix theme link style in footer.
- [#1831](https://github.com/nautobot/nautobot/issues/1831) - Fixed missing `parent_interface` and `bridge` from 1.4 serializer of Interfaces.

### Removed
