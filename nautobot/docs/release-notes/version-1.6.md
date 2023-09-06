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

#### Additional HIDE_RESTRICTED_UI Effects for Unauthenticated Users ([#3646](https://github.com/nautobot/nautobot/issues/3646))

When `HIDE_RESTRICTED_UI` is enabled, unauthenticated users are no longer able to view the OpenAPI (Swagger) UI, the GraphiQL UI, or any configured top/bottom banners. Additionally, the page footer on the login page will not display the Nautobot server hostname in this case.

#### Increased `Device.asset_tag` maximum length ([#3693](https://github.com/nautobot/nautobot/issues/3693))

The maximum length of the `Device.asset_tag` field has been increased from 50 to 100 characters.

#### Changed Default Python Version for Docker Images ([#4029](https://github.com/nautobot/nautobot/issues/4029))

The default Python version for Nautobot Docker images has been changed from 3.7 to 3.11.

### Removed

#### Removed Python 3.7 Support ([#3561](https://github.com/nautobot/nautobot/issues/3561))

As Python 3.7 has reached end-of-life, Nautobot 1.6 and later do not support installation or operation under Python 3.7.

<!-- towncrier release notes start -->
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
