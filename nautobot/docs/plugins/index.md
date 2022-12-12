# Installing and Using Plugins

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
* **Provide Jobs.** A plugin can serve as a convenient way to package and install [Jobs](../additional-features/jobs.md).
* **Add additional Git data types.** A plugin can add support for processing additional types of data stored in a [Git repository](../models/extras/gitrepository.md).

+++ 1.1.0
    * **Register additional Jinja2 filters.** A plugin can define custom Jinja2 filters to be used in computed fields, webhooks, custom links, and export templates.

+++ 1.2.0
    * **Populate extensibility features in the database.** A plugin can add content to the Nautobot database when installed, such as automatically creating new custom fields, relationships, and so forth.

    * **Add additional secrets providers.** A plugin can add support for retrieving [Secret](../models/extras/secret.md) values from additional sources or external systems.

+++ 1.4.0
    * **Override already-defined views.** A plugin can define a view which can be set to override a view from the core set of views or another plugin's view.

### Add entirely new features

* **Add new data models.** A plugin can introduce one or more models to hold data. (A model is essentially a table in the SQL database.) These models can be integrated with core implementations of GraphQL, webhooks, logging, custom relationships, custom fields, and tags.
* **Add new URLs and views.** A plugin can register URLs under the `/plugins/` root path to provide browseable views (pages) for users.
* **Add new REST API endpoints.** A plugin can register URLs under the `/api/plugins/` root path to provide new REST API views.
* **Add custom middleware.** A plugin can provide and register custom Django middleware.

### Declare dependencies and requirements

* **Declare configuration parameters.** A plugin can define required, optional, and default configuration parameters within its unique namespace. Plugin configuration parameters are configurable under [`PLUGINS_CONFIG`](../configuration/optional-settings.md#plugins_config) in `nautobot_config.py`.
* **Limit installation by Nautobot version.** A plugin can specify a minimum and/or maximum Nautobot version with which it is compatible.
* **Add additional Django dependencies.** A plugin can define additional Django application dependencies to require when the plugin is enabled.

Details on how to implement any of these features are described in the plugin [development](./development.md) documentation.

## Limitations

Either by policy or by technical limitation, the interaction of plugins with Nautobot core is restricted in certain ways. A plugin may not:

* **Modify core models.** Plugins may not alter, remove, or override core Nautobot models in any way. This rule is in place to ensure the integrity of the core data model.
* **Register URLs outside the `/plugins` root.** All plugin URLs are restricted to this path to prevent path collisions with core or other plugins.
* **Override core templates.** Plugins can inject additional content where supported, but may not manipulate or remove core content.
* **Modify core settings.** A configuration registry is provided for plugins, however they cannot alter or delete the core configuration.
* **Disable core components.** Plugins are not permitted to disable or hide core Nautobot components.

## Installing Plugins

The instructions below detail the process for installing and enabling a Nautobot plugin.

You must be **absolutely** sure to install the plugin within Nautobot's virtual environment.

!!! note
    If you installed Nautobot in a production environment, you'll want to sudo to the nautobot user first using `sudo -iu nautobot`.

### Install the Package

Download and install the plugin package per its installation instructions. Plugins published via PyPI are typically installed using `pip3`.

```no-highlight
pip3 install <package>
```

Alternatively, if you're or installing a plugin from from a local source copy, you may wish to install the plugin manually by running `python setup.py install`.

If you are developing a plugin and want to install it only temporarily, run `python setup.py develop` instead.

### Enable the Plugin

In your `nautobot_config.py`, add the plugin's name to the `PLUGINS` list:

```python
PLUGINS = [
    'plugin_name',
]
```

### Configure the Plugin

If the plugin requires any configuration, define it in `nautobot_config.py` under the `PLUGINS_CONFIG` parameter. The available configuration parameters should be detailed in the plugin's README file.

```python
PLUGINS_CONFIG = {
    'plugin_name': {
        'foo': 'bar',
        'buzz': 'bazz'
    }
}
```

### Run `nautobot-server post_upgrade`

After installing or upgrading a plugin, you should always run [`nautobot-server post_upgrade`](../administration/nautobot-server.md#post_upgrade). This command will ensure that any necessary post-installation tasks are run, for example:

* Migrating the database to include any new or updated data models from the plugin
* Collecting any static files provided by the plugin
* Etc.

```no-highlight
# nautobot-server post_upgrade
Performing database migrations...
Operations to perform:
  Apply all migrations: admin, auth, circuits, contenttypes, db, dcim, extras, ipam,
nautobot_plugin_example, sessions, social_django, taggit, tenancy, users, virtualization
Running migrations:
  No migrations to apply.

Generating cable paths...
Found no missing circuit termination paths; skipping
Found no missing console port paths; skipping
Found no missing console server port paths; skipping
Found no missing interface paths; skipping
Found no missing power feed paths; skipping
Found no missing power outlet paths; skipping
Found no missing power port paths; skipping
Finished.

Collecting static files...

0 static files copied to '/opt/nautobot/static', 972 unmodified.

Removing stale content types...

Removing expired sessions...

Invalidating cache...

```

### Restart the WSGI Service

Restart the WSGI service to load the new plugin:

```no-highlight
# sudo systemctl restart nautobot nautobot-worker
```

### Verify that the Plugin is Installed

In the Nautobot UI, navigate to **Plugins -> Installed Plugins**. The newly installed plugin should appear in the displayed table if everything is configured correctly. You can also click on the plugin's name in this table to view more detailed information about this plugin.
