<!-- markdownlint-disable MD024 -->
# Nautobot v1.4

This document describes all new features and changes in Nautobot 1.4.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Status Field on Interface, VMInterface Models ([#984](https://github.com/nautobot/nautobot/issues/984))

Interface and VMInterface models now support a status. Default statuses that are available to be set are: Active, Planned, Maintenance, Failed, and Decommissioned. During migration all existing interfaces will be set to the status of "Active".

A new version of the `/dcim/interfaces/*` REST API endpoints have been implemented. By default this endpoint continues to demonstrate the pre-1.4 behavior unless the REST API client explicitly requests API version=1.4. If you continue to use the pre-1.4 API endpoints, status is defaulted to "Active". 

Visit the documentation on [REST API versioning](../rest-api/overview/#versioning) for more information on using the versioned APIs.

### Changed

### Fixed

### Removed

## v1.4.0a1 (2022-MM-DD)

### Added

- [#984](https://github.com/nautobot/nautobot/issues/984) - Added status field to Interface, VMInterface models.

### Changed

### Fixed

### Removed
