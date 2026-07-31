# Change Logging

Nautobot utilizes two fundamental types of change categories to log change events: Administrative and Object-level.

## Administrative Changes

Administrative changes are those made under the "Admin" section of the user interface. This is the primary view for Users, Groups, Object Permissions, and other objects core to the administration of Nautobot. Any changes made to objects using this interface will be displayed as "Log entries" under the "Administration" section of the Admin list view. This is a read-only view that disallows manual creation, updating, or deletion of these objects.

These records are commonly referred to as "admin logs" for short and are provided by default by the Django web framework.  

You may access these records if logged in either as a superuser, or a staff user with `view_logentry` permission, by navigating to `/admin/` or by clicking your username in the navigation bar, then "Admin".

## Object Changes

Every time an object in Nautobot is created, updated, or deleted, a serialized copy of that object is saved to the database, along with meta data including the current time and the user associated with the change. These records form a persistent record of changes both for each individual object as well as Nautobot as a whole. The global change log can be viewed by navigating to Extensibility > Logging > Change Log.

A serialized representation of the instance being modified is included in JSON format. This is similar to how objects are conveyed within the REST API.

When a request is made, a UUID is generated and attached to any change records resulting from that request. For example, editing three objects in bulk will create a separate change record for each  (three in total), and each of those objects will be associated with the same UUID. This makes it easy to identify all the change records resulting from a particular request.

Change records are exposed in the API via the read-only endpoint `/api/extras/object-changes/`. They may also be exported via the web UI in CSV format.

Change records can also be accessed via the read-only GraphQL endpoint `/api/graphql/`. An example query to fetch change logs by action:

```graphql
{ 
  query: object_changes(action: "created") {
    action
    user_name
    object_repr
  }
}
```

## Many-to-Many Association Changes

+++ 2.4.39

Some many-to-many relationships in Nautobot are implemented with an explicit "through" model that is exposed through its own REST API endpoint, for example `IPAddressToInterface` (`/api/ipam/ip-address-to-interface/`, associating IP addresses with interfaces) or `VRFPrefixAssignment` (`/api/ipam/vrf-prefix-assignments/`, associating VRFs with prefixes).

Creating or deleting such an association record - whether through its REST API endpoint, the UI, or ORM many-to-many operations such as `interface.ip_addresses.add(...)`, `.remove(...)`, `.set(...)`, or `.clear()` - records an "update" change against *both* of the objects it associates. These change records appear in both objects' change logs and drive any [webhooks](webhook.md), [job hooks](jobs/jobhook.md), and [events](events.md) configured for those objects.

!!! note
    As with all change logging, ORM operations are only recorded when performed within a change-logging context: this is automatic for web requests and Jobs, while shell or script usage must be wrapped in `web_request_context`. See [Change Logging and Webhooks](../administration/tools/nautobot-shell.md#change-logging-and-webhooks) for details.

Please note the following behavioral details:

- Deleting an object that *cascades* to its association records (for example, deleting a Device that has VRF assignments) records a "delete" change for the deleted object only; the surviving objects on the other side of its associations (the VRFs) do not receive a change record, and their webhooks and job hooks do not fire. This is a deliberate trade-off: a single delete may cascade to association records for many thousands of surviving objects (consider deleting a Location to which thousands of Prefixes are assigned), and recording a change for each would require serializing every one of those objects and dispatching a webhook, job hook, and event for each within that one request. Note that the deleted object's own "delete" change record includes its final serialized data, so removed associations remain discoverable from that record where the object's REST API representation includes them (for example, a deleted Prefix's record includes its location assignments).
- Updating additional fields on an association record itself (for example, `VRFDeviceAssignment.rd`) does not record a change against the associated objects, as their own data is unaffected.
- Because the serialized data of the associated objects may not include the association itself, the "difference" display of such a change record may be empty even though the change record is meaningful and still drives webhooks, job hooks, and events.
- App-defined models automatically receive the same behavior for any many-to-many relationship declared with an explicit `through` model. An App can opt an association model out of this behavior by setting the class attribute `is_m2m_change_logged = False` on the through model, as Nautobot itself does for user-specific preference data such as `UserSavedViewAssociation`.
