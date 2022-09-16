# Best Practices

While there are many different development interfaces in Nautobot that each expose unique functionality, there are a common set of a best practices that have broad applicability to users and developers alike. This includes elements of writing Jobs, Plugins, and scripts for execution through the `nbshell`.

The below best practices apply to test code as well as feature code, and there are additional [test-specific best practices](testing.md) to be aware of as well.

## Base Classes

For models that support change-logging, custom fields, and relationships (which includes all subclasses of `OrganizationalModel` and `PrimaryModel`), the "Full-featured models" base classes below should always be used. For less full-featured models, refer to the "Minimal models" column instead.

| Feature                  | Full-featured models       | Minimal models             |
| ------------------------ | -------------------------- | -------------------------- |
| FilterSets               | `NautobotFilterSet`        | `BaseFilterSet`            |
| Object create/edit forms | `NautobotModelForm`        | `BootstrapMixin`           |
| Object bulk-edit forms   | `NautobotBulkEditForm`     | `BootstrapMixin`           |
| Table filter forms       | `NautobotFilterForm`       | `BootstrapMixin`           |
| Read-only serializers    | `BaseModelSerializer`      | `BaseModelSerializer`      |
| Nested serializers       | `WritableNestedSerializer` | `WritableNestedSerializer` |
| All other serializers    | `NautobotModelSerializer`  | `ValidatedModelSerializer` |
| API View Sets            | `NautobotModelViewSet`     | `ModelViewSet`             |

## Model Existence in the Database

A common Django pattern is to check whether a model instance's primary key (`pk`) field is set as a proxy for whether the instance has been written to the database or whether it exists only in memory.
Because of the way Nautobot's UUID primary keys are implemented, **this check will not work as expected** because model instances are assigned a UUID in memory _at instance creation time_, not at the time they are written to the database (when the model's `save()` method is called).
Instead, for any model which inherits from `nautobot.core.models.BaseModel`, you should check an instance's `present_in_database` property which will be either `True` or `False`.

Instead of:

```python
if instance.pk:
    # Are we working with an existing instance in the database?
    # Actually, the above check doesn't tell us one way or the other!
    ...
else:
    # Will never be reached!
    ...
```

Use:

```python
if instance.present_in_database:
    # We're working with an existing instance in the database!
    ...
else:
    # We're working with a newly created instance not yet written to the database!
    ...
```

!!! note
    There is one case where a model instance _will_ have a null primary key, and that is the case where it has been removed from the database and is in the process of being deleted.
    For most purposes, this is not the case you are intending to check!

## Model Validation

Django offers several places and mechanism in which to exert data and model validation. All model specific validation should occur within the model's `clean()` method or field specific validators. This ensures the validation logic runs and is consistent through the various Nautobot interfaces (Web UI, REST API, ORM, etc).

### Consuming Model Validation

Django places specific separation between validation and the saving of an instance and this means it is a common Django pattern to make explicit calls first to a model instance's `clean()`/`full_clean()` methods and then the `save()` method. Calling only the `save()` method **does not** automatically enforce validation and may lead to data integrity issues.

Nautobot provides a convenience method that both enforces model validation and saves the instance in a single call to `validated_save()`. Any model which inherits from `nautobot.core.models.BaseModel` has this method available. This includes all core models and it is recommended that all new Nautobot models and plugin-provided models also inherit from `BaseModel` or one of its descendants such as `nautobot.core.models.generics.OrganizationalModel` or `nautobot.core.models.generics.PrimaryModel`.

The intended audience for the `validated_save()` convenience method is Job authors and anyone writing scripts for, or interacting with the ORM directly through the `nbshell` command. It is generally not recommended however, to use `validated_save()` as a blanket replacement for the `save()` method in the core of Nautobot.

During execution, should model validation fail, `validated_save()` will raise `django.core.exceptions.ValidationError` in the normal Django fashion.

## Slug Field

Moving forward in Nautobot, all models should have a `slug` field. This field can be safely/correctly used in URL patterns, dictionary keys, GraphQL and REST API. Nautobot has provided the `AutoSlugField` to handle automatically populating the `slug` field from another field(s). Generally speaking model slugs should be populated from the `name` field. Below is an example on defining the `slug` field.

```python
from django.db import models

from nautobot.core.fields import AutoSlugField
from nautobot.core.models.generics import PrimaryModel

class ExampleModel(PrimaryModel):
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from='name')
```

## Getting URL Routes

When developing new models a need often arises to retrieve a reversible route for a model to access it in either the web UI or the REST API. When this time comes, you **must** use `nautobot.utilities.utils.get_route_for_model`. You **must not** write your own logic to construct route names.

```python
from nautobot.utilities.utils import get_route_for_model
```

This utility function supports both UI and API views for both Nautobot core apps and Nautobot plugins.

+++ 1.4.3
    Support for generating API routes was added to `get_route_for_model()` by passing the argument `api=True`.

### UI Routes

Instead of:

```python
route = f"{model._meta.app_label}:{model._meta.model_name}_list"
if model._meta.app_label in settings.PLUGINS:
    route = f"plugins:{route}"
```

Use:

```python
route = get_route_for_model(model, "list")
```

### REST API Routes

Instead of:

```python
api_route = f"{model._meta.app_label}-api:{model._meta.model_name}-list"
if model._meta.app_label in settings.PLUGINS:
    api_route = f"plugins-api:{api_route}"
```

Use:

```python
api_route = get_route_for_model(model, "list", api=True)
```

### Examples

Core models:

```python
>>> get_route_for_model(Device, "list")
"dcim:device_list"
>>> get_route_for_model(Device, "list", api=True)
"dcim-api:device-list"
```

Plugin models:

```python
>>> get_route_for_model(ExampleModel, "list")
"plugins:example_plugin:examplemodel_list"
>>> get_route_for_model(ExampleModel, "list", api=True)
"plugins-api:example_plugin-api:examplemodel-list"
```

!!! tip
    The first argument may also optionally be an instance of a model, or a string using the dotted notation of `{app_label}.{model}` (e.g. `dcim.device`).

Using an instance:

```python
>>> instance = Device.objects.first()
>>> get_route_for_model(instance, "list")
"dcim:device_list"
```

Using dotted notation:

```python
>>> get_route_for_model("dcim.device", "list")
"dcim:device_list"
```

## Filtering Models with FilterSets

The following best practices must be considered when establishing new `FilterSet` classes for model classes.

### Mapping Model Fields to Filters

- Filtersets **must** inherit from `nautobot.extras.filters.NautobotFilterSet` (which inherits from `nautobot.utilities.filters.BaseFilterSet`)
    - This affords that automatically generated lookup expressions (`ic`, `nic`, `iew`, `niew`, etc.) are always included
    - This also asserts that the correct underlying `Form` class that maps the generated form field types and widgets will be included
- FIltersets **must** publish all model fields from a model, including related fields.
    - All fields should be provided using `Meta.fields = "__all__"` and this would be preferable for the first and common case as it requires the least maintanence and overhead and asserts parity between the model fields and the filterset filters.
    - In some cases simply excluding certain fields would be the next most preferable e.g. `Meta.exclude = ["unwanted_field", "other_unwanted_field"]`
    - Finally, the last resort should be explicitly declaring the desired fields using `Meta.fields =`. This should be avoided because it incurs the highest technical debt in maintaining alignment between model fields and filters.
- In the event that fields do need to be customized to extend lookup expressions, a [dictionary of field names mapped to a list of lookups](https://django-filter.readthedocs.io/en/stable/ref/filterset.html#declaring-filterable-fields) **may** be used, however, this pattern is only compatible with explicitly declaring all fields, which should also be avoided for the common case. For example:

```python
class UserFilter(NautobotFilterSet):
    class Meta:
        model = User
        fields = {
            'username': ['exact', 'contains'],
            'last_login': ['exact', 'year__gt'],
        }
```

- It is acceptable that default filter mappings **may** need to be overridden with custom filter declarations, but [`filter_overrides`](https://django-filter.readthedocs.io/en/stable/ref/filterset.html#customise-filter-generation-with-filter-overrides) (see below) should be used as a first resort.
- Custom filter definitions **must not** shadow the name of an existing model field if it is also changing the type.
    - For example `DeviceFilterSet.interfaces` is a `BooleanFilter` that is shadowing the `Device.interfaces` related manager. This introduces problems with automatic introspection of the filterset and this pattern **must** be avoided.
- For foreign-key related fields, **on existing core models in the v1.3 release train**:
    - The field **should** be shadowed, replacing the PK filter with a lookup-based on a more human-readable value (typically `slug`, if available).
    - A PK-based filter **should** be made available as well, generally with a name suffixed by `_id`. For example:

```python
    provider = django_filters.ModelMultipleChoiceFilter(
        field_name="provider__slug",
        queryset=Provider.objects.all(),
        to_field_name="slug",
        label="Provider (slug)",
    )
    provider_id = django_filters.ModelMultipleChoiceFilter(
        queryset=Provider.objects.all(),
        label="Provider (ID)",
    )
```

- For foreign-key related fields on **new core models for v1.4 or later:**
    - The field **must** be shadowed utilizing a hybrid `NaturalKeyOrPKMultipleChoiceFilter` which will automatically try to lookup by UUID or `slug` depending on the value of the incoming argument (e.g. UUID string vs. slug string).
    - Fields that use `name` instead of `slug` can set the `natural_key` argument on `NaturalKeyOrPKMultipleChoiceFilter`.
    - In default settings for filtersets, when not using `NaturalKeyOrPKMultipleChoiceFilter`, `provider` would be a `pk` (UUID) field, whereas using `NaturalKeyOrPKMultipleChoiceFilter` will automatically support both input values for `slug` or `pk`.
    - New filtersets should follow this direction vs. propagating the need to continue to overload the default foreign-key filter and define an additional `_id` filter on each new filterset. _We know that most existing FilterSets aren't following this pattern, and we plan to change that in a major release._
    - Using the previous field (`provider`) as an example, it would look something like this:

```python
    from nautobot.utilities.filters import NaturalKeyOrPKMultipleChoiceFilter
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Provider.objects.all(),
        label="Provider (slug or ID)",
    )
    # optionally use the to_field_name argument to set the field to name instead of slug
    provider = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="name",
        queryset=Provider.objects.all(),
        label="Provider (name or ID)",
    )
```

### Filter Naming and Definition

- Boolean filters for membership **must** be named with `has_{related_name}` (e.g. `has_interfaces`)

- Boolean filters for identity **must** be named with `is_{name}` (e.g. `is_virtual_chassis`) although this is semantically identical to `has_` filters, there may be occasions where naming the filter `is_` would be more intuitive.

- Filters **must** declare [`field_name`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#field-name) when they have a different name than the underlying model field they are referencing. Where possible the suffix component of the filter name **must** map directly to the underlying field name.

  For example, `DeviceFilterSet.has_console_ports` could be better named, to assert that the filter name following the `has_` prefix is a one-to-one mapping to the underlying model's related field name (`consoleports`) therefore `field_name` must point to the field name as defined on the model:

```python
    has_consoleports = BooleanFilter(field_name="consoleports")
```

- Filters **must** be declared using the appropriate lookup expression (`lookup_expr`) if any other expression than `exact` (the default) is required. For example:

```python
   has_consoleports = BooleanFilter(field_name="consoleports", lookup_expr="isnull")
```

- Filters **must** be declared using [`exclude=True`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#exclude) if a queryset `.exclude()` is required to be called vs. queryset `.filter()` which is the default when the filter default `exclude=False` is passed through. If you require `Foo.objects.exclude()`, you must pass `exclude=True` instead of defining a filterset method to explicitly hard-code such a query. For example:

```python
   has_consoleports = BooleanFilter(field_name="consoleports", lookup_expr="isnull", exclude=True)
```

- Filters **must** be declared using [`disinct=True`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#distinct) if a queryset `.distinct()`is required to be called on the queryset

- Filters **must not** be set to be required using `required=True`

- Filter methods defined using the [`method=`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#method) keyword argument **may only be used as a last resort** (see below) when correct usage of `field_name`, `lookup_expr`, `exclude`, or other filter keyword arguments do not suffice. In other words: filter methods should used as the exception and not the rule.

- Use of [`filter_overrides`](https://django-filter.readthedocs.io/en/stable/ref/filterset.html#filter-overrides) **must be considered** in cases where more-specific class-local overrides. The need may ocassionally arise to change certain filter-level arguments used for filter generation, such such as changing a filter class, or customizing a UI widget. Any `extra` arguments are sent to the filter as keyword arguments at instance creation time. (Hint: `extra` must be a callable)

    For example:

```python
class ProductFilter(NautobotFilterSet):

     class Meta:
         model = Interface
         fields = "__all__"
         filter_overrides = {
             # This would change the default to all CharFields to use lookup_expr="icontains". It
             # would also pass in the custom `choices` generated by the `generate_choices()`
             # function.
             models.CharField: {
                 "filter_class": filters.MultiValueCharFilter,
                 "extra": lambda f: {
                     "lookup_expr": "icontains",
                     "choices": generate_choices(),
                 },
             },
             # This would make BooleanFields use a radio select widget vs. the default of checkbox
             models.BooleanField: {
                 "extra": lambda f: {
                     "widget": forms.RadioSelect,
                 },
             },
         }
```

!!!warning
    Existing features of filtersets and filters **must** be exhausted first using keyword arguments before resorting to customizing, re-declaring/overloading, or defining filter methods.

### Filter Methods

Filters on a filterset can reference a `method` (either a callable, or the name of a method on the filterset) to perform custom business logic for that filter field. However, many uses of filter methods in Nautobot are problematic because they break the ability for such filter fields to be properly reversible.

Consider this example from `nautobot.dcim.filters.DeviceFilterSet.pass_through_ports`:

```python
    # Filter field definition is a BooleanFilter, for which an "isnull" lookup_expr
    # is the only valid filter expression
    pass_through_ports = django_filters.BooleanFilter(
        method="_pass_through_ports",
        label="Has pass-through ports",
    )

    # Method definition loses context and further the field's lookup_expr
    # falls back to the default of "exact" and the `name` value is irrelevant here.
    def _pass_through_ports(self, queryset, name, value):
        breakpoint()  # This was added to illustrate debugging with pdb below
        return queryset.exclude(frontports__isnull=value, rearports__isnull=value)
```

The default `lookup_expr` unless otherwise specified is “exact”, as seen in [django_filters.conf](https://github.com/carltongibson/django-filter/blob/main/django_filters/conf.py#L10):

```python
  'DEFAULT_LOOKUP_EXPR': 'exact',
```

When this method is called, the internal state is default, making reverse introspection impossible, because the `lookup_expr` is defaulting to “exact”:

```python
(Pdb) field = self.filters[name]
(Pdb) field.exclude
False
(Pdb) field.lookup_expr
'exact'
```

This means that the arguments for the field are being completely ignored and the hard-coded queryset `queryset.exclude(frontports__isnull=value, rearports__isnull=value)` is all that is being run when this method is called.

Additionally, `name` variable that gets passed to the method cannot be used here because there are two field names at play (`frontports` and `rearports`). This hard-coding is impossible to introspect and therefore impossible to reverse.

So while this filter definition coudl be improved like so, there is still no way to know what is going on in the method body:

```python
    pass_through_ports = django_filters.BooleanFilter(
        method="_pass_through_ports",  # The method that is called
        exclude=True,                  # Perform an `.exclude()` vs. `.filter()``
        lookup_expr="isnull",          # Perform `isnull` vs. `exact``
        label="Has pass-through ports",
    )
```

For illustration, if we use another breakpoint, you can see that the filter field now has the correct attributes that can be used to help reverse this query:

```python
(Pdb) field = self.filters[name]
(Pdb) field.exclude
True
(Pdb) field.lookup_expr
'isnull'
```

Except that it stops there becuse of the method body. Here are the problems:

- There's no way to identify either of the field names required here
- The `name` that is incoming to the method is the filter name as defined (`pass_through_ports` in this case) does not map to an actual model field
- So the filter can be introspected for `lookup_expr` value using `self.filters[name].lookup_expr`, but it would have to be assumed that applies to both fields.
- Same with `exclude` (`self.filters[name].exclude`)

It would be better to just eliminate `pass_through_ports=True` entirely in exchange for `front_ports=True&rear_ports=True` (current) or `has_frontports=True&has_rearports=True` (future).

#### Generating Reversible Q Objects

With consistent and proper use of filter field arguments when defining them on a fitlerset, a query could be constructed using the `field_name` and `lookup_expr` values. For example:

```python
    def generate_query(self, field, value):
        query = Q()
        predicate = {f"{field.field_name}__{field.lookup_expr}": value}
        if field.exclude:
            query |= ~Q(**predicate)
        else:
            query |= Q(**predicate)
        return query


## Somewhere else in business logic:
field = filterset.filters[name]
value = filterset.data[name]
query = generate_query(field, value)
filterset.qs.filter(query).count()  # 339
```

### Summary

- For the vast majority of cases where we have method filters, it’s for Boolean filters
- For the common case **method filters are unnecessary technical debt and should be eliminated where better suited by proper use of filter field arguments**
- Reversibility may not always necessarily be required, but by properly defining `field_name`, `lookup_expr`, and `exclude` on filter fields, **introspection becomes deterministic and reversible queries can be reliably generated as needed.**
- For exceptions such as `DeviceFilterSet.has_primary_ip` where it checks for both `Device.primary_ip4` OR `Device.primary_ip6`, method filters may still be necessary, however, they would be **the exception and not the norm.**
- The good news is that in the core there are not that many of these filter methods defined, but we also don’t want to see them continue to proliferate.

## Using NautobotUIViewSet for Plugin Development

+++ 1.4.0
    Using `NautobotUIViewSet` for [plugin development](../plugins/development.md#nautobotuiviewset) is strongly recommended.
