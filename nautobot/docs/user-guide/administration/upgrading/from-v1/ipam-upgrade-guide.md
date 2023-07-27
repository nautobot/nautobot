# Nautobot 2.0 IPAM Migration Guide

## Goal

This document aims to answer the question "What do I need to do to my data (or what changes with my data) when migrating to 2.0, specifically IPAM?"

## What Changed

This section details the high-level changes as it relates to the data modeling for IPAM objects. Some of the sections are repeating content found in the release notes with detail added for improved readability. Additionally, not all changes described will be distinctly related to IPAM, but if there were changes to relationships to or from IPAM data models, the impact of those changes will be described here.

### Namespaces were introduced

The new `Namespace` model expands on the functionality previously provided by `VRF.enforce_unique` and the `ENFORCE_GLOBAL_UNIQUE` setting, both of which have now been removed. Within a Namespace, all VRFs, Prefixes, and IP addresses must be unique. This enables greater flexibility in managing discrete duplicate `VRF`, `Prefix` or `IPAddress` objects, asserting that each set of duplicates will be in a distinct `Namespace`.

For more details please refer to the [Namespace model documentation](../../../core-data-model/ipam/namespace.md).

### Default Namespace

A default `Namespace` object named "Global" will be created for you. All objects that did not have duplicates found will be found in this Namespace. All new objects will default to this Namespace unless otherwise specified.

#### Cleanup Namespaces

After upgrading, any duplicate objects that were found in the "Global" Namespace will be moved to one or more "Cleanup" Namespaces. Cleanup Namespaces are named numerically. When duplicate objects are identified that are not associated with a VRF that has `enforce_unique` set to `True`, each Cleanup Namespace will be enumerated until one that does not have conflicting objects can be found. If one cannot be found, a new Cleanup Namespace will be created.

For example, the very first duplicate `Prefix` found will be moved to a Namespace named "Cleanup Namespace 1". For each pass that identifies a duplicate of an object in an existing Namespace, new Namespaces will be created by incrementing the number resulting in "Cleanup Namespace 2", "Cleanup Namespace 3", etc.

#### VRF Namespaces

For `VRF` objects that had `enforce_unique` enabled with `Prefixes` assigned to them, any child `Prefixes` or child `IPAddresses` of those `Prefixes` will be moved to a "VRF Namespace" with the name of the `VRF` included.

For example, if the `VRF` is named "Blue" and has `Prefixes` assigned to it, the `VRF`, all `Prefixes` assigned to it, and any child `Prefixes` or `IPAddresses` will be moved to a new `Namespace` with the name "VRF Namespace Blue".

### Aggregate model was merged into Prefix

The `Aggregate` model was removed and all existing aggregates will be migrated to `Prefix` with type set to `Container`. The `Aggregate.date_added` field will be migrated to `Prefix.date_allocated` and changed from a `Date` field to a `DateTime` field with the time set to `00:00`. The fields `Aggregate.tenant`, `Aggregate.rir`, and `Aggregate.description` will be migrated over to the same fields on `Prefix`.

See the [upgrade guide](./upgrading-from-nautobot-v1.md#aggregate-migrated-to-prefix) for more details on the data migration.

### Role model is now Generic across Nautobot

The `DeviceRole`, `RackRole`, `ipam.Role`, and `IPAddressRoleChoices` have all been removed and replaced with an `extras.Role` model. This means that all references to any of the replaced models and choices now points to this generic `Role` model.

In addition, the `role` field of the `IPAddress` model will be changed from a choice field to a foreign key field related to the `extras.Role` model.

For more details please refer to the [documention on Roles](../../../platform-functionality/role.md).

### Prefix Parenting Concrete Relationship was added

The `Prefix` model was modified to have a self-referencing foreign key as the `parent` field. Parenting of prefixes is now automatically managed at the database level to greatly improve performance especially when calculating tree hierarchy and utilization.

As a result of this change, it is no longer necessary nor possible to disable tree hierarchy using `settings.DISABLE_PREFIX_LIST_HIERARCHY` as this setting has been removed. Additionally it is no longer possible to disable global uniqueness using `settings.ENFORCE_GLOBAL_UNIQUE` as this setting has been removed.

#### Prefix Parenting Guidance

The following guidance has been added for the `Prefix` model in order to ensure more accurate network modeling:

- A `Prefix` of type `Container` should only have a parent (if any) of type `Container`
- A `Prefix` of type `Network` should only have a parent (if any) of type `Container`
- A `Prefix` of type `Pool` should only have a parent (if any) of type `Network`
- Any `Prefix` can be a root prefix (i.e. have no parent)

In Nautobot 2.0, creating or updating prefixes that violate this guidance will result in a warning; in a future Nautobot release this will be changed to an enforced data constraint.

### Prefix.is_pool field and "Container" status replaced by new field Prefix.type

A new type field was added to `Prefix` to replace the `is_pool` boolean field and the "Container" `status`. The `type` field can be set to "Network", "Pool" or "Container", with "Network" being the default.

Existing `Prefixes` with a `status` of "Container" will be migrated to the "Container" `type`. Existing prefixes with `is_pool` set are migrated to the "Pool" `type`. Prefixes with both `is_pool set` and a `status` of "Container" are migrated to the "Pool" `type`.

The "Container" `status` will be removed and all prefixes will be migrated to the "Active" `status` if it exists. If the "Active" `status` does not exist, prefixes will instead be migrated to the first available `Prefix` `status` in the database that is not "Container".

### Prefix utilization calculations were revamped

The `get_utilization` method on the `ipam.Prefix` model has been updated in 2.0 to account for the `Prefix.type` field as described above under **Prefix Parenting Guidance**. The behavior is now as follows:

- If the `Prefix.type` is `Container`, the utilization is calculated as the sum of the total address space of all child prefixes.
- If the `Prefix.type` is `Pool`, the utilization is calculated as the sum of the total number of IP addresses within the pool's range.
- If the `Prefix.type` is `Network`:
    - The utilization is calculated as the sum of the total address space of all child `Pool` prefixes plus the total number of child IP addresses.
    - For IPv4 networks with a `prefix_length` larger (lower) than `/31`, if neither the first or last address is occupied by either a pool or an IP address, they are subtracted from the total size of the prefix.

#### Example

- 192.168.0.0/16          `Container - 1024/65536 utilization`
    - 192.168.1.0/24      `Network - 1/254 utilization`
        - 192.168.1.1     `IP Address`
    - 192.168.2.0/24      `Network - 4/256 utilization`
        - 192.168.2.0/30  `Pool - 1/4 utilization`
            - 192.168.2.1 `IP Address`
    - 192.168.3.0/24      `Network - 5/254 utilization`
        - 192.168.3.1     `IP Address`
        - 192.168.3.64/30 `Pool - 0/4 utilization`
    - 192.168.4.0/24      `Network - 1/256 utilization`
        - 192.168.4.255   `IP Address`

### IPAddress Parenting Concrete Relationship was added

The `ipam.IPAddress` model has been modified to have a mandatory foreign key to `ipam.Prefix` as the `parent` field. Parenting of IP addresses is now automatically managed at the database level to greatly improve performance especially when calculating tree hierarchy and utilization.

#### IPAddress Parenting Guidance

The following guidance has been added to the `IPAddress` model:

- An `IPAddress` should have a parent `Prefix` of type `Network`
- An `IPAddress` should not be created if a suitable parent `Prefix` of type `Network` does not exist
- An `IPAddress` can be a member of a `Pool` but only if the `Pool` is a child of a `Network`
- If an eligible parent `Prefix` cannot be found for an `IPAddress` in a given `Namespace`, creation or update of that `IPAddress` will fail.
- If deleting a parent `Prefix` would result in any child `IPAddress` objects to become orphaned, the delete operation will fail.

As with the [`Prefix` parenting guidance](#prefix-parenting-guidance) above, violating this guidance in Nautobot 2.0 will result in a warning; in a future Nautobot release this will be changed to an enforced data constraint.

### Parenting affinity during the upgrade

A best effort is made to keep `Prefixes` and `IPAddresses` together by shared attributes such as `Tenant`, but this is not always possible for various reasons such as numerous duplicates with identical or too-closely-similar criteria.

When identifying possible ancestors for child `Prefix` or `IPAddress` objects during the reparenting phase of the upgrade process, the following sets of attributes will be compared in order:

- `Tenant` assigned, `VRF` assigned
- `Tenant` null, `VRF` assigned
- `Tenant` assigned, `VRF` null
- `VRF` assigned
- `Tenant` null, `VRF` null
- `VRF` null
- Default ordering

### IPAddress to VRF relationships were changed

The foreign key relationship from `IPAddress` to `VRF` was removed. `IPAddress` objects may no longer have a `VRF` assigned to them. The `VRF` value for an `IPAddress` is now inherited from its parent `Prefix`.

Additionally, some new constraints have been put into place to alleviate issues that existed previously which allowed an Interface to have multiple `IPAddress` assignments each with differing VRFs, which is not technically possible in real-world networking configurations.

The `Interface`/`VMInterface` assignment constraints are as follows:

- If the `VRF` has no `Prefixes` assigned, `IPAddresses` may freely be assigned to the `Interface`/`VMInterface`
- If the `VRF` has `Prefixes` assigned, only child `IPAddresses` of those `Prefixes` may be assigned to the `Interface`/`VMInterface`

### IPAddress prefix_length is now mask_length

The `prefix_length` field on `IPAddress` has been renamed to `mask_length`. This is to enforce that this field is used for documentation purposes only to indicate the mask length that may be used in practice when configuring this address for use on your network.

The `mask_length` field is not used for the parenting algorithm when determining the appropriate parent `Prefix` within a given `Namespace`.

### VRF is no longer used for uniqueness

`VRF` objects can no longer be used for uniqueness boundaries and the `enforce_unique` field has been removed. A new uniqueness constraint has been added to the `VRF` `rd` field, which requires it to be unique for each `Namespace`.

The foreign key relationship from `Prefix` to `VRF` has been inverted and replaced with a many-to-many relationship from `VRF` to `Prefix`. Now each `Prefix` can be assigned to one or more `VRF` object in the same `Namespace`.

Lastly, one or more `Device`/`VirtualMachine` objects can now be assigned to a `VRF`. A `VRF` must be assigned to a `Device`/`VirtualMachine` before it may be assigned to an `Interface`/`VMInterface`. This is the modeling equivalent of creating a `VRF` in the device configuration before it may be used on an interface.

### IPAddress to Interface relationship was inverted

In Nautobot 1.x the relationship from an `IPAddress` to an `Interface`/`VMInterface` was done by way of a foreign key to `Interface`/`VMInterface` on the `IPAddress` object. This implementation was flawed in that if a need arose to assign the same IP address to multiple interfaces, it required the creation of duplicate `IPAddress` objects with the same `host` address in order to assign each one to a different `Interface`/`VMInterface`.

As of Nautobot 2.0, this relationship was inverted. Now an `Interface`/`VMInterface` has a many-to-many relationship to `IPAddresses`. This allows the same `IPAddress` object to be assigned to multiple `Interface`/`VMInterface` objects without the need to create duplicate `IPAddress` objects.

### VRF is now assigned to Interface/VMInterface, not IPAddress

A new foreign key to `VRF` has been introduced to `Interface/VMInterface`.

- A `VRF` must be assigned to a `Device` before it may be assigned to an `Interface`
- A `VRF` must be assigned to a `VirtualMachine` before it may be assigned to an `VMInterface`

This addresses a fundamental flaw in which an Interface could have multiple `IPAddress` objects assigned with conflicting `VRFs`, which is impossible in practice when applied to a network device configuration.

### Primary IPv4/IPv6 no longer unique

On `Device` and `VirtualMachine` objects, the `primary_ip4` and `primary_ip6` fields were changed from a one-to-one field--which is a foreign key with a uniqueness constraint--to a foreign key, dropping the uniqueness constraint.

This was necessary to support the case where the same `IPAddress` object may be assigned to one or more `Interface`/`VMInterface` objects to share a (non-duplicated) primary `IPAddress` record, reducing the need to proliferate duplicate `IPAddress` objects merely for the purpose of facilitating `Interface`/`VMInterface` assignments.

## Preparing your IPAM Data for Nautobot 2.0

### Run the pre-migration helper before upgrading

A new pre-migration management command was added that will allow you to check your existing data for compatibility with the data model changes introduced in Nautobot 2.0. You are highly encouraged to run this before upgrading!

For more information please see the [documentation on Pre-migration validation](./upgrading-from-nautobot-v1.md##pre-migration-validation).

### You cannot migrate Interfaces or VMInterfaces that have IPs with differing VRFs

When assigning a `VRF` to an`IPaddress`, the `VRF` must be the same across each IP when multiple `IPAddress` objects are assigned to `Interface`/`VMInterface` objects.

Make sure for `Interfaces`/`VMInterfaces` with multiple IPs that each `IPAddress`1 assigned to the same `Interface`/`VMInterface` share the same VRF, or are not assigned a VRF.

### Parent Prefixes, child Prefixes, and child IPAddresses must share the same Namespace

Parent `Prefixes`, child `Prefixes`, and `IPAddresses` must share the same `Namespace` and any case for duplicate `Prefix`/`IPAddress` must involve leveraging distinct `Namespace` objects.

If you need to maintain duplicates for any reason, assert that each set of duplicate objects are assigned to a distinct `VRF` with `enforce_unique` set to `True`, as during the upgrade process these will each be moved to their own "VRF Namespace" (Please see the section on **VRF Namespaces** above).

### IPAddress objects can no longer be orphaned

`IPAddresses` must now always have a parent `Prefix` to contain them. Any `IPAddress` that does not have a parent is considered to be "orphaned" and as of Natutobot 2.0 this is not allowed.

When upgrading to Nautobot 2.0, the database migration will automatically create a parent `Prefix` for `IPAddresses` that do not have an eligible parent `Prefix`. For example an `IPAddress` with address of `1.2.3.4/32` will have a parent `Prefix` created of the same `network` and `prefix_length` e.g. `1.2.3.4/32`.

If you do not wish for these single-host `Prefixes` to be created, create a parent `Prefix` of your desired size to contain any would-be orphaned `IPAddresses` before upgrading.

## After you Upgrade

This section includes various things to consider after you have successfully upgraded Nautobot.

### Review any Cleanup Namespaces

> This may also apply to any "VRF Namespace" objects that were created, depending on your requirements on maintaining duplicate Prefix/IPAddress objects.

A priority of the upgrade process is to assert that no data will be lost. Due to the introduction of strict uniqueness constraints to disallow duplicate `Prefix`, `IPAddress`, and `VRF` objects within the same `Namespace`.

#### A word on Tenant affinity

A best effort is made to keep `Prefixes` and `IPAddresses` together in the same `Namespace` by shared attributes such as `Tenant`, but this is not always possible for various reasons such as numerous duplicates with identical or too-closely-similar criteria.

For more information on how this is done please see the section **Parenting affinity during the upgrade** above.

If you find that you have objects that were moved to the wrong Namespaces, you might try the next section on swapping Namespaces.

#### Swapping Namespaces

If you need to swap a duplicate object into another `Namespace` (say "Global" and "Cleanup Namespace 1") where it conflicts with one in the desired `Namespace`, you can use this basic strategy to facilitate moving duplicate objects between `Namespaces` by using a temporary interstitial `Namespace`.

In this example we'll use three `Namespaces`. "Global", the `Namespace` in which you have duplicate objects that are found in "Cleanup Namespace 1", but you would like them to be the "Global" Namespace. We'll create a third Namespace called "Temporary" to act as the go-between to temporarily hold objects from one `Namespace` that we want to swap into another.

- First, Create a new  Namespace named "Temporary"
- Next, edit any desired objects you want to swap in objects from the "Global" Namespace and update their Namespace to "Temporary"
    - After performing this step, there should be no duplicates found in the "Global" Namespace
- Next, edit the duplicate objects you want moved in from "Cleanup Namespace 1" and set their Namespace to "Global".
    - After performing this step there should be no duplicates found in the "Cleanup Namespace 1" Namespace, as they've been moved to "Global"
- Finally, edit the original objects found in the "Temporary" Namespace that were moved from "Global" to "Temporary" and set their Namespace "Cleanup Namespace 1"
    - After performing this final step, the duplicate objects that were originally in the "Global" have now been swapped with those that were originally in the "Cleanup Namespace 1" Namespace.
    - There are no duplicate objects found in the "Temporary" Namespace. This Namespace can safely be deleted.
- Delete the "Temporary" Namespace when done.

### Merge duplicate IP Addresses

After upgrading to Nautobot v2.0 and running the data migrations necessary, duplicate `IPAddress` objects might exist in your database. We define duplicate `IPAddress` objects as those which have the same `host` attribute but exist in different `Namespaces`. If you have no use case to keep those duplicate `IPAddress` objects around, we recommend you to use this tool to de-duplicate those `IPAddress` objects and keep your database clean and manageable. But if you do have reasons to maintain duplicate `IPAddress` objects, this tool is not for you.

For more information, please see the [documentation on the Duplicate IP Address Merge Tool](../../../feature-guides/ip-address-merge-tool.md).

### Delete duplicate objects

Because preventing data loss is prioritized, some objects that may have been required to be duplicates before may no longer be needed. For objects that weren't covered by the Duplicate IP Address Merge Tool, deleting objects might be your next course of action.

Some examples include:

- The same `IPAddress` assigned to multiple `Interfaces/VMInterfaces`. Where possible, a single `IPAddress` is now assigned leaving duplicate objects across other Namespaces to be potentially no longer necessary.
- `VRFs` that were used strictly for custom uniqueness boundaries with `enforce_unique` set to `True` may not necessarily be needed.

### Cleanup your config

Remove the now-deprecated settings from your `nautobot_config.py`:

- `DISABLE_PREFIX_LIST_HIERARCHY`
- `ENFORCE_GLOBAL_UNIQUE`

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
2. Removal of `slug` fields in preference to the use of autogenerated composite keys.

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
2. Renaming of tree model fields for consistency and due to the change from `django-mptt` to `django-tree-queries` (for example, `InventoryItem._depth` to `InventoryItem.tree_depth`)

| Model     | Renamed Field | New Name   |
| :-------- | :------------ | :--------- |
| IPAddress | family        | ip_version |
| Prefix    | family        | ip_version |
| VLAN      | group         | vlan_group |

### Removed Serializer Fields

Most removed database fields in Nautobot 2.0 fall into the following general categories:

1. Removal of references to removed models such as `Site` and `Region`
2. Removal of `slug` fields in preference to the use of autogenerated composite keys.

| Model/Endpoint | Removed Field   | Comments                                                     |
| :------------- | :-------------- | :----------------------------------------------------------- |
| IPAddress      | assigned_object | Use `interfaces` and/or `vm_interfaces` instead.             |
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
4. Most `<related>_id` filters have been merged into the corresponding `<related>` filter (see ["Enhanced Filter Fields"](https://docs.nautobot.com/projects/core/en/next/user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1/#enhanced-filter-fields) below).

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

Below is a table documenting [enhanced filter field changes](https://docs.nautobot.com/projects/core/en/next/release-notes/version-2.0/#enhanced-filter-fields-2804) in Nautobot 2.0. These enhancements mostly fall into the following general categories:

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

Below is a table documenting [corrected filter field changes](https://docs.nautobot.com/projects/core/en/next/release-notes/version-2.0/#corrected-filter-fields-2804) in Nautobot 2.0. These corrections mostly involve filters that previously permitted filtering on related membership only (`/api/dcim/devices/?console_ports=True`) and have now been corrected into filters for related membership (`/api/dcim/devices/?has_console_ports=True`) as well as by actual related objects (`/api/dcim/devices/?console_ports=<UUID>`).

| Model     | Filter | Correction                                                   |
| :-------- | :----- | :----------------------------------------------------------- |
| IPAddress | parent | The `parent` filter now checks for an exact match of the parent Prefix; for legacy `net_host_contained` behavior now use the new `prefix` filter instead |

### Removed Filter Fields

Below is a table documenting [removed filter field changes](https://docs.nautobot.com/projects/core/en/next/release-notes/version-2.0/#removed-filter-fields-2804) in v2.x. Most removed database fields in Nautobot 2.0 fall into the following general categories:

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
