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
