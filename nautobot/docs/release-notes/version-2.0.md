<!-- markdownlint-disable MD024 -->

# Nautobot v2.0

This document describes all new features and changes in Nautobot 2.0.

If you are a user migrating from Nautobot v1.X, please refer to the ["Upgrading from Nautobot v1.X"](../installation/upgrading-from-nautobot-v1.md) documentation.

## Release Overview

### Added

#### Generic Role Model ([#1063](https://github.com/nautobot/nautobot/issues/1063))

DeviceRole, RackRole, IPAM Role, and IPAddressRoleChoices have all been merged into a single generic Role model. A role can now be created and associated to one or more of the content-types that previously implemented role as a field. These model content-types include dcim.device, dcim.rack, virtualization.virtualmachine, ipam.ipaddress, ipam.prefix, and ipam.vlan.

#### Added Site Fields to Location ([#2954](https://github.com/nautobot/nautobot/issues/2954))

Added Site Model Fields to Location. Location Model now has `asn`, `comments`, `contact_email`, `contact_name`, `contact_phone`, `facility`, `latitude`, `longitude`, `physical_address`, `shipping_address` and `time_zone` fields.

#### Natural Key Support Across Nautobot Models ([#2900](https://github.com/nautobot/nautobot/issues/2900))

Nautobot's `BaseModel` base class and related classes now implement automatic support for Django [natural keys](https://docs.djangoproject.com/en/3.2/topics/serialization/#natural-keys) for lookup and referencing, as well as supporting a `natural_key_slug` concept similar to that introduced by `django-natural-keys`. (Nautobot does not depend on `django-natural-keys` but its implementation is heavily inspired by that project.) For example:

```python
>>> DeviceType.objects.first().natural_key()
['Arista', 'Arista DeviceType 15']

>>> DeviceType.objects.get_by_natural_key("Arista", "Arista DeviceType 15")
<DeviceType: Arista DeviceType 15>

>>> DeviceType.objects.first().natural_key_slug
'Arista&Arista+DeviceType+15'

>>> DeviceType.objects.get(natural_key_slug="Arista&Arista+DeviceType+15")
<DeviceType: Arista DeviceType 15>
```

Developers can refer to the [documentation on natural keys](../development/natural-keys.md) for details on how to support and use this feature.

### Changed

#### Aggregate model Migrated to Prefix ([#3302](https://github.com/nautobot/nautobot/issues/3302))

The `ipam.Aggregate` model has been removed and all existing aggregates will be migrated to `ipam.Prefix` with `type` set to "Container". The `Aggregate.date_added` field will be migrated to `Prefix.date_allocated` and changed from a Date field to a DateTime field with the time set to `00:00`. `Aggregate.tenant`, `Aggregate.rir` and `Aggregate.description` will be migrated over to the same fields on `Prefix`.

See the [upgrade guide](../installation/upgrading-from-nautobot-v1.md#aggregate-migrated-to-prefix) for more details on the data migration.

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

Check out the API and UI endpoints changes incurred by the changes stated above in the ["Upgrading from Nautobot v1.X"](../installation/upgrading-from-nautobot-v1.md) guide.

Check out the [Region and Site Related Data Model Migration Guide](../installation/region-and-site-data-migration-guide.md#region-and-site-related-data-model-migration-guide-for-existing-nautobot-app-installations) to learn how to migrate your Nautobot Apps and data models from `Site` and `Region` to `Location`.

#### Collapsed `nautobot.utilities` into `nautobot.core` ([#2721](https://github.com/nautobot/nautobot/issues/2721))

`nautobot.utilities` no longer exists as a separate Python module or Django app. Its functionality has been collapsed into the `nautobot.core` app. See details at [Python Code Location Changes](../installation/upgrading-from-nautobot-v1.md#python-code-location-changes).

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

Check out more Foreign Key related changes documented in the table [Renamed Database Fields](../installation/upgrading-from-nautobot-v1.md#renamed-database-fields)

In addition to the changes made to Foreign Key fields' own names, some of their `related_names` are also renamed:

For example in v1.x, to query `Circuit` objects with `CircuitTermination` instances located in sites ["ams01", "ams02", "atl03"], you would do:

```python
Circuit.objects.filter(terminations__site__in=["ams01", "ams02", "atl03"])
```

Now in v2.x, we have renamed the Foreign Key field `circuit`'s `related_name` attribute `terminations` on `CircuitTermination` Model to `circuit_terminations`, the same operations would look like:

```python
Circuit.objects.filter(circuit_terminations__site__in=["ams01", "ams02", "atl03"])
```

Check out more `related-name` changes documented in the table [Renamed Database Fields](../installation/upgrading-from-nautobot-v1.md#renamed-database-fields)

#### Renamed Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

Some filter fields have been renamed to reflect their functionalities better.

For example in v1.X, to filter `FrontPorts` that has a cable attached in the UI or make changes to them via Rest API, you would use the `cabled` filter:

`/dcim/front-ports/?cabled=True`

Now in v2.x, you would instead use the `has_cable` filter which has a more user-friendly name:

`/dcim/front-ports/?has_cable=True`

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../installation/upgrading-from-nautobot-v1.md#renamed-filter-fields)

#### Enhanced Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

Many filter fields have been enhanced to enable filtering by both slugs and UUID primary keys.

For example in v1.X, to filter `Regions` with a specific `parent` value in the UI or make changes to them via Rest API, you are only able to input slugs as the filter values:

`/dcim/regions/?parent=<slug>`

Now in v2.x, you are able to filter those `Regions` by slugs or UUID primary keys:

`/dcim/regions/?parent=<slug>` or `/dcim/regions/?parent=<uuid>`

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../installation/upgrading-from-nautobot-v1.md#enhanced-filter-fields)

#### Corrected Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

There were also instances where a foreign-key related field (e.g. `console_ports`) was incorrectly mapped to a boolean membership filter (e.g. `has_console_ports`), making it impossible to filter based on specific values of the foreign key:

For example in v1.x:

`/dcim/devices/?console_ports=True` and `/dcim/devices/?has_console_ports=True` are functionally the same and this behavior is **incorrect**.

This has been addressed in v2.x as follows:

`console_ports` and similar filters are taking foreign key UUIDs as input values and can be used in this format: `/dcim/devices/?console_ports=<uuid>` whereas `has_console_ports` and similar filters remain the same.

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../installation/upgrading-from-nautobot-v1.md#corrected-filter-fields)

#### Generic Role Model ([#1063](https://github.com/nautobot/nautobot/issues/1063))

The `DeviceRole`, `RackRole`, `ipam.Role`, and `IPAddressRoleChoices` have all been removed and replaced with a `extras.Role` model, This means that all references to any of the replaced models and choices now points to this generic role model.

In addition, the `role` field of the `IPAddress` model has also been changed from a choice field to a foreign key related field to the `extras.Role` model.

#### Prefix `is_pool` field and "Container" status replaced by new field `Prefix.type` ([#1362](https://github.com/nautobot/nautobot/issues/1362))

A new `type` field was added to `Prefix` to replace the `is_pool` boolean field and the "Container" status. The `type` field can be set to "Network", "Pool" or "Container", with "Network" being the default.

Existing prefixes with a status of "Container" will be migrated to the "Container" type. Existing prefixes with `is_pool` set will be migrated to the "Pool" type. Prefixes with both `is_pool` set and a status of "Container" will be migrated to the "Pool" type.

The "Container" status will be removed and all prefixes will be migrated to the "Active" status if it exists. If the "Active" status was deleted, prefixes will be migrated to the first available prefix status in the database that is not "Container".

### Removed

#### Removed Redundant Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

As a part of breaking changes made in v2.X, shadowed filter/filterset fields are being removed throughout Nautobot.

In Nautobot 1.x, for some of the foreign-key related fields:
    - The field was shadowed for the purpose of replacing the PK filter with a lookup-based on a more human-readable value (typically `slug`, if available).
    - A PK-based filter was available as well, generally with a name suffixed by `_id`

Now these two filter fields will be replaced by a single filter field that can support both slugs and UUID primary keys as inputs; As a result, PK-based filters suffixed by `_id` will no longer be supported in v2.0.

For example in v1.X, to filter `Devices` with a specific `site` value in the UI or make changes to them via Rest API with a UUID primary key, you will use:

`/dcim/devices/?site_id=<uuid>`

Now in v2.x, that format is no longer supported. Instead, you would use:

`/dcim/devices/?site=<uuid>`

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../installation/upgrading-from-nautobot-v1.md#removed-redundant-filter-fields)

#### Removed RQ support ([#2523](https://github.com/nautobot/nautobot/issue/2523))

Support for RQ and `django-rq`, deprecated since Nautobot 1.1.0, has been fully removed from Nautobot 2.0.

<!-- towncrier release notes start -->
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
