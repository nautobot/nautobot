<!-- markdownlint-disable MD024 -->
# Nautobot v1.1

This document describes all new features and changes in Nautobot 1.1.

If you are a user migrating from NetBox to Nautobot, please refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation.

## Release Overview

### Added

#### Computed Fields ([#4](https://github.com/nautobot/nautobot/issues/4))

[Computed fields](../models/extras/computedfield.md) offers users the ability to create read-only custom fields using existing data already stored in the database. Users define Jinja2 templates that populate the value of these fields. Computed fields are available on all data models that currently support custom fields.

#### Config Context JSON Schemas ([#274](https://github.com/nautobot/nautobot/issues/274))

While config contexts allow for arbitrary data structures to be stored within Nautobot, at scale it is desirable to apply validation constraints to that data to ensure its consistency and to avoid data entry errors. To service this need, Nautobot supports optionally backing config contexts with [JSON Schemas](https://json-schema.org/) for validation. These schema are managed via the config context schema model and are optionally linked to config context instances, in addition to devices and virtual machines for the purpose of validating their local context data. Please see the [docs](../additional-features/config-contexts.md#config-context-schemas) for more details.

Just like config contexts, config context JSON schemas can optionally be [managed via a Git repository](../models/extras/gitrepository.md#configuration-context-schemas).

#### Dynamic Navigation Menus ([#12](https://github.com/nautobot/nautobot/issues/12))

Applications and plugins can now define tabs, groups, items and buttons in the navigation menu. Using navigation objects a developer can add items to any section of the navigation using key names and weight values. Please see [Application Registry](../development/application-registry.md) for more details.

#### MySQL Database Support ([#17](https://github.com/nautobot/nautobot/issues/17))

MySQL 8.x is now fully supported as a database backend!

The installation and configuration guides have been revised to include MySQL. If you prefer MySQL or it is more easily supported in your environment, configuring Nautobot to use MySQL is as easy as changing value of `ENGINE` in your `DATABASES` setting to point to `django.db.backends.mysql` and installing the MySQL Python driver using `pip3 install nautobot[mysql]`.

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

## v1.1.6 (2021-12-03)

### Fixed

- [#1093](https://github.com/nautobot/nautobot/pull/1093) - Improved REST API performance by adding caching of serializer "opt-in fields".

## v1.1.5 (2021-11-11)

### Added

- [#263](https://github.com/nautobot/nautobot/issues/263) - Added a link in the Docker deployment guide to the Nautobot Docker Compose repository.
- [#931](https://github.com/nautobot/nautobot/issues/931) - Added support for direct upload of CSV files as an alternative to copy-pasting CSV text into a form field. (Partially based on [NetBox #6561](https://github.com/netbox-community/netbox/pull/6561))
- [#953](https://github.com/nautobot/nautobot/pull/953) - Added option to use MySQL in the docker-compose development environment
- [#954](https://github.com/nautobot/nautobot/pull/954) - Added documentation for migrating from PostgreSQL to MySQL, improved documentation as to recommended MySQL database configuration.
- [#989](https://github.com/nautobot/nautobot/issues/989) - Added `id` and `name` fields to `NestedJobResultSerializer` for the REST API.
- [#1019](https://github.com/nautobot/nautobot/pull/1019) - Added GitHub action to redeploy the Nautobot sandbox on pushes to `main`, `develop`, and `next`.
- [#1025](https://github.com/nautobot/nautobot/issues/1025) - Added reference documentation for how to hide navigation menu items with no permissions.
- [#1031](https://github.com/nautobot/nautobot/pull/1031) - Added a troubleshooting note around the combination of RedHat/CentOS, uWSGI, and static files.
- [#1057](https://github.com/nautobot/nautobot/pull/1057) - Added GitHub action to automatically push Docker images to `ghcr.io`.

### Fixed

- [#555](https://github.com/nautobot/nautobot/issues/555) - Fixed `Status.DoesNotExist` during `nautobot-server loaddata`.
- [#567](https://github.com/nautobot/nautobot/issues/567) - Fixed incorrect GraphQL schema generation for `_custom_field_data` when certain plugins are installed.
- [#733](https://github.com/nautobot/nautobot/issues/733) - A Job erroring out early in initialization could result in its associated JobResult staying in Pending state indefinitely.
- [#816](https://github.com/nautobot/nautobot/issues/816) - Fixed `AttributeError` reported when viewing a Rack with certain associated power configurations.
- [#948](https://github.com/nautobot/nautobot/issues/948) - Fixed advanced logging example to use `EXTRA_MIDDLEWARE` instead of `MIDDLEWARE.append()`.
- [#970](https://github.com/nautobot/nautobot/pull/970) - Clarified documentation around config context definition in Git repositories.
- [#981](https://github.com/nautobot/nautobot/pull/981) - Fixed incorrect handling of missing custom fields in the `fix_custom_fields` management command.
- [#986](https://github.com/nautobot/nautobot/issues/986) - Fixed `TemplateDoesNotExist` exception when running a Job containing a `FileVar` variable.
- [#991](https://github.com/nautobot/nautobot/pull/991) - Fixed incorrect logging when importing ConfigContextSchemas from Git.
- [#993](https://github.com/nautobot/nautobot/pull/993) - Fixed incorrect `git` command when refreshing a previously checked out repository.
- [#1023](https://github.com/nautobot/nautobot/issues/1023) - Removed invalid link in "Deploying Nautobot" documentation.

### Security

- [#998](https://github.com/nautobot/nautobot/pull/998) - Update `mkdocs` dependency to avoid a potential path-traversal vulnerability; note that mkdocs is only used in development and is not a production deployment dependency of Nautobot.

## v1.1.4 (2021-10-04)

### Added

- [#623](https://github.com/nautobot/nautobot/issues/623) - Git repository sync logs now include the commit hash that was synchronized to.
- [#728](https://github.com/nautobot/nautobot/issues/728) - Added `SOCIAL_AUTH_BACKEND_PREFIX` configuration setting to support custom authentication backends.
- [#861](https://github.com/nautobot/nautobot/issues/861) - Bulk editing of devices can now update their site, rack, and rack-group assignments.
- [#949](https://github.com/nautobot/nautobot/pull/949/) - Added documentation note about using `MAINTENANCE_MODE` in combination with LDAP.

### Changed

- [#956](https://github.com/nautobot/nautobot/pull/956) - Switched CI from Travis to GitHub Actions.
- [#964](https://github.com/nautobot/nautobot/pull/964) - Updated README.md build status badge to show GitHub status.

### Fixed

- [#944](https://github.com/nautobot/nautobot/issues/944) - Jobs that commit changes to the database could not be invoked successfully from the `nautobot-server runjob` command.
- [#955](https://github.com/nautobot/nautobot/issues/955) - REST API endpoint for syncing Git repositories was still checking for RQ workers instead of Celery workers.
- [#969](https://github.com/nautobot/nautobot/issues/969) - IPv6 prefixes such as `::1/128` were not being treated correctly.

### Security

- [#939](https://github.com/nautobot/nautobot/issues/939) - Nautobot views now default to `X-Frame-Options: DENY` rather than `X-Frame-Options: SAMEORIGIN`, with the exception of the rack-elevation API view (`/api/dcim/rack-elevation/`) which specifically requires `X-Frame-Options: SAMEORIGIN` for functional reasons.

## v1.1.3 (2021-09-13)

### Added

- [#11](https://github.com/nautobot/nautobot/issues/11) - Added tests to verify that plugin models can support webhooks if appropriately decorated with `@extras_features("webhooks")`
- [#652](https://github.com/nautobot/nautobot/issues/652) - Jobs REST API `run` endpoint now can look up ObjectVar references via a dictionary of parameters.
- [#755](https://github.com/nautobot/nautobot/issues/755) - Added example showing how to use `django-request-logging` middleware to log the user associated with inbound requests.
- [#791](https://github.com/nautobot/nautobot/issues/791) - Added support for `NAUTOBOT_DOCKER_SKIP_INIT` variable to allow running the Docker container with a read-only database.
- [#841](https://github.com/nautobot/nautobot/pull/841) - Added more detailed documentation around defining Relationship filters.
- [#850](https://github.com/nautobot/nautobot/pull/850) - Added developer documentation around the installation and use of `mkdocs` to locally preview documentation changes.
- [#856](https://github.com/nautobot/nautobot/issues/856) - Added more detailed user documentation on how to create an API token.

### Changed

- [#601](https://github.com/nautobot/nautobot/issues/601) - Developer documentation for advanced docker-compose use cases is now a separate file.
- [#709](https://github.com/nautobot/nautobot/issues/709) - Computed fields can now have a blank `fallback_value`.
- [#812](https://github.com/nautobot/nautobot/pull/812) - In the GraphiQL interface, the "Queries" dropdown now appears alongside the other GraphiQL interface buttons instead of appearing in the main Nautobot navigation bar.
- [#832](https://github.com/nautobot/nautobot/issues/832) - Plugin installation documentation now recommends `nautobot-server post_upgrade` instead of separately running `nautobot-server migrate` and `nautobot-server collectstatic`.

### Fixed

- [#464](https://github.com/nautobot/nautobot/issues/464) - Fixed GraphQL schema generation error when certain custom field names are used.
- [#651](https://github.com/nautobot/nautobot/issues/651) - Fixed Jobs validation enforce schema consistently across UI and API.
- [#670](https://github.com/nautobot/nautobot/pull/670) - Clarified Jobs documentation regarding how to fail or abort a Job.
- [#715](https://github.com/nautobot/nautobot/issues/715) - Fixed display of GraphiQL interface in narrow browser windows.
- [#718](https://github.com/nautobot/nautobot/issues/718) - Fixed rendering of long template values in Computed Field detail view.
- [#731](https://github.com/nautobot/nautobot/issues/731) - Config context schemas including `format` properties (such as `"format": "ipv4"`) are now correctly enforced.
- [#779](https://github.com/nautobot/nautobot/issues/779) - Fixed incorrect Tenant display in Prefix "Duplicate Prefixes" table. (Port of [two](https://github.com/netbox-community/netbox/commit/20a85c1ef264ecfffcbe8602ab103baed5a7cf5b) [fixes](https://github.com/netbox-community/netbox/commit/0a1531ce8a5597333f2ac87fcc795c83a052fd47) originally from NetBox)
- [#809](https://github.com/nautobot/nautobot/issues/809) - Fixed docker-compose file `version` values to work correctly with older versions of docker-compose.
- [#818](https://github.com/nautobot/nautobot/issues/818) - Database health-check now reports as healthy even when in `MAINTENANCE_MODE`.
- [#825](https://github.com/nautobot/nautobot/issues/825) - Removed unnecessary `-B` flag from development Celery worker invocation.
- [#830](https://github.com/nautobot/nautobot/issues/830) - Fixed incorrect database migration introduced by #818.
- [#845](https://github.com/nautobot/nautobot/pull/845) - Clarified documentation around `nautobot-server init` and `NAUTOBOT_ROOT`.
- [#848](https://github.com/nautobot/nautobot/pull/848) - Fixed stale links to NAPALM documentation

### Security

- [#893](https://github.com/nautobot/nautobot/pull/893) - Bump Pillow dependency version from 8.2.0 to 8.2.3 to address numerous critical CVE advisories

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
