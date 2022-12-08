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

| Model                 | Enhanced Filter Field| Changes                                                  | UI and Rest API endpoints Available in v2.X|
|-----------------------|----------------------|------------------------------------------------------------|----------------------------------------------|
| ConsolePort           | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-ports/?device=<uuid|name>`|
|                       | `cabled`             | Renamed to `has_cable`                                     | `/dcim/console-ports/?has_cable=True|False`|
| ConsoleServerPort     | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-server-ports/?device=<uuid|name>`|
|                       | `cabled`             | Renamed to `has_cable`                                     | `/dcim/console-server-ports/?has_cable=True|False`|
| Device                | `manufacturer`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?manufacturer=<uuid|slug>`|
|                       | `device_type_id`     | Renamed to `device_type` and enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?device_type=<uuid|slug>`|
|                       | `role`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?role=<uuid|slug>`|
|                       | `platform`           | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?platform=<uuid|slug>`|
|                       | `rack_group_id`      | Renamed to `rack_group`                                    | `/dcim/devices/?rack_group=<uuid|slug>`|
|                       | `rack_id`            | Renamed to `rack` and enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack=<uuid|slug>`|
|                       | `cluster_id`         | Renamed to `cluster` and enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?cluster=<uuid|slug>`|
|                       | `model`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?model=<uuid|slug>`|
|                       | `serial`             | Enhanced to permit filtering on multiple values            | `/dcim/devices/?serial=<value>&serial=<value>...`|
|                       | `secrets_group`      | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?secrets_group=<uuid|slug>`|
|                       | `virtual_chassis_id` | Renamed to `virtual_chassis` and enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?virtual_chassis=<uuid|slug>`|
|                       | `site`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?site=<uuid|slug>`|
| DeviceBay             | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/device-bays/?device=<uuid|name>`|
|                       | `cable`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid|slug>`|
| DeviceType            | `manufacturer`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/device-types/?manufacturer=<uuid|slug>`|
| FrontPort             | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/front-ports/?device=<uuid|name>`
|                       | `cabled`             | Renamed to `has_cable`                                     | `/dcim/front-ports/?has_cable=True|False`|
| Interface             | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/interfaces/?device=<uuid|name>`|
|                       | `cabled`             | Renamed to `has_cable`                                     | `/dcim/interfaces/?has_cable=True|False`|
| InventoryItem         | `site`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?site=<uuid|slug>`|
|                       | `device`             | Enhanced to support primary key UUIDs in addition to name  | `/dcim/inventory-items/?device=<uuid|name>`|
|                       | `manufacturer`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?manufacturer=<uuid|slug>`|
|                       | `serial`             | Enhanced to permit filtering on multiple values            | `/dcim/inventory-items/?serial=<value>&serial=<value>...`|
| Platform              | `manufacturer`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/platforms/?manufacturer=<uuid|slug>`|
| PowerFeed             | `site`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/power-feeds/?site=<uuid|slug>`|
|                       | `cabled`             | Renamed to `has_cable`                                     | `/dcim/power-feeds/?has_cable=True|False`|
| PowerOutlet           | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-outlets/?device=<uuid|name>`|
|                       | `cabled`             | Renamed to `has_cable`                                     |  `/dcim/power-outlets/?has_cable=True|False`|
| PowerPort             | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-ports/?device=<uuid|name>`|
|                       | `cabled`             | Renamed to `has_cable`                                     | `/dcim/power-ports/?has_cable=True|False`|
| Rack                  | `role`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/racks/?role=<uuid|slug>`|
|                       | `serial`             | Enhanced to permit filtering on multiple values            | `/dcim/racks/?serial=<value>&serial=<value>...`|
| RackGroup             | `parent`             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-groups/?parent=<uuid|slug>`|
| RackReservation       | `user`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-reservations/?user=<uuid|slug>`|
| RearPort              | `device`             | Enhanced to support primary key UUIDs in addition to names | `/dcim/rear-ports/?device=<uuid|name>`|
|                       | `cabled`             | Renamed to `has_cable`                                     | `/dcim/rear-ports/?has_cable=True|False`|
| Region                | `parent`             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid|slug>`|
| VirtualChassis        | `site`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?site=<uuid|slug>`|
|                       | `master`             | Enhanced to support primary key UUIDs in addition to name  | `/dcim/virtual-chassis/?master=<uuid|name>`|
|                       | `tenant`             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?tenant=<uuid|slug>`|

#### Corrected Filter Fields

Below is a table documenting [corrected filter field changes](../release-notes/version-2.0.md#corrected-filter-fields-2804) in v2.x.

| Model  | Changed Filter Field   | Before                                     | After                                                                                   |
|--------|------------------------|--------------------------------------------|-----------------------------------------------------------------------------------------|
| Device | `console_ports`        | `/dcim/devices/?console_ports=True`        | `/dcim/devices/?console_ports=<uuid>` or `?has_console_ports=<True|False>`              |
|        | `console_server_ports` | `/dcim/devices/?console_server_ports=True` | `/dcim/devices/?console_server_ports=<uuid>` or `?has_console_server_ports=<True|False>`|
|        | `device_bays`          | `/dcim/devices/?device_bays=True`          | `/dcim/devices/?device_bays=<uuid>` or `?has_device_bays=<True|False>`                  |
|        | `front_ports`          | `/dcim/devices/?front_ports=True`          | `/dcim/devices/?front_ports=<uuid>` or `?has_front_ports=<True|False>`                  |
|        | `interfaces`           | `/dcim/devices/?interfaces=True`           | `/dcim/devices/?interfaces=<uuid>` or `?has_interfaces=<True|False>`                    |
|        | `rear_ports`           | `/dcim/devices/?rear_ports=True`           | `/dcim/devices/?rear_ports=<uuid>` or `?has_rear_ports=<True|False>`                    |
|        | `power_ports`          | `/dcim/devices/?power_ports=True`          | `/dcim/devices/?power_ports=<uuid>` or `?has_power_ports=<True|False>`                  |
|        | `power_outlets`        | `/dcim/devices/?power_outlets=True`        | `/dcim/devices/?power_outlets=<uuid>` or `?has_power_outlets=<True|False>`              |

#### Removed Redundant Filter Fields

Below is a table documenting [removed redundant filter field changes](../release-notes/version-2.0.md#removed-redundant-filter-fields-2804) in v2.x.

| Model                 |Removed Filter Field | UI and API endpoints that are no longer supported in v2.X                              |
|-----------------------|---------------------|----------------------------------------------------------------------------------------|
| CircuitTermination    | `region_id`         | instead of `/circuits/circuit-terminations/?region_id=<uuid>`, use `region=<uuid>`     |
|                       | `site_id`           | instead of `/circuits/circuit-terminations/?site_id=<uuid>`, use `site=<uuid>`         |
| Cluster               | `region_id`         | instead of `/virtualization/clusters/?region_id=<uuid>`, use `region=<uuid>`           |
|                       | `site_id`           | instead of `/virtualization/clusters/?site_id=<uuid>` , use `site=<uuid>`              |
| ConsolePort           | `region_id`         | instead of `/dcim/console-ports/?region_id=<uuid>`, use `region=<uuid>`                |
|                       | `device_id`         | instead of `/dcim/console-ports/?device_id=<uuid>`, use `device=<uuid>`                |
| ConsoleServerPort     | `region_id`         | instead of `/dcim/console-server-ports/?region_id=<uuid>`, use `region=<uuid>`         |
|                       | `device_id`         | instead of `/dcim/console-server-ports/?device_id=<uuid>`, use `device=<uuid>`         |
| Device                | `region_id`         | instead of `/dcim/devices/?region_id=<uuid>`, use `region=<uuid>`                      |
|                       | `site_id`           | instead of `/dcim/devices/?site_id=<uuid>`, use `site=<uuid>`                          |
|                       | `manufacturer_id`   | instead of `/dcim/devices/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`          |
|                       | `role_id`           | instead of `/dcim/devices/?role_id=<uuid>`, use `role=<uuid>`                          |
|                       | `platform_id`       | instead of `/dcim/devices/?platform_id=<uuid>`, use `platform=<uuid>`                  |
|                       | `secrets_group_id`  | instead of `/dcim/devices/?secrets_group_id=<uuid>`, use `secrets_group=<uuid>`        |
|                       | `pass_through_ports`| instead of `/dcim/devices/?pass_through_ports=<bool>`, use `has_front|rear_ports`      |
| DeviceBay             | `region_id`         | instead of `/dcim/device-bays/?region_id=<uuid>`, use `region=<uuid>`                  |
|                       | `device_id`         | instead of `/dcim/device-bays/?device_id=<uuid>`, use `device=<uuid>`                  |
| DeviceType            | `manufacturer_id`   | instead of `/dcim/device-types/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`     |
| FrontPort             | `region_id`         | instead of `/dcim/front-ports/?region_id=<uuid>`, use `region=<uuid>`                  |
|                       | `device_id`         | instead of `/dcim/front-ports/?device_id=<uuid>`, use `device=<uuid>`                  |
| Interface             | `region_id`         | instead of `/dcim/interfaces/?region_id=<uuid>`, use `region=<uuid>`                   |
|                       | `device_id`         | instead of `/dcim/interfaces/?device_id=<uuid>`, use `device=<uuid>`                   |
|                       | `lag_id`            | instead of `/dcim/interfaces/?lag_id=<uuid>`, use `lag=<uuid>`                         |
| InventoryItem         | `region_id`         | instead of `/dcim/inventory-items/?region_id=<uuid>`, use `region=<uuid>`              |
|                       | `site_id`           | instead of `/dcim/inventory-items/?site_id=<uuid>`, use `site=<uuid>`                  |
|                       | `device_id`         | instead of `/dcim/inventory-items/?device_id=<uuid>`, use `device=<uuid>`              |
|                       | `parent_id`         | instead of `/dcim/inventory-items/?parent_id=<uuid>`, use `parent=<uuid>`              |
|                       | `manufacturer_id`   | instead of `/dcim/inventory-items/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`  |
| Rack                  | `region_id`         | instead of `/dcim/racks/?region_id=<uuid>`, use `region=<uuid>`                        |
|                       | `site_id`           | instead of `/dcim/racks/?site_id=<uuid>`, use `site=<uuid>`                            |
|                       | `group_id`          | instead of `/dcim/racks/?group_id=<uuid>`, use `group=<uuid>`                          |
|                       | `role_id`           | instead of `/dcim/racks/?role_id=<uuid>`, use `role=<uuid>`                            |
| RackGroup             | `region_id`         | instead of `/dcim/rack-groups/?region_id=<uuid>`, use `region=<uuid>`                  |
|                       | `site_id`           | instead of `/dcim/rack-groups/?site_id=<uuid>`, use `site=<uuid>`                      |
|                       | `parent_id`         | instead of `/dcim/rack-groups/?parent_id=<uuid>`, use `parent=<uuid>`                  |
| RackReservation       | `rack_id`           | instead of `/dcim/rack-reservations/?rack_id=<uuid>`, use `rack=<uuid>`                |
|                       | `group_id`          | instead of `/dcim/rack-reservations/?group_id=<uuid>`, use `group=<uuid>`              |
|                       | `user_id`           | instead of `/dcim/rack-reservations/?user_id=<uuid>`, use `user=<uuid>`                |
|                       | `site_id`           | instead of `/dcim/rack-reservations/?site_id=<uuid>`, use `site=<uuid>`                |
| RearPort              | `region_id`         | instead of `/dcim/rear-ports/?region_id=<uuid>`, use `region=<uuid>`                   |
|                       | `device_id`         | instead of `/dcim/rear-ports/?device_id=<uuid>`, use `device=<uuid>`                   |
| Region                | `parent_id`         | instead of `/dcim/regions/?parent_id=<uuid>`, use `parent=<uuid>`                      |
| Platform              | `manufacturer_id`   | instead of `/dcim/platforms/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`        |
| PowerOutlet           | `region_id`         | instead of `/dcim/power-outlets/?region_id=<uuid>`, use `region=<uuid>`                |
|                       | `device_id`         | instead of `/dcim/power-outlets/?device_id=<uuid>`, use `device=<uuid>`                |
| PowerFeed             | `region_id`         | instead of `/dcim/power-feeds/?region_id=<uuid>`, use `region=<uuid>`                  |
|                       | `site_id`           | instead of `/dcim/power-feeds/?site_id=<uuid>`, use `site=<uuid>`                      |
|                       | `power_panel_id`    | instead of `/dcim/power-feeds/?power_panel_id=<uuid>`, use `power_panel=<uuid>`        |
|                       | `rack_id`           | instead of `/dcim/power-feeds/?rack_id=<uuid>`, use `rack=<uuid>`                      |
| PowerPanel            | `region_id`         | instead of `/dcim/power-panels/?region_id=<uuid>`, use `region=<uuid>`                 |
|                       | `site_id`           | instead of `/dcim/power-panels/?site_id=<uuid>`, use `site=<uuid>`                     |
|                       | `rack_group_id`     | instead of `/dcim/power-panels/?rack_group_id=<uuid>`, use `rack_group=<uuid>`         |
| PowerPort             | `region_id`         | instead of `/dcim/power-ports/?region_id=<uuid>`, use `region=<uuid>`                  |
|                       | `device_id`         | instead of `/dcim/power-ports/?device_id=<uuid>`, use `device=<uuid>`                  |
| Prefix                | `region_id`         | instead of `/ipam/prefixes/?region_id=<uuid>`, use `region=<uuid>`                     |
|                       | `site_id`           | instead of `/ipam/prefixes/?site_id=<uuid>`, use `site=<uuid>`                         |
| Site                  | `region_id`         | instead of `/dcim/sites/?region_id=<uuid>`, use `region=<uuid>`                        |
| VirtualChassis        | `region_id`         | instead of `/dcim/virtual-chassis/?region_id=<uuid>`, use `region=<uuid>`              |
|                       | `site_id`           | instead of `/dcim/virtual-chassis/?site_id=<uuid>`, use `site=<uuid>`                  |
|                       | `master_id`         | instead of `/dcim/virtual-chassis/?master_id=<uuid>`, use `master=<uuid>`              |
|                       | `tenant_id`         | instead of `/dcim/virtual-chassis/?tenant_id=<uuid>`, use `tenant=<uuid>`              |
| VLANGroup             | `region_id`         | instead of `/ipam/vlan-groups/?region_id=<uuid>`, use `region=<uuid>`                  |
|                       | `site_id`           | instead of `/ipam/vlan-groups/?site_id=<uuid>`, use `site=<uuid>`                      |
| VLAN                  | `region_id`         | instead of `/ipam/vlans/?region_id=<uuid>`, use `region=<uuid>`                        |
|                       | `site_id`           | instead of `/ipam/vlans/?site_id=<uuid>`, use `site=<uuid>`                            |

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
