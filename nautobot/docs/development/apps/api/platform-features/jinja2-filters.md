# Adding Jinja2 Filters

Apps can define custom Jinja2 filters to be used when rendering user-authored templates, such as those in computed fields, custom links, export templates and job buttons. Check out the [official Jinja2 documentation](https://jinja.palletsprojects.com/en/3.0.x/api/#custom-filters) on how to create filter functions.

In the file that defines your filters (by default `jinja_filters.py`, but configurable in the `NautobotAppConfig` if desired), you must import the `library` module from the `django_jinja` library. Filters must then be decorated with `@library.filter`. See an example below that defines a filter called `leet_speak`.

```python
from django_jinja import library


@library.filter
def leet_speak(input_str):
    charset = {"a": "4", "e": "3", "l": "1", "o": "0", "s": "5", "t": "7"}
    output_str = ""
    for char in input_str:
        output_str += charset.get(char.lower(), char)
    return output_str
```

This filter will then be available for use in computed field templates like so:

```jinja2
{{ "HELLO WORLD" | leet_speak }}
```

The output of this template results in the string `"H3110 W0R1D"`.

## Writing Safe Filters

User-authored templates are rendered in a sandbox that refuses access to private attributes, to [sensitive fields](../../../core/sensitive-fields.md) such as API token keys and password hashes, and to the database internals behind the ORM. The sandbox only checks what the template itself does, though: its attribute lookups, item lookups and calls. A filter is ordinary Python that runs outside the sandbox, so nothing checks what it does with the values it is given. A filter that reads, queries or returns more than its template could have reached directly gives every template author that extra access.

Follow these rules for any filter that receives an object from the template.

**Do not look up a name supplied by the template yourself.** Calls such as `getattr(value, name)`, `operator.attrgetter(name)`, `queryset.filter(**{name: value})` or `queryset.values_list(name)`, where `name` is a filter argument, bypass the sandbox's checks entirely. If a filter needs to read an attribute named by the template, decorate it with Jinja's `pass_environment` and read the attribute through `environment.getattr()`, which applies the same checks as attribute access in the template:

```python
from django_jinja import library
from jinja2 import pass_environment


@library.filter
@pass_environment
def field_with_name(environment, obj, field_name):
    return f"{field_name}: {environment.getattr(obj, field_name)}"
```

With this filter, `{{ device|field_with_name("name") }}` renders the device's name, while a sensitive field such as a token's `key` raises a `SecurityError` and a private attribute such as `__dict__` renders a placeholder instead of its value.

**Do not serialize a whole object.** `model_to_dict()`, `vars()`, `__dict__` and REST API serializers include every loaded field, sensitive fields included. Name the fields you output.

**Do not return more than the template could reach.** Avoid returning an unrestricted queryset such as `Device.objects.all()`, which ignores the object permissions of the user the template is rendered for, or a model class, `_meta`, or a model `Field` object, which expose the ORM machinery behind the data.

**Do not write data.** The sandbox refuses calls a template makes to methods marked `alters_data`, but it cannot stop a filter from saving or deleting an object itself.

**Escape anything you mark safe.** Build HTML output with `django.utils.html.format_html()`, which escapes its arguments, rather than calling `mark_safe()` on a string containing values from the template or the database.
