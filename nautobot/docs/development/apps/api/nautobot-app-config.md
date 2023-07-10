# NautobotAppConfig

The `NautobotAppConfig` class is a Nautobot-specific wrapper around Django's built-in [`AppConfig`](https://docs.djangoproject.com/en/stable/ref/applications/) class. It is used to declare Nautobot app functionality within a Python package. Each app should provide its own subclass, defining its name, metadata, and default and required configuration parameters. An example is below:

```python
from nautobot.apps import NautobotAppConfig

class AnimalSoundsConfig(NautobotAppConfig):
    name = 'nautobot_animal_sounds'
    verbose_name = 'Animal Sounds'
    description = 'An example app for development purposes'
    version = '0.1'
    author = 'Bob Jones'
    author_email = 'bob@example.com'
    base_url = 'animal-sounds'
    required_settings = []
    default_settings = {
        'loud': False
    }

config = AnimalSoundsConfig
```

Nautobot looks for the `config` variable within an app's `__init__.py` to load its configuration. Typically, this will be set to the `NautobotAppConfig` subclass, but you may wish to dynamically generate a `NautobotAppConfig` class based on environment variables or other factors.

## Required NautobotAppConfig Attributes

| Name | Description |
| ---- | ----------- |
| `author` | Name of app's author |
| `author_email` | Author's public email address |
| `description` | Brief description of the app's purpose |
| `name` | Raw app name; same as the app's source directory |
| `verbose_name` | Human-friendly name for the app |
| `version` | Current release ([semantic versioning](https://semver.org/) is encouraged) |

## Optional NautobotAppConfig Attributes

| Name | Default | Description |
| ---- | ------- | ----------- |
| `base_url` | Same as specified `name` | Base path to use for app URLs |
| `config_view_name` | `None` | [URL name](#adding-links-to-the-installed-apps-view) for a "configuration" view defined by this app |
| `default_settings` | `{}` | A dictionary of configuration parameters and their default values |
| `home_view_name` | `None` | [URL name](#adding-links-to-the-installed-apps-view) for a "home" or "dashboard" view defined by this app |
| `docs_view_name` | `None` | [URL name](#adding-links-to-the-installed-apps-view) for a "documentation" view defined by this app |
| `installed_apps` | `[]` | A list of additional Django application dependencies to automatically enable when the app is activated (you must still make sure these underlying dependent libraries are installed) |
| `max_version` | `None` | Maximum version of Nautobot with which the app is compatible |
| `middleware` | `[]` | A list of middleware classes to append after Nautobot's built-in middleware |
| `min_version` | `None` | Minimum version of Nautobot with which the app is compatible |
| `required_settings` | `[]` | A list of any configuration parameters that **must** be defined by the user |
| `searchable_models` | `[]` | A list of model names to include in the global Nautobot search |
| `constance_config` | `{}` | [Django Constance](#adding-database-backed-config) configuration parameters for settings. |

+++ 2.0.0
    Support for the `searchable_models` and `constance_config` attributes were added.

--- 2.0.0
    Support for `caching_config` was removed with the removal of `django-cacheops`.

!!! note
    All `required_settings` must be configured in `PLUGINS_CONFIG` in `nautobot_config.py` before the app can be used.

!!! warning
    If a configuration parameter is listed in either of `required_settings` or `constance_config`, and also in `default_settings`, the default setting will be ignored.

## NautobotAppConfig Code Location Attributes

The following `NautobotAppConfig` attributes can be configured to customize where Nautobot will look to locate various pieces of app code. In most cases you will not need to change these, but they are provided as options in case your app has a non-standard organizational structure.

!!! info
    As used below, a "dotted path" is the combination of a Python module path within the app and the name of a variable within that module. For example, `"template_content.template_extensions"` refers to a variable named `template_extensions` inside a `template_content` module located at the root of the app.

| Name | Default | Description |
| ---- | ------- | ----------- |
| `banner_function` | `"banner.banner"` | Dotted path to a function that can render a custom [banner](#adding-a-banner) |
| `custom_validators` | `"custom_validators.custom_validators"` | Dotted path to a list of [custom validator classes](#implementing-custom-validators) |
| `datasource_contents` | `"datasources.datasource_contents"` | Dotted path to a list of [datasource (Git, etc.) content types](#loading-data-from-a-git-repository) to register |
| `graphql_types` | `graphql.types.graphql_types` | Dotted path to a list of [GraphQL type classes](#creating-your-own-graphql-type-object) |
| `homepage_layout` | `"homepage.layout"` | Dotted path to a list of [home page items](#adding-home-page-content) provided by the app |
| `jinja_filters` | `"jinja_filters"` | Path to a module that contains [Jinja2 filters](#adding-jinja2-filters) to be registered |
| `jobs` | `"jobs.jobs"` | Dotted path to a list of [Job classes](#including-jobs) |
| `menu_items` | `"navigation.menu_items"` | Dotted path to a list of [navigation menu items](#adding-navigation-menu-items) provided by the app |
| `secrets_providers` | `"secrets.secrets_providers"` | Dotted path to a list of [secrets providers](#implementing-secrets-providers) in the app |
| `template_extensions` | `"template_content.template_extensions"` | Dotted path to a list of [template extension classes](#extending-object-detail-views) |
