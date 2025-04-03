# Adding and Updating Nautobot Settings

Best practices when adding, updating, and deprecating/removing Nautobot configuration settings.

## Consider Constance

If the setting is one that would be desirable to configure at run time rather than install time, and the nature of the setting is such that it *can* be changed at run time without requiring a server reload or similar operations to fully take effect, consider implementing it as a [`django-constance`](https://django-constance.readthedocs.io/en/latest/) setting.

### Constance Advantages

* Constance-enabled settings can be configured through the UI by any user with admin privileges, rather than requiring filesystem access to the Nautobot installation to modify.
* Constance-enabled settings changes can take effect with zero downtime, as no server restart is required.
* Constance-enabled settings can still be set in `nautobot_config.py` as a way to "lock" the configuration and disable the ability for admin users to modify it through the UI.

### Constance Drawbacks

* Constance-enabled settings must be definable through the UI, so advanced settings patterns like callable functions and other Python objects can't generally be implemented through Constance.
* Many native Django settings can't be implemented through Constance as they typically require a process restart to fully take effect.
* Care needs to be taken when implementing environment variable support for settings that are also Constance-enabled - you must check for `"<variable_name>" in os.environ` before setting a variable in the Nautobot settings, so that it remains unset (and therefore manageable by Constance) if the environment variable isn't specified, rather than the simpler common pattern of just `SETTING = os.getenv("<variable_name>", <default value>)` used elsewhere in the settings.

## Environment Variable Support

For all settings where it's feasible to do so, you should make sure that it's configurable via environment variable as an alternative to directly editing `nautobot_config.py`. Exceptions would be for settings that cannot easily be defined as an environment variable string, such as Python functions, complex dicts, etc.

The environment variable should typically be named `NAUTOBOT_<setting_name>` unless there is a *strong* existing convention in other tools for a different name.

For Constance-enabled settings, the general pattern would be:

```python title="nautobot/core/settings.py"
if "NAUTOBOT_MY_SETTING" in os.environ and os.environ["NAUTOBOT_MY_SETTING"] != "":
    MY_SETTING = os.environ["NAUTOBOT_MY_SETTING"]
```

and in `CONSTANCE_CONFIG`:

```python title="nautobot/core/settings.py"
CONSTANCE_CONFIG = {
    "MY_SETTING": ConstanceConfigItem(
        default="<default_value>",
        help_text="<user-facing string>",
    ),
}
```

For non-Constance-enabled settings, the pattern is simpler:

```python title="nautobot/core/settings.py"
MY_SETTING = os.getenv("NAUTOBOT_MY_SETTING", "<default_value>")
```

## Documentation

As of Nautobot 2.2.0, settings documentation is automatically generated from the contents of `nautobot/core/settings.yaml`. This document describes a JSON Schema for Nautobot settings, with a number of custom extensions to support richer documentation. In general, documentation for a typical string-based setting will take the following form:

```yaml title="nautobot/core/settings.yaml"
properties:
  MY_SETTING:
    default: "some_default"
    description: "My setting. One to three sentences here at most."
    details: "<optional additional details, examples, caveats, etc.>"
    environment_variable: "NAUTOBOT_MY_SETTING"
    see_also:
      "Documentation on example.com": "http://docs.example.com/my-setting"
    type: "string"
    version_added: "2.2.0"
```

As with a standard JSON Schema, it's possible to define other data types (`"type": "array"`, `"type": "object"`, etc.) and those will have other available/expected keys. Refer to documents like [Creating your first schema](https://json-schema.org/learn/getting-started-step-by-step) for details if you're less familiar with JSON Schema conventions.

The special keys added specifically for documentation are as follows:

* `details`: additional text beyond what's included in `description`, including examples, caveats, etc.
* `default_literal`: The `default` must be the actual JSON-serializable value that is the default value for this setting. If the default value is not sufficiently self-explanatory, or is not JSON-serializable (such as a Python function), you can define a **string** for this key that will be rendered directly into the documentation in place of the `default`.
* `environment_variable`: The environment variable that can be used to define this setting. Omit if not supported.
* `is_constance_setting`: Set to `true` if this setting can be managed through Constance. Can be omitted if false.
* `is_required_setting`: Set to `true` if this setting should be documented in `required-settings.md`; omit to default to `optional-settings.md`.
* `see_also`: Optional dictionary of `"<link text>": "<link URL>"` entries that direct the user to other pages (local or remote) for additional details or context.
* `version_added`: Nautobot version number where support for this setting was first added.

Markdown rendering is supported for the `description`, `details`, and `default_literal` fields. The `see_also` field is also rendered as Markdown, but only the link text should include any markdown formatting.

!!! info
    Markdown is *technically* supported in other fields, but it's not recommended to use it outside of the fields above as it may not render as expected in all contexts.

### Technical Details of Settings Documentation

The `optional-settings.md` and `required-settings.md` files are rendered as Jinja2 templates via [`Mkdocs-Macros`](https://mkdocs-macros-plugin.readthedocs.io/en/latest/). The file `nautobot/docs/macros.py` is responsible for loading `settings.yaml` into the template context for rendering. `mkdocs.yml` instructs Mkdocs-Macros to run that file at documentation rendering time. The macros and templating are *not* enabled for all documentation by default - instead, only the files with `render_macros: true` in their headers will be templated.
