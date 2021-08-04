# Nautobot v1.2

This document describes all new features and changes in Nautobot 1.2.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Common Base Template for Object Detail Views ([#479](https://github.com/nautobot/nautobot/issues/479))

All "object detail" views (pages displaying details of a single Nautobot record) now inherit from a common base template, providing improved UI consistency, reducing the amount of boilerplate code needed to create a new detail view, and fixing a number of bugs in various views. Plugin developers are encouraged to make use of this new template (`generic/object_detail.html`) to take advantage of these improvements.

#### Plugin Banners ([#534](https://github.com/nautobot/nautobot/issues/534))

Each plugin is now able to inject a custom banner into any of the Nautobot core views.

#### Software-Defined Home Page ([#674](https://github.com/nautobot/nautobot/pull/674), [#716](https://github.com/nautobot/nautobot/pull/716))

Nautobot core applications and plugins can now both define panels, groups, and items to populate the Nautobot home page. The home page now dynamically reflows to accommodate available content. Plugin developers can add to existing panels or groups or define entirely new panels as needed. For more details, see [Populating the Home Page](../development/homepage.md).


## v1.2.0b1 (2021-??-??)

### Added

- [#479](https://github.com/nautobot/nautobot/issues/479) - Added shared generic template for all object detail views
- [#534](https://github.com/nautobot/nautobot/issues/534) - Added ability to inject a banner from a plugin
- [#674](https://github.com/nautobot/nautobot/pull/674) - Plugins can now add items to the Nautobot home page
- [#716](https://github.com/nautobot/nautobot/pull/716) - Nautobot home page content is now dynamically populated based on installed apps and plugins. 
- 
