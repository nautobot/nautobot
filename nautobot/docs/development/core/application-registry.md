# Application Registry

The registry is an in-memory data structure which houses various application-wide parameters, such as the list of enabled Apps. It is not exposed to the user and is not intended to be modified by any code outside of Nautobot core.

The registry behaves essentially like a Python dictionary, with the notable exception that once a store (key) has been declared, it cannot be deleted or overwritten. The value of a store can, however, be modified; e.g. by appending a value to a list. Store values generally do not change once the application has been initialized.

The registry can be inspected by importing `registry` from `nautobot.extras.registry`. Page templates that need access to the registry can use the `registry` template tag to load it into the template context, for example:

```django
<!-- Load the "registry" template tag library -->
{% load registry %}
<!-- Load the registry into the template context as variable "registry"-->
{% registry %}
<!-- Use the registry variable in the template -->
{{ registry.datasource_contents }}
```

## Stores

### `datasource_contents`

Definition of data types that can be provided by data source models (such as [Git repositories](../../user-guide/platform-functionality/gitrepository.md)). Implemented as a dictionary mapping the data source model name to a list of the types of data that it may contain and callback functions associated with those data types. The default mapping in Nautobot is currently:

```python
{
    "extras.gitrepository": [
        DatasourceContent(
            name='config contexts',
            content_identifier='extras.configcontext',
            icon='mdi-code-json',
            callback=extras.datasources.git.refresh_git_config_contexts,
        ),
        DatasourceContent(
            name='jobs',
            content_identifier='extras.job',
            icon='mdi-script-text',
            callback=extras.datasources.git.refresh_git_jobs,
        ),
        DatasourceContent(
            name='export templates',
            content_identifier='extras.exporttemplate',
            icon='mdi-database-export',
            callback=extras.datasources.git.refresh_git_export_templates,
        ),
    ]
}
```

Apps may extend this dictionary with additional data sources and/or data types by calling `extras.registry.register_datasource_contents()` as desired.

### `homepage_layout`

A dictionary holding information about the layout of Nautobot's homepage. Each app may register homepage panels and items using objects from the generic app class. Each object has a weight attribute allowing the developer to define the position of the object.

``` python
{
    "panels": {
        "Panel 1" {
            "weight": 100,
            "items": {
                "Item 1": {
                    "description": "This is item 1",
                    "link": "example.link_1"
                    "model": Example,
                    "permissions": "example.view_link_1",
                    "weight": 100,
                },
                "Item 2": {
                    "description": "This is item 2",
                    "link": "example.link_2"
                    "model": Example,
                    "permissions": "example.view_link_2",
                    "weight": 200,
                }
            }
        }
        "Panel 2": {
            "weight": 200,
            "custom_template": "panel_example.html",
            "custom_data": {
                "example": example_callback_function,
            },
        }
    }
}
```

### `feature_models`

+++ 2.4.14

A dictionary of particular features (e.g. "graphql") mapped to the set of Nautobot model classes which support each such feature. For example:

```python
>>> from nautobot.extras.registry import registry
>>> registry["feature_models"]["graphql"]
[<class 'nautobot.extras.models.change_logging.ObjectChange'>, <class 'nautobot.extras.models.customfields.ComputedField'>, <class 'nautobot.extras.models.customfields.CustomFieldChoice'>, <class 'nautobot.extras.models.roles.Role'>, ...
```

Useful as an alternative to `model_features` ([below](#model_features)) for cases where direct access to the Django model classes is desired, such as in generating the GraphQL schema.

### `jobs`

+++ 2.2.3

A dictionary of registered [Job classes](../jobs/index.md), indexed by their [class path](../../user-guide/platform-functionality/jobs/models.md#understanding-job-class-paths). For example:

```python
{
    "nautobot.core.jobs.ExportObjectList": <class "nautobot.core.jobs.ExportObjectList">,
    "nautobot.core.jobs.GitRepositorySync": <class "nautobot.core.jobs.GitRepositorySync">,
    "nautobot.core.jobs.GitRepositoryDryRun": <class "nautobot.core.jobs.GitRepositoryDryRun">,
    "nautobot.core.jobs.ImportObjects": <class "nautobot.core.jobs.ImportObjects">,
    "example_app.jobs.ExampleDryRunJob": <class "example_app.jobs.ExampleDryRunJob">,
    "example_app.jobs.ExampleJob": <class "example_app.jobs.ExampleJob">,
    "example_app.jobs.ExampleHiddenJob": <class "example_app.jobs.ExampleHiddenJob">,
    "example_app.jobs.ExampleLoggingJob": <class "example_app.jobs.ExampleLoggingJob">,
    "example_app.jobs.ExampleFileInputOutputJob": <class "example_app.jobs.ExampleFileInputOutputJob">,
    "example_app.jobs.ExampleJobHookReceiver": <class "example_app.jobs.ExampleJobHookReceiver">,
    "example_app.jobs.ExampleSimpleJobButtonReceiver": <class "example_app.jobs.ExampleSimpleJobButtonReceiver">,
    "example_app.jobs.ExampleComplexJobButtonReceiver": <class "example_app.jobs.ExampleComplexJobButtonReceiver">
}
```

!!! caution
    This registry entry should be treated as a cache and as an implementation detail; in general you should prefer the use of the `nautobot.apps.get_jobs()` and/or `nautobot.apps.get_job()` APIs in order to retrieve specific Job classes.

### `model_features`

A dictionary of particular features (e.g. custom fields) mapped to the names of Nautobot models which support them, arranged by app. For example:

```python
{
    'custom_fields': {
        'circuits': ['provider', 'circuit'],
        'dcim': ['location', 'rack', 'devicetype', ...],
        ...
    },
    'webhooks': {
        ...
    },
    ...
}
```

For more information visit [model-features](model-features.md).

In cases where grouping by app is not important, and direct access to the Django model classes is desired, the `feature_models` registry entry ([above](#feature_models)) may be used as an alternative in recent versions of Nautobot.

### `nav_menu`

Navigation menu items provided by Nautobot applications. Each app may register its navbar configuration inside of the `nav_menu` dictionary using `navigation.py`. Tabs are stored in the top level moving down to groups, items and buttons. Tabs, groups and items can be modified by using the key values inside other core applications and Apps. The `nav_menu` dict should never be modified directly.

Example:

```python
{
    "tabs": {
        "tab_1": {
            "weight": 100,
            "permissions": [],
            "groups": {
                "group_1":{
                    "weight": 100,
                    "permissions": [],
                    "items": {
                        "item_link_1": {
                            "link_text": "Item 1",
                            "weight": 100,
                            "permissions": [],
                            "buttons": {
                                "button_1": {
                                    "button_class": "success",
                                    "icon_class": "mdi-plus-thick",
                                    "link": "button_link_1",
                                    "weight": 100,
                                    "permissions": [],
                                },
                                "button_2": {
                                    "button_class": "success",
                                    "icon_class": "mdi-plus-thick",
                                    "link": "button_link_2",
                                    "weight": 200,
                                    "permissions": [],
                                }
                            }
                        },
                        "item_link_2": {
                            "link_text": "Item 2",
                            "weight": 200,
                            "permissions": [],
                            "buttons": {
                                "button_1": {
                                    "button_class": "success",
                                    "icon_class": "mdi-plus-thick",
                                    "link": "button_link_1",
                                    "weight": 100,
                                    "permissions": [],
                                },
                                "button_2": {
                                    "button_class": "success",
                                    "icon_class": "mdi-plus-thick",
                                    "link": "button_link_2",
                                    "weight": 200,
                                    "permissions": [],
                                }
                            }
                        },
                    }
                }
            }
        }
    }
}
```

### `plugin_custom_validators`

App [custom validator classes](../apps/api/platform-features/custom-validators.md) that provide additional data model validation logic. Implemented as a dictionary mapping data model names to a list of `CustomValidator` subclasses, for example:

```python
{
    'circuits.circuit': [CircuitMustHaveDescriptionValidator],
    'dcim.location': [LocationMustHaveTenantValidator, LocationNameMustIncludeCountryCodeValidator],
}
```

### `plugin_graphql_types`

List of GraphQL Type objects that will be added to the GraphQL schema. GraphQL objects that are defined in an App will be automatically registered into this registry. An example:

```python
[
    <DjangoObjectType>, <DjangoObjectType>, <OptimizedDjangoObjectType>
]
```

--- 2.0.0
    The `plugin_jobs` registry has been replaced by [`nautobot.core.celery.register_jobs`](../jobs/index.md) which should be called at import time by any App that provides jobs.

### `plugin_template_extensions`

App content that gets embedded into core Nautobot templates. The store comprises Nautobot models registered as dictionary keys, each pointing to a list of applicable template extension classes that exist. An example:

```python
{
    'dcim.location': [
        <TemplateExtension>, <TemplateExtension>, <TemplateExtension>,
    ],
    'dcim.rack': [
        <TemplateExtension>, <TemplateExtension>,
    ],
}
```
