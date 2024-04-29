<!-- markdownlint-disable MD024 -->

# Nautobot v2.3

This document describes all new features and changes in Nautobot 2.3.

## Release Overview

### Added

#### Added an Optional `role` field to Interface and VMInterface models ([#4406](https://github.com/nautobot/nautobot/issues/4406))

Added an optional `role` field to Interface and VMInterface models to track common interface configurations. Now the users can create [Role](../user-guide/platform-functionality/role.md) instances that can be assigned to [interfaces](../user-guide/core-data-model/dcim/interface.md) and [vminterfaces](../user-guide/core-data-model/virtualization/vminterface.md).

### Changed

#### Log Cleanup as System Job ([#3749](https://github.com/nautobot/nautobot/issues/3749))

Cleanup of the change log (deletion of `ObjectChange` records older than a given cutoff) is now handled by the new `LogsCleanup` system Job, rather than occurring at random as a side effect of new change log records being created. Admins desiring automatic cleanup are encouraged to schedule this job to run at an appropriate interval suitable to your deployment's needs.

!!! info
    Setting [`CHANGELOG_RETENTION`](../user-guide/administration/configuration/optional-settings.md#changelog_retention) in your Nautobot configuration by itself no longer directly results in periodic cleanup of `ObjectChange` records. You must run (or schedule to periodically run) the `LogsCleanup` Job for this to occur.

As an additional enhancement, the `LogsCleanup` Job can also be used to cleanup `JobResult` records if desired as well.

<!-- towncrier release notes start -->