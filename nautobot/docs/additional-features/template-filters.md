# Additional Template Filters

## Introduction

Nautobot uses 2 template engines internally, Django Template and Jinja2. Django Template is used to render the UI pages and Jinja2 is used for features such as computed fields, custom links, export templates, etc.

!!! note
    Jinja2 and Django Template are very similar, the main difference between them is the syntax of the template. Historically, Django Template has been the go-to solution to generate webpage in Django and Jinja2 is the industry standard outside of Django.

Both Django Template and Jinja2 can be extended with a library of functions, called `filters`, that apply formatting or transformations to a provided input. Nautobot provides many built-in `filters`, including network specific `filters` from the [netutils library](https://netutils.readthedocs.io/en/latest/index.html).

## Netutils Filters

+++ 1.2.0

[Netutils](https://netutils.readthedocs.io/en/latest/) is an external library, maintained by Network to Code, that is focusing on providing a collection of functions for common network automation tasks.

Please [check the netutils documentation](https://netutils.readthedocs.io/en/latest/netutils/index.html) to see the list of available functions.

All functions in Netutils are available in Nautobot in both Jinja2 filters and Django Template.

## Nautobot Built-In Filters

The Nautobot project also provides the following built-in `filters` that can be used in both Jinja2 and Django Template.

### as_range

Given a list of *n* items, return a corresponding range of *n* integers.

```django
# Django template
{% for i in record.parents|as_range %}
    <i class="mdi mdi-circle-small"></i>
{% endfor %}
```

### bettertitle

Alternative to the built-in `title` filter; capitalizes words without replacing letters that are already uppercase.

For example, `title("IP address") == "Ip Address"`, while `bettertitle("IP address") == "IP Address"`.

```django
{{ obj_type.name|bettertitle }}
```

### divide

Return x/y (rounded).

```django
# Django Template
{{ powerfeed.available_power|divide:3 }}VA

# Jinja
{{ powerfeed.available_power|divide(3) }}
```

### fgcolor

Return the ideal foreground color (black `"#000000"` or white `"#ffffff"`) given an arbitrary background color in RRGGBB format.

```django
color: {{ object.status.color|fgcolor }}
```

### get_docs_url

Return the static URL of the documentation for the specified model.

```django
{{ obj | get_docs_url }}
```

### get_item

Access a specific item/key in a dictionary.

```django
# Django Template
{{ labels|get_item:key }}

# Jinja
{{ labels|get_item(key) }}
```

### has_one_or_more_perms

Return True if the user has *at least one* of the permissions in the list.

```django
# Django Template
{{ request.user|has_one_or_more_perms:panel_details.permissions }}

# Jinja
{{ request.user|has_one_or_more_perms(panel_details.permissions) }}
```

### has_perms

Return True if the user has *all* permissions in the list.

```django
# Django Template
{{ request.user|has_perms:group_item_details.permissions }}

# Jinja
{{ request.user|has_perms(group_item_details.permissions) }}
```

### humanize_speed

Humanize speeds given in Kbps.
    1544 => "1.544 Mbps"
    100000 => "100 Mbps"
    10000000 => "10 Gbps"

```django
{{ speed_value | humanize_speed }}
```

### hyperlinked_object

+++ 1.4.0

Render and link to a Django model instance, if any, or render a placeholder if not.

Uses `object.display` if available, otherwise uses the string representation of the object.
If the object defines `get_absolute_url()` this will be used to hyperlink the displayed object;
additionally if there is an `object.description` this will be used as the title of the hyperlink.

```django
{{ device|hyperlinked_object }}
```

+++ 1.5.0
    This filter now accepts an optional `field` parameter, which allows you to use a field other than `object.display` for the object representation if desired. For example, to display the object's `name` field instead:

    ```django
    # Django Template
    {{ location|hyperlinked_object:"name" }}

    # Jinja
    {{ location|hyperlinked_object("name") }}
    ```

### meta

Return the specified Meta attribute of a model.

```django
{{ obj | meta('app_label') }}
```

### meters_to_feet

Convert a length from meters to feet.

```django
{{ meter_value | meters_to_feet }}
```

### percentage

Return x/y as a percentage.

```django
# Django Template
{{ powerfeed.available_power|percentage:total_power }}VA

# Jinja
{{ powerfeed.available_power|percentage(total_power) }}
```

### placeholder

Render a muted placeholder (`<span class="text-muted">&mdash;</span>`) if value is falsey, else render the provided value.

```django
{{ html | placeholder }}
```

### render_boolean

Render HTML from a computed boolean value.

If value is (for example) a non-empty string or True or a non-zero number, this renders `<span class="text-success"><i class="mdi mdi-check-bold" title="Yes"></i></span>`

If value is (for example) "" or 0 or False, this renders `<span class="text-danger"><i class="mdi mdi-close-thick" title="No"></i></span>`

If value is None this renders `<span class="text-muted">&mdash;</span>`

```django
{{ value | render_boolean }}
```

### render_json

Render a dictionary as formatted JSON.

```django
{{ data | render_json }}
```

### render_markdown

Render text as Markdown.

```django
{{ text | render_markdown }}
```

### render_yaml

Render a dictionary as formatted YAML.

```django
{{ data | render_yaml }}
```

### settings_or_config

Get a value from Django settings (if specified) or Constance configuration (otherwise).

```django
{{ "RELEASE_CHECK_URL" | settings_or_config }}
```

### split

Split a string by the given value (default: comma)

```django
# Django Template
{{ string | split }}
{{ string | split:';' }}

# Jinja
{{ string | split }}
{{ string | split(';') }}
```

### tzoffset

Returns the hour offset of a given time zone using the current time.

```django
{{ object.time_zone|tzoffset }}
```

### validated_viewname

Return the view name for the given model and action if valid, or None if invalid.

```django
# Django Template
{{ obj | validated_viewname:'list' }}

# Jinja
{{ obj | validated_viewname('list') }}
```

### viewname

Return the view name for the given model and action. Does not perform any validation.

```django
# Django Template
{{ obj | viewname:'list' }}

# Jinja
{{ obj | viewname('list') }}
```
