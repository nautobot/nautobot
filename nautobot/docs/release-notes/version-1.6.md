<!-- markdownlint-disable MD024 -->

# Nautobot v1.6

This document describes all new features and changes in Nautobot 1.6.

## Release Overview

### Added

#### Custom Field "Markdown" Type ([#4006](https://github.com/nautobot/nautobot/issues/4006))

A new Custom Field type, "Markdown", has been added. Custom fields of this type can store Markdown-formatted text which will be rendered in the web UI.

#### Caching of Dynamic Groups and Content Types ([#4092](https://github.com/nautobot/nautobot/pull/4092))

APIs have been added to allow for caching of the results of looking up an object's content-type or Dynamic Group memberships, as well as for looking up the members of a Dynamic Group itself. These caches are disabled by default but can be enabled by configuring the [`DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT`](../configuration/optional-settings.md#dynamic_groups_member_cache_timeout) and [`CONTENT_TYPE_CACHE_TIMEOUT`](../configuration/optional-settings.md#content_type_cache_timeout) settings respectively. Apps (plugins) that make use of dynamic groups should review the [documentation for the APIs](../models/extras/dynamicgroup.md#membership-and-caching) to determine how and when to make use of the cache for improved performance.

#### Interface Redundancy Group ([#2825](https://github.com/nautobot/nautobot/issues/2825))

Interface Redundancy Group model and related views have been added to allow logical grouping of multiple interfaces under a specific interface redundancy protocol (HSRP, VRRP, CARP, and etc).

#### Installation Metrics ([#4047](https://github.com/nautobot/nautobot/issues/4047))

A new setting, [`INSTALLATION_METRICS_ENABLED`](../configuration/optional-settings.md#installation_metrics_enabled), has been added to allow Nautobot to send anonymous installation metrics to the Nautobot maintainers. This setting is `True` by default but can be changed in `nautobot_config.py` or the `NAUTOBOT_INSTALLATION_METRICS_ENABLED` environment variable.

If the [`INSTALLATION_METRICS_ENABLED`](../configuration/optional-settings.md#installation_metrics_enabled) setting is `True`, running the [`post_upgrade`](../administration/nautobot-server.md#post_upgrade) or [`send_installation_metrics`](../administration/nautobot-server.md#send_installation_metrics) management commands will send a list of all installed [plugins](../plugins/index.md) and their versions, as well as the currently installed Nautobot and Python versions, to the Nautobot maintainers. A randomized UUID will be generated and saved in the [`DEPLOYMENT_ID`](../configuration/optional-settings.md#deployment_id) setting to anonymously and uniquely identify each installation. The plugin names will be one-way hashed with SHA256 to further anonymize the data sent. This enables tracking the installation metrics of publicly released plugins without disclosing the names of any private plugins.

The following is an example of the data that is sent:

```py
{
    "deployment_id": "1de3dacf-f046-4a98-8d4a-17419080db79",
    "nautobot_version": "1.6.0b1",
    "python_version": "3.10.12",
    "installed_apps": {
        # "example_plugin" hashed by sha256
        "3ffee4622af3aad6f78257e3ae12da99ca21d71d099f67f4a2e19e464453bee7": "1.0.0"
    },
    "debug": true
}
```

#### `Platform.network_driver` and related fields ([4136](https://github.com/nautobot/nautobot/issues/4136))

The [Platform](../models/dcim/platform.md) model has been enhanced to include a `network_driver` database field and a `network_driver_mappings` derived property based on the [`netutils`](https://netutils.readthedocs.io/en/latest/) library. For example, if you set a Platform to have a `network_driver` value of `"cisco_ios"`, the `platform.network_driver_mappings` property will return a dictionary containing `ansible`, `hier_config`, `napalm`, `netmiko`, `ntc_templates`, `pyats`, `pyntc`, and `scrapli` keys corresponding to this entry. These properties can be referenced via the REST API and GraphQL to assist in developing and maintaining Apps, Jobs, or third-party code that interact with devices by using any of these libraries.

If the default derivations provided by `netutils` are not suitable for your purposes, you can extend or override them by configuring the [`NETWORK_DRIVERS`](../configuration/optional-settings.md#network_drivers) system setting.

#### Python 3.11 Support ([#3561](https://github.com/nautobot/nautobot/issues/3561))

Nautobot 1.6.0 formally adds support for installation and operation under Python 3.11.

### Changed

#### Additional `HIDE_RESTRICTED_UI` Effects for Unauthenticated Users ([#3646](https://github.com/nautobot/nautobot/issues/3646))

When `HIDE_RESTRICTED_UI` is enabled, unauthenticated users are no longer able to view the OpenAPI (Swagger) UI, the GraphiQL UI, or any configured top/bottom banners. Additionally, the page footer on the login page will not display the Nautobot server hostname in this case.

#### Increased `Device.asset_tag` maximum length ([#3693](https://github.com/nautobot/nautobot/issues/3693))

The maximum length of the `Device.asset_tag` field has been increased from 50 to 100 characters.

#### Changed Default Python Version for Docker Images ([#4029](https://github.com/nautobot/nautobot/issues/4029))

The default Python version for Nautobot Docker images has been changed from 3.7 to 3.11.

### Removed

#### Removed Python 3.7 Support ([#3561](https://github.com/nautobot/nautobot/issues/3561))

As Python 3.7 has reached end-of-life, Nautobot 1.6 and later do not support installation or operation under Python 3.7.

<!-- towncrier release notes start -->

## v1.6.31 (2025-05-12)

### Security

- [#6983](https://github.com/nautobot/nautobot/issues/6983) - Updated dependency `Jinja2` to `~3.1.6` to address `CVE-2025-27516`.

### Fixed

- [#6985](https://github.com/nautobot/nautobot/issues/6985) - Fixed Rack Elevation filtering by adding `filterset_form` to the `RackElevationListView`.

### Housekeeping

- [#6618](https://github.com/nautobot/nautobot/issues/6618) - Update GitHub actions *.yml file to use minimum ubuntu-24.04 since ubuntu-20.04 is deprecated.
- [#6988](https://github.com/nautobot/nautobot/issues/6988) - Updated GitHub Actions to use `networktocode/gh-action-setup-poetry-environment@v6`.

## v1.6.30 (2025-01-06)

### Security

- [#6695](https://github.com/nautobot/nautobot/issues/6695) - Updated dependency `Jinja2` to `~3.1.5` to address `CVE-2024-56201` and `CVE-2024-56326`.

### Housekeeping

- [#6659](https://github.com/nautobot/nautobot/issues/6659) - Enhanced development environment and associated `invoke` tasks to be Nautobot major/minor version aware, such that a different Docker compose `project-name` (and different local Docker image label) will be used for containers in a `develop`-based branch versus a `next`-based branch versus an `ltm`-based branch.

## v1.6.29 (2024-12-10)

### Security

- [#5911](https://github.com/nautobot/nautobot/issues/5911) - Updated `zipp` to `3.19.2` to address `CVE-2024-5569`. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#6625](https://github.com/nautobot/nautobot/issues/6625) - Patched `set_values()` method of Query class from django.db.models.sql.query to address `CVE-2024-42005`.

### Fixed

- [#5924](https://github.com/nautobot/nautobot/issues/5924) - Fixed the redirect URL for the Device Bay Populate/Depopulate view to take the user back to the Device Bays tab on the Device page.
- [#6502](https://github.com/nautobot/nautobot/issues/6502) - Fixed a bug in the Dockerfile that prevented `docker build` from working on some platforms.
- [#6502](https://github.com/nautobot/nautobot/issues/6502) - Fixed Docker builds failing in Gitlab CI.

## v1.6.28 (2024-09-24)

### Fixed

- [#6152](https://github.com/nautobot/nautobot/issues/6152) - Fixed table column ordering.
- [#6237](https://github.com/nautobot/nautobot/issues/6237) - Corrected presentation of rendered Markdown content in Notes table.
- [#6262](https://github.com/nautobot/nautobot/issues/6262) - Fixed invalid installation of `xmlsec` library in the Nautobot Docker images.

### Housekeeping

- [#5637](https://github.com/nautobot/nautobot/issues/5637) - Removed "version" from development `docker-compose.yml` files as newer versions of Docker complain about it being obsolete.
- [#5637](https://github.com/nautobot/nautobot/issues/5637) - Fixed behavior of `invoke stop` so that it also stops the optional `mkdocs` container if present.
- [#6262](https://github.com/nautobot/nautobot/issues/6262) - Brought `.gitignore` up to date with latest to aid in branch switching.

## v1.6.27 (2024-09-03)

### Security

- [#6182](https://github.com/nautobot/nautobot/issues/6182) - Updated `cryptography` to `43.0.1` to address `GHSA-h4gh-qq45-vh27`. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Fixed

- [#6081](https://github.com/nautobot/nautobot/issues/6081) - Fixed AttributeError during pre_migrate when permission constraints are applied to custom fields.

## v1.6.26 (2024-07-22)

### Fixed

- [#5935](https://github.com/nautobot/nautobot/issues/5935) - Fixed issue in which a save() could be called unnecessarily on child devices.

## v1.6.25 (2024-07-09)

### Security

- [#5891](https://github.com/nautobot/nautobot/issues/5891) - Updated `certifi` to `2024.7.4` to address `CVE-2024-39689`. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Dependencies

- [#5897](https://github.com/nautobot/nautobot/pull/5897) - Pinned dev dependency `faker` to `>=0.7.0,<26.0.0` to work around breaking change in v26.0.0 ([faker/#2070](https://github.com/joke2k/faker/issues/2070)).

## v1.6.24 (2024-06-24)

### Security

- [#5821](https://github.com/nautobot/nautobot/issues/5821) - Updated `urllib3` to 2.2.2 due to CVE-2024-37891. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Housekeeping

- [#5754](https://github.com/nautobot/nautobot/issues/5754) - Updated development dependency `requests` to `~2.32.2`.

## v1.6.23 (2024-05-28)

### Security

- [#5740](https://github.com/nautobot/nautobot/issues/5740) - Updated `requests` to `2.32.1` to address [GHSA-9wx4-h78v-vm56](https://github.com/psf/requests/security/advisories/GHSA-9wx4-h78v-vm56). This is not a direct dependency so it will not auto-update when upgrading Nautobot. Please be sure to update your local environment.
- [#5762](https://github.com/nautobot/nautobot/issues/5762) - Fixed missing member object permission enforcement (e.g., enforce Device permissions for a Dynamic Group containing Devices) when viewing Dynamic Group member objects in the UI or REST API ([GHSA-qmjf-wc2h-6x3q](https://github.com/nautobot/nautobot/security/advisories/GHSA-qmjf-wc2h-6x3q)).

### Housekeeping

- [#5740](https://github.com/nautobot/nautobot/issues/5740) - Updated test dependency `requests` to `~2.32.1`.

## v1.6.22 (2024-05-13)

### Security

- [#1858](https://github.com/nautobot/nautobot/issues/1858) - Added sanitization of HTML tags in the content of `BANNER_TOP`, `BANNER_BOTTOM`, and `BANNER_LOGIN` configuration to prevent against potential injection of malicious scripts (stored XSS) via these features ([GHSA-r2hr-4v48-fjv3](https://github.com/nautobot/nautobot/security/advisories/GHSA-r2hr-4v48-fjv3)).

### Added

- [#1858](https://github.com/nautobot/nautobot/issues/1858) - Added support in `BRANDING_FILEPATHS` configuration to specify a custom `css` and/or `javascript` file to be added to Nautobot page content.
- [#1858](https://github.com/nautobot/nautobot/issues/1858) - Added Markdown support to the `BANNER_TOP`, `BANNER_BOTTOM`, and `BANNER_LOGIN` configuration settings.

### Fixed

- [#2974](https://github.com/nautobot/nautobot/issues/2974) - Fixed an error when deleting and then recreating a GitRepository that provides Jobs.

## v1.6.21 (2024-05-07)

### Security

- [#5521](https://github.com/nautobot/nautobot/issues/5521) - Updated `Pillow` dependency to `~10.3.0` to address `CVE-2024-28219`.
- [#5561](https://github.com/nautobot/nautobot/issues/5561) - Updated `idna` to `3.7` due to `CVE-2024-3651`. This is not a direct dependency so will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#5624](https://github.com/nautobot/nautobot/issues/5624) - Updated `social-auth-app-django` dependency to `~5.4.1` to address `CVE-2024-32879`.
- [#5675](https://github.com/nautobot/nautobot/issues/5675) - Updated `Jinja2` dependency to `3.1.4` to address `CVE-2024-34064`.

## v1.6.20 (2024-04-30)

### Security

- [#5647](https://github.com/nautobot/nautobot/issues/5647) - Fixed a reflected-XSS vulnerability ([GHSA-jxgr-gcj5-cqqg](https://github.com/nautobot/nautobot/security/advisories/GHSA-jxgr-gcj5-cqqg)) in object-list view rendering of user-provided query parameters.

### Fixed

- [#5626](https://github.com/nautobot/nautobot/issues/5626) - Increased performance of `brief=true` in API endpoints by eliminating unnecessary database joins.

## v1.6.19 (2024-04-23)

### Security

- [#5579](https://github.com/nautobot/nautobot/issues/5579) - Updated `sqlparse` to `0.5.0` to fix [GHSA-2m57-hf25-phgg](https://github.com/advisories/GHSA-2m57-hf25-phgg). This is not a direct dependency so it will not auto-update when upgrading Nautobot. Please be sure to update your local environment.

### Fixed

- [#5610](https://github.com/nautobot/nautobot/issues/5610) - Fixed static media failure on `/graphql/` and `/admin/` pages.

## v1.6.18 (2024-04-15)

### Security

- [#5543](https://github.com/nautobot/nautobot/issues/5543) - Updated `jquery-ui` to version `1.13.2` due to `CVE-2022-31160`.

### Dependencies

- [#5543](https://github.com/nautobot/nautobot/issues/5543) - Updated `jquery` to version `3.7.1`.

## v1.6.17 (2024-04-01)

### Dependencies

- [#4583](https://github.com/nautobot/nautobot/issues/4583) - Updated pinned version of `social-auth-core` to remove dependency on `python-jose` & its dependency on `ecdsa`.
- [#5495](https://github.com/nautobot/nautobot/issues/5495) - Changed `jsonschema` version constraint from `>=4.7.0,<4.18.0` to `^4.7.0`.

## v1.6.16 (2024-03-25)

### Security

- [#5450](https://github.com/nautobot/nautobot/issues/5450) - Updated `django` to `~3.2.25` due to `CVE-2024-27351`.
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added requirement for user authentication to access the endpoint `/extras/job-results/<uuid:pk>/log-table/`; furthermore it will not allow an authenticated user to view log entries for a JobResult they don't otherwise have permission to view. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added narrower permissions enforcement on the endpoints `/extras/git-repositories/<str:slug>/sync/` and `/extras/git-repositories/<str:slug>/dry-run/`; a user who has `change` permissions for a subset of Git repositories is no longer permitted to sync or dry-run other repositories for which they lack the appropriate permissions. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added narrower permissions enforcement on the `/api/dcim/connected-device/?peer_device=...&?peer_interface=...` REST API endpoint; a user who has `view` permissions for a subset of interfaces is no longer permitted to query other interfaces for which they lack permissions. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added narrower permissions enforcement on all `<app>/<model>/<lookup>/notes/` UI endpoints; a user must now have the appropriate `extras.view_note` permissions to view existing notes. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added requirement for user authentication to access the REST API endpoints `/api/redoc/`, `/api/swagger/`, `/api/swagger.json`, and `/api/swagger.yaml`. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added requirement for user authentication to access the `/api/graphql` REST API endpoint, even when `EXEMPT_VIEW_PERMISSIONS` is configured. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added requirement for user authentication to access the endpoints `/dcim/racks/<uuid>/dynamic-groups/`, `/dcim/devices/<uuid>/dynamic-groups/`, `/ipam/prefixes/<uuid>/dynamic-groups/`, `/ipam/ip-addresses/<uuid>/dynamic-groups/`, `/virtualization/clusters/<uuid>/dynamic-groups/`, and `/virtualization/virtual-machines/<uuid>/dynamic-groups/`, even when `EXEMPT_VIEW_PERMISSIONS` is configured. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added requirement for user authentication to access the endpoint `/extras/secrets/provider/<str:provider_slug>/form/`. ([GHSA-m732-wvh2-7cq4](https://github.com/nautobot/nautobot/security/advisories/GHSA-m732-wvh2-7cq4))

### Added

- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added `nautobot.apps.utils.get_url_for_url_pattern` and `nautobot.apps.utils.get_url_patterns` lookup functions.
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added `nautobot.apps.views.GenericView` base class.

### Changed

- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added support for `view_name` and `view_description` optional parameters when instantiating a `nautobot.apps.api.OrderedDefaultRouter`. Specifying these parameters is to be preferred over defining a custom `APIRootView` subclass when defining App API URLs.
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added requirement for user authentication by default on the `nautobot.core.api.AuthenticatedAPIRootView` class. As a consequence, viewing the browsable REST API root endpoints (e.g. `/api/`, `/api/circuits/`, `/api/dcim/`, etc.) now requires user authentication.
- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Added requirement for user authentication to access `/api/docs/` and `/graphql/` even when `HIDE_RESTRICTED_UI` is False.

### Fixed

- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Fixed a 500 error when accessing any of the `/dcim/<port-type>/<uuid>/connect/<termination_b_type>/` view endpoints with an invalid/nonexistent `termination_b_type` string.

### Documentation

- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Updated example views in the App developer documentation to include `ObjectPermissionRequiredMixin` or `LoginRequiredMixin` as appropriate best practices.

### Housekeeping

- [#5465](https://github.com/nautobot/nautobot/issues/5465) - Updated custom views in the `example_plugin` to use the new `GenericView` base class as a best practice.

## v1.6.15 (2024-03-18)

### Added

- [#1102](https://github.com/nautobot/nautobot/issues/1102) - Added `CELERY_BEAT_HEARTBEAT_FILE` settings variable.
- [#5424](https://github.com/nautobot/nautobot/issues/5424) - Added `TemplateExtension.list_buttons()` API, allowing apps to register button content to be injected into object list views.

### Fixed

- [#5247](https://github.com/nautobot/nautobot/issues/5247) - Fixed Job buttons do not respect the `task_queues` of the job class.
- [#5354](https://github.com/nautobot/nautobot/issues/5354) - Fixed Configuration Context not applied based on nested Tenant Groups.

### Housekeeping

- [#1102](https://github.com/nautobot/nautobot/issues/1102) - Added health check for Celery Beat based on it touching a file (by default `/tmp/nautobot_celery_beat_heartbeat`) each time its scheduler wakes up.
- [#5434](https://github.com/nautobot/nautobot/issues/5434) - Fixed health check for beat container in `docker-compose.yml` under `docker-compose` v1.x.

## v1.6.14 (2024-03-05)

### Fixed

- [#5387](https://github.com/nautobot/nautobot/issues/5387) - Fixed an error in the Dockerfile that resulted in `pyuwsgi` being installed without SSL support.

## v1.6.13 (2024-03-04)

### Added

- [#4247](https://github.com/nautobot/nautobot/issues/4247) - Added a check to the `nautobot-server pre_migrate` command to identify Interfaces and VMInterfaces with multiple VRFs through IPAddress relationships.

### Fixed

- [#5307](https://github.com/nautobot/nautobot/issues/5307) - Fixed Custom Field form field(s) missing from git repository edit form.
- [#5336](https://github.com/nautobot/nautobot/issues/5336) - Fixed 'docker-compose: command not found' error when running invoke commands.
- [#5345](https://github.com/nautobot/nautobot/issues/5345) - Fixed intermittent 405 errors when using the Docker image with SAML authentication.

### Documentation

- [#5345](https://github.com/nautobot/nautobot/issues/5345) - Added a note to the Nautobot installation documentation about the need to do `pip3 install --no-binary=pyuwsgi` in order to have SSL support in `pyuwsgi`.
- [#5345](https://github.com/nautobot/nautobot/issues/5345) - Added a note to the SSO documentation about the need to do `pip3 install --no-binary=lxml` to avoid incompatibilities between `lxml` and `xmlsec` packages.

## v1.6.12 (2024-02-20)

### Added

- [#5104](https://github.com/nautobot/nautobot/issues/5104) - Added User Token as permission constraints.

### Security

- [#5251](https://github.com/nautobot/nautobot/issues/5251) - Updated `Django` dependency to 3.2.24 due to CVE-2024-24680.

### Changed

- [#5254](https://github.com/nautobot/nautobot/issues/5254) - Changed `TreeQuerySet.ancestors` implementation to a more efficient approach for shallow trees.
- [#5254](https://github.com/nautobot/nautobot/issues/5254) - Changed the location detail view not to annotate tree fields on its queries.

### Fixed

- [#5253](https://github.com/nautobot/nautobot/issues/5253) - Fixed issue with Job Button Groups displaying when Conditional Rendering should remove the button.
- [#5261](https://github.com/nautobot/nautobot/issues/5261) - Fixed a regression introduced in v1.6.8 where Job Buttons would always run with `commit=False`.

## v1.6.11 (2024-02-05)

### Security

- [#5151](https://github.com/nautobot/nautobot/issues/5151) - Updated `pillow` dependency to 10.2.0 due to CVE-2023-50447.

### Added

- [#5169](https://github.com/nautobot/nautobot/issues/5169) - Added support for user session profiling via django-silk.

### Fixed

- [#3664](https://github.com/nautobot/nautobot/issues/3664) - Fixed AssertionError when querying Date type custom fields in GraphQL.
- [#5162](https://github.com/nautobot/nautobot/issues/5162) - Fixed incorrect rack group variable in device template.

## v1.6.10 (2024-01-22)

### Security

- [#5109](https://github.com/nautobot/nautobot/issues/5109) - Removed `/files/get/` URL endpoint (for viewing FileAttachment files in the browser), as it was unused and could potentially pose security issues.
- [#5134](https://github.com/nautobot/nautobot/issues/5134) - Fixed an XSS vulnerability ([GHSA-v4xv-795h-rv4h](https://github.com/nautobot/nautobot/security/advisories/GHSA-v4xv-795h-rv4h)) in the `render_markdown()` utility function used to render comments, notes, job log entries, etc.

### Added

- [#5134](https://github.com/nautobot/nautobot/issues/5134) - Enhanced Markdown-supporting fields (`comments`, `description`, Notes, Job log entries, etc.) to also permit the use of a limited subset of "safe" HTML tags and attributes.

### Changed

- [#5132](https://github.com/nautobot/nautobot/issues/5132) - Updated poetry version for development Docker image to match 2.0.

### Dependencies

- [#5087](https://github.com/nautobot/nautobot/issues/5087) - Updated GitPython to version 3.1.41 to address Windows security vulnerability [GHSA-2mqj-m65w-jghx](https://github.com/gitpython-developers/GitPython/security/advisories/GHSA-2mqj-m65w-jghx).
- [#5087](https://github.com/nautobot/nautobot/issues/5087) - Updated Jinja2 to version 3.1.3 to address to address XSS security vulnerability [GHSA-h5c8-rqwp-cp95](https://github.com/pallets/jinja/security/advisories/GHSA-h5c8-rqwp-cp95).
- [#5134](https://github.com/nautobot/nautobot/issues/5134) - Added `nh3` HTML sanitization library as a dependency.

## v1.6.9 (2024-01-08)

### Fixed

- [#5042](https://github.com/nautobot/nautobot/issues/5042) - Fixed early return conditional in `ensure_git_repository`.

## v1.6.8 (2023-12-21)

### Security

- [#4876](https://github.com/nautobot/nautobot/issues/4876) - Updated `cryptography` to `41.0.7` due to CVE-2023-49083. As this is not a direct dependency of Nautobot, it will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Fixed missing object-level permissions enforcement when running a JobButton ([GHSA-vf5m-xrhm-v999](https://github.com/nautobot/nautobot/security/advisories/GHSA-vf5m-xrhm-v999)).
- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Removed the requirement for users to have both `extras.run_job` and `extras.run_jobbutton` permissions to run a Job via a Job Button. Only `extras.run_job` permission is now required.
- [#5002](https://github.com/nautobot/nautobot/issues/5002) - Updated `paramiko` to `3.4.0` due to CVE-2023-48795. As this is not a direct dependency of Nautobot, it will not auto-update when upgrading. Please be sure to upgrade your local environment.

### Added

- [#4965](https://github.com/nautobot/nautobot/issues/4965) - Added MMF OM5 cable type to cable type choices.

### Removed

- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Removed redundant `/extras/job-button/<uuid>/run/` URL endpoint; Job Buttons now use `/extras/jobs/<uuid>/run/` endpoint like any other job.

### Fixed

- [#4977](https://github.com/nautobot/nautobot/issues/4977) - Fixed early return conditional in `ensure_git_repository`.

### Housekeeping

- [#4988](https://github.com/nautobot/nautobot/issues/4988) - Fixed some bugs in `example_plugin.jobs.ExampleComplexJobButtonReceiver`.

## v1.6.7 (2023-12-12)

### Security

- [#4959](https://github.com/nautobot/nautobot/issues/4959) - Enforce authentication and object permissions on DB file storage views ([GHSA-75mc-3pjc-727q](https://github.com/nautobot/nautobot/security/advisories/GHSA-75mc-3pjc-727q)).

### Added

- [#4873](https://github.com/nautobot/nautobot/issues/4873) - Added QSFP112 interface type to interface type choices.

### Removed

- [#4797](https://github.com/nautobot/nautobot/issues/4797) - Removed erroneous `custom_fields` decorator from InterfaceRedundancyGroupAssociation as it's not a supported feature for this model.
- [#4857](https://github.com/nautobot/nautobot/issues/4857) - Removed Jathan McCollum as a point of contact in `SECURITY.md`.

### Fixed

- [#4142](https://github.com/nautobot/nautobot/issues/4142) - Fixed unnecessary git operations when calling `ensure_git_repository` while the desired commit is already checked out.
- [#4917](https://github.com/nautobot/nautobot/issues/4917) - Fixed slow performance on location hierarchy html template.
- [#4921](https://github.com/nautobot/nautobot/issues/4921) - Fixed inefficient queries in `Location.base_site`.

## v1.6.6 (2023-11-21)

### Security

- [#4833](https://github.com/nautobot/nautobot/issues/4833) - Fixed cross-site-scripting (XSS) potential with maliciously crafted Custom Links, Computed Fields, and Job Buttons (GHSA-cf9f-wmhp-v4pr).

### Changed

- [#4833](https://github.com/nautobot/nautobot/issues/4833) - Changed the `render_jinja2()` API to no longer automatically call `mark_safe()` on the output.

### Fixed

- [#3179](https://github.com/nautobot/nautobot/issues/3179) - Fixed the error that occurred when fetching the API response for CircuitTermination with a cable connected to CircuitTermination, FrontPort, or RearPort.
- [#4799](https://github.com/nautobot/nautobot/issues/4799) - Reduced size of Nautobot `sdist` and `wheel` packages from 69 MB to 29 MB.

### Dependencies

- [#4799](https://github.com/nautobot/nautobot/issues/4799) - Updated `mkdocs` development dependency to `1.5.3`.

### Housekeeping

- [#4799](https://github.com/nautobot/nautobot/issues/4799) - Updated docs configuration for `examples/example_plugin`.
- [#4833](https://github.com/nautobot/nautobot/issues/4833) - Added `ruff` to invoke tasks and CI.

## v1.6.5 (2023-11-13)

### Added

- [#4649](https://github.com/nautobot/nautobot/issues/4649) - Added `device_redundancy_groups` field to `ConfigContextSerializer`.

### Changed

- [#4638](https://github.com/nautobot/nautobot/issues/4638) - Renamed `ltm/1.6` branch to `ltm-1.6`.

### Fixed

- [#4645](https://github.com/nautobot/nautobot/issues/4645) - Fixed a bug where the `failover-strategy` field was required for the device redundancy group api.
- [#4686](https://github.com/nautobot/nautobot/issues/4686) - Fixed incorrect tagging of 1.6.x Docker `nautobot-dev` images as `latest`.
- [#4718](https://github.com/nautobot/nautobot/issues/4718) - Fixed bug in which a device's device redundancy group priority was not being set to `None` when the device redundancy group was deleted.
- [#4728](https://github.com/nautobot/nautobot/issues/4728) - Fixed bug with JobResultFilterSet and ScheduledJobFilterSet using `django_filters.DateTimeFilter` for only exact date matches.
- [#4733](https://github.com/nautobot/nautobot/issues/4733) - Fixed the bug that prevents retrieval of IPAddress using its address args if it was created using `host` and `prefix_length`.

### Housekeeping

- [#4700](https://github.com/nautobot/nautobot/issues/4700) - Removed incorrect `NAUTOBOT_DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT` environment variable reference from settings documentation.

### Security

- [#4671](https://github.com/nautobot/nautobot/issues/4671) - Updated `urllib3` to 2.0.7 due to CVE-2023-45803. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#4748](https://github.com/nautobot/nautobot/issues/4748) - Updated `Django` minimum version to 3.2.23 to protect against CVE-2023-46695.

## v1.6.4 (2023-10-17)

### Added

- [#4361](https://github.com/nautobot/nautobot/issues/4361) - Added `SUPPORT_MESSAGE` configuration setting.
- [#4573](https://github.com/nautobot/nautobot/issues/4573) - Added caching for `display` property of `Location` and `LocationType`, mitigating duplicated SQL queries in the related API views.

### Changed

- [#4313](https://github.com/nautobot/nautobot/issues/4313) - Updated device search to include manufacturer name.

### Housekeeping

- [#4619](https://github.com/nautobot/nautobot/issues/4619) - Fixed broken links in Nautobot README.md.

### Removed

- [#4595](https://github.com/nautobot/nautobot/issues/4595) - Removed `stable` tagging for container builds in LTM release workflow.

## v1.6.3 (2023-10-03)

### Added

- [#3372](https://github.com/nautobot/nautobot/issues/3372) - Added ObjectPermission constraints check to pre_migrate management command.

### Fixed

- [#4396](https://github.com/nautobot/nautobot/issues/4396) - Fixed rack form silently dropping custom field values.

### Housekeeping

- [#4587](https://github.com/nautobot/nautobot/issues/4587) - Fixed `release.yml` and `pre-release.yml` workflow files to target `ci_integration.yml` in its own branch.
- [#4587](https://github.com/nautobot/nautobot/issues/4587) - Enforced changelog requirement in `ci_pullrequest.yml` for `ltm/1.6`.

### Security

- [#4446](https://github.com/nautobot/nautobot/issues/4446) - Updated `GitPython` to `3.1.36` to address `CVE-2023-41040`.

## v1.6.2 (2023-09-01)

### Added

- [#3289](https://github.com/nautobot/nautobot/issues/3289) - Added documentation on factory data caching.
- [#3913](https://github.com/nautobot/nautobot/issues/3913) - Added `url` field to GraphQL objects.
- [#4201](https://github.com/nautobot/nautobot/issues/4201) - Added docs for `InterfaceRedundancyGroup`.
- [#4316](https://github.com/nautobot/nautobot/issues/4316) - Added management command "nautobot-server populate_platform_network_driver" to help update the `Platform.network_driver` field in bulk.
- [#4317](https://github.com/nautobot/nautobot/issues/4317) - Added tests for GraphQL url field.

### Changed

- [#3212](https://github.com/nautobot/nautobot/issues/3212) - Updated Dynamic Group field filter/child group exclusivity error to be more noticeable.
- [#3949](https://github.com/nautobot/nautobot/issues/3949) - Moved DynamicGroup `clean_filter()` call from `clean()` to `clean_fields()`, which has the impact that it will still be called by `full_clean()` and `validated_save()` but no longer called on a simple `clean()`.
- [#4216](https://github.com/nautobot/nautobot/issues/4216) - Changed the rendering of `TagFilterField` to prevent very slow rendering of pages when large numbers of tags are defined.
- [#4217](https://github.com/nautobot/nautobot/issues/4217) - Added a restriction that two Git repositories with the same `remote_url` cannot overlap in their `provided_contents`, as such cases are highly likely to introduce data conflicts.

### Fixed

- [#3949](https://github.com/nautobot/nautobot/issues/3949) - Fixed a ValueError when editing an existing DynamicGroup that has invalid `filter` data.
- [#3949](https://github.com/nautobot/nautobot/issues/3949) - Fixed `DynamicGroup.clean_fields()` so that it will respect an `exclude=["filter"]` kwarg by not validating the `filter` field.
- [#4262](https://github.com/nautobot/nautobot/issues/4262) - Fixed warning message when trying to use bulk edit with no items selected.

### Housekeeping

- [#4331](https://github.com/nautobot/nautobot/issues/4331) - Added a "housekeeping" subsection to the release-notes via `towncrier`.

## v1.6.1 (2023-08-21)

### Changed

- [#4242](https://github.com/nautobot/nautobot/issues/4242) - Changed `development/nautobot_config.py` to disable installation metrics for developer environments by default.
- [#4242](https://github.com/nautobot/nautobot/issues/4242) - Changed behavior of `dev` and `final-dev` Docker images to disable installation metrics by default.

### Fixed

- [#4028](https://github.com/nautobot/nautobot/issues/4028) - Fixed CI integration workflow to publish 'final-dev', and build only `final` images.
- [#4028](https://github.com/nautobot/nautobot/issues/4028) - Fixed CI integration workflow `set-output` warnings.
- [#4093](https://github.com/nautobot/nautobot/issues/4093) - Fixed dependencies required for saml support missing in final docker image.
- [#4149](https://github.com/nautobot/nautobot/issues/4149) - Fixed a bug that prevented renaming a `Rack` if it contained any devices whose names were not globally unique.
- [#4241](https://github.com/nautobot/nautobot/issues/4241) - Added a timeout and exception handling to the `nautobot-server send_installation_metrics` command.
- [#4256](https://github.com/nautobot/nautobot/issues/4256) - Introduced new `mkdocs` setting of `tabbed`.
- [#4256](https://github.com/nautobot/nautobot/issues/4256) - Updated docs at `nautobot/docs/installation/nautobot.md` and `nautobot/docs/installation/http-server.md` to adopt tabbed interfaces.
- [#4258](https://github.com/nautobot/nautobot/issues/4258) - Re-enabled copy-to-clipboard button in mkdocs theme.

## v1.6.0 (2023-08-08)

### Added

- [#4169](https://github.com/nautobot/nautobot/issues/4169) - Added environment variable `NAUTOBOT_SESSION_EXPIRE_AT_BROWSER_CLOSE` to set the `SESSION_EXPIRE_AT_BROWSER_CLOSE` Django setting which expires session cookies when the user closes their browser.
- [#4184](https://github.com/nautobot/nautobot/issues/4184) - Added documentation detailing rack power utilization calculation.

### Dependencies

- [#4208](https://github.com/nautobot/nautobot/issues/4208) - Updated django-rq to 2.8.1.
- [#4209](https://github.com/nautobot/nautobot/issues/4209) - Relaxed constraint on prometheus-client minimum version to `0.14.1`.
- [#4173](https://github.com/nautobot/nautobot/issues/4173) - Updated `drf-spectacular` to `0.26.4`.
- [#4199](https://github.com/nautobot/nautobot/issues/4199) - Updated `cryptography` to `~41.0.3`. As this is not a direct dependency of Nautobot, it will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#4215](https://github.com/nautobot/nautobot/issues/4215) - Broadened the range of acceptable `packaging` dependency versions.

### Fixed

- [#3985](https://github.com/nautobot/nautobot/issues/3985) - Added error handling in `JobResult.log()` for the case where an object's `get_absolute_url()` raises an exception.
- [#3985](https://github.com/nautobot/nautobot/issues/3985) - Added missing `get_absolute_url()` implementation on `CustomFieldChoice` model.
- [#4175](https://github.com/nautobot/nautobot/issues/4175) - Changed custom field clean to not populate null default values.
- [#4204](https://github.com/nautobot/nautobot/issues/4204) - Fixed failing Apps CI by downgrading `jsonschema<4.18`.
- [#4205](https://github.com/nautobot/nautobot/issues/4205) - Fixed failing Apps CI due to missing dependency of `toml`.
- [#4222](https://github.com/nautobot/nautobot/issues/4222) - Fixed a bug in which `Job` `ChoiceVars` could sometimes get rendered incorrectly in the UI as multiple-choice fields.

## v1.6.0-rc.1 (2023-08-02)

### Added

- [#2825](https://github.com/nautobot/nautobot/issues/2825) - Added InterfaceRedundancyGroup and related views, forms, filtersets and table.
- [#3269](https://github.com/nautobot/nautobot/issues/3269) - Added ability to cache `DynamicGroup` memberships in Redis to improve reverse lookup performance.
- [#3269](https://github.com/nautobot/nautobot/issues/3269) - Added ability to cache `ContentType` lookups in Redis to improve performance.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Added support for Python 3.11.
- [#4006](https://github.com/nautobot/nautobot/issues/4006) - Added Markdown custom field type.
- [#4044](https://github.com/nautobot/nautobot/issues/4044) - Added ability to use `@action(detail=True)` decorator for registering additional non-standard `GET` views to a `NautobotUIViewSet`.
- [#4047](https://github.com/nautobot/nautobot/issues/4047) - Added ability for Nautobot to send installation metrics.
- [#4118](https://github.com/nautobot/nautobot/issues/4118) - Added documentation for troubleshooting integration test failures via VNC.
- [#4136](https://github.com/nautobot/nautobot/issues/4136) - Added `network_driver` database field to the `Platform` model.
- [#4136](https://github.com/nautobot/nautobot/issues/4136) - Added `network_driver_mappings` derived attribute on the `Platform` model.
- [#4136](https://github.com/nautobot/nautobot/issues/4136) - Added `CONSTANCE_DATABASE_CACHE_BACKEND = 'default'` to `settings.py`, which should improve performance a bit.
- [#4136](https://github.com/nautobot/nautobot/issues/4136) - Added support for `NETWORK_DRIVERS` config setting to override or extend default network driver mappings from `netutils` library.
- [#4161](https://github.com/nautobot/nautobot/issues/4161) - Enhanced `NautobotUIViewSet` to allow Create and Update methods to have their own form classes.

### Changed

- [#3646](https://github.com/nautobot/nautobot/issues/3646) - Redirect unauthenticated users on all views to login page if `HIDE_RESTRICTED_UI` is True.
- [#3646](https://github.com/nautobot/nautobot/issues/3646) - Only time is shown on the footer if a user is unauthenticated and `HIDE_RESTRICTED_UI` is True.
- [#3693](https://github.com/nautobot/nautobot/issues/3693) - Increased Device model's `asset_tag` size limit to 100.
- [#4029](https://github.com/nautobot/nautobot/issues/4029) - Changed default Python version for Docker images from 3.7 to 3.11.

### Dependencies

- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `celery` dependency to `~5.3.1`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-auth-ldap` optional dependency to `~4.3.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-cacheops` dependency to `~6.2`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-celery-beat` dependency to `~2.5.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-constance` dependency to `~2.9.1`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-cors-headers` dependency to `~4.2.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-cryptography` dependency to `~1.1`. Note that this dependency will be removed in Nautobot 2.0.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-extensions` dependency to `~3.2.3`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-filter` dependency to `~23.1`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-health-check` dependency to `~3.17.0`
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-prometheus` dependency to `~2.3.1`.`
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-redis` dependency to `~5.3.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-storages` optional dependency to `~1.13.2`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-tables2` dependency to `~2.6.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-taggit` dependency to `~4.0.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-timezone-field` dependency to `~5.1`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-tree-queries` dependency to `~0.15.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `drf-spectacular` dependency to `~0.26.3`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `graphene-django` dependency to `~2.16.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `Jinja2` dependency to `~3.1.2`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `jsonschema` dependency to permit versions up to 4.18.x. Note that versions back to 4.7.0 are still permitted, so this dependency may not necessarily auto-upgrade when updating Nautobot.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `MarkupSafe` dependency to `~2.1.3`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `mysqlclient` optional dependency to `~2.2.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `napalm` optional dependency to `~4.1.0`. Note that as a result of this update, the following indirect package dependencies are no longer included by default when installing Nautobot with NAPALM: `ciscoconfparse`, `dnspython`, `loguru`, `passlib`, `tenacity`, `toml`, `win32-setctime`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `packaging` dependency to `~23.1`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `Pillow` dependency to `~10.0.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `prometheus-client` dependency to `~0.17.1`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `social-auth-core` optional dependency to `~4.4.2`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `social-auth-app-django` dependency to `~5.2.0`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated various development-only dependencies to the latest available versions.

### Fixed

- [#4178](https://github.com/nautobot/nautobot/issues/4178) - Fixed JSON serialization of overloaded/non-default FilterForm fields on Dynamic Groups.

### Removed

- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Dropped support for Python 3.7. Python 3.8 is now the minimum version required by Nautobot.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Removed direct dependency on `importlib-metadata`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Removed direct dependency on `pycryptodome` as Nautobot does not currently use this library and hasn't for some time.
