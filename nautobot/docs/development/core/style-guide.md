# Style Guide

Nautobot generally follows the [Django style guide](https://docs.djangoproject.com/en/stable/internals/contributing/writing-code/coding-style/), which is itself based on [PEP 8](https://www.python.org/dev/peps/pep-0008/). The following tools are used to enforce coding style and best practices:

* [Flake8](https://flake8.pycqa.org/) is used to validate code style.
* [Black](https://black.readthedocs.io/) is used to enforce code formatting conventions.
* [ESLint](https://eslint.org) is used to validate code style for the UI.
* [Prettier](https://prettier.io) is used to enforce code formatting conventions for the UI.
* [Pylint](https://pylint.pycqa.org/en/latest/) is used for Python static code analysis.
* [Hadolint](https://github.com/hadolint/hadolint) is used to lint and validate Docker best practices in the Dockerfile.
* [MarkdownLint-cli](https://github.com/igorshubovych/markdownlint-cli) is used to lint and validate Markdown (documentation) files.

Nautobot-specific configuration of these tools is maintained in the files `.flake8`, `.markdownlint.yml`, `.prettierrc`, `package.json`, or `pyproject.toml` as appropriate to the individual tool.

It is strongly recommended to include all of the above tools as part of your commit process before opening any pull request. A Git commit hook is provided in the source at `scripts/git-hooks/pre-commit`. Linking to this script from `.git/hooks/` will invoke these tools prior to every commit attempt and abort if the validation fails.

```bash
cd .git/hooks/
ln -s ../../scripts/git-hooks/pre-commit
```

You can also invoke these utilities manually against the development Docker containers by running:

```no-highlight
invoke flake8
invoke black
invoke eslint
invoke prettier
invoke check-migrations
invoke hadolint
invoke markdownlint
invoke pylint
```

## Introducing New Dependencies

The introduction of a new dependency is best avoided unless it is absolutely necessary. For small features, it's generally preferable to replicate functionality within the Nautobot code base rather than to introduce reliance on an external project. This reduces both the burden of tracking new releases and our exposure to outside bugs and attacks.

If there's a strong case for introducing a new dependency, it must meet the following criteria:

* Its complete source code must be published and freely accessible without registration.
* Its license must be conducive to inclusion in an open source project.
* It must be actively maintained, with no longer than one year between releases.
* It must be available via the [Python Package Index](https://pypi.org/) (PyPI).

New dependencies can be added to the project via the `poetry add` command. This will correctly add the dependency to `pyproject.toml` as well as the `poetry.lock` file. You should then update the `pyproject.toml` with a comment providing a short description of the package and/or how Nautobot is making use of it.

## General Guidance

* When in doubt, remain consistent: It is better to be consistently incorrect than inconsistently correct. If you notice in the course of unrelated work a pattern that should be corrected, continue to follow the pattern for now and open a bug so that the entire code base can be evaluated at a later point.

* Prioritize readability over concision. Python is a very flexible language that typically offers several options for expressing a given piece of logic, but some may be more friendly to the reader than others. (List comprehensions are particularly vulnerable to over-optimization.) Always remain considerate of the future reader who may need to interpret your code without the benefit of the context within which you are writing it.

* No easter eggs. While they can be fun, Nautobot must be considered as a business-critical tool. The potential, however minor, for introducing a bug caused by unnecessary logic is best avoided entirely.

* Constants (variables which generally do not change) should be declared in `constants.py` within each app.

* Every model should have a docstring. Every custom method should include an explanation of its function.

* The combination of `nautobot.core.filters.BaseFilterSet`, `nautobot.extras.filters.CreatedUpdatedModelFilterSetMixin`, `nautobot.extras.filters.CustomFieldModelFilterSetMixin`, and `nautobot.extras.filters.RelationshipModelFilterSetMixin` is such a common use case throughout the code base that they have a helper class which combines all of these at `nautobot.extras.NautobotFilterSet`. Use this helper class if you need the functionality from these classes.

* The combination of `nautobot.core.forms.BootstrapMixin`, `nautobot.extras.forms.CustomFieldModelFormMixin`, `nautobot.extras.forms.RelationshipModelFormMixin` and `nautobot.extras.forms.NoteModelFormMixin` is such a common use case throughout the code base that they have a helper class which combines all of these at `nautobot.extras.forms.NautobotModelForm`. Use this helper class if you need the functionality from these classes.

+++ 1.4.0

    * Similarly, for filter forms, `nautobot.extras.forms.NautobotFilterForm` combines `nautobot.core.forms.BootstrapMixin`, `nautobot.extras.forms.CustomFieldModelFilterFormMixin`, and `nautobot.extras.forms.RelationshipModelFilterFormMixin`, and should be used where appropriate.

    * Similarly, for bulk-edit forms, `nautobot.extras.forms.NautobotBulkEditForm` combines `nautobot.core.forms.BulkEditForm` and `nautobot.core.forms.BootstrapMixin` with `nautobot.extras.forms.CustomFieldModelBulkEditFormMixin`, `nautobot.extras.forms.RelationshipModelBulkEditFormMixin` and `nautobot.extras.forms.NoteModelBulkEditFormMixin`, and should be used where appropriate.

    * API serializers for most models should inherit from `nautobot.extras.api.serializers.NautobotModelSerializer` and any appropriate mixins. Only use more abstract base classes such as ValidatedModelSerializer where absolutely required.

    * `NautobotModelSerializer` will automatically add serializer fields for `id`, `created`/`last_updated` (if applicable), `custom_fields`, `computed_fields`, and `relationships`, so there's generally no need to explicitly declare these fields in `.Meta.fields` of each serializer class. Similarly, `TaggedModelSerializerMixin` and `` will automatically add the `tags` and `status` fields when included in a serializer class.

    * API Views for most models should inherit from `nautobot.extras.api.views.NautobotModelViewSet`. Only use more abstract base classes such as `ModelViewSet` where absolutely required.

## Branding

* When referring to Nautobot in writing, use the proper form "Nautobot," with the letter N. The lowercase form "nautobot" should be used in code, filenames, etc.

<!-- markdownlint-disable-next-line NAUTOBOTMD001 -->
* There is an SVG form of the Nautobot logo at [nautobot/docs/nautobot_logo.svg](../../nautobot_logo.svg). It is preferred to use this logo for all purposes as it scales to arbitrary sizes without loss of resolution. If a raster image is required, the SVG logo should be converted to a PNG image of the prescribed size.

## Importing Python Packages

To prevent circular dependency errors and improve code readability, the following standards should be followed when importing from other python modules.

### PEP8 Style Guide

Nautobot follows the [PEP8 style guide's](https://peps.python.org/pep-0008/#imports) standard for importing modules. Libraries should be imported in these groups: standard library, third party libraries, then `nautobot` packages and finally try/except imports. The groups should be separated by a single blank line. Within these groups,import lines should be sorted alphanumerically by the package name. Lists of of names imported from packages should also be sorted alphanumerically.

!!! example

    ```py
    from abc import ABC
    import logging
    from uuid import UUID

    from django.db.models import CharField, DecimalField, TextField
    import django_filters

    from nautobot.dcim import models as dcim_models
    from nautobot.extras import models
    ```

### Wildcard Imports

Wildcard imports (`from foo import *`) should only be used in `__init__.py` files to import names from submodules that have a `__all__` variable defined.

!!! example

    ```py title="nautobot/dcim/models/__init__.py"
    from nautobot.dcim.models.cables import *
    from nautobot.dcim.models.device_component_templates import *
    from nautobot.dcim.models.device_components import *
    # etc ...
    ```

### Importing from External Packages

Individual names may be imported from external packages (`from foo import some_function, SomeClass`). This differs from the standard for [importing from the `nautobot` package](#module-name-imports).

### Importing Nautobot Packages

#### Module Name Imports

Whenever possible, imports from the `nautobot` package should use module level imports, not individual names from a module.

!!! example

    ```py
    # module import
    from nautobot.core import xyz

    # name import (do not use)
    from nautobot.core.xyz import SomeClass, some_function
    ```

#### Absolute Imports

Always use absolute imports instead of relative imports.

!!! example

    ```py
    # absolute import
    from nautobot.dcim import constants
    from nautobot.dcim.models import Device

    # relative import (do not use)
    import constants
    from .models import Device
    ```

#### Import Style Conventions

To import modules from other apps under the `nautobot` namespace, use the convention `from nautobot.<app_name> import <module> as <app_name>_<module>`. If importing from within the same app do not alias the imported namespace.

!!! example

    ```py title="nautobot/extras/models.py"
    # inter-app import
    from nautobot.dcim import models as dcim_models

    # intra-app import
    from nautobot.extras import constants
    ```

#### Resolving Name Conflicts

When using external libraries you may need to import multiple different modules with the same name. In this case, the namespace from the external package should be aliased. For aliasing external libraries, use `<package>_<module>`.

!!! example

    ```py
    # from within the current app
    from nautobot.extras import models

    # from a different Nautobot app
    from nautobot.dcim import models as dcim_models

    # other libraries
    from django.db import models as django_models
    from tree_queries import models as tree_queries_models
    ```

#### Convenience Imports

Nautobot uses convenience imports in the same way that [django](https://docs.djangoproject.com/en/dev/internals/contributing/writing-code/coding-style/#imports) implements them. These should be leveraged whenever possible.

!!! example

    ```py
    from nautobot.extras import forms

    # use top level import if available:
    forms.NoteModelFormMixin()

    # instead of the full path:
    forms.mixins.NoteModelFormMixin()
    ```
