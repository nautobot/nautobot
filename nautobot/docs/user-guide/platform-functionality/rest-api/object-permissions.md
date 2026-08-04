# REST API Object Permissions

The Nautobot REST API enforces the same object-based permission model used throughout Nautobot (see [Object Permissions](../users/objectpermission.md) and the [Permissions guide](../../administration/guides/permissions.md)). This page describes how a user's object permissions affect what the REST API returns and what it accepts, with particular attention to _related_ objects reached through a serializer.

Throughout this page, "view permission" means that the user has been granted the `view` action for the relevant model — subject to any constraints on the granting [object permission](../users/objectpermission.md) — and that the model has not been exempted via the [`EXEMPT_VIEW_PERMISSIONS`](../../administration/configuration/settings.md#exempt_view_permissions) configuration setting. Superusers implicitly have all object permissions and are exempt from every check described here.

## Primary Objects

For any list or detail (retrieve) request, the set of _primary_ objects is restricted to those the requesting user has permission to view:

- A list endpoint returns only the objects the user is permitted to view.
- A detail endpoint returns `404 Not Found` (rather than `403 Forbidden`) for an object the user is not permitted to view, so as not to disclose the object's existence.

This applies to all list and detail requests and is independent of the [`?depth` query parameter](overview.md#depth-query-parameter).

## Related Objects on Read

When a serializer includes related objects — foreign keys, many-to-many relationships, and [generic relations](overview.md#generic-relations) — the amount of detail returned for each related object depends on the type of relation (single object versus list-of-objects), the [`?depth` query parameter](overview.md#depth-query-parameter), and the user's permission to view that specific related object(s).

### Lists of Related Objects

Lists of related objects (such as reverse foreign-key relations and many-to-many relations) are _filtered_ by view permissions, such that objects that the user is permitted to view are included in the list, and those the user cannot view are omitted from the list. This matches the primary-object listing behavior described above, as well as the behavior of UI "list" views.

### At `?depth=0` (the default)

At depth 0, single related objects are always represented in _brief_ form — an object containing only its `id`, `object_type`, and `url` — _regardless_ of whether the user has permission to view them:

```json
{
    "id": "8badf00d-0000-0000-0000-000000000000",
    "object_type": "dcim.location",
    "url": "https://nautobot.example.com/api/dcim/locations/8badf00d-0000-0000-0000-000000000000/"
}
```

Because only the `id`, `object_type`, and `url` are exposed, this brief representation is considered safe to return even for related objects the user cannot view. It matches the information already visible in the UI, where a related object's link and display text is shown in list and detail views without requiring full view permission on that object.

### At `?depth=1` and Beyond

When `?depth` is greater than `0`, single related objects are serialized according to the user's permission to view them:

- If the user **has** permission to view the related object, it is serialized in full (recursively, up to the requested depth), exactly as it was previously.
- If the user **does not** have permission to view the related object, it is _restricted_ to a brief representation.

The restricted representation is the same `{id, object_type, url}` brief form used at `?depth=0`, plus the related object's human-friendly `display` value:

```json
{
    "id": "8badf00d-0000-0000-0000-000000000000",
    "object_type": "dcim.location",
    "url": "https://nautobot.example.com/api/dcim/locations/8badf00d-0000-0000-0000-000000000000/",
    "display": "Example Location"
}
```

The `display` value is included for parity with the UI, where the name (or other display value) of a related object is visible without requiring full view permission on that object. This is by design, as it allows your system to remain operational and secure with a relatively minimal set of permissions granted to users; if Nautobot did not work this way, you would have to grant explicit view permission to all related models (and hence _all_ of their data fields) in order to see even this basic information.

The `display` field is added _only_ when the object would otherwise have been serialized in full (that is, when it is reached within the requested `?depth`); related objects at the boundary of the requested depth remain limited to the `{id, object_type, url}` brief form.

This behavior applies to foreign key fields, one-to-one fields, [generic relations](overview.md#generic-relations), and equivalent single-value (one-to-one or many-to-one) [relationships](../relationship.md) returned by [`?include=relationships`](overview.md#retrieving-object-relationships-and-relationship-associations).

!!! note
    Related objects belonging to models that are not subject to object-level permissions — for example Django's built-in `Group` and `ContentType` models — are not downgraded, as there is no object-level `view` permission to enforce for them.

## Related Objects on Write

When creating (`POST`) or updating (`PATCH`/`PUT`) an object, any related object(s) referenced in the request body, whether single-relation or many-relation, must be object(s) that the user has permission to view. This applies whether the related object is referenced by primary key, by URL, or by a dictionary of attributes, and it honors object-level constraints — a user may only reference related objects that fall within their view constraints.

- If the user does not have permission to view a referenced foreign key or many-to-many object, the request is rejected with a `400 Bad Request` and an error such as `"Related object not found using the provided attributes: ..."`.
- The same applies to [generic relations](overview.md#generic-relations): assigning an object the user cannot view — for example, attaching a [Note](../note.md) to that object — is rejected with an `"Object not found"` error.

Because a reference to a non-viewable object is, from the API's perspective, indistinguishable from a reference to a nonexistent object, both produce the same "not found" error.

Regardless of the `?depth` value supplied on a write request, the serialized response always renders as if it were `?depth=0`, so related objects in the response body are shown in brief form.
