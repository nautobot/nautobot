# For Developers

This section covers technical changes to the underlying data models and programmable interfaces and is intended for developers or integrators to help facilitate any necessary changes to functional code in Apps/plugins that extend Nautobot.

## Database (ORM) Changes

### Database Field Behavior Changes

| Model     | Field           | Changes                                                      |
| :-------- | :-------------- | :----------------------------------------------------------- |
| IPAddress | role            | Changed from `CharField` to a `ForeignKey` to the new `Role` model. |
| IPAddress | primary_ip4_for | Now a list as the reverse relation for the `Device.primary_ip4` foreign key |
| IPAddress | primary_ip6_for | Now a list as the reverse relation for the `Device.primary_ip6` foreign key |
| Prefix    | is_pool         | Replaced by new field `type`, valid choices are "Container", "Network" and "Pool" |
| Prefix    | namespace       | New required foreign key to Namespace, defaulting to 'Global' |
| Prefix    | status          | "Container" status has been replaced by new field `type`     |
| VRF       | namespace       | New required foreign key to Namespace, defaulting to 'Global' |

### Renamed Database Fields

Most renamed database fields in Nautobot 2.0 fall into the following general categories:

1. Renaming of foreign keys and reverse relations to more consistently and specifically match the related model name or plural name (for example, `Circuit.terminations` to `Circuit.circuit_terminations`, `Rack.group` to `Rack.rack_group`)
2. Explicitly for the `IPAddress` and `Prefix` models, `family`, a derived field, was replaced with `ip_version`, a concrete integer field that may be used in query filters.

| Model     | Renamed Field | New Name     |
| :-------- | :------------ | :----------- |
| IPAddress | family        | ip_version   |
| IPAddress | prefix_length | mask_length  |
| Prefix    | family        | ip_version   |
| Service   | ipaddresses   | ip_addresses |
| VLAN      | group         | vlan_group   |

### Removed Database Fields

Most removed database fields in Nautobot 2.0 fall into the following general categories:

1. Removal of references to removed models such as `Site` and `Region`
2. Removal of `slug` fields in preference to the use of the natural key.

| Model       | Removed Field   | Comments                                                     |
| :---------- | :-------------- | :----------------------------------------------------------- |
| IPAddress   | assigned_object | Replaced by `interfaces` and `vm_interfaces` many-to-many relations |
| IPAddress   | broadcast       | Use parent Prefix's broadcast instead                        |
| IPAddress   | vrf             | VRF is now related to the assigned Interface(s), as well as the parent Prefix |
| Prefix      | is_pool         | Replaced by new `type` field                                 |
| Prefix      | site            | Use `location` instead                                       |
| Prefix      | vrf             | Replaced by `vrf_assignments` many-to-many relation          |
| RouteTarget | slug            |                                                              |
| VLAN        | site            | Use `location` instead                                       |
| VLANGroup   | site            | Use `location` instead                                       |
| VLANGroup   | slug            |                                                              |
| VRF         | enforce_unique  | Uniqueness of Prefixes and IPAddresses is now enforced by the database |

### Replaced Models

The `ipam.Role`  model has been removed and replaced by a single `extras.Role` model. This means that any references to the removed models in the code now use the `extras.Role` model instead.

| Removed Model | Replaced With |
| :------------ | :------------ |
| `ipam.Role`   | `extras.Role` |

## GraphQL and REST API Changes Changes

### API Behavior changes

Most of the API behavior changes in Nautobot 2.0 fall into the following general categories:

1. The `created` field on most models has changed from a date only ("2023-04-06") to being a date/time ("2023-04-06T19:57:45.320232Z")
2. The `status` fields on various models has changed from a pseudo-enum value (containing a "value" and a "label") to referencing the related Status object in full, similar to other foreign-key fields.
3. Various models that had a required `site` field and an optional `location` field now have a required `location` field.

| Model     | Field     | Changes                                                      |
| :-------- | :-------- | :----------------------------------------------------------- |
| IPAddress | parent    | A new foreign-key to `Prefix`. Required on creation, if `namespace` isn't provided, to find a correct parent Prefix |
| IPAddress | role      | Now is a foreign-key to `Role` rather than a string          |
| IPAddress | status    | Now is a foreign-key rather than a pseudo-enum               |
| Prefix    | namespace | New required foreign key to Namespace, defaulting to 'Global' |
| Prefix    | status    | Now is a foreign-key rather than a pseudo-enum               |
| VLAN      | status    | Now is a foreign-key rather than a pseudo-enum               |
| VRF       | namespace | New required foreign key to Namespace, defaulting to 'Global' |

### Renamed Serializer Fields

Most renamed API fields in Nautobot 2.0 fall into the following general categories:

1. Renaming of foreign keys and reverse relations to more consistently and specifically match the related model name or plural name (for example, `Circuit.type` to `Circuit.circuit_type`, `Interface.count_ipaddresses` to `Interface.ip_address_count`)

| Model     | Renamed Field | New Name   |
| :-------- | :------------ | :--------- |
| IPAddress | family        | ip_version |
| Prefix    | family        | ip_version |
| VLAN      | group         | vlan_group |

### Removed Serializer Fields

Most removed database fields in Nautobot 2.0 fall into the following general categories:

1. Removal of references to removed models such as `Site` and `Region`
2. Removal of `slug` fields in preference to the use of the natural key.

| Model/Endpoint | Removed Field   | Comments                                                     |
| :------------- | :-------------- | :----------------------------------------------------------- |
| IPAddress      | assigned_object | Changed to many-to-many field. Use the REST API view for `IPAddressToInterface`(/api/ipam/ip-address-to-interface/) to create/modify/delete associations or `interfaces`/`vm_interfaces` on this model to retrieve a list of associated interfaces. |
| IPAddress      | broadcast       | Use parent Prefix's broadcast instead                        |
| IPAddress      | vrf             | VRF is now related to the assigned Interface(s), as well as the parent Prefix |
| Prefix         | is_pool         | Use `type` instead                                           |
| Prefix         | vrf             | Prefixes are now assigned to a VRF in the same Namespace via a many-to-many relationship |
| Prefix         | site            | Use `location` instead                                       |
| RouteTarget    | slug            |                                                              |
| VLAN           | site            | Use `location` instead                                       |
| VLANGroup      | site            | Use `location` instead                                       |
| VLANGroup      | slug            |                                                              |
| VRF            | enforce_unique  | Uniqueness of Prefixes and IPAddresses is now enforced at the database level |

### Replaced Endpoints

The endpoint `/ipam/roles/` is no longer available. Instead, use the `/extras/roles/` endpoint to retrieve and manipulate `role` data.

| Removed Endpoints | Replaced With    |
| :---------------- | :--------------- |
| `/ipam/roles/`    | `/extras/roles/` |

## UI, GraphQL, and REST API Filter Changes

### Renamed Filter Fields

Most renamed filter fields in Nautobot 2.0 fall into the following general categories:

1. The `tag` filter is renamed to `tags` on all models supporting Tags.
2. Renames to match renamed model/serializer fields as described earlier in this document.
3. Related membership filters are renamed to `has_<related>` throughout, for example `ConsolePort.cabled` is renamed to `ConsolePort.has_cable`.
4. Most `<related>_id` filters have been merged into the corresponding `<related>` filter (see ["Enhanced Filter Fields"](#enhanced-filter-fields) below).

| Model       | Renamed Filter        | New Name                  | Renamed Field |
| :---------- | :-------------------- | :------------------------ | :------------ |
| IPAddress   | assigned_to_interface | has_interface_assignments |               |
| IPAddress   | family                | ip_version                |               |
| IPAddress   | parent                | prefix                    |               |
| IPAddress   | tag                   | tags                      |               |
| Prefix      | family                | ip_versionip_version      |               |
| Prefix      | is_pool               | type                      |               |
| Prefix      | tag                   | tags                      |               |
| RouteTarget | tag                   | tags                      |               |
| Service     | tag                   | tags                      |               |
| VLAN        | group                 | vlan_group                |               |
| VLAN        | tag                   | tags                      |               |
| VRF         | tag                   | tags                      |               |

### Enhanced Filter Fields

Below is a table documenting [enhanced filter field changes](../../../../../release-notes/version-2.0.md#enhanced-filter-fields-2804) in Nautobot 2.0. These enhancements mostly fall into the following general categories:

1. Many filters are enhanced to permit filtering by UUID *or* by name.
2. Filters that previously only supported a single filter value can now filter on multiple values.

| Model       | Filter              | Enhancements                         |
| :---------- | :------------------ | :----------------------------------- |
| IPAddress   | mask_length         | Filtering on multiple integer values |
| IPAddress   | rir                 | Filter by UUID or by name            |
| IPAddress   | tenant              | Filter by UUID or by name            |
| IPAddress   | tenant_group        | Filter by UUID or by name            |
| Prefix      | rir                 | Filter by UUID or by name            |
| Prefix      | tenant              | Filter by UUID or by name            |
| Prefix      | tenant_group        | Filter by UUID or by name            |
| RouteTarget | tenant              | Filter by UUID or by name            |
| RouteTarget | tenant_group        | Filter by UUID or by name            |
| VLAN        | available_on_device | Filtering on multiple values         |
| VLAN        | tenant              | Filter by UUID or by name            |
| VLAN        | tenant_group        | Filter by UUID or by name            |
| VLAN        | vlan_group          | Filter by UUID or by name            |
| VRF         | tenant              | Filter by UUID or by name            |
| VRF         | tenant_group        | Filter by UUID or by name            |

### Corrected Filter Fields

Below is a table documenting [corrected filter field changes](../../../../../release-notes/version-2.0.md#corrected-filter-fields-2804) in Nautobot 2.0. These corrections mostly involve filters that previously permitted filtering on related membership only (`/api/dcim/devices/?console_ports=True`) and have now been corrected into filters for related membership (`/api/dcim/devices/?has_console_ports=True`) as well as by actual related objects (`/api/dcim/devices/?console_ports=<UUID>`).

| Model     | Filter | Correction                                                   |
| :-------- | :----- | :----------------------------------------------------------- |
| IPAddress | parent | The `parent` filter now checks for an exact match of the parent Prefix; for legacy `net_host_contained` behavior now use the new `prefix` filter instead |

### Removed Filter Fields

Below is a table documenting [removed filter field changes](../../../../../release-notes/version-2.0.md#removed-redundant-filter-fields-2804) in v2.x. Most removed database fields in Nautobot 2.0 fall into the following general categories:

1. Removal of `*_id=<uuid>` filters as they have have been merged into filters that support both uuid and name/slug (for example, instead of `/api/circuits/circuits/?provider_id=<UUID>`, use `/api/circuits/circuits/?provider=<uuid>`).
2. Removal of filtering on removed models such as `Region` and `Site`. (Use `location` filters instead.)
3. Removal of `slug` filters from models that no longer have a `slug` field.

| Model       | Removed Filter  | Comments                |
| :---------- | :-------------- | :---------------------- |
| Prefix      | region          |                         |
| Prefix      | region_id       |                         |
| Prefix      | site            |                         |
| Prefix      | site_id         |                         |
| Prefix      | vrf_id          | Use vrf filter instead  |
| RouteTarget | slug            |                         |
| RouteTarget | tenant_group_id |                         |
| VLAN        | group_id        | Use `vlan_group` filter |
| VLAN        | region          |                         |
| VLAN        | region_id       |                         |
| VLAN        | site            |                         |
| VLAN        | site_id         |                         |
| VLAN        | tenant_group_id |                         |
| VLANGroup   | region          |                         |
| VLANGroup   | region_id       |                         |
| VLANGroup   | site            |                         |
| VLANGroup   | site_id         |                         |
| VLANGroup   | slug            |                         |
| VRF         | tenant_group_id |                         |
