# Plugin Development

This documentation covers the development of custom plugins for Nautobot. Plugins are essentially self-contained [Django applications](https://docs.djangoproject.com/en/stable/ref/applications/) which integrate with Nautobot to provide custom functionality. Since the development of Django applications is already very well-documented, we'll only be covering the aspects that are specific to Nautobot.

Plugins can do a lot, including:

* Create Django models to store data in the database
* Add custom validation logic to apply to existing data models
* Provide their own "pages" (views) in the web user interface
* Provide [Jobs](../additional-features/jobs.md)
* Inject template content and navigation links
* Establish their own REST API endpoints
* Add custom request/response middleware

However, keep in mind that each piece of functionality is entirely optional. For example, if your plugin merely adds a piece of middleware or an API endpoint for existing data, there's no need to define any new models.

## Initial Setup

### Plugin Structure

Although the specific structure of a plugin is largely left to the discretion of its authors, a Nautobot plugin that makes use of all available plugin features described in this document would look something like this:

```no-highlight
plugin_name/
  - plugin_name/
    - __init__.py           # required
    - admin.py              # Django Admin Interface
    - api/
      - serializers.py      # REST API Model serializers
      - urls.py             # REST API URL patterns
      - views.py            # REST API view sets
    - custom_validators.py  # Custom Validators
    - datasources.py        # Loading Data from a Git Repository
    - graphql/
      - types.py            # GraphQL Type Objects
    - jobs.py               # Job classes
    - middleware.py         # Request/response middleware
    - migrations/
      - 0001_initial.py     # Database Models
    - models.py             # Database Models
    - navigation.py         # Navigation Menu Items
    - template_content.py   # Extending Core Templates
    - templates/
      - plugin_name/
        - *.html            # UI content templates
    - urls.py               # UI URL Patterns
    - views.py              # UI Views
  - README.md
  - setup.py                # required
```

The top level is the project root. Immediately within the root should exist several items:

* `setup.py` - This is a standard installation script used to install the plugin package within the Python environment.
* `README.md` - A brief introduction to your plugin, how to install and configure it, where to find help, and any other pertinent information. It is recommended to write README files using a markup language such as Markdown.
* The plugin source directory, with the same name as your plugin.

The plugin source directory contains all of the actual Python code and other resources used by your plugin. Its structure is left to the author's discretion, however it is recommended to follow best practices as outlined in the [Django documentation](https://docs.djangoproject.com/en/stable/intro/reusable-apps/). At a minimum, this directory **must** contain an `__init__.py` file containing an instance of Nautobot's `PluginConfig` class.

### Create setup.py

The`setup.py` script is the [setup script](https://docs.python.org/3.6/distutils/setupscript.html) we'll use to install our plugin once it's finished. The primary function of this script is to call the setuptools library's `setup()` function to create a Python distribution package. We can pass a number of keyword arguments to inform the package creation as well as to provide metadata about the plugin.

An example `setup.py` is below:

```python
from setuptools import find_packages, setup

setup(
    name='nautobot-animal-sounds',
    version='0.1',
    description='An example Nautobot plugin',
    url='https://github.com/nautobot/nautobot-animal-sounds',
    author='Jeremy Stretch',
    license='Apache 2.0',
    install_requires=[],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
```

Many of these are self-explanatory, but for more information, see the [setuptools documentation](https://setuptools.readthedocs.io/en/latest/setuptools.html).

!!! note
    `zip_safe=False` is **required** as the current plugin iteration is not zip safe due to upstream python issue [issue19699](https://bugs.python.org/issue19699)

### Define a PluginConfig

The `PluginConfig` class is a Nautobot-specific wrapper around Django's built-in [`AppConfig`](https://docs.djangoproject.com/en/stable/ref/applications/) class. It is used to declare Nautobot plugin functionality within a Python package. Each plugin should provide its own subclass, defining its name, metadata, and default and required configuration parameters. An example is below:

```python
from nautobot.extras.plugins import PluginConfig

class AnimalSoundsConfig(PluginConfig):
    name = 'nautobot_animal_sounds'
    verbose_name = 'Animal Sounds'
    description = 'An example plugin for development purposes'
    version = '0.1'
    author = 'Jeremy Stretch'
    author_email = 'author@example.com'
    base_url = 'animal-sounds'
    required_settings = []
    default_settings = {
        'loud': False
    }

config = AnimalSoundsConfig
```

Nautobot looks for the `config` variable within a plugin's `__init__.py` to load its configuration. Typically, this will be set to the `PluginConfig` subclass, but you may wish to dynamically generate a `PluginConfig` class based on environment variables or other factors.

#### PluginConfig Attributes

The configurable attributes for a `PluginConfig` are listed below in alphabetical order.

| Name | Description |
| ---- | ----------- |
| `author` | Name of plugin's author |
| `author_email` | Author's public email address |
| `base_url` | (Optional) Base path to use for plugin URLs. If not specified, the project's `name` will be used. |
| `caching_config` | Plugin-specific cache configuration |
| `custom_validators` | The dotted path to the list of custom validator classes (default: `custom_validators.custom_validators`) |
| `datasource_contents` | The dotted path to the list of datasource (Git, etc.) content types to register (default: `datasources.datasource_contents`) |
| `default_settings` | A dictionary of configuration parameters and their default values |
| `description` | Brief description of the plugin's purpose |
| `graphql_types` | The dotted path to the list of GraphQL type classes (default: `graphql.graphql_types)` |
| `installed_apps` | A list of additional Django application dependencies to automatically enable when the plugin is activated (you must still make sure these underlying dependent libraries are installed) |
| `jobs` | The dotted path to the list of Job classes (default: `jobs.jobs`) |
| `max_version` | Maximum version of Nautobot with which the plugin is compatible |
| `menu_items` | The dotted path to the list of menu items provided by the plugin (default: `navigation.menu_items`) |
| `middleware` | A list of middleware classes to append after Nautobot's built-in middleware |
| `min_version` | Minimum version of Nautobot with which the plugin is compatible |
| `name` | Raw plugin name; same as the plugin's source directory |
| `required_settings` | A list of any configuration parameters that **must** be defined by the user |
| `template_extensions` | The dotted path to the list of template extension classes (default: `template_content.template_extensions`) |
| `verbose_name` | Human-friendly name for the plugin |
| `version` | Current release ([semantic versioning](https://semver.org/) is encouraged) |

All required settings must be configured by the user. If a configuration parameter is listed in both `required_settings` and `default_settings`, the default setting will be ignored.

### Install the Plugin for Development

To ease development, it is recommended to go ahead and install the plugin at this point using setuptools' `develop` mode. This will create symbolic links within your Python environment to the plugin development directory. Call `setup.py` from the plugin's root directory with the `develop` argument (instead of `install`):

```no-highlight
$ python setup.py develop
```

## Database Models

If your plugin introduces a new type of object in Nautobot, you'll probably want to create a [Django model](https://docs.djangoproject.com/en/stable/topics/db/models/) for it. A model is essentially a Python representation of a database table, with attributes that represent individual columns. Model instances can be created, manipulated, and deleted using [queries](https://docs.djangoproject.com/en/stable/topics/db/queries/). Models must be defined within a file named `models.py`.

It is highly recommended to have plugin models inherit from at least `nautobot.core.models.BaseModel` which provides base functionality and convenience methods common to all models.

Below is an example `models.py` file containing a model with two character fields:

```python
# models.py
from django.db import models


class Animal(models.Model):
    """Base model for animals."""

    name = models.CharField(max_length=50)
    sound = models.CharField(max_length=50)

    def __str__(self):
        return self.name
```

Once you have defined the model(s) for your plugin, you'll need to create the database schema migrations. A migration file is essentially a set of instructions for manipulating the PostgreSQL database to support your new model, or to alter existing models. Creating migrations can usually be done automatically using Django's `makemigrations` management command.

!!! note
    A plugin must be installed before it can be used with Django management commands. If you skipped this step above, run `python setup.py develop` from the plugin's root directory.

```no-highlight
$ nautobot-server makemigrations nautobot_animal_sounds
Migrations for 'nautobot_animal_sounds':
  /home/jstretch/animal_sounds/nautobot_animal_sounds/migrations/0001_initial.py
    - Create model Animal
```

Next, we can apply the migration to the database with the `migrate` command:

```no-highlight
$ nautobot-server migrate nautobot_animal_sounds
Operations to perform:
  Apply all migrations: nautobot_animal_sounds
Running migrations:
  Applying nautobot_animal_sounds.0001_initial... OK
```

For more background on schema migrations, see the [Django documentation](https://docs.djangoproject.com/en/stable/topics/migrations/).

### Using the Django Admin Interface

Plugins can optionally expose their models via Django's built-in [administrative interface](https://docs.djangoproject.com/en/stable/ref/contrib/admin/). This can greatly improve troubleshooting ability, particularly during development. To expose a model, simply register it using Django's `admin.register()` function. An example `admin.py` file for the above model is shown below:

```python
# admin.py
from django.contrib import admin

from .models import Animal


@admin.register(Animal)
class AnimalAdmin(admin.ModelAdmin):
    list_display = ('name', 'sound')
```

This will display the plugin and its model in the admin UI. Staff users can create, change, and delete model instances via the admin UI without needing to create a custom view.

![Nautobot plugin in the admin UI](../media/plugins/plugin_admin_ui.png)

### Register your model in the GraphQL interface

Plugins can optionally expose their models via the GraphQL interface to allow the models to be part of the Graph and to be queried easily. There are two ways to expose a model to the graphql interface.
* By using the `extras_features` decorator
* By creating your own GraphQL Type object and registering it within `graphql/types.py` of your plugin (decorator is not needed)

#### Using the `extras_features` decorator for "graphql"

To expose a model, simply register it using the `extras_features("graphql")` decorator. Nautobot will automatically create a GraphQL `Type` object and try to convert the model automatically to GraphQL. If a `FilterSet` is available at `<app_name>.filters.<ModelName>FilterSet` Nautobot will automatically use the filterset to generate search parameters for the list views.

```python
# models.py
from django.db import models

from nautobot.extras.utils import extras_features


@extras_features("graphql")
class Animal(models.Model):
    """Base model for animals."""

    name = models.CharField(max_length=50)
    sound = models.CharField(max_length=50)

    def __str__(self):
        return self.name
```

#### Create your own GraphQL Type object

In some cases, usually when an object is using some Generic Relationship, the default GraphQL `Type` object generated by the `extras_features` decorator may not work as the developer intends, and it will be preferable to provide custom GraphQL types. A GraphQL `Type` object can be created and registered to the GraphQL interface by defining the type in the `graphql_types` variables in `graphql/types.py` file within the plugin. The object must inherit from `DjangoObjectType` and must follow the [standard defined by graphene-django](https://docs.graphene-python.org/projects/django/en/latest/queries/).

All GraphQL `Type` objects registered will be automatically modify to support some built-in features:
- Add support for permissions
- Add support for tags
- Add support for custom fields

```python
# graphql/types.py
from graphene_django import DjangoObjectType

from nautobot_animal_sounds.models import Animal


class AnimalType(DjangoObjectType):
    """GraphQL Type for Animal"""

    class Meta:
        model = Animal
        exclude = ["sound"]


graphql_types = [AnimalType]
```

## Web UI Views

If your plugin needs its own page or pages in the Nautobot web UI, you'll need to define views. A view is a particular page tied to a URL within Nautobot, which renders content using a template. Views are typically defined in `views.py`, and URL patterns in `urls.py`. As an example, let's write a view which displays a random animal and the sound it makes. First, we'll create the view in `views.py`:

```python
# views.py
from django.shortcuts import render
from django.views.generic import View

from .models import Animal


class RandomAnimalView(View):
    """Display a randomly-selected Animal."""

    def get(self, request):
        animal = Animal.objects.order_by('?').first()
        return render(request, 'nautobot_animal_sounds/animal.html', {
            'animal': animal,
        })
```

This view retrieves a random animal from the database and and passes it as a context variable when rendering a template named `animal.html`, which doesn't exist yet. To create this template, first create a directory named `templates/nautobot_animal_sounds/` within the plugin source directory. (We use the plugin's name as a subdirectory to guard against naming collisions with other plugins.) Then, create a template named `animal.html` as described below.

### Extending the Base Template

Nautobot provides a base template to ensure a consistent user experience, which plugins can extend with their own content. This template includes four content blocks:

* `title` - The page title
* `header` - The upper portion of the page
* `content` - The main page body
* `javascript` - A section at the end of the page for including Javascript code

For more information on how template blocks work, consult the [Django documentation](https://docs.djangoproject.com/en/stable/ref/templates/builtins/#block).

```jinja2
{# templates/nautobot_animal_sounds/animal.html #}
{% extends 'base.html' %}

{% block content %}
    {% with config=settings.PLUGINS_CONFIG.nautobot_animal_sounds %}
        <h2 class="text-center" style="margin-top: 200px">
            {% if animal %}
                The {{ animal.name|lower }} says
                {% if config.loud %}
                    {{ animal.sound|upper }}!
                {% else %}
                    {{ animal.sound }}
                {% endif %}
            {% else %}
                No animals have been created yet!
            {% endif %}
        </h2>
    {% endwith %}
{% endblock %}

```

The first line of the template instructs Django to extend the Nautobot base template and inject our custom content within its `content` block.

!!! note
    Django renders templates with its own custom [template language](https://docs.djangoproject.com/en/stable/topics/templates/#the-django-template-language). This template language is very similar to Jinja2, however there are some important differences to keep in mind.

Finally, to make the view accessible to users, we need to register a URL for it. We do this in `urls.py` by defining a `urlpatterns` variable containing a list of paths.

```python
# urls.py
from django.urls import path

from . import views


urlpatterns = [
    path('random/', views.RandomAnimalView.as_view(), name='random_animal'),
]
```

A URL pattern has three components:

* `route` - The unique portion of the URL dedicated to this view
* `view` - The view itself
* `name` - A short name used to identify the URL path internally

This makes our view accessible at the URL `/plugins/animal-sounds/random/`. (Remember, our `AnimalSoundsConfig` class sets our plugin's base URL to `animal-sounds`.) Viewing this URL should show the base Nautobot template with our custom content inside it.

## REST API Endpoints

Plugins can declare custom endpoints on Nautobot's REST API to retrieve or manipulate models or other data. These behave very similarly to views, except that instead of rendering arbitrary content using a template, data is returned in JSON format using a serializer. Nautobot uses the [Django REST Framework](https://www.django-rest-framework.org/), which makes writing API serializers and views very simple.

First, we'll create a serializer for our `Animal` model, in `api/serializers.py`:

```python
# api/serializers.py
from rest_framework.serializers import ModelSerializer

from nautobot_animal_sounds.models import Animal


class AnimalSerializer(ModelSerializer):
    """API serializer for interacting with Animal objects."""

    class Meta:
        model = Animal
        fields = ('id', 'name', 'sound')
```

Next, we'll create a generic API view set that allows basic CRUD (create, read, update, and delete) operations for Animal instances. This is defined in `api/views.py`:

```python
# api/views.py
from rest_framework.viewsets import ModelViewSet

from nautobot_animal_sounds.models import Animal
from .serializers import AnimalSerializer


class AnimalViewSet(ModelViewSet):
    """API viewset for interacting with Animal objects."""

    queryset = Animal.objects.all()
    serializer_class = AnimalSerializer
```

Finally, we'll register a URL for our endpoint in `api/urls.py`. This file **must** define a variable named `urlpatterns`.

```python
# api/urls.py
from rest_framework import routers

from .views import AnimalViewSet


router = routers.DefaultRouter()
router.register('animals', AnimalViewSet)
urlpatterns = router.urls
```

With these three components in place, we can request `/api/plugins/animal-sounds/animals/` to retrieve a list of all Animal objects defined.

![Nautobot REST API plugin endpoint](../media/plugins/plugin_rest_api_endpoint.png)

!!! warning
    This example is provided as a minimal reference implementation only. It does not address authentication, performance, or the myriad of other concerns that plugin authors should have.

## Navigation Menu Items

To make its views easily accessible to users, a plugin can inject items in Nautobot's navigation menu under the "Plugins" header. Menu items are added by defining a list of PluginMenuItem instances. By default, this should be a variable named `menu_items` in the file `navigation.py`. An example is shown below.

```python
# navigation.py
from nautobot.extras.plugins import PluginMenuButton, PluginMenuItem
from nautobot.utilities.choices import ButtonColorChoices


menu_items = (
    PluginMenuItem(
        link='plugins:nautobot_animal_sounds:random_animal',
        link_text='Random sound',
        buttons=(
            PluginMenuButton('home', 'Button A', 'mdi mdi-help-circle', ButtonColorChoices.BLUE),
            PluginMenuButton('home', 'Button B', 'mdi mdi-alert', ButtonColorChoices.GREEN),
        )
    ),
)
```

A `PluginMenuItem` has the following attributes:

* `link` - The name of the URL path to which this menu item links
* `link_text` - The text presented to the user
* `permissions` - A list of permissions required to display this link (optional)
* `buttons` - An iterable of PluginMenuButton instances to display (optional)

A `PluginMenuButton` has the following attributes:

* `link` - The name of the URL path to which this button links
* `title` - The tooltip text (displayed when the mouse hovers over the button)
* `icon_class` - Button icon CSS classes (Nautobot currently supports [Material Design Icons](https://materialdesignicons.com))
* `color` - One of the choices provided by `ButtonColorChoices` (optional)
* `permissions` - A list of permissions required to display this button (optional)

!!! note
    Any buttons associated within a menu item will be shown only if the user has permission to view the link, regardless of what permissions are set on the buttons.

## Extending Core Templates

Plugins can inject custom content into certain areas of the detail views of applicable models. This is accomplished by subclassing `PluginTemplateExtension`, designating a particular Nautobot model, and defining the desired methods to render custom content. Four methods are available:

* `left_page()` - Inject content on the left side of the page
* `right_page()` - Inject content on the right side of the page
* `full_width_page()` - Inject content across the entire bottom of the page
* `buttons()` - Add buttons to the top of the page

Additionally, a `render()` method is available for convenience. This method accepts the name of a template to render, and any additional context data you want to pass. Its use is optional, however.

When a PluginTemplateExtension is instantiated, context data is assigned to `self.context`. Available data include:

* `object` - The object being viewed
* `request` - The current request
* `settings` - Global Nautobot settings
* `config` - Plugin-specific configuration parameters

For example, accessing `{{ request.user }}` within a template will return the current user.

Declared subclasses should be gathered into a list or tuple for integration with Nautobot. By default, Nautobot looks for an iterable named `template_extensions` within a `template_content.py` file. (This can be overridden by setting `template_extensions` to a custom value on the plugin's `PluginConfig`.) An example is below.

```python
# template_content.py
from nautobot.extras.plugins import PluginTemplateExtension

from .models import Animal


class SiteAnimalCount(PluginTemplateExtension):
    """Template extension to display animal count on the right side of the page."""

    model = 'dcim.site'

    def right_page(self):
        return self.render('nautobot_animal_sounds/inc/animal_count.html', extra_context={
            'animal_count': Animal.objects.count(),
        })


template_extensions = [SiteAnimalCount]
```

## Including Jobs

Plugins can provide [jobs](../additional-features/jobs.md) to take advantage of all the built-in functionality provided by that feature (user input forms, background execution, results logging and reporting, etc.). This plugin feature is provided for convenience; it remains possible to instead install jobs manually into [`JOBS_ROOT`](../configuration/optional-settings.md#jobs_root) or provide them as part of a [Git repository](../models/extras/gitrepository.md) if desired.

By default, for each plugin, Nautobot looks for an iterable named `jobs` within a `jobs.py` file. (This can be overridden by setting `jobs` to a custom value on the plugin's `PluginConfig`.) A brief example is below; for more details on job design and implementation, refer to the jobs feature documentation.

```python
# jobs.py
from nautobot.extras.jobs import Job


class CreateDevices(Job):
    ...


class DeviceConnectionsReport(Job):
    ...


class DeviceIPsReport(Job):
    ...


jobs = [CreateDevices, DeviceConnectionsReport, DeviceIPsReport]
```

## Implementing Custom Validators

Plugins can register custom validator classes which implement model validation logic to be executed during a model's `clean()` method. Like template extensions, custom validators are registered to a single model and offer a method which plugin authors override to implement their validation logic. This is accomplished by subclassing `PluginCustomValidator` and implementing the `clean()` method.

Plugin authors must raise `django.core.exceptions.ValidationError` within the `clean()` method to trigger validation error messages which are propgated to the user and prevent saving of the model instance. A convenience method `validation_error()` may be used to simplify this process. Raising a `ValidationError` is no different than vanilla Django, and the convenience method will simply pass the provided message through to the exception.

When a PluginCustomValidator is instantiated, the model instance is assigned to context dictionary using the `object` key, much like PluginTemplateExtensions. E.g. `self.context['object']`.

Declared subclasses should be gathered into a list or tuple for integration with Nautobot. By default, Nautobot looks for an iterable named `custom_validators` within a `custom_validators.py` file. (This can be overridden by setting `custom_validators` to a custom value on the plugin's `PluginConfig`.) An example is below.

```python
# custom_validators.py
from nautobot.extras.plugins import PluginCustomValidator


class SiteValidator(PluginCustomValidator):
    """Custom validator for Sites to enforce that they must have a Region."""

    model = 'dcim.site'

    def clean(self):
        if self.context['object'].region is None:
            # Enforce that all sites must be assigned to a region
            self.validation_error({
                "region": "All sites must be assigned to a region"
            })


custom_validators = [SiteValidator]
```

## Caching Configuration

By default, all query operations within a plugin are cached. To change this, define a caching configuration under the `PluginConfig` class' `caching_config` attribute. All configuration keys will be applied within the context of the plugin; there is no need to include the plugin name. An example configuration is below:

```python
class MyPluginConfig(PluginConfig):
    ...
    caching_config = {
        'foo': {
            'ops': 'get',
            'timeout': 60 * 15,
        },
        '*': {
            'ops': 'all',
        }
    }
```

To disable caching for your plugin entirely, set:

```python
caching_config = {
    '*': None
}
```

See the [django-cacheops](https://github.com/Suor/django-cacheops) documentation for more detail on configuring caching.

## Loading Data from a Git Repository

It's possible for a plugin to register additional types of data that can be provided by a [Git repository](../models/extras/gitrepository.md) and be automatically notified when such a repository is refreshed with new data. By default, Nautobot looks for an iterable named `datasource_contents` within a `datasources.py` file. (This can be overridden by setting `datasource_contents` to a custom value on the plugin's `PluginConfig`.) An example is below.

```python
# datasources.py
import yaml
import os

from nautobot.extras.choices import LogLevelChoices
from nautobot.extras.registry import DatasourceContent

from .models import Animal


def refresh_git_animals(repository_record, job_result, delete=False):
    """Callback for GitRepository updates - refresh Animals managed by it."""
    if 'nautobot_animal_sounds.Animal' not in repository_record.provided_contents or delete:
        # This repository is defined not to provide Animal records.
        # In a more complete worked example, we might want to iterate over any
        # Animals that might have been previously created by this GitRepository
        # and ensure their deletion, but for now this is a no-op.
        return

    # We have decided that a Git repository can provide YAML files in a
    # /animals/ directory at the repository root.
    animal_path = os.path.join(repository_record.filesystem_path, 'animals')
    for filename in os.listdir(animal_path):
        with open(os.path.join(animal_path, filename)) as fd:
            animal_data = yaml.safe_load(fd)

        # Create or update an Animal record based on the provided data
        animal_record, created = Animal.objects.update_or_create(
            name=animal_data['name'],
            defaults={'sound': animal_data['sound']}
        )

        # Record the outcome in the JobResult record
        job_result.log(
            "Successfully created/updated animal",
            obj=animal_record,
            level_choice=LogLevelChoices.LOG_SUCCESS,
            grouping="animals",
        )


# Register that Animal records can be loaded from a Git repository,
# and register the callback function used to do so
datasource_contents = [
    (
        'extras.gitrepository',                                # datasource class we are registering for
        DatasourceContent(
            name='animals',                                    # human-readable name to display in the UI
            content_identifier='nautobot_animal_sounds.animal',  # internal slug to identify the data type
            icon='mdi-paw',                                    # Material Design Icons icon to use in UI
            callback=refresh_git_animals,                      # callback function on GitRepository refresh
        )
    )
]
```

With this code, once your plugin is installed, the Git repository creation/editing UI will now include "Animals" as an option for the type(s) of data that a given repository may provide. If this option is selected for a given Git repository, your `refresh_git_animals` function will be automatically called when the repository is synced.
