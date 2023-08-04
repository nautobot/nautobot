# Region and Site to Location Migration Guide

In Nautobot 2.0.0, all the `Region` and `Site` related data models are being migrated to use `Location`. Below is a comprehensive guide for Nautobot users and Nautobot App developers to migrate their `Region` and `Site` related models and apps to `Location`.

## Migrate ObjectPermission instances in Nautobot from Region and Site to Location

Nautobot admins need to migrate `Site` and `Region` Related `ObjectPermission` instances to `Location`. The correct way to do it are documented below with practical examples.

### Region Specific ObjectPermission

Replace `Location` ContentType to `object_types` field of the `ObjectPermission` if it is not already present and add `"location_type__name": "Region"` to `constraints` field if the old `ObjectPermission` only allows operations on `Region` instances and not on `Site` instances.

Since `Location` has all the filters that `Region` had and they retain the same functionalities. We **do not** need to modify the `constraints` field of any `Region` specific `ObjectPermission` instances any further.

### Site Specific ObjectPermission

Replace `Location` ContentType to `object_types` field of the `ObjectPermission` if it is not already present and add `location_type__name: "Site"` to `constraints` field if the old `ObjectPermission` only allows operations on `Site` instances and not on `Region` instances.

The old `constraints` field for a `Site` specific `ObjectPermission` instance might look like this:

```json
{
    "name": "AMS01",
    "name__in": ["AMS01", "ATL01", "EDX01"],
    "slug": "ams01",
    "slug__in": ["ams01", "atl01", "edx01"],
    "id": "c12753e5-8f01-49a6-b0cf-bf8b460853a1",
    "id__in": ["c12753e5-8f01-49a6-b0cf-bf8b460853a1", "455038c3-4045-4b78-85f5-17d9f34cb9e8"],
    "region__name": "United States",
    "region__name__in": ["United States", "Greece", "England"],
    "region__slug": "united-states",
    "region__slug__in": ["united-states", "greece", "england"],
    "region__id": "f77f5706-e5b3-49e0-9749-b8f818319c40",
    "region__id__in": ["f77f5706-e5b3-49e0-9749-b8f818319c40", "7df99dc2-283a-4130-8125-60b9ca293131"],
    "region__parent__name": "North America",
    "region__parent__name__in": ["North America", "Europe"],
    "region__parent__slug": "north-america",
    "region__parent__slug__in": ["north-america", "europe"],
    "region__parent__id": "c1a816df-876f-44d4-8ea0-335898998780",
    "region__parent__id__in": ["c1a816df-876f-44d4-8ea0-335898998780", "a68b0838-d7fb-416c-b4ba-a3e464e552ba"]
}
```

To modify the data correctly, we need to:
    1. Replace all occurrences of "region" with "parent" in the **Key** portion (before ":") of the data **not Value** (after ":").
    2. Since Nautobot carries over the UUIDs of the old `Site`/`Region` instances when creating the new "Site"/"Region" type `Location` instances, we **do not** need to change the UUID values in `...__id` and `...__id__in` Keys.
    3. Since Nautobot 2.x `Locations` do not have `slug` fields, we will need to remove those references. (In a real example, you'd probably want to replace them with `name` references, but in this example we already have `name` references that are redundant with the `slug`, so here we'll just remove the `slug` references entirely.)

The updated JSON data might look like this:

```json
{
    "location_type__name": "Site",
    "name": "AMS01",
    "name__in": ["AMS01", "ATL01", "EDX01"],
    "id": "c12753e5-8f01-49a6-b0cf-bf8b460853a1",
    "id__in": ["c12753e5-8f01-49a6-b0cf-bf8b460853a1", "455038c3-4045-4b78-85f5-17d9f34cb9e8"],
    "parent__name": "United States",
    "parent__name__in": ["United States", "Greece", "England"],
    "parent__id":  "f77f5706-e5b3-49e0-9749-b8f818319c40",
    "parent__id__in": ["f77f5706-e5b3-49e0-9749-b8f818319c40", "7df99dc2-283a-4130-8125-60b9ca293131"],
    "parent__parent__name": "North America",
    "parent__parent__name__in": ["North America", "Europe"],
    "parent__parent__id": "c1a816df-876f-44d4-8ea0-335898998780",
    "parent__parent__id__in": ["c1a816df-876f-44d4-8ea0-335898998780", "a68b0838-d7fb-416c-b4ba-a3e464e552ba"]
}
```

### Other Data Model Specific ObjectPermission e.g. Interface

The old `constraints` field for a `Site`/`Region` related data model's (e.g. `Interface`) `ObjectPermission` instance might look like this:

```json
{
    "device__site__name": "AMS01",
    "device__site__name__in": ["AMS01", "ATL01", "ETX02"],
    "device__site__slug": "ams01",
    "device__site__slug__in": ["ams01", "atl01", "etx02"],
    "device__site__id": "0ab47314-2944-45f6-b964-9e009fc48ce0",
    "device__site__id__in": ["0ab47314-2944-45f6-b964-9e009fc48ce0", "b09545d4-6e2b-471e-8f07-27f25ca308f5"],
    "device__site__region__name": "United States",
    "device__site__region__name__in": ["United States", "United Kingdom", "Greece"],
    "device__site__region__slug": "united-states",
    "device__site__region__slug__in": ["united-states", "united-kingdom", "greece"],
    "device__site__region__id": "f1a79a3c-d980-40e1-979d-abdb0f83388e",
    "device__site__region__id__in": ["f1a79a3c-d980-40e1-979d-abdb0f83388e", "6335a61e-503d-463c-99c2-9c87ef8354d9"],
    "device__site__region__parent__name": "North America",
    "device__site__region__parent__name__in": ["North America", "Europe", "South America"],
    "device__site__region__parent__slug": "north-america",
    "device__site__region__parent__slug__in": ["north-america", "europe", "south-america"],
    "device__site__region__parent__id": "6695809c-b33b-4f12-b0de-a4969000434d",
    "device__site__region__parent__id__in": ["6695809c-b33b-4f12-b0de-a4969000434d", "e51d07bb-3fcf-4306-9d87-6b1ff6dd6378"]
}
```

To modify the data correctly, we need to:
    1. Replace all occurrences of "site" with "location" in the **Key** portion (before ":") of the data **not Value** (after ":").
    2. Replace all occurrences of "region" with "parent" in the **Key** portion (before ":") of the data **not Value** (after ":").
    3. Add `"device__location__location_type__name": "Site"` if the old `ObjectPermission` only allows operations on `Interfaces` of `Device` instances assigned to `Sites`.
    4. Since Nautobot carries over the UUIDs of the old `Site`/`Region` instances when creating the new "Site"/"Region" type `Location` instances, we **do not** need to change the UUID values in `...__id` and `...__id__in` Keys.
    5. As before, remove any `slug` references or replace them with appropriate `name` or `id` references.

The updated JSON data might look like this:

```json
{
    "device__location__location_type__name": "Site",
    "device__location__name": "AMS01",
    "device__location__name__in": ["AMS01", "ATL01", "ETX02"],
    "device__location__id": "0ab47314-2944-45f6-b964-9e009fc48ce0",
    "device__location__id__in": ["0ab47314-2944-45f6-b964-9e009fc48ce0", "b09545d4-6e2b-471e-8f07-27f25ca308f5"],
    "device__location__parent__name": "United States",
    "device__location__parent__name__in": ["United States", "United Kingdom", "Greece"],
    "device__location__parent__id": "f1a79a3c-d980-40e1-979d-abdb0f83388e",
    "device__location__parent__id__in": ["f1a79a3c-d980-40e1-979d-abdb0f83388e", "6335a61e-503d-463c-99c2-9c87ef8354d9"],
    "device__location__parent__parent__name": "North America",
    "device__location__parent__parent__name__in": ["North America", "Europe", "South America"],
    "device__location__parent__parent__id": "6695809c-b33b-4f12-b0de-a4969000434d",
    "device__location__parent__parent__id__in": ["6695809c-b33b-4f12-b0de-a4969000434d", "e51d07bb-3fcf-4306-9d87-6b1ff6dd6378"]
}
```

### Other Data Model Specific ObjectPermission e.g. Note

The old `constraints` field for a `Site`/`Region` related data model's (e.g. `Note`) `ObjectPermission` instance might look like this:

```json
{
    "assigned_object_type": "dcim.site",
    "assigned_object_id": "932d94ee-5571-40a0-903f-4274fcfbed32",
    "assigned_object_id__in": ["932d94ee-5571-40a0-903f-4274fcfbed32", "e383db9a-dd55-464d-9e56-2f18bc03b32c"]
}
```

To modify the data correctly, we need to:
    1. Replace all occurrences of "dcim.site" and/or "dcim.region" with "dcim.location" in the **Value** portion (after ":") of the `assigned_object_type` Key.
    2. Since Nautobot carries over the UUIDs of the old `Site`/`Region` instances when creating the new "Site"/"Region" type `Location` instances, we **do not** need to change the UUID values in the `assigned_object_id` and `assigned_object_id__in` Keys.

The updated JSON data might look like this:

```json
{
    "assigned_object_type": "dcim.location",
    "assigned_object_id": "932d94ee-5571-40a0-903f-4274fcfbed32",
    "assigned_object_id__in": ["932d94ee-5571-40a0-903f-4274fcfbed32", "e383db9a-dd55-464d-9e56-2f18bc03b32c"]
}
```

## Update Nautobot Apps

Any Nautobot Apps that you use and maintain which have existing data referencing Site or Region records will need to be [updated](../../../../development/apps/migration/model-updates/dcim.md#replace-site-and-region-with-location-model) before you can complete your migration to Nautobot 2.0.

## Region and Site Related Data Model Migration Guide For New Nautobot App installations in an Existing Nautobot 2.0 Environment
