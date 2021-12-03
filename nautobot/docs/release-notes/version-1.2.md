# Nautobot v1.2

This document describes all new features and changes in Nautobot 1.2.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Admin Configuration UI ([#370](https://github.com/nautobot/nautobot/issues/370))

The Nautobot Admin UI now includes a "Configuration" page that can be used to dynamically customize a number of [optional settings](../configuration/optional-settings.md#administratively-configurable-settings) as an alternative to editing `nautobot_config.py` and restarting the Nautobot processes.

If upgrading from a previous Nautobot version where these settings were defined in your `nautobot_config.py`, you must remove those definitions in order to use this feature, as explicit configuration in `nautobot_config.py` takes precedence over values configured in the Admin UI.

#### Common Base Template for Object Detail Views ([#479](https://github.com/nautobot/nautobot/issues/479), [#585](https://github.com/nautobot/nautobot/issues/585))

All "object detail" views (pages displaying details of a single Nautobot record) now inherit from a common base template, providing improved UI consistency, reducing the amount of boilerplate code needed to create a new detail view, and fixing a number of bugs in various views. Plugin developers are encouraged to make use of this new template (`generic/object_detail.html`) to take advantage of these improvements.

Views based on this template now include a new "Advanced" tab - currently this tab includes the UUID and slug (if any) of the object being viewed, but may be extended in the future to include additional information not relevant to the basic object detail view.

#### Custom Fields are now User Configurable ([#229](https://github.com/nautobot/nautobot/issues/229))

Creation and management of Custom Field definitions can now be performed by any user with appropriate permissions. (Previously, only admin users were able to manage Custom Fields.)

#### Custom Field Webhooks ([#519](https://github.com/nautobot/nautobot/issues/519))

Webhooks can now be triggered when creating/updating/deleting `CustomField` and `CustomFieldChoice` definition records.

#### Database Ready Signal ([#13](https://github.com/nautobot/nautobot/issues/13))

After running `nautobot-server migrate` or `nautobot-server post_upgrade`, Nautobot now emits a custom signal, `nautobot_database_ready`. This signal is designed for plugins to connect to in order to perform automatic database population (such as defining custom fields, relationships, webhooks, etc.) at install/upgrade time. For more details, refer to [the plugin development documentation](../plugins/development.md#populating-extensibility-features).

#### GraphQL Filters at All Levels ([#248](https://github.com/nautobot/nautobot/issues/248))

The GraphQL API now supports query filter parameters at any level of a query. For example:

```graphql
query {
  sites(name: "ams") {
    devices(role: "edge") {
      name
      interfaces(type: "virtual") {
        name
      }
    }
  }
}
```

#### GraphQL Query Optimizations ([#171](https://github.com/nautobot/nautobot/issues/171))

Complex GraphQL queries have been greatly optimized thanks to integration of 
[`graphene-django-optimizer`](https://github.com/tfoxy/graphene-django-optimizer) into Nautobot! 

In our internal testing and benchmarking the number of SQL queries generated per GraphQL query have been drastically reduced, resulting in much quicker response times and less strain on the database.

For in depth details on our benchmarks, please see the [comment thread on the issue](https://github.com/nautobot/nautobot/issues/171#issuecomment-907483759).

#### Installed Plugins List and Detail Views, Plugin Config and Home Views ([#935](https://github.com/nautobot/nautobot/pull/935))

The `Plugins` menu now includes an "Installed Plugins" menu item which provides a list view of information about all installed and enabled plugins, similar to a formerly administrator-only view.

Additionally, when viewing this list, each plugin can now be clicked on for a detail view, which provides an in-depth look at the capabilities of the plugin, including whether it makes use of each or all of the various Nautobot features available to be used by plugins.

Additionally, plugins now have the option of registering specific "home" and/or "configuration" views, which will be linked and accessible directly from the installed-plugins list and detail views.

Please refer to the [plugin development documentation](../plugins/development.md) for more details about this functionality.

#### Job Approval ([#125](https://github.com/nautobot/nautobot/issues/125))

Jobs can now be optionally defined as `approval_required = True`, in which case the Job will not be executed immediately upon submission, but will instead be placed into an approval queue; any user *other than the submitter* can approve or deny a queued Job, at which point it will then be executed as normal.

#### Job Scheduling ([#374](https://github.com/nautobot/nautobot/issues/374))

Jobs can now be scheduled for execution at a future date and time (such as during a planned maintenance window), and can also be scheduled for repeated execution on an hourly, daily, or weekly recurring cadence.

!!! note
    Execution of scheduled jobs is dependent on [Celery Beat](https://docs.celeryproject.org/en/stable/userguide/periodic-tasks.html); enablement of this system service is a new requirement in Nautobot 1.2.

Please see the documentation on enabling the [Celery Beat scheduler service](../installation/services.md#celery-beat-scheduler) to get started!

#### Organizational Branding ([#859](https://github.com/nautobot/nautobot/issues/859))

Organizations may provide custom branding assets to change the logo, icons, and footer URLs to help Nautobot fit within their environments and user communities. Please see the [configuration documenation](../configuration/optional-settings.md#BRANDING_FILEPATHS) for details on how to specify the location and usage of custom branding assets.

#### Plugin Banners ([#534](https://github.com/nautobot/nautobot/issues/534))

Each plugin is now able to optionally inject a custom banner into any of the Nautobot core views.

Please refer to the [plugin development documentation](../plugins/development.md) for more details about this functionality.

#### Same-Type and Symmetric Relationships ([#157](https://github.com/nautobot/nautobot/issues/157))

The [Relationships](../models/extras/relationship.md) feature has been extended in two ways:

1. Relationships between the same object type (e.g. device-to-device) are now permitted and supported.
2. For same-object-type relationships specifically, *symmetric* (peer-to-peer rather than source-to-destination) relationships are now an option.

For more details, refer to the [Relationships](../models/extras/relationship.md) documentation.

#### Secrets Integration ([#541](https://github.com/nautobot/nautobot/issues/541))

Nautobot can now read secret values (such as device or Git repository access credentials) on demand from a variety of external sources, including environment variables and text files, and extensible via plugins to support additional secrets providers such as Hashicorp Vault and AWS Secrets Manager. Both the [NAPALM device integration](../additional-features/napalm.md) and the [Git repository integration](../models/extras/gitrepository.md) can now make use of these secrets, and plugins and jobs can do so as well.

For more details, please refer to the [Secrets](../core-functionality/secrets.md) documentation.

#### Software-Defined Home Page ([#674](https://github.com/nautobot/nautobot/pull/674), [#716](https://github.com/nautobot/nautobot/pull/716))

Nautobot core applications and plugins can now both define panels, groups, and items to populate the Nautobot home page. The home page now dynamically reflows to accommodate available content. Plugin developers can add to existing panels or groups or define entirely new panels as needed. For more details, see [Populating the Home Page](../development/homepage.md).

### Changed

#### Admin Site Changes ([#900](https://github.com/nautobot/nautobot/pull/900))

The Admin sub-site within Nautobot (`/admin/` and its child pages) has been revamped in appearance and functionality. It has been re-skinned to resemble the rest of the Nautobot UI, and has been slimmed down to only include those models and features that are still exclusive to admin users, such as user/group/permission management.

#### Slug fields are now Optional in CSV import, REST API and ORM ([#493](https://github.com/nautobot/nautobot/issues/493))

All models that have `slug` fields now use `AutoSlugField` from the `django-extensions` package. This means that when creating a record via the REST API, CSV import, or direct ORM Python calls, the `slug` field is now fully optional; if unspecified, it will be automatically assigned a unique value, just as how a `slug` is auto-populated in the UI when creating a new record.

Just as with the UI, the `slug` can still always be explicitly set if desired.

## v1.2.0b2 (2021-??-??)

### Added

### Changed

### Fixed

- [#1078](https://github.com/nautobot/nautobot/issues/1078) - Fixed missing support for filtering several models by their custom fields and/or created/updated stamps.
- [#1093](https://github.com/nautobot/nautobot/pull/1093) - Improved REST API performance by adding caching of serializer "opt-in fields".
- [#1112](https://github.com/nautobot/nautobot/issues/1112) - Fixed broken single-object GraphQL query endpoints.
- [#1116](https://github.com/nautobot/nautobot/issues/1116) - Fixed UnboundLocalError when using device NAPALM integration
- [#1121](https://github.com/nautobot/nautobot/pull/1121) - Fixed issue with handling of relationships referencing no-longer-present model classes.

## v1.2.0b1 (2021-11-19)

### Added

- [#13](https://github.com/nautobot/nautobot/issues/13) - Added `nautobot_database_ready` signal
- [#125](https://github.com/nautobot/nautobot/issues/125) - Added support for `approval_required = True` on Jobs
- [#157](https://github.com/nautobot/nautobot/issues/157) - Added support for same-object-type and symmetric Relationships
- [#171](https://github.com/nautobot/nautobot/issues/171) - GraphQL queries have been greatly optimized by integration with `graphene-django-optimizer`
- [#229](https://github.com/nautobot/nautobot/issues/229) - Added user-facing views for Custom Field management
- [#248](https://github.com/nautobot/nautobot/issues/248) - Added support for filtering GraphQL queries at all levels
- [#370](https://github.com/nautobot/nautobot/issues/370) - Added support for server configuration via the Admin UI.
- [#374](https://github.com/nautobot/nautobot/issues/374) - Added ability to schedule Jobs for future and/or recurring execution
- [#478](https://github.com/nautobot/nautobot/issues/478) - CustomFieldChoice model now supports GraphQL.
- [#479](https://github.com/nautobot/nautobot/issues/479) - Added shared generic template for all object detail views
- [#519](https://github.com/nautobot/nautobot/issues/519) - Added webhook support for `CustomField` and `CustomFieldChoice` models.
- [#534](https://github.com/nautobot/nautobot/issues/534) - Added ability to inject a banner from a plugin
- [#541](https://github.com/nautobot/nautobot/issues/541) - Added Secrets integration
- [#580](https://github.com/nautobot/nautobot/issues/580) - Added ability for plugins to register "home" and "configuration" views.
- [#585](https://github.com/nautobot/nautobot/issues/585) - Added "Advanced" tab to object detail views including UUID and slug information.
- [#642](https://github.com/nautobot/nautobot/issues/642) - Added documentation of the `GIT_SSL_NO_VERIFY` environment variable for using self-signed Git repositories
- [#674](https://github.com/nautobot/nautobot/pull/674) - Plugins can now add items to the Nautobot home page
- [#716](https://github.com/nautobot/nautobot/pull/716) - Nautobot home page content is now dynamically populated based on installed apps and plugins.
- [#866](https://github.com/nautobot/nautobot/pull/859) - Added support for organizational custom branding for the logo and icons
- [#866](https://github.com/nautobot/nautobot/pull/866) - Added documentation for job scheduling and approvals
- [#879](https://github.com/nautobot/nautobot/pull/879) - Added API testing for job scheduling and approvals
- [#908](https://github.com/nautobot/nautobot/pull/908) - Added UI testing for job scheduling and approvals
- [#935](https://github.com/nautobot/nautobot/pull/935) - Added Installed Plugins list view and detail view
- [#937](https://github.com/nautobot/nautobot/issues/937) - Added bulk-delete option for scheduled jobs
- [#938](https://github.com/nautobot/nautobot/issues/938) - Added titles to job approval UI buttons
- [#953](https://github.com/nautobot/nautobot/pull/953) - Added option to use MySQL in docker-compose development environment

### Changed

- [#222](https://github.com/nautobot/nautobot/issues/222) - Changed wildcard imports to explicitly enumerated imports and enabled associated Flake8 linter rules.
- [#472](https://github.com/nautobot/nautobot/issues/472) - `JobResult` lists now show the associated Job's name (if available) instead of the Job's `class_path`.
- [#493](https://github.com/nautobot/nautobot/issues/493) - All `slug` fields are now optional when creating records via the REST API, ORM, or CSV import. Slugs will be automatically assigned if unspecified.
- [#877](https://github.com/nautobot/nautobot/pull/877) - Hid unused "Social Auth" section from Django admin page.
- [#900](https://github.com/nautobot/nautobot/pull/900) - Admin site has been revised and re-skinned to more closely match the core Nautobot UI.

### Fixed

- [#852](https://github.com/nautobot/nautobot/issues/852) - Fixed missing "Change Log" tab on certain object detail views
- [#853](https://github.com/nautobot/nautobot/issues/853) - Fixed `AttributeError` on certain object detail views
- [#891](https://github.com/nautobot/nautobot/issues/891) - Fixed custom field select/multiselect not handled by new UI and added integration tests
- [#966](https://github.com/nautobot/nautobot/issues/966) - Fixed missing "Advanced" tab on Device detail views
- [#1060](https://github.com/nautobot/nautobot/issues/1060) - Fixed documentation incorrectly indicating that the Admin UI was the only way to manage custom field definitions.

### Security

- [#1017](https://github.com/nautobot/nautobot/issues/1017) - Custom field descriptions no longer potentially render as arbitrary HTML in object edit forms; Markdown format is now supported as a less dangerous option.
