<!-- markdownlint-disable MD024 -->

# Nautobot v1.5

This document describes all new features and changes in Nautobot 1.5.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

### Changed

#### Database Query Caching is now Disabled by Default

In prior versions of Nautobot, database query caching using the [`django-cacheops`](https://github.com/Suor/django-cacheops) application (aka Cacheops) was enabled by default. This is determined by the default value of the [`CACHEOPS_ENABLED`](../configuration/optional-settings.md#cacheops_enabled) setting being set to `True`.

Through much trial and error we ultimately decided that this feature is more trouble than it is worth and we have begun to put more emphasis on improving performance of complex database queries over continuing to rely upon the various benefits and pitfalls of utilizing Cacheops.

As a result, the value of this setting now defaults to `False`, disabling database query caching entirely for new deployments. Cacheops will be removed entirely in a future release.

!!! important
    Users with existing `nautobot_config.py` files generated from earlier versions of Nautobot will still have `CACHEOPS_ENABLED = True` unless they modify or regenerate their configuration. If users no longer desire caching, please be sure to explicitly toggle the value of this setting to `False` and restart your Nautobot services.

### Fixed

### Removed

<!-- towncrier release notes start -->
