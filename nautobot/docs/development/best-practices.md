# Best Practices

While there are many different development interfaces in Nautobot that each expose unique functionality, there are a common set of a best practices that have broad applicability to users and developers alike. This includes elements of writing Jobs, Plugins, and scripts for execution through the `nbshell`.

## Model Existence in the Database

A common Django pattern is to check whether a model instance's primary key (`pk`) field is set as a proxy for whether the instance has been written to the database or whether it exists only in memory.
Because of the way Nautobot's UUID primary keys are implemented, **this check will not work as expected** because model instances are assigned a UUID in memory *at instance creation time*, not at the time they are written to the database (when the model's `save()` method is called).
Instead, for any model which inherits from `nautobot.core.models.BaseModel`, you should check an instance's `present_in_database` property which will be either `True` or `False`.

Wrong:

```python
if instance.pk:
    # Are we working with an existing instance in the database?
    # Actually, the above check doesn't tell us one way or the other!
    ...
else:
    # Will never be reached!
    ...
```

Right:

```python
if instance.present_in_database:
    # We're working with an existing instance in the database!
    ...
else:
    # We're working with a newly created instance not yet written to the database!
    ...
```

!!! note
    There is one case where a model instance *will* have a null primary key, and that is the case where it has been removed from the database and is in the process of being deleted.
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
    - For example `DeviceFilterSet.interfaces` is a `BooleanFilter` that is shadowing the `Device.interfaces` related manager. This introduces problems with automatic introspection of the filterset and this pattern MUST be avoided.
- Custom filter definitions **may** shadow the name of an existing field IF this is to adapt a filter for a human-readable field value (such as `slug`) on a related field vs. the `pk` (the default for most related fields). This pattern still relies on accessing the related field by name and then traversing into the relationship using a nested lookup.

### Filter Naming and Definition

- Boolean filters for membership **must** be named with `has_{related_name}` (e.g. `has_interfaces`)

- Boolean filters for identity **must** be named with `is_{name}` (e.g. `is_virtual_chassis`) although this is semantically identical to `has_` filters, there may be occasions where naming the filter `is_` would be more intuitive.

- Filters **must** declare [`field_name`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#field-name) when they have a different name than the underlying field they are referencing. Where possible the suffix component of the filter name should map directly to the underlying field name.

  For example, `DeviceFilterSet.has_console_ports` could be better named, to assert that the filter name following the `has_` prefix is a one-to-one mapping to the underlying model's related field name (`consoleports`) which also means that `field_name` is not required:

```python
    has_consoleports = BooleanFilter(...)
```

- Filters **must** be declared using the appropriate lookup expression (`lookup_expr`) if any other expression than `exact` (the default) is required. For example:

```python
   has_consoleports = BooleanFilter(lookup_expr="isnull", ...)
```

- Filters **must** be declared using [`exclude=True`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#exclude) if a queryset `.exclude()` is required to be called vs. queryset `.filter()` which is the default when the filter default `exclude=False` is passed through. If you require `Foo.objects.exclude()`, you must pass `exclude=True` instead of defining a filterset method to explicitly hard-code such a query. For example:

```python
   has_consoleports = BooleanFilter(lookup_expr="isnull", exclude=True)
```

- Filters **must** be declared using [`disinct=True`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#distinct) if a queryset `.distinct()`is required to be called on the queryset
- Filters **must not** be set to be required using `required=True`
- Filter methods defined using the [`method=`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#method) keyword argument **may only be used as a last resort** (see below) when correct usage of `lookup_expr` ,  `exclude`, or other filter keyword arguments do not suffice. In other words: filter methods should used as the exception and not the rule.
- Use of [`filter_overrides`](https://django-filter.readthedocs.io/en/stable/ref/filterset.html#filter-overrides) **must be considered** in cases where local overrides to certain model field types are required vs. overloading or re-declaring the filter fields are required, such as changing a filter class, or customizing a UI widget. For example:

```python
class ProductFilter(NautobotFilterSet):

     class Meta:
         model = Product
         fields = "__all__"
         filter_overrides = {
             models.CharField: {
                 'filter_class': django_filters.CharFilter,
                 'extra': lambda f: {
                     'lookup_expr': 'icontains',
                 },
             },
             models.BooleanField: {
                 'filter_class': django_filters.BooleanFilter,
                 'extra': lambda f: {
                     'widget': forms.CheckboxInput,
                 },
             },
         }
```

!!!warning
    Existing features of filtersets and filters **must** be exhausted first using keyword arguments before resorting to customizing, re-declaring/overloading, or defining filter methods.

### Filter Methods

Filter methods in the current Nautobot core are problematic because they break the ability for such filter fields to be properly reversible. Specifically a filter method is a callable or the name of a method on a filterset that can be declared on a filter when it is defined on a filterset. This method is used to perform custom business logic on a filter field.

Consider this example from `nautobot.dcim.filters.DeviceFilterSet`:

```python
  # Filter field definition is a BooleanFilter, for which an "isnull" lookup_expr 
  # is the only valid filter expression
  console_ports = django_filters.BooleanFilter(
      method="_console_ports",
      label="Has console ports",
  )
  
  # Method definition loses context and further the field's lookup_expr 
  # falls back to the default of "exact".
  def _console_ports(self, queryset, name, value):
      breakpoint()  # This is where we'll illustrate pdb below
      return queryset.exclude(consoleports__isnull=value)
```

The default `lookup_expr` unless otherwise specified is “exact”, as seen in [django_filters.conf](https://github.com/carltongibson/django-filter/blob/main/django_filters/conf.py#L10):

```python
  'DEFAULT_LOOKUP_EXPR': 'exact',
```

When this method is called, the internal state is default, making reverse introspection impossible, because the `lookup_expr` is defaulting to “exact”:

```python
(Pdb) field = self.filters["console_ports"]
(Pdb) field.exclude
False
(Pdb) field.lookup_expr
'exact' 
```

This means that the arguments for the field are being completely ignored and the hard-coded queryset `queryset.exclude(consoleports__isnull=value)` is all that is being run when this method is called. This hard-coding is impossible to introspect and therefore reverse.

In fact, this method is completely unnecessary, because it could be replaced with options on the filter field itself:

```python
    console_ports = django_filters.BooleanFilter(
        field_name="consoleports",  # The actual related field name
        exclude=True,               # Perform an `.exclude()` vs. `.filter()``
        lookup_expr="isnull",       # Perform `isnull` vs. `exact``
        label="Has console ports",
    )
```

Now, if we use another breakpoint (this time inside of the `DeviceListView.get()` since there’s no method we can break into), you can see that the filter field now has the correect attributes that can be used to accurately reverse this query:

```python
(Pdb) filterset = self.filterset(request.GET, self.queryset)
(Pdb) field = filterset.filters["console_ports"]
(Pdb) field.exclude
True
(Pdb) field.lookup_expr
'isnull'
```

#### Generating Reversible Q Objects

These field values could be used to construct a `Q()` query that looks something like:

```python
def generate_query(self, field_name, lookup_expr, value):
    query = Q()
    predicate = {f"{field_name}__{lookup_expr}": value}
    if field.exclude:
        query |= ~Q(**predicate)
    else:
        query |= Q(**predicate)
    return query
    
## Somewhere else in business logic:
field = filterset.filters[name]
value = filterset.data[name]
query = generate_query(field.field_name, field.lookup_expr, value)
filterset.qs.filter(query).count()  # 339
```

But furthermore, this also becomes unnecessary for the common case, because we can **just trust the filterset itself to do the proper filtering and completely obviate the need to reverse the query at all.**

Consider this input filter:

```python
filter_params = {"console_ports": True}
```

With properly configured filter fields, this will just work:

```python
DeviceFilterSet(filter_params).qs.count()  # 339
```

### Summary

- For the vast majority of cases where we have method filters, it’s for Boolean filters
- I am asserting for the common case **method filters are unnecessary technical debt and should be eliminated where better suited by proper use of filter field arguments**
- Reversibility may not necessarily be required, but by properly defining `field_name`, `lookup_expr`, and `exclude` on filter fields, **introspection becomes deterministic and reversible queries can be reliably generated as needed.**
- For exceptions such as `DeviceFilterSet.has_primary_ip` where it checks for both `Device.primary_ip4` OR `Device.primary_ip6`, method filters may still be necessary, however, they would be **the exception and not the norm.**
- The good news is that in the core there are not that many of these filter methods defined, but we also don’t want to see them continue to proliferate.
