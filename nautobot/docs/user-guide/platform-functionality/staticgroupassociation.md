# Static Group Associations

+++ 2.3.0

Each Static Group Association database record represents the association of a single Nautobot object to a single [Static Group](staticgroup.md), such as the association of [Prefix](../core-data-model/ipam/prefix.md) "10.0.0.0/8" to Static Group "Private Address Space". A Static Group may contain any number of objects as members, and an object may belong to any number of Static Groups of the appropriate content-type; this many-to-many relationship is recorded by Static Group Association records.
