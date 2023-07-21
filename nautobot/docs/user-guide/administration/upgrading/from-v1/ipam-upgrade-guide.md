# Nautobot 2.0 IPAM Migration Guide

## Goal

This document aims to answer the question “What do I need to do to my data (or what changes with my data) when migrating to 2.0, specifically IPAM?”

## What Changed

This section details the high-level changes as it relates to the data modeling for IPAM objects. Some of the sections are repeating content found in the release notes with detail added for improved readability. Additionally, not all changes described will be distinctly related to IPAM, but if there were changes to relationships to or from IPAM data models, their impact will be described here.

### Namespaces were introduced

The new `Namespace` model expands on the functionality previously provided by `VRF.enforce_unique` and the `ENFORCE_GLOBAL_UNIQUE` setting, both of which have now been removed. Within a Namespace, all VRFs, Prefixes, and IP addresses must be unique. This enables greater flexibility in managing discrete duplicate `Prefix` or `IPAddress` objects, asserting that each set of duplicates will be in a distinct `Namespace`.

For more details please refer to the [documentation](https://docs.nautobot.com/projects/core/en/next/user-guide/core-data-model/ipam/namespace/).

A default `Namespace` object named "Global" wil be created for you. After upgrading, any duplicate objects that were identified will be moved to one or more "Cleanup" Namespaces.

For VRF objects that had `enforce_unique` enabled, any prefixes or child IPAddresses assigned to those Prefixes will be moved to a "VRF Namespace" with the name of the VRF included.

### Aggregate model was merged into Prefix

The `Aggregate` model will be removed and all existing aggregates will be migrated to `Prefix` with type set to `Container`. The `Aggregate.date_added` field will be migrated to `Prefix.date_allocated` and changed from a `Date` field to a `DateTime` field with the time set to `00:00`. The fields `Aggregate.tenant`, `Aggregate.rir`, and `Aggregate.description` will be migrated over to the same fields on `Prefix`.

See the [upgrade guide](https://docs.nautobot.com/projects/core/en/next/user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1/#aggregate-migrated-to-prefix) for more details on the data migration.

### Role model is now Generic across Nautobot

The `DeviceRole`, `RackRole`, `ipam.Role`, and `IPAddressRoleChoices` have all been removed and replaced with a `extras.Role` model, This means that all references to any of the replaced models and choices now points to this generic `Role` model.

In addition, the `role` field of the `IPAddress` model will be changed from a choice field to a foreign key field related to the `extras.Role` model.

### Prefix Parenting Concrete Relationship was added

The `Prefix` model wil be modified to have a self-referencing foreign key as the `parent` field. Parenting of prefixes is now automatically managed at the database level to greatly improve performance especially when calculating tree hierarchy and utilization.

As a result of this change, it is no longer necessary nor possible to disable tree hierarchy using `settings.DISABLE_PREFIX_LIST_HIERARCHY` as this setting has been removed. Additionally it is no longer possible to disable global uniqueness using `settings.ENFORCE_GLOBAL_UNIQUE` as this setting has been removed.

#### Prefix Parenting Guidance

The following guidance has been added for the `Prefix` model in order to ensure more accurate network modeling:

- A `Prefix` of type `Container` should only have a parent (if any) of type `Container`
- A `Prefix` of type `Network` should only have a parent (if any) of type `Container`
- A `Prefix` of type `Pool` should only have a parent (if any) of type `Network`
- Any `Prefix` can be a root prefix (i.e. have no parent)

In Nautobot 2.0, creating or updating prefixes that violate this guidance will result in a warning; in a future Nautobot release this will be changed to an enforced data constraint.

### Prefix.is_pool field and "Container" status replaced by new field Prefix.type

A new type field was added to `Prefix` to replace the `is_poo`l boolean field and the "Container" status. The `type` field can be set to "Network", "Pool" or "Container", with "Network" being the default.

Existing prefixes with a status of "Container" will be migrated to the "Container" `type`. Existing prefixes with `is_pool` set is migrated to the "Pool" `type`. Prefixes with both `is_pool set` and a status of "Container" are migrated to the "Pool" `type`.

The "Container" status will be removed and all prefixes will be migrated to the "Active" status if it exists. If the"Active" status was deleted, prefixes will be migrated to the first available prefix status in the database that is not"Container".

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

| Removed                | Replaced With   |
| ---------------------- | --------------- |
| `get_child_prefixes()` | `descendants()` |

#### IPAddress Parenting Guidance

The following guidance has been added to the `IPAddress` model:

- An `IPAddress` should have a parent `Prefix` of type `Network`
- An `IPAddress` should not be created if a suitable parent `Prefix` of type `Network` does not exist
- An `IPAddress` can be a member of a `Pool` but only if the `Pool` is a child of a `Network`
- If an eligible parent `Prefix` cannot be found for an `IPAddress` in a given `Namespace`, creation or update of that `IPAddress` will fail.
- If deleting a parent `Prefix` would result in any child `IPAddress` objects to become orphaned, the delete opration will fail.

As with the [`Prefix` parenting guidance](#prefix-parenting-guidance) above, violating this guidance in Nautobot 2.0 will result in a warning; in a future Nautobot release this will be changed to an enforced data constraint.

### Parenting affinity during the upgrade

A best effort is made to keep `Prefixes` and `IPAddresses` together by shared attributes such as Tenant, but this is not alway possible for various reasons such as numerous duplicate with identical or too-closely-similar criteria.

When identifying possible ancestors for child `Prefix` or `IPAddress` objects during the reparenting phase of the upgrade process, the following sets of attributes will be compared in order:

- `Tenant` assigned, `VRF` assigned
- `Tenant` null, `VRF` assigned
- `Tenant` assigned, `VRF` null
- `VRF` assigned
- `Tenant` null, `VRF` null
- `VRF` null
- Default ordering

### IPAddress to VRF relationships were changed

- VRF removed; now inherited from parent Prefix
- Constraints for assignment to Interfaces with VRF
    - If the VRF has no Prefixes assigned, IPAddresses may freely be assigned
    - If the VRF has Prefixes assigned, only child IPAddresses of those Prefixes may be assigned

### VRF is no longer used for uniqueness

- The `rd` field must unique to each Namespace
- Relationship from Prefix inverted; now many Prefixes can be assigned to one or more VRF in the same Namespace
- One ore mor Devices now be assigned to a VRF
    - A VRF must be assigned to a Device before it may be assigned to an Interface/VMInterface

### IPAddress to Interface relationship was inverted

> This also applies to `VMInterface` objects

In Nautobot 1.x the relationship from an IPAddress to an Interface was done by way of a foreign key to `Interface` on the `IPAddress` object. This implementation was flawed in that if a need arose to assign the same IP address host value to multiple Interfaces, it required the creation of duplicate `IPAddress` objects with the same `host` address in order to assign each one to a different `Interface`.

As of Nautobot 2.0, this relationships was inverted. Now an `Interface` has a many-to-many relationship to `IPAddresses`. This allows the same `IPAddress` object to be assigned to multiple `Interface` objects without the need to create duplicate `IPAdress` objects.

### VRF is now assigned to Interface/VMInterface, not IPAddress

- A new foreign key to `VRF` has been introduced to `Interface/VMInterface`
    - A`VRF` must be assigned to a `Device` before it may be assigned to an `Interface`
    - A`VRF` must be assigned to a `VirtualMachine` before it may be assigned to an `VMInterface`
- This addresses a fundamental flaw in which an Interface could have multiple IPAddresses assigned with conflicting VRFs, which is impossible in practice.

### Primary IPv4/IPv6 no longer unique

- [#3939](https://github.com/nautobot/nautobot/issues/3939) - Changed `Device.primary_ip4` and `primary_ip6` fields from `OneToOneField`to `ForeignKey`, relaxing the uniqueness constraint.
- [#3939](https://github.com/nautobot/nautobot/issues/3939) - Changed `VirtualMachine.primary_ip4` and `primary_ip6` fields from `OneToOneField` to `ForeignKey`, relaxing the uniqueness constraint.
- Because now same IP used in multiple places requires this.

## Preparing your IPAM Data for Nautobot 2.0

- IPaddress VRF assignments must be unique
- Parents and IPAddresses must share the same Namespace
- IPAddress objects can no longer be orphaned
    - The database migration will automatically create a parent prefix for IPAddresses that do not have an eligible parent. For example 1.2.3.4/32 will have a parent Prefix created of the same network and prefix_length e.g. 1.2.3.4/32.
    - If you do not wish for these single host prefixes to be created, create a parent prefix of your desired size to contain them before upgrading
- You cannot migrate Interfaces or VMInterfaces that have IPs with differing VRFs
    - Make sure for interfaces with multiple IPs that each IP assigned to the same Interface share the same VRF or are not assigned a VRF

## After you Upgrade

This section includes various things to consider after you have successfully upgraded Nautobot.

### Cleanup Namespaces

> This also applies to any "VRF Namespace" objects that were created.

A priority of the upgrade process is to assert that no data will be lost. Due to the introduction of strict uniqueness constraints to disallow duplicate Prefix, IPAddress, and VRF objects within the same Namespace.

- If you need to swap an object into another Namespace (say Global and Cleanup Namespace 1)
    - Create a third "Temporary" namespace
    - Move objects from Global to Temporary
    - Move objects from Cleanup Namespace 1 to Global
    - Move objects from Temporary to Cleanup Namespace 1
    - Delete Temporary
- Tenant affinity
    - A best effort is made to keep Prefixes and IPAddresses together by shared attributes such as tenant, but this is not alway possible for various reasons such as numerous duplicate with identical or too-closely-similar criteria.

### Delete duplicate objects

- No data loss is prioritized, therefore some objects that may have been duplicates before, may no longer be needed. Some examples include:
    - The same IP assigned to multple interfaces. Where possible, a single IP is now assigned
    - VRFs that were used strictly for custom uniqueness boundaries

### Cleanup your config

Remove:

- `DISABLE_PREFIX_LIST_HIERARCHY`
- `ENFORCE_GLOBAL_UNIQUE`
