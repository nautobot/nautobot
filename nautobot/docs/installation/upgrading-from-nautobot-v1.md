# Upgrading from Nautobot v1.X

## Dependency Changes

- Nautobot no longer uses or supports the use of `django-mptt`.
- Nautobot no longer uses or supports the use of `django-rq`.

## Database (ORM) Changes

### Database Behavior Changes

| Model        | Field          | Changes                                                                           |
|--------------|----------------|-----------------------------------------------------------------------------------|
| (all)        | `created`      | Changed from DateField to DateTimeField                                           |
| JobLogEntry  | `absolute_url` | No longer accepts `null` values, use `""` instead                                 |
|              | `log_object`   | No longer accepts `null` values, use `""` instead                                 |
| Prefix       | `is_pool`      | Replaced by new field `type`, valid choices are "Container", "Network" and "Pool" |
|              | `status`       | Container status has been replaced by new field `type`                            |
| ScheduledJob | `queue`        | No longer accepts `null` values, use `""` instead                                 |
| Webhook      | `ca_file_path` | No longer accepts `null` values, use `""` instead                                 |

### Renamed Database Fields

| Model                   | Renamed Field                           | New Name                                       |
|-------------------------|-----------------------------------------|------------------------------------------------|
| CablePath               | `circuittermination`                    | `circuit_terminations`                         |
|                         | `consoleport`                           | `console_ports`                                |
|                         | `consoleserverport`                     | `console_server_ports`                         |
|                         | `interface`                             | `interfaces`                                   |
|                         | `powerfeed`                             | `power_feeds`                                  |
|                         | `poweroutlet`                           | `power_outlets`                                |
|                         | `powerport`                             | `power_ports`                                  |
| Circuit                 | `termination_a`                         | `circuit_termination_a`                        |
|                         | `termination_z`                         | `circuit_termination_z`                        |
|                         | `terminations`                          | `circuit_terminations`                         |
|                         | `type`                                  | `circuit_type`                                 |
| Cluster                 | `group`                                 | `cluster_group`                                |
|                         | `type`                                  | `cluster_type`                                 |
| ConfigContextSchema     | `schema`                                | `config_context_schema`                        |
|                         | `device_set`                            | `devices`                                      |
|                         | `virtualmachine_set`                    | `virtual_machines`                             |
| ContentType             | `computedfield_set`                     | `computed_fields`                              |
|                         | `configcontext_set`                     | `config_contexts`                              |
|                         | `configcontextschema_set`               | `config_context_schemas`                       |
|                         | `customlink_set`                        | `custom_links`                                 |
|                         | `dcim_device_related`                   | `devices`                                      |
|                         | `dynamicgroup_set`                      | `dynamic_groups`                               |
|                         | `exporttemplate_set`                    | `export_templates`                             |
|                         | `imageattachment_set`                   | `image_attachments`                            |
|                         | `note_set`                              | `notes`                                        |
|                         | `virtualization_virtualmachine_related` | `virtual_machines`                             |
| CustomFieldChoice       | `field`                                 | `custom_field`                                 |
| CustomField             | `choices`                               | `custom_field_choices`                         |
|                         | `slug`                                  | `key`                                          |
| Device                  | `consoleports`                          | `console_ports`                                |
|                         | `consoleserverports`                    | `console_server_ports`                         |
|                         | `devicebays`                            | `device_bays`                                  |
|                         | `device_role`                           | `role`                                         |
|                         | `frontports`                            | `front_ports`                                  |
|                         | `inventoryitems`                        | `inventory_items`                              |
|                         | `local_context_data`                    | `local_config_context_data`                    |
|                         | `local_context_data_owner_content_type` | `local_config_context_data_owner_content_type` |
|                         | `local_context_data_owner_object_id`    | `local_config_context_data_owner_object_id`    |
|                         | `local_context_schema`                  | `local_config_context_schema`                  |
|                         | `poweroutlets`                          | `power_outlets`                                |
|                         | `powerports`                            | `power_ports`                                  |
|                         | `rearports`                             | `rear_ports`                                   |
| DeviceRedundancyGroup   | `members`                               | `devices`                                      |
| DeviceType              | `consoleporttemplates`                  | `console_port_templates`                       |
|                         | `consoleserverporttemplates`            | `console_server_port_templates`                |
|                         | `devicebaytemplates`                    | `device_bay_templates`                         |
|                         | `frontporttemplates`                    | `front_port_templates`                         |
|                         | `interfacetemplates`                    | `interface_templates`                          |
|                         | `instances`                             | `devices`                                      |
|                         | `poweroutlettemplates`                  | `power_outlet_templates`                       |
|                         | `powerporttemplates`                    | `power_port_templates`                         |
|                         | `rearporttemplates`                     | `rear_port_templates`                          |
| FrontPortTemplate       | `rear_port`                             | `rear_port_template`                           |
| InventoryItem           | `child_items`                           | `children`                                     |
|                         | `level`                                 | `tree_depth`                                   |
| Job                     | `job_hook`                              | `job_hooks`                                    |
|                         | `results`                               | `job_results`                                  |
| JobResult               | `logs`                                  | `job_log_entries`                              |
|                         | `schedule`                              | `scheduled_job`                                |
| Location                | `powerpanels`                           | `power_panels`                                 |
| PowerOutletTemplate     | `power_port`                            | `power_port_template`                          |
| PowerPanel              | `powerfeeds`                            | `power_feeds`                                  |
| PowerPort               | `poweroutlets`                          | `power_outlets`                                |
| PowerPortTemplate       | `poweroutlet_templates`                 | `power_outlet_templates`                       |
| Rack                    | `group`                                 | `rack_group`                                   |
|                         | `powerfeed_set`                         | `power_feeds`                                  |
|                         | `reservations`                          | `rack_reservations`                            |
| RackGroup               | `level`                                 | `tree_depth`                                   |
|                         | `powerpanel_set`                        | `power_panels`                                 |
| RearPort                | `frontports`                            | `front_ports`                                  |
| RearPortTemplate        | `frontport_templates`                   | `front_port_templates`                         |
| Region                  | `level`                                 | `tree_depth`                                   |
| Relationship            | `associations`                          | `relationship_associations`                    |
| Secret                  | `groups`                                | `secrets_groups`                               |
|                         | `secretsgroupassociation_set`           | `secrets_group_associations`                   |
| RIR                     | `aggregates`                            | [`prefixes`](#aggregate-migrated-to-prefix)    |
| SecretsGroup            | `device_set`                            | `devices`                                      |
|                         | `deviceredundancygroup_set`             | `device_redundancy_groups`                     |
|                         | `gitrepository_set`                     | `git_repositories`                             |
|                         | `secretsgroupassociation_set`           | `secrets_group_associations`                   |
| SecretsGroupAssociation | `group`                                 | `secrets_group`                                |
| Service                 | `ipaddresses`                           | `ip_addresses`                                 |
| Status                  | `circuits_circuit_related`              | `circuits`                                     |
|                         | `dcim_cable_related`                    | `cables`                                       |
|                         | `dcim_device_related`                   | `devices`                                      |
|                         | `dcim_deviceredundancygroup_related`    | `device_redundancy_groups`                     |
|                         | `dcim_interface_related`                | `interfaces`                                   |
|                         | `dcim_location_related`                 | `locations`                                    |
|                         | `dcim_powerfeed_related`                | `power_feeds`                                  |
|                         | `dcim_rack_related`                     | `racks`                                        |
|                         | `ipam_ipaddress_related`                | `ip_addresses`                                 |
|                         | `ipam_prefix_related`                   | `prefixes`                                     |
|                         | `ipam_vlan_related`                     | `vlans`                                        |
|                         | `virtualization_virtualmachine_related` | `virtual_machines`                             |
|                         | `virtualization_vminterface_related`    | `vm_interfaces`                                |
| Tenant                  | `group`                                 | `tenant_group`                                 |
|                         | `rackreservations`                      | `rack_reservations`                            |
| TenantGroup             | `level`                                 | `tree_depth`                                   |
| User                    | `changes`                               | `object_changes`                               |
|                         | `note`                                  | `notes`                                        |
|                         | `rackreservation_set`                   | `rack_reservations`                            |
| VirtualMachine          | `local_context_data`                    | `local_config_context_data`                    |
|                         | `local_context_data_owner_content_type` | `local_config_context_data_owner_content_type` |
|                         | `local_context_data_owner_object_id`    | `local_config_context_data_owner_object_id`    |
|                         | `local_context_schema`                  | `local_config_context_schema`                  |
| VLAN                    | `group`                                 | `vlan_group`                                   |

### Removed Database Fields

| Model                   | Removed Field |
|-------------------------|---------------|
| CircuitTermination      | `site`        |
| CircuitType             | `slug`        |
| Cluster                 | `site`        |
| ClusterGroup            | `slug`        |
| ClusterType             | `slug`        |
| ConfigContext           | `sites`       |
| CustomLink              | `slug`        |
|                         | `regions`     |
| CustomField             | `name`        |
| Device                  | `site`        |
| DeviceRedundancyGroup   | `slug`        |
| DynamicGroup            | `slug`        |
| GitRepository           | `_token`      |
| GraphQLQuery            | `slug`        |
|                         | `username`    |
| InventoryItem           | `lft`         |
|                         | `rght`        |
|                         | `tree_id`     |
| JobHook                 | `slug`        |
| Location                | `site`        |
| Manufacturer            | `slug`        |
| Platform                | `slug`        |
| Provider                | `slug`        |
| PowerFeed               | `site`        |
| PowerPanel              | `site`        |
| Prefix                  | `is_pool`     |
|                         | `site`        |
| Rack                    | `site`        |
| RackGroup               | `lft`         |
|                         | `rght`        |
|                         | `tree_id`     |
| Region                  | `lft`         |
|                         | `rght`        |
|                         | `tree_id`     |
| RIR                     | `slug`        |
| RelationshipAssociation | `slug`        |
| Role                    | `slug`        |
| RouteTarget             | `slug`        |
| Secret                  | `slug`        |
| SecretsGroup            | `slug`        |
| SecretsGroupAssociation | `slug`        |
| Status                  | `slug`        |
| Tenant                  | `slug`        |
| TenantGroup             | `lft`         |
|                         | `rght`        |
|                         | `slug`        |
|                         | `tree_id`     |
| VLAN                    | `site`        |
| VLANGroup               | `site`        |
| Webhook                 | `slug`        |

### Replaced Models

#### Generic Role Model

The `ipam.Role`, `dcim.RackRole`, and `dcim.DeviceRole` models have been removed and replaced by a single `extras.Role` model. This means that any references to the removed models in the code now use the `extras.Role` model instead.

| Removed Model     | Replaced With  |
|-------------------|----------------|
| `dcim.DeviceRole` | `extras.Role`  |
| `dcim.RackRole`   | `extras.Role`  |
| `ipam.Role`       | `extras.Role`  |

#### Site and Region Models

The `dcim.Region` and `dcim.Site` models have been removed and replaced by `dcim.Location` model. This means that any references to the removed models in the code now use the `dcim.Location` model instead with `LocationType` "Site" and "Region".

!!! important
    If you are a Nautobot App developer, or have any Apps installed that include data models that reference `Site` or `Region`, please review the [Region and Site Related Data Model Migration Guide](../installation/region-and-site-data-migration-guide.md#region-and-site-related-data-model-migration-guide-for-existing-nautobot-app-installations) to learn how to migrate your apps and models from `Site` and `Region` to `Location`.

| Removed Model     | Replaced With  |
|-------------------|----------------|
| `dcim.Region`     | `dcim.Location`|
| `dcim.Site`       | `dcim.Location`|

#### Aggregate Migrated to Prefix

The `ipam.Aggregate` model has been removed and all existing Aggregates will be migrated to `ipam.Prefix` records with their `type` set to "Container". The `Aggregate.date_added` field will be migrated to `Prefix.date_allocated` and changed from a Date field to a DateTime field with the time set to `00:00` UTC. `Aggregate.tenant`, `Aggregate.rir` and `Aggregate.description` will be migrated over to the equivalent fields on the new `Prefix`. ObjectChanges, Tags, Notes, Permissions, Custom Fields, Custom Links, Computed Fields and Relationships will be migrated to relate to the new `Prefix` as well.

If a `Prefix` already exists with the same network and prefix length as a previous `Aggregate`, the `rir` and `date_added` fields will be copied to the `rir` and `date_allocated` fields on the existing Prefix object. Messages will be output during migration (`nautobot-server migrate` or `nautobot-server post_upgrade`) if the `tenant`, `description` or `type` fields need to be manually migrated.

| Aggregate        | Prefix               |
|------------------|----------------------|
| `broadcast`      | `broadcast`          |
| **`date_added`** | **`date_allocated`** |
| `description`    | `description`        |
| `network`        | `network`            |
| `prefix_length`  | `prefix_length`      |
| `rir`            | `rir`                |
| `tenant`         | `tenant`             |

## GraphQL and REST API Changes

### API Behavior Changes

| Model                 | Field          | Changes                                                                                                  |
|-----------------------|----------------|----------------------------------------------------------------------------------------------------------|
| (all)                 | `created`      | Now is a date/time (`"2023-02-14T19:57:45.320232Z"`) rather than only a date                             |
| Cable                 | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Circuit               | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Device                | `location`     | Now `location` has changed to a required field on this model Serializer                                  |
|                       | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| DeviceRedundancyGroup | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Interface             | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| IPAddress             | `role`         | `/ipam/ip-addresses/` endpoint now uses role nested serializer for the role field, rather than a string. |
|                       | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Location              | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| PowerFeed             | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| PowerPanel            | `location`     | Now `location` has changed to a required field on this model Serializer                                  |
| Prefix                | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| Rack                  | `location`     | Now `location` has changed to a required field on this model Serializer                                  |
|                       | `status`       | Now uses a nested Status serializer, rather than `{"value": "<slug>", "label": "<name>"}`                |
| RackGroup             | `location`     | Now `location` has changed to a required field on this model Serializer                                  |
|                       | `rack_count`   | Now only counts Racks directly belonging to this RackGroup, not those belonging to its descendants.      |
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
| CustomField             | `slug`                 | `key`                         |
| CustomFieldChoice       | `field`                | `custom_field`                |
| Device                  | `device_role`          | `role`                        |
|                         | `local_context_data`   | `local_config_context_data`   |
|                         | `local_context_schema` | `local_config_context_schema` |
| FrontPortTemplate       | `rear_port`            | `rear_port_template`          |
| Interface               | `count_ipaddresses`    | `ip_address_count`            |
| InventoryItem           | `_depth`               | `tree_depth`                  |
| Location                | `virtualmachine_count` | `virtual_machine_count`       |
| Manufacturer            | `devicetype_count`     | `device_type_count`           |
|                         | `inventoryitem_count`  | `inventory_item_count`        |
| Platform                | `virtualmachine_count` | `virtual_machine_count`       |
| PowerOutletTemplate     | `power_port`           | `power_port_template`         |
| PowerPanel              | `powerfeed_count`      | `power_feed_count`            |
| Rack                    | `group`                | `rack_group`                  |
|                         | `powerfeed_count`      | `power_feed_count`            |
| JobResult               | `schedule`             | `scheduled_job`               |
| RackGroup               | `_depth`               | `tree_depth`                  |
| Region                  | `_depth`               | `tree_depth`                  |
| SecretsGroupAssociation | `group`                | `secrets_group`               |
| Service                 | `ipaddresses`          | `ip_addresses`                |
| Tenant                  | `group`                | `tenant_group`                |
| TenantGroup             | `_depth`               | `tree_depth`                  |
| VirtualMachine          | `local_context_data`   | `local_config_context_data`   |
|                         | `local_context_schema` | `local_config_context_schema` |
| VLAN                    | `group`                | `vlan_group`                  |

### Removed Serializer Fields

| Model/Endpoint                       | Removed Field        | Comments                                              |
|--------------------------------------|----------------------|-------------------------------------------------------|
| `/api/status/`                       | `rq-workers-running` | Removed as RQ is no longer supported                  |
| `/circuits/circuit-terminations/`    | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/circuits/circuit-types/`           | `slug`               | `slug` field no longer supported                      |
| `/circuits/providers/`               | `slug`               | `slug` field no longer supported                      |
| `/extras/config-contexts/`           | `regions`            | `Site` and `Region` models are replaced by `Location` |
|                                      | `sites`              | `Site` and `Region` models are replaced by `Location` |
| `/dcim/device-redundancy-groups/`    | `slug`               | `slug` field no longer supported                      |
| `/dcim/devices/`                     | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/dcim/locations/`                   | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/dcim/manufacturers/`               | `slug`               | `slug` field no longer supported                      |
| `/dcim/platforms/`                   | `slug`               | `slug` field no longer supported                      |
| `/dcim/power-feeds/`                 | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/dcim/power-panels/`                | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/dcim/racks/`                       | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/dcim/rack-groups/`                 | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/extras/custom-links/`              | `slug`               | `slug` field no longer supported                      |
| `/extras/dynamic-groups/`            | `slug`               | `slug` field no longer supported                      |
| `/extras/graphql-queries/`           | `slug`               | `slug` field no longer supported                      |
| `/extras/job-hooks/`                 | `slug`               | `slug` field no longer supported                      |
| `/extras/relationship-associations/` | `slug`               | `slug` field no longer supported                      |
| `/extras/roles/`                     | `slug`               | `slug` field no longer supported                      |
| `/extras/secrets/`                   | `slug`               | `slug` field no longer supported                      |
| `/extras/secrets-groups/`            | `slug`               | `slug` field no longer supported                      |
| `/extras/statuses/`                  | `slug`               | `slug` field no longer supported                      |
| `/extras/webhooks/`                  | `slug`               | `slug` field no longer supported                      |
| `/ipam/prefixes/`                    | `is_pool`            | Functionality replaced by `type` field                |
|                                      | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/ipam/rirs/`                        | `slug`               | `slug` field no longer supported                      |
| `/ipam/route-targets/`               | `slug`               | `slug` field no longer supported                      |
| `/ipam/vlans/`                       | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/ipam/vlangroups/`                  | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/virtualization/clusters/`          | `site`               | `Site` and `Region` models are replaced by `Location` |
| `/tenancy/tenants/`                  | `slug`               | `slug` field no longer supported                      |
| `/tenancy/tenant-groups/`            | `slug`               | `slug` field no longer supported                      |
| `/virtualization/cluster-groups/`    | `slug`               | `slug` field no longer supported                      |
| `/virtualization/cluster-types/`     | `slug`               | `slug` field no longer supported                      |

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

| Model                   | Renamed Filter Field      | New Name                         | UI and Rest API endpoints Available in v2.X                               |
|-------------------------|---------------------------|----------------------------------|---------------------------------------------------------------------------|
| Cable                   | `tag`                     | `tags`                           | `/dcim/cables/?tags=<uuid/slug>`                                          |
| Circuit                 | `tag`                     | `tags`                           | `/circuits/circuits/?tags=<uuid/slug>`                                    |
|                         | `type`                    | `circuit_type`                   | `/circuits/circuits/?circuit_type=<uuid/slug>`                            |
| Cluster                 | `tag`                     | `tags`                           | `/virtualization/clusters/?tags=<uuid/slug>`                              |
| ConsolePort             | `cabled`                  | `has_cable`                      | `/dcim/console-ports/?has_cable=True/False`                               |
| ConsoleServerPort       | `cabled`                  | `has_cable`                      | `/dcim/console-server-ports/?has_cable=True/False`                        |
| CustomFieldChoice       | `field`                   | `custom_field`                   | `/extras/custom-field-choices/?custom_field=<uuid/key>`                   |
| Device                  | `cluster_id`              | `cluster`                        | `/dcim/devices/?cluster=<uuid/slug>`                                      |
|                         | `device_type_id`          | `device_type`                    | `/dcim/devices/?device_type=<uuid/slug>`                                  |
|                         | `local_context_data`      | `local_config_context_data`      | `/dcim/devices/?local_config_context_data=True/False`                     |
|                         | `local_context_schema_id` | `local_config_context_schema_id` | `/dcim/devices/?local_config_context_schema_id=<uuid>`                    |
|                         | `local_context_schema`    | `local_config_context_schema`    | `/dcim/devices/?local_config_context_schema=<slug>`                       |
|                         | `rack_group_id`           | `rack_group`                     | `/dcim/devices/?rack_group=<uuid/slug>`                                   |
|                         | `rack_id`                 | `rack`                           | `/dcim/devices/?rack=<uuid/slug>`                                         |
|                         | `tag`                     | `tags`                           | `/dcim/devices/?tags=<uuid/slug>`                                         |
|                         | `virtual_chassis_id`      | `virtual_chassis`                | `/dcim/devices/?virtual_chassis=<uuid/slug>`                              |
| DeviceBay               | `tag`                     | `tags`                           | `/dcim/device-bays/?tags=<uuid/slug>`                                     |
| DeviceRedundancyGroup   | `tag`                     | `tags`                           | `/dcim/device-redundancy-groups/?tag=<uuid/slug>`                         |
| DeviceType              | `has_instances`           | `has_devices`                    | `/dcim/device-types/?has_devices=True/False`                              |
|                         | `instances`               | `devices`                        | `/dcim/device-types/?devices=<uuid>`                                      |
|                         | `tag`                     | `tags`                           | `/dcim/device-types/?tags=<uuid/slug>`                                    |
| FrontPort               | `cabled`                  | `has_cable`                      | `/dcim/front-ports/?has_cable=True/False`                                 |
|                         | `tag`                     | `tags`                           | `/dcim/front-ports/?tags=<uuid/slug>`                                     |
| GitRepository           | `tag`                     | `tags`                           | `/extras/git-repositories/?tags=<uuid/slug>`                              |
| Interface               | `cabled`                  | `has_cable`                      | `/dcim/interfaces/?has_cable=True/False`                                  |
| InventoryItem           | `child_items`             | `children`                       | `/dcim/inventory-items/?children=<uuid/name>`                             |
|                         | `has_child_items`         | `has_children`                   | `/dcim/inventory-items/?has_children=True/False`                          |
|                         | `tag`                     | `tags`                           | `/dcim/inventory-items/?tags=<uuid/slug>`                                 |
| IPAddress               | `tag`                     | `tags`                           | `/ipam/ip-addresses/?tags=<uuid/slug>`                                    |
| Job                     | `tag`                     | `tags`                           | `/extras/jobs/?tags=<uuid/slug>`                                          |
| Location                | `tag`                     | `tags`                           | `/dcim/locations/?tags=uuid/slug>`                                        |
| ObjectPermission        | `group`                   | `groups`                         | `/users/permissions/?groups=<slug>`                                       |
|                         | `group_id`                | `groups_id`                      | `/users/permissions/?groups_id=<id>`                                      |
|                         | `user`                    | `users`                          | `/users/permissions/?users=<uuid/username>`                               |
| PowerFeed               | `cabled`                  | `has_cable`                      | `/dcim/power-feeds/?has_cable=True/False`                                 |
|                         | `tag`                     | `tags`                           | `/dcim/power-feeds/?tags=<uuid/slug>`                                     |
| PowerOutlet             | `cabled`                  | `has_cable`                      | `/dcim/power-outlets/?has_cable=True/False`                               |
| PowerPanel              | `tag`                     | `tags`                           | `/dcim/power-panels/?tags=<uuid/slug>`                                    |
| PowerPort               | `cabled`                  | `has_cable`                      | `/dcim/power-ports/?has_cable=True/False`                                 |
| Prefix                  | `is_pool`                 | `type`                           | `/ipam/prefixes/?type=<container/network/pool>`                           |
|                         | `tag`                     | `tags`                           | `/ipam/prefixes/?tags=<uuid/slug>`                                        |
| Provider                | `tag`                     | `tags`                           | `/circuits/provider/?tags=<uuid/slug>`                                    |
| ProviderNetwork         | `tag`                     | `tags`                           | `/circuits/provider-networks/?tags=<uuid/slug>`                           |
| Rack                    | `group`                   | `rack_group`                     | `/dcim/racks/?rack_group=<uuid/slug>`                                     |
|                         | `has_reservations`        | `has_rack_reservations`          | `/dcim/racks/?has_rack_reservations=True/False`                           |
|                         | `reservations`            | `rack_reservations`              | `/dcim/racks/?rack_reservations=<uuid>`                                   |
|                         | `tag`                     | `tags`                           | `/dcim/racks/?tags=<uuid/slug>`                                           |
| RackReservation         | `group`                   | `rack_group`                     | `/dcim/rack-reservations/?rack_group=<uuid/slug>`                         |
|                         | `tag`                     | `tags`                           | `/dcim/rack-reservations/?tags=<uuid/slug>`                               |
| RearPort                | `cabled`                  | `has_cable`                      | `/dcim/rear-ports/?has_cable=True/False`                                  |
|                         | `tag`                     | `tags`                           | `/dcim/rear-ports/?tags=<uuid/slug>`                                      |
| RouteTarget             | `tag`                     | `tags`                           | `/ipam/route-targets/?tags=<uuid/slug>`                                   |
| SecretsGroupAssociation | `group`                   | `secrets_group`                  | `/extras/secrets-groups-associations/?secrets_group=<uuid/slug>`          |
| Service                 | `tag`                     | `tags`                           | `/ipam/services/?tags=<uuid/slug>`                                        |
| Site                    | `tag`                     | `tags`                           | `/dcim/sites/?tags=<uuid/slug>`                                           |
| Tenant                  | `tag`                     | `tags`                           | `/tenancy/tenants/?tags=<uuid/slug>`                                      |
| User                    | `changes`                 | `object_changes`                 | `/users/users/?object_changes=<id>`                                       |
|                         | `has_changes`             | `has_object_changes`             | `/users/users/?has_object_changes=True/False`                             |
|                         | `group`                   | `groups`                         | `/users/users/?groups=<slug>`                                             |
|                         | `group_id`                | `groups_id`                      | `/users/users/?groups_id=<id>`                                            |
| VirtualMachine          | `local_context_data`      | `local_config_context_data`      | `/virtualization/virtual-machines/?local_config_context_data=True/False`  |
|                         | `local_context_schema_id` | `local_config_context_schema_id` | `/virtualization/virtual-machines/?local_config_context_schema_id=<uuid>` |
|                         | `local_context_schema`    | `local_config_context_schema`    | `/virtualization/virtual-machines/?local_config_context_schema=<slug>`    |
|                         | `tag`                     | `tags`                           | `/virtualization/virtual-machines/?tags=<uuid/slug>`                      |
| VLAN                    | `tag`                     | `tags`                           | `/ipam/vlans/?tags=<uuid/slug>`                                           |
| VMInterface             | `tag`                     | `tags`                           | `/virtualization/interfaces/?tags=<uuid/slug>`                            |
| VRF                     | `tag`                     | `tags`                           | `/ipam/vrfs/?tags=<uuid/slug>`                                            |

### Enhanced Filter Fields

Below is a table documenting [enhanced filter field changes](../release-notes/version-2.0.md#enhanced-filter-fields-2804) in v2.x.

| Model                   | Enhanced Filter Field     | Changes                                                    | UI and Rest API endpoints Available in v2.X                    |
|-------------------------|---------------------------|------------------------------------------------------------|----------------------------------------------------------------|
| (all)                   | `created[__(gte/lte)]`    | Now can filter on multiple values; now supports date-times | `?created__gte=2023-02-14%2012:00:00`                          |
| Cable                   | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/cabels/?tenant=<uuid/name>`                             |
| Circuit                 | `circuit_type`            | Enhanced to support primary key UUIDs in addition to names | `/circuits/circuits/?circuit_type=<uuid/name>`                 |
|                         | `provider`                | Enhanced to support primary key UUIDs in addition to names | `/circuits/circuits/?provider=<uuid/name>`                     |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/circuits/circuits/?tenant=<uuid/name>`                       |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/circuits/circuits/?tenant_group=<uuid/name>`                 |
| Cluster                 | `cluster_group`           | Enhanced to support primary key UUIDs in addition to names | `/virtualization/clusters/?cluster_group=<uuid/name>`          |
|                         | `cluster_type`            | Enhanced to support primary key UUIDs in addition to names | `/virtualization/clusters/?cluster_type=<uuid/name>`           |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/virtualization/clusters/?tenant=<uuid/name>`                 |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/virtualization/clusters/?tenant_group=<uuid/name>`           |
| ConfigContext           | `cluster_group`           | Enhanced to support primary key UUIDs in addition to names | `/extras/config-contexts/?cluster_group=<uuid/name>`           |
|                         | `device_redundancy_group` | Enhanced to support primary key UUIDs in addition to names | `/extras/config-contexts/?device_redundancy_group=<uuid/name>` |
|                         | `platform`                | Enhanced to support primary key UUIDs in addition to names | `/extras/config-contexts/?platform=<uuid/name>`                |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/extras/config-contexts/?tenant=<uuid/name>`                  |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/extras/config-contexts/?tenant_group=<uuid/name>`            |
|                         | `dynamic_groups`          | Enhanced to support primary key UUIDs in addition to names | `/extras/config-contexts/?dynamic_groups=<uuid/name>`          |
| ConsolePort             | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-ports/?device=<uuid/name>`                      |
| ConsoleServerPort       | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/console-server-ports/?device=<uuid/name>`               |
| Device                  | `cluster_id`              | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?cluster=<uuid/slug>`                           |
|                         | `device_type_id`          | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?device_type=<uuid/slug>`                       |
|                         | `device_redundancy_group` | Enhanced to support primary key UUIDs in addition to names | `/dcim/devices/?device_redundancy_group=<uuid/name>`           |
|                         | `manufacturer`            | Enhanced to support primary key UUIDs in addition to names | `/dcim/devices/?manufacturer=<uuid/name>`                      |
|                         | `platform`                | Enhanced to support primary key UUIDs in addition to names | `/dcim/devices/?platform=<uuid/name>`                          |
|                         | `role`                    | Enhanced to support primary key UUIDs in addition to names | `/dcim/devices/?role=<uuid/name>`                              |
|                         | `rack_id`                 | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack=<uuid/slug>`                              |
|                         | `rack_group_id`           | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?rack_group=<uuid/slug>`                        |
|                         | `serial`                  | Enhanced to permit filtering on multiple values            | `/dcim/devices/?serial=<value>&serial=<value>...`              |
|                         | `secrets_group`           | Enhanced to support primary key UUIDs in addition to names | `/dcim/devices/?secrets_group=<uuid/name>`                     |
|                         | `virtual_chassis_id`      | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/devices/?virtual_chassis=<uuid/slug>`                   |
| DeviceBay               | `cable`                   | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/regions/?parent=<uuid/slug>`                            |
|                         | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/device-bays/?device=<uuid/name>`                        |
| DeviceType              | `manufacturer`            | Enhanced to support primary key UUIDs in addition to names | `/dcim/device-types/?manufacturer=<uuid/name>`                 |
| DeviceRedundancyGroup   | `secrets_group`           | Enhanced to support primary key UUIDs in addition to names | `/dcim/device-redundancy-groups/?secrets_group=<uuid/name>`    |
| DynamicGroupMembership  | `group`                   | Enhanced to support primary key UUIDs in addition to names | `/extras/dynamic-froup-membership/?group=<uuid/name>`          |
|                         | `parent_group`            | Enhanced to support primary key UUIDs in addition to names | `/extras/dynamic-froup-membership/?parent_group=<uuid/name>`   |
| FrontPort               | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/front-ports/?device=<uuid/name>`                        |
| GitRepository           | `secrets_group`           | Enhanced to support primary key UUIDs in addition to names | `/extras/git-repository/?secrets_group=<uuid/name>`            |
| Interface               | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/interfaces/?device=<uuid/name>`                         |
| IPAddress               | `rir`                     | Enhanced to support primary key UUIDs in addition to names | `/ipam/ip-addresses/?rir=<uuid/name>`                          |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/ipam/ip-addresses/?tenant=<uuid/name>`                       |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/ipam/ip-addresses/?tenant_group=<uuid/name>`                 |
| InventoryItem           | `device`                  | Enhanced to support primary key UUIDs in addition to name  | `/dcim/inventory-items/?device=<uuid/name>`                    |
|                         | `manufacturer`            | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/inventory-items/?manufacturer=<uuid/slug>`              |
|                         | `serial`                  | Enhanced to permit filtering on multiple values            | `/dcim/inventory-items/?serial=<value>&serial=<value>...`      |
| Manufacturer            | `platforms`               | Enhanced to support primary key UUIDs in addition to names | `/dcim/manufacturers/?platforms=<uuid/name>`                   |
| Platform                | `manufacturer`            | Enhanced to support primary key UUIDs in addition to names | `/dcim/platforms/?manufacturer=<uuid/name>`                    |
| PowerOutlet             | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-outlets/?device=<uuid/name>`                      |
| PowerPort               | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/power-ports/?device=<uuid/name>`                        |
| Prefix                  | `rir`                     | Enhanced to support primary key UUIDs in addition to names | `/ipam/prefixes/?rir=<uuid/name>`                              |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/ipam/prefixes/?tenant=<uuid/name>`                           |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/ipam/prefixes/?tenant_group=<uuid/name>`                     |
| ProviderNetwork         | `provider`                | Enhanced to support primary key UUIDs in addition to names | `/circuits/provider-networks/?provider=<uuid/name>`            |
| Rack                    | `role`                    | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/racks/?role=<uuid/slug>`                                |
|                         | `serial`                  | Enhanced to permit filtering on multiple values            | `/dcim/racks/?serial=<value>&serial=<value>...`                |
| RackGroup               | `parent`                  | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-groups/?parent=<uuid/slug>`                        |
| RackReservation         | `user`                    | Enhanced to support primary key UUIDs in addition to slugs | `/dcim/rack-reservations/?user=<uuid/slug>`                    |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/rack-reservations/?tenant=<uuid/name>`                  |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/dcim/rack-reservations/?tenant_group=<uuid/name>`            |
| RearPort                | `device`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/rear-ports/?device=<uuid/name>`                         |
| Region                  | `parent`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/regions/?parent=<uuid/slug>`                            |
| RouteTarget             | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/ipam/route-targets/?tenant=<uuid/name>`                      |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/ipam/route-targets/?tenant_group=<uuid/name>`                |
| SecretsGroupAssociation | `secrets`                 | Enhanced to support primary key UUIDs in addition to names | `/extras/secrets-group-association/?secrets=<uuid/name>`       |
|                         | `secrets_group`           | Enhanced to support primary key UUIDs in addition to names | `/extras/secrets-group-association/?secrets_group=<uuid/name>` |
| Tenant                  | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/tenancy/tenants/?tenant_group=<uuid/name>`                   |
| TenantGroup             | `parent`                  | Enhanced to support primary key UUIDs in addition to names | `/tenancy/tenant-groups/?parent=<uuid/name>`                   |
|                         | `children`                | Enhanced to support primary key UUIDs in addition to names | `/tenancy/tenant-groups/?children=<uuid/name>`                 |
|                         | `tenants`                 | Enhanced to support primary key UUIDs in addition to names | `/tenancy/tenant-groups/?tenants=<uuid/name>`                  |
| VirtualChassis          | `master`                  | Enhanced to support primary key UUIDs in addition to name  | `/dcim/virtual-chassis/?master=<uuid/name>`                    |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/dcim/virtual-chassis/?tenant=<uuid/name>`                    |
| VirtualMachine          | `cluster_group`           | Enhanced to support primary key UUIDs in addition to names | `/virtualization/virtual-machines/?cluster_group=<uuid/name>`  |
|                         | `cluster_type`            | Enhanced to support primary key UUIDs in addition to names | `/virtualization/virtual-machines/?cluster_type=<uuid/name>`   |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/virtualization/virtual-machines/?tenant=<uuid/name>`         |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/virtualization/virtual-machines/?tenant_group=<uuid/name>`   |
|                         | `platform`                | Enhanced to support primary key UUIDs in addition to names | `/virtualization/virtual-machines/?platform=<uuid/name>`       |
| VRF                     | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/ipam/vrfs/?tenant=<uuid/name>`                               |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/ipam/vrfs/?tenant_group=<uuid/name>`                         |
| VLAN                    | `available_on_device`     | Enhanced to permit filtering on multiple values            | `/ipam/vlans/?available_on_device=<uuid>&...`                  |
|                         | `vlan_group`              | Enhanced to support primary key UUIDs in addition to slugs | `/ipam/vlans/?vlan_group=<uuid/slug>`                          |
|                         | `tenant`                  | Enhanced to support primary key UUIDs in addition to names | `/ipam/vlans/?tenant=<uuid/name>`                              |
|                         | `tenant_group`            | Enhanced to support primary key UUIDs in addition to names | `/ipam/vlans/?tenant_group=<uuid/name>`                        |

### Corrected Filter Fields

Below is a table documenting [corrected filter field changes](../release-notes/version-2.0.md#corrected-filter-fields-2804) in v2.x.

| Model             | Changed Filter Field   | Before                                                   | After                                                                                    |
|-------------------|------------------------|----------------------------------------------------------|------------------------------------------------------------------------------------------|
| CustomFieldChoice | `custom_field`         | `/extras/custom-field-choices/?custom_field=<uuid/name>` | `/extras/custom-field-choices/?custom_field=<uuid/key>`                                  |
| Device            | `console_ports`        | `/dcim/devices/?console_ports=True`                      | `/dcim/devices/?console_ports=<uuid>` or `?has_console_ports=<True/False>`               |
|                   | `console_server_ports` | `/dcim/devices/?console_server_ports=True`               | `/dcim/devices/?console_server_ports=<uuid>` or `?has_console_server_ports=<True/False>` |
|                   | `device_bays`          | `/dcim/devices/?device_bays=True`                        | `/dcim/devices/?device_bays=<uuid>` or `?has_device_bays=<True/False>`                   |
|                   | `front_ports`          | `/dcim/devices/?front_ports=True`                        | `/dcim/devices/?front_ports=<uuid>` or `?has_front_ports=<True/False>`                   |
|                   | `interfaces`           | `/dcim/devices/?interfaces=True`                         | `/dcim/devices/?interfaces=<uuid>` or `?has_interfaces=<True/False>`                     |
|                   | `power_ports`          | `/dcim/devices/?power_ports=True`                        | `/dcim/devices/?power_ports=<uuid>` or `?has_power_ports=<True/False>`                   |
|                   | `power_outlets`        | `/dcim/devices/?power_outlets=True`                      | `/dcim/devices/?power_outlets=<uuid>` or `?has_power_outlets=<True/False>`               |
|                   | `rear_ports`           | `/dcim/devices/?rear_ports=True`                         | `/dcim/devices/?rear_ports=<uuid>` or `?has_rear_ports=<True/False>`                     |

### Removed Filter Fields

Below is a table documenting [removed filter field changes](../release-notes/version-2.0.md#removed-filter-fields-2804) in v2.x.
Unless stated otherwise, all of the `*_id=<uuid>` filters have been replaced by generic filters that support both uuid and slug.
For example `/circuits/circuits/?provider_id=<uuid>` has been replaced by `/circuits/circuits/?provider=<uuid>`.

In addition, `region_id`/`region` and `site_id`/`site` are all being removed because `Region` and `Site` Models are being collapsed into `Location` Model.
Their filters are also being replaced by `?location=<uuid/slug>`. For example `/dcim/devices/?site=ams-01` is replaced by `/dcim/devices/?location=ams-01`.

| Model                   | Removed Filter Field  | UI and API endpoints that are no longer supported in v2.X                                     |
|-------------------------|-----------------------|-----------------------------------------------------------------------------------------------|
| Aggregate               | `tenant_group_id`     |                                                                                               |
| Circuit                 | `provider_id`         |                                                                                               |
|                         | `provider_network_id` |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
|                         | `type_id`             | instead of `/circuits/circuits/?type_id=<uuid>`, use `circuit_type=<uuid>`                    |
| CircuitTermination      | `circuit_id`          |                                                                                               |
|                         | `provider_network_id` |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| CircuitType             | `slug`                |                                                                                               |
| Cluster                 | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
| ClusterGroup            | `slug`                |                                                                                               |
| ClusterType             | `slug`                |                                                                                               |
| ConfigContext           | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `role_id`             |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| ConsolePort             | `device_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| ConsoleServerPort       | `device_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| CustomFieldChoice       | `field_id`            | instead of `/extras/custom-field-choices/?field_id=<uuid>`, use `custom_field=<uuid>`         |
| CustomLink              | `slug`                |                                                                                               |
| Device                  | `manufacturer_id`     |                                                                                               |
|                         | `model`               | instead of `/dcim/devices/?model=<uuid>`, use `device_type=<uuid>`                            |
|                         | `pass_through_ports`  | instead of `/dcim/devices/?pass_through_ports=<bool>`, use `has_front_ports`/`has_rear_ports` |
|                         | `platform_id`         |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `role_id`             |                                                                                               |
|                         | `secrets_group_id`    |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
| DeviceBay               | `device_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| DeviceType              | `manufacturer_id`     |                                                                                               |
| DeviceRedundancyGroup   | `slug`                |                                                                                               |
| DynamicGroup            | `slug`                |                                                                                               |
| FrontPort               | `device_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| GraphQLQuery            | `slug`                |                                                                                               |
| Interface               | `bridge_id`           |                                                                                               |
|                         | `device_id`           |                                                                                               |
|                         | `lag_id`              |                                                                                               |
|                         | `parent_interface_id` |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| InventoryItem           | `device_id`           |                                                                                               |
|                         | `manufacturer_id`     |                                                                                               |
|                         | `parent_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| IPAddress               | `tenant_group_id`     |                                                                                               |
| JobHook                 | `slug`                |                                                                                               |
| Location                | `tenant_group_id`     |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| Manufacturer            | `slug`                |                                                                                               |
| ObjectPermission        | `user_id`             | instead of `/users/permissions/?user_id=<uuid>`, use `users=<uuid>`                           |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| Platform                | `slug`                |                                                                                               |
| Provider                | `region`              |                                                                                               |
|                         | `slug`                |                                                                                               |
| ProviderNetwork         | `provider_id`         |                                                                                               |
| Platform                | `manufacturer_id`     |                                                                                               |
| PowerOutlet             | `device_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| PowerFeed               | `power_panel_id`      |                                                                                               |
|                         | `rack_id`             |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| PowerPanel              | `rack_group_id`       |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| PowerPort               | `device_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| Prefix                  | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
| Rack                    | `group_id`            |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `role_id`             |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
| RackGroup               | `parent_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| RackReservation         | `group_id`            |                                                                                               |
|                         | `rack_id`             |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
|                         | `user_id`             |                                                                                               |
| RearPort                | `device_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| Region                  | `parent_id`           |                                                                                               |
| RelationshipAssociation | `slug`                |                                                                                               |
| RIR                     | `slug`                |                                                                                               |
| RouteTarget             | `slug`                |                                                                                               |
| RouteTarget             | `tenant_group_id`     |                                                                                               |
| Role                    | `slug`                |                                                                                               |
| Secret                  | `slug`                |                                                                                               |
| SecretsGroup            | `slug`                |                                                                                               |
| SecretsGroupAssociation | `group_id`            | instead of `/extras/secrets-groups-associations/?group_id=<uuid>`, use `secrets_group=<uuid>` |
|                         | `slug`                |                                                                                               |
| Status                  | `slug`                |                                                                                               |
| Site                    | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
| Tenant                  | `aggregates`          |                                                                                               |
|                         | `group_id`            |                                                                                               |
|                         | `has_aggregates`      |                                                                                               |
|                         | `has_sites`           |                                                                                               |
|                         | `sites`               |                                                                                               |
|                         | `slug`                |                                                                                               |
| TenantGroup             | `parent_id`           |                                                                                               |
|                         | `slug`                |                                                                                               |
| VirtualChassis          | `master_id`           |                                                                                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_id`           |                                                                                               |
| VirtualMachine          | `tenant_group_id`     |                                                                                               |
| VLANGroup               | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
| VLAN                    | `group_id`            |                                                                                               |
|                         | `group`               | instead of `/ipam/vlans/?group=<slug>`, use `vlan_group=<slug>`                               |
|                         | `region`              |                                                                                               |
|                         | `region_id`           |                                                                                               |
|                         | `site`                |                                                                                               |
|                         | `site_id`             |                                                                                               |
|                         | `tenant_group_id`     |                                                                                               |
| VMInterface             | `bridge_id`           |                                                                                               |
|                         | `parent_interface_id` |                                                                                               |
| VRF                     | `tenant_group_id`     |                                                                                               |
| Webhook                 | `slug`                |                                                                                               |

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

## Git Data Source Changes

The Configuration Contexts Metadata key `schema` has been replaced with `config_context_schema`. This means that any `schema` references in your git repository's data must be updated to reflect this change.

`GitRepository` sync operations are now Jobs. As a result, when creating a new `GitRepository` it is not automatically synchronized. A `GitRepository.sync()` method has been implemented that will execute the sync job on a worker and return the `JobResult` for the operation. This method takes `dry_run` and `user` arguments. The `dry_run` argument defaults to `False`; if set to `True` will cause the sync to dry-run. The `user` argument is required if a sync is performed.

Additionally, the `GitRepository.save()` method no longer takes a `trigger_resync=<True|False>` argument as it is no longer required. The act of creating a new `GitRepository` no longer has side effects.

Below is a table documenting changes in names for Git-related Jobs. There should NOT be a need to ever manually execute the jobs due to the addition of `GitRepository.sync()`, but this is being provided for clarity.

| Old Job Location                                                       | New Job Location                         |
|------------------------------------------------------------------------|------------------------------------------|
| `nautobot.extras.datasources.git.pull_git_repository_and_refresh_data` | `nautobot.core.jobs.GitRepositorySync`   |
| `nautobot.extras.datasources.git.git_repository_diff_origin_and_local` | `nautobot.core.jobs.GitRepositoryDryRun` |

## Logging Changes

Where applicable, `logging.getLogger("module_name")` is replaced with `logging.getLogger(__name__)` or `logging.getLogger(__name__ + ".MyFeature")`.

Below is a table documenting changes in logger names that could potentially affect existing deployments with expectations around specific logger names used for specific purposes.

| Old Logger Name                          | New Logger Name                                       |
|------------------------------------------|-------------------------------------------------------|
| `nautobot.authentication`                | `nautobot.core.authentication`                        |
| `nautobot.datasources.git`               | `nautobot.extras.datasources.git`                     |
| `nautobot.datasources.utils`             | `nautobot.extras.datasources.utils`                   |
| `nautobot.dcim.cable`                    | `nautobot.dcim.signals.cable`                         |
| `nautobot.graphql.generators`            | `nautobot.core.graphql.generators`                    |
| `nautobot.graphql.schema`                | `nautobot.core.graphql.schema`                        |
| `nautobot.jobs`                          | `nautobot.extras.jobs`                                |
| `nautobot.jobs.*`                        | `nautobot.extras.jobs.*`                              |
| `nautobot.releases`                      | `nautobot.core.releases`                              |
| `nautobot.releases`                      | `nautobot.utilities.tasks`                            |
| `nautobot.plugins`                       | `nautobot.extras.templatetags.plugins`                |
| `nautobot.plugins`                       | `nautobot.extras.plugins.utils`                       |
| `nautobot.views.ObjectEditView`          | `nautobot.core.views.generic.ObjectEditView`          |
| `nautobot.views.ObjectDeleteView`        | `nautobot.core.views.generic.ObjectDeleteView`        |
| `nautobot.views.BulkCreateView`          | `nautobot.core.views.generic.BulkCreateView`          |
| `nautobot.views.ObjectImportView`        | `nautobot.core.views.generic.ObjectImportView`        |
| `nautobot.views.BulkImportView`          | `nautobot.core.views.generic.BulkImportView`          |
| `nautobot.views.BulkEditView`            | `nautobot.core.views.generic.BulkEditView`            |
| `nautobot.views.BulkRenameView`          | `nautobot.core.views.generic.BulkRenameView`          |
| `nautobot.views.BulkDeleteView`          | `nautobot.core.views.generic.BulkDeleteView`          |
| `nautobot.views.ComponentCreateView`     | `nautobot.core.views.generic.ComponentCreateView`     |
| `nautobot.views.BulkComponentCreateView` | `nautobot.core.views.generic.BulkComponentCreateView` |

## Job Database Model Changes

The Job `name` field has been changed to a unique field and the `name` + `grouping` uniqueness constraint has been removed. The processes that refresh jobs (`nautobot-server post_upgrade` and `nautobot-server migrate`) have been updated to gracefully handle duplicate job names.

!!! example
    ```py
    class NautobotJob1(Job):
        class Meta:
            name = "Sample job"

    class NautobotJob2(Job):
        class Meta:
            name = "Sample job"
    ```

    These jobs would be named `Sample job` and `Sample job (2)`

The Job `slug` has been updated to be derived from the `name` field instead of a combination of `job_source`, `git_repository`, and `job_class`.

!!! example
    The Nautobot Golden Config backup job's slug will change from `plugins-nautobot_golden_config-jobs-backupjob` to `backup-configurations`.

## JobResult Database Model Changes

The `JobResult` objects for which results from Job executions are stored are now automatically managed. Therefore job authors must never manipulate or `save()` these objects as they are now used internally for all state transitions and saving the objects yourself could interfere with and cause Job execution to fail or cause data loss.

Therefore all code that is calling `JobResult.set_status()` (which has been removed) or `JobResult.save()` must be removed.
