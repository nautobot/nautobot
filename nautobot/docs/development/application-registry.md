# Application Registry

The registry is an in-memory data structure which houses various application-wide parameters, such as the list of enabled plugins. It is not exposed to the user and is not intended to be modified by any code outside of Nautobot core.

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

Definition of data types that can be provided by data source models (such as [Git repositories](../models/extras/gitrepository.md)). Implemented as a dictionary mapping the data source model name to a list of the types of data that it may contain and callback functions associated with those data types. The default mapping in Nautobot is currently:

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

Plugins may extend this dictionary with additional data sources and/or data types by calling `extras.registry.register_datasource_contents()` as desired.

### `homepage_layout`

+++ 1.2.0

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

### `model_features`

A dictionary of particular features (e.g. custom fields) mapped to the Nautobot models which support them, arranged by app. For example:

```python
{
    'custom_fields': {
        'circuits': ['provider', 'circuit'],
        'dcim': ['site', 'rack', 'devicetype', ...],
        ...
    },
    'webhooks': {
        ...
    },
    ...
}
```

### `nav_menu`

+++ 1.1.0

Navigation menu items provided by Nautobot applications. Each app may register its navbar configuration inside of the `nav_menu` dictionary using `navigation.py`. Tabs are stored in the top level moving down to groups, items and buttons. Tabs, groups and items can be modified by using the key values inside other application and plugins. The `nav_menu` dict should never be modified directly.

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

Plugin [custom validator classes](../plugins/development.md#implementing-custom-validators) that provide additional data model validation logic. Implemented as a dictionary mapping data model names to a list of `CustomValidator` subclasses, for example:

```python
{
    'circuits.circuit': [CircuitMustHaveDescriptionValidator],
    'dcim.site': [SiteMustHaveRegionValidator, SiteNameMustIncludeCountryCodeValidator],
}
```

### `plugin_graphql_types`

List of GraphQL Type objects that will be added to the GraphQL schema. GraphQL objects that are defined in a plugin will be automatically registered into this registry. An example:

```python
[
    <DjangoObjectType>, <DjangoObjectType>, <OptimizedDjangoObjectType>
]
```

### `plugin_jobs`

[Jobs](../additional-features/jobs.md) provided by plugins. A list of `Job` classes, for example:

```python
[
    demo_data_plugin.jobs.CreateDemoData,
    demo_data_plugin.jobs.DestroyDemoData,
    branch_creation_plugin.jobs.CreateNewSmallBranch,
    branch_creation_plugin.jobs.CreateNewMediumBranch,
    branch_creation_plugin.jobs.CreateNewLargeBranch,
]
```

### `plugin_template_extensions`

Plugin content that gets embedded into core Nautobot templates. The store comprises Nautobot models registered as dictionary keys, each pointing to a list of applicable template extension classes that exist. An example:

```python
{
    'dcim.site': [
        <TemplateExtension>, <TemplateExtension>, <TemplateExtension>,
    ],
    'dcim.rack': [
        <TemplateExtension>, <TemplateExtension>,
    ],
}
```
