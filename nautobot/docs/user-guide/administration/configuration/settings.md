---
render_macros: true
---

# Optional Configuration Settings

This document describes Nautobot-specific configuration settings that may be customized in your `nautobot_config.py`, or, in many cases, by configuration of appropriate environment variables. It also describes a number of common Django configuration settings that may also be customized similarly.

The [official Django documentation](https://docs.djangoproject.com/en/stable/ref/settings/) documents _all_ Django settings, and this document does not attempt to replace that documentation.

## Administratively Configurable Settings

A number of settings can alternatively be configured via the Nautobot Admin UI. To do so, these settings must **not** be defined in your `nautobot_config.py`, as any settings defined there will take precedence over any values defined in the Admin UI. Settings that are currently configurable via the Admin UI include:

<!-- pyml disable-num-lines 5 blanks-around-lists -->
{% for property, attrs in settings_schema.properties.items() %}
{% if attrs.is_constance_config|default(false) %}
* [`{{ property }}`](#{{ property|lower }})
{% endif %}
{% endfor %}

## Settings configurable in `nautobot_config.py`

### Extra Applications

A need may arise to allow the user to register additional settings. These will automatically apply
based on keynames prefixed with `EXTRA_` assuming the base key (the latter part of the setting name) is
of type list or tuple.

For example, to register additional `INSTALLED_APPS`, you would simply specify this in your custom
(user) configuration::

```python
EXTRA_INSTALLED_APPS = [
    'foo.bar',
]
```

This will ensure your default setting's `INSTALLED_APPS` do not have to be modified, and the user
can specify additional apps with ease.  Similarly, additional `MIDDLEWARE` can be added using `EXTRA_MIDDLEWARE`.

{% for property, attrs in settings_schema.properties.items() %}

---

### `{{ property }}`

{% if attrs.version_added|default(None) %}
+++ {{ attrs.version_added }}
{% endif %}

{% if attrs.default_literal|default(None) %}
**Default:**

{{ attrs.default_literal }}
{% else %}
{% with default = attrs.default|default(None) %}
**Default:**
{% if default is string %}`"{{ default }}"`
{% elif default is boolean %}`{{ default|title }}`
{% elif default is mapping and default != {} %}

```python
{{ default|pprint }}
```

{% else %}`{{ default }}`
{% endif %}
{% endwith %}
{% endif %}

{% if attrs.enum|default(None) %}
**Permitted Values:**

{% for enum in attrs.enum %}
* `{{ enum|pprint }}`
{% endfor %}
{% endif %}

{% if attrs.environment_variable|default(None) %}
**Environment Variable:** `{{ attrs.environment_variable }}`
{% elif attrs.environment_variables|default(None) %}
**Environment Variables:**

{% for environment_variable in attrs.environment_variables %}
* `{{ environment_variable }}`
{% endfor %}
{% elif attrs.properties|default(None) != None and attrs.properties.default|default(None) != None %}
{% for property_attrs in attrs.properties.default.properties.values() if property_attrs.environment_variable|default(None) or property_attrs.environment_variables|default(None) %}
{% if loop.first %}
**Environment Variables:**

{% endif %}
{% if property_attrs.environment_variable|default(None) %}
* `{{ property_attrs.environment_variable }}`
{% else %}
{% for environment_variable in property_attrs.environment_variables %}
* `{{ environment_variable }}`
{% endfor %}
{% endif %}
{% endfor %}
{% elif attrs.properties|default(None) != None %}
{% for property_attrs in attrs.properties.values() if property_attrs.environment_variable|default(None) or property_attrs.environment_variables|default(None) %}
{% if loop.first %}
**Environment Variables:**

{% endif %}
{% if property_attrs.environment_variable|default(None) %}
* `{{ property_attrs.environment_variable }}`
{% else %}
{% for environment_variable in property_attrs.environment_variables %}
* `{{ environment_variable }}`
{% endfor %}
{% endif %}
{% endfor %}
{% endif %}

{{ attrs.description|default("") }}

{{ attrs.details|default("") }}

{% if attrs.is_constance_config|default(false) %}
!!! tip
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.
{% endif %}

{% if attrs.see_also|default({}) %}
**See Also:**

{% for text, url in attrs.see_also.items() %}
* [ {{ text }} ]({{ url }})
{% endfor %}
{% endif %}

{% endfor %}

## Environment-Variable-Only Settings

!!! warning
    The following settings are **only** configurable as environment variables, and not via `nautobot_config.py` or similar.

---

### `GIT_SSL_NO_VERIFY`

Default: Unset

If you are using a self-signed git repository, you will need to set the environment variable `GIT_SSL_NO_VERIFY="1"`
in order for the repository to sync.

!!! warning
    This _must_ be specified as an environment variable. Setting it in `nautobot_config.py` will not have the desired effect.

---

### `NAUTOBOT_LOG_DEPRECATION_WARNINGS`

Default: `False`

This can be set to `True` to allow deprecation warnings raised by Nautobot to (additionally) be logged as `WARNING` level log messages. (Deprecation warnings are normally silent in Python, but can be enabled globally by [various means](https://docs.python.org/3/library/warnings.html) such as setting the `PYTHONWARNINGS` environment variable. However, doing so can be rather noisy, as it will also include warnings from within Django about various code in various package dependencies of Nautobot's, etc. This configuration setting allows a more targeted enablement of only warnings from within Nautobot itself, which can be useful when vetting various Nautobot Apps for future-proofness against upcoming changes to Nautobot.)

---

### `NAUTOBOT_ROOT`

Default: `~/.nautobot/`

The filesystem path to use to store Nautobot files (Jobs, uploaded images, Git repositories, etc.).

This setting is used internally in the core settings to provide default locations for [features that require file storage](index.md#file-storage), and the [default location of the `nautobot_config.py`](index.md#specifying-your-configuration).

!!! warning
    Do not override `NAUTOBOT_ROOT` in your `nautobot_config.py`. It will not work as expected. If you need to customize this setting, please always set the `NAUTOBOT_ROOT` environment variable.
