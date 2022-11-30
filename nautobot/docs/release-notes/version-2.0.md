<!-- markdownlint-disable MD024 -->

# Nautobot v2.0

This document describes all new features and changes in Nautobot 2.0.

If you are a user migrating from Nautobot v1.X, please refer to the ["Upgrading from Nautobot v1.X"](../installation/upgrading-from-nautobot-v1.md) documentation.

## Release Overview

### Added

### Changed

#### Enhanced Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

In nautobot v2.X, we changed some of the filter fields to enable filtering by both slugs and UUID primary keys:

For example in v1.X, to filter `Regions` with a specific `parent` value in the UI or make changes to them via Rest API, you are only able to input slugs as the filter values:

`/dcim/regions/?parent=<slug>`

Now in v2.x, you are able to filter those `Regions` by slugs or UUID primary keys:

`/dcim/regions/?parent=<slug>` or `/dcim/regions/?parent=<uuid>`

Below is a table documenting all such changes and where they occurred.

| Filterset                      | Enhanced Filter Field| Changes                                                    | UI and Rest API endpoints Available in v2.X                                                                   |
|--------------------------------|--------------------|------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|
| ConsolePortFilterSet           | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-ports/?device=<uuid>` and `/dcim/console-ports/?device=<name>`                                 |
|                                | cabled             | Renamed to has_cable                                       | `/dcim/console-ports/?has_cable=True` and `/dcim/console-ports/?has_cable=False`                              |
| ConsoleServerPortFilterSet     | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-server-ports/?device=<uuid>` and `/dcim/console-server-ports/?device=<name>`                   |
|                                | cabled             | Renamed to has_cable                                       | `/dcim/console-server-ports/?has_cable=True` and `/dcim/console-server-ports/?has_cable=False`                |
| DeviceFilterSet                | manufacturer       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?manufacturer=<uuid>` and `/dcim/devices/?manufacturer=<slug>`                                 |
|                                | device_type_id     | Renamed to device_type Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?device_type=<uuid>` and `/dcim/devices/?device_type=<slug>`            |
|                                | role               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?role=<uuid>` and `/dcim/devices/?role=<slug>`                                                 |
|                                | platform           | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?platform=<uuid>` and `/dcim/devices/?platform=<slug>`                                         |
|                                | rack_group_id      | Renamed to rack_group                                      | `/dcim/devices/?rack_group=<uuid>` and `/dcim/devices/?rack_group=<slug>`                                     |
|                                | rack_id            | Renamed to rack Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack=<uuid>` and `/dcim/devices/?rack=<slug>`                                 |
|                                | cluster_id         | Renamed to cluster Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?cluster=<uuid>` and `/dcim/devices/?cluster=<slug>`                        |
|                                | model              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?model=<uuid>` and `/dcim/devices/?model=<slug>`                                               |
|                                | serial             | Enhanced to permit filtering on multiple values            | `/dcim/devices/?serial=<value>&serial=<value>...`                                                             |
|                                | secrets_group      | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?secrets_group=<uuid>` and `/dcim/devices/?secrets_group=<slug>`                               |
|                                | virtual_chassis_id | Renamed to virtual_chassis Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?virtual_chassis=<uuid>` and `/dcim/devices/?virtual_chassis=<slug>`|
|                                | site               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?site=<uuid>` and `/dcim/devices/?site=<slug>`                                                 |
| DeviceBayFilterSet             | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/device-bays/?device=<uuid>` and `/dcim/device-bays/?device=<name>`                                     |
|                                | cable              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid>` and `/dcim/regions/?parent=<slug>`                                             |
| DeviceTypeFilterSet            | manufacturer       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/device-types/?manufacturer=<uuid>` and `/dcim/device-types/?manufacturer=<slug>`                       |
| FrontPortFilterSet             | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/front-ports/?device=<uuid>` and `/dcim/front-ports/?device=<name>`                                     |
|                                | cabled             | Renamed to has_cable                                       | `/dcim/front-ports/?has_cable=True` and `/dcim/front-ports/?has_cable=False`                                  |
| InterfaceFilterSet             | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/interfaces/?device=<uuid>` and `/dcim/interfaces/?device=<name>`                                       |
|                                | cabled             | Renamed to has_cable                                       | `/dcim/interfaces/?has_cable=True` and `/dcim/interfaces/?has_cable=False`                                    |
| InventoryItemFilterSet         | site               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?site=<uuid>` and `/dcim/inventory-items/?site=<slug>`                                 |
|                                | device             | Enhanced to support primary key UUIDs in addition to name  | `/dcim/inventory-items/?device=<uuid>` and `/dcim/inventory-items/?has_cable=False`                           |
|                                | manufacturer       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?manufacturer=<uuid>` and `/dcim/inventory-items/?manufacturer=<slug>`                 |
|                                | serial             | Enhanced to permit filtering on multiple values            | `/dcim/inventory-items/?serial=<value>&serial=<value>...`                                                     |
| PlatformFilterSet              | manufacturer       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/platforms/?manufacturer=<slug>` and `/dcim/platforms/?manufacturer=<slug>`                             |
| PowerFeedFilterSet             | site               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/power-feeds/?site=<uuid>` and `/dcim/power-feeds/?site=<slug>`                                         |
|                                | cabled             | Renamed to has_cable                                       | `/dcim/power-feeds/?has_cable=True` and `/dcim/power-feeds/?has_cable=False`                                  |
| PowerOutletFilterSet           | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-outlets/?device=<uuid>` and `/dcim/power-outlets/?device=<name>`                                 |
|                                | cabled             | Renamed to has_cable                                       |  `/dcim/power-outlets/?has_cable=True` and `/dcim/power-outlets/?has_cable=False`                             |
| PowerPortFilterSet             | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-ports/?device=<uuid>` and `/dcim/power-ports/?device=<name>`                                     |
|                                | cabled             | Renamed to has_cable                                       | `/dcim/power-ports/?has_cable=True` and `/dcim/power-ports/?has_cable=False`                                  |
| RackFilterSet                  | role               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/racks/?role=<uuid>` and `/dcim/racks/?role=<slug>`                                                     |
|                                | serial             | Enhanced to permit filtering on multiple values            | `/dcim/racks/?serial=<value>&serial=<value>...`                                                               |
| RackGroupFilterSet             | parent             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-groups/?parent=<uuid>` and `/dcim/rack-groups/?parent=<slug>`                                     |
| RackReservationFilterSet       | user               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-reservations/?user=<uuid>` and `/dcim/rack-reservations/?user=<slug>`                             |
| RearPortFilterSet              | device             | Enhanced to support primary key UUIDs in addition to names | `/dcim/rear-ports/?device=<uuid>` and `/dcim/rear-ports/?device=<name>`                                       |
|                                | cabled             | Renamed to has_cable                                       | `/dcim/rear-ports/?has_cable=True` and `/dcim/rear-ports/?has_cable=False`                                    |
| RegionFilterSet                | parent             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid>` and `/dcim/regions/?parent=<slug>`                                             |
| VirtualChassisFilterSet        | site               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?site=<uuid>` and `/dcim/virtual-chassis/?site=<slug>`                                 |
|                                | master             | Enhanced to support primary key UUIDs in addition to name  | `/dcim/virtual-chassis/?master=<uuid>` and `/dcim/virtual-chassis/?master=<name>`                             |
|                                | tenant             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?tenant=<uuid>` and `/dcim/virtual-chassis/?tenant=<slug>`                             |

#### Corrected Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

There were also instances where a foreign-key related field (e.g. `console_ports`) was incorrectly mapped to a boolean membership filter (e.g. `has_console_ports`), making it impossible to filter based on specific values of the foreign key:

For example in v1.x:

`/dcim/devices/?console_ports=True` and `/dcim/devices/?has_console_ports=True` are functionally the same and this behavior is **incorrect**.

This has been addressed in v2.x as follows:

`console_ports` and similar filters are taking foreign key UUIDs as input values and can be used in this format: `/dcim/devices/?console_ports=<uuid>` whereas `has_console_ports` and similar filters remain the same.

Below is a table documenting all such changes and where they occurred.

| Filterset       | Changed Filter Field | Before                                     | After                                           |
|-----------------|----------------------|--------------------------------------------|-------------------------------------------------|
| DeviceFilterSet | console_ports        | `/dcim/devices/?console_ports=True`        | `/dcim/devices/?console_ports=<uuid>`           |
|                 | console_server_ports | `/dcim/devices/?console_server_ports=True` | `/dcim/devices/?console_server_ports=<uuid>`    |
|                 | device_bays          | `/dcim/devices/?device_bays=True`          | `/dcim/devices/?device_bays=<uuid>`             |
|                 | front_ports          | `/dcim/devices/?front_ports=True`          | `/dcim/devices/?front_ports=<uuid>`             |
|                 | interfaces           | `/dcim/devices/?interfaces=True`           | `/dcim/devices/?interfaces=<uuid>`              |
|                 | rear_ports           | `/dcim/devices/?rear_ports=True`           | `/dcim/devices/?rear_ports=<uuid>`              |
|                 | power_ports          | `/dcim/devices/?power_ports=True`          | `/dcim/devices/?power_ports=<uuid>`             |
|                 | power_outlets        | `/dcim/devices/?power_outlets=True`        | `/dcim/devices/?power_outlets=<uuid>`           |

### Removed

#### Removed Redundant Filter Fields ([#2804](https://github.com/nautobot/nautobot/pull/2804))

As a part of breaking changes made in v2.X, shadowed filter/filterset fields are being removed in the dcim app:

Currently for some of the foreign-key related fields:
    - The field is shadowed for the purpose of replacing the PK filter with a lookup-based on a more human-readable value (typically `slug`, if available).
    - A PK-based filter is available as well, generally with a name suffixed by `_id`

Now these two filter fields will be replaced by a single filter field that can support both slugs and UUID primary keys as inputs; As a result, PK-based filters suffixed by `_id` will no longer be supported in v2.0.

For example in v1.X, to filter `Devices` with a specific `site` value in the UI or make changes to them via Rest API with a UUID primary key, you will use:

`/dcim/devices/?site_id=<uuid>`

Now in v2.x, that format is no longer supported. Instead, you would use:

`/dcim/devices/?site=<uuid>`

Below is a table documenting all such changes and where they occurred.

| Filterset                      |Removed Filter Field| UI and API endpoints that are no longer supported in v2.X                     |
|--------------------------------|--------------------|-------------------------------------------------------------------------------|
| CircuitTerminationFilterSet    | region_id          | `/circuits/circuit-terminations/?region_id=<uuid>` is no longer supported     |
|                                | site_id            | `/circuits/circuit-terminations/?site_id=<uuid>` is no longer supported       |
| ClusterFilterSet               | region_id          | `/virtualization/clusters/?region_id=<uuid>` is no longer supported           |
|                                | site_id            | `/virtualization/clusters/?site_id=<uuid>` is no longer supported             |
| ConsolePortFilterSet           | region_id          | `/dcim/console-ports/?region_id=<uuid>` is no longer supported                |
|                                | device_id          | `/dcim/console-ports/?device_id=<uuid>` is no longer supported                |
| ConsoleServerPortFilterSet     | region_id          | `/dcim/console-server-ports/?region_id=<uuid>` is no longer supported         |
|                                | device_id          | `/dcim/console-server-ports/?device_id=<uuid>` is no longer supported         |
| DeviceFilterSet                | region_id          | `/dcim/devices/?region_id=<uuid>` is no longer supported                      |
|                                | site_id            | `/dcim/devices/?site_id=<uuid>` is no longer supported                        |
|                                | manufacturer_id    | `/dcim/devices/?manufacturer_id=<uuid>` is no longer supported                |
|                                | role_id            | `/dcim/devices/?role_id=<uuid>` is no longer supported                        |
|                                | platform_id        | `/dcim/devices/?platform_id=<uuid>` is no longer supported                    |
|                                | secrets_group_id   | `/dcim/devices/?secrets_group_id=<uuid>` is no longer supported               |
|                                | pass_through_ports | `/dcim/devices/?pass_through_ports=<bool>` is no longer supported             |
| DeviceBayFilterSet             | region_id          | `/dcim/device-bays/?region_id=<uuid>` is no longer supported                  |
|                                | device_id          | `/dcim/device-bays/?device_id=<uuid>` is no longer supported                  |
| DeviceTypeFilterSet            | manufacturer_id    | `/dcim/device-types/?manufacturer_id=<uuid>` is no longer supported           |
| FrontPortFilterSet             | region_id          | `/dcim/front-ports/?region_id=<uuid>` is no longer supported                  |
|                                | device_id          | `/dcim/front-ports/?device_id=<uuid>` is no longer supported                  |
| InterfaceFilterSet             | region_id          | `/dcim/interfaces/?region_id=<uuid>` is no longer supported                   |
|                                | device_id          | `/dcim/interfaces/?device_id=<uuid>` is no longer supported                   |
|                                | lag_id             | `/dcim/interfaces/?lag_id=<uuid>` is no longer supported                      |
| InventoryItemFilterSet         | region_id          | `/dcim/inventory-items/?region_id=<uuid>` is no longer supported              |
|                                | site_id            | `/dcim/inventory-items/?site_id=<uuid>` is no longer supported                |
|                                | device_id          | `/dcim/inventory-items/?device_id=<uuid>` is no longer supported              |
|                                | parent_id          | `/dcim/inventory-items/?parent_id=<uuid>` is no longer supported              |
|                                | manufacturer_id    | `/dcim/inventory-items/?manufacturer_id=<uuid>` is no longer supported        |
| RackFilterSet                  | region_id          | `/dcim/racks/?region_id=<uuid>` is no longer supported                        |
|                                | site_id            | `/dcim/racks/?site_id=<uuid>` is no longer supported                          |
|                                | group_id           | `/dcim/racks/?group_id=<uuid>` is no longer supported                         |
|                                | role_id            | `/dcim/racks/?role_id=<uuid>` is no longer supported                          |
| RackGroupFilterSet             | region_id          | `/dcim/rack-groups/?region_id=<uuid>` is no longer supported                  |
|                                | site_id            | `/dcim/rack-groups/?site_id=<uuid>` is no longer supported                    |
|                                | parent_id          | `/dcim/rack-groups/?parent_id=<uuid>` is no longer supported                  |
| RackReservationFilterSet       | rack_id            | `/dcim/rack-reservations/?rack_id=<uuid>` is no longer supported              |
|                                | group_id           | `/dcim/rack-reservations/?group_id=<uuid>` is no longer supported             |
|                                | user_id            | `/dcim/rack-reservations/?user_id=<uuid>` is no longer supported              |
|                                | site_id            | `/dcim/rack-reservations/?site_id=<uuid>` is no longer supported              |
| RearPortFilterSet              | region_id          | `/dcim/rear-ports/?region_id=<uuid>` is no longer supported                   |
|                                | device_id          | `/dcim/rear-ports/?device_id=<uuid>` is no longer supported                   |
| RegionFilterSet                | parent_id          | `/dcim/regions/?parent_id=<uuid>` is no longer supported                      |
| PlatformFilterSet              | manufacturer_id    | `/dcim/platforms/?manufacturer_id=<uuid>` is no longer supported              |
| PowerOutletFilterSet           | region_id          | `/dcim/power-outlets/?region_id=<uuid>` is no longer supported                |
|                                | device_id          | `/dcim/power-outlets/?device_id=<uuid>` is no longer supported                |
| PowerFeedFilterSet             | region_id          | `/dcim/power-feeds/?region_id=<uuid>` is no longer supported                  |
|                                | site_id            | `/dcim/power-feeds/?site_id=<uuid>` is no longer supported                    |
|                                | power_panel_id     | `/dcim/power-feeds/?power_panel_id=<uuid>` is no longer supported             |
|                                | rack_id            | `/dcim/power-feeds/?rack_id=<uuid>` is no longer supported                    |
| PowerPanelFilterSet            | region_id          | `/dcim/power-panels/?region_id=<uuid>` is no longer supported                 |
|                                | site_id            | `/dcim/power-panels/?site_id=<uuid>` is no longer supported                   |
|                                | rack_group_id      | `/dcim/power-panels/?rack_group_id=<uuid>` is no longer supported             |
| PowerPortFilterSet             | region_id          | `/dcim/power-ports/?region_id=<uuid>` is no longer supported                  |
|                                | device_id          | `/dcim/power-ports/?device_id=<uuid>` is no longer supported                  |
| PrefixFilterSet                | region_id          | `/ipam/prefixes/?region_id=<uuid>` is no longer supported                     |
|                                | site_id            | `/ipam/prefixes/?site_id=<uuid>` is no longer supported                       |
| SiteFilterSet                  | region_id          | `/dcim/sites/?region_id=<uuid>` is no longer supported                        |
| VirtualChassisFilterSet        | region_id          | `/dcim/virtual-chassis/?region_id=<uuid>` is no longer supported              |
|                                | site_id            | `/dcim/virtual-chassis/?site_id=<uuid>` is no longer supported                |
|                                | master_id          | `/dcim/virtual-chassis/?master_id=<uuid>` is no longer supported              |
|                                | tenant_id          | `/dcim/virtual-chassis/?tenant_id=<uuid>` is no longer supported              |
| VLANGroupFilterSet             | region_id          | `/ipam/vlan-groups/?region_id=<uuid>` is no longer supported                  |
|                                | site_id            | `/ipam/vlan-groups/?site_id=<uuid>` is no longer supported                    |
| VLANFilterSet                  | region_id          | `/ipam/vlans/?region_id=<uuid>` is no longer supported                        |
|                                | site_id            | `/ipam/vlans/?site_id=<uuid>` is no longer supported                          |

<!-- towncrier release notes start -->
