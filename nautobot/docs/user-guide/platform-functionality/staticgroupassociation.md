# Static Group Associations

+++ 2.3.0

Each Static Group Association database record represents the association of a single Nautobot object to a single [Static Group](staticgroup.md), such as the association of [Prefix](../core-data-model/ipam/prefix.md) "10.0.0.0/8" to Static Group "Private Address Space". A Static Group may contain any number of objects as members, and an object may belong to any number of Static Groups of the appropriate content-type; this many-to-many relationship is recorded by Static Group Association records.

## REST API

The REST API endpoints under `/api/extras/static-group-associations/` normally omit Static Group Associations corresponding to a hidden (Nautobot internal) Static Group. It is possible to view (but not modify) such groups in the REST API by specifying `?hidden=True` as a query parameter but this should be treated as debugging functionality rather than a feature intended for consumption by end users.

## Python API

The `StaticGroupAssociation.objects` default manager omits associations corresponding to hidden Static Groups. If you have a need to perform queries that include hidden groups as well, use the `StaticGroupAssociation.all_objects` manager instead.
