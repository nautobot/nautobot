# Style Guide

Nautobot generally follows the [Django style guide](https://docs.djangoproject.com/en/stable/internals/contributing/writing-code/coding-style/), which is itself based on [PEP 8](https://www.python.org/dev/peps/pep-0008/). The following tools are used to enforce coding style and best practices:

* [Flake8](https://flake8.pycqa.org/) is used to validate code style.
* [Black](https://black.readthedocs.io/) is used to enforce code formatting conventions.
* [Pylint](https://pylint.pycqa.org/en/latest/) is used for Python static code analysis.
* [Hadolint](https://github.com/hadolint/hadolint) is used to lint and validate Docker best practices in the Dockerfile.
* [MarkdownLint-cli](https://github.com/igorshubovych/markdownlint-cli) is used to lint and validate Markdown (documentation) files.

Nautobot-specific configuration of these tools is maintained in the files `.flake8`, `.markdownlint.yml`, or `pyproject.toml` as appropriate to the individual tool.

It is strongly recommended to include all of the above tools as part of your commit process before opening any pull request. A Git commit hook is provided in the source at `scripts/git-hooks/pre-commit`. Linking to this script from `.git/hooks/` will invoke these tools prior to every commit attempt and abort if the validation fails.

```bash
cd .git/hooks/
ln -s ../../scripts/git-hooks/pre-commit
```

You can also invoke these utilities manually against the development Docker containers by running:

```no-highlight
invoke flake8
invoke black
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

* Constants (variables which generally do not change) should be declared in `constants.py` within each app. Wildcard imports from the file are acceptable.

* Every model should have a docstring. Every custom method should include an explanation of its function.

* Nested API serializers generate minimal representations of an object. These are stored separately from the primary serializers to avoid circular dependencies. Always import nested serializers from other apps directly. For example, from within the DCIM app you would write `from nautobot.ipam.api.nested_serializers import NestedIPAddressSerializer`.

* The combination of `nautobot.utilities.filters.BaseFilterSet`, `nautobot.extras.filters.CreatedUpdatedModelFilterSetMixin`, `nautobot.extras.filters.CustomFieldModelFilterSetMixin`, and `nautobot.extras.filters.RelationshipModelFilterSetMixin` is such a common use case throughout the code base that they have a helper class which combines all of these at `nautobot.extras.NautobotFilterSet`. Use this helper class if you need the functionality from these classes.

* The combination of `nautobot.utilities.forms.BootstrapMixin`, `nautobot.extras.forms.CustomFieldModelFormMixin`, `nautobot.extras.forms.RelationshipModelFormMixin` and `nautobot.extras.forms.NoteModelFormMixin` is such a common use case throughout the code base that they have a helper class which combines all of these at `nautobot.extras.forms.NautobotModelForm`. Use this helper class if you need the functionality from these classes.

+++ 1.4.0

    * Similarly, for filter forms, `nautobot.extras.forms.NautobotFilterForm` combines `nautobot.utilities.forms.BootstrapMixin`, `nautobot.extras.forms.CustomFieldModelFilterFormMixin`, and `nautobot.extras.forms.RelationshipModelFilterFormMixin`, and should be used where appropriate.

    * Similarly, for bulk-edit forms, `nautobot.extras.forms.NautobotBulkEditForm` combines `nautobot.utilities.forms.BulkEditForm` and `nautobot.utilities.forms.BootstrapMixin` with `nautobot.extras.forms.CustomFieldModelBulkEditFormMixin`, `nautobot.extras.forms.RelationshipModelBulkEditFormMixin` and `nautobot.extras.forms.NoteModelBulkEditFormMixin`, and should be used where appropriate.

    * API serializers for most models should inherit from `nautobot.extras.api.serializers.NautobotModelSerializer` and any appropriate mixins. Only use more abstract base classes such as ValidatedModelSerializer where absolutely required.

    * `NautobotModelSerializer` will automatically add serializer fields for `id`, `created`/`last_updated` (if applicable), `custom_fields`, `computed_fields`, and `relationships`, so there's generally no need to explicitly declare these fields in `.Meta.fields` of each serializer class. Similarly, `TaggedModelSerializerMixin` and `StatusModelSerializerMixin` will automatically add the `tags` and `status` fields when included in a serializer class.

    * API Views for most models should inherit from `nautobot.extras.api.views.NautobotModelViewSet`. Only use more abstract base classes such as `ModelViewSet` where absolutely required.

## Branding

* When referring to Nautobot in writing, use the proper form "Nautobot," with the letter N. The lowercase form "nautobot" should be used in code, filenames, etc.

<!-- markdownlint-disable-next-line NAUTOBOTMD001 -->
* There is an SVG form of the Nautobot logo at [nautobot/docs/nautobot_logo.svg](../nautobot_logo.svg). It is preferred to use this logo for all purposes as it scales to arbitrary sizes without loss of resolution. If a raster image is required, the SVG logo should be converted to a PNG image of the prescribed size.
