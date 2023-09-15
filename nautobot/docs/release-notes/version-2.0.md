<!-- markdownlint-disable MD024 -->

# Nautobot v2.0

This document describes all new features and changes in Nautobot 2.0.

If you are a user migrating from Nautobot v1.X, please refer to the ["Upgrading from Nautobot v1.X"](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md) documentation.

## Release Overview

### Added

#### IPAM Namespaces

The new Namespace model expands on the functionality previously provided by `VRF.enforce_unique` and the `ENFORCE_GLOBAL_UNIQUE` settings flag, both of which have now been removed. Within a namespace, all VRFs, prefixes, and IP addresses must be unique and non-duplicated. For more details please refer to the [documentation](../user-guide/core-data-model/ipam/namespace.md).

#### Generic Role Model ([#1063](https://github.com/nautobot/nautobot/issues/1063))

DeviceRole, RackRole, IPAM Role, and IPAddressRoleChoices have all been merged into a single generic Role model. A role can now be created and associated to one or more of the content-types that previously implemented role as a field. These model content-types include dcim.device, dcim.rack, virtualization.virtualmachine, ipam.ipaddress, ipam.prefix, and ipam.vlan.

#### Added Site Fields to Location ([#2954](https://github.com/nautobot/nautobot/issues/2954))

Added Site Model Fields to Location. Location Model now has `asn`, `comments`, `contact_email`, `contact_name`, `contact_phone`, `facility`, `latitude`, `longitude`, `physical_address`, `shipping_address` and `time_zone` fields.

#### Added Depth REST API Query Parameter

Added the `?depth` query parameter in Nautobot v2.X to replace the `?brief` parameter in the REST API. It enables [nested serialization](https://www.django-rest-framework.org/api-guide/serializers/#specifying-nested-serialization) functionality and offers a more dynamic and comprehensive browsable API. It allows users greater control of the API response data and it is available for both retrieving a single object and a list of objects. This parameter is a positive integer value that can range from 0 to 10. To learn more more, check out the [documentation on the `?depth` query parameter](../user-guide/platform-functionality/rest-api/overview.md/#depth-query-parameter).

#### Natural Key Support Across Nautobot Models ([#2900](https://github.com/nautobot/nautobot/issues/2900))

Nautobot's `BaseModel` base class and related classes now implement automatic support for Django [natural keys](https://docs.djangoproject.com/en/3.2/topics/serialization/#natural-keys) for lookup and referencing, as well as supporting a `composite_key` concept similar to that introduced by `django-natural-keys`. (Nautobot does not depend on `django-natural-keys` but its implementation is heavily inspired by that project.) For example:

<!-- TODO(jathan): Remove this admonition before v2.0.0 final release. -->
!!! warning
    Composite Key will be removed in the final release of Nautobot. Existing references may still exist in RC3.

```python
>>> DeviceType.objects.first().natural_key()
['MegaCorp', 'Model 9000']

>>> DeviceType.objects.get_by_natural_key("MegaCorp", "Model 9000")
<DeviceType: Model 9000>

>>> DeviceType.objects.first().composite_key
'MegaCorp;Model+9000'

>>> DeviceType.objects.get(composite_key="MegaCorp;Model+9000")
<DeviceType: Model 9000>
```

Developers can refer to the [documentation on natural keys](../development/core/natural-keys.md) for details on how to support and use this feature.

Two new configuration settings, [`DEVICE_NAME_AS_NATURAL_KEY`](../user-guide/administration/configuration/optional-settings.md#device_name_as_natural_key) and [`LOCATION_NAME_AS_NATURAL_KEY`](../user-guide/administration/configuration/optional-settings.md#location_name_as_natural_key), have been added to allow an administrator to customize the natural-key behavior of these two widely-used models.

### Changed

#### Aggregate model Migrated to Prefix ([#3302](https://github.com/nautobot/nautobot/issues/3302))

The `ipam.Aggregate` model has been removed and all existing aggregates will be migrated to `ipam.Prefix` with `type` set to "Container". The `Aggregate.date_added` field will be migrated to `Prefix.date_allocated` and changed from a Date field to a DateTime field with the time set to `00:00`. `Aggregate.tenant`, `Aggregate.rir` and `Aggregate.description` will be migrated over to the same fields on `Prefix`.

See the [upgrade guide](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#aggregate-migrated-to-prefix) for more details on the data migration.

#### Collapse Region and Site Models into Location ([#2517](https://github.com/nautobot/nautobot/issues/2517))

##### Initial Data Migration

The `Site` and `Region` models have been removed in v2.0 and have been replaced with `Location` of specific `LocationType`. As a result, the existing `Site` and `Region` data will be migrated to corresponding `LocationType` and `Location` objects. Here is what to expect:

1. If you do not have any `Site` and `Region` instances in your existing database, running this data migration will do nothing.
2. If you only have `Region` instances in your existing database, a `LocationType` named **Region** will be created and for each legacy `Region` instance, a corresponding `Location` instance with the same attributes (`id`, `name`, `description`, etc.) and hierarchy will be created.
3. If you only have `Site` instances in your existing database:

    - A `LocationType` named **Site** will be created and every preexisting root level `LocationType` in your database will be updated to have the new **Site** `LocationType` as their parent.

    - For each legacy `Site` instance, a corresponding `Location` instance with the same attributes (`id`, `name`, `description`, `tenant`, `facility`, `asn`, `latitude`, `longitude`, etc.) will be created, and any preexisting `Locations` in your database will be updated to have the appropriate "site" `Locations` as their parents.

    - Model instances that had a `site` field (`CircuitTermination`, `Device`, `PowerPanel`, `RackGroup`, `Rack`, `Prefix`, `VLANGroup`, `VLAN`, `Cluster`) assigned and *did not* have a `location` attribute assigned will be updated to have their `location` point to the new `Location` corresponding to that `Site`. All other attributes on these models will remain unchanged.

    - Model instances that were previously associated to the `ContentType` for `Site` (`ComputedField`, `CustomField`, `CustomLink`, `ExportTemplate`, `ImageAttachment`, `JobHook`, `Note`, `Relationship`, `Status`, `Tag` and `Webhook`) will have their `ContentType` replaced with `Location`. All other attributes on these models will remain unchanged.

    For Example:

    - We will start with a `Site` instance with name **AMS01** as the base `Site` for two top-level `Location` objects with names **root-01** and **root-02** respectively.

    - During the data migration, a `LocationType` named **Site** will be created, and a `Location` of **Site** `LocationType` named **AMS01** with all the information (`asn`, `latitude`, etc.) from the base `Site` will be created.

    - The `Location` objects named **root-01** and **root-02** will have this **AMS01** `Location` set as their `parent`.

4. If you have both `Site` and `Region` instances in your existing database:

    - A `LocationType` named **Region** will be created.

    - For each legacy `Region` instance, a corresponding `Location` instance with the same attributes (`id`, `name`, `description`, etc.) will be created.

    - A `LocationType` named **Site** will be created with the new `LocationType` named **Region** set as its `parent`.

    - Every pre-existing root-level `LocationType` in your database will be updated to have the new `LocationType` named **Site** as its `parent`.

    - For each legacy `Site` instance, a corresponding "site" `Location` instance with the same attributes (`id`, `name`, `description`, `tenant`, `facility`, `asn`, `latitude`, `longitude`, etc.) will be created with its parent set to the corresponding "region" `Location` if any.

        - If you have `Site` instances in your database without a `Region` assigned to them, one additional `Location` named **Global Region** of `LocationType` **Region** will be created and each `Location` of `LocationType` **Site** created from the legacy region-less `Site` instances will have the **Global Region** `Location` as their parent.

    - Model instances that had a `site` attribute (`CircuitTermination`, `Device`, `Location`, `PowerPanel`, `Rack`, `RackGroup`, `Prefix`, `VLANGroup`, `VLAN`, `Cluster`) assigned and *did not* have a `location` attribute assigned will be updated to have their `location` point to the new `Location` of `LocationType` **Site**. All other attributes on these models will remain unchanged.

    - Model instances that were previously associated to the `ContentType` for `Site`  or `Region` (`ComputedField`, `CustomField`, `CustomLink`, `ExportTemplate`, `ImageAttachment`, `JobHook`, `Note`, `Relationship`, `Status`, `Tag` and `Webhook`) will have their `ContentType` replaced with `Location`. All other attributes on these models will remain unchanged.

    For Example:

    - There are two `Site` instances and one `Region` instance in your existing database. The `Region` with name **America** has one child `Site` instance named **AMS01**. And the other `Site` instance named **AUS01** is not associated with any `Region` (`region` attribute is set to `None`).

    - The `Site` **AMS01** is the base `Site` for two top-level `Location` objects with names **root-01** and **root-02** respectively.

    - During the data migration, a `LocationType` named **Region** and a `Location` of this `LocationType` named **America** with all the same information will be created.

    - The `LocationType` named **Site** with its `parent` set as the new `LocationType` **Region** and a `Location` of `LocationType` named **AMS01** with all the same information (`asn`, `latitude`, etc.) will be created. The `Location` **AMS01** will have `Location` **America** as its `parent` and each - `Location` **root-01** and **root-02** will have `Location` **AMS01** as its `parent`.

    - Finally, the `Site` instance **AUS01**, since it does not have a `Region` instance associated with it, its corresponding `Location` **AUS01** will have a new `Location` named **Global Region** of `LocationType` **Region** as its `parent`.

    - In addition, legacy `Site` instance with name **AMS01** also has three `Device` instances associated with it named **ams01-edge-01**, **ams01-edge-02**,  and **ams01-edge-03**.

    - However, **ams01-edge-01** only has its `site` attribute set as `Site` **AMS01** whereas **ams01-edge-02** and **ams01-edge-03** have both its `site` and `location` attributes set `Site` **AMS01** and `Location` **root-01** respectively.

    - During the data migration, **ams01-edge-01**'s `location` attribute will point to the new `Location` of `LocationType` **Site** with name **AMS01** while devices **ams01-edge-02** and **ams01-edge-03** will remain unchanged.

##### Remove Site and Region Related Fields from Models

`Region` and `Site` relationships are being removed from these models: `CircuitTermination`, `Device`, `Location`, `Rack`, `RackGroup`, `PowerFeed`, `PowerPanel`, `ConfigContext`, `Prefix`, `VLAN`, `VLANGroup`, `Cluster`.

The `ContentType` for `Region` and `Site` are being replaced with `Location` on these models: `ComputedField`, `CustomField`, `CustomLink`, `ExportTemplate`, `ImageAttachment`, `JobHook`, `Note`, `Relationship`, `Status`, `Tag` and `Webhook`.

The `region` and `site` fields are being removed in the `filter` data of `DynamicGroup` objects. The previously associated values are being added to the existing `location` field and its associated list of filter values or to a new `location` key with an empty list if one does not exist.

Check out the API and UI endpoints changes incurred by the changes stated above in the ["Upgrading from Nautobot v1.X"](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md) guide.

Check out the [Region and Site Related Data Model Migration Guide](../user-guide/administration/upgrading/from-v1/region-and-site-data-migration-guide.md#region-and-site-related-data-model-migration-guide-for-existing-nautobot-app-installations) to learn how to migrate your Nautobot Apps and data models from `Site` and `Region` to `Location`.

#### Collapsed `nautobot.utilities` into `nautobot.core` ([#2721](https://github.com/nautobot/nautobot/issues/2721))

`nautobot.utilities` no longer exists as a separate Python module or Django app. Its functionality has been collapsed into the `nautobot.core` app. See details at [Python Code Location Changes](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#python-code-location-changes).

#### REST API Versioning Behavior ([#2799](https://github.com/nautobot/nautobot/issues/2799))

In Nautobot 2.0 and later, the REST API defaults, when the caller doesn't request a specific API version, to using the latest available version of the REST API. This is a change from Nautobot 1.x, where the default behavior was to use the 1.2 version of the REST API even when newer versions were available.

#### Revamped CSV Import and Export ([#2569](https://github.com/nautobot/nautobot/issues/2569), [#3715](https://github.com/nautobot/nautobot/issues/3715))

Exporting objects and lists of objects to CSV format has been totally reimplemented in a new framework for ease of use and maintainability. Instead of accessing `http://nautobot/<app>/<model>/?export` you will now use the URL pattern `http://nautobot/api/<app>/<model>/?format=csv`, as the new CSV renderer is based on the REST API serializer definitions. This results in substantially more comprehensive CSV representations of many models.

Conversely, importing objects from CSV format has also been reimplemented in the same new framework. The REST API can now accept CSV files as well as the existing JSON support, and the UI for importing CSVs uses this same framework behind the scenes.

An immediate benefit you can notice from this reimplementation is that CSVs should now **generally** be "round-trip" capable, meaning that you can export a set of records to CSV format and then import that CSV into a different Nautobot instance (or delete the records and use the CSV to recreate them) without needing to "massage" the CSV into a different set of columns or fields.

In addition to the above improvements, you can now reference related objects in your CSV by using a combination of unique fields. For instance:

Instead of:

```csv
name,rack
Device one,7f3ca431-8103-45cc-a9ce-b94c1f784a1d
```

you can use:

```csv
name,rack__location__name,rack__name
Device one,Equinix DC6,R204
```

This enhancement allows you to specify related objects using their unique attributes, making data import even more intuitive and flexible.

#### Renamed Database Foreign Keys and Related Names ([#2520](https://github.com/nautobot/nautobot/issues/2520))

Some Foreign Key fields have been renamed to follow a more self-consistent pattern across the Nautobot app. This change is aimed to offer more clarity and predictability when it comes to related object database operations:

For example in v1.x to create a circuit object with `type` "circuit-type-1", you would do:

```python
Circuit.objects.create(
    cid="Circuit 1",
    provider="provider-1",
    type="circuit-type-1",
    status="active",
)
```

and to filter `Circuit` objects of `type` "circuit-type-2", you would do:

```python
Circuit.objects.filter(type="circuit-type-2")
```

Now in v2.x, we have renamed the Foreign Key field `type` on Circuit Model to `circuit_type`, because this naming convention made it clearer that this Foregin Key field is pointing to the model `CircuitType`. The same operations would look like:

```python
Circuit.objects.create(
    cid="Circuit 1",
    provider="provider-1",
    circuit_type="circuit-type-1",
    status="active",
)
```

```python
Circuit.objects.filter(circuit_type="circuit-type-2")
```

Check out more Foreign Key related changes documented in the table [Renamed Database Fields](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#renamed-database-fields)

In addition to the changes made to Foreign Key fields' own names, some of their `related_names` are also renamed:

For example in v1.x, to query `Circuit` objects with `CircuitTermination` instances located in sites ["ams01", "ams02", "atl03"], you would do:

```python
Circuit.objects.filter(terminations__site__in=["ams01", "ams02", "atl03"])
```

Now in v2.x, we have renamed the Foreign Key field `circuit`'s `related_name` attribute `terminations` on `CircuitTermination` Model to `circuit_terminations`, the same operations would look like:

```python
Circuit.objects.filter(circuit_terminations__site__in=["ams01", "ams02", "atl03"])
```

Check out more `related-name` changes documented in the table [Renamed Database Fields](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#renamed-database-fields)

#### Renamed Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

Some filter fields have been renamed to reflect their functionalities better.

For example in v1.X, to filter `FrontPorts` that has a cable attached in the UI or make changes to them via Rest API, you would use the `cabled` filter:

`/dcim/front-ports/?cabled=True`

Now in v2.x, you would instead use the `has_cable` filter which has a more user-friendly name:

`/dcim/front-ports/?has_cable=True`

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#renamed-filter-fields)

#### Enhanced Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

Many filter fields have been enhanced to enable filtering by both names and UUID primary keys.

For example in v1.X, to filter `RackGroups` with a specific `parent` value in the UI or make changes to them via the REST API, you could only to input slugs as the filter values:

`/dcim/rack-groups/?parent=<slug>`

Now in v2.x, you are able to filter those `RackGroups` by their parent(s) names or UUID primary keys:

`/dcim/rack-groups/?parent=<name>` or `/dcim/rack-groups/?parent=<uuid>`

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#enhanced-filter-fields)

#### Corrected Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

There were also instances where a foreign-key related field (e.g. `console_ports`) was incorrectly mapped to a boolean membership filter (e.g. `has_console_ports`), making it impossible to filter based on specific values of the foreign key:

For example in v1.x:

`/dcim/devices/?console_ports=True` and `/dcim/devices/?has_console_ports=True` are functionally the same and this behavior is **incorrect**.

This has been addressed in v2.x as follows:

`console_ports` and similar filters are taking foreign key UUIDs as input values and can be used in this format: `/dcim/devices/?console_ports=<uuid>` whereas `has_console_ports` and similar filters remain the same.

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#corrected-filter-fields)

#### Generic Role Model ([#1063](https://github.com/nautobot/nautobot/issues/1063))

The `DeviceRole`, `RackRole`, `ipam.Role`, and `IPAddressRoleChoices` have all been removed and replaced with a `extras.Role` model, This means that all references to any of the replaced models and choices now points to this generic role model.

In addition, the `role` field of the `IPAddress` model has also been changed from a choice field to a foreign key related field to the `extras.Role` model.

#### Prefix `is_pool` field and "Container" status replaced by new field `Prefix.type` ([#1362](https://github.com/nautobot/nautobot/issues/1362))

A new `type` field was added to `Prefix` to replace the `is_pool` boolean field and the "Container" status. The `type` field can be set to "Network", "Pool" or "Container", with "Network" being the default.

Existing prefixes with a status of "Container" will be migrated to the "Container" type. Existing prefixes with `is_pool` set will be migrated to the "Pool" type. Prefixes with both `is_pool` set and a status of "Container" will be migrated to the "Pool" type.

The "Container" status will be removed and all prefixes will be migrated to the "Active" status if it exists. If the "Active" status was deleted, prefixes will be migrated to the first available prefix status in the database that is not "Container".

### Removed

#### Removed Brief REST API Query Parameter

Support for `?brief` REST API query parameter and `Nested*Serializers` have been removed in Nautobot v2.X. They are replaced by the new [`?depth` query parameter](../user-guide/platform-functionality/rest-api/overview.md/#depth-query-parameter).

#### Removed `django-cacheops` ([#1721](https://github.com/nautobot/nautobot/issues/1721))

Nautobot no longer uses `django-cacheops` for caching of database queries or other information. In some cases this has been replaced by the use of Django's native Redis caching capabilities.

The configuration settings `CACHEOPS`, `CACHEOPS_DEFAULTS`, `CACHEOPS_DEGRADE_ON_FAILURE`, `CACHEOPS_ENABLED`, `CACHEOPS_HEALTH_CHECK_ENABLED`, `CACHEOPS_REDIS`, etc. are now unused by Nautobot and may be removed from your configuration.

#### Removed Redundant Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

As a part of breaking changes made in v2.X, shadowed filter/filterset fields are being removed throughout Nautobot.

In Nautobot 1.x, for some of the foreign-key related fields:
    - The field was shadowed for the purpose of replacing the PK filter with a lookup-based on a more human-readable value (typically `slug`, if available).
    - A PK-based filter was available as well, generally with a name suffixed by `_id`

Now these two filter fields will be replaced by a single filter field that can support both names and UUID primary keys as inputs; As a result, PK-based filters suffixed by `_id` will no longer be supported in v2.0.

For example in v1.X, to filter `Circuits` with a specific `provider` value in the UI or make changes to them via the REST API with a UUID primary key, you would use:

`/circuits/circuits/?provider_id=<uuid>`

Now in v2.x, that format is no longer supported. Instead, you would use:

`/circuits/circuits/?provider=<uuid>`

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.md#removed-redundant-filter-fields)

#### Removed RQ support ([#2523](https://github.com/nautobot/nautobot/issue/2523))

Support for RQ and `django-rq`, deprecated since Nautobot 1.1.0, has been fully removed from Nautobot 2.0.

<!-- towncrier release notes start -->
## v2.0.0-rc.3 (2023-09-15)

### Added

- [#3289](https://github.com/nautobot/nautobot/issues/3289) - Added documentation on factory data caching and generic filter tests.
- [#3372](https://github.com/nautobot/nautobot/issues/3372) - Added documentation for migrating permission constraints.
- [#3934](https://github.com/nautobot/nautobot/issues/3934) - Added `Namespace` column to `VRFDeviceAssignmentTable` and `VRFPrefixAssignmentTable` to display assigned VRFs' `namespace` property.
- [#3934](https://github.com/nautobot/nautobot/issues/3934) - Added `namespace` attribute to rendering of "IP Addresses" columns of relevant `Interface` and `InterfaceRedundancyGroup` tables.
- [#3934](https://github.com/nautobot/nautobot/issues/3934) - Added `namespace` attribute to rendering of `primary_ip` fields in `DeviceDetailView` and `VirtualMachineDetailView`.
- [#3934](https://github.com/nautobot/nautobot/issues/3934) - Added hover copy button and functionality to `primary_ip` field in `VirtualMachineDetailView`.
- [#4011](https://github.com/nautobot/nautobot/issues/4011) - Added redirect in new UI to legacy UI if the page being visited is not new UI ready.
- [#4249](https://github.com/nautobot/nautobot/issues/4249) - Added REST API endpoint for the IPAddressToInterface model.
- [#4249](https://github.com/nautobot/nautobot/issues/4249) - Added section on many-to-many relationships in the REST API overview docs.
- [#4303](https://github.com/nautobot/nautobot/issues/4303) - Added documentation on identifying objects after the removal of slug fields.
- [#4326](https://github.com/nautobot/nautobot/issues/4326) - Update documentation on Nautobot release workflow.
- [#4346](https://github.com/nautobot/nautobot/issues/4346) - Implemented `.natural_slug` property on all models.

### Changed

- [#2821](https://github.com/nautobot/nautobot/issues/2821) - Adds navigation.footer to mkdocs features to enable navigation in the footer.
- [#2821](https://github.com/nautobot/nautobot/issues/2821) - Updates installation documentation into a single path, using tabs for MySQL/PostgeSQL & Ubuntu/Debian/RHEL.
- [#2821](https://github.com/nautobot/nautobot/issues/2821) - Removes centos.md and ubuntu.md as these are collapsed into single `install_system.md` file.
- [#2821](https://github.com/nautobot/nautobot/issues/2821) - Updates docker-compose standalone to docker compose plugin to assist in development environment.
- [#4012](https://github.com/nautobot/nautobot/issues/4012) - Disable non ready Model View in new-ui sidebar.
- [#4015](https://github.com/nautobot/nautobot/issues/4015) - Refined new-UI IPAddress detail view.
- [#4017](https://github.com/nautobot/nautobot/issues/4017) - Refined new-UI DeviceType detail view.
- [#4017](https://github.com/nautobot/nautobot/issues/4017) - Moved `object_type` to the Advanced tab of new-UI detail views in general.
- [#4019](https://github.com/nautobot/nautobot/issues/4019) - Refine new-ui Location Detail view.
- [#4333](https://github.com/nautobot/nautobot/issues/4333) - Updated Dockerfile not to use Python virtual environment.
- [#4338](https://github.com/nautobot/nautobot/issues/4338) - Updated GitHub CI integration workflow for Long-term maintenance branch.
- [#4429](https://github.com/nautobot/nautobot/issues/4429) - Updated the pylint-nautobot migration steps.
- [#4440](https://github.com/nautobot/nautobot/issues/4440) - Fixed an issues with ModelForm's that used `__all__`  on `Meta.fields` and `custom_fields` displayed a JSON blob.

### Fixed

- [#3934](https://github.com/nautobot/nautobot/issues/3934) - Fixed validation logic for VirtualMachine primary ips.
- [#4010](https://github.com/nautobot/nautobot/issues/4010) - Fixed error not being raised when an invalid parent is provided to the IPAddress in both the API and ORM.
- [#4293](https://github.com/nautobot/nautobot/issues/4293) - Fixed the issue of ObjectChange Detail View not rendering in the new UI.
- [#4307](https://github.com/nautobot/nautobot/issues/4307) - Fixed incorrect hyperlinks that exist in the Notes and ChangeLog Tables in the ObjectDetailView of the new UI.
- [#4329](https://github.com/nautobot/nautobot/issues/4329) - Fixed an issue in `TreeNodeMultipleChoiceFilter` filtering that could result in incorrect inclusion of unrelated records with the same name located elsewhere in the tree.
- [#4377](https://github.com/nautobot/nautobot/issues/4377) - Fixed incorrect OpenAPI schema for filters available on Device and VirtualMachine REST API endpoints.
- [#4377](https://github.com/nautobot/nautobot/issues/4377) - Fixed incorrect logic for queryset annotation on Device and VirtualMachine REST API views.
- [#4388](https://github.com/nautobot/nautobot/issues/4388) - Fixed a bug that makes ConfigContexts applied to parent locations missing from rendered config context of child location Devices/Virtual Machines.
- [#4407](https://github.com/nautobot/nautobot/issues/4407) - Fixed Dockerfile Node.js `setup_XX.x` [deprecated script](https://github.com/nodesource/distributions#new-update-%EF%B8%8F).

### Housekeeping

- [#4310](https://github.com/nautobot/nautobot/issues/4310) - Updated CI integration workflow to remove some redundant tests, run more tests in parallel and remove arm64 platform from the container build.
- [#4311](https://github.com/nautobot/nautobot/issues/4311) - Updated CI pull request workflow for `next` branch to remove some redundant tests, run more tests in parallel and test the container build.
- [#4409](https://github.com/nautobot/nautobot/issues/4409) - Updated upstream testing workflow for apps to test against LTM and 2.0 with `ltm-1.6` and `develop` branch tags respectively.

### Removed

- [#3934](https://github.com/nautobot/nautobot/issues/3934) - Removed `ip_family` queryset annotation from `PrefixQuerySet` and `IPAddressQuerySet`.
- [#4011](https://github.com/nautobot/nautobot/issues/4011) - Removed the "disable menu" feature for non-NewUI ready menu links in the sidebar and NavBar.
- [#4015](https://github.com/nautobot/nautobot/issues/4015) - Removed `tags`, `custom-fields`, `computed-fields`, `relationships` from new-UI object detail
- [#4017](https://github.com/nautobot/nautobot/issues/4017) - Removed `notes_url` from new-UI object detail views.

### Security

- [#3880](https://github.com/nautobot/nautobot/issues/3880) - Updated `GitPython` to `3.1.36` to address `CVE-2023-41040`.

## v2.0.0.rc-2 (2023-08-24)

### Added

- [#3794](https://github.com/nautobot/nautobot/issues/3794) - Added support for multi-column keys for CSV Import.

### Changed

- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Renamed `IPAddress` `vrf` filter to `vrfs`.
- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Renamed `Prefix` `mask_length` filter to `prefix_length` and `vrf` filter to `vrfs`.
- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Enhanced `Prefix` `vlan_vid` filter to permit multiple query values.
- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Renamed `RouteTarget` `exporting_vrf` filter to `exporting_vrfs` and `importing_vrf` filter to `importing_vrfs`.
- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Renamed `Service` `port` filter to `ports`.
- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Renamed `VRF` `export_target` filter to `export_targets` and `import_target` filter to `import_targets`.
- [#2853](https://github.com/nautobot/nautobot/issues/2853) - Renamed `JobView` to `JobRunView` and `JobDetailView` to `JobView`.
- [#2853](https://github.com/nautobot/nautobot/issues/2853) - Rename url lookups `job` to `job_run_by_class_path` and `job_detail` to `job`.
- [#2853](https://github.com/nautobot/nautobot/issues/2853) - Changed `as_form_class`, `as_form` and `validate_data` functions on BaseJob Model to `classmethods`.
- [#4305](https://github.com/nautobot/nautobot/issues/4305) - Merged develop back into next after release 1.6.1

### Fixed

- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Fixed misnamed `tag` fields on various filter forms (correct filter name is now `tags`).
- [#4299](https://github.com/nautobot/nautobot/issues/4299) - Added missing `to_field_name` attribute on `TagFilterField`, which was causing dynamic-group filtering failures.
- [#4300](https://github.com/nautobot/nautobot/issues/4300) - Fixed a permission issue when using `final-dev` containers by switching to root user before exposing port and entrypoint.

### Removed

- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Removed `RouteTarget` `exporting_vrf_id` and `importing_vrf_id` filters as they are redundant with the `exporting_vrfs` and `importing_vrfs` filters.
- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Removed `Service` `device_id` and `virtual_machine_id` filters as they are redundant with the `device` and `virtual_machine` filters.
- [#2807](https://github.com/nautobot/nautobot/issues/2807) - Removed `VRF` `export_target_id` and `import_target_id` filters as they are redundant with the `export_targets` and `import_targets` filters.
- [#2853](https://github.com/nautobot/nautobot/issues/2853) - Removed `/extras/jobs/results/<uuid:pk>/` URL endpoint.

## v2.0.0rc1 (2023-08-18)

### Added

- [#1175](https://github.com/nautobot/nautobot/issues/1175) - Added "Submit Feedback" functionality to the new UI.
- [#3330](https://github.com/nautobot/nautobot/issues/3330) - Added UI configuration documentation.
- [#3386](https://github.com/nautobot/nautobot/issues/3386) - Added documentation linking to best practices for database backup.
- [#3386](https://github.com/nautobot/nautobot/issues/3386) - Added missing files to the documentation table of contents.
- [#3387](https://github.com/nautobot/nautobot/issues/3387) - Added an app developer migration guide on how to upgrade an Nautobot App from v1.x to v2.0.
- [#3394](https://github.com/nautobot/nautobot/issues/3394) - Added Developer migration guide.
- [#3582](https://github.com/nautobot/nautobot/issues/3582) - The 'GetFilterSetFieldDOMElementAPIView' now has the option to return the filterset field's DOM element in JSON format.
- [#3690](https://github.com/nautobot/nautobot/issues/3690) - Added an IPAM Migration Guide for users upgrading to Nautobot 2.0.
- [#3904](https://github.com/nautobot/nautobot/issues/3904) - Added Input component for changing the page number, in addition to using the arrows.
- [#3904](https://github.com/nautobot/nautobot/issues/3904) - Added total number of rows to footer.
- [#3976](https://github.com/nautobot/nautobot/issues/3976) - Added support for related-object specification by PK (UUID) in CSV imports as an alternative to composite-keys.
- [#3976](https://github.com/nautobot/nautobot/issues/3976) - Added support for related-object specification by composite-key in JSON REST API data.
- [#3977](https://github.com/nautobot/nautobot/issues/3977) - Added `DEVICE_NAME_AS_NATURAL_KEY` and `LOCATION_NAME_AS_NATURAL_KEY` optional config settings to allow the use of simplified natural keys for Device and Location models.
- [#3978](https://github.com/nautobot/nautobot/issues/3978) - Added data migration for JobResult to migrate old status to its equivalent new status.
- [#3983](https://github.com/nautobot/nautobot/issues/3983) - Added `FiltersPanel` UI component.
- [#4042](https://github.com/nautobot/nautobot/issues/4042) - Added additional documentations and references for how CustomField, ComputedField, and Relationship behave in Nautobot v2.0.
- [#4052](https://github.com/nautobot/nautobot/issues/4052) - Added the option for models to specify a `documentation_static_path` attribute if a non-default path is needed.
- [#4081](https://github.com/nautobot/nautobot/issues/4081) - Added data migration to ensure `Note` objects' `created` timestamps are unique.
- [#4091](https://github.com/nautobot/nautobot/issues/4091) - Added information about installing and running Node.js as a part of the Nautobot installation documentation.
- [#4100](https://github.com/nautobot/nautobot/issues/4100) - Added columns for interface count, device count, VM interface count and virtual machine count to the IP address list view.
- [#4154](https://github.com/nautobot/nautobot/issues/4154) - Added handleOnKeyDown to Pagination to now update the page number when Enter key is pressed.
- [#4154](https://github.com/nautobot/nautobot/issues/4154) - Added double arrow icons to Pagination for navigating to first/last page.
- [#4197](https://github.com/nautobot/nautobot/issues/4197) - Added Bulk Import View for Namespace.
- [#4225](https://github.com/nautobot/nautobot/issues/4225) - Added Namespace to IPAddressDetailTable.
- [#4228](https://github.com/nautobot/nautobot/issues/4228) - Incorporated all code changes from Nautobot 1.6.0.

### Changed

- [#3229](https://github.com/nautobot/nautobot/issues/3229) - Rename JobResult.data to JobResult.result and delete the original JobResult.result.
- [#3636](https://github.com/nautobot/nautobot/issues/3636) - Reintroduced "Assign IP Address" button to Device Interfaces list view.
- [#3892](https://github.com/nautobot/nautobot/issues/3892) - Removed `logger` kwarg from `JobResult.log()`. Jobs' `self.logger` logging instance automatically logs to both the console and database and should be used instead of this method.
- [#3892](https://github.com/nautobot/nautobot/issues/3892) - Changed the function signatures for `nautobot.extras.datasources.git` methods `get_repo_from_url_to_path_and_from_branch`, `ensure_git_repository`, `git_repository_dry_run`, `import_config_context`, `import_local_config_context`, and `import_config_context_schema`.
- [#3904](https://github.com/nautobot/nautobot/issues/3904) - Restyled the pagination section.
- [#3904](https://github.com/nautobot/nautobot/issues/3904) - Modified the back "<" and next ">" arrows to navigate to the previous/next page, respectively, rather than the first/last page.
- [#3904](https://github.com/nautobot/nautobot/issues/3904) - The back "<" and next ">" arrows no longer show when they aren't relevant (i.e. when on the first/last page).
- [#3904](https://github.com/nautobot/nautobot/issues/3904) - Changed Pagination component from Class to function.
- [#3906](https://github.com/nautobot/nautobot/issues/3906) - Changed visual loading behavior of object list views in new UI.
- [#3928](https://github.com/nautobot/nautobot/issues/3928) - Updated settings documentation for Nautobot 2.0 Celery changes.
- [#3972](https://github.com/nautobot/nautobot/issues/3972) - Changed the natural-key for `ComponentModel` to `["name", "device"]`.
- [#3972](https://github.com/nautobot/nautobot/issues/3972) - Re-ordered the natural-key fields for `PowerOutlet` and `PowerPanel`.
- [#3972](https://github.com/nautobot/nautobot/issues/3972) - Changed the natural-key fields for `Cable`, `CablePath`, and `TaggedItem` to merely "pk".
- [#3972](https://github.com/nautobot/nautobot/issues/3972) - Changed the natural-key for `RackReservation` to `["units", "racks"]`.
- [#3972](https://github.com/nautobot/nautobot/issues/3972) - Changed the natural-key of `VirtualChassis` to "name".
- [#3976](https://github.com/nautobot/nautobot/issues/3976) - Moved `NautobotHyperlinkedRelatedField` from `nautobot.core.api.serializers` to `nautobot.core.api.fields`.
- [#4013](https://github.com/nautobot/nautobot/issues/4013) - Refined the Device Detail View in the New UI.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Changed development `nodejs` Docker container to use Nautobot `dev` image instead of generic `node` image.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Changed the `dev` and `final-dev` Docker images to install and run Nautobot as a `nautobot` user instead of as `root`.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Updated `poetry` version included in `dev` and `final-dev` Docker images from 1.3.1 to 1.5.1.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Updated `markdownlint-cli` to version 0.35.0.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Changed all Docker images to install Nautobot and its dependencies to a virtualenv in `/opt/nautobot/` instead of the system Python.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Changed Docker build to install dependencies for and then build the new UI as a separate set of stages from the installation of Python dependencies and build of the Python package.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Consolidated development/non-development `package.json` and `package-lock.json` files into a single set of files.
- [#4164](https://github.com/nautobot/nautobot/issues/4164) - Modified docker dev stage to run as root user to prevent permission issues with bind mounts.
- [#4242](https://github.com/nautobot/nautobot/issues/4242) - Changed `development/nautobot_config.py` to disable installation metrics for developer environments by default.
- [#4242](https://github.com/nautobot/nautobot/issues/4242) - Changed behavior of `dev` and `final-dev` Docker images to disable installation metrics by default.

### Dependencies

- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Added support for Python 3.11.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `django-auth-ldap` optional dependency to `~4.3.0`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `django-cors-headers` dependency to `~4.2.0`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `django-storages` optional dependency to `~1.13.2`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `django-tables2` dependency to `~2.6.0`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `django-tree-queries` dependency to `~0.15.0`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `drf-spectacular` dependency to `~0.26.3`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `napalm` optional dependency to `~4.1.0`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `Pillow` dependency to `~10.0.0`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `prometheus-client` dependency to `~0.17.1`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated `social-auth-core` optional dependency to `~4.4.2`.
- [#4125](https://github.com/nautobot/nautobot/issues/4125) - Updated various development-only dependencies to the latest available versions.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `celery` dependency to `~5.3.1`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `django-celery-beat` dependency to `~2.5.0`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `django-constance` dependency to `~2.9.1`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `django-extensions` dependency to `~3.2.3`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `django-prometheus` dependency to `~2.3.1`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `django-redis` dependency to `~5.3.0`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `django-taggit` dependency to `~4.0.0.`
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `django-timezone-field` dependency to `~5.1`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `GitPython` dependency to `~3.1.32`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `graphene-django` dependency to `~2.16.0`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `Jinja2` dependency to `~3.1.2`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `jsonschema` dependency to permit versions up to 4.18.x. Note that versions back to 4.7.0 are still permitted, so this dependency may not necessarily auto-upgrade when updating Nautobot.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `MarkupSafe` dependency to `~2.1.3`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `mysqlclient` optional dependency to `~2.2.0`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `packaging` dependency to `~23.1`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated `psycopg2-binary` dependency to `~2.9.6`.
- [#4143](https://github.com/nautobot/nautobot/issues/4143) - Updated various development-only dependencies to the latest available versions.

### Fixed

- [#3904](https://github.com/nautobot/nautobot/issues/3904) - Added proper spacing/alignment to pagination section.
- [#3974](https://github.com/nautobot/nautobot/issues/3974) - Corrected the natural-key definitions for `ComputedField`, `CustomField`, `FileAttachment`, `ImageAttachment`, `ObjectChange`, `Relationship`, `RelationshipAssociation`, and `Token` models.
- [#3976](https://github.com/nautobot/nautobot/issues/3976) - Fixed an error when creating `VRF` or `Prefix` records via the REST API without specifying a `namespace` value.
- [#4013](https://github.com/nautobot/nautobot/issues/4013) - Fixed incorrect related model url rendering in ObjectRetrieve view.
- [#4028](https://github.com/nautobot/nautobot/issues/4028) - Fixed CI integration workflow to publish 'final-dev', and build only `final` images.
- [#4028](https://github.com/nautobot/nautobot/issues/4028) - Fixed CI integration workflow `set-output` warnings.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Fixed error when running 'invoke markdownlint' with Docker Compose workflow.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Fixed a few broken links in the documentation.
- [#4083](https://github.com/nautobot/nautobot/issues/4083) - Fixed a issue that was causing the build process of react to be slow.
- [#4100](https://github.com/nautobot/nautobot/issues/4100) - Fixed `assigned` column in the IP address list view.
- [#4115](https://github.com/nautobot/nautobot/issues/4115) - Fixed missing data validation in `IPAddressForm` and `PrefixForm`.
- [#4124](https://github.com/nautobot/nautobot/issues/4124) - Fixed inability to start `nodejs` development container due to missing files.
- [#4131](https://github.com/nautobot/nautobot/issues/4131) - Fixed inability to filter most models with `.exclude(composite_key="...")`.
- [#4131](https://github.com/nautobot/nautobot/issues/4131) - Fixed inability to call `Prefix.objects.exclude(prefix="...")`.
- [#4131](https://github.com/nautobot/nautobot/issues/4131) - Fixed inability to call `IPAddress.objects.exclude(address="...")`.
- [#4149](https://github.com/nautobot/nautobot/issues/4149) - Fixed a bug that prevented renaming a `Rack` if it contained any devices whose names were not globally unique.
- [#4154](https://github.com/nautobot/nautobot/issues/4154) - Added useEffect to fix the last_page in Pagination from not updating dynamically.
- [#4241](https://github.com/nautobot/nautobot/issues/4241) - Added a timeout and exception handling to the `nautobot-server send_installation_metrics` command.
- [#4254](https://github.com/nautobot/nautobot/issues/4254) - Fixed CI container builds failing on `npm install` steps.
- [#4285](https://github.com/nautobot/nautobot/issues/4285) - Fixed `next` container build workflow.

### Removed

- [#3761](https://github.com/nautobot/nautobot/issues/3761) - Remove remaining `Site` and `Region` references from core docs.
- [#3892](https://github.com/nautobot/nautobot/issues/3892) - Removed unused method `get_job_result_and_repository_record` in `nautobot.extras.datasources.git`.
- [#4061](https://github.com/nautobot/nautobot/issues/4061) - Removed `node_modules` shared volume from Docker development environment as no longer needed.
- [#4104](https://github.com/nautobot/nautobot/issues/4104) - Removed unused `primary_for_device` from Interface data migration.
- [#4115](https://github.com/nautobot/nautobot/issues/4115) - Removed temporary code from `ObjectEditView` that was working around some IPAddress/Prefix form validation gaps.

## v2.0.0-beta.2 (2023-07-07)

### Added

- [#3287](https://github.com/nautobot/nautobot/issues/3287) - Added `nautobot-server audit_dynamic_groups` management command for evaluating breaking filter changes to existing DynamicGroup instances.
- [#3526](https://github.com/nautobot/nautobot/issues/3526) - Added detail view UI layout config.
- [#3635](https://github.com/nautobot/nautobot/issues/3635) - Added `interfaces` and `vm_interfaces` fields to REST API representation of `IPAddress`.
- [#3845](https://github.com/nautobot/nautobot/issues/3845) - Added data migration to ensure all existing service instances fit those uniqueness constraints.
- [#3845](https://github.com/nautobot/nautobot/issues/3845) - Added CreateView for Service Model.
- [#3846](https://github.com/nautobot/nautobot/issues/3846) - Added migration helper method to check if a model contains duplicate records based on its natural key fields.
- [#3846](https://github.com/nautobot/nautobot/issues/3846) - Added migration to check whether all existing Virtual Chassis instances have unique names and to fail if they do not.
- [#3885](https://github.com/nautobot/nautobot/issues/3885) - Added a `unique_together` constraint for `ObjectChange` records.
- [#3900](https://github.com/nautobot/nautobot/issues/3900) - Added 'invoke migration-test' and corresponding CI step.
- [#3935](https://github.com/nautobot/nautobot/issues/3935) - Added constraints to the `parent` field on `Prefix` based on the prefix's `type` and the parent's `type`.
- [#3939](https://github.com/nautobot/nautobot/issues/3939) - Added a post-migration helper tool for de-duplicating `IPAddresses`.
- [#3940](https://github.com/nautobot/nautobot/issues/3940) - Added Jobs migration docs.
- [#4003](https://github.com/nautobot/nautobot/issues/4003) - Synced in code changes from `develop` branch up through version 1.5.22.
- [#4004](https://github.com/nautobot/nautobot/issues/4004) - Added `--save` option to `nautobot-server validate_models` command.
- [#4004](https://github.com/nautobot/nautobot/issues/4004) - Added `successful_post` callback function to `ObjectEditView`.
- [#4004](https://github.com/nautobot/nautobot/issues/4004) - Added `parent` filter for `Prefix` objects.
- [#4004](https://github.com/nautobot/nautobot/issues/4004) - Added warning messages when creating or editing a `Prefix` or `IPAddress` that does not follow prefix `type` guidance.

### Changed

- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Changed many FilterSet filters to filter on (name or ID) instead of (slug or ID) since the relevant model `slug` fields have been removed.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Changed FilterSet filters referring to `DeviceType` objects to filter on (model or ID) instead of (slug or ID).
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Changed `NaturalKeyOrPKMultipleChoiceFilter` default `to_field_name` from `slug` to `name`.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Replaced `NameSlugSearchFilterSet` with `NameSearchFilterSet`.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Changed default `ModelViewTestCase._get_url()` behavior to prefer `pk`-based URLs over `slug`-based URLs.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Changed `ObjectEditView.get_object()` and `ObjectDeleteView.get_object()` to prefer `pk`-based object lookups over `slug`-based lookups.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Revised development best-practices documentation around the inclusion of `slug` fields in models.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Changed Git repository provided "implicit" config context files to be based on `name` (or `model` in the case of DeviceType contexts) instead of `slug`.
- [#2916](https://github.com/nautobot/nautobot/issues/2916) - Updated prefix utilization calculation.
- [#3287](https://github.com/nautobot/nautobot/issues/3287) - Changed the `ip_version` filters in `PrefixFilterSet` and `IPAddressFilterSet` to `django_filters.NumberFilter`.
- [#3424](https://github.com/nautobot/nautobot/issues/3424) - Added `IPAddress.type` field and moved DHCP/SLAAC status to types.
- [#3424](https://github.com/nautobot/nautobot/issues/3424) - Unskipped `nautobot.ipam.tests.test_forms.IPAddressFormTest`
- [#3634](https://github.com/nautobot/nautobot/issues/3634) - Restored `assigned_to_interface` as a `RelatedMembershipBooleanFilter` with name `has_interface_assignments` on `IPAddressFilterSet`.
- [#3634](https://github.com/nautobot/nautobot/issues/3634) - Restored `present_in_vrf` and `present_in_vrf_id` filters on `IPAddressFilterSet`.
- [#3635](https://github.com/nautobot/nautobot/issues/3635) - Re-enabled and updated some GraphQL tests relating to IPAddress objects in GraphQL.
- [#3725](https://github.com/nautobot/nautobot/issues/3725) - Changed REST API nested hyperlink to a brief object representation consisting of its ID, URL, and object_type.
- [#3748](https://github.com/nautobot/nautobot/issues/3748) - Updated API serializers to support Namespaces and unskip unit tests
- [#3770](https://github.com/nautobot/nautobot/issues/3770) - Modified the text color to be gray-1 for the sidebarNav components.
- [#3770](https://github.com/nautobot/nautobot/issues/3770) - In Layout.js, also made the 'Return to Legacy UI' link gray-1 for consistency.
- [#3770](https://github.com/nautobot/nautobot/issues/3770) - Made the sidebar button links be orange when selected and on that page.
- [#3778](https://github.com/nautobot/nautobot/issues/3778) - Changed the REST API depth for generating the OpenAPI schema from 1 to 0.
- [#3778](https://github.com/nautobot/nautobot/issues/3778) - Set `ENUM_GENERATE_CHOICE_DESCRIPTION` to False to make OpenAPI schema for REST API filters less verbose.
- [#3793](https://github.com/nautobot/nautobot/issues/3793) - Renamed Natural-key slug to Composite key throughout the code base, UI, REST API, and documentation.
- [#3793](https://github.com/nautobot/nautobot/issues/3793) - Changed url separator character for Composite keys from `&` to `;`.
- [#3845](https://github.com/nautobot/nautobot/issues/3845) - Changed `Service.name` and `Service.device` or `Service.name` and `Service.virtual_machine` to be globally unique and to serve as the natural key for this model.
- [#3846](https://github.com/nautobot/nautobot/issues/3846) - Changed `VirtualChassis.name` to be globally unique and to serve as the natural key for this model.
- [#3847](https://github.com/nautobot/nautobot/issues/3847) - Changed `ScheduledJob.name` to be globally unique and serve as the natural key for this model.
- [#3847](https://github.com/nautobot/nautobot/issues/3847) - Increased `ScheduledJob.task` `max_length` to fix an off-by-one potential error.
- [#3848](https://github.com/nautobot/nautobot/issues/3848) - Changed `ExportTemplate` uniqueness constraint (and natural key) to be simply `(content_type, name)`.
- [#3849](https://github.com/nautobot/nautobot/issues/3849) - Changed `ConfigContext.name` to be globally unique and serve as the natural key for this model.
- [#3849](https://github.com/nautobot/nautobot/issues/3849) - Changed `ConfigContextSchema.name` to be globally unique and serve as the natural key for this model.
- [#3850](https://github.com/nautobot/nautobot/issues/3850) - Changed VLANGroup `name` to unique.
- [#3851](https://github.com/nautobot/nautobot/issues/3851) - Changed `ObjectPermission.name` to be globally unique and serve as the natural key for this model.
- [#3854](https://github.com/nautobot/nautobot/issues/3854) - Updated default index page for "Networks" context to Prefixes.
- [#3883](https://github.com/nautobot/nautobot/issues/3883) - Updated nautobot-ui package in next.
- [#3898](https://github.com/nautobot/nautobot/issues/3898) - Changed the `IPAddress` natural key definition (`IPAddress.natural_key_field_names`) to `[parent__namespace, host]`.
- [#3936](https://github.com/nautobot/nautobot/issues/3936) - Restored navigation menu structure in the legacy UI.
- [#3939](https://github.com/nautobot/nautobot/issues/3939) - Changed `Device.primary_ip4` and `primary_ip6` fields from `OneToOneField` to `ForeignKey`, relaxing the uniqueness constraint.
- [#3939](https://github.com/nautobot/nautobot/issues/3939) - Changed `VirtualMachine.primary_ip4` and `primary_ip6` fields from `OneToOneField` to `ForeignKey`, relaxing the uniqueness constraint.
- [#3940](https://github.com/nautobot/nautobot/issues/3940) - Updated `JOBS_ROOT` Jobs import code to check for conflicts with existing package names.
- [#3953](https://github.com/nautobot/nautobot/issues/3953) - Removed static "Home" text.
- [#3953](https://github.com/nautobot/nautobot/issues/3953) - Fixed padding/spacing of Home and Object Views to be consistent.
- [#3973](https://github.com/nautobot/nautobot/issues/3973) - Changed natural-key for `Prefix` model to `[namespace, prefix]`.
- [#3973](https://github.com/nautobot/nautobot/issues/3973) - Changed natural-key for `Service` model to `[name, virtual_machine, device]`.
- [#3973](https://github.com/nautobot/nautobot/issues/3973) - Changed natural-key for `VLANGroup` model to simply `[name]`.
- [#3973](https://github.com/nautobot/nautobot/issues/3973) - Changed natural-key for `VLAN` model to `[pk]` for now.
- [#4004](https://github.com/nautobot/nautobot/issues/4004) - Changed `Prefix.type` validation with respect to parents and children from strictly-enforced to advisory-only for 2.0.
- [#4004](https://github.com/nautobot/nautobot/issues/4004) - Changed `parent` filter on `IPAddress` to be exact-match by PK; the previously present filter is renamed to `prefix`.

### Fixed

- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Corrected leftover "natural key slug" reference in `object_bulk_create.html`.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Corrected incorrect logic in generic view test `test_list_objects_filtered` and `test_list_objects_unknown_filter_strict_filtering`.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Fixed leftover reference to `GraphQLQuery.slug` in `CustomGraphQLView`.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Fixed leftover references to `slug` in various detail view and edit view templates.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Fixed leftover references to `slug` in various IPAM table columns.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Fixed various leftover references to `slug` fields in the documentation.
- [#3424](https://github.com/nautobot/nautobot/issues/3424) - Fixed a typo in `AvailableIPSerializer` for `ip_version` field representation.
- [#3574](https://github.com/nautobot/nautobot/issues/3574) - Fixed Inability to select multiple entries on (Multiple) selection custom fields in filter.
- [#3580](https://github.com/nautobot/nautobot/issues/3580) - Fixed a bug that prevented moving IP Addresses between Namespaces.
- [#3778](https://github.com/nautobot/nautobot/issues/3778) - Fixed self-referential type loop in the OpenAPI schema that made Swagger UI unusable for some endpoints.
- [#3782](https://github.com/nautobot/nautobot/issues/3782) - Fixed filename for CSV exports.
- [#3847](https://github.com/nautobot/nautobot/issues/3847) - Corrected out-of-date information about `class_path` in the Jobs documentation.
- [#3847](https://github.com/nautobot/nautobot/issues/3847) - Fixed incorrect filter form definitions for JobHookFilterForm, JobResultFilterForm, ScheduledJobFilterForm.
- [#3858](https://github.com/nautobot/nautobot/issues/3858) - Fixed broken dynamic filter form in legacy view.
- [#3859](https://github.com/nautobot/nautobot/issues/3859) - Added logic to protect against defining a `GitRepository.slug` that would conflict with existing Python modules.
- [#3865](https://github.com/nautobot/nautobot/issues/3865) - Fixed errorneous algorithms used in CustomField and Relationship data migrations.
- [#3867](https://github.com/nautobot/nautobot/issues/3867) - Fixed node_modules volume mount in docker-compose.
- [#3876](https://github.com/nautobot/nautobot/issues/3876) - Fixed markdownlint command syntax.
- [#3879](https://github.com/nautobot/nautobot/issues/3879) - Fixed permission check for navigation menu item for Namespaces.
- [#3885](https://github.com/nautobot/nautobot/issues/3885) - Fixed missing `natural_key` for `ObjectChange` records.
- [#3889](https://github.com/nautobot/nautobot/issues/3889) - Fixed a bug in `ScheduledJob` data migration where it is trying to delete a non-existent key from a dictionary.
- [#3890](https://github.com/nautobot/nautobot/issues/3890) - Fixed an error that could happen during migrations if a Site and a Location both have the same `slug`.
- [#3896](https://github.com/nautobot/nautobot/issues/3896) - Fixed a `KeyError` when accessing `ObjectChange` records for a `ConfigContext` via the REST API.
- [#3898](https://github.com/nautobot/nautobot/issues/3898) - Fixed several errors that could occur when defining a model's `natural_key_field_names` to include related object lookups.
- [#3902](https://github.com/nautobot/nautobot/issues/3902) - Fixed a GraphQL error when querying Interface `mac_address` when unset/null/empty values are present.
- [#3916](https://github.com/nautobot/nautobot/issues/3916) - Fixed custom NautobotHyperlinkedRelatedField `to_representation` logic.
- [#3930](https://github.com/nautobot/nautobot/issues/3930) - Fixed inconsistent job test behavior.
- [#3933](https://github.com/nautobot/nautobot/issues/3933) - Fixed noisy output of unit tests.
- [#3955](https://github.com/nautobot/nautobot/issues/3955) - Fixed an error in dcim.0030 migration when CircuitTerminations terminated to ProviderNetworks exist.
- [#3955](https://github.com/nautobot/nautobot/issues/3955) - Fixed an error in ipam.0031 migration when an interface had multiple IPs in the same VRF.
- [#3955](https://github.com/nautobot/nautobot/issues/3955) - Fixed failure of ipam.0031 migration to detect when an interface has a mix of VRF IPs and non-VRF IPs.
- [#3980](https://github.com/nautobot/nautobot/issues/3980) - Fixed a regression in the display of Tag records in the UI.
- [#3998](https://github.com/nautobot/nautobot/issues/3998) - Fixed rendering of breadcrumbs in the 2.0 UI.
- [#4005](https://github.com/nautobot/nautobot/issues/4005) - Added logic to catch and report errors when registering a Job to the database.
- [#4005](https://github.com/nautobot/nautobot/issues/4005) - Added logic to Job class `@classproperty` methods to enforce correct data types.
- [#4005](https://github.com/nautobot/nautobot/issues/4005) - Fixed incorrect documentation about how to register Jobs from an app.
- [#4071](https://github.com/nautobot/nautobot/issues/4071) - Fixed Docker tag syntax for pre-release workflow.
- [#4078](https://github.com/nautobot/nautobot/issues/4078) - Fixed prerelease workflow referenced `ci_integration.yml` file.

### Removed

- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `DeviceType.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `Location.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `LocationType.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `Note.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `ProviderNetwork.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `RackGroup.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `Tag.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `VLANGroup.slug` field.
- [#2662](https://github.com/nautobot/nautobot/issues/2662) - Removed `slug` FilterSet filters from models that no longer have slugs.
- [#3424](https://github.com/nautobot/nautobot/issues/3424) - The built-in "SLAAC" `Status` object has been removed and replaced with an `IPAddress.type` of the same name.
- [#3424](https://github.com/nautobot/nautobot/issues/3424) - The built-in "DHCP" `Status` object has been removed and replaced with an `IPAddress.type` of the same name.
- [#3635](https://github.com/nautobot/nautobot/issues/3635) - Removed leftover `interface` and `vminterface` fields from `IPAddress` GraphQL representation.
- [#3778](https://github.com/nautobot/nautobot/issues/3778) - Removed currently unused `app_full_width_fragment`, `detail-view-config`, `form-fields`, and `table-fields` REST API endpoints.
- [#3847](https://github.com/nautobot/nautobot/issues/3847) - Removed `ScheduledJob.job_class` field as redundant.
- [#3849](https://github.com/nautobot/nautobot/issues/3849) - Removed `ConfigContextSchema.slug` field.
- [#3850](https://github.com/nautobot/nautobot/issues/3850) - Removed VLANGroup [`location`, `name`] uniqueness constraint.
- [#3941](https://github.com/nautobot/nautobot/issues/3941) - Removed `device, rd, name` and `virtual_machine, rd, name` uniqueness constraints on `VRFDeviceAssignment`.
- [#3941](https://github.com/nautobot/nautobot/issues/3941) - Removed `namespace, name` uniqueness constraint on `VRF`.
- [#3941](https://github.com/nautobot/nautobot/issues/3941) - Removed some overly verbose messaging in IPAM migration utilities.

## v2.0.0-beta.1 (2023-06-06)

### Added

- [#851](https://github.com/nautobot/nautobot/issues/851) - Added list view with CSV import/export buttons for `CircuitTermination` objects.
- [#1633](https://github.com/nautobot/nautobot/issues/1633) - Added `created` and `last_updated` fields on the `VMInterface` model. When migrating to this release, these fields will default to `None` for any pre-existing instances of this model.
- [#2331](https://github.com/nautobot/nautobot/issues/2331) - Added job stdout/stderr redirection to database `JobLogEntry` records.
- [#2331](https://github.com/nautobot/nautobot/issues/2331) - Added support to skip job logs from being written to the database.
- [#2901](https://github.com/nautobot/nautobot/issues/2901) - Added `get_absolute_url` method on `BaseModel` which will attempt to resolve the detail view route for all subclassed models.
- [#3192](https://github.com/nautobot/nautobot/issues/3192) - Added a data migration to migrate existing ScheduledJob instances to support new format.
- [#3203](https://github.com/nautobot/nautobot/issues/3203) - Added a `nautobot-server build_ui` command for building the web UI
- [#3237](https://github.com/nautobot/nautobot/issues/3237) - Added Node.JS to Docker final image, bundled `node_modules` to speed up rebuilds.
- [#3615](https://github.com/nautobot/nautobot/issues/3615) - Added toggle buttons between Legacy UI and New UI.
- [#3637](https://github.com/nautobot/nautobot/issues/3637) - Added `pre_delete` signal to nullify the device's `primary_ip` field/fields if its primary ips are removed from interface's `ip_addresses` m2m field.
- [#3637](https://github.com/nautobot/nautobot/issues/3637) - Added `pre_save` signal to catch invalid operations in manual creations of `IPAddressToInterface`.
- [#3637](https://github.com/nautobot/nautobot/issues/3637) - Added `unique_together` for through model `IPAddressToInterface`.
- [#3651](https://github.com/nautobot/nautobot/issues/3651) - Added `home_url`, `config_url`, and `docs_url` keys to the `/api/plugins/installed-plugins/` REST API endpoint.
- [#3679](https://github.com/nautobot/nautobot/issues/3679) - Added optional `api` argument to `BaseModel.get_absolute_url()`.
- [#3702](https://github.com/nautobot/nautobot/issues/3702) - Added basic Redis caching for `TreeModel.display` to reduce redundant queries when listing such objects.
- [#3708](https://github.com/nautobot/nautobot/issues/3708) - Added sorting support to the REST API via the `sort` query parameter.
- [#3713](https://github.com/nautobot/nautobot/issues/3713) - Added `celery_kwargs` field to `JobResult` and `ScheduledJob` models.
- [#3714](https://github.com/nautobot/nautobot/issues/3714) - Added generic test for GET/PUT round-trip in the REST API.
- [#3714](https://github.com/nautobot/nautobot/issues/3714) - Added support for `{"value": "x"}` format when writing to ChoiceFields in the REST API, making round-trip data easier.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Added `NautobotCSVParser` class, providing the ability for the REST API to accept CSV as an input format.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Added ability to specify a `parent_bay` when creating a Device via the REST API.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Added `APIViewTestCases.CreateObjectViewTestCase.test_recreate_object_csv` generic test, testing the "round-trip" capability of each API endpoint's CSV export and import.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Added (temporary) `natural_key_field_names` to `IPAddress`, `Prefix`, `RackReservation`, `ScheduledJob`, and `Service` models.
- [#3721](https://github.com/nautobot/nautobot/issues/3721) - Added App provided model view override.
- [#3722](https://github.com/nautobot/nautobot/issues/3722) - Added `termination_type` filter to `CableFilterSet`.
- [#3722](https://github.com/nautobot/nautobot/issues/3722) - Added `natural_key_slug` field to REST API serializers.
- [#3736](https://github.com/nautobot/nautobot/issues/3736) - Added App provided custom route view.
- [#3741](https://github.com/nautobot/nautobot/issues/3741) - Added natural-key-slug information to UI detail views.
- [#3754](https://github.com/nautobot/nautobot/issues/3754) - Added loading widget to the left of the ObjectListTable Buttons after initial data load.
- [#3759](https://github.com/nautobot/nautobot/issues/3759) - Implemented IPAM Namespace & parenting data migrations.
- [#3767](https://github.com/nautobot/nautobot/issues/3767) - Added `detail-view-config` API endpoint to `ModelViewSetMixin`.
- [#3804](https://github.com/nautobot/nautobot/issues/3804) - Added feature to redirect all add and edit views to legacy UI.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Added `bool` return value for `Nautobot.extras.datasources.git.ensure_git_repository()` to indicate whether the filesystem was changed.

### Changed

- [#1633](https://github.com/nautobot/nautobot/issues/1633) - The base class for all `tags` fields on `PrimaryModel` subclasses is now `nautobot.core.models.fields.TagsField` rather than `taggit.managers.TaggableManager`. Any apps using `PrimaryModel` as a base class will likely need to generate and run a schema migration to reflect this change.
- [#2331](https://github.com/nautobot/nautobot/issues/2331) - Changed `JobLogEntry.log_level` choices from `default`, `info`, `success`, `warning`, `failure` to Python default logging levels `debug`, `info`, `warning`, `error` and `critical`.
- [#2331](https://github.com/nautobot/nautobot/issues/2331) - Changed job logging from custom log methods on the `BaseJob` class to celery's `get_task_logger` logging implementation.
- [#2569](https://github.com/nautobot/nautobot/issues/2569) - Revamped CSV export functionality to use REST API serializers for more self-consistency and reduced boilerplate.
- [#2569](https://github.com/nautobot/nautobot/issues/2569) - Revised the natural key for `SecretsGroupAssociation` through-table model.
- [#2569](https://github.com/nautobot/nautobot/issues/2569) - Changed behavior of `JobLogEntry.display` REST API field to match the model behavior.
- [#2799](https://github.com/nautobot/nautobot/issues/2799) - Changed REST API versioning to default to latest instead of earliest when unspecified by the client.
- [#3042](https://github.com/nautobot/nautobot/issues/3042) - Removed all `Nested*Serializer` classes in favor of a `depth`-based REST API design.
- [#3042](https://github.com/nautobot/nautobot/issues/3042) - The `?brief=True` REST API parameter has been replaced by a new `?depth=<0-10>` API parameter, allowing greater control of the returned data.
- [#3228](https://github.com/nautobot/nautobot/issues/3228) - Removed `run_job` Celery task and updated `BaseJob` to subclass Celery `Task`.
- [#3449](https://github.com/nautobot/nautobot/issues/3449) - Renamed `Relationship` model attribute `slug` to `key`.
- [#3449](https://github.com/nautobot/nautobot/issues/3449) - Renamed `Relationship` model attribute `name` to `label`.
- [#3450](https://github.com/nautobot/nautobot/issues/3450) - Renamed `ComputedField` model attribute `slug` to `key`.
- [#3465](https://github.com/nautobot/nautobot/issues/3465) - Renamed IPAddress `prefix_length` field to `mask_length`.
- [#3465](https://github.com/nautobot/nautobot/issues/3465) - Made IPAddress `host` field non-modifiable.
- [#3527](https://github.com/nautobot/nautobot/issues/3527) - Restructured navigation menus to context-centered design for 2.0.
- [#3552](https://github.com/nautobot/nautobot/issues/3552) - Extracted data tables from upgrading-from-nautobot-v1.md into separate YAML files.
- [#3586](https://github.com/nautobot/nautobot/issues/3586) - Changed REST API for Device and VirtualMachine to omit `config_context` by default and only include it when requested by using the `?include=config_context` query parameter.
- [#3607](https://github.com/nautobot/nautobot/issues/3607) - Changed the default `lookup_field` for `NautobotUIViewSet` to `"pk"` instead of `"slug"`.
- [#3650](https://github.com/nautobot/nautobot/issues/3650) - Updated ui 2.0 jsconfig.json to exclude `node_modules` and `build` directories.
- [#3663](https://github.com/nautobot/nautobot/issues/3663) - Modified `delete_button` and `edit_button` template tags to lookup `pk` and `slug` without the need to specify the lookup key.
- [#3679](https://github.com/nautobot/nautobot/issues/3679) - Changed `BaseModelSerializer` to inherit from `HyperlinkedModelSerializer` instead of `ModelSerializer`. This changed the REST API representation of related objects (at depth 0) from UUIDs to API hyperlinks to improve discoverability and usability of the API.
- [#3691](https://github.com/nautobot/nautobot/issues/3691) - Implemented `Meta.list_display_fields` for all serializers.
- [#3692](https://github.com/nautobot/nautobot/issues/3692) - Updated `JobResult` manager `store_result` method to censor sensitive variables.
- [#3702](https://github.com/nautobot/nautobot/issues/3702) - Changed nested serialization to never include tags, computed fields, relationships, and other M2M fields.
- [#3713](https://github.com/nautobot/nautobot/issues/3713) - Changed `Job.read_only` field to an informational field set by the job author and removed the ability for administrators to override this field. This field no longer changes the behavior of Nautobot core.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Reworked CSV import to be based on the REST API implementation instead of custom forms and views.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Changed the parameters and behavior of `CSVDataField` and `CSVFileField` in support of the new CSV import framework.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Changed the `user` parameter on the RackReservation REST API to optional; if omitted, the requesting user will now be automatically selected as the owner of any created reservations.
- [#3742](https://github.com/nautobot/nautobot/issues/3742) - Centered the LoadingWidget component in UI.
- [#3742](https://github.com/nautobot/nautobot/issues/3742) - Lightened the color of the LoadingWidget text to gray-3.
- [#3742](https://github.com/nautobot/nautobot/issues/3742) - Lightened the color of the skeleton component when loading tables.
- [#3744](https://github.com/nautobot/nautobot/issues/3744) - A batch of improvements to state handling in the UI to solve loading bugs.
- [#3767](https://github.com/nautobot/nautobot/issues/3767) - Enhanced error handling for fetcher in React UI `ObjectRetrieveView`.
- [#3785](https://github.com/nautobot/nautobot/issues/3785) - Deprecated `StatusModel` mixin in favor of directly including a `StatusField` as needed.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Changed Job `class_path` property from `<source>/<module>/<ClassName>` to simply `<module>.<ClassName>`.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Changed GitRepository slugs to use underscores rather than dashes so they can be used as Python module names.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Changed Job `module_name` for Git-derived Jobs to `<git_repository_slug>.jobs.<module>`.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - System-provided Jobs are now enabled by default for running.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Changed return signature for `Nautobot.core.utils.git.GitRepo.checkout()` to include whether the filesystem was changed.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Changed `job` filter on JobButton, JobHook, JobResult, and ScheduledJob to be name-based rather than slug-based.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Changed `Job.runnable` property to not consider whether the `job_class` is set, as a performance optimization.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Moved test Jobs from `nautobot/extras/tests/example_jobs/test_*.py` to `nautobot/extras/test_jobs/*.py` to avoid unnecessary loading by the `unittest` runner.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Changed client-side slug construction (legacy UI) to use underscores rather than dashes.

### Dependencies

- [#1721](https://github.com/nautobot/nautobot/issues/1721) - Removed dependency on `django-cacheops`.
- [#3672](https://github.com/nautobot/nautobot/issues/3672) - Changed `napalm` dependency to 4.x release in order to allow Netmiko 4.x to install. Dependency resolution resulted in removing the following packages: `ciscoconfparse`, `deprecat`, `dnspython`, `loguru`, `toml`, `win32-setctime`.

### Fixed

- [#3378](https://github.com/nautobot/nautobot/issues/3378) - Re-enabled skipped tests.
- [#3437](https://github.com/nautobot/nautobot/issues/3437) - Fixed the possibility of inadvertently applying the same `Tag` to the same object multiple times by adding appropriate uniqueness constraints on the `TaggedItem` through table.
- [#3518](https://github.com/nautobot/nautobot/issues/3518) - Fixed an error seen when running the `extras.0061_collect_roles_from_related_apps_roles` migration.
- [#3545](https://github.com/nautobot/nautobot/issues/3545) - Fixed a bug in Job edit view template where slug was missing, preventing creation from happening.
- [#3591](https://github.com/nautobot/nautobot/issues/3591) - Fixed a few errors in the v2.0 migration documentation.
- [#3592](https://github.com/nautobot/nautobot/issues/3592) - Fixed heuristic for duplicate calls to `populate_model_features_registry` causing skipped updates.
- [#3618](https://github.com/nautobot/nautobot/issues/3618) - Fix corrupted `package-lock.json` which was causing test failures.
- [#3675](https://github.com/nautobot/nautobot/issues/3675) - Fixed job edit form silently failing.
- [#3687](https://github.com/nautobot/nautobot/issues/3687) - Fixed a bug in `Prefix.reparent_ips()` that was too greedy in reparenting IP addresses when child prexies were deeply nested (such as /31)
- [#3702](https://github.com/nautobot/nautobot/issues/3702) - Added some missing `select_related` on `DeviceViewSet` and `PrefixViewSet` to improve performance.
- [#3714](https://github.com/nautobot/nautobot/issues/3714) - Fixed inability to set null via the REST API on `Interface.mac_address` and `VMInterface.mac_address`.
- [#3714](https://github.com/nautobot/nautobot/issues/3714) - Fixed inability to set null via the REST API on `DeviceType.front_image` and `DeviceType.rear_image`.
- [#3714](https://github.com/nautobot/nautobot/issues/3714) - Fixed `password` being incorrectly marked as a required field when editing a User via the REST API.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Fixed inability to set the `failover_strategy` field as unspecified/blank when creating/updating `DeviceRedundancyGroup` via the REST API.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Fixed incorrect interim natural key definition for `Device` and `VRF` models.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Fixed the possibility of setting values for nonexistent custom fields via the REST API.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Fixed incorrect password-handling logic when creating/updating a `User` via the REST API.
- [#3716](https://github.com/nautobot/nautobot/issues/3716) - Fixed an error when attempting to edit a user via the Nautobot admin UI.
- [#3722](https://github.com/nautobot/nautobot/issues/3722) - Fixed incorrect filter forms on console-connections, power-connections, and interface-connections list views.
- [#3729](https://github.com/nautobot/nautobot/issues/3729) - Fixed a bug that references a non-existent Relationship model attribute in Relationship migration file.
- [#3731](https://github.com/nautobot/nautobot/issues/3731) - Fixed `debugpy` workflow not working with the removal of `manage.py`.
- [#3737](https://github.com/nautobot/nautobot/issues/3737) - Fixed broken `--cache_test_fixtures` when running tests.
- [#3740](https://github.com/nautobot/nautobot/issues/3740) - Fixed container builds failed resulting from #3731.
- [#3741](https://github.com/nautobot/nautobot/issues/3741) - Fixed missing time-zone information on various Job-related tests in `nautobot.extras.tests.test_views`.
- [#3741](https://github.com/nautobot/nautobot/issues/3741) - Fixed various cable-termination API serializers incorrectly reporting the `cable` field as writable.
- [#3768](https://github.com/nautobot/nautobot/issues/3768) - Fixed new UI homepage breaks if recent object-changes reference objects that no longer exist.
- [#3785](https://github.com/nautobot/nautobot/issues/3785) - Fixed undesirable nullability of `status` fields to correctly match their intended usage.
- [#3786](https://github.com/nautobot/nautobot/issues/3786) - Fixed default descriptions of REST API actions in the OpenAPI schema to be more accurate.
- [#3792](https://github.com/nautobot/nautobot/issues/3792) - Fixed logging output not being suppressed during unit and integration tests.
- [#3828](https://github.com/nautobot/nautobot/issues/3828) - Fixed a bug caused by [#3637](https://github.com/nautobot/nautobot/issues/3637) that prevents devices with primary_ip from being deleted.
- [#3829](https://github.com/nautobot/nautobot/issues/3829) - Fixed build failure caused by registered App missing ui/index.js.
- [#3833](https://github.com/nautobot/nautobot/issues/3833) - Fixed build failure caused by registered App missing urls.py file or a urlpatterns.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Removed leftover/non-functional `Source` tab from job_approval_request.html.
- [#3864](https://github.com/nautobot/nautobot/issues/3864) - Fixed cases where Device.role was null, incongruent with the enforcement in the API and UI.

### Removed

- [#1633](https://github.com/nautobot/nautobot/issues/1633) - Removed monkey-patching of `taggit.managers.TaggableManager`.
- [#1633](https://github.com/nautobot/nautobot/issues/1633) - Removed `nautobot.extras.utils.is_taggable`; use `nautobot.core.models.utils.is_taggable` instead.
- [#1633](https://github.com/nautobot/nautobot/issues/1633) - Removed backward-compatibility with `taggit` 1.x Python API; instead of `object.tags.set(tag1, tag2, tag3)` you must now do `object.tags.set([tag1, tag2, tag3])`.
- [#1721](https://github.com/nautobot/nautobot/issues/1721) - Removed dependency on and usage of `django-cacheops`.
- [#2331](https://github.com/nautobot/nautobot/issues/2331) - Removed custom `BaseJob` logging methods `_log`, `log`, `log_debug`, `log_success`, `log_info`, `log_warning` and `log_failure`.
- [#2331](https://github.com/nautobot/nautobot/issues/2331) - Removed `active_test` and `failed` properties from `BaseJob` class.
- [#2569](https://github.com/nautobot/nautobot/issues/2569) - Removed `csv_headers` and `to_csv()` from all models as they are no longer needed.
- [#2885](https://github.com/nautobot/nautobot/issues/2885) - Removed `changelog_url` from `ObjectView`'s context.
- [#3228](https://github.com/nautobot/nautobot/issues/3228) - Removed atomic transaction from Jobs.
- [#3228](https://github.com/nautobot/nautobot/issues/3228) - Removed support for `test_*` and `post_run` methods in Jobs.
- [#3465](https://github.com/nautobot/nautobot/issues/3465) - Removed `broadcast` field from IPAddress.
- [#3527](https://github.com/nautobot/nautobot/issues/3527) - Removed `NavMenuButton` and its subclasses as they are not a part of the 2.0 UI.
- [#3527](https://github.com/nautobot/nautobot/issues/3527) - Removed `NavMenuTab.weight` property as the menu tabs/contexts are not reorderable in 2.0.
- [#3623](https://github.com/nautobot/nautobot/issues/3623) - Removed remaining erroneous slug references from tenant.html and tenantgroup.html.
- [#3651](https://github.com/nautobot/nautobot/issues/3651) - Removed misspelled `verison` key from `/api/plugins/installed-plugins` REST API endpoint.
- [#3679](https://github.com/nautobot/nautobot/issues/3679) - Removed explicit `url` field declarations from most REST API serializers as they are now derived automatically.
- [#3713](https://github.com/nautobot/nautobot/issues/3713) - Removed `Job.read_only_override`, `JobResult.obj_type`, `JobResult.periodic_task_name`, and `JobResult.task_id` fields.
- [#3713](https://github.com/nautobot/nautobot/issues/3713) - Removed `NautobotFakeRequest` and associated methods, variables and logic.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Removed `LocatableModelCSVFormMixin`, `RoleModelCSVFormMixin`, `RoleRequiredRoleModelCSVFormMixin`, and `StatusModelCSVFormMixin` classes, as they are no longer needed after reworking how CSV import is handled.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Removed `bulk_create_form_class` field from `NautobotUIViewSet` as it's no longer used or needed.
- [#3715](https://github.com/nautobot/nautobot/issues/3715) - Removed `model_form` and `widget_attrs` fields from `BulkImportView` as they are no longer used or needed.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Removed `Job.slug`, `Job.source`, and `Job.git_repository` database fields.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Removed `source` and `slug` filters for Jobs.
- [#3840](https://github.com/nautobot/nautobot/issues/3840) - Removed `get_jobs()`, `get_job_classpaths()`, `jobs_in_directory()` functions.

## v2.0.0-alpha.3 (2023-04-13)

### Added

- [#3337](https://github.com/nautobot/nautobot/issues/3337) - Add `Namespace` model to IPAM.

### Changed

- [#2915](https://github.com/nautobot/nautobot/issues/2915) - Implemented a concrete `parent` relationship from `Prefix` to itself.
- [#3337](https://github.com/nautobot/nautobot/issues/3337) - Changed Prefix and other model uniqueness to center around Namespace model.
- [#3337](https://github.com/nautobot/nautobot/issues/3337) - TODO: Update with many more changes.
- [#3439](https://github.com/nautobot/nautobot/issues/3439) - Changed the GraphQL `execute_saved_query` function's argument from `saved_query_slug` to `saved_query_name`.
- [#3523](https://github.com/nautobot/nautobot/issues/3523) - Renamed `nat_outside` field on IPAddress serializer to `nat_outside_list` for self-consistency.

### Dependencies

- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Dropped support for Python 3.7. Python 3.8 is now the minimum version required by Nautobot.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `django-auth-ldap` dependency to `~4.2.0`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `django-cors-headers` dependency to `~3.14.0`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `django-filter` dependency to `~23.1`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `django-health-check` dependency to `~3.17.0`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `django-tables2` dependency to `~2.5.3`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `django-tree-queries` dependency to `~0.14.0`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Removed direct dependency on `importlib-metadata`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `pillow` dependency to `~9.5.0`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `prometheus-client` dependency to `~0.16.0`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `social-auth-core` dependency to `~4.4.1`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated `social-auth-app-django` dependency to `~5.2.0`.
- [#2316](https://github.com/nautobot/nautobot/issues/2316) - Updated various development-only dependencies to the latest available versions.
- [#3525](https://github.com/nautobot/nautobot/issues/3525) - Added explicit dependency on `packaging` that had been inadvertently omitted.

### Removed

- [#3439](https://github.com/nautobot/nautobot/issues/3439) - Removed `slug` field from many database models.
- [#3523](https://github.com/nautobot/nautobot/issues/3523) - Removed `nat_outside` getter-setter in IPAddress model.

## v2.0.0-alpha.2 (2023-03-29)

### Added

- [#2900](https://github.com/nautobot/nautobot/issues/2900) - Added natural-key support to most Nautobot models, inspired by the `django-natural-keys` library.
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Added Location constraints for objects (CircuitTermination, Device, PowerPanel, PowerFeed, RackGroup, Rack, Prefix, VLAN, VLANGroup, Cluster).
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Added Region and Site data migration to Locations for existing ConfigContext instances.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Added `ForeignKeyWithAutoRelatedName` helper class.
- [#3154](https://github.com/nautobot/nautobot/issues/3154) - Added ability for `tags` filters to filter by UUID as well as by slug.
- [#3185](https://github.com/nautobot/nautobot/issues/3185) - Added missing user filterset fields.
- [#3222](https://github.com/nautobot/nautobot/issues/3222) - Added Site and Region data migration for ConfigContext class and ensured that "Site" LocationType allows the correct ContentTypes.
- [#3255](https://github.com/nautobot/nautobot/issues/3255) - Added `--cache-test-fixtures` command line argument to Nautobot unit and integration tests.
- [#3256](https://github.com/nautobot/nautobot/issues/3256) - Added Site and Region data migration for ComputedFields, CustomFields, CustomLinks, ExportTemplates, ImageAttachments, JobHooks, Notes, Relationships, Webhooks, Statuses and Tags
- [#3283](https://github.com/nautobot/nautobot/issues/3283) - Added Site and Region migration to Location for filter data of DynamicGroups.
- [#3360](https://github.com/nautobot/nautobot/issues/3360) - Added an alternate approach to updating model feature registry without having to decorate a model with `@extras_features`.
- [#3364](https://github.com/nautobot/nautobot/issues/3364) - Added FK fields `migrated_location` to Site and Region models before data migration is applied.
- [#3403](https://github.com/nautobot/nautobot/issues/3403) - Added support for Nautobot Apps to provide Django Constance Fields for the settings.
- [#3418](https://github.com/nautobot/nautobot/issues/3418) - Added ObjectPermission Data Migration from Region/Site to Location.

### Changed

- [#824](https://github.com/nautobot/nautobot/issues/824) - Renamed `slug` field to `key` on CustomField model class.
- [#824](https://github.com/nautobot/nautobot/issues/824) - Changed validation of CustomField `key` to enforce that it is valid as a GraphQL identifier.
- [#951](https://github.com/nautobot/nautobot/issues/951) - The `nautobot-server nbshell` command is now based on `shell_plus` from `django-extensions`.
- [#1362](https://github.com/nautobot/nautobot/issues/1362) - Added `type` field to `Prefix`, replacing "Container" status and `is_pool` field.
- [#2076](https://github.com/nautobot/nautobot/issues/2076) - Changed the `created` field of all models from a DateField to a DateTimeField for added granularity. Preexisting records will show as created at midnight UTC on their original creation date.
- [#2611](https://github.com/nautobot/nautobot/issues/2611) - Changed `Job` model uniqueness constraints and `slug` field.
- [#2806](https://github.com/nautobot/nautobot/issues/2806) - Enhanced VLAN `available_on_device` filter to permit specifying multiple Devices.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `related_name` values for path endpoints on `CablePath` for consistency and readability (`dcim_interface_related` to `interfaces`, `circuits_circuittermination_related` to `circuit_terminations`, etc.)
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `related_name` values for device components on `Device` for consistency and readability (`consoleports` to `console_ports`, `devicebays` to `device_bays`, etc.)
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `related_name` values for device component templates on `DeviceType` for consistency and readability (`consoleporttemplates` to `console_port_templates`, `devicebaytemplates` to `device_bay_templates`, etc.)
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `DeviceType.instances` to `devices` and renamed the corresponding query filters.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `DeviceRedundancyGroup.members` to `devices`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `FrontPortTemplate.rear_port` to `rear_port_template`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `Location.powerpanels` to `power_panels`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `PowerOutletTemplate.power_port` to `power_port_template`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `PowerPanel.powerfeeds` to `power_feeds`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `PowerPort.poweroutlets` to `power_outlets`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `PowerPortTemplate.poweroutlet_templates` to `power_outlet_templates`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `Rack.powerfeed_set` to `power_feeds`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `Rack.group` and `Rack.reservations` to `rack_group` and `rack_reservations` and renamed the corresponding query filters.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `RackGroup.powerpanel_set` to `power_panels`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `RearPort.frontports` to `front_ports`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `RearPortTemplate.frontport_templates` to `front_port_templates`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `SecretsGroup.device_set` and `SecretsGroup.deviceredundancygroup_set` to `devices` and `device_redundancy_groups`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `Tenant.rackreservations` to `rack_reservations`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `User.rackreservation_set` to `rack_reservations`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed REST API field on `Interface` from `count_ipaddresses` to `ip_address_count`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed REST API fields on `Manufacturer` from `devicetype_count` and `inventoryitem_count` to `device_type_count` and `inventory_item_count`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed REST API field on `Platform` from `virtualmachine_count` to `virtual_machine_count`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed REST API field on `PowerPanel` from `powerfeed_count` to `power_feed_count`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed REST API field on `Rack` from `powerfeed_count` to `power_feed_count`.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Changed `RackReservation` `group` filter to `rack_group`.
- [#3154](https://github.com/nautobot/nautobot/issues/3154) - Renamed various `tag` filters to `tags` for self-consistency.
- [#3160](https://github.com/nautobot/nautobot/issues/3160) - Changed logger names to use `__name__` instead of explicit module names.
- [#3215](https://github.com/nautobot/nautobot/issues/3215) - Changed representation of related Status objects in the REST API to use a NestedStatusSerializer instead of presenting as enums.
- [#3236](https://github.com/nautobot/nautobot/issues/3236) - Changed `Interface` and `VMInterface` relationship to `IPAddress` to many-to-many instead of one-to-many.
- [#3262](https://github.com/nautobot/nautobot/issues/3262) - Changed extras FKs and related names.
- [#3266](https://github.com/nautobot/nautobot/issues/3266) - Changed erroneous attribute "type" to correct "circuit_type" in circuit-related templates.
- [#3302](https://github.com/nautobot/nautobot/issues/3302) - Migrated `Aggregate` model to `Prefix` with type set to "Container".
- [#3351](https://github.com/nautobot/nautobot/issues/3351) - Changed extras abstract model ForeignKeys to use ForeignKeyWithAutoRelatedName.
- [#3354](https://github.com/nautobot/nautobot/issues/3354) - Synced in fixes from 1.5.x LTM branch up through v1.5.11.

### Dependencies

- [#2521](https://github.com/nautobot/nautobot/issues/2521) - Removed dependency on `django-cryptography`.
- [#2524](https://github.com/nautobot/nautobot/issues/2524) - Removed no-longer-used `drf-yasg` dependency.

### Fixed

- [#633](https://github.com/nautobot/nautobot/issues/633) - Fixed job result not updating when job hard time limit is reached.
- [#1362](https://github.com/nautobot/nautobot/issues/1362) - Fixed migrations for `Prefix.type`.
- [#1422](https://github.com/nautobot/nautobot/issues/1422) - Improved OpenAPI schema representation of polymorphic fields such as `cable_peer`, `assigned_object`, etc.
- [#2806](https://github.com/nautobot/nautobot/issues/2806) - Fixed some issues with initialization and updating of the dynamic ("advanced") filter form.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Fixed incorrect `field_class` when filtering `FloatField` and `DecimalField` model fields.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Fixed inability to provide non-integer values when filtering on `FloatField` and `DecimalField` fields in GraphQL.
- [#3066](https://github.com/nautobot/nautobot/issues/3066) - Fixed inability to specify partial substrings in the UI when filtering by MAC address.
- [#3154](https://github.com/nautobot/nautobot/issues/3154) - Fixed incorrect initialization of `TagFilter` when auto-attached to a FilterSet.
- [#3164](https://github.com/nautobot/nautobot/issues/3164) - Merged `TaskResult` from `django-celery-results` into `JobResult`.
- [#3291](https://github.com/nautobot/nautobot/issues/3291) - Fixed inheritance and `RoleField` definition on `Role` model mixins.
- [#3342](https://github.com/nautobot/nautobot/issues/3342) - Fixed BaseFilterSet not using multiple choice filters for CharFields with choices.
- [#3457](https://github.com/nautobot/nautobot/issues/3457) - Fixed bug preventing scheduled job from running.

### Removed

- [#824](https://github.com/nautobot/nautobot/issues/824) - Removed `name` field from CustomField model class.
- [#1634](https://github.com/nautobot/nautobot/issues/1634) - Removed unnecessary legacy `manage.py` file from Nautobot repository.
- [#2521](https://github.com/nautobot/nautobot/issues/2521) - Removed support for storing Git repository credentials (username/token) in the Nautobot database. Use [Secrets](../user-guide/platform-functionality/secret.md) instead.
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Removed Site constraints for model classes (CircuitTermination, Device, Location, PowerPanel, PowerFeed, RackGroup, Rack, Prefix, VLAN, VLANGroup, Cluster).
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Removed `regions` and `sites` attributes from ConfigContext model class.
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Removed `region` and `site` related fields from Serializers for aforementioned model classes.
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Removed `region` and `site` related fields from Forms for aforementioned model classes.
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Removed `region` and `site` related UI and API Endpoints for aforementioned model classes.
- [#2957](https://github.com/nautobot/nautobot/issues/2957) - Removed `region` and `site` columns from Tables for aforementioned model classes.
- [#2958](https://github.com/nautobot/nautobot/issues/2958) - Removed Region and Site factories, filtersets, forms, factories, models, navigation menu items, serializers, tables, templates, tests and urls.
- [#3224](https://github.com/nautobot/nautobot/issues/3224) - Removed support for Nautobot "1.x" REST API versions. The minimum supported REST API version is now "2.0".
- [#3233](https://github.com/nautobot/nautobot/issues/3233) - Removed `CeleryTestCase` and associated calling code as it is no longer needed.
- [#3302](https://github.com/nautobot/nautobot/issues/3302) - Removed `Aggregate` and migrated all existing instances to `Prefix`.

## v2.0.0-alpha.1 (2023-01-31)

### Added

- [#204](https://github.com/nautobot/nautobot/issues/204) - Added style guide documentation for importing python modules in Nautobot.
- [#1731](https://github.com/nautobot/nautobot/issues/1731) - Added missing filters to `circuits` app.
- [#1733](https://github.com/nautobot/nautobot/issues/1733) - Added support for filtering on many more fields to the `Tenant` and `TenantGroup` filtersets.
- [#2954](https://github.com/nautobot/nautobot/issues/2954) - Added fields (`contact_name`, `latitude`, etc.) from `Site` model to `Location` model to prepare for merging all sites into locations.
- [#2955](https://github.com/nautobot/nautobot/issues/2955) - Added "Region" and "Site" `LocationTypes` and their respective locations based on existing `Site` and `Region` instances.
- [#3132](https://github.com/nautobot/nautobot/issues/3132) - Added the ability for apps to register their models for inclusion in the global Nautobot search.

### Changed

- [#204](https://github.com/nautobot/nautobot/issues/204) - Changed imports to use module namespaces in `utilities/filters.py`.
- [#510](https://github.com/nautobot/nautobot/issues/510) - The `Region`, `RackGroup`, `TenantGroup`, and `InventoryItem` models are now based on `django-tree-queries` instead of `django-mptt`. This does change the API for certain tree operations on these models, for example `get_ancestors()` is now `ancestors()` and `get_descendants()` is now `descendants()`.
- [#510](https://github.com/nautobot/nautobot/issues/510) - The UI and REST API for `Region`, `RackGroup`, and `TenantGroup` now provide only the related count of objects (e.g. `site_count` for `Region`) that are directly related to each instance. Formerly they provided a cumulative total including objects related to its descendants as well.
- [#510](https://github.com/nautobot/nautobot/issues/510) - Renamed field `_depth` to `tree_depth` in the REST API for `Region`, `RackGroup`, `TenantGroup`, and `InventoryItem`.
- [#510](https://github.com/nautobot/nautobot/issues/510) - Renamed InventoryItem database relation `child_items` and filter fields `child_items` and `has_child_items` to `children` and `has_children` respectively.
- [#2163](https://github.com/nautobot/nautobot/issues/2163) - `JobLogEntry.log_object`, `JobLogEntry.absolute_url`, `ScheduledJob.queue`, and `WebHook.ca_file_path` no longer permit null database values; use `""` instead if needed.
- [#2822](https://github.com/nautobot/nautobot/issues/2822) - Collapsed `DeviceRole`, `RackRole`, IPAM `Role` model and `IPAddressRoleChoices` into a single generic `Role` model.
- [#2674](https://github.com/nautobot/nautobot/issues/2674) - Updated development dependency `black` to `~22.10.0`.
- [#2721](https://github.com/nautobot/nautobot/issues/2721) - Collapsed `nautobot.utilities` into `nautobot.core`. Refer to the 2.0 migration guide for details.
- [#2771](https://github.com/nautobot/nautobot/issues/2771) - Updated `jsonschema` version to `~4.17.0`.
- [#2788](https://github.com/nautobot/nautobot/issues/2788) - Changed REST framework allowed versions logic to support 1.2-1.5 and 2.0+.
- [#2803](https://github.com/nautobot/nautobot/issues/2803) - Updated `mkdocs-include-markdown-plugin` to `3.9.1`.
- [#2809](https://github.com/nautobot/nautobot/issues/2809) - Renamed `tag` filter on `TenantFilterSet` to `tags` same as elsewhere.
- [#2844](https://github.com/nautobot/nautobot/issues/2844) - Updated development dependency `mkdocstrings-python` to 0.8.0.
- [#2872](https://github.com/nautobot/nautobot/issues/2872) - Refactored imports in `utilities` app to follow new code style.
- [#2883](https://github.com/nautobot/nautobot/issues/2883) - Updated `django-taggit` to `3.1.0`.
- [#2942](https://github.com/nautobot/nautobot/issues/2942) - Updated `django-tree-queries` to `0.13.0`.
- [#2943](https://github.com/nautobot/nautobot/issues/2943) - Updated dependency `rich` to `~12.6.0`.
- [#2955](https://github.com/nautobot/nautobot/issues/2955) - Changed `CircuitTermination`, `Device`, `PowerPanel`, `RackGroup`, `Rack`, `Prefix`, `VLANGroup`, `VLAN`, `Cluster` instances associated with existing `Site` model instances to use the newly created corresponding `Locations` of `LocationType` "Site".
- [#2993](https://github.com/nautobot/nautobot/issues/2993) - Implemented initial database backend for Celery task results.
- [#3027](https://github.com/nautobot/nautobot/issues/3027) - Updated dependencies `prometheus-client`, `django-storages`, `drf-spectacular`, `black`, `django-debug-toolbar`, `mkdocstrings`, `mkdocstrings-python`, `pylint`, `requests`, `selenium`, `watchdog`.
- [#3068](https://github.com/nautobot/nautobot/issues/3068) - Renamed fields on `Circuit` model: `type` to `circuit_type`, `terminations` to `circuit_terminations`, `termination_a` to `circuit_termination_a`, and `termination_z` to `circuit_termination_z`.
- [#3068](https://github.com/nautobot/nautobot/issues/3068) - Renamed reverse-relation `circuittermination` to `circuit_terminations` on the `CablePath` model.
- [#3068](https://github.com/nautobot/nautobot/issues/3068) - Renamed `group` field to `vlan_group` on VLAN model, renamed `ipaddresses` to `ip_addresses` on `Service` model.
- [#3068](https://github.com/nautobot/nautobot/issues/3068) - Renamed `group` field to `tenant_group` on `Tenant` model.
- [#3069](https://github.com/nautobot/nautobot/issues/3069) - Renamed foreign key fields and related names in Virtualization and DCIM apps to follow a common naming convention. See v2 upgrade guide for full list of changes.
- [#3177](https://github.com/nautobot/nautobot/issues/3177) - Updated `VLANFactory` to generate longer and more "realistic" `VLAN` names.

### Fixed

- [#1982](https://github.com/nautobot/nautobot/issues/1982) - Fixed a UI presentation/validation issue with dynamic-groups using foreign-key filters that aren't explicitly defined in the corresponding FilterForm.
- [#2808](https://github.com/nautobot/nautobot/issues/2808) - Fixed incorrectly named filters in `circuits` app.
- [#3126](https://github.com/nautobot/nautobot/issues/3126) - Fixed `Interface` not raising exception when adding a `VLAN` from a different `Site` in `tagged_vlans`.
- [#3153](https://github.com/nautobot/nautobot/issues/3153) - Made integration test `CableConnectFormTestCase.test_js_functionality` more resilient and less prone to erroneous failures.
- [#3167](https://github.com/nautobot/nautobot/issues/3167) - Fixed `ObjectChange` records not being migrated and `legacy_role__name` not being a property in `Role` migrations.
- [#3177](https://github.com/nautobot/nautobot/issues/3177) - Fixed a spurious failure in `BulkEditObjectsViewTestCase.test_bulk_edit_objects_with_constrained_permission`.

### Removed

- [#510](https://github.com/nautobot/nautobot/issues/510) - Removed dependency on `django-mptt`. Models (`Region`, `RackGroup`, `TenantGroup`, `InventoryItem`) that previously were based on MPTT are now implemented using `django-tree-queries` instead.
- [#1731](https://github.com/nautobot/nautobot/issues/1731) - Removed redundant filters from `circuits` app.
- [#2163](https://github.com/nautobot/nautobot/issues/2163) - Removed unused `NullableCharField`, `NullableCharFieldFilter` and `MACAddressField` (not to be confused with `MACAddressCharField`, which remains) classes.
- [#2523](https://github.com/nautobot/nautobot/issues/2523) - Removed `django-rq` dependency and support for RQ workers.
- [#2815](https://github.com/nautobot/nautobot/issues/2815) - Removed `pycryptodome` dependency as it is no longer used.
- [#2993](https://github.com/nautobot/nautobot/issues/2993) - Removed `NAUTOBOT_CELERY_RESULT_BACKEND` environment variable used to customize where Celery stores task results.
- [#2993](https://github.com/nautobot/nautobot/issues/2993) - Removed optional settings documentation for `CELERY_RESULT_BACKEND` as it is no longer user-serviceable.
- [#2993](https://github.com/nautobot/nautobot/issues/2993) - Removed optional settings documentation for `CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS` as it is no longer user-serviceable.
- [#3130](https://github.com/nautobot/nautobot/issues/3130) - Removed `CSS_CLASSES` definitions from legacy `ChoiceSets`.
