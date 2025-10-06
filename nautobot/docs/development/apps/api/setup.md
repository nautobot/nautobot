# Initial Setup

!!! important "Use a Development Environment, Not Production For App Development"
    You should not use your production environment for app development. For information on getting started with a development environment, check out [Nautobot development guide](../../core/getting-started.md).

!!! note
    The Nautobot organization provides a Python [CookieCutter](https://cookiecutter.readthedocs.io/en/stable/) to help get started with your applications. Get started at [`https://github.com/nautobot/cookiecutter-nautobot-app`](https://github.com/nautobot/cookiecutter-nautobot-app).

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
    - table_extensions.py   # Extending Tables
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

## Serving Apps Documentation

The documentation for each pip-installed application is served dynamically through Django views and is restricted to authenticated users. This approach ensures that:

* Works regardless of where the app is installed (editable install, virtualenv, system site-packages).
* Access is protected by Django authentication.

### File Structure

Documentation for an app (e.g., example_app) is expected to be located inside the package:

```no-highlight
example_app/
├── docs/
│   ├── index.html
│   ├── assets/
      └── extra.css
      └── nautobot_logo.svg
```


### Build Process using MkDocs

If using MkDocs to compile Markdown documentation to HTML, you should ensure that `mkdocs.yml` defines `site_dir` to be the path `<app_name>/docs` so that the compiled HTML is correctly placed in that directory.

```no-highlight
mkdocs build --no-directory-urls --strict
```

### URL Routing

The `docs_index` and `docs_files` URL patterns defined in `nautobot.core.urls` are used for serving the documentation of all apps.

`/docs/example_app/` - serves the `example_app/docs/index.html` file.

`/docs/example_app/assets/extra.css` - serves the requested file from `example_app/docs/` and its subdirectories, for example here `example_app/docs/assets/extra.css`.

Both routes go through AppDocsView, which enforces login.

### Redirect for Each App

Each app should define its own top-level `/docs/` URL that redirects to the appropriate app documentation:

```python
app_name = example_app
path(
    "docs/",
    RedirectView.as_view(pattern_name="docs_index"),
    {"app_name": app_name},
    name="docs",
)
```

This allows users to access `/docs/<app-name>`.
