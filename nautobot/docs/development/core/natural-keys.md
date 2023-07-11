# Natural Keys in Nautobot Models

+++ 2.0.0

Nautobot models derived from `BaseModel` automatically support the following [natural key](https://docs.djangoproject.com/en/3.2/topics/serialization/#natural-keys) APIs:

- Django's `instance.natural_key()` and `Model.objects.get_by_natural_key()` method APIs
- `instance.composite_key` property inspired by the `django-natural-keys` project
- `Model.objects.get(composite_key=...)` lookup filter inspired by the `django-natural-keys` project

## Using the Natural Key APIs

The `natural_key()` and `get_by_natural_key()` APIs are symmetric with one another:

```python
>>> DeviceType.objects.first().natural_key()
['MegaCorp', 'Model 9000']

>>> DeviceType.objects.get_by_natural_key("MegaCorp", "Model 9000")
<DeviceType: Model 9000>
```

Similarly, the `composite_key` and `get(composite_key=...`) APIs are also symmetric:

```python
# Note that composite_key is a property, not a method!
>>> DeviceType.objects.first().composite_key
'MegaCorp;Model+9000'

>>> DeviceType.objects.get(composite_key="MegaCorp;Model+9000")
<DeviceType: Model 9000>
```

!!! note
    The `composite_key` is designed to be suitable for future use in URL patterns, such as an object detail endpoint potentially supporting `/app/model/<composite_key>/` as an alternative to the common `/app/model/<primary-key>/` pattern.

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
        for _ in range(cls.objects.max_tree_depth() + 1):
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
        unique_together = [["location", "name"]]   # wrong, nested location natural key cannot be variadic
```

Do this:

```python
class VLANGroup(BaseModel):
    class Meta:
        unique_together = [["name", "location"]]   # correct, nested location natural key can be variadic
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
