# Best Practices

While there are many different development interfaces in Nautobot that each expose unique functionality, there are a common set of a best practices that have broad applicability to users and developers alike. This includes elements of writing Jobs, Plugins, and scripts for execution through `nautobot-server nbshell`.

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

## Data Model Best Practices

### Model Existence in the Database

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

### Model Validation

Django offers several places and mechanism in which to exert data and model validation. All model specific validation should occur within the model's `clean()` method or field specific validators. This ensures the validation logic runs and is consistent through the various Nautobot interfaces (Web UI, REST API, ORM, etc).

#### Consuming Model Validation

Django places specific separation between validation and the saving of an instance and this means it is a common Django pattern to make explicit calls first to a model instance's `clean()`/`full_clean()` methods and then the `save()` method. Calling only the `save()` method **does not** automatically enforce validation and may lead to data integrity issues.

Nautobot provides a convenience method that both enforces model validation and saves the instance in a single call to `validated_save()`. Any model which inherits from `nautobot.core.models.BaseModel` has this method available. This includes all core models and it is recommended that all new Nautobot models and plugin-provided models also inherit from `BaseModel` or one of its descendants such as `nautobot.core.models.generics.OrganizationalModel` or `nautobot.core.models.generics.PrimaryModel`.

The intended audience for the `validated_save()` convenience method is Job authors and anyone writing scripts for, or interacting with the ORM directly through the `nautobot-server nbshell` command. It is generally not recommended however, to use `validated_save()` as a blanket replacement for the `save()` method in the core of Nautobot.

During execution, should model validation fail, `validated_save()` will raise `django.core.exceptions.ValidationError` in the normal Django fashion.

### Field Naming in Data Models

Model field names **must** always follow the following conventions:

- Use lowercase letters, numbers, and underscores only
- Separate words with underscores for readability/clarity
- For foreign keys and their corresponding reverse-relations, match the `verbose_name` or `verbose_name_plural` of the related model

Instead of:

```python
Rack.group
DeviceType.consoleserverporttemplates
Device.ipaddress_set
```

Use:

```python
Rack.rack_group
DeviceType.console_server_port_templates
Device.ip_addresses
```

#### Foreign Key `related_name` for Abstract Model Classes

+/- 2.0.0

If an abstract model class defines a foreign key to a concrete model class, Django's default `related_name` functionality doesn't provide great options - the best you could normally do for a `related_name` on a `ForeignKey` from an abstract base class, for example, would be `"%(class)ss"` (potentially resulting in related names like `"devices"` or, less optimally, `"ipaddresss"`) or `"%(app_label)s_%(class)s_related"` (resulting in related names like `"dcim_device_related"` or `"ipam_ipaddress_related"`, which while at least consistent, are rather clunky).

Fortunately, Nautobot provides a `ForeignKeyWithAutoRelatedName` model field class that solves this problem. On any concrete subclass of an abstract base class that uses `ForeignKeyWithAutoRelatedName` instead of `ForeignKey`, the `related_name` will be automatically set based on the concrete subclass's `verbose_name_plural` value (which in many cases Django is clever enough to automatically derive from the class name, but can also be specified directly on your `Meta` class if needed). Thus, if your model's `verbose_name_plural` is "IP addresses", the `related_name` for the `ForeignKeyWithAutoRelatedName` will automatically be `ip_addresses`.

!!! note
    At this time we _only_ recommend using `ForeignKeyWithAutoRelatedName` for this abstract model case; for foreign keys between concrete models, it's still best to use a regular `ForeignKey` with an explicitly specified `related_name` string.

Nautobot doesn't currently have a similar class provided for `ManyToManyField`; in this case you'll probably be best, for now, to just use `related_name="%(app_label)s_%(class)s_related"` for any abstract base class's ManyToManyField if a reverse relation is desired.

### Slug Field

+/- 2.0.0
    Models should generally **not** have a `slug` field, and should use the model's primary key (UUID) in URL patterns for both the UI and the REST API. All models should have a human-friendly natural key, either a single unique field (typically `name`) or a minimally complex unique-together set of fields (such as `DeviceType`'s `(manufacturer, model)`).

For models that have a strong use case for a `slug` or similar field (such as `GitRepository.slug`, which defines a module name for Python imports from the repository, or `CustomField.key`, which defines the key used to access this field in the REST API and GraphQL), Nautobot provides the `AutoSlugField` to handle automatically populating the `slug` field from another field(s). Generally speaking model slugs should be populated from the `name` field. Below is an example on defining the `slug` field.

```python
from django.db import models

from nautobot.core.models.fields import AutoSlugField
from nautobot.core.models.generics import PrimaryModel

class ExampleModel(PrimaryModel):
    name = models.CharField(max_length=100, unique=True)
    slug = AutoSlugField(populate_from='name')
```

## Getting URL Routes

When developing new models a need often arises to retrieve a reversible route for a model to access it in either the web UI or the REST API. When this time comes, you **must** use `nautobot.core.utils.lookup.get_route_for_model`. You **must not** write your own logic to construct route names.

+/- 2.0.0
    `get_route_for_model` was moved from the `nautobot.utilities.utils` module to `nautobot.core.utils.lookup`.

```python
from nautobot.core.utils.lookup import get_route_for_model
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

## REST API Best Practices

- Generally the field names on a REST API serializer should correspond directly to the field names on the model, subject to the best practices described above.
- For related count fields, use the related model name suffixed with `_count`.

Instead of:

```python
Interface.count_ipaddresses
```

Use:

```python
Interface.ip_address_count
```

## Filtering Models with FilterSets

The following best practices must be considered when establishing new `FilterSet` classes for model classes.

### Mapping Model Fields to Filters

- FilterSets **must** inherit from `nautobot.extras.filters.NautobotFilterSet` (which inherits from `nautobot.core.filters.BaseFilterSet`)
    - This affords that automatically generated lookup expressions (`ic`, `nic`, `iew`, `niew`, etc.) are always included
    - This also asserts that the correct underlying `Form` class that maps the generated form field types and widgets will be included

- FilterSets **must** publish all model fields from a model, including related fields.
    - All fields should be provided using `Meta.fields = "__all__"` and this would be preferable for the first and common case as it requires the least maintenance and overhead and asserts parity between the model fields and the filterset filters.
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

### Filter Naming and Definition

- Custom filter definitions **must not** shadow the name of an existing model field if it is also changing the type.
    - For example (before Nautobot 2.0.0), `DeviceFilterSet.interfaces` was a `BooleanFilter` that was shadowing the `Device.interfaces` related manager. This caused problems with automatic introspection of the filterset and was fixed in 2.0 by introducing a separate `has_interfaces` filter and changing the `interfaces` filter to show the correct behavior. Shadowing database fields with a filter field of a different type **must** be avoided in all new filters.

- In Nautobot 2.0 and later, for all foreign-key related fields and their corresponding reverse-relations:
    - If there is no appropriate single field that could be used as a natural key (e.g. a globally-unique `name` or `slug`), then the default filtering behavior for this field (using `django_filters.ModelMultipleChoiceFilter`) can be used for now, until [issue 2875](https://github.com/nautobot/nautobot/issues/2875) is implemented to allow for the use of multiple fields with `NaturalKeyOrPKMultipleChoiceFilter`.
    - Otherwise, the field **must** be shadowed with a Nautobot `NaturalKeyOrPKMultipleChoiceFilter` which will automatically try to lookup by UUID or `name` depending on the value of the incoming argument (e.g. UUID string vs. name string).
        - This provides an advantage over the default `django_filters.ModelMultipleChoiceFilter` which only supports a UUID (`pk`) value as an input.
    - Fields that use `slug` or some other natural key field instead of `name` can set the `to_field_name` argument on `NaturalKeyOrPKMultipleChoiceFilter` accordingly.

```python
# Typical usage
from nautobot.core.filters import NaturalKeyOrPKMultipleChoiceFilter

    provider = NaturalKeyOrPKMultipleChoiceFilter(
        queryset=Provider.objects.all(),
        to_field_name="name",
        label="Provider (name or ID)",
    )
```

```python
# Optionally, using the to_field_name argument to look up by "slug" instead of by "name"
from nautobot.core.filters import NaturalKeyOrPKMultipleChoiceFilter

    git_repository = NaturalKeyOrPKMultipleChoiceFilter(
        to_field_name="slug",
        queryset=GitRepository.objects.all(),
        label="Git repository (slug or ID)",
    )
```

- Boolean filters for membership **must** be named with `has_{related_name}` (e.g. `has_interfaces`) and should use the `RelatedMembershipBooleanFilter` filter class.
    - One exception to this naming convention may be made for Boolean filters for identity, which **may** be named `is_{name}` instead (e.g. `is_virtual_chassis_member` versus `has_virtual_chassis`). Although this is semantically identical to `has_` filters, there may be occasions where naming the filter `is_` would be more intuitive.

```python
from nautobot.core.filters import RelatedMembershipBooleanFilter

    has_interfaces = RelatedMembershipBooleanFilter(
        field_name="interfaces",
        label="Has interfaces",
    )

    is_virtual_chassis_member = RelatedMembershipBooleanFilter(
        field_name="virtual_chassis",
        label="Is a virtual chassis member",
    )
```

- Whenever possible otherwise, filter names **must** correspond exactly to the underlying model field they are referencing.

- If there's necessarily a mismatch between the filter name and the model field name (such as in the `has_*` and `is_*` cases described above):
    1. The suffix component of the filter name **must** correspond exactly to the underlying model field name (for example, for a field of `console_port_templates`, the filter must be `has_console_port_templates`, **not** `has_consoleporttemplates` or `has_console_ports`).
    2. The filter itself **must** declare [`field_name`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#field-name) to identify unambiguously the underlying model field.

- Filters **must** be declared using the appropriate lookup expression (`lookup_expr`) if any other expression than `exact` (the default) is required.

- Filters **must** be declared using [`exclude=True`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#exclude) if a queryset `.exclude()` is required to be called vs. queryset `.filter()` which is the default when the filter default `exclude=False` is passed through. If you require `Foo.objects.exclude()`, you must pass `exclude=True` instead of defining a filterset method to explicitly hard-code such a query.

For example, for a boolean filter that checks to see whether the `console_ports` field is null if False and not null if True, you would need to combine all of the above rules, resulting in:

```python
   has_console_ports = BooleanFilter(field_name="console_ports", lookup_expr="isnull", exclude=True)
```

!!! tip
    For boolean filters on related memberships (`has_*`/`is_*`), you should always use `RelatedMembershipBooleanFilter`, which is a `BooleanFilter` subclass that defaults to the correct `lookup_expr` and `exclude` values for this common case.

- Filters **must** be declared using [`distinct=True`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#distinct) if a queryset `.distinct()`is required to be called on the queryset.

- Filters **must not** be set to be required using `required=True`

- Filter methods defined using the [`method=`](https://django-filter.readthedocs.io/en/stable/ref/filters.html#method) keyword argument **may only be used as a last resort** (see below) when correct usage of `field_name`, `lookup_expr`, `exclude`, or other filter keyword arguments do not suffice. In other words: filter methods should used as the exception and not the rule.

- Use of [`filter_overrides`](https://django-filter.readthedocs.io/en/stable/ref/filterset.html#filter-overrides) **must be considered** in cases where more-specific class-local overrides. The need may occasionally arise to change certain filter-level arguments used for filter generation, such such as changing a filter class, or customizing a UI widget. Any `extra` arguments are sent to the filter as keyword arguments at instance creation time. (Hint: `extra` must be a callable)

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

So while this filter definition could be improved like so, there is still no way to know what is going on in the method body:

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

Except that it stops there because of the method body. Here are the problems:

- There's no way to identify either of the field names required here
- The `name` that is incoming to the method is the filter name as defined (`pass_through_ports` in this case) does not map to an actual model field
- So the filter can be introspected for `lookup_expr` value using `self.filters[name].lookup_expr`, but it would have to be assumed that applies to both fields.
- Same with `exclude` (`self.filters[name].exclude`)

It would be better to just eliminate `pass_through_ports=True` entirely in exchange for `front_ports=True&rear_ports=True` (current) or `has_frontports=True&has_rearports=True` (future).

#### Generating Reversible Q Objects

With consistent and proper use of filter field arguments when defining them on a filterset, a query could be constructed using the `field_name` and `lookup_expr` values. For example:

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
    Using `NautobotUIViewSet` for [plugin development](../apps/api/views/nautobotuiviewset.md) is strongly recommended.
