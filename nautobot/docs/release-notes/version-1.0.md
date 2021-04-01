# Nautobot v1.0

This document describes all new features and changes in Nautobot 1.0, a divergent fork of NetBox 2.10.  For the launch of Nautobot 1.0 and for the purpose of this document,  all “new” features or “changes” are referring to the features and changes comparing Nautobot 1.0 coming from NetBox 2.10.  All future release notes will only refer to features and changes relative to prior releases of Nautobot.

Users migrating from NetBox to Nautobot should also refer to the ["Migrating from NetBox"](../installation/migrating-from-netbox.md) documentation as well.

## v1.0.0b3 (FUTURE)

!!! warning
    v1.0.0b3 introduces several database changes that are **not** backwards-compatible with v1.0.0b2 and earlier. There is no direct upgrade path from v1.0.0b2 to v1.0.0b3 - you **must** create a new database when installing v1.0.0b3!

### Added

- [#100](https://github.com/nautobot/nautobot/issues/100) - Added detailed documentation of the `nautobot-server` command
- [#105](https://github.com/nautobot/nautobot/issues/105) - Added tooltip with detailed information to utilization graph bars.
- [#109](https://github.com/nautobot/nautobot/pull/109) - Docker development environment build now automatically installs from any present `local_requirements.txt` file
- [#121](https://github.com/nautobot/nautobot/pull/121) - Added "Data Model Changes" section to the "Migrating from NetBox" documentation
- [#141](https://github.com/nautobot/nautobot/pull/141) - Custom Link UI now includes example usage hints

### Changed

- [#78](https://github.com/nautobot/nautobot/pull/78) - Replaced PostgreSQL-specific IP network/address fields with more generic field types
- [#83](https://github.com/nautobot/nautobot/issues/83) - Custom user model added; UserConfig model merged into User model
- [#84](https://github.com/nautobot/nautobot/issues/84) - Revised developer documentation for clarity and current workflows
- [#119](https://github.com/nautobot/nautobot/pull/119) - Various documentation improvements
- [#122](https://github.com/nautobot/nautobot/pull/122) - Improved installation flow for creating nautobot user and virtualenv
- [#131](https://github.com/nautobot/nautobot/pull/131) - Replaced PostgreSQL-specific ArrayField with a more generic JSONArrayField
- [#142](https://github.com/nautobot/nautobot/pull/142) - Converted various config validation checks into proper Django checks
- [#180](https://github.com/nautobot/nautobot/pull/180) - Revised available Invoke tasks for simplicity and maintainability

### Removed

- [#124](https://github.com/nautobot/nautobot/pull/124) - Removed incorrect statement from feature request template
- [#161](https://github.com/nautobot/nautobot/pull/161) - Removed leftover references in documentation to `RQ_DEFAULT_TIMEOUT`

### Fixed

- [#76](https://github.com/nautobot/nautobot/issues/76) - Cable paths could not be traced through circuits
- [#95](https://github.com/nautobot/nautobot/issues/95) - Plugin load errors under Gunicorn
- [#128](https://github.com/nautobot/nautobot/pull/128) - Overview of usage for the `nautobot-netbox-importer` plugin could be mistaken for full instructions
- [#132](https://github.com/nautobot/nautobot/issues/132) - Generated `nautobot_config.py` did not include a trailing newline
- [#134](https://github.com/nautobot/nautobot/issues/134) - Missing venv activation step in install guide
- [#153](https://github.com/nautobot/nautobot/issues/153) - Editing an existing user token shows "create" buttons instead of "update"
- [#154](https://github.com/nautobot/nautobot/issues/154) - Some tests were failing when run in the development Docker container
- [#155](https://github.com/nautobot/nautobot/issues/155) - NAPALM driver string not displayed in Platform detail view
- [#168](https://github.com/nautobot/nautobot/issues/168) - Incorrect `AUTHENTICATION_BACKENDS` example in remote authentication documentation
- [#172](https://github.com/nautobot/nautobot/issues/172) - Incorrect whitespace in some HTML template tags
- [#181](https://github.com/nautobot/nautobot/pull/181) - Incorrect UI reference in Webhook documentation

## v1.0.0b2 (2021-03-08)

### Added

- [#35](https://github.com/nautobot/nautobot/issues/35) - Documentation for troubleshooting Nautobot's interaction with SELinux.
- [#47](https://github.com/nautobot/nautobot/issues/47) - Basic user documentation for Relationships feature.
- [#48](https://github.com/nautobot/nautobot/issues/48) - Additional unit testing and bug fixes for Relationships feature.
- [#99](https://github.com/nautobot/nautobot/pull/99) - Add `BASE_PATH` to `development/nautobot_config.py`.
- [#101](https://github.com/nautobot/nautobot/issues/101) - Complete documentation of `NAUTOBOT_ROOT`
- [#107](https://github.com/nautobot/nautobot/pull/107) - Add `nautobot-server post_upgrade` command

### Changed

- [#52](https://github.com/nautobot/nautobot/pull/52) - Disabled Poetry's "parallel installation" feature for CI and development builds.
- [#61](https://github.com/nautobot/nautobot/pull/61) - Updated pull request template contents for clarity.
- [#74](https://github.com/nautobot/nautobot/pull/74) - Refactor install instructions to be more streamlined and more intuitive.
    - Renamed `nautobot-rq` service to `nautobot-worker`
    - Replaced `BASE_STORAGE_DIR` configuration setting with `NAUTOBOT_ROOT`; this new setting also influences the default value of `DEFAULT_CONFIG_PATH`.
- [#88](https://github.com/nautobot/nautobot/issues/88) - Replace Gunicorn w/ uWSGI
- [#89](https://github.com/nautobot/nautobot/pull/89) - Development workflow improvements
    - Replace `pycodestyle` with `flake8` for linting.
    - Add `invoke black` and `invoke tests` commands
    - Improve speed of development Docker container rebuilds
    - `django-debug-toolbar` is now a development dependency rather than a production dependency for Nautobot.
- [#106](https://github.com/nautobot/nautobot/pull/106) - Revise deployment docs to use `$PATH` instead of venv activate
- [#108](https://github.com/nautobot/nautobot/pull/108) - Document special workflow for development using containers on remote servers

### Removed

- [#72](https://github.com/nautobot/nautobot/pull/72) - Removed issue template for "Documentation Change"; use "Bug" or "Feature Request" issue templates instead.

### Fixed

- [#36](https://github.com/nautobot/nautobot/pull/36) - Broken links to ReadTheDocs pages.
- [#41](https://github.com/nautobot/nautobot/pull/41) - Incorrect field name in CustomLink Admin page.
- [#42](https://github.com/nautobot/nautobot/issues/42) - Incorrect link to `nautobot-plugin-golden-config` GitHub repository
- [#45](https://github.com/nautobot/nautobot/issues/45) - Incorrect button labels when creating/editing an Interface record.
- [#43](https://github.com/nautobot/nautobot/issues/43) - Incorrect commands in documentation for adding optional dependencies to `local_requirements.txt`
- [#51](https://github.com/nautobot/nautobot/issues/51) - Incorrect functioning of "development container" in VSCode integration.
- [#57](https://github.com/nautobot/nautobot/pull/57) - Incorrect `AUTHENTICATION_BACKENDS` example in `authentication/ldap.md`
- [#63](https://github.com/nautobot/nautobot/issues/63) - Incorrect help text for "Destination Label" field when creating/editing Relationship records.
- [#64](https://github.com/nautobot/nautobot/issues/64) - Incorrect absolute link to ReadTheDocs page.
- [#69](https://github.com/nautobot/nautobot/issues/69) - More incorrect links to ReadTheDocs pages.
- [#79](https://github.com/nautobot/nautobot/issues/79) - Incorrect internal documentation link to `STORAGE_BACKEND` optional setting.
- [#81](https://github.com/nautobot/nautobot/issues/81) - Unable to change Device rack position after creation.
- [#93](https://github.com/nautobot/nautobot/issues/93) - Bug when setting `CACHEOPS_DEFAULTS` timeout value to `0`.

## v1.0.0b1 (2021-02-24)

### Added

#### Custom Fields on All Models

[Custom fields](../additional-features/custom-fields.md) allow user-defined fields, or attributes, on specific data models such as sites or devices. Historically, custom fields have been supported only on “primary” models (Site, Device, Rack, Virtual Machine, etc.) but not on “organizational” models (Region, Device Platform, Rack Group, etc.) or on “device component” models like interfaces. As of Nautobot 1.0, custom fields are now supported on every model, including interfaces.

#### Customizable Statuses

A new ["Status" model](../models/extras/status.md) has been added, allowing users to define additional permitted values for the "status" field on any or all of the models that have such a field (Cable, Circuit, Device, IPAddress, PowerFeed, Prefix, Rack, Site, VirtualMachine, VLAN). The default sets of statuses permitted for each model remain the same as in NetBox 2.10, but you are now free to define additional status values as suit your needs and workflows.

One example application for custom statuses would be in defining additional values to apply to a Device as part of an automation workflow, with statuses such as `upgrading` or `rebooting` to reflect the progress of each device through the workflow, allowing automation to identify the appropriate next action to take for each status.

#### Data Validation Plugin API

Data quality assurance in Nautobot becomes easier with the new [data validation plugin API](../plugins/development.md#implementing-custom-validators). This makes it possible to codify organizational standards.  Using a data validation [plugin](../../plugins/), an organization can ensure all data stored in Nautobot meets its specific standards, such as enforcing device naming standards, ensuring certain prefixes are never used, asserting that VLANs always have a name, requiring interfaces to always have a description, etc. The ability to ensure a high quality of data becomes much more streamlined; error-prone, manual process becomes automated; and there is no more need to actively run reports to check data quality.

A [data validation plugin](https://github.com/nautobot/nautobot-plugin-data-validation-engine) is available that addresses many common use cases for data validation, but you are also free to implement your own plugin to meet your own unique requirements.

#### Detail Views for more Models

Detailed view pages are now provided for models including ClusterGroup, ClusterType, DeviceRole, Manufacturer, Platform, and RackRole.

#### Docker-Based Development Environment

In addition to the previously available virtual-environment-based developer workflow, Nautobot now additionally supports a [development environment based around Docker](../development/getting-started.md#docker-development-environment-workflow) as an alternative.

#### Git Integration as a Data Source

[Git integration](../models/extras/gitrepository.md) offers users an option to integrate into a more traditional NetDevOps pipeline for managing Python modules, Jinja templates, and YAML/JSON data.  There are several use cases that have historically required users to either manage Python modules on the filesystem or use Jinja2 templates within the GUI. With this new feature, users can add a Git repository from the UI or REST API, the contents of which will be synchronized into Nautobot immediately and can be later refreshed on-demand. This allows users to more easily update and manage:

- *Jobs* - store your Python modules that define Jobs (formerly known as Custom Scripts and/or Reports) in a Git repository
- *Export Templates* - store your Jinja templates used to create an export template in a Git repository
- *Config Contexts* - store your YAML/JSON data used within a config context in a Git repository
- *Arbitrary Files* - usable by custom plugins and apps

Not only does this integration and feature simplify management of these features in Nautobot, it offers users the ability to use Git workflows for the management of the jobs, templates, and data ensuring there has been proper review and approval before updating them on the system.

#### GraphQL Support

Nautobot now provides an HTTP API endpoint supporting [GraphQL](https://graphql.org/). This feature adds a tremendous amount of flexibility in querying data from Nautobot. It offers the ability to query for specific datasets across multiple models in a single query.  Historically, if you wanted to retrieve the list of devices, all of their interfaces, and all of their neighbors, this would require numerous REST API calls.  GraphQL gives the flexibility to get all the data desired and nothing unnecessary, all in a single API call.

For more details, please refer to the GraphQL website, as well as to the [Nautobot GraphQL](../additional-features/graphql.md) documentation.

#### Plugin API Enhancements

Plugins can now provide custom [data validation](#data-validation-plugin-api) logic.

Plugins can now include executable [Jobs](../additional-features/jobs.md) (formerly known as Custom Scripts and Reports) that will automatically be added to the list of available Jobs for a user to execute.

Additional data models defined by a plugin are automatically made available in [GraphQL](../additional-features/graphql).

Plugins can now define additional Django apps that they require and these dependencies will be automatically enabled when the plugin is activated.

#### Single Sign-On / Social Authentication Support

Nautobot now supports single sign on as an authentication option using OAuth2, OpenID, SAML, and others, using the [social-auth-app-django](https://python-social-auth.readthedocs.io/en/latest/) module. For more details please refer to the guide on [SSO authentication](../configuration/authentication/sso.md).

#### User-Defined Relationships

User-Defined, or "custom", [relationships](../../models/extras/relationship) allow users to create their own relationships between models in Nautobot to best suit the needs of their specific network design. Nautobot comes with opinionated data models and relationships.

For example, a VLAN is mapped to a Site by default.  After a VLAN is created today, you then assign that VLAN to an Interface on a Device. This Device should be within the initial mapped Site.  However, many networks today have different requirements and relationships for VLANs (and many other models): VLANs may be limited to racks in Layer 3 DC fabrics; VLANs may be mapped to multiple buildings in a campus; they may span sites.  Other use cases include circuits, ASNs, or IP addressing--just to name a few--allowing users to define the exact relationships required for their network.

### Changed

#### Code Reorganization

All of the individual Django apps in NetBox (`dcim`, `extras`, `ipam`, etc.) have been moved into a common `nautobot` Python package namespace. The `netbox` application namespace has been moved to `nautobot.core`. This will require updates when porting NetBox custom scripts and reports to Nautobot jobs, as well as when porting NetBox plugins to Nautobot.

#### Packaging Changes

Nautobot is now packaged using [Poetry](https://python-poetry.org/) and builds as an installable Python package. `setup.py` and `requirements.txt` have been replaced with `pyproject.toml`. Releases of Nautobot are now published to [PyPI](https://pypi.org/), the Python Package Index, and therefore can now be installed using `pip install nautobot`.

#### Installation and Startup

Because Nautobot may be installed using `pip`, we have replaced `manage.py` with a dedicated `nautobot-server` CLI command used to adminster the server. It works exactly as `manage.py` does, but does not require you to be within the project root directory.

#### Configuration and Settings

Nautobot has done away with the requirement to duplicate or modify files anywhere in the source code. The `configuration.py` file has been replaced with a `nautobot_config.py` file that may be read from anywhere on your system. It is also much easier to add custom settings or overload nearly any default setting.

To facilitate this, many automatically generated settings have been removed, and replaced with their underlying static configurations. We feel this affords a greater amount of flexibility in deployment patterns, with a tradeoff of slightly more initial configuration.

To make things a little easier, you may generate a new configuration with sane defaults using the `nautobot-server init` command! The configuration file defaults to `~/.nautbot/nautobot_config.py` but using the `nautobot-server --config` argument, you may name or place the file anywhere you choose.

You may also defined a `NAUTOBOT_CONFIG` variable to tell Nautobot where to find the file so that you don't need to always pass the `--config` argument.

For details see [Configuring Nautobot](../../configuration).

#### Consolidating Custom Scripts and Reports into Jobs

Nautobot has consolidated NetBox's "custom scripts" and "reports" into what is now called [Jobs](../additional-features/jobs.md).

The job history ([results](../models/extras/jobresult.md)) table on the home page now shows metadata on each job such as the timestamp and the user that executed the job. Additionally, jobs can be defined and executed by the system and by plugins, and when they are, users can see their results in the history too. UI views have been added for viewing the details of a given job result, and the [JobResult](../models/extras/jobresult.md) model now provides standard APIs for Jobs to log their status and results in a consistent way.

Job result history is now retained indefinitely unless intentionally deleted. Historically only the most recent result for each custom script or report was retained and all older records were deleted.

Python modules that define jobs can now be stored in Git and easily added to Nautobot via the UI as documented above in [Git Integration as a Data Source](#git-integration-as-a-data-source).

#### Hiding UI Elements based on Permissions

Historically, a user viewing the home page and navigation menu would see a list of all model types and menu items in the system, with a “lock” icon on items that they were not granted access to view in detail.

As an [option](../configuration/optional-settings.md#hide_restricted_ui), administrators can now choose to instead hide un-permitted items altogether from the home page and the navigation menu, providing a simpler interface for limited-access users. The prior behavior remains as the default.

#### Navigation Menu Changes

The "Other" menu has been renamed to "Extensibility" and many new items have been added to this menu.

[Status](../models/extras/status.md) records have been added to the "Organization" menu.

#### New Name and Logo

NetBox has been changed to Nautobot throughout the code, UI, and documentation, and Nautobot has a new logo.

#### User-Defined Custom Links

Nautobot allows for the definition of [custom links](../models/extras/customlink.md) to add to various built-in data views. These can be used to provide convenient cross-references to other data sources outside Nautobot, among many other possibilities.

Historically this feature was restricted so that only administrators could define and manage custom links. In Nautobot this has been moved into the main user interface, accessible to any user who has been granted appropriate access permissions.

#### User-Defined Export Templates

Nautobot allows for the definition of custom [Jinja2 templates](../models/extras/exporttemplate.md) to use to format exported data.

Historically this feature was restricted such that only administrators could define and edit these templates. In Nautobot this has been moved into the main user interface, accessible to any user who has been granted appropriate access permissions.

#### User-Defined Webhooks

Nautobot allows for the creation of [webhooks](../models/extras/webhook.md), HTTP callbacks that are triggered automatically when a specified data model(s) are created, updated, and/or deleted.

Historically this feature was restricted such that only administrators could define and manage webhooks. In Nautobot this has been moved into the main user interface, accessible to any user who has been granted appropriate access permissions.

#### UUID Primary Database Keys

Database keys are now defined as Universally Unique Identifiers (UUIDs) instead of integers, protecting against certain classes of data-traversal attacks.

### Removed

#### Secrets

Secrets storage and management has been removed from Nautobot.

#### Related Devices

The "Related Devices" table has been removed from the detailed Device view.

### Fixed

- Fixed a bug in which object permissions were not filtered correctly in the admin interface. <!-- FIXME(john): improve the description of this fix -->
- Fixed a bug in which the UI would report an exception if the database contains ChangeLog entries that reference a nonexistent ContentType.

---
