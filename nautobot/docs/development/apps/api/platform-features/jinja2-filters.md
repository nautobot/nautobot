# Adding Jinja2 Filters

+++ 1.1.0

Apps can define custom Jinja2 filters to be used when rendering templates defined in computed fields. Check out the [official Jinja2 documentation](https://jinja.palletsprojects.com/en/3.0.x/api/#custom-filters) on how to create filter functions.

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
