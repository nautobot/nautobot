<!-- markdownlint-disable MD024 -->

# Nautobot v1.5

This document describes all new features and changes in Nautobot 1.5.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

### Changed

### Fixed

### Removed

## v1.5.0a1 (2022-MM-DD)

### Added

- [#899](https://github.com/nautobot/nautobot/issues/899) - Added support for grouping of Custom Fields.
- [#1468](https://github.com/nautobot/nautobot/issues/1468) - Added relationship columns to ObjectListTableView and disabled sorting.
- [#2063](https://github.com/nautobot/nautobot/issues/2063) - Added documentation and initial support for custom celery queues.
- [#2281](https://github.com/nautobot/nautobot/issues/2281) - Added test database fixtures for Tag and Status models.

### Changed

- [#1983](https://github.com/nautobot/nautobot/issues/1983) - Updated `django-taggit` dependency to 3.0.0.
- [#2170](https://github.com/nautobot/nautobot/pull/2170) - Updated `django-constance` dependency to 2.9.1; updated `Jinja2` dependency to 3.1.2; updated `black` development dependency to 22.8.0.
- [#2320](https://github.com/nautobot/nautobot/pull/2320) - Removed PKs from Tag test database fixture.

### Fixed

- [#192](https://github.com/nautobot/nautobot/issues/192) - Eliminated Unit Test noisy output.
- [#2416](https://github.com/nautobot/nautobot/issues/2416) - Return "—" instead of "None" when relationship column is empty.
