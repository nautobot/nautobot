# Style Guide

Nautobot generally follows the [Django style guide](https://docs.djangoproject.com/en/stable/internals/contributing/writing-code/coding-style/), which is itself based on [PEP 8](https://www.python.org/dev/peps/pep-0008/). [Flake8](https://flake8.pycqa.org/) is used to validate code style, ignoring certain violations, and [Black](https://black.readthedocs.io/) is used to enforce code formatting conventions. See `scripts/cibuild.sh` and `tasks.py`.

## Flake8 Exceptions

* Whitespace before ':' is permitted (E203) as Black maintains that there are cases where this is the preferred style.
* Imported-but-unused modules (F401) are currently not flagged, but we want to fix this in the future.
* Wildcard imports (for example `from .constants import *`, F403) are currently not flagged, as this is a pattern inherited from NetBox's coding style, but we want to change this in the future, and recommend against introducing this pattern in any new code.
* "Name may be undefined or defined from star imports" (F405) is currently not flagged due to the previous item; we plan to
enable this check after changing the above import pattern.
* Maximum line length is 120 characters (E501)
* Line breaks are permitted both before (W503) and after (W504) binary operators.

## Enforcing Code Style

The `flake8` and `black` utilities are used by the CI process to enforce code style. It is strongly recommended to include both as part of your commit process. A git commit hook is provided in the source at `scripts/git-hooks/pre-commit`. Linking to this script from `.git/hooks/` will invoke `flake8` and `black --check` prior to every commit attempt and abort if the validation fails.

```
$ cd .git/hooks/
$ ln -s ../../scripts/git-hooks/pre-commit
```

You can also invoke these utilities manually against the development Docker containers by running:

```
invoke flake8
invoke black
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

## Branding

* When referring to Nautobot in writing, use the proper form "Nautobot," with the letter N. The lowercase form "nautobot" should be used in code, filenames, etc.

* There is an SVG form of the Nautobot logo at [nautobot/docs/nautobot_logo.svg](../nautobot_logo.svg). It is preferred to use this logo for all purposes as it scales to arbitrary sizes without loss of resolution. If a raster image is required, the SVG logo should be converted to a PNG image of the prescribed size.
