# Nautobot v1.3

This document describes all new features and changes in Nautobot 1.3.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

### Changed

### Fixed

### Removed

## v1.3.0a1 (2022-??-??)

### Added

- [#803](https://github.com/nautobot/nautobot/issues/803) - There is now a *render_boolean* template filter in helpers, which renders computed boolean values as HTML in a consistent manner.
- [#863](https://github.com/nautobot/nautobot/issues/863) - Added the ability to hide a job in the UI by setting `hidden = True` in the Job's inner `Meta` class
- [#881](https://github.com/nautobot/nautobot/issues/881) - Improved the UX of the main Jobs by adding accordion style interface that can collapse/expand jobs provided by each module

### Changed

- [#591](https://github.com/nautobot/nautobot/issues/591) - All uses of type() are now refactored to use isinstance() where applicable.
- [#880](https://github.com/nautobot/nautobot/issues/880) - Jobs menu items now form their own top-level menu instead of a sub-section under the Extensibility menu.
- [#909](https://github.com/nautobot/nautobot/issues/909) - Device, InventoryItem, and Rack serial numbers can now be up to 255 characters in length.
- [#916](https://github.com/nautobot/nautobot/issues/916) - A Job.Meta.description can now contain markdown-formatted multi-line text.
- [#1107](https://github.com/nautobot/nautobot/issues/1107) - Circuit Provider account numbers can now be up to 100 characters in length.

### Fixed

### Removed
