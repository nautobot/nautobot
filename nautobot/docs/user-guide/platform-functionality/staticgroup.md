# Static Groups

+++ 2.3.0

Static Groups provide a way to organize objects (of a single Content Type). They are a counterpart to [Dynamic Groups](dynamicgroup.md), the difference between the two being that members of a Static Group are manually (statically) assigned to that group, whereas members of a Dynamic Group are automatically (dynamically) determined based on a set of filter rules.

A given Static Group may contain any number of objects of the appropriate type as members, and an object may belong to any number of Static Groups of the appropriate content-type as a member of each.

When creating a Static Group, you must provide a unique name for the group and define the Content Type of objects that it contains, for example `dcim.device`. You can also optionally provide a description for the group, assign it to a [Tenant](../core-data-model/tenancy/tenant.md) and/or apply [Tags](tag.md) to it.

Once created, the Content Type for a Static Group may not be changed, as doing so would invalidate any existing members of this group. The name, description, tenant, and tags may be updated if desired.

Each association of a given object into a given Static Group is recorded by a [Static Group Association](staticgroupassociation.md) database record. Individual objects can be associated to Static Groups in their create/edit form, but in most cases it's easier and quicker to bulk-update a set of objects from their appropriate list/table view via the "Update Static Groups" button.

## REST API

The REST API endpoints under `/api/extras/static-groups/` are used to perform standard CRUD (Create/Retrieve/Update/Delete) operations on Static Group definitions. There is also a special read-only endpoint `/api/extras/static-groups/<group UUID>/members/` that returns a serialized list of the group's member objects; for example, for a Static Group of Prefixes, this endpoint would return a list of the Prefix objects contained in this Static Group.

As in the database itself, in the REST API, assignment of individual objects to an individual Static Group is managed via the endpoints under `/api/extras/static-group-associations/`. Here you can perform CRUD operations to associate objects to an existing Static Group, retrieve the list of associations, and update/delete existing object associations.

## Python API

From a given `StaticGroup` record, the following Python APIs are available:

* `group.members` - returns a `QuerySet` directly representing the objects (for example, a `QuerySet` of `Prefix` records for a Static Group of Prefixes) that are members of this group. Can also be set by providing either a list or `QuerySet` of appropriate objects -- doing so will replace all assigned group members with the provided objects, so in many cases you may prefer to use the `add_members` and `remove_members` APIs below instead.
* `group.static_group_associations` - returns a `QuerySet` of `StaticGroupAssociation` records representing the assignment of objects to this group.
* `group.add_members(list_or_queryset)` - associate the given objects to this group as members by creating the appropriate `StaticGroupAssociation` database records.
* `group.remove_members(list_or_queryset)` - disassociate the given objects from this group by deleting any appropriate `StaticGroupAssociation` database records.

From a given record of any object type that can be a member of a Static Group, the following Python APIs are available:

* `object.static_groups` - returns a `QuerySet` directly representing the `StaticGroup` records that contain this object as a member.
* `object.associated_static_groups` - returns a `QuerySet` of `StaticGroupAssociation` records representing the assignment of this object to static groups.

!!! tip
    By default, all models inheriting from Nautobot's `OrganizationalModel` or `PrimaryModel` classes are assumed to be a viable object type for Static Groups to contain. Individual models that do not wish to be assignable to Static Groups can declare the flag `is_static_group_associable_model = False` on their model definition. Conversely, models that inherit directly from Nautobot's `BaseModel` default to *not* supporting Static Groups, but can include the `nautobot.apps.models.StaticGroupMixin` class as a part of their class definition in order to enable Static Group support.
