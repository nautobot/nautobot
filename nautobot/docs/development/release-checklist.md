# Release Checklist

This document is intended for Nautobot maintainers and covers the steps to perform when releasing new versions.

## Minor Version Bumps

### Update Requirements

Required Python packages are maintained in two files: `pyproject.toml` and `poetry.lock`. 

#### The `pyproject.toml` file
Python packages are defined inside of `pyproject.toml`. The `[tool.poetry.dependencies]` section of this file contains a list of all the packages required by Nautobot.

Where possible, we use [tilde requirements](https://python-poetry.org/docs/dependency-specification/#tilde-requirements) to specify a minimal version with some ability to update, for example:

```
# REST API framework
djangorestframework = "~3.12.2"
```

This would allow Poetry to install `djangorestframework` versions `>=3.12.2` but `<3.13.0`.

#### The `poetry.lock` file

The other file is `poetry.lock`, which is managed by Poetry and contains package names, versions, and other metadata.

Each of the required packages pinned to its current stable version. When Nautobot is installed, this file is used to resolve and install all dependencies listed in `pyproject.toml`, but Poetry will use the exact versions found in `poetry.lock` to ensure that a new release of a dependency doesn't break Nautobot.

!!! warning
    You must never directly edit this file. You will use `poetry update` commands to manage it.

#### Run `poetry update`

Every minor version release should refresh `poetry.lock`, so that it lists the most recent stable release of each package. To do this:

1. Review each requirement's release notes for any breaking or otherwise noteworthy changes.
2. Run `poetry update <package>` to update the package versions in `poetry.lock` as appropriate.
3. If a required package requires updating to a new release not covered in the version constraints for a package as defined in `pyproject.toml`, (e.g. `Django ~3.1.7` would never install `Django >=4.0.0`), update it manually in `pyproject.toml`.
4. Run `poetry install` to install the refreshed versions of all required packages.
5. Run all tests and check that the UI and API function as expected.

!!! hint
    You may use `poetry update --dry-run` to have Poetry automatically tell you what package updates are avaiable and the versions it would upgrade.

### Update Static Libraries

Update the following static libraries to their most recent stable release:

* [Bootstrap 3](https://getbootstrap.com/docs/3.4)
* [Material Design Icons](https://materialdesignicons.com/)
* [Select2](https://github.com/select2/select2/releases)
* [jQuery](https://jquery.com/download/)
* [jQuery UI](https://jqueryui.com/)

### Link to the Release Notes Page

Add the release notes (`/docs/release-notes/X.Y.md`) to the table of contents within `mkdocs.yml`, and point `index.md` to the new file.

### Manually Perform a New Install

Fire up `mkdocs serve` in your local environment to start the documentation server:

```no-highlight
$ mkdocs serve
```

Follow these instructions to perform a new installation of Nautobot. This process must _not_ be automated: The goal of this step is to catch any errors or omissions in the documentation, and ensure that it is kept up-to-date for each release. Make any necessary changes to the documentation before proceeding with the release.

### Close the Release Milestone

Close the release milestone on GitHub after ensuring there are no remaining open issues associated with it.

### Merge the Release Branch

Submit a pull request to merge the `feature` branch into the `develop` branch in preparation for its release.

---

## All Releases

### Verify CI Build Status

Ensure that continuous integration testing on the `develop` branch is completing successfully.

### Update Version and Changelog

Update the package version in `pyproject.toml` to the new release version. For example, if we wanted to update the package to `2.0.0`:

```no-highlight
$ poetry version 2.0.0
Bumping version from 1.0.0 to 2.0.0
```

Next, update the release notes for the new version and commit these changes to the `develop` branch.

### Submit a Pull Request

Submit a pull request title **"Release vX.Y.Z"** to merge the `develop` branch into `main`. Copy the documented release notes into the pull request's body.

Once CI has completed on the PR, merge it.

### Create a New Release

Draft a [new release](https://github.com/nautobot/nautobot/releases/new) with the following parameters.

* **Tag:** Current version (e.g. `v1.0.0`)
* **Target:** `main`
* **Title:** Version and date (e.g. `v1.0.0 - 2021-06-01`)

Copy the description from the pull request to the release.

### Publish to PyPI

Now that there is a tagged release, the final step is to upload the package to the Python Package Index.

First, you'll need to build the Python package distributions:

```no-highlight
$ poetry build
```

Next, publish to PyPI using the username `__token__` and the Nautobot PyPI API token as the password. The API token can be found in the Nautobot maintainers vault (if you're a maintainer, you'll have access to this vault):

```
$ poetry publish --username __token__ --password <api_token>
```
