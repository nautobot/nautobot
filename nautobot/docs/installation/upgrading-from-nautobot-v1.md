# Upgrading from Nautobot v1.X

## Dependency Changes

- Nautobot no longer uses or supports the use of `django-mptt`.
- Nautobot no longer uses or supports the use of `django-rq`.

## Database (ORM) Changes

### Database Behavior Changes

| Model        | Field          | Changes                                           |
|--------------|----------------|---------------------------------------------------|
| JobLogEntry  | `absolute_url` | No longer accepts `null` values, use `""` instead |
|              | `log_object`   | No longer accepts `null` values, use `""` instead |
| ScheduledJob | `queue`        | No longer accepts `null` values, use `""` instead |
| Webhook      | `ca_file_path` | No longer accepts `null` values, use `""` instead |

### Renamed Database Fields

| Model               | Renamed Field                           | New Name                                       |
|---------------------|-----------------------------------------|------------------------------------------------|
| Cluster             | `group`                                 | `cluster_group`                                |
|                     | `type`                                  | `cluster_type`                                 |
| ConfigContextSchema | `device_set`                            | `dcim_device_related`                          |
|                     | `virtualmachine_set`                    | `virtualization_virtualmachine_related`        |
| Device              | `device_role`                           | `role`                                         |
|                     | `local_context_data`                    | `local_config_context_data`                    |
|                     | `local_context_data_owner_content_type` | `local_config_context_data_owner_content_type` |
|                     | `local_context_data_owner_object_id`    | `local_config_context_data_owner_object_id`    |
|                     | `local_context_schema`                  | `local_config_context_schema`                  |
| InventoryItem       | `child_items`                           | `children`                                     |
|                     | `level`                                 | `tree_depth`                                   |
| RackGroup           | `level`                                 | `tree_depth`                                   |
| Region              | `level`                                 | `tree_depth`                                   |
| TenantGroup         | `level`                                 | `tree_depth`                                   |
| VirtualMachine      | `local_context_data`                    | `local_config_context_data`                    |
|                     | `local_context_data_owner_content_type` | `local_config_context_data_owner_content_type` |
|                     | `local_context_data_owner_object_id`    | `local_config_context_data_owner_object_id`    |
|                     | `local_context_schema`                  | `local_config_context_schema`                  |

### Removed Database Fields

| Model         | Removed Field |
|---------------|---------------|
| InventoryItem | `lft`         |
|               | `rght`        |
|               | `tree_id`     |
| RackGroup     | `lft`         |
|               | `rght`        |
|               | `tree_id`     |
| Region        | `lft`         |
|               | `rght`        |
|               | `tree_id`     |
| TenantGroup   | `lft`         |
|               | `rght`        |
|               | `tree_id`     |

### Replaced Models

The `ipam.Role`, `dcim.RackRole`, and `dcim.DeviceRole` models have been removed and replaced by a single `extras.Role` model. This means that any references to the removed models in the code now use the `extras.Role` model instead.

| Removed Model     | Replaced With |
|-------------------|---------------|
| `dcim.DeviceRole` | `extras.Role` |
| `dcim.RackRole`   | `extras.Role` |
| `ipam.Role`       | `extras.Role` |

## GraphQL and REST API Changes

### API Behavior Changes

| Model       | Field          | Changes                                                                                                  |
|-------------|----------------|----------------------------------------------------------------------------------------------------------|
| IPAddress   | `role`         | `/ipam/ip-addresses/` endpoint now uses role nested serializer for the role field, rather than a string. |
| RackGroup   | `rack_count`   | Now only counts Racks directly belonging to this RackGroup, not those belonging to its descendants.      |
| Region      | `site_count`   | Now only counts Sites directly belonging to this Region, not those belonging to its descendants.         |
| TenantGroup | `tenant_count` | Now only counts Tenants directly belonging to this TenantGroup, not those belonging to its descendants.  |

### Renamed Serializer Fields

| Model                 | Renamed Field          | New Name                      |
|-----------------------|------------------------|-------------------------------|
| Cluster               | `group`                | `cluster_group`               |
|                       | `type`                 | `cluster_type`                |
| Device                | `device_role`          | `role`                        |
|                       | `local_context_data`   | `local_config_context_data`   |
|                       | `local_context_schema` | `local_config_context_schema` |
| InventoryItem         | `_depth`               | `tree_depth`                  |
| RackGroup             | `_depth`               | `tree_depth`                  |
| Region                | `_depth`               | `tree_depth`                  |
| TenantGroup           | `_depth`               | `tree_depth`                  |
| VirtualMachine        | `local_context_data`   | `local_config_context_data`   |
|                       | `local_context_schema` | `local_config_context_schema` |

### Removed Serializer Fields

| Model/Endpoint | Removed Field        | Comments                             |
|----------------|----------------------|--------------------------------------|
| `/api/status/` | `rq-workers-running` | Removed as RQ is no longer supported |

### Replaced Endpoints

These endpoints `/ipam/roles/`, `/dcim/rack-roles/` and `/dcim/device-roles/` are no longer available. Instead,  use the `/extras/roles/` endpoint to retrieve and manipulate `role` data.

| Removed Endpoints     | Replaced With    |
|-----------------------|------------------|
| `/dcim/device-roles/` | `/extras/roles/` |
| `/dcim/rack-roles/`   | `/extras/roles/` |
| `/ipam/roles/`        | `/extras/roles/` |

## UI, GraphQL, and REST API Filter Changes

### Renamed Filter Fields

| Model                 | Renamed Filter Field      | New Name                         | UI and Rest API endpoints Available in v2.X                               |
|-----------------------|---------------------------|----------------------------------|---------------------------------------------------------------------------|
| Cable                 | `tag`                     | `tags`                           | `/dcim/cables/?tags=<slug>`                                               |
| Circuit               | `tag`                     | `tags`                           | `/circuits/circuits/?tags=<slug>`                                         |
| ConsolePort           | `cabled`                  | `has_cable`                      | `/dcim/console-ports/?has_cable=True/False`                               |
| ConsoleServerPort     | `cabled`                  | `has_cable`                      | `/dcim/console-server-ports/?has_cable=True/False`                        |
| Device                | `cluster_id`              | `cluster`                        | `/dcim/devices/?cluster=<uuid/slug>`                                      |
|                       | `device_type_id`          | `device_type`                    | `/dcim/devices/?device_type=<uuid/slug>`                                  |
|                       | `local_context_data`      | `local_config_context_data`      | `/dcim/devices/?local_config_context_data=True/False`                     |
|                       | `local_context_schema_id` | `local_config_context_schema_id` | `/dcim/devices/?local_config_context_schema_id=<uuid>`                    |
|                       | `local_context_schema`    | `local_config_context_schema`    | `/dcim/devices/?local_config_context_schema=<slug>`                       |
|                       | `rack_group_id`           | `rack_group`                     | `/dcim/devices/?rack_group=<uuid/slug>`                                   |
|                       | `rack_id`                 | `rack`                           | `/dcim/devices/?rack=<uuid/slug>`                                         |
|                       | `tag`                     | `tags`                           | `/dcim/devices/?tags=<slug>`                                              |
|                       | `virtual_chassis_id`      | `virtual_chassis`                | `/dcim/devices/?virtual_chassis=<uuid/slug>`                              |
| DeviceBay             | `tag`                     | `tags`                           | `/dcim/device-bays/?tags=<slug>`                                          |
| DeviceRedundancyGroup | `tag`                     | `tags`                           | `/dcim/device-redundancy-groups/?tag=<slug>`                              |
| DeviceType            | `tag`                     | `tags`                           | `/dcim/device-types/?tags=<slug>`                                         |
| FrontPort             | `cabled`                  | `has_cable`                      | `/dcim/front-ports/?has_cable=True/False`                                 |
|                       | `tag`                     | `tags`                           | `/dcim/front-ports/?tags=<slug>`                                          |
| Interface             | `cabled`                  | `has_cable`                      | `/dcim/interfaces/?has_cable=True/False`                                  |
| InventoryItem         | `child_items`             | `children`                       | `/dcim/inventory-items/?children=<uuid/name>`                             |
|                       | `has_child_items`         | `has_children`                   | `/dcim/inventory-items/?has_children=True/False`                          |
|                       | `tag`                     | `tags`                           | `/dcim/inventory-items/?tags=<slug>`                                      |
| Location              | `tag`                     | `tags`                           | `/dcim/locations/?tags=<slug>`                                            |
| PowerFeed             | `cabled`                  | `has_cable`                      | `/dcim/power-feeds/?has_cable=True/False`                                 |
|                       | `tag`                     | `tags`                           | `/dcim/power-feeds/?tags=<slug>`                                          |
| PowerOutlet           | `cabled`                  | `has_cable`                      | `/dcim/power-outlets/?has_cable=True/False`                               |
| PowerPanel            | `tag`                     | `tags`                           | `/dcim/power-panels/?tags=<slug>`                                         |
| PowerPort             | `cabled`                  | `has_cable`                      | `/dcim/power-ports/?has_cable=True/False`                                 |
| Provider              | `tag`                     | `tags`                           | `/circuits/provider/?tags=<slug>`                                         |
| ProviderNetwork       | `tag`                     | `tags`                           | `/circuits/provider-networks/?tags=<slug>`                                |
| Rack                  | `tag`                     | `tags`                           | `/dcim/racks/?tags=<slug>`                                                |
| RackReservation       | `tag`                     | `tags`                           | `/dcim/rack-reservations/?tags=<slug>`                                    |
| RearPort              | `cabled`                  | `has_cable`                      | `/dcim/rear-ports/?has_cable=True/False`                                  |
|                       | `tag`                     | `tags`                           | `/dcim/rear-ports/?tags=<slug>`                                           |
| Site                  | `tag`                     | `tags`                           | `/dcim/sites/?tags=<slug>`                                                |
| Tenant                | `tag`                     | `tags`                           | `/tenancy/tenants/?tags=<slug>`                                           |
| VirtualMachine        | `local_context_data`      | `local_config_context_data`      | `/virtualization/virtual-machines/?local_config_context_data=True/False`  |
|                       | `local_context_schema_id` | `local_config_context_schema_id` | `/virtualization/virtual-machines/?local_config_context_schema_id=<uuid>` |
|                       | `local_context_schema`    | `local_config_context_schema`    | `/virtualization/virtual-machines/?local_config_context_schema=<slug>`    |

### Enhanced Filter Fields

Below is a table documenting [enhanced filter field changes](../release-notes/version-2.0.md#enhanced-filter-fields-2804) in v2.x.

| Model                 | Enhanced Filter Field | Changes                                                    | UI and Rest API endpoints Available in v2.X|
|-----------------------|-----------------------|------------------------------------------------------------|----------------------------------------------|
| Circuit               | `provider`            | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/circuits/?provider=<uuid/slug>`|
|                       | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/circuits/?site=<uuid/slug>`|
|                       | `type`                | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/circuits/?type=<uuid/slug>`|
| ConsolePort           | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-ports/?device=<uuid/name>`|
| ConsoleServerPort     | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-server-ports/?device=<uuid/name>`|
| Device                | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?manufacturer=<uuid/slug>`|
|                       | `device_type_id`      | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?device_type=<uuid/slug>`|
|                       | `role`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?role=<uuid/slug>`|
|                       | `platform`            | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?platform=<uuid/slug>`|
|                       | `rack_group_id`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack_group=<uuid/slug>`|
|                       | `rack_id`             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack=<uuid/slug>`|
|                       | `cluster_id`          | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?cluster=<uuid/slug>`|
|                       | `model`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?model=<uuid/slug>`|
|                       | `serial`              | Enhanced to permit filtering on multiple values            | `/dcim/devices/?serial=<value>&serial=<value>...`|
|                       | `secrets_group`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?secrets_group=<uuid/slug>`|
|                       | `virtual_chassis_id`  | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?virtual_chassis=<uuid/slug>`|
|                       | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?site=<uuid/slug>`|
| DeviceBay             | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/device-bays/?device=<uuid/name>`|
|                       | `cable`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid/slug>`|
| DeviceType            | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/device-types/?manufacturer=<uuid/slug>`|
| FrontPort             | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/front-ports/?device=<uuid/name>`
| Interface             | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/interfaces/?device=<uuid/name>`|
| InventoryItem         | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?site=<uuid/slug>`|
|                       | `device`              | Enhanced to support primary key UUIDs in addition to name  | `/dcim/inventory-items/?device=<uuid/name>`|
|                       | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?manufacturer=<uuid/slug>`|
|                       | `serial`              | Enhanced to permit filtering on multiple values            | `/dcim/inventory-items/?serial=<value>&serial=<value>...`|
| Platform              | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/platforms/?manufacturer=<uuid/slug>`|
| PowerFeed             | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/power-feeds/?site=<uuid/slug>`|
| PowerOutlet           | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-outlets/?device=<uuid/name>`|
| PowerPort             | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-ports/?device=<uuid/name>`|
| Provider              | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/providers/?site=<uuid/slug>`|
| ProviderNetwork       | `provider`            | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/provider-networks/?provider=<uuid/slug>`|
| Rack                  | `role`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/racks/?role=<uuid/slug>`|
|                       | `serial`              | Enhanced to permit filtering on multiple values            | `/dcim/racks/?serial=<value>&serial=<value>...`|
| RackGroup             | `parent`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-groups/?parent=<uuid/slug>`|
| RackReservation       | `user`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-reservations/?user=<uuid/slug>`|
| RearPort              | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/rear-ports/?device=<uuid/name>`|
| Region                | `parent`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid/slug>`|
| VirtualChassis        | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?site=<uuid/slug>`|
|                       | `master`              | Enhanced to support primary key UUIDs in addition to name  | `/dcim/virtual-chassis/?master=<uuid/name>`|
|                       | `tenant`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?tenant=<uuid/slug>`|

### Corrected Filter Fields

Below is a table documenting [corrected filter field changes](../release-notes/version-2.0.md#corrected-filter-fields-2804) in v2.x.

| Model  | Changed Filter Field   | Before                                     | After                                                                                   |
|--------|------------------------|--------------------------------------------|-----------------------------------------------------------------------------------------|
| Device | `console_ports`        | `/dcim/devices/?console_ports=True`        | `/dcim/devices/?console_ports=<uuid>` or `?has_console_ports=<True/False>`              |
|        | `console_server_ports` | `/dcim/devices/?console_server_ports=True` | `/dcim/devices/?console_server_ports=<uuid>` or `?has_console_server_ports=<True/False>`|
|        | `device_bays`          | `/dcim/devices/?device_bays=True`          | `/dcim/devices/?device_bays=<uuid>` or `?has_device_bays=<True/False>`                  |
|        | `front_ports`          | `/dcim/devices/?front_ports=True`          | `/dcim/devices/?front_ports=<uuid>` or `?has_front_ports=<True/False>`                  |
|        | `interfaces`           | `/dcim/devices/?interfaces=True`           | `/dcim/devices/?interfaces=<uuid>` or `?has_interfaces=<True/False>`                    |
|        | `rear_ports`           | `/dcim/devices/?rear_ports=True`           | `/dcim/devices/?rear_ports=<uuid>` or `?has_rear_ports=<True/False>`                    |
|        | `power_ports`          | `/dcim/devices/?power_ports=True`          | `/dcim/devices/?power_ports=<uuid>` or `?has_power_ports=<True/False>`                  |
|        | `power_outlets`        | `/dcim/devices/?power_outlets=True`        | `/dcim/devices/?power_outlets=<uuid>` or `?has_power_outlets=<True/False>`              |

### Removed Redundant Filter Fields

Below is a table documenting [removed redundant filter field changes](../release-notes/version-2.0.md#removed-redundant-filter-fields-2804) in v2.x.

| Model              | Removed Filter Field  | UI and API endpoints that are no longer supported in v2.X                                              |
|--------------------|-----------------------|--------------------------------------------------------------------------------------------------------|
| Circuit            | `provider_id`         | instead of `/circuits/circuits/?provider_id=<uuid>`, use `provider=<uuid>`                             |
|                    | `provider_network_id` | instead of `/circuits/circuits/?provider_network_id=<uuid>`, use `provider_network=<uuid>`             |
|                    | `region_id`           | instead of `/circuits/circuits/?region_id=<uuid>`, use `region=<uuid>`                                 |
|                    | `site_id`             | instead of `/circuits/circuits/?site_id=<uuid>`, use `site=<uuid>`                                     |
|                    | `type_id`             | instead of `/circuits/circuits/?type_id=<uuid>`, use `type=<uuid>`                                     |
| CircuitTermination | `circuit_id`          | instead of `/circuits/circuit-terminations/?circuit_id=<uuid>`, use `circuit=<uuid>`                   |
|                    | `provider_network_id` | instead of `/circuits/circuit-terminations/?provider_network_id=<uuid>`, use `provider_network=<uuid>` |
|                    | `region_id`           | instead of `/circuits/circuit-terminations/?region_id=<uuid>`, use `region=<uuid>`                     |
|                    | `site_id`             | instead of `/circuits/circuit-terminations/?site_id=<uuid>`, use `site=<uuid>`                         |
| Cluster            | `region_id`           | instead of `/virtualization/clusters/?region_id=<uuid>`, use `region=<uuid>`                           |
|                    | `site_id`             | instead of `/virtualization/clusters/?site_id=<uuid>` , use `site=<uuid>`                              |
| ConfigContext      | `role_id`             | instead of `/extras/config-contexts/?role_id=<uuid>`, use `role=<uuid>`                                |
| ConsolePort        | `region_id`           | instead of `/dcim/console-ports/?region_id=<uuid>`, use `region=<uuid>`                                |
|                    | `device_id`           | instead of `/dcim/console-ports/?device_id=<uuid>`, use `device=<uuid>`                                |
| ConsoleServerPort  | `region_id`           | instead of `/dcim/console-server-ports/?region_id=<uuid>`, use `region=<uuid>`                         |
|                    | `device_id`           | instead of `/dcim/console-server-ports/?device_id=<uuid>`, use `device=<uuid>`                         |
| Device             | `region_id`           | instead of `/dcim/devices/?region_id=<uuid>`, use `region=<uuid>`                                      |
|                    | `site_id`             | instead of `/dcim/devices/?site_id=<uuid>`, use `site=<uuid>`                                          |
|                    | `manufacturer_id`     | instead of `/dcim/devices/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`                          |
|                    | `model`               | instead of `/dcim/devices/?model=<uuid>`, use `device_type=<uuid>`                                     |
|                    | `role_id`             | instead of `/dcim/devices/?role_id=<uuid>`, use `role=<uuid>`                                          |
|                    | `platform_id`         | instead of `/dcim/devices/?platform_id=<uuid>`, use `platform=<uuid>`                                  |
|                    | `secrets_group_id`    | instead of `/dcim/devices/?secrets_group_id=<uuid>`, use `secrets_group=<uuid>`                        |
|                    | `pass_through_ports`  | instead of `/dcim/devices/?pass_through_ports=<bool>`, use `has_front/rear_ports`                      |
| DeviceBay          | `region_id`           | instead of `/dcim/device-bays/?region_id=<uuid>`, use `region=<uuid>`                                  |
|                    | `device_id`           | instead of `/dcim/device-bays/?device_id=<uuid>`, use `device=<uuid>`                                  |
| DeviceType         | `manufacturer_id`     | instead of `/dcim/device-types/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`                     |
| FrontPort          | `region_id`           | instead of `/dcim/front-ports/?region_id=<uuid>`, use `region=<uuid>`                                  |
|                    | `device_id`           | instead of `/dcim/front-ports/?device_id=<uuid>`, use `device=<uuid>`                                  |
| Interface          | `bridge_id`           | instead of `/dcim/interfaces/?bridge_id=<uuid>`, use `bridge=<uuid>`                                   |
|                    | `device_id`           | instead of `/dcim/interfaces/?device_id=<uuid>`, use `device=<uuid>`                                   |
|                    | `parent_interface_id` | instead of `/dcim/interfaces/?parent_interface_id=<uuid>`, use `parent_interface=<uuid>`               |
|                    | `region_id`           | instead of `/dcim/interfaces/?region_id=<uuid>`, use `region=<uuid>`                                   |
|                    | `lag_id`              | instead of `/dcim/interfaces/?lag_id=<uuid>`, use `lag=<uuid>`                                         |
| InventoryItem      | `region_id`           | instead of `/dcim/inventory-items/?region_id=<uuid>`, use `region=<uuid>`                              |
|                    | `site_id`             | instead of `/dcim/inventory-items/?site_id=<uuid>`, use `site=<uuid>`                                  |
|                    | `device_id`           | instead of `/dcim/inventory-items/?device_id=<uuid>`, use `device=<uuid>`                              |
|                    | `parent_id`           | instead of `/dcim/inventory-items/?parent_id=<uuid>`, use `parent=<uuid>`                              |
|                    | `manufacturer_id`     | instead of `/dcim/inventory-items/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`                  |
| Provider           | `region_id`           | instead of `/circuits/providers/?region_id=<uuid>`, use `region=<uuid>`                                |
|                    | `site_id`             | instead of `/circuits/providers/?site_id=<uuid>`, use `site=<uuid>`                                    |
| ProviderNetwork    | `provider_id`         | instead of `/circuits/provider-networks/?provider_id=<uuid>`, use `provider=<uuid>`                    |
| Rack               | `region_id`           | instead of `/dcim/racks/?region_id=<uuid>`, use `region=<uuid>`                                        |
|                    | `site_id`             | instead of `/dcim/racks/?site_id=<uuid>`, use `site=<uuid>`                                            |
|                    | `group_id`            | instead of `/dcim/racks/?group_id=<uuid>`, use `group=<uuid>`                                          |
|                    | `role_id`             | instead of `/dcim/racks/?role_id=<uuid>`, use `role=<uuid>`                                            |
| RackGroup          | `region_id`           | instead of `/dcim/rack-groups/?region_id=<uuid>`, use `region=<uuid>`                                  |
|                    | `site_id`             | instead of `/dcim/rack-groups/?site_id=<uuid>`, use `site=<uuid>`                                      |
|                    | `parent_id`           | instead of `/dcim/rack-groups/?parent_id=<uuid>`, use `parent=<uuid>`                                  |
| RackReservation    | `rack_id`             | instead of `/dcim/rack-reservations/?rack_id=<uuid>`, use `rack=<uuid>`                                |
|                    | `group_id`            | instead of `/dcim/rack-reservations/?group_id=<uuid>`, use `group=<uuid>`                              |
|                    | `user_id`             | instead of `/dcim/rack-reservations/?user_id=<uuid>`, use `user=<uuid>`                                |
|                    | `site_id`             | instead of `/dcim/rack-reservations/?site_id=<uuid>`, use `site=<uuid>`                                |
| RearPort           | `region_id`           | instead of `/dcim/rear-ports/?region_id=<uuid>`, use `region=<uuid>`                                   |
|                    | `device_id`           | instead of `/dcim/rear-ports/?device_id=<uuid>`, use `device=<uuid>`                                   |
| Region             | `parent_id`           | instead of `/dcim/regions/?parent_id=<uuid>`, use `parent=<uuid>`                                      |
| Platform           | `manufacturer_id`     | instead of `/dcim/platforms/?manufacturer_id=<uuid>`, use `manufacturer=<uuid>`                        |
| PowerOutlet        | `region_id`           | instead of `/dcim/power-outlets/?region_id=<uuid>`, use `region=<uuid>`                                |
|                    | `device_id`           | instead of `/dcim/power-outlets/?device_id=<uuid>`, use `device=<uuid>`                                |
| PowerFeed          | `region_id`           | instead of `/dcim/power-feeds/?region_id=<uuid>`, use `region=<uuid>`                                  |
|                    | `site_id`             | instead of `/dcim/power-feeds/?site_id=<uuid>`, use `site=<uuid>`                                      |
|                    | `power_panel_id`      | instead of `/dcim/power-feeds/?power_panel_id=<uuid>`, use `power_panel=<uuid>`                        |
|                    | `rack_id`             | instead of `/dcim/power-feeds/?rack_id=<uuid>`, use `rack=<uuid>`                                      |
| PowerPanel         | `region_id`           | instead of `/dcim/power-panels/?region_id=<uuid>`, use `region=<uuid>`                                 |
|                    | `site_id`             | instead of `/dcim/power-panels/?site_id=<uuid>`, use `site=<uuid>`                                     |
|                    | `rack_group_id`       | instead of `/dcim/power-panels/?rack_group_id=<uuid>`, use `rack_group=<uuid>`                         |
| PowerPort          | `region_id`           | instead of `/dcim/power-ports/?region_id=<uuid>`, use `region=<uuid>`                                  |
|                    | `device_id`           | instead of `/dcim/power-ports/?device_id=<uuid>`, use `device=<uuid>`                                  |
| Prefix             | `region_id`           | instead of `/ipam/prefixes/?region_id=<uuid>`, use `region=<uuid>`                                     |
|                    | `site_id`             | instead of `/ipam/prefixes/?site_id=<uuid>`, use `site=<uuid>`                                         |
| Site               | `region_id`           | instead of `/dcim/sites/?region_id=<uuid>`, use `region=<uuid>`                                        |
| Tenant             | `group_id`            | instead of `/tenancy/tenants/?group_id=<uuid>` use `group=<uuid>`                                      |
| TenantGroup        | `parent_id`           | instead of `/tenancy/tenant-groups/?parent_id=<uuid>`, use `parent=<uuid>`                             |
| VirtualChassis     | `region_id`           | instead of `/dcim/virtual-chassis/?region_id=<uuid>`, use `region=<uuid>`                              |
|                    | `site_id`             | instead of `/dcim/virtual-chassis/?site_id=<uuid>`, use `site=<uuid>`                                  |
|                    | `master_id`           | instead of `/dcim/virtual-chassis/?master_id=<uuid>`, use `master=<uuid>`                              |
|                    | `tenant_id`           | instead of `/dcim/virtual-chassis/?tenant_id=<uuid>`, use `tenant=<uuid>`                              |
| VLANGroup          | `region_id`           | instead of `/ipam/vlan-groups/?region_id=<uuid>`, use `region=<uuid>`                                  |
|                    | `site_id`             | instead of `/ipam/vlan-groups/?site_id=<uuid>`, use `site=<uuid>`                                      |
| VLAN               | `region_id`           | instead of `/ipam/vlans/?region_id=<uuid>`, use `region=<uuid>`                                        |
|                    | `site_id`             | instead of `/ipam/vlans/?site_id=<uuid>`, use `site=<uuid>`                                            |
| VMInterface        | `bridge_id`           | instead of `/virtualization/interfaces/?bridge_id=<uuid>`, use `bridge=<uuid>`                         |
|                    | `parent_interface_id` | instead of `/virtualization/interfaces/?parent_interface_id=<uuid>`, use `parent_interface=<uuid>`     |
