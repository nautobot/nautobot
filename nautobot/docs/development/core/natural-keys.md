# Natural Keys in Nautobot Models

+++ 2.0.0

Nautobot models derived from `BaseModel` automatically support the following [natural key](https://docs.djangoproject.com/en/3.2/topics/serialization/#natural-keys) APIs:

- Django's `instance.natural_key()` and `Model.objects.get_by_natural_key()` method APIs

## Using the Natural Key APIs

The `natural_key()` and `get_by_natural_key()` APIs are symmetric with one another:

```python
>>> DeviceType.objects.first().natural_key()
['MegaCorp', 'Model 9000']

>>> DeviceType.objects.get_by_natural_key("MegaCorp", "Model 9000")
<DeviceType: Model 9000>
```

## Implementing the Natural Key APIs

In many model cases, Nautobot's default implementation of these APIs will suffice. As long as your model has any of the following, a default natural key will be automatically made available:

- One or more `UniqueConstraint` declarations
- Any `unique_together` declaration
- Any field (other than `id`) that is set as `unique=True`.

There are a few special cases that will need special handling as described below.

### Self-Referential Natural Keys

An example of this can be seen with the `Location` model, where a given instance is only uniquely identified by its name **in combination with its parent**, which is another `Location`. Nautobot's default implementation would fall into an infinite recursion when trying to identify the Location's natural key fields, since they would be identified as  `("name", "parent__name", "parent__parent__name", "parent__parent__parent__name", ...)`.

In a case like this, Nautobot is able to support _variadic_ natural keys, where the number and listing of natural keys may vary depending on the data of a given instance. To make this work, you will need to override two APIs related to natural keys on your model (`natural_key_field_lookups` and `natural_key_args_to_kwargs`) as follows:

```python
class Location(TreeModel):
    class Meta:
        unique_together = [["parent", "name"]]

    @classproperty
    def natural_key_field_lookups(cls):
        """
        Due to the recursive nature of Location's natural key, we need a custom implementation of this property.

        This returns a set of natural key lookups based on the current maximum depth of the Location tree.
        For example if the tree is 2 layers deep, it will return ["name", "parent__name", "parent__parent__name"].

        Without this custom implementation, the generic `natural_key_field_lookups` would recurse infinitely.
        """
        lookups = []
        name = "name"
        for _ in range(cls.objects.max_depth + 1):
            lookups.append(name)
            name = f"parent__{name}"
        return lookups

    @classmethod
    def natural_key_args_to_kwargs(cls, args):
        """Handle the possibility that more recursive "parent" lookups were specified than we initially expected."""
        args = list(args)
        natural_key_field_lookups = list(cls.natural_key_field_lookups)
        while len(args) < len(natural_key_field_lookups):
            args.append(None)
        while len(args) > len(natural_key_field_lookups):
            natural_key_field_lookups.append(f"parent__{natural_key_field_lookups[-1]}")
        return dict(zip(natural_key_field_lookups, args))
```

### Natural Keys Referencing a Different Self-Referential Model

Similarly, if you have a model whose natural keys include a `ForeignKey` to a model like `Location` with self-referential and variadic natural keys, for the related model to be handled properly, you must always ensure that the related field is the **last** such field in your model's uniqueness constraint or `natural_key_field_names` declaration.

Instead of this:

```python
class VLANGroup(BaseModel):
    class Meta:
        unique_together = [["location", "name"]]  # wrong, nested location natural key cannot be variadic
```

Do this:

```python
class VLANGroup(BaseModel):
    class Meta:
        unique_together = [["name", "location"]]  # correct, nested location natural key can be variadic
```

### No Uniqueness Constraints

You really **shouldn't** implement any models that lack one of the aforementioned uniqueness constraints, but if for some reason you find yourself in this situation, there are two possible approaches you can take:

#### Approximate the Natural Key

Perhaps your model doesn't have any actual database-level uniqueness constraints, but there are one or more fields that practically serve to uniquely identify a model instance. An example case here might be a model that has a `DateTimeField` with `auto_now_add=True` - while it may not be guaranteed unique by the database, in most cases a given timestamp is going to match at most one model instance. In cases like this you can declare `natural_key_field_names` on your model class to explicitly specify the list of "nearly unique" fields that should serve as the natural key for your model:

```python
class FileProxy(BaseModel):
    name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    # no UniqueConstraint or unique_together - whoops!

    natural_key_field_names = ["name", "uploaded_at"]
```

#### Remove the Natural Key

If the model simply lacks any conceivable combination of fields that could uniquely identify a specific model instance, you'll need to explicitly remove the `natural_key` method from your model so that Django doesn't attempt to automatically call it at various points (notably, when running [`nautobot-server dumpdata --natural-primary`](../../user-guide/administration/tools/nautobot-server.md#dumpdata)) and error out. This can be accomplished as follows:

```python
class MyUnnaturalModel(BaseModel):
    class AttributeRemover:
        def __get__(self, instance, owner):
            raise AttributeError("MyUnnaturalModel doesn't yet have a natural key!")

    natural_key = AttributeRemover()
```

### Natural Keys and Export/Import Match Fields

When [exporting and importing records](../../user-guide/feature-guides/import-and-export.md), a model's natural key also serves as the basis for its default declared [match fields](../../user-guide/feature-guides/import-and-export.md#match-fields) in an export. The natural-key field names are translated to the serializer fields any lookups start from: for example, a natural key of `name`, `tenant__name` and `location__name` makes the default match fields `name`, `tenant` and `location`.

#### Overriding the Default Match Fields

If the model's database-level natural key differs from the REST API serializer's fields that should be used for lookup on import, you can declare on the serializer a `Meta.import_match_fields` attribute to override the above default. For example, `IPAddress.natural_key_field_names = ["parent__namespace", "host"]`, but `IPAddressSerializer` has `namespace` and `address` fields instead. In this case we must declare `IPAddressSerializer.Meta.import_match_fields = ["namespace", "address"]` as an override.

#### Overriding Matching Behavior

Each import match field must be a writable field of the serializer that contains a single value (not a to-many field such as `tags`). By default, an import matches existing records by passing each such field's value to the model queryset's `filter()` under the field's own name, so the queryset must accept that argument. Where it doesn't, the serializer has two ways to override this default behavior:

- A serializer can define `Meta.related_field_query_paths` to specify mappings between serializer related fields and their equivalent queryset filters. For example, the IP Address serializer matches partly on the serializer field `namespace`, which needs to be mapped back to the database lookup `parent__namespace`, so we must declare `IPAddressSerializer.Meta.related_field_query_paths = {"namespace": "parent__namespace"}`. This mapping also applies on export, where it allows the `namespace` field to be exported as its natural-key lookups (`namespace__name`) and declared as a match field.
- A serializer can override `get_import_match_filter(field_name, value)` in cases where the previous option is insufficient, for example where the serializer field's _value_ also needs to be transformed in some way. Again, the IP Address serializer is an example of this, where it needs to transform a provided `address` value (`netaddr.IPNetwork("10.0.0.1/24")`) to its `host` value alone (`netaddr.IPAddress("10.0.0.1")`) for a proper query lookup.

!!! warning
    Any override to `get_import_match_filter()` must handle the possibility that `value` is `None`, as it is called
    this way when validating match fields, including when determining a model's default match fields during export
    and import.

#### Avoiding Conflicts Between Fields

Finally, in cases where the default (all-fields) export would include fields that contain derived values or are otherwise redundant with the preferred natural-key fields, a serializer can additionally define `Meta.derived_fields_omitted_from_default_export`, which is a list of field names that are omitted from the default export, but can still be explicitly selected for inclusion if desired. The IP Address serializer again provides an example here - because the serializer `parent` field derives its value from the natural-key `namespace` and `address` fields on an import, it would be undesirable to include this field in the default export since a change to the `namespace` would invalidate the `parent` and vice versa. Therefore, `IPAddressSerializer.Meta.derived_fields_omitted_from_default_export` is declared as `["parent"]`.

#### Worked Example

Putting all of the above together, the relevant parts of `IPAddressSerializer` look like this:

```python
class IPAddressSerializer(NautobotModelSerializer):
    class Meta:
        model = IPAddress
        fields = "__all__"
        # The natural key's `parent__namespace` is written as `namespace`, and `host` as part of `address`
        import_match_fields = ["namespace", "address"]
        related_field_query_paths = {"namespace": "parent__namespace"}
        derived_fields_omitted_from_default_export = ["parent"]

    def get_import_match_filter(self, field_name, value):
        if field_name == "address":
            return {"host": value.ip if value is not None else None}
        return super().get_import_match_filter(field_name, value)
```
