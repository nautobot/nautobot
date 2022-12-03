# Upgrading to a New Nautobot Release

## Review the Release Notes

Prior to upgrading your Nautobot instance, be sure to carefully review all [release notes](../release-notes/index.md) that
have been published since your current version was released. Although the upgrade process typically does not involve
additional work, certain releases may introduce breaking or backward-incompatible changes. These are called out in the
release notes under the release in which the change went into effect.

The below sub-sections describe some key changes that deployers should be aware of, but are not intended to be a replacement for reading the release notes carefully and in depth.

### Updating from Nautobot 1.0.x to 1.1.x

#### Migration from RQ to Celery

Prior to version 1.1.0, Nautobot utilized RQ as the primary background task worker. As of Nautobot 1.1.0, RQ is now *deprecated*, as Celery has been introduced to eventually replace RQ for executing background tasks within Nautobot. All Nautobot **core** usage of RQ has been migrated to use Celery.

RQ support for custom tasks was not removed in order to give plugin authors time to migrate, however, to continue to utilize advanced Nautobot features such as Git repository synchronization, webhooks, jobs, etc. you must migrate your `nautobot-worker` deployment from RQ to Celery.

Please see the section on [migrating to Celery from RQ](./services.md#migrating-to-celery-from-rq) for more information on how to easily migrate your deployment.

### Updating from Nautobot 1.1.x to 1.2.x

#### Introduction of Celery Beat Scheduler

As of Nautobot v1.2.0, Nautobot supports deferring ("scheduling") Jobs. To facilitate this, a new service called `celery-scheduler` is now required. Please review the [service installation documentation](./services.md#celery-beat-scheduler) to find out how to set it up.

### Updating from Nautobot 1.2.x to 1.3.x

#### Revision of Recommended MySQL UTF-8 Encoding

The recommended database encoding settings have been revised to rely upon the default UTF-8 encoding provided by MySQL for collation of data in the database. Previously we were recommending in our documentation that the collation encoding be set explicitly to `utf8mb4_bin`. We are now recommending  `utf8mb4_0900_ai_ci` which is configured by default on unmodified MySQL database server deployments.

The collation encoding is used to inform MySQL how characters are sorted in the database. This is important when it comes to retrieving data that has special characters or special byte-encoding such as accents or ligatures, and also including emojis. In some cases, with the `utf8mb4_bin` encoding we were previously recommending, case-insensitive searching may return inconsistent or incorrect results.

!!! danger
    It is **strongly recommended** that you backup your database before executing this query and that you perform this in a non-production environment to identify any potential issues prior to updating your production environment.

If you have an existing MySQL database, you may update your database to use the recommended encoding by using `nautobot-server dbshell` to launch a database shell and executing the following command:

```no-highlight
$ nautobot-server dbshell
mysql> ALTER DATABASE nautobot COLLATE utf8mb4_0900_ai_ci;
Query OK, 1 row affected (0.07 sec)
```

Please see the [official MySQL documentation on migrating collation encoding settings](https://dev.mysql.com/blog-archive/mysql-8-0-collations-migrating-from-older-collations/) for more information on troubleshooting any issues you may encounter.

### Updating from Nautobot 1.5 to 2.0

#### Enhanced Filter Fields

Below is a table documenting [enhanced filter field changes](../release-notes/version-2.0.md#enhanced-filter-fields-2804) in v2.x.

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

#### Corrected Filter Fields

Below is a table documenting [corrected filter field changes](../release-notes/version-2.0.md#corrected-filter-fields-2804) in v2.x.

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

#### Removed Redundant Filter Fields

Below is a table documenting [removed redundant filter field changes](../release-notes/version-2.0.md#removed-redundant-filter-fields-2804) in v2.x.

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

## Update Prerequisites to Required Versions

Nautobot v1.3.0 and later requires the following:

| Dependency | Minimum Version |
|------------|-----------------|
| Python     | 3.7             |
| PostgreSQL | 9.6             |
| Redis      | 4.0             |

Nautobot v1.1.0 and later can optionally support the following:

> *Nautobot v1.1.0 added support for MySQL 8.0 as a database backend as an alternative to PostgreSQL.*

| Dependency | Minimum Version |
|------------|-----------------|
| MySQL      | 8.0             |

!!! tip
    If you wish to migrate from PostgreSQL to MySQL, we recommend creating a new Nautobot installation based on MySQL and then [migrating the database contents to the new installation](./migrating-from-postgresql.md), rather than attempting an in-place upgrade or migration.

## Install the Latest Release

As with the initial installation, you can upgrade Nautobot by installing the Python package directly from the Python Package Index (PyPI).

!!! warning
    Unless explicitly stated, all steps requiring the use of `pip3` or `nautobot-server` in this document should be performed as the `nautobot` user!

Upgrade Nautobot using `pip3`:

```no-highlight
$ pip3 install --upgrade nautobot
```

## Upgrade your Optional Dependencies

If you do not have any optional dependencies, you may skip this step.

Once the new code is in place, verify that any optional Python packages required by your deployment (e.g. `napalm` or
`django-auth-ldap`) are listed in `local_requirements.txt`.

Then, upgrade your dependencies using `pip3`:

```no-highlight
$ pip3 install --upgrade -r $NAUTOBOT_ROOT/local_requirements.txt
```

## Run the Post Upgrade Operations

Finally, run Nautobot's `post_upgrade` management command:

```no-highlight
$ nautobot-server post_upgrade
```

This command performs the following actions:

* Applies any database migrations that were included in the release
* Generates any missing cable paths among all cable termination objects in the database
* Collects all static files to be served by the HTTP service
* Deletes stale content types from the database
* Deletes all expired user sessions from the database
* Clears all cached data to prevent conflicts with the new release

## Restart the Nautobot Services

Finally, with root permissions, restart the web and background services:

```no-highlight
$ sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```
