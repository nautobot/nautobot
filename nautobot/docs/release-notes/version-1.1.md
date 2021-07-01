# Nautobot v1.1

This document describes all new features and changes in Nautobot 1.1

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Saved GraphQL Queries ([#3](https://github.com/nautobot/nautobot/issues/3))

[Saved GraphQL queries](../additional-features/graphql.md#saved-queries) offers a new model where reusable queries can be stored in Nautobot. New views for managing saved queries are available; additionally, the GraphiQL interface has been augmented to allow populating the interface from a saved query, editing and saving new queries.

Saved queries can easily be imported into the GraphiQL interface by using the new navigation tab located on the right side of the navbar. Inside the new tab are also buttons for editing and saving queries directly into Nautobot's databases.

#### App Defined Navigation ([#12](https://github.com/nautobot/nautobot/pull/485))

Applications can now define tabs, groups, items and buttons in the navigation menu. Using navigation objects a developer can add items to any section of the navigation using key names and weight values. Please see [Application Registry](../development/application-registry.md) for more details.

#### GraphQL ORM Functions

Two new [GraphQL utility functions](../plugins/development.md) have been added to allow easy access to the GraphQL system from source code. Both can be accessed by using `from nautobot.core.graphql import execute_saved_query, execute_query`.

1. `execute_query()`: Runs string as a query against GraphQL.
2. `execute_saved_query()`: Execute a saved query from Nautobot database.

#### MySQL Database Support ([#17](https://github.com/nautobot/nautobot/issues/17))

MySQL 8.x is now fully supported as a database backend!

The installation and configuration guides have been revised to include MySQL. If you prefer MySQL or it is more easily supported in your environment, configuring Nautobot to use MySQL is as easy as changing value of `ENGINE` in your `DATABASES` setting to point to `django.db.backends.mysql` and installing the MySQL Python driver using `pip3 install nautobot[mysql]`.

!!! note
    You will not be able to directly migrate your data from PostgreSQL to MySQL. A fresh start is required.

A new `NAUTOBOT_DB_ENGINE` environment variable has been added to allow for specifying the desired database engine at runtime without needing to modify your `nautobot_config.py`. Please see the [configuration guide on `DATABASES`](../configuration/required-settings.md#databases) for more details on how to configure Nautobot to use MySQL.

Please see the MySQL setup guides for [Ubuntu](../installation/ubuntu.md#mysql-setup) and [CentOS](../installation/centos.md#mysql-setup) to get started.

#### Read Only Jobs ([#200](https://github.com/nautobot/nautobot/issues/200))

Jobs may be optionally marked as read only by setting the `read_only = True` meta attribute. This prevents the job from making any changes to nautobot data and suppresses certain log messages. Read only jobs can be a great way to safely develop new jobs, and for working with reporting use cases. Please see the [Jobs documentation](../additional-features/jobs.md) for more details.

#### Config Context Schemas ([#274](https://github.com/nautobot/nautobot/issues/274))

While config contexts allow for arbitrary data structures to be stored within Nautobot, at scale it is desirable to apply validation constraints to that data to ensure its consistency and to avoid data entry errors. To service this need, Nautobot supports optionally backing config contexts with [JSON Schemas](https://json-schema.org/) for validation. These schema are managed via the config context schema model and are optionally linked to config context instances, in addition to devices and virtual machines for the purpose of validating their local context data. Please see the [docs](../additional-features/config-contexts.md#config-context-schemas) for more details.

#### Background Tasks now use Celery ([#223](https://github.com/nautobot/nautobot/issues/223))

Celery has been introduced to eventually replace RQ for executing background tasks within Nautobot. All core usage of RQ has been migrated to use Celery.

Prior to version 1.1.0, Nautobot utilized RQ as the primary background task worker. As of Nautobot 1.1.0, RQ is now *deprecated*. RQ and the `@job` decorator for custom tasks are still supported for now, but will no longer be documented, and support for RQ will be removed in a future release.

RQ support for custom tasks was not removed in order to give plugin authors time to migrate, however, to continue to utilize advanced Nautobot features such as Git repository synchronization, webhooks, jobs, etc. you must migrate your `nautobot-worker` deployment from RQ to Celery.

Please see the section on [migrating to Celery from RQ](../installation/services.md#migrating-to-celery-from-rq) for more information on how to easily migrate your deployment.

### Changed

### Removed

## v1.1.0 (2021-MM-DD)

### Added

- [#3](https://github.com/nautobot/nautobot/issues/3) - GraphQL queries can now be saved for later execution
- [#17](https://github.com/nautobot/nautobot/issues/17) - MySQL 8.x is now fully supported as a database backend
- [#200](https://github.com/nautobot/nautobot/issues/200) - Jobs can be marked as read-only
- [#274](https://github.com/nautobot/nautobot/issues/274) - Added config context schemas to optionally validate config and local context data against JSON Schemas
- [#297](https://github.com/nautobot/nautobot/issues/297) -  Added an anonymous health-checking endpoint at /`health/`using, also introducing a `nautobot-server health_check` command.
- [#485](https://github.com/nautobot/nautobot/pulls/485) - Applications can define navbar properties through `navigation.py`
- [#561](https://github.com/nautobot/nautobot/pulls/561) - Added autodetection of `mime_type` on `export_templates` provided by Git datasources

### Changed

### Fixed

### Removed
