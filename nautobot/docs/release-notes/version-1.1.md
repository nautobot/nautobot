# Nautobot v1.1

This document describes all new features and changes in Nautobot 1.1

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Computed Fields ([#4](https://github.com/nautobot/nautobot/issues/4))

[Computed fields](../additional-features/computed-fields.md) offers users the ability to create read-only custom fields using existing data already stored in the database. Users define Jinja2 templates that populate the value of these fields. Computed fields are available on all data models that currently support custom fields.

#### Config Context JSON Schemas ([#274](https://github.com/nautobot/nautobot/issues/274))

While config contexts allow for arbitrary data structures to be stored within Nautobot, at scale it is desirable to apply validation constraints to that data to ensure its consistency and to avoid data entry errors. To service this need, Nautobot supports optionally backing config contexts with [JSON Schemas](https://json-schema.org/) for validation. These schema are managed via the config context schema model and are optionally linked to config context instances, in addition to devices and virtual machines for the purpose of validating their local context data. Please see the [docs](../additional-features/config-contexts.md#config-context-schemas) for more details.

Just like config contexts, config context JSON schemas can optionally be [managed via a Git repository](../models/extras/gitrepository.md#configuration-context-schemas).

#### Dynamic Navigation Menus ([#12](https://github.com/nautobot/nautobot/issues/12))

Applications and plugins can now define tabs, groups, items and buttons in the navigation menu. Using navigation objects a developer can add items to any section of the navigation using key names and weight values. Please see [Application Registry](../development/application-registry.md) for more details.

#### MySQL Database Support ([#17](https://github.com/nautobot/nautobot/issues/17))

MySQL 8.x is now fully supported as a database backend!

The installation and configuration guides have been revised to include MySQL. If you prefer MySQL or it is more easily supported in your environment, configuring Nautobot to use MySQL is as easy as changing value of `ENGINE` in your `DATABASES` setting to point to `django.db.backends.mysql` and installing the MySQL Python driver using `pip3 install nautobot[mysql]`.

!!! note
    You will not be able to directly migrate your data from PostgreSQL to MySQL. A fresh start is required.

A new `NAUTOBOT_DB_ENGINE` environment variable has been added to allow for specifying the desired database engine at runtime without needing to modify your `nautobot_config.py`. Please see the [configuration guide on `DATABASES`](../configuration/required-settings.md#databases) for more details on how to configure Nautobot to use MySQL.

Please see the MySQL setup guides for [Ubuntu](../installation/ubuntu.md#mysql-setup) and [CentOS](../installation/centos.md#mysql-setup) to get started.

#### Plugin Defined Jinja2 Filters

Plugins can now define custom Jinja2 filters to be used when rendering templates defined within computed fields or custom links. To register your own filters, you may add a `jinja_filters.py` to your plugin and any filters defined there will be automatically registered and globally usable. 

Please see the [plugin development documentation on including Jinja2 filters](../plugins/development.md#including-jinja2-filters) to get started.

#### Read Only Jobs ([#200](https://github.com/nautobot/nautobot/issues/200))

Jobs may be optionally marked as read only by setting the `read_only = True` meta attribute. This prevents the job from making any changes to nautobot data and suppresses certain log messages. Read only jobs can be a great way to safely develop new jobs, and for working with reporting use cases. Please see the [Jobs documentation](../additional-features/jobs.md) for more details.

#### Saved GraphQL Queries ([#3](https://github.com/nautobot/nautobot/issues/3))

[Saved GraphQL queries](../additional-features/graphql.md#saved-queries) offers a new model where reusable queries can be stored in Nautobot. New views for managing saved queries are available; additionally, the GraphiQL interface has been augmented to allow populating the interface from a saved query, editing and saving new queries.

Saved queries can easily be imported into the GraphiQL interface by using the new navigation tab located on the right side of the navbar. Inside the new tab are also buttons for editing and saving queries directly into Nautobot's databases.

Additionally, two new [GraphQL utility functions](../plugins/development.md#using-graphql-orm-utility) have been added to allow easy access to the GraphQL system from source code. Both functions can be imported from `nautobot.core.graphql`:

1. `execute_query()`: Runs string as a query against GraphQL.
2. `execute_saved_query()`: Execute a saved query from Nautobot database.

### Changed

#### Background Tasks now use Celery ([#223](https://github.com/nautobot/nautobot/issues/223))

Celery has been introduced to eventually replace RQ for executing background tasks within Nautobot. All Nautobot **core** usage of RQ has been migrated to use Celery. 

!!! note
    Custom background tasks implemented by plugins are not part of Nautobot core functions

Prior to version 1.1.0, Nautobot utilized RQ as the primary background task worker. As of Nautobot 1.1.0, RQ is now *deprecated*. RQ and the `@job` decorator for custom tasks are still supported for now, but will no longer be documented, and support for RQ will be removed in a future release.

RQ support for custom tasks was not removed in order to give plugin authors time to migrate, however, to continue to utilize advanced Nautobot features such as Git repository synchronization, webhooks, jobs, etc. you must migrate your `nautobot-worker` deployment from RQ to Celery.

Please see the section on [migrating to Celery from RQ](../installation/services.md#migrating-to-celery-from-rq) for more information on how to easily migrate your deployment.

!!! warning
    If you are running plugins that use background tasks requiring the RQ worker, you will need to run both the RQ and Celery workers concurrently until the plugins are converted to use the Celery worker. See the [Migrating to Celery from RQ](../installation/services.md#migrating-to-celery-from-rq) for details.

### Fixed

#### HTTP "Remote end closed connection" errors ([#725](https://github.com/nautobot/nautobot/issues/725))

The example `uwsgi.ini` provided in earlier versions of the Nautobot documentation was missing a recommendation to include the configuration `http-keepalive = 1` which enables support for HTTP/1.1 keep-alive headers.

!!! warning
    If you are upgrading from an earlier version of Nautobot (including 1.1.0) you should check your `uwsgi.ini` and ensure that it contains this important configuration line.

## v1.1.3 (2021-??-??)

### Added

- [#791](https://github.com/nautobot/nautobot/issues/791) - Added support for `NAUTOBOT_DOCKER_SKIP_INIT` variable to allow running the Docker container with a read-only database.

### Fixed

- [#464](https://github.com/nautobot/nautobot/issues/464) - Fixed GraphQL schema generation error when certain custom field names are used.
- [#731](https://github.com/nautobot/nautobot/issues/731) - Config context schemas including `format` properties (such as `"format": "ipv4"`) are now correctly enforced.
- [#779](https://github.com/nautobot/nautobot/issues/779) - Fixed incorrect Tenant display in Prefix "Duplicate Prefixes" table. (Port of [two](https://github.com/netbox-community/netbox/commit/20a85c1ef264ecfffcbe8602ab103baed5a7cf5b) [fixes](https://github.com/netbox-community/netbox/commit/0a1531ce8a5597333f2ac87fcc795c83a052fd47) originally from NetBox)
- [#809](https://github.com/nautobot/nautobot/issues/809) - Fixed docker-compose file `version` values to work correctly with older versions of docker-compose.
- [#818](https://github.com/nautobot/nautobot/issues/818) - Database health-check now reports as healthy even when in `MAINTENANCE_MODE`.

## v1.1.2 (2021-08-10)

### Added

- [#758](https://github.com/nautobot/nautobot/pull/758) - Added documentation about the Job `class_path` concept.
- [#771](https://github.com/nautobot/nautobot/pull/771) - Added examples of various possible logging configurations.
- [#773](https://github.com/nautobot/nautobot/pull/773) - Added documentation around enabling Prometheus metrics for database and caching backends.

### Changed

- [#742](https://github.com/nautobot/nautobot/pull/742) - The development environment now respects the setting of the `NAUTOBOT_DEBUG` environment variable if present.

### Fixed

- [#723](https://github.com/nautobot/nautobot/issues/723) - Fixed power draw not providing a `UtilizationData` type for use in graphing power draw utilization
- [#782](https://github.com/nautobot/nautobot/pull/782) - Corrected documentation regarding the use of `docker-compose.override.yml`
- [#785](https://github.com/nautobot/nautobot/issues/785) - Fixed plugin loading error when using `final` Docker image.
- [#786](https://github.com/nautobot/nautobot/issues/786) - Fixed `Unknown command: 'post_upgrade'` when using `final` Docker image.
- [#789](https://github.com/nautobot/nautobot/pull/789) - Avoid a `NoReverseMatch` exception at startup time if an app or plugin defines a nav menu item with an invalid link reference.

## v1.1.1 (2021-08-05)

### Added

- [#506](https://github.com/nautobot/nautobot/issues/506) - `nautobot-server` now detects and rejects the misconfiguration of setting `MAINTENANCE_MODE` while using database-backed session storage (`django.contrib.sessions.backends.db`)
- [#681](https://github.com/nautobot/nautobot/pull/681) - Added an example guide on how to use AWS S3 for hosting static files in production.

### Changed

- [#738](https://github.com/nautobot/nautobot/issues/738) - Added `*.env` (except `dev.env`) to `.gitignore` to prevent local environment variable files from accidentally being committed to Git

### Fixed

- [#683](https://github.com/nautobot/nautobot/issues/683) - Fixed slug auto-construction when defining a new ComputedField.
- [#725](https://github.com/nautobot/nautobot/issues/725) - Added missing `http-keepalive = 1` to recommended `uswgi.ini` configuration.
- [#727](https://github.com/nautobot/nautobot/issues/727) - Fixed broken REST API endpoint (`/api/extras/graphql-queries/<uuid>/run/`) for running saved GraphQL queries.
- [#744](https://github.com/nautobot/nautobot/issues/744) - Fixed missing Celery Django fixup that could cause assorted errors when multiple background tasks were run concurrently.
- [#746](https://github.com/nautobot/nautobot/issues/746) - Fixed data serialization error when running Jobs that used `IPAddressVar`, `IPAddressWithMaskVar`, and/or `IPNetworkVar` variables.
- [#759](https://github.com/nautobot/nautobot/issues/759) - Corrected backwards add/import links for Power Feed and Power Panel in navigation bar

## v1.1.0 (2021-07-20)

### Added

- [#372](https://github.com/nautobot/nautobot/issues/372) - Added support for displaying custom fields in tables used in object list views
- [#620](https://github.com/nautobot/nautobot/pull/620) - Config context schemas can now be managed via Git repositories.

### Changed

- [#675](https://github.com/nautobot/nautobot/pull/675) - Update MySQL unicode settings docs to be more visible
- [#684](https://github.com/nautobot/nautobot/issues/684) - Renamed `?opt_in_fields=` query param to `?include=`
- [#691](https://github.com/nautobot/nautobot/pull/691) - Clarify documentation on RQ to Celery worker migration and running both workers in parallel to help ease migration
- [#692](https://github.com/nautobot/nautobot/pull/692) - Clarify plugin development docs on naming of file for custom Jinja2 filters
- [#697](https://github.com/nautobot/nautobot/issues/697) - Added `CELERY_TASK_SOFT_TIME_LIMIT` to `settings.py` and lowered the default `CELERY_TASK_TIME_LIMIT` configuration.

### Fixed

- [#363](https://github.com/nautobot/nautobot/issues/363) - Fixed using S3 django-storages backend requires `USE_TZ=False`
- [#466](https://github.com/nautobot/nautobot/issues/466) - Fixed improper GraphQL schema generation on fields that can be blank but not null (such as `Interface.mode`)
- [#663](https://github.com/nautobot/nautobot/issues/663) - Fixed `kombu.exceptions.EncodeError` when trying to execute Jobs using `(Multi)ObjectVar` objects with nested relationships
- [#672](https://github.com/nautobot/nautobot/issues/672) - Fixed inheritance of Celery broker/results URL settings for dev/template configs (they can now be defined using Redis env. vars)
- [#677](https://github.com/nautobot/nautobot/issues/677) - Revise LDAPS outdated documentation for ignoring TLS cert errors
- [#680](https://github.com/nautobot/nautobot/issues/680) - Removed unnecessary warning message when both RQ and Celery workers are present
- [#686](https://github.com/nautobot/nautobot/issues/686) - Fixed incorrect permission name for Tags list view in nav menu
- [#690](https://github.com/nautobot/nautobot/pull/690) - Fixed Jinja2 dependency version to remain backwards-compatible with Nautobot 1.0.x
- [#696](https://github.com/nautobot/nautobot/pull/696) - Fixed inheritance of VRF and Tenant assignment when creating an IPAddress or Prefix under a parent Prefix. (Port of [NetBox #5703](https://github.com/netbox-community/netbox/issues/5703) and [NetBox #6012](https://github.com/netbox-community/netbox/issues/6012))
- [#698](https://github.com/nautobot/nautobot/issues/698) - Fixed cloning of a computed field object to now carry over required non-unique fields
- [#699](https://github.com/nautobot/nautobot/issues/699) - Exceptions such as TypeError are now caught and handled correctly when rendering a computed field.
- [#702](https://github.com/nautobot/nautobot/issues/702) - GraphiQL view no longer requires internet access to load libraries.
- [#703](https://github.com/nautobot/nautobot/issues/703) - Fixed direct execution of saved GraphQL queries containing double quotes
- [#705](https://github.com/nautobot/nautobot/issues/705) - Fixed missing description field from detail view for computed fields

### Security

- [#717](https://github.com/nautobot/nautobot/pull/717) - Bump Pillow dependency version from 8.1.2 to 8.2.0 to address numerous critical CVE advisories

## v1.1.0b2 (2021-07-09)

### Added

- [#599](https://github.com/nautobot/nautobot/issues/599) - Custom fields are now supported on `JobResult` objects
- [#637](https://github.com/nautobot/nautobot/pull/637) - Implemented a `nautobot-server fix_custom_fields` command to manually purge stale custom field data

### Changed

- [#634](https://github.com/nautobot/nautobot/pull/634) - Documentation on plugin capabilities has been clarified.

### Fixed

- [#495](https://github.com/nautobot/nautobot/issues/495) - Fixed search for partial IPv4 prefixes/aggregates not finding all matching objects
- [#533](https://github.com/nautobot/nautobot/issues/533) - Custom field tasks are now run atomically to avoid stale field data from being saved on objects.
- [#554](https://github.com/nautobot/nautobot/issues/554) - Fixed search for partial IPv6 prefixes/aggregates not finding all matching objects
- [#569](https://github.com/nautobot/nautobot/issues/569) - Change minimum/maximum allowed values for integer type in Custom Fields to 64-bit `BigIntegerField` types (64-bit)
- [#600](https://github.com/nautobot/nautobot/issues/600) - The `invoke migrate` step is now included in the development getting started guide for Docker workflows
- [#617](https://github.com/nautobot/nautobot/pull/617) - Added extra comments to `uwsgi.ini` config to help with load balancer deployments in Nautobot services documentation
- [#626](https://github.com/nautobot/nautobot/pull/626) - Added prefix `NAUTOBOT_` in `override.env` example inside of `docker-entrypoint.sh`
- [#645](https://github.com/nautobot/nautobot/issues/645) - Updated services troubleshooting docs to include "incorrect string value" fix when using Unicode emojis with MySQL as a database backend
- [#653](https://github.com/nautobot/nautobot/issues/653) - Fixed systemd unit file for `nautobot-worker` to correctly start/stop/restart
- [#661](https://github.com/nautobot/nautobot/issues/661) - Fixed `computed_fields` key not being included in API response for devices when using `include` (for opt-in fields)
- [#667](https://github.com/nautobot/nautobot/pull/667) - Fixed various outdated/incorrect places in the documentation for v1.1.0 release.

## v1.1.0b1 (2021-07-02)

### Added

- [#3](https://github.com/nautobot/nautobot/issues/3) - GraphQL queries can now be saved for later execution
- [#10](https://github.com/nautobot/nautobot/issues/10) - Added a new "Getting Started in the Web UI" section to the documentation to help new users begin learning how to use Nautobot.
- [#17](https://github.com/nautobot/nautobot/issues/17) - MySQL 8.x is now fully supported as a database backend
- [#200](https://github.com/nautobot/nautobot/issues/200) - Jobs can be marked as read-only
- [#274](https://github.com/nautobot/nautobot/issues/274) - Added config context schemas to optionally validate config and local context data against JSON Schemas
- [#297](https://github.com/nautobot/nautobot/issues/297) -  Added an anonymous health-checking endpoint at `/health/`using, also introducing a `nautobot-server health_check` command.
- [#485](https://github.com/nautobot/nautobot/pull/485) - Applications can define navbar properties through `navigation.py`
- [#557](https://github.com/nautobot/nautobot/issues/557) - `Prefix` records can now be created using /32 (IPv4) and /128 (IPv6) networks. (Port of [NetBox #6545](https://github.com/netbox-community/netbox/pull/6545))
- [#561](https://github.com/nautobot/nautobot/pull/561) - Added autodetection of `mime_type` on `export_templates` provided by Git datasources
- [#636](https://github.com/nautobot/nautobot/pull/636) - Added custom fields to `JobResult` model, with minor changes to job result detail page

### Changed

- [#431](https://github.com/nautobot/nautobot/issues/431) - `ConfigContext` and `ExportTemplate` records now must have unique `name` values. This was always the case in NetBox, but was inadvertently un-enforced in earlier versions of Nautobot.

### Fixed

- [#460](https://github.com/nautobot/nautobot/issues/460) - Deleting a record now deletes any associated `RelationshipAssociation` records
- [#494](https://github.com/nautobot/nautobot/issues/494) - Objects with `status` fields now emit limited choices correctly when performing `OPTIONS` metadata API requests
- [#602](https://github.com/nautobot/nautobot/issues/602) - Fixed incorrect requirement to install `toml` Python library before running `invoke` tasks
- [#618](https://github.com/nautobot/nautobot/pull/618) - Fixed typo in release-notes
