# Release Checklist

This document is intended for Nautobot maintainers and covers the steps to perform when releasing new versions.

## Minor Version Bumps

### Update Requirements

Required Python packages are maintained in two files: `pyproject.toml` and `poetry.lock`.

#### The `pyproject.toml` file

Python packages are defined inside of `pyproject.toml`. The `[tool.poetry.dependencies]` section of this file contains a list of all the packages required by Nautobot.

Where possible, we use [tilde requirements](https://python-poetry.org/docs/dependency-specification/#tilde-requirements) to specify a minimal version with some ability to update, for example:

```toml
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
    You may use `poetry update --dry-run` to have Poetry automatically tell you what package updates are available and the versions it would upgrade.

### Update Static Libraries

Update the following static libraries to their most recent stable release:

* [Bootstrap 3](https://getbootstrap.com/docs/3.4)
* [Material Design Icons](https://materialdesignicons.com/)
* [Select2](https://github.com/select2/select2/releases)
* [jQuery](https://jquery.com/download/)
* [jQuery UI](https://jqueryui.com/)

### Link to the Release Notes Page

Add the release notes (`docs/release-notes/X.Y.md`) to the table of contents within `mkdocs.yml`, and point `index.md` to the new file.

### Verify and Revise the Install Documentation

Follow the [install instructions](../../user-guide/administration/installation/nautobot.md) to perform a new production installation of Nautobot.

The goal of this step is to walk through the entire install process *as documented* to make sure nothing there needs to be changed or updated, to catch any errors or omissions in the documentation, and to ensure that it is current with each release.

!!! tip
    Fire up `mkdocs serve` in your development environment to start the documentation server! This allows you to view the documentation locally and automatically rebuilds the documents as you make changes.

Commit any necessary changes to the documentation before proceeding with the release.

### Close the Release Milestone

Close the release milestone on GitHub after ensuring there are no remaining open issues associated with it.

---

## All Releases

### Verify CI Build Status

Ensure that continuous integration testing on the `develop` branch is completing successfully.

### Bump the Version

Update the package version using `invoke version`. This command shows the current version of the project or bumps the version of the project and writes the new version back to `pyproject.toml` (for the Nautobot Python package) and `package.json` (for the Nautobot UI) if a valid bump rule is provided.

The new version should ideally be a valid semver string or a valid bump rule: `patch`, `minor`, `major`, `prepatch`, `preminor`, `premajor`, `prerelease`. Always try to use a bump rule when you can.

Display the current version with no arguments:

```no-highlight
invoke version
```

Example output:

```no-highlight
{
  nautobot: '2.0.0-beta.2',
  npm: '9.5.1',
  node: '18.16.1',
  ...
}
```

Bump pre-release versions using `prerelease`:

```no-highlight
invoke version -v prerelease
```

Example output:

```no-highlight
v2.0.0-beta.3
```

For major versions, use `major`:

```no-highlight
invoke version -v major
```

Example output:

```no-highlight
v3.0.0
```

For patch versions, use `minor`:

```no-highlight
invoke version minor
```

Example output:

```no-highlight
v2.1.0
```

And lastly, for patch versions, you guessed it, use `patch`:

```no-highlight
invoke version patch
```

Example output:

```no-highlight
v2.0.1
```

The `invoke version [<version>]` command internally runs `poetry version` and `npm version` commands to handle the versioning process. However, there might be cases where you need to manually configure the version. Here's how you can do that:

* **Poetry Version**: If you want to manually set the version for the Python dependencies managed by Poetry, you can refer to the [Poetry documentation](https://python-poetry.org/docs/cli/#version) on version for detailed instructions. It provides information on how to set the version directly in the `pyproject.toml` file or update it using the `poetry version` command.
* **npm Version**: To manually configure the version for the Node.js packages managed by npm, you can refer to the official [npm documentation](https://docs.npmjs.com/cli/v9/commands/npm-version) on `npm version` for more information. It explains how to set the version directly in the `package.json` file or update it using the `npm version` command.

### Update the Changelog

Create a release branch off of `develop` (`git checkout -b release/1.4.3 develop`)

Generate release notes with `towncrier build --version 1.4.3` and answer `yes` to the prompt `Is it okay if I remove those files? [Y/n]:`. This will update the release notes in `nautobot/docs/release-notes/version-1.4.md`, stage that file in git, and `git rm` all of the fragments that have now been incorporated into the release notes.

Run `invoke markdownlint` to make sure the generated release notes pass the linter checks.

Check the git diff to verify the changes are correct (`git diff --cached`).

Commit and push the staged changes.

!!! important
    The changelog must adhere to the [Keep a Changelog](https://keepachangelog.com/) style guide.

### Submit Pull Request

Submit a pull request titled **"Release vX.Y.Z"** to merge your release branch into `main`. Copy the documented release notes into the pull request's body.

Once CI has completed on the PR, merge it.

!!! important
    Do not squash merge this branch into `main`. Make sure to select `Create a merge commit` when merging in GitHub.

### Create a New Release Tag

You need to create a release tag locally so that you can use it later when you draft the new release for nautobot, for example, `v1.4.3`.
To create the tag locally:

```bash
$ git tag v1.4.3
```

To list all the tags to see if it is created successfully:

```bash
$ git tag
```

To push the tag upstream:

```bash
$ git push origin v1.4.3
```

### Create a New Release

Draft a [new release](https://github.com/nautobot/nautobot/releases/new) with the following parameters.

* **Tag:** Current version (e.g. `v1.0.0`)

!!! warning
    You will need to create a new release tag locally **before** you draft the new release. To create a new release tag, follow the steps outlined [here](#create-a-new-release-tag).

* **Target:** `main`
* **Title:** Version and date (e.g. `v1.0.0 - 2021-06-01`)
* **Release Notes:** Follow the steps below

1. Click on **Generate release notes** button and you should see some release notes auto-generated by GitHub.
2. Copy and paste the changelog entries newly generated by towncrier in `nautobot/docs/release-notes/version-1.4.md` from your previous pull request to the auto-generated release notes on top of the **What's Changed** section.
3. Change the heading **What's Changed** to **Contributors**.
4. Change the entries under the heading to only the usernames of the contributors. e.g. `* Updated dockerfile by @nautobot_user in https://github.com/nautobot/nautobot/pull/123` -> `* @nautobot_user`
5. Make sure there is no redundant username in the **Contributors** list.
6. Leave the **New Contributors** list as it is.

### Publish to PyPI

Now that there is a tagged release, the final step is to upload the package to the Python Package Index.

First, you'll need to render the documentation.

```no-highlight
poetry run mkdocs build --no-directory-urls --strict
```

Second, you'll need to build the Python package distributions (which will include the rendered documentation):

```no-highlight
poetry build
```

Finally, publish to PyPI using the username `__token__` and the Nautobot PyPI API token as the password. The API token can be found in the Nautobot maintainers vault (if you're a maintainer, you'll have access to this vault):

```no-highlight
poetry publish --username __token__ --password <api_token>
```

### Publish Docker Images

Build the images locally:

```no-highlight
for ver in 3.8 3.9 3.10 3.11; do
  export INVOKE_NAUTOBOT_PYTHON_VER=$ver
  invoke buildx --target final --tag networktocode/nautobot-py${INVOKE_NAUTOBOT_PYTHON_VER}:local
  invoke buildx --target final-dev --tag networktocode/nautobot-dev-py${INVOKE_NAUTOBOT_PYTHON_VER}:local
done
```

Test the images locally - to do this you need to set the following in your `invoke.yml`:

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.postgres.yml"
    - "docker-compose.final.yml"
```

!!! warning
    You should *not* include `docker-compose.dev.yml` in this test scenario!

```no-highlight
for ver in 3.8 3.9 3.10 3.11; do
  export INVOKE_NAUTOBOT_PYTHON_VER=$ver
  invoke stop
  invoke integration-tests
done
```

Push the images to GitHub Container Registry and Docker Hub

```no-highlight
docker login
docker login ghcr.io
for ver in 3.8 3.9 3.10 3.11; do
  export INVOKE_NAUTOBOT_PYTHON_VER=$ver
  invoke docker-push main
done
```

### Bump the Development Version

Create a new branch off of `main` and use `poetry version prepatch` to bump the version to the next release. Then open a pull request to the `develop` branch to update the version and sync the release notes and changelog fragment updates from `main`.

For example, if you just released `v1.1.0`:

```no-highlight
poetry version prepatch
```

Example output:

```no-highlight
Bumping version from 1.1.0 to 1.1.1-alpha.0
```

!!! important
    Do not squash merge this branch into `develop`. Make sure to select `Create a merge commit` when merging in GitHub.
