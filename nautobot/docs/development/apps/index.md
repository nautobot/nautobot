# App Development

This documentation covers the development of custom apps (plugins) for Nautobot. Nautobot apps are essentially self-contained [Django applications](https://docs.djangoproject.com/en/stable/ref/applications/) which integrate with Nautobot to provide custom functionality. Since the development of Django applications is already very well-documented, this will only be covering the aspects that are specific to Nautobot.

Apps can [do a lot of different things](./index.md#capabilities), all of which will be covered in detail in this document.
Keep in mind that each piece of functionality is entirely optional. For example, if your app merely adds a piece of middleware or an API endpoint for existing data, there's no need to define any new models.

+/- 1.5.2
    The `nautobot.apps` namespace was added in Nautobot 1.5.2. If developing apps to be backwards-compatible with older versions of Nautobot, please refer to the app developer documentation of your required Nautobot version.

!!! tip
    The app detail view (`/plugins/installed-plugins/<plugin_name>/`, accessible to superusers via **Plugins -> Installed Plugins** in the navigation menu, then selecting a specific app) provides in-depth information about which features any installed app is implementing or making use of.

## Installing and Using Plugins

Plugins are packaged [Django](https://docs.djangoproject.com/) apps that can be installed alongside Nautobot to provide custom functionality not present in the core application. Plugins can introduce their own models and views, but cannot interfere with existing components. A Nautobot user may opt to install plugins provided by the community or build his or her own.

## Capabilities

The Nautobot plugin architecture allows for plugins to do any or all of the following:

### Extend the existing Nautobot UI

* **Add navigation menu items.** A plugin can extend the navigation menus with new links and buttons or even entirely new menus.
* **Add home page content.** A plugin can add custom items or custom panels to the Nautobot home page.
* **Add content to existing model detail views.** A plugin can inject custom HTML content within the view of a core Nautobot model. This content can appear in the left column, right column, or full width of the page, and can also include custom buttons at the top of the page.

+++ 1.2.0
    * **Add a banner.** A plugin can add a custom banner to the top of any appropriate views.

+++ 1.4.0
    * **Add extra tabs to existing model detail views.** A plugin can inject additional tabs which will appear at the end of the object detail tabs list.

### Extend and customize existing Nautobot functionality

* **Add custom validation logic to existing data models.** A plugin can provide additional logic to customize the rules for validating created/updated data records.
* **Provide Jobs.** A plugin can serve as a convenient way to package and install [Jobs](../../user-guide/platform-functionality/jobs/index.md).
* **Add additional Git data types.** A plugin can add support for processing additional types of data stored in a [Git repository](../../user-guide/platform-functionality/gitrepository.md).

+++ 1.1.0
    * **Register additional Jinja2 filters.** A plugin can define custom Jinja2 filters to be used in computed fields, webhooks, custom links, and export templates.

+++ 1.2.0
    * **Populate extensibility features in the database.** A plugin can add content to the Nautobot database when installed, such as automatically creating new custom fields, relationships, and so forth.

    * **Add additional secrets providers.** A plugin can add support for retrieving [Secret](../../user-guide/platform-functionality/secret.md) values from additional sources or external systems.

+++ 1.4.0
    * **Override already-defined views.** A plugin can define a view which can be set to override a view from the core set of views or another plugin's view.

### Add entirely new features

* **Add new data models.** A plugin can introduce one or more models to hold data. (A model is essentially a table in the SQL database.) These models can be integrated with core implementations of GraphQL, webhooks, logging, custom relationships, custom fields, and tags.
* **Add new URLs and views.** A plugin can register URLs under the `/plugins/` root path to provide browseable views (pages) for users.
* **Add new REST API endpoints.** A plugin can register URLs under the `/api/plugins/` root path to provide new REST API views.
* **Add custom middleware.** A plugin can provide and register custom Django middleware.

+++ 2.0.0
    * **Register data models for the global search.** A plugin's data models can easily be included in the top-level "global" search.

### Declare dependencies and requirements

* **Declare configuration parameters.** A plugin can define required, optional, and default configuration parameters within its unique namespace. Plugin configuration parameters are configurable under [`PLUGINS_CONFIG`](../../user-guide/administration/configuration/optional-settings.md#plugins_config) in `nautobot_config.py`.
* **Limit installation by Nautobot version.** A plugin can specify a minimum and/or maximum Nautobot version with which it is compatible.
* **Add additional Django dependencies.** A plugin can define additional Django application dependencies to require when the plugin is enabled.

## Limitations

Either by policy or by technical limitation, the interaction of plugins with Nautobot core is restricted in certain ways. A plugin may not:

* **Modify core models.** Plugins may not alter, remove, or override core Nautobot models in any way. This rule is in place to ensure the integrity of the core data model.
* **Register URLs outside the `/plugins` root.** All plugin URLs are restricted to this path to prevent path collisions with core or other plugins.
* **Override core templates.** Plugins can inject additional content where supported, but may not manipulate or remove core content.
* **Modify core settings.** A configuration registry is provided for plugins, however they cannot alter or delete the core configuration.
* **Disable core components.** Plugins are not permitted to disable or hide core Nautobot components.
