# Static Group Associations

+++ 2.3.0

Each Static Group Association database record represents the association of a single Nautobot object to a single [static-assignment-based Dynamic Group](dynamicgroup.md), such as the association of [Prefix](../core-data-model/ipam/prefix.md) "10.0.0.0/8" to Dynamic Group "Private Address Space". A Dynamic Group may contain any number of objects as members, and an object may belong to any number of Dynamic Groups of the appropriate content-type; this many-to-many relationship is recorded by Static Group Association records.

!!! info
    As an implementation detail, to improve performance, other types of Dynamic Groups (filter-based and set-based) also use Static Group Association records as a cache of their member objects. By default, the Nautobot UI, REST API, and Python ORM do *not* expose such records; see below.

## UI

The `/extras/static-group-associations/` UI views normally only show Static Group Associations corresponding to static-assignment-based Dynamic Groups; those corresponding to other types of Dynamic Groups are not displayed. It is possible to view (but not modify) such records in the UI list view by filtering on a specific Dynamic Group of another type, but this should be treated as debugging functionality rather than a feature intended for consumption by end users.

## REST API

The REST API endpoints under `/api/extras/static-group-associations/` normally only show Static Group Associations corresponding to static-assignment-based Dynamic Groups; those corresponding to other types of Dynamic Groups are not displayed. It is possible to view (but not modify) such records in the REST API by filtering on a specific Dynamic Group of another type, but this should be treated as debugging functionality rather than a feature intended for consumption by end users.

## Python ORM

The `StaticGroupAssociation.objects` default manager also only includes records corresponding to static-assignment-based Dynamic Groups. If you have a need to perform queries or other operations that include associations of other group types as well, use the `StaticGroupAssociation.all_objects` manager instead.
