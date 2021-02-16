# Application Registry

The registry is an in-memory data structure which houses various application-wide parameters, such as the list of enabled plugins. It is not exposed to the user and is not intended to be modified by any code outside of NetBox core.

The registry behaves essentially like a Python dictionary, with the notable exception that once a store (key) has been declared, it cannot be deleted or overwritten. The value of a store can, however, be modified; e.g. by appending a value to a list. Store values generally do not change once the application has been initialized.

The registry can be inspected by importing `registry` from `extras.registry`.

## Stores

### `datasource_contents`

Definition of data types that can be provided by data source models (such as [Git repositories](../models/extras/gitrepository.md)). Implemented as a dictionary mapping the data source model name to a list of the types of data that it may contain and callback functions associated with those data types. The default mapping in NetBox is currently:

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

### `model_features`

A dictionary of particular features (e.g. custom fields) mapped to the NetBox models which support them, arranged by app. For example:

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

### `plugin_custom_validators`

Plugin [custom validator classes](../plugins/development.md#implementing-custom-validators) that provide additional data model validation logic. Implemented as a dictionary mapping data model names to a list of `PluginCustomValidator` subclasses, for example:

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
    <DjangoObjectType>, <DjangoObjectType>
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

### `plugin_menu_items`

Navigation menu items provided by NetBox plugins. Each plugin is registered as a key with the list of menu items it provides. An example:

```python
{
    'Plugin A': (
        <MenuItem>, <MenuItem>, <MenuItem>,
    ),
    'Plugin B': (
        <MenuItem>, <MenuItem>, <MenuItem>,
    ),
}
```

### `plugin_template_extensions`

Plugin content that gets embedded into core NetBox templates. The store comprises NetBox models registered as dictionary keys, each pointing to a list of applicable template extension classes that exist. An example:

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
