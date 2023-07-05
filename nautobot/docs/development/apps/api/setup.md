# Initial Setup

!!! important "Use a Development Environment, Not Production For App Development"
    You should not use your production environment for app development. For information on getting started with a development environment, check out [Nautobot development guide](../../core/getting-started.md).

## App Structure

Although the specific structure of an app is largely left to the discretion of its authors, a Nautobot app that makes use of all available app features described in this document could potentially look something like this:

```no-highlight
app_name/
  - app_name/
    - __init__.py           # required
    - admin.py              # Django Admin Interface
    - api/
      - serializers.py      # REST API Model serializers
      - urls.py             # REST API URL patterns
      - views.py            # REST API view sets
    - banner.py             # Banners
    - custom_validators.py  # Custom Validators
    - datasources.py        # Loading Data from a Git Repository
    - filter_extensions.py  # Extending Filters
    - filters.py            # Filtersets for UI, REST API, and GraphQL Model Filtering
    - forms.py              # UI Forms and Filter Forms
    - graphql/
      - types.py            # GraphQL Type Objects
    - homepage.py           # Home Page Content
    - jinja_filters.py      # Jinja Filters
    - jobs.py               # Job classes
    - middleware.py         # Request/response middleware
    - migrations/
      - 0001_initial.py     # Database Models
    - models.py             # Database Models
    - navigation.py         # Navigation Menu Items
    - secrets.py            # Secret Providers
    - signals.py            # Signal Handler Functions
    - template_content.py   # Extending Core Templates
    - templates/
      - app_name/
        - *.html            # UI content templates
    - urls.py               # UI URL Patterns
    - views.py              # UI Views and any view override definitions
  - pyproject.toml          # *** REQUIRED *** - Project package definition
  - README.md
```

The top level is the project root. Immediately within the root should exist several items:

* `pyproject.toml` - This is the new [unified Python project settings file](https://www.python.org/dev/peps/pep-0518/) that replaces `setup.py`, `requirements.txt`, and various other setup files (like `setup.cfg`, `MANIFEST.in`, among others).
* `README.md` - A brief introduction to your app, how to install and configure it, where to find help, and any other pertinent information. It is recommended to write README files using a markup language such as Markdown.
* The app source directory, with the same name as your app.

The app source directory contains all of the actual Python code and other resources used by your app. Its structure is left to the author's discretion, however it is recommended to follow best practices as outlined in the [Django documentation](https://docs.djangoproject.com/en/stable/intro/reusable-apps/). At a minimum, this directory **must** contain an `__init__.py` file containing an instance of Nautobot's `NautobotAppConfig` class.

!!! note
    Nautobot includes a command to help create the app directory:
    `nautobot-server startplugin [app_name]`
    Please see the [Nautobot Server Guide](../../../user-guide/administration/tools/nautobot-server.md#startplugin) for more information.

## Create pyproject.toml

## Poetry Init (Recommended)

To get started with a project using [Python Poetry](https://python-poetry.org/) you use the `poetry init` command. This will guide you through the prompts necessary to generate a pyproject.toml with details required for packaging.

```no-highlight
This command will guide you through creating your pyproject.toml config.

Package name [tmp]:  nautobot-animal-sounds
Version [0.1.0]:
Description []:  An example Nautobot app
Author [, n to skip]:  Bob Jones
License []:  Apache 2.0
Compatible Python versions [^3.8]:  ^3.8

Would you like to define your main dependencies interactively? (yes/no) [yes] no
Would you like to define your development dependencies interactively? (yes/no) [yes] no
Generated file

[tool.poetry]
name = "nautobot-animal-sounds"
version = "0.1.0"
description = "An example Nautobot app"
authors = ["Bob Jones"]
license = "Apache 2.0"

[tool.poetry.dependencies]
python = "^3.8"

[tool.poetry.dev-dependencies]

[build-system]
requires = ["poetry-core>=1.0.0"]
build-backend = "poetry.core.masonry.api"


Do you confirm generation? (yes/no) [yes]
```

## Install the App for Development

The app needs to be installed into the same python environment where Nautobot is, so that we can get access to `nautobot-server` command, and also so that the nautobot-server is aware of the new app.

If you installed Nautobot using Poetry, then go to the root directory of your clone of the Nautobot repository and run `poetry shell` there.  Afterward, return to the root directory of your app to continue development.

Otherwise if using the pip install or Docker workflows, manually activate nautobot using `source /opt/nautobot/bin/activate`.

To install the app for development the following steps should be taken:

* Activate the Nautobot virtual environment (as detailed above)
* Navigate to the project root, where the `pyproject.toml` file exists for the app
* Execute the command `poetry install` to install the local package into the Nautobot virtual environment

!!! note
    Poetry installs the current project and its dependencies in editable mode (aka ["development mode"](https://setuptools.readthedocs.io/en/latest/userguide/development_mode.html)).

!!! important "This should be done in development environment"
    You should not use your production environment for app development. For information on getting started with a development environment, check out [Nautobot development guide](../../core/getting-started.md).

```no-highlight
poetry install
```

Once the app has been installed, add it to the configuration for Nautobot:

```python
PLUGINS = ["animal_sounds"]
```

## Verify that the App is Installed

After restarting the Nautobot server, the newly installed app should appear in **Plugins -> Installed Plugins** if everything is configured correctly. You can also click on the app's name in this table to view more detailed information about this app based on its NautobotAppConfig and other contents.
