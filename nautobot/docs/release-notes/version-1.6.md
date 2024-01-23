<!-- markdownlint-disable MD024 -->

# Nautobot v1.6

This document describes all new features and changes in Nautobot 1.6.

## Release Overview

### Added

#### Custom Field "Markdown" Type ([#4006](https://github.com/nautobot/nautobot/issues/4006))

A new Custom Field type, "Markdown", has been added. Custom fields of this type can store Markdown-formatted text which will be rendered in the web UI.

#### Caching of Dynamic Groups and Content Types ([#4092](https://github.com/nautobot/nautobot/pull/4092))

APIs have been added to allow for caching of the results of looking up an object's content-type or Dynamic Group memberships, as well as for looking up the members of a Dynamic Group itself. These caches are disabled by default but can be enabled by configuring the [`DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT`](../user-guide/administration/configuration/optional-settings.md#dynamic_groups_member_cache_timeout) and [`CONTENT_TYPE_CACHE_TIMEOUT`](../user-guide/administration/configuration/optional-settings.md#content_type_cache_timeout) settings respectively. Apps (plugins) that make use of dynamic groups should review the [documentation for the APIs](../user-guide/platform-functionality/dynamicgroup.md/#membership-and-caching) to determine how and when to make use of the cache for improved performance.

#### Interface Redundancy Group ([#2825](https://github.com/nautobot/nautobot/issues/2825))

Interface Redundancy Group model and related views have been added to allow logical grouping of multiple interfaces under a specific interface redundancy protocol (HSRP, VRRP, CARP, and etc).

#### Installation Metrics ([#4047](https://github.com/nautobot/nautobot/issues/4047))

A new setting, [`INSTALLATION_METRICS_ENABLED`](../user-guide/administration/configuration/optional-settings.md#installation_metrics_enabled), has been added to allow Nautobot to send anonymous installation metrics to the Nautobot maintainers. This setting is `True` by default but can be changed in `nautobot_config.py` or the `NAUTOBOT_INSTALLATION_METRICS_ENABLED` environment variable.

If the [`INSTALLATION_METRICS_ENABLED`](../user-guide/administration/configuration/optional-settings.md#installation_metrics_enabled) setting is `True`, running the [`post_upgrade`](../user-guide/administration/tools/nautobot-server.md#post_upgrade) or [`send_installation_metrics`](../user-guide/administration/tools/nautobot-server.md#send_installation_metrics) management commands will send a list of all installed [apps](../development/apps/index.md) and their versions, as well as the currently installed Nautobot and Python versions, to the Nautobot maintainers. A randomized UUID will be generated and saved in the [`DEPLOYMENT_ID`](../user-guide/administration/configuration/optional-settings.md#deployment_id) setting to anonymously and uniquely identify each installation. The plugin names will be one-way hashed with SHA256 to further anonymize the data sent. This enables tracking the installation metrics of publicly released apps without disclosing the names of any private apps.

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

The [Platform](../user-guide/core-data-model/dcim/platform.md) model has been enhanced to include a `network_driver` database field and a `network_driver_mappings` derived property based on the [`netutils`](https://netutils.readthedocs.io/en/latest/) library. For example, if you set a Platform to have a `network_driver` value of `"cisco_ios"`, the `platform.network_driver_mappings` property will return a dictionary containing `ansible`, `hier_config`, `napalm`, `netmiko`, `ntc_templates`, `pyats`, `pyntc`, and `scrapli` keys corresponding to this entry. These properties can be referenced via the REST API and GraphQL to assist in developing and maintaining Apps, Jobs, or third-party code that interact with devices by using any of these libraries.

If the default derivations provided by `netutils` are not suitable for your purposes, you can extend or override them by configuring the [`NETWORK_DRIVERS`](../user-guide/administration/configuration/optional-settings.md#network_drivers) system setting.

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

### Security

- [#4671](https://github.com/nautobot/nautobot/issues/4671) - Updated `urllib3` to 2.0.7 due to CVE-2023-45803. This is not a direct dependency so it will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#4748](https://github.com/nautobot/nautobot/issues/4748) - Updated `Django` minimum version to 3.2.23 to protect against CVE-2023-46695.

### Added

- [#4649](https://github.com/nautobot/nautobot/issues/4649) - Added `device_redundancy_groups` field to `ConfigContextSerializer`.

### Fixed

- [#4645](https://github.com/nautobot/nautobot/issues/4645) - Fixed a bug where the `failover-strategy` field was required for the device redundancy group API.
- [#4686](https://github.com/nautobot/nautobot/issues/4686) - Fixed incorrect tagging of 1.6.x Docker `nautobot-dev` images as `latest`.
- [#4718](https://github.com/nautobot/nautobot/issues/4718) - Fixed bug in which a device's device redundancy group priority was not being set to `None` when the device redundancy group was deleted.
- [#4728](https://github.com/nautobot/nautobot/issues/4728) - Fixed bug with JobResultFilterSet and ScheduledJobFilterSet using `django_filters.DateTimeFilter` for only exact date matches.
- [#4733](https://github.com/nautobot/nautobot/issues/4733) - Fixed the bug that prevents retrieval of IPAddress using its address args if it was created using `host` and `prefix_length`.

### Documentation

- [#4700](https://github.com/nautobot/nautobot/issues/4700) - Removed incorrect `NAUTOBOT_DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT` environment variable reference from settings documentation.

### Housekeeping

- [#4638](https://github.com/nautobot/nautobot/issues/4638) - Renamed `ltm/1.6` branch to `ltm-1.6`.

## v1.6.4 (2023-10-17)

### Added

- [#4361](https://github.com/nautobot/nautobot/issues/4361) - Added `SUPPORT_MESSAGE` configuration setting.
- [#4573](https://github.com/nautobot/nautobot/issues/4573) - Added caching for `display` property of `Location` and `LocationType`, mitigating duplicated SQL queries in the related API views.

### Changed

- [#4313](https://github.com/nautobot/nautobot/issues/4313) - Updated device search to include manufacturer name.

### Removed

- [#4595](https://github.com/nautobot/nautobot/issues/4595) - Removed `stable` tagging for container builds in LTM release workflow.

### Housekeeping

- [#4619](https://github.com/nautobot/nautobot/issues/4619) - Fixed broken links in Nautobot README.md.

## v1.6.3 (2023-10-03)

### Security

- [#4446](https://github.com/nautobot/nautobot/issues/4446) - Updated `GitPython` to `3.1.36` to address `CVE-2023-41040`.

### Added

- [#3372](https://github.com/nautobot/nautobot/issues/3372) - Added ObjectPermission constraints check to `pre_migrate` management command.

### Fixed

- [#4396](https://github.com/nautobot/nautobot/issues/4396) - Fixed rack form silently dropping custom field values.

### Housekeeping

- [#4587](https://github.com/nautobot/nautobot/issues/4587) - Fixed `release.yml` and `pre-release.yml` workflow files to target `ci_integration.yml` in its own branch.
- [#4587](https://github.com/nautobot/nautobot/issues/4587) - Enforced changelog requirement in `ci_pullrequest.yml` for `ltm/1.6`.

## v1.6.2 (2023-09-01)

### Added

- [#3913](https://github.com/nautobot/nautobot/issues/3913) - Added `url` field to GraphQL objects.
- [#4316](https://github.com/nautobot/nautobot/issues/4316) - Added management command `nautobot-server populate_platform_network_driver` to help update the `Platform.network_driver` field in bulk.

### Changed

- [#3212](https://github.com/nautobot/nautobot/issues/3212) - Updated Dynamic Group field filter/child group exclusivity error to be more noticeable.
- [#3949](https://github.com/nautobot/nautobot/issues/3949) - Moved DynamicGroup `clean_filter()` call from `clean()` to `clean_fields()`, which has the impact that it will still be called by `full_clean()` and `validated_save()` but no longer called on a simple `clean()`.
- [#4216](https://github.com/nautobot/nautobot/issues/4216) - Changed the rendering of `TagFilterField` to prevent very slow rendering of pages when large numbers of tags are defined.
- [#4217](https://github.com/nautobot/nautobot/issues/4217) - Added a restriction that two Git repositories with the same `remote_url` cannot overlap in their `provided_contents`, as such cases are highly likely to introduce data conflicts.

### Fixed

- [#3949](https://github.com/nautobot/nautobot/issues/3949) - Fixed a ValueError when editing an existing DynamicGroup that has invalid `filter` data.
- [#3949](https://github.com/nautobot/nautobot/issues/3949) - Fixed `DynamicGroup.clean_fields()` so that it will respect an `exclude=["filter"]` kwarg by not validating the `filter` field.
- [#4262](https://github.com/nautobot/nautobot/issues/4262) - Fixed warning message when trying to use bulk edit with no items selected.

### Documentation

- [#3289](https://github.com/nautobot/nautobot/issues/3289) - Added documentation on factory data caching.
- [#4201](https://github.com/nautobot/nautobot/issues/4201) - Added docs for `InterfaceRedundancyGroup`.

### Housekeeping

- [#4317](https://github.com/nautobot/nautobot/issues/4317) - Added tests for GraphQL url field.
- [#4331](https://github.com/nautobot/nautobot/issues/4331) - Added a "housekeeping" subsection to the release-notes via `towncrier`.

## v1.6.1 (2023-08-21)

### Changed

- [#4242](https://github.com/nautobot/nautobot/issues/4242) - Changed behavior of `dev` and `final-dev` Docker images to disable installation metrics by default.

### Fixed

- [#4093](https://github.com/nautobot/nautobot/issues/4093) - Fixed dependencies required for saml support missing in final docker image.
- [#4149](https://github.com/nautobot/nautobot/issues/4149) - Fixed a bug that prevented renaming a `Rack` if it contained any devices whose names were not globally unique.
- [#4241](https://github.com/nautobot/nautobot/issues/4241) - Added a timeout and exception handling to the `nautobot-server send_installation_metrics` command.

### Documentation

- [#4256](https://github.com/nautobot/nautobot/issues/4256) - Introduced new `mkdocs` setting of `tabbed`.
- [#4256](https://github.com/nautobot/nautobot/issues/4256) - Updated docs at `nautobot/docs/installation/nautobot.md` and `nautobot/docs/installation/http-server.md` to adopt tabbed interfaces.
- [#4258](https://github.com/nautobot/nautobot/issues/4258) - Re-enabled copy-to-clipboard button in mkdocs theme.

### Housekeeping

- [#4028](https://github.com/nautobot/nautobot/issues/4028) - Fixed CI integration workflow to publish 'final-dev', and build only `final` images.
- [#4028](https://github.com/nautobot/nautobot/issues/4028) - Fixed CI integration workflow `set-output` warnings.
- [#4242](https://github.com/nautobot/nautobot/issues/4242) - Changed `development/nautobot_config.py` to disable installation metrics for developer environments by default.

## v1.6.0 (2023-08-08)

### Added

- [#4169](https://github.com/nautobot/nautobot/issues/4169) - Added environment variable `NAUTOBOT_SESSION_EXPIRE_AT_BROWSER_CLOSE` to set the `SESSION_EXPIRE_AT_BROWSER_CLOSE` Django setting which expires session cookies when the user closes their browser.

### Fixed

- [#3985](https://github.com/nautobot/nautobot/issues/3985) - Added error handling in `JobResult.log()` for the case where an object's `get_absolute_url()` raises an exception.
- [#3985](https://github.com/nautobot/nautobot/issues/3985) - Added missing `get_absolute_url()` implementation on `CustomFieldChoice` model.
- [#4175](https://github.com/nautobot/nautobot/issues/4175) - Changed custom field clean to not populate null default values.
- [#4204](https://github.com/nautobot/nautobot/issues/4204) - Fixed failing Apps CI by downgrading `jsonschema<4.18`.
- [#4205](https://github.com/nautobot/nautobot/issues/4205) - Fixed failing Apps CI due to missing dependency of `toml`.
- [#4222](https://github.com/nautobot/nautobot/issues/4222) - Fixed a bug in which `Job` `ChoiceVars` could sometimes get rendered incorrectly in the UI as multiple-choice fields.

### Dependencies

- [#4208](https://github.com/nautobot/nautobot/issues/4208) - Updated django-rq to 2.8.1.
- [#4209](https://github.com/nautobot/nautobot/issues/4209) - Relaxed constraint on prometheus-client minimum version to `0.14.1`.
- [#4173](https://github.com/nautobot/nautobot/issues/4173) - Updated `drf-spectacular` to `0.26.4`.
- [#4199](https://github.com/nautobot/nautobot/issues/4199) - Updated `cryptography` to `~41.0.3`. As this is not a direct dependency of Nautobot, it will not auto-update when upgrading. Please be sure to upgrade your local environment.
- [#4215](https://github.com/nautobot/nautobot/issues/4215) - Broadened the range of acceptable `packaging` dependency versions.

### Documentation

- [#4184](https://github.com/nautobot/nautobot/issues/4184) - Added documentation detailing rack power utilization calculation.

## v1.6.0-rc.1 (2023-08-02)

### Added

- [#2825](https://github.com/nautobot/nautobot/issues/2825) - Added InterfaceRedundancyGroup and related views, forms, filtersets and table.
- [#3269](https://github.com/nautobot/nautobot/issues/3269) - Added ability to cache `DynamicGroup` memberships in Redis to improve reverse lookup performance.
- [#3269](https://github.com/nautobot/nautobot/issues/3269) - Added ability to cache `ContentType` lookups in Redis to improve performance.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Added support for Python 3.11.
- [#4006](https://github.com/nautobot/nautobot/issues/4006) - Added Markdown custom field type.
- [#4044](https://github.com/nautobot/nautobot/issues/4044) - Added ability to use `@action(detail=True)` decorator for registering additional non-standard `GET` views to a `NautobotUIViewSet`.
- [#4047](https://github.com/nautobot/nautobot/issues/4047) - Added ability for Nautobot to send installation metrics.
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

### Removed

- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Dropped support for Python 3.7. Python 3.8 is now the minimum version required by Nautobot.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Removed direct dependency on `importlib-metadata`.
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Removed direct dependency on `pycryptodome` as Nautobot does not currently use this library and hasn't for some time.

### Fixed

- [#4178](https://github.com/nautobot/nautobot/issues/4178) - Fixed JSON serialization of overloaded/non-default FilterForm fields on Dynamic Groups.

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
- [#3561](https://github.com/nautobot/nautobot/issues/3561) - Updated `django-prometheus` dependency to `~2.3.1`.
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

### Documentation

- [#4118](https://github.com/nautobot/nautobot/issues/4118) - Added documentation for troubleshooting integration test failures via VNC.
