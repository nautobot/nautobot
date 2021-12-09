# Additional Jinja2 filters and Django Template helpers

## Introduction

Nautobot uses 2 template engines internally, Django Template and Jinja2.
Django Template is used to render the UI pages and Jinja2 is used for all extensibility features like: computed fields, custom links etc ...

!!! note
	Jinja2 and Django Template are very similar, the main difference between them is the syntax of the template. Historically, Django Template has been the go-to solution to generate webpage in Django and Jinja2 is the industry standard outside of Django.

Both Django Template and Jinja2 can be extended with a library of functions, called `filters`, that apply formatting or transformations to a provided input. Nautobot provides many built-in `filters`, including network specific `filters` from the [netutils library](https://netutils.readthedocs.io/en/latest/index.html).

## Netutils Filters

[Netutils](https://netutils.readthedocs.io/en/latest/) is an external library, maintained by Network to Code, that is focusing on providing a collection of functions for common network automation tasks.

Please [check the netutils documentation](https://netutils.readthedocs.io/en/latest/netutils/index.html) to see the list of available functions.

All functions in Netutils are available in Nautobot in both Jinja2 and Django Template.

## Nautobot Built-in Django Template helpers / Jinja2 filters

The Nautobot project also provides the following built-in `filters` that can be used in both Jinja2 and Django Template.

### as_range

Return a range of n items.

```no-highlight
# Django template
{% for i in record.parents|as_range %}
    <i class="mdi mdi-circle-small"></i>
{% endfor %}
```

### bettertitle

Alternative to the builtin title(); uppercases words without replacing letters that are already uppercase.

```no-highlight
{{ obj_type.name|bettertitle }}
```


### divide

Return x/y (rounded).

```no-highlight
# Django Template
{{ powerfeed.available_power|divide:3 }}VA

# Jinja
{{ powerfeed.available_power|divide(3) }}
```

### fgcolor

Return the ideal foreground color (block or white) given an arbitrary background color in RRGGBB format.

```no-highlight
color: {{ object.status.color|fgcolor }}
```

### get_docs

Render and return documentation for the specified model.

```no-highlight
{{ obj | get_docs }}
```


### get_item

Access a specific item/key in a dictionary. 

```no-highlight
# Django Template
{{ labels|get_item:key }}

# Jinja
{{ labels|get_item(key) }}
```


### has_one_or_more_perms

Return True if the user has *at least one* permissions in the list.

```no-highlight
# Django Template
{{ request.user|has_one_or_more_perms:panel_details.permissions }}

# Jinja
{{ request.user|has_one_or_more_perms(panel_details.permissions) }}
```

### has_perms

Return True if the user has *all* permissions in the list.

```no-highlight
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

```no-highlight
{{ speed_value | humanize_speed }}
```

### meta

Return the specified Meta attribute of a model. 

```no-highlight
{{ obj | meta('app_label') }}
```

### meters_to_feet

Convert a length from meters to feet.

```no-highlight
{{ meter_value | meters_to_feet }}
```


### percentage

Return x/y as a percentage.

```no-highlight
# Django Template
{{ powerfeed.available_power|percentage:total_power }}VA

# Jinja
{{ powerfeed.available_power|percentage(total_power) }}
```

### placeholder

Render a muted placeholder if value equates to False.

```no-highlight
{{ html | placeholder }}
```

### render_json

Render a dictionary as formatted JSON.

```no-highlight
{{ data | render_json }}
```

### render_markdown

Render text as Markdown.

```no-highlight
{{ text | render_markdown }}
```

### render_yaml

Render a dictionary as formatted YAML.

```no-highlight
{{ data | render_yaml }}
```

### settings_or_config

Get a value from Django settings (if specified) or Constance configuration (otherwise).

```no-highlight
{{ "RELEASE_CHECK_URL" | settings_or_config }}
```

### split

Split a string by the given value (default: comma)

```no-highlight
# Django Template
{{ string | split }}
{{ string | split:';' }}

# Jinja
{{ string | split }}
{{ string | split(';') }}
```

### tzoffset

Returns the hour offset of a given time zone using the current time.

```no-highlight
{{ object.time_zone|tzoffset }}
```

### validated_viewname

Return the view name for the given model and action if valid, or None if invalid.

```no-highlight
# Django Template
{{ obj | validated_viewname:'list' }}

# Jinja
{{ obj | validated_viewname('list') }}
```

### viewname

Return the view name for the given model and action. Does not perform any validation.

```no-highlight
# Django Template
{{ obj | viewname:'list' }}

# Jinja
{{ obj | viewname('list') }}
```




