# Additional Template Filters

## Introduction

Nautobot uses 2 template engines internally, Django Template and Jinja2. Django Template is used to render the UI pages and Jinja2 is used for features such as computed fields, custom links, export templates, etc.

!!! note
    Jinja2 and Django Template are very similar, the main difference between them is the syntax of the template. Historically, Django Template has been the go-to solution to generate webpage in Django and Jinja2 is the industry standard outside of Django.

Both Django Template and Jinja2 can be extended with a library of functions, called `filters`, that apply formatting or transformations to a provided input. Nautobot provides many built-in `filters`, including network specific `filters` from the [netutils library](https://netutils.readthedocs.io/en/latest/).

## Netutils Filters

[Netutils](https://netutils.readthedocs.io/en/latest/) is an external library, maintained by Network to Code, that is focusing on providing a collection of functions for common network automation tasks. Please [check the netutils documentation](https://netutils.readthedocs.io/en/latest/) to see the list of available functions.

These functions are available automatically in Jinja2 rendered by Nautobot. For example you could define a [computed field](./computedfield.md) on Circuit objects, using the Netutils `bits_to_name` function, to display the "Commit Rate" as a human-readable value by using the template code `{{ (obj.commit_rate * 1000) | bits_to_name }}`. (This particular example is contrived, as the Nautobot UI already humanizes the raw `commit_rate` value for display, but it demonstrates the kinds of things that these filters can be used for.)

In general the syntax for using a netutils filter in a Jinja2 template is something like `{{ arg1 | function_name }}` for functions that take a single argument, and `{{ arg1 | function_name(arg_name2=arg2, arg_name3=arg3) }}` for functions that take multiple arguments.

Netutils functions are also available in Django templates after using the `{% load netutils %}` directive in a template. The syntax to use these functions is then generally `{% function_name arg_name1=arg1 arg_name2=arg2 %}`.

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

### queryset_to_pks

Return all object's in a queryset UUIDs/pks as a string separated by a comma.

```django
# Django Template
{{ ip.tags.all | queryset_to_pks }}
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

### hyperlinked_email

+++ 2.2.0

Render an email address, if any, as a `mailto:` hyperlink, or render a placeholder if no email is given.

### hyperlinked_phone_number

+++ 2.2.0

Render a phone number string, if any, as a `tel:` hyperlink, or render a placeholder if no phone number is given.

### hyperlinked_object

Render and link to a Django model instance, if any, or render a placeholder if not.

Uses `object.display` if available, otherwise uses the string representation of the object.
If the object defines `get_absolute_url()` this will be used to hyperlink the displayed object;
additionally if there is an `object.description` this will be used as the title of the hyperlink.

```django
{{ device|hyperlinked_object }}
```

This filter also accepts an optional `field` parameter, which allows you to use a field other than `object.display` for the object representation if desired. For example, to display the object's `name` field instead:

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

### pluck

Extract values of given `key` from a `list` of dictionaries or objects to a separate list.

```django
{{ list|pluck:key }}
```

### pre_tag

Render a value within `<pre></pre>` tags to enable formatting.

```django title="template.html"
{{ some_html | pre_tag }}
```

```django title="script.py"
pre_tag(some_html)
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

+/- 2.2.0
    Unless `syntax_highlight=False` is specified, the returned string will be wrapped in a `<code class="language-json>` HTML tag to flag it for syntax highlighting by highlight.js.

+++ 2.3.0
    Added option for pretty print the output: `pretty_print=False`, default is False. If True the output will be wrapped in `<pre>` tags.

```django
{{ data | render_json }}
{{ data | render_json:False }} <!-- without syntax highlitning ->>
```

```django
json_pretty_printed = render_json(data, pretty_print=True)
```

### render_markdown

Render and sanitize Markdown text into HTML. A limited subset of HTML tags and attributes are permitted in the text as well; non-permitted HTML will be stripped from the output for security.

```django
{{ text | render_markdown }}
```

#### Permitted HTML Tags and Attributes

+++ 2.1.2

The set of permitted HTML tags is defined in `nautobot.core.constants.HTML_ALLOWED_TAGS`, and their permitted attributes are defined in `nautobot.core.constants.HTML_ALLOWED_ATTRIBUTES`. As of Nautobot 2.1.2 the following are permitted:

??? info "Full list of HTML tags and attributes"
    | Tag            | Attributes                                                           |
    | -------------- | -------------------------------------------------------------------- |
    | `<a>`          | `href`, `hreflang`                                                   |
    | `<abbr>`       |                                                                      |
    | `<acronym>`    |                                                                      |
    | `<b>`          |                                                                      |
    | `<bdi>`        |                                                                      |
    | `<bdo>`        | `dir`                                                                |
    | `<blockquote>` | `cite`                                                               |
    | `<br>`         |                                                                      |
    | `<caption>`    |                                                                      |
    | `<center>`     |                                                                      |
    | `<cite>`       |                                                                      |
    | `<code>`       |                                                                      |
    | `<col>`        | `align`, `char`, `charoff`, `span`                                   |
    | `<colgroup>`   | `align`, `char`, `charoff`, `span`                                   |
    | `<dd>`         |                                                                      |
    | `<del>`        | `cite`, `datetime`                                                   |
    | `<details>`    |                                                                      |
    | `<div>`        |                                                                      |
    | `<dl>`         |                                                                      |
    | `<dt>`         |                                                                      |
    | `<em>`         |                                                                      |
    | `<h1>`         |                                                                      |
    | `<h2>`         |                                                                      |
    | `<h3>`         |                                                                      |
    | `<h4>`         |                                                                      |
    | `<h5>`         |                                                                      |
    | `<h6>`         |                                                                      |
    | `<hgroup>`     |                                                                      |
    | `<hr>`         | `align`, `size`, `width`                                             |
    | `<i>`          |                                                                      |
    | `<img>`        | `align`, `alt`, `height`, `src`, `width`                             |
    | `<ins>`        | `cite`, `datetime`                                                   |
    | `<kbd>`        |                                                                      |
    | `<li>`         |                                                                      |
    | `<mark>`       |                                                                      |
    | `<ol>`         | `start`                                                              |
    | `<p>`          |                                                                      |
    | `<pre>`        |                                                                      |
    | `<q>`          | `cite`                                                               |
    | `<rp>`         |                                                                      |
    | `<rt>`         |                                                                      |
    | `<rtc>`        |                                                                      |
    | `<ruby>`       |                                                                      |
    | `<s>`          |                                                                      |
    | `<samp>`       |                                                                      |
    | `<small>`      |                                                                      |
    | `<span>`       |                                                                      |
    | `<strike>`     |                                                                      |
    | `<strong>`     |                                                                      |
    | `<sub>`        |                                                                      |
    | `<summary>`    |                                                                      |
    | `<sup>`        |                                                                      |
    | `<table>`      | `align`, `char`, `charoff`, `summary`                                |
    | `<tbody>`      | `align`, `char`, `charoff`                                           |
    | `<td>`         | `align`, `char`, `charoff`, `colspan`, `headers`, `rowspan`          |
    | `<th>`         | `align`, `char`, `charoff`, `colspan`, `headers`, `rowspan`, `scope` |
    | `<thead>`      | `align`, `char`, `charoff`                                           |
    | `<time>`       |                                                                      |
    | `<tr>`         | `align`, `char`, `charoff`                                           |
    | `<tt>`         |                                                                      |
    | `<u>`          |                                                                      |
    | `<ul>`         |                                                                      |
    | `<var>`        |                                                                      |
    | `<wbr>`        |                                                                      |

### render_uptime

Render an uptime value in seconds to a human readable value.
    1024768 => "11 days 20 hours 39 minutes"
    1 => "0 days 0 hours 0 minutes"
    3660 => "0 days 1 hour 1 minute"

```django
{{ 1024768 | render_uptime }}
```

### render_yaml

Render a dictionary as formatted YAML.

+/- 2.2.0
    Unless `syntax_highlight=False` is specified, the returned string will be wrapped in a `<code class="language-yaml>` HTML tag to flag it for syntax highlighting by highlight.js.

```django
{{ data | render_yaml }}
```

### settings_or_config

Get a value from Django settings (if specified) or Constance configuration (otherwise).

```django
{{ "RELEASE_CHECK_URL" | settings_or_config }}
```

+++ 2.0.0
    This filter now accepts an optional `app_name` parameter, which allows you to use this filter for Third-Party Nautobot Apps.

    ```django
    # Django Template
    {{ "SAMPLE_VARIABLE" | settings_or_config:"example_app" }}
    {{ "lowercase_example" | settings_or_config:"example_app" }}
    ```

### slugify

Slugify a string.

```django
# Django Template
{{ string | slugify }}

# Jinja
{{ string | slugify }}
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

### validated_api_viewname

Return the API view name for the given model and action if valid, or None if invalid.

```django
# Django Template
{{ obj | validated_api_viewname:'detail' }}

# Jinja
{{ obj | validated_api_viewname('detail') }}
```

### viewname

Return the view name for the given model and action. Does not perform any validation.

```django
# Django Template
{{ obj | viewname:'list' }}

# Jinja
{{ obj | viewname('list') }}
```
