---
render_macros: true
---

# Optional Configuration Settings

This document describes Nautobot-specific configuration settings that may be customized in your `nautobot_config.py`, or, in many cases, by configuration of appropriate environment variables. It also describes a number of common Django configuration settings that may also be customized similarly.

The [official Django documentation](https://docs.djangoproject.com/en/stable/ref/settings/) documents _all_ Django settings, and this document does not attempt to replace that documentation.

## Administratively Configurable Settings

<!-- markdownlint-disable blanks-around-lists -->

+++ 1.2.0

A number of settings can alternatively be configured via the Nautobot Admin UI. To do so, these settings must **not** be defined in your `nautobot_config.py`, as any settings defined there will take precedence over any values defined in the Admin UI. Settings that are currently configurable via the Admin UI include:

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

{% with header="###", required=false %}

{% include "/user-guide/administration/configuration/render-settings-fragment.j2" %}

{% endwith %}

<!-- markdownlint-enable blanks-around-lists -->

## Environment-Variable-Only Settings

!!! warning
    The following settings are **only** configurable as environment variables, and not via `nautobot_config.py` or similar.

---

### GIT_SSL_NO_VERIFY

Default: Unset

If you are using a self-signed git repository, you will need to set the environment variable `GIT_SSL_NO_VERIFY="1"`
in order for the repository to sync.

!!! warning
    This _must_ be specified as an environment variable. Setting it in `nautobot_config.py` will not have the desired effect.

---

### NAUTOBOT_LOG_DEPRECATION_WARNINGS

+++ 1.5.2

+/- 1.5.3
    This was previously available as a config file setting but changed to environment-variable only. Also `DEBUG = True` will no longer work to log deprecation warnings.

Default: `False`

This can be set to `True` to allow deprecation warnings raised by Nautobot to (additionally) be logged as `WARNING` level log messages. (Deprecation warnings are normally silent in Python, but can be enabled globally by [various means](https://docs.python.org/3/library/warnings.html) such as setting the `PYTHONWARNINGS` environment variable. However, doing so can be rather noisy, as it will also include warnings from within Django about various code in various package dependencies of Nautobot's, etc. This configuration setting allows a more targeted enablement of only warnings from within Nautobot itself, which can be useful when vetting various Nautobot Apps for future-proofness against upcoming changes to Nautobot.)

---

### NAUTOBOT_ROOT

Default: `~/.nautobot/`

The filesystem path to use to store Nautobot files (Jobs, uploaded images, Git repositories, etc.).

This setting is used internally in the core settings to provide default locations for [features that require file storage](index.md#file-storage), and the [default location of the `nautobot_config.py`](index.md#specifying-your-configuration).

!!! warning
    Do not override `NAUTOBOT_ROOT` in your `nautobot_config.py`. It will not work as expected. If you need to customize this setting, please always set the `NAUTOBOT_ROOT` environment variable.
