<!-- markdownlint-disable MD024 -->

# Nautobot v2.0

This document describes all new features and changes in Nautobot 2.0.

If you are a user migrating from Nautobot v1.X, please refer to the ["Upgrading from Nautobot v1.X"](../installation/upgrading-from-nautobot-v1.md) documentation.

## Release Overview

### Added

#### Added Site Fields to Location ([#2954](https://github.com/nautobot/nautobot/issues/2954))

Added Site Model Fields to Location. Location Model now has `asn`, `comments`, `contact_email`, `contact_name`, `contact_phone`, `facility`, `latitude`, `longitude`, `physical_address`, `shipping_address` and `time_zone` fields.

### Changed

#### Collapse Region and Site Models into Location ([#2517](https://github.com/nautobot/nautobot/issues/2517))

##### Initial Data Migration

The `Site` and `Region` models have been removed in v2.0 and have been replaced with `Location` of specific `LocationType`. As a result, the existing `Site` and `Region` data will be migrated to corresponding `LocationType` and `Location` objects. Here is what to expect:

1. If you do not have any `Site` and `Region` instances in your existing database, running this data migration will do nothing.
2. If you only have `Region` instances in your existing database, a `LocationType` named "Region" will be created and for each legacy `Region` instance, a corresponding `Location` instance with the same attributes (`name`, `description`, etc.) and hierarchy will be created.
3. If you only have `Site` instances in your existing database:

    - A `LocationType` named "Site" will be created and every root level `LocationType` in your database will have the new "Site" `LocationType` as their parent.

    - For each legacy `Site` instance, a corresponding `Location` instance with the same attributes (`name`, `description`, `tenant`, `facility`, `asn`, `latitude`, `longitude`, etc.) will be created.

    - Model instances that had a `site` field (`CircuitTermination`, `Device`, `PowerPanel`, `RackGroup`, `Rack`, `Prefix`, `VLANGroup`, `VLAN`, `Cluster`) assigned and *did not* have a `location` attribute assigned will be updated to have their `location` point to the new `Location` corresponding to that `Site`. All other attributes on these models will remain unchanged.

    For Example:

    - We will start with a `Site` instance with name **AMS01** as the base `Site` for two top-level `Location` objects with names **root-01** and **root-02** respectively.

    - During the data migration, a `LocationType` named **Site** will be created, and a `Location` of **Site** `LocationType` named **AMS01** with all the information (`asn`, `latitude`, etc.) from the base `Site` will be created.

    - The `Location` objects named **root-01** and **root-02** will have this **AMS01** `Location` set as their `parent`.

4. If you have both `Site` and `Region` instances in your existing database:

    - A `LocationType` named **Region** will be created.

    - For each legacy `Region` instance, a corresponding `Location` instance with the same attributes (`name`, `description`, etc.) will be created.

    - A `LocationType` named **Site** will be created with the new `LocationType` named **Region** set as its `parent`.

    - Every pre-existing root-level `LocationType` in your database will be updated to have the new `LocationType` named **Site** as its `parent`.

    - For each legacy `Site` instance, a corresponding "Site" `Location` instance with the same attributes (`name`, `description`, `tenant`, `facility`, `asn`, `latitude`, `longitude`, etc.) will be created with its parent set to the corresponding "Region" `Location` if any.

        - If you have `Site` instances in your database without a `Region` assigned to them, one additional `Location` named **Global Region** of `LocationType` **Region** will be created and each `Location` of `LocationType` **Site** created from the legacy region-less `Site` instances will have the **Global Region** `Location` as their parent.

    - Model instances that had a `site` attribute (`CircuitTermination`, `Device`, `PowerPanel`, `RackGroup`, `Rack`, `Prefix`, `VLANGroup`, `VLAN`, `Cluster`) assigned and *did not* have a `location` attribute assigned will be updated to have their `location` point to the new `Location` of `LocationType` **Site**. All other attributes on these models will remain unchanged.

    For Example:

    - There are two `Site` instances and one `Region` instance in your existing database. The `Region` with name **America** has one child `Site` instance named **AMS01**. And the other `Site` instance named **AUS01** is not associated with any `Region` (`region` attribute is set to `None`).

    - The `Site` **AMS01** is the base `Site` for two top-level `Location` objects with names **root-01** and **root-02** respectively.

    - During the data migration, a `LocationType` named **Region** and a `Location` of this `LocationType` named **America** with all the same information will be created.

    - The `LocationType` named **Site** with its `parent` set as the new `LocationType` **Region** and a `Location` of `LocationType` named **AMS01** with all the same information (`asn`, `latitude`, etc.) will be created. The `Location` **AMS01** will have `Location` **America** as its `parent` and each - `Location` **root-01** and **root-02** will have `Location` **AMS01** as its `parent`.

    - Finally, the `Site` instance **AUS01**, since it does not have a `Region` instance associated with it, its corresponding `Location` **AUS01** will have a new `Location` named **Global Region** of `LocationType` **Region** as its `parent`.

    - In addition, legacy `Site` instance with name **AMS01** also has three `Device` instances associated with it named **ams01-edge-01**, **ams01-edge-02**,  and **ams01-edge-03**.

    - However, **ams01-edge-01** only has its `site` attribute set as `Site` **AMS01** whereas **ams01-edge-02** and **ams01-edge-03** have both its `site` and `location` attributes set `Site` **AMS01** and `Location` **root-01** respectively.

    - During the data migration, **ams01-edge-01**'s `location` attribute will point to the new `Location` of `LocationType` **Site** with name **AMS01** while devices **ams01-edge-02** and **ams01-edge-03** will remain unchanged.

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

### Removed

#### Removed Redundant Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

As a part of breaking changes made in v2.X, shadowed filter/filterset fields are being removed in the DCIM app:

Currently for some of the foreign-key related fields:
    - The field is shadowed for the purpose of replacing the PK filter with a lookup-based on a more human-readable value (typically `slug`, if available).
    - A PK-based filter is available as well, generally with a name suffixed by `_id`

Now these two filter fields will be replaced by a single filter field that can support both slugs and UUID primary keys as inputs; As a result, PK-based filters suffixed by `_id` will no longer be supported in v2.0.

For example in v1.X, to filter `Devices` with a specific `site` value in the UI or make changes to them via Rest API with a UUID primary key, you will use:

`/dcim/devices/?site_id=<uuid>`

Now in v2.x, that format is no longer supported. Instead, you would use:

`/dcim/devices/?site=<uuid>`

Check out the specific changes documented in the table at [UI and REST API Filter Changes](../installation/upgrading-from-nautobot-v1.md#removed-redundant-filter-fields)

<!-- towncrier release notes start -->
