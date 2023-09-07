# Before you Upgrade

This section covers how you can prepare your IPAM Data for Nautobot 2.0.

## Run the pre-migration helper before upgrading

A new pre-migration management command was added that will allow you to check your existing data for compatibility with the data model changes introduced in Nautobot 2.0. You are highly encouraged to run this before upgrading!

For more information please see the [documentation on Pre-migration validation](../upgrading-from-nautobot-v1.md#pre-migration-validation).

## You cannot migrate Interfaces or VMInterfaces that have IPs with differing VRFs

When assigning a `VRF` to an`IPaddress`, the `VRF` must be the same across each IP when multiple `IPAddress` objects are assigned to `Interface`/`VMInterface` objects.

Make sure for `Interfaces`/`VMInterfaces` with multiple IPs that each `IPAddress`1 assigned to the same `Interface`/`VMInterface` share the same VRF, or are not assigned a VRF.

## Parent Prefixes, child Prefixes, and child IPAddresses must share the same Namespace

Parent `Prefixes`, child `Prefixes`, and `IPAddresses` must share the same `Namespace` and any case for duplicate `Prefix`/`IPAddress` must involve leveraging distinct `Namespace` objects.

If you need to maintain duplicates for any reason, assert that each set of duplicate objects are assigned to a distinct `VRF` with `enforce_unique` set to `True`, as during the upgrade process these will each be moved to their own "VRF Namespace". Please see the section on [VRF Namespaces](#vrf-namespaces) below for more information.

## IPAddress objects can no longer be orphaned

`IPAddresses` must now always have a parent `Prefix` to contain them. Any `IPAddress` that does not have a parent is considered to be "orphaned" and as of Natutobot 2.0 this is not allowed.

When upgrading to Nautobot 2.0, the database migration will automatically create a parent `Prefix` for `IPAddresses` that do not have an eligible parent `Prefix`. For example an `IPAddress` with address of `1.2.3.4/32` will have a parent `Prefix` created of the same `network` and `prefix_length` e.g. `1.2.3.4/32`.

If you do not wish for these single-host `Prefixes` to be created, create a parent `Prefix` of your desired size to contain any would-be orphaned `IPAddresses` before upgrading.

## Prepare for Namespaces

After upgrading, there will be two distinct sets of extra `Namespace` objects created based on specific conditions of your data set.

First, any `VRF` objects with `enforce_unique` enabled (which is the default), will be moved to "VRF Namespace" objects. Second, any duplicate objects will be moved to "Cleanup Namespace" objects.

Each of these are covered below.

### Cleanup Namespaces

After upgrading, any duplicate objects that were found in the "Global" Namespace will be moved to one or more "Cleanup" Namespaces. Cleanup Namespaces are named numerically. When duplicate objects are identified that are not associated with a VRF that has `enforce_unique` set to `True`, each Cleanup Namespace will be enumerated until one that does not have conflicting objects can be found. If one cannot be found, a new Cleanup Namespace will be created.

For example, the very first duplicate `Prefix` found will be moved to a Namespace named "Cleanup Namespace 1". For each pass that identifies a duplicate of an object in an existing Namespace, new Namespaces will be created by incrementing the number resulting in "Cleanup Namespace 2", "Cleanup Namespace 3", etc.

Because Cleanup Namespaces will be created to avoid data loss, there is little you can do to avoid their creation during the upgrade process. You may want to review your Cleanup Namespaces or swap objects around between other Namespaces.

Please [review any Cleanup Namespaces](./after-you-upgrade.md#review-any-cleanup-or-vrf-namespaces) after you upgrade.

### VRF Namespaces

For `VRF` objects that had `enforce_unique` enabled with `Prefixes` assigned to them, any child `Prefixes` or child `IPAddresses` of those `Prefixes` will be moved to a "VRF Namespace" with the name of the `VRF` included.

For example, if the `VRF` is named "Blue" and has `Prefixes` assigned to it, the `VRF`, all `Prefixes` assigned to it, and any child `Prefixes` or `IPAddresses` will be moved to a new `Namespace` with the name "VRF Namespace Blue".

If you wish to reduce the need for creation of VRF Namespaces, review your existing `VRF` objects with `enforce_unique` enabled to identify their relevance. If you do not require enforcing uniqueness in the VRF itself, you may toggle `enforce_unique` to tell Nautobot to handle any potential duplicates globally instead, which may result in duplicate objects being moved to Cleanup Namespaces that will need to be reviewed following the upgrade process.

Please [review any Cleanup or VRF Namespaces](./after-you-upgrade.md#review-any-cleanup-or-vrf-namespaces) after you upgrade.

## Aggregate model was merged into Prefix

The `Aggregate` model was removed and all existing aggregates will be migrated to `Prefix` with type set to `Container`. The `Aggregate.date_added` field will be migrated to `Prefix.date_allocated` and changed from a `Date` field to a `DateTime` field with the time set to `00:00`. The fields `Aggregate.tenant`, `Aggregate.rir`, and `Aggregate.description` will be migrated over to the same fields on `Prefix`.

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
