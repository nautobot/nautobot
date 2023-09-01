# Uniquely Identifying a Nautobot Object

In Nautobot v1.X, the slug field of many models could be used to uniquely identify a specific instance in the database. This was a convenient way to reference an object, but the slug field had some drawbacks and slugs were ultimately removed in Nautobot v2.0. As a result, new patterns will have to be adopted when trying to retrieve specific objects from the database.

## Primary Keys vs. Natural Keys

When designing an application for Nautobot, one of the key decisions is whether to use a primary key or a natural key to uniquely identify individual model instances. Here are some trade-offs to consider:

### Primary Keys

The primary key is a concrete database field and is the primary method for referencing an object or relating multiple objects in the Nautobot database. Here are some advantages of using primary keys:

- **Uniqueness:** Primary keys are guaranteed to be unique.
- **Performance:** Primary keys are always indexed in Nautobot, which makes lookups very fast.

However, there are also some disadvantages to using primary keys:

- **Usability**: Primary keys in Nautobot use UUIDs and can be difficult to work with directly.
- **Portability:** Primary keys are specific to a single database and cannot be used to identify an object in multiple contexts, such as in external applications or in different databases.

### Natural Keys

A natural key is an identifier that is based on the natural attributes of a record, such as a platform's name or, in the case of some Nautobot models, a combination of fields. For example, the Prefix model's natural key is formed using a combination of the `prefix` field and the associated Namespace's `name`. Here are some advantages of using natural keys:

- **Usability:** Natural keys are more user-friendly and easier to remember.
- **Portability:** Natural keys can be used to identify an object in multiple contexts, such as in external applications or in different databases.

However, there are also some disadvantages to using natural keys:

- **Complexity:** Using natural keys can make it more difficult to change the underlying data structure without breaking existing integrations.
- **Performance:** Natural keys are not guaranteed to be indexed which can make lookups slower. Also, natural keys that include fields from related objects will require database joins to retrieve the object from the database.

In general, the decision of whether to use a primary key or a natural key depends on the specific requirements of the application. If uniqueness is critical, or if performance is a concern, a primary key may be the best choice. If human-readability is important, or if portability is a concern, a natural key may be the best choice.

### Using Primary Keys

In Nautobot v2.0, all object view URLs use the primary key of the object. In the web UI and REST API, the object can be accessed by building a URL using the primary key. For example, to retrieve the device with primary key `00000000-0000-0000-0000-000000000000`, the REST API URL would be `/api/dcim/devices/00000000-0000-0000-0000-000000000000/`.

In the Python ORM, the object can be retrieved using the `get()` method of the model manager. For example, to retrieve the device with primary key `00000000-0000-0000-0000-000000000000`, the Python ORM call would be `Device.objects.get(pk='00000000-0000-0000-0000-000000000000')`. Once an instance of the object is retrieved, the primary key can be accessed using the `pk` attribute.

### Using Natural Keys

Natural keys in Nautobot v2.0 are determined by the combination of database fields that uniquely identify an object. In some cases, such as the Platform model, this is a single field (`name`). In other cases, such as the Prefix model, this is a combination of fields (`namespace__name`, `prefix`). To retrieve the list of lookups that are used to form the natural key for a model, use the `natural_key_field_lookups` property of the model. For example, to retrieve the list of fields that are used to form the natural key for the Prefix model, the Python ORM call would be `Prefix.natural_key_field_lookups`.

In Nautobot v2.0, the REST API and web UI list views can be filtered to find objects based on their attributes. In some cases, these filters will be sufficient for filtering a list down to an individual object. For example, to retrieve the device with name "router1" in tenant "xyz", the REST API URL would be `/api/dcim/devices/?name=router1&tenant=xyz`. However, the filters in Nautobot do not currently cover all combinations of natural key field lookups for all models and the previous example could return multiple objects because it does not filter on the location field which is also required to uniquely define a device.

In the Python ORM, objects can be retrieved using the `get_by_natural_key()` method of the model manager. For example, to retrieve the prefix for "10.0.0.0/8" in namespace "Global", the Python ORM call would be `Prefix.objects.get_by_natural_key("Global", "10.0.0.0/8")`. Once an instance of a model is retrieved, the natural key can be accessed using the `natural_key` method:

```py
>>> prefix = Prefix.objects.get_by_natural_key("Global", "10.0.0.0/8")
>>> prefix.natural_key()
['Global', '10.0.0.0/8']
```

!!! info
    See the [documentation on natural keys](../../../../development/core/natural-keys.md) for more information on Nautobot's natural key implementation.

## Customizing Natural Keys

Nautobot provides settings for overriding the default behavior of the natural key for some models. These allow the natural key to be formed by a single field instead of a combination of fields. For more information, see the documentation for the settings listed below.

- [DEVICE_NAME_AS_NATURAL_KEY](../../../../user-guide/administration/configuration/optional-settings.md#device_name_as_natural_key)
- [LOCATION_NAME_AS_NATURAL_KEY](../../../../user-guide/administration/configuration/optional-settings.md#location_name_as_natural_key)
