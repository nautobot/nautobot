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
| Prefix       | `is_pool`      | Replaced by new field `type`, valid choices are "Container", "Network" and "Pool" |
|              | `status`       | Container status has been replaced by new field `type` |
| ScheduledJob | `queue`        | No longer accepts `null` values, use `""` instead |
| Webhook      | `ca_file_path` | No longer accepts `null` values, use `""` instead |

### Renamed Database Fields

| Model                   | Renamed Field                           | New Name                                       |
|-------------------------|-----------------------------------------|------------------------------------------------|
| CablePath               | `circuittermination`                    | `circuits_circuittermination_related`          |
|                         | `consoleport`                           | `dcim_consoleport_related`                     |
|                         | `consoleserverport`                     | `dcim_consoleserverport_related`               |
|                         | `interface`                             | `dcim_interface_related`                       |
|                         | `powerfeed`                             | `dcim_powerfeed_related`                       |
|                         | `poweroutlet`                           | `dcim_poweroutlet_related`                     |
|                         | `powerport`                             | `dcim_powerport_related`                       |
| Circuit                 | `termination_a`                         | `circuit_termination_a`                        |
|                         | `termination_z`                         | `circuit_termination_z`                        |
|                         | `terminations`                          | `circuit_terminations`                         |
|                         | `type`                                  | `circuit_type`                                 |
| Cluster                 | `group`                                 | `cluster_group`                                |
|                         | `type`                                  | `cluster_type`                                 |
| ConfigContextSchema     | `schema`                                | `config_context_schema`                        |
|                         | `device_set`                            | `dcim_device_related`                          |
|                         | `virtualmachine_set`                    | `virtualization_virtualmachine_related`        |
| ContentType             | `computedfield`                         | `computed_fields`                              |
|                         | `configcontext`                         | `config_contexts`                              |
|                         | `configcontextschema`                   | `config_context_schemas`                       |
|                         | `customlink`                            | `custom_links`                                 |
|                         | `dynamicgroup`                          | `dynamic_groups`                               |
|                         | `exporttemplate`                        | `export_templates`                             |
|                         | `imageattachment`                       | `image_attachments`                            |
|                         | `note`                                  | `notes`                                        |
| CustomFieldChoice       | `field`                                 | `custom_field`                                 |
| CustomField             | `choices`                               | `custom_field_choices`                         |
| Device                  | `device_role`                           | `role`                                         |
|                         | `local_context_data`                    | `local_config_context_data`                    |
|                         | `local_context_data_owner_content_type` | `local_config_context_data_owner_content_type` |
|                         | `local_context_data_owner_object_id`    | `local_config_context_data_owner_object_id`    |
|                         | `local_context_schema`                  | `local_config_context_schema`                  |
| InventoryItem           | `child_items`                           | `children`                                     |
|                         | `level`                                 | `tree_depth`                                   |
| Job                     | `job_hook`                              | `job_hooks`                                    |
|                         | `results`                               | `job_results`                                  |
| JobResult               | `logs`                                  | `job_log_entries`                              |
|                         | `schedule`                              | `scheduled_job`                                |
| RackGroup               | `level`                                 | `tree_depth`                                   |
| Region                  | `level`                                 | `tree_depth`                                   |
| Relationship            | `associations`                          | `relationship_associations`                    |
| ScheduledJob            | `job_model`                             | `job`                                          |
|                         | `jobresult`                             | `job_results`                                  |
| Secrets                 | `groups`                                | `secrets_groups`                               |
|                         | `secretsgroupassociation`               | `secrets_group_associations`                   |
| SecretsGroup            | `gitrepository`                         | `git_repositories`                             |
|                         | `secretsgroupassociation`               | `secrets_group_associations`                   |
| SecretsGroupAssociation | `group`                                 | `secrets_group`                                |
| Service                 | `ipaddresses`                           | `ip_addresses`                                 |
| Tenant                  | `group`                                 | `tenant_group`                                 |
| TenantGroup             | `level`                                 | `tree_depth`                                   |
| VirtualMachine          | `local_context_data`                    | `local_config_context_data`                    |
|                         | `local_context_data_owner_content_type` | `local_config_context_data_owner_content_type` |
|                         | `local_context_data_owner_object_id`    | `local_config_context_data_owner_object_id`    |
|                         | `local_context_schema`                  | `local_config_context_schema`                  |
| User                    | `changes`                               | `object_changes`                               |
|                         | `note`                                  | `notes`                                        |
| VLAN                    | `group`                                 | `vlan_group`                                   |

### Removed Database Fields

| Model         | Removed Field |
|---------------|---------------|
| InventoryItem | `lft`         |
|               | `rght`        |
|               | `tree_id`     |
| RackGroup     | `lft`         |
|               | `rght`        |
|               | `tree_id`     |
| Prefix        | `is_pool`     |
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

| Model                 | Field          | Changes                                                                                                  |
|-----------------------|----------------|----------------------------------------------------------------------------------------------------------|
| Cable                 | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Circuit               | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Device                | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| DeviceRedundancyGroup | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Interface             | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| IPAddress             | `role`         | `/ipam/ip-addresses/` endpoint now uses role nested serializer for the role field, rather than a string. |
|                       | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Location              | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| PowerFeed             | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Prefix                | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Rack                  | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| RackGroup             | `rack_count`   | Now only counts Racks directly belonging to this RackGroup, not those belonging to its descendants.      |
| Region                | `site_count`   | Now only counts Sites directly belonging to this Region, not those belonging to its descendants.         |
| Site                  | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| TenantGroup           | `tenant_count` | Now only counts Tenants directly belonging to this TenantGroup, not those belonging to its descendants.  |
| VirtualMachine        | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| VLAN                  | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| VMInterface           | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |

### Renamed Serializer Fields

| Model                   | Renamed Field          | New Name                      |
|-------------------------|------------------------|-------------------------------|
| Circuit                 | `termination_a`        | `circuit_termination_a`       |
|                         | `termination_z`        | `circuit_termination_z`       |
|                         | `type`                 | `circuit_type`                |
| ConfigContext           | `schema`               | `config_context_schema`       |
| Cluster                 | `group`                | `cluster_group`               |
|                         | `type`                 | `cluster_type`                |
| CustomFieldChoice       | `field`                | `custom_field`                |
| Device                  | `device_role`          | `role`                        |
|                         | `local_context_data`   | `local_config_context_data`   |
|                         | `local_context_schema` | `local_config_context_schema` |
| InventoryItem           | `_depth`               | `tree_depth`                  |
| JobResult               | `schedule`             | `scheduled_job`               |
| RackGroup               | `_depth`               | `tree_depth`                  |
| Region                  | `_depth`               | `tree_depth`                  |
| ScheduledJob            | `job_model`            | `job`                         |
| SecretsGroupAssociation | `group`                | `secrets_group`               |
| Service                 | `ipaddresses`          | `ip_addresses`                |
| Tenant                  | `group`                | `tenant_group`                |
| TenantGroup             | `_depth`               | `tree_depth`                  |
| VirtualMachine          | `local_context_data`   | `local_config_context_data`   |
|                         | `local_context_schema` | `local_config_context_schema` |
| VLAN                    | `group`                | `vlan_group`                  |

### Removed Serializer Fields

| Model/Endpoint    | Removed Field        | Comments                               |
|-------------------|----------------------|----------------------------------------|
| `/api/status/`    | `rq-workers-running` | Removed as RQ is no longer supported   |
| `/ipam/prefixes/` | `is_pool`            | Functionality replaced by `type` field |

### Removed 1.X Version Endpoints and Serializer Representations

Nautobot 2.0 removes support for 1.X versioned REST APIs and their Serializers. Requesting [older API versions](../rest-api/overview.md#versioning) will result in a `400 Bad Request` error.

Please ensure you are using the latest representations of request/response representations as seen in the API docs or Swagger.

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
|                       | `type`                    | `circuit_type`                   | `/circuits/circuits/?circuit_type=<uuid/slug>`                            |
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
| Prefix                | `is_pool`                 | `type`                           | `/ipam/prefixes/?type=<container                                          |network|pool>`                           |
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

| Model                 | Enhanced Filter Field | Changes                                                    | UI and Rest API endpoints Available in v2.X               |
|-----------------------|-----------------------|------------------------------------------------------------|-----------------------------------------------------------|
| Circuit               | `circuit_type`        | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/circuits/?circuit_type=<uuid/slug>`            |
|                       | `provider`            | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/circuits/?provider=<uuid/slug>`                |
|                       | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/circuits/?site=<uuid/slug>`                    |
| ConsolePort           | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-ports/?device=<uuid/name>`                 |
| ConsoleServerPort     | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-server-ports/?device=<uuid/name>`          |
| Device                | `cluster_id`          | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?cluster=<uuid/slug>`                      |
|                       | `device_type_id`      | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?device_type=<uuid/slug>`                  |
|                       | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?manufacturer=<uuid/slug>`                 |
|                       | `model`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?model=<uuid/slug>`                        |
|                       | `platform`            | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?platform=<uuid/slug>`                     |
|                       | `role`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?role=<uuid/slug>`                         |
|                       | `rack_id`             | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack=<uuid/slug>`                         |
|                       | `rack_group_id`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack_group=<uuid/slug>`                   |
|                       | `serial`              | Enhanced to permit filtering on multiple values            | `/dcim/devices/?serial=<value>&serial=<value>...`         |
|                       | `secrets_group`       | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?secrets_group=<uuid/slug>`                |
|                       | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?site=<uuid/slug>`                         |
|                       | `virtual_chassis_id`  | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?virtual_chassis=<uuid/slug>`              |
| DeviceBay             | `cable`               | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid/slug>`                       |
|                       | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/device-bays/?device=<uuid/name>`                   |
| DeviceType            | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/device-types/?manufacturer=<uuid/slug>`            |
| FrontPort             | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/front-ports/?device=<uuid/name>`                   |
| Interface             | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/interfaces/?device=<uuid/name>`                    |
| InventoryItem         | `device`              | Enhanced to support primary key UUIDs in addition to name  | `/dcim/inventory-items/?device=<uuid/name>`               |
|                       | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?manufacturer=<uuid/slug>`         |
|                       | `serial`              | Enhanced to permit filtering on multiple values            | `/dcim/inventory-items/?serial=<value>&serial=<value>...` |
|                       | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?site=<uuid/slug>`                 |
| Platform              | `manufacturer`        | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/platforms/?manufacturer=<uuid/slug>`               |
| PowerFeed             | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/power-feeds/?site=<uuid/slug>`                     |
| PowerOutlet           | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-outlets/?device=<uuid/name>`                 |
| PowerPort             | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-ports/?device=<uuid/name>`                   |
| Provider              | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/providers/?site=<uuid/slug>`                   |
| ProviderNetwork       | `provider`            | Enhanced to support primary key UUIDs in addition to slugs | `/circuits/provider-networks/?provider=<uuid/slug>`       |
| Rack                  | `role`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/racks/?role=<uuid/slug>`                           |
|                       | `serial`              | Enhanced to permit filtering on multiple values            | `/dcim/racks/?serial=<value>&serial=<value>...`           |
| RackGroup             | `parent`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-groups/?parent=<uuid/slug>`                   |
| RackReservation       | `user`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-reservations/?user=<uuid/slug>`               |
| RearPort              | `device`              | Enhanced to support primary key UUIDs in addition to names | `/dcim/rear-ports/?device=<uuid/name>`                    |
| Region                | `parent`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid/slug>`                       |
| Tenant                | `tenant_group`        | Enhanced to support primary key UUIDs in addition to slugs | `/tenancy/tenants/?tenant_group=<uuid/slug>`              |
| VirtualChassis        | `master`              | Enhanced to support primary key UUIDs in addition to name  | `/dcim/virtual-chassis/?master=<uuid/name>`               |
|                       | `site`                | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?site=<uuid/slug>`                 |
|                       | `tenant`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/virtual-chassis/?tenant=<uuid/slug>`               |
| VLAN                  | `vlan_group`          | Enhanced to support primary key UUIDs in addition to slugs | `/ipam/vlans/?vlan_group=<uuid/slug>`                     |

### Corrected Filter Fields

Below is a table documenting [corrected filter field changes](../release-notes/version-2.0.md#corrected-filter-fields-2804) in v2.x.

| Model  | Changed Filter Field   | Before                                     | After                                                                                    |
|--------|------------------------|--------------------------------------------|------------------------------------------------------------------------------------------|
| Device | `console_ports`        | `/dcim/devices/?console_ports=True`        | `/dcim/devices/?console_ports=<uuid>` or `?has_console_ports=<True/False>`               |
|        | `console_server_ports` | `/dcim/devices/?console_server_ports=True` | `/dcim/devices/?console_server_ports=<uuid>` or `?has_console_server_ports=<True/False>` |
|        | `device_bays`          | `/dcim/devices/?device_bays=True`          | `/dcim/devices/?device_bays=<uuid>` or `?has_device_bays=<True/False>`                   |
|        | `front_ports`          | `/dcim/devices/?front_ports=True`          | `/dcim/devices/?front_ports=<uuid>` or `?has_front_ports=<True/False>`                   |
|        | `interfaces`           | `/dcim/devices/?interfaces=True`           | `/dcim/devices/?interfaces=<uuid>` or `?has_interfaces=<True/False>`                     |
|        | `power_ports`          | `/dcim/devices/?power_ports=True`          | `/dcim/devices/?power_ports=<uuid>` or `?has_power_ports=<True/False>`                   |
|        | `power_outlets`        | `/dcim/devices/?power_outlets=True`        | `/dcim/devices/?power_outlets=<uuid>` or `?has_power_outlets=<True/False>`               |
|        | `rear_ports`           | `/dcim/devices/?rear_ports=True`           | `/dcim/devices/?rear_ports=<uuid>` or `?has_rear_ports=<True/False>`                     |

### Removed Redundant Filter Fields

Below is a table documenting [removed redundant filter field changes](../release-notes/version-2.0.md#removed-redundant-filter-fields-2804) in v2.x.
Unless stated otherwise, all of the `*_id=<uuid>` filters have been replaced by generic filters that support both uuid and slug.
For example `/circuits/circuits/?provider_id=<uuid>` has been replaced by `/circuits/circuits/?provider=<uuid>`.

| Model              | Removed Filter Field  | UI and API endpoints that are no longer supported in v2.X                                     |
|--------------------|-----------------------|-----------------------------------------------------------------------------------------------|
| Aggregate          | `tenant_group_id`     |                                                                                               |
| Circuit            | `provider_id`         |                                                                                               |
|                    | `provider_network_id` |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
|                    | `type_id`             | instead of `/circuits/circuits/?type_id=<uuid>`, use `circuit_type=<uuid>`                    |
| CircuitTermination | `circuit_id`          |                                                                                               |
|                    | `provider_network_id` |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
| Cluster            | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
| ConfigContext      | `role_id`             |                                                                                               |
| ConsolePort        | `device_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
| ConsoleServerPort  | `device_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
| Device             | `manufacturer_id`     |                                                                                               |
|                    | `model`               | instead of `/dcim/devices/?model=<uuid>`, use `device_type=<uuid>`                            |
|                    | `pass_through_ports`  | instead of `/dcim/devices/?pass_through_ports=<bool>`, use `has_front_ports`/`has_rear_ports` |
|                    | `platform_id`         |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `role_id`             |                                                                                               |
|                    | `secrets_group_id`    |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
| DeviceBay          | `device_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
| DeviceType         | `manufacturer_id`     |                                                                                               |
| FrontPort          | `device_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
| Interface          | `bridge_id`           |                                                                                               |
|                    | `device_id`           |                                                                                               |
|                    | `lag_id`              |                                                                                               |
|                    | `parent_interface_id` |                                                                                               |
|                    | `region_id`           |                                                                                               |
| InventoryItem      | `device_id`           |                                                                                               |
|                    | `manufacturer_id`     |                                                                                               |
|                    | `parent_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
| IPAddress          | `tenant_group_id`     |                                                                                               |
| Location           | `tenant_group_id`     |                                                                                               |
| Provider           | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
| ProviderNetwork    | `provider_id`         |                                                                                               |
| Rack               | `group_id`            |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `role_id`             |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
| RackGroup          | `parent_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
| RackReservation    | `group_id`            |                                                                                               |
|                    | `rack_id`             |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
|                    | `user_id`             |                                                                                               |
| RearPort           | `device_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
| Region             | `parent_id`           |                                                                                               |
| RouteTarget        | `tenant_group_id`     |                                                                                               |
| Platform           | `manufacturer_id`     |                                                                                               |
| PowerOutlet        | `device_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
| PowerFeed          | `power_panel_id`      |                                                                                               |
|                    | `rack_id`             |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
| PowerPanel         | `rack_group_id`       |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
| PowerPort          | `region_id`           |                                                                                               |
|                    | `device_id`           |                                                                                               |
| Prefix             | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
| Site               | `region_id`           |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
| Tenant             | `group_id`            |                                                                                               |
| TenantGroup        | `parent_id`           |                                                                                               |
| VirtualChassis     | `master_id`           |                                                                                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_id`           |                                                                                               |
| VirtualMachine     | `tenant_group_id`     |                                                                                               |
| VLANGroup          | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
| VLAN               | `group_id`            |                                                                                               |
|                    | `group`               | instead of `/ipam/vlans/?group=<slug>`, use `vlan_group=<slug>`                               |
|                    | `region_id`           |                                                                                               |
|                    | `site_id`             |                                                                                               |
|                    | `tenant_group_id`     |                                                                                               |
| VMInterface        | `bridge_id`           |                                                                                               |
|                    | `parent_interface_id` |                                                                                               |
| VRF                | `tenant_group_id`     |                                                                                               |

## Python Code Location Changes

The below is mostly relevant only to authors of Jobs and Nautobot Apps. End users should not be impacted by the changes in this section.

| Old Module                           | Class/Function(s)                                           | New Module                             |
|--------------------------------------|-------------------------------------------------------------|----------------------------------------|
| `nautobot.core.api.utils`            | `TreeModelSerializerMixin`                                  | `nautobot.core.api.serializers`        |
| `nautobot.core.fields`               | `*`                                                         | `nautobot.core.models.fields`          |
| `nautobot.core.forms`                | `SearchForm`                                                | `nautobot.core.forms.search`           |
| `nautobot.core.utilities`            | `*`                                                         | `nautobot.core.views.utils`            |
| `nautobot.dcim.fields`               | `MACAddressCharField`                                       | `nautobot.core.models.fields`          |
| `nautobot.dcim.forms`                | `MACAddressField`                                           | `nautobot.core.forms`                  |
| `nautobot.utilities.api`             | `*`                                                         | `nautobot.core.api.utils`              |
| `nautobot.utilities.apps`            | `*`                                                         | `nautobot.core.apps`                   |
| `nautobot.utilities.checks`          | `*`                                                         | `nautobot.core.checks`                 |
| `nautobot.utilities.choices`         | `*`                                                         | `nautobot.core.choices`                |
| `nautobot.utilities.config`          | `*`                                                         | `nautobot.core.utils.config`           |
| `nautobot.utilities.constants`       | `*`                                                         | `nautobot.core.constants`              |
| `nautobot.utilities.deprecation`     | `*`                                                         | `nautobot.core.utils.deprecation`      |
| `nautobot.utilities.error_handlers`  | `*`                                                         | `nautobot.core.views.utils`            |
| `nautobot.utilities.exceptions`      | `*`                                                         | `nautobot.core.exceptions`             |
| `nautobot.utilities.factory`         | `*`                                                         | `nautobot.core.factory`                |
| `nautobot.utilities.fields`          | `*`                                                         | `nautobot.core.models.fields`          |
| `nautobot.utilities.filters`         | `*`                                                         | `nautobot.core.filters`                |
| `nautobot.utilities.forms`           | `*`                                                         | `nautobot.core.forms`                  |
| `nautobot.utilities.git`             | `*`                                                         | `nautobot.core.utils.git`              |
| `nautobot.utilities.logging`         | `*`                                                         | `nautobot.core.utils.logging`          |
| `nautobot.utilities.management`      | `*`                                                         | `nautobot.core.management`             |
| `nautobot.utilities.ordering`        | `*`                                                         | `nautobot.core.utils.ordering`         |
| `nautobot.utilities.paginator`       | `*`                                                         | `nautobot.core.views.paginator`        |
| `nautobot.utilities.permissions`     | `*`                                                         | `nautobot.core.utils.permissions`      |
| `nautobot.utilities.query_functions` | `*`                                                         | `nautobot.core.models.query_functions` |
| `nautobot.utilities.querysets`       | `*`                                                         | `nautobot.core.models.querysets`       |
| `nautobot.utilities.tables`          | `*`                                                         | `nautobot.core.tables`                 |
| `nautobot.utilities.tasks`           | `*`                                                         | `nautobot.core.tasks`                  |
| `nautobot.utilities.templatetags`    | `*`                                                         | `nautobot.core.templatetags`           |
| `nautobot.utilities.testing`         | `*`                                                         | `nautobot.core.testing`                |
| `nautobot.utilities.tree_queries`    | `*`                                                         | `nautobot.core.models.tree_queries`    |
| `nautobot.utilities.utils`           | `array_to_string`                                           | `nautobot.core.models.utils`           |
|                                      | `convert_querydict_to_factory_formset_acceptable_querydict` | `nautobot.core.utils.requests`         |
|                                      | `copy_safe_request`                                         | `nautobot.core.utils.requests`         |
|                                      | `count_related`                                             | `nautobot.core.models.querysets`       |
|                                      | `csv_format`                                                | `nautobot.core.views.utils`            |
|                                      | `deepmerge`                                                 | `nautobot.core.utils.data`             |
|                                      | `dict_to_filter_params`                                     | `nautobot.core.api.utils`              |
|                                      | `dynamic_import`                                            | `nautobot.core.api.utils`              |
|                                      | `ensure_content_type_and_field_name_inquery_params`         | `nautobot.core.utils.requests`         |
|                                      | `flatten_dict`                                              | `nautobot.core.utils.data`             |
|                                      | `flatten_iterable`                                          | `nautobot.core.utils.data`             |
|                                      | `foreground_color`                                          | `nautobot.core.utils.color`            |
|                                      | `get_all_lookup_expr_for_field`                             | `nautobot.core.utils.filtering`        |
|                                      | `get_api_version_serializer`                                | `nautobot.core.api.utils`              |
|                                      | `get_changes_for_model`                                     | `nautobot.core.utils.lookup`           |
|                                      | `get_filterset_field`                                       | `nautobot.core.utils.filtering`        |
|                                      | `get_filterset_for_model`                                   | `nautobot.core.utils.lookup`           |
|                                      | `get_filterable_params_from_filter_params`                  | `nautobot.core.utils.requests`         |
|                                      | `get_form_for_model`                                        | `nautobot.core.utils.lookup`           |
|                                      | `get_model_from_name`                                       | `nautobot.core.utils.lookup`           |
|                                      | `get_related_class_for_model`                               | `nautobot.core.utils.lookup`           |
|                                      | `get_route_for_model`                                       | `nautobot.core.utils.lookup`           |
|                                      | `get_table_for_model`                                       | `nautobot.core.utils.lookup`           |
|                                      | `hex_to_rgb`                                                | `nautobot.core.utils.color`            |
|                                      | `is_taggable`                                               | `nautobot.core.models.utils`           |
|                                      | `is_uuid`                                                   | `nautobot.core.utils.data`             |
|                                      | `lighten_color`                                             | `nautobot.core.utils.color`            |
|                                      | `normalize_querydict`                                       | `nautobot.core.utils.requests`         |
|                                      | `prepare_cloned_fields`                                     | `nautobot.core.views.utils`            |
|                                      | `pretty_print_query`                                        | `nautobot.core.models.utils`           |
|                                      | `render_jinja2`                                             | `nautobot.core.utils.data`             |
|                                      | `rgb_to_hex`                                                | `nautobot.core.utils.color`            |
|                                      | `SerializerForAPIVersions`                                  | `nautobot.core.api.utils`              |
|                                      | `serialize_object`                                          | `nautobot.core.models.utils`           |
|                                      | `serialize_object_v2`                                       | `nautobot.core.models.utils`           |
|                                      | `shallow_compare_dict`                                      | `nautobot.core.utils.data`             |
|                                      | `slugify_dots_to_dashes`                                    | `nautobot.core.models.fields`          |
|                                      | `slugify_dashes_to_underscores`                             | `nautobot.core.models.fields`          |
|                                      | `to_meters`                                                 | `nautobot.core.utils.data`             |
|                                      | `UtilizationData`                                           | `nautobot.core.utils.data`             |
|                                      | `versioned_serializer_selector`                             | `nautobot.core.api.utils`              |
| `nautobot.utilities.validators`      | `*`                                                         | `nautobot.core.models.validators`      |
| `nautobot.utilities.views`           | `*`                                                         | `nautobot.core.views.mixins`           |
