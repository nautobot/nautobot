# Release Checklist

This document is intended for Nautobot maintainers and covers the steps to perform when releasing new versions.

## Summary

1. For new minor/major versions (recommended but not required for patch versions):
    1. [Update Python Dependencies](#update-python-dependencies)
    2. [Update UI Libraries](#update-ui-libraries)
    3. [Link to the New Release Notes Page](#link-to-the-new-release-notes-page)
    4. [Verify and Revise the Install Documentation](#verify-and-revise-the-install-documentation)
2. [Verify CI Build Status](#verify-ci-build-status)
3. [Create a Release Branch](#create-a-release-branch)
4. [Bump the Version](#bump-the-version)
5. [Update the Changelog](#update-the-changelog)
6. [Submit Release Pull Request](#submit-release-pull-request)
7. [Merge Release Pull Request](#merge-release-pull-request)
8. [Create a New Release](#create-a-new-release)
9. If needed due to CI failures:
    1. [Publish to PyPI Manually (if needed)](#publish-to-pypi-manually-if-needed)
    2. [Publish Docker Images Manually (if needed)](#publish-docker-images-manually-if-needed)
10. [Bump the Development Version in `develop`](#bump-the-development-version-in-develop)
11. [Sync Changes into `next`](#sync-changes-into-next)

## Prerequisites for New Minor or Major Versions

### Update Python Dependencies

Nautobot's required Python packages are tracked in two files: `pyproject.toml` and `poetry.lock`. `pyproject.toml` specifies the ranges of versions of each direct Nautobot dependency that can be included when preparing a production installation of Nautobot (e.g. via `pip install nautobot`), while `poetry.lock` serves two distinct but important purposes:

1. Specify the exact versions of all Nautobot dependencies (direct and indirect) that are installed in a Nautobot *developer* environment (`poetry install`)
2. Specify the exact versions of all Nautobot dependencies (direct and indirect) that are installed in the Nautobot Docker images (including both developer and final targets).

Note that you should never manually edit `poetry.lock`; instead, you will typically update it (and often `pyproject.toml` as well) via the `poetry` CLI command.

We use [Renovate](https://docs.renovatebot.com/) and [Dependabot](https://docs.github.com/en/code-security/dependabot) to generally keep both of these files up to date. Before releasing a new minor or major Nautobot version, you should review any open Renovate and Dependabot PRs for suitability and merge them if appropriate. In addition, it's a good idea to manually review the contents of `pyproject.toml` to see if there are any dependencies that need additional manual updates. (For example, in some cases we temporarily pin dependencies to specific older versions while we await a critical fix for some regression in the current version of said dependency; once that regression is addressed, it might be necessary to manually update the dependency to the fixed version.)

#### Manually Updating Dependencies

Use the [`poetry add`](https://python-poetry.org/docs/cli/#add) command as appropriate to update the range of versions permitted in `pyproject.toml` for a direct Python dependency of Nautobot. For example, `poetry add 'netutils^1.14.0'` or `poetry add --optional --extras=saml 'social-auth-core~4.8.1'`.

Use the [`poetry update`](https://python-poetry.org/docs/cli/#update) command as appropriate to update the `poetry.lock` file to use the latest versions of all Python dependencies of Nautobot (within the constraints specified in `pyproject.toml`).

After making any changes to `pyproject.toml` or `poetry.lock` with the above commands, you should of course commit the changes and re-run Nautobot tests and CI to verify that the dependency updates have not broken anything before proceeding with the release preparation.

### Update UI Libraries

Update UI libraries to their latest version (specified by the tag config) respecting the semver constraints of both package and its dependencies:

```no-highlight
invoke npm --command "update --save"
invoke ui-build
```

Test and commit any resultant changes to `nautobot/ui/src/` and `nautobot/project-static/dist/` before proceeding with the release.

### Link to the New Release Notes Page

Add the release notes (`docs/release-notes/X.Y.md`) to the table of contents within `mkdocs.yml`, and point `docs/release-notes/index.md` to the new file.

### Verify and Revise the Install Documentation

Follow the [install instructions](../../user-guide/administration/installation/nautobot.md) to perform a new production installation of Nautobot.

The goal of this step is to walk through the entire install process *as documented* to make sure nothing there needs to be changed or updated, to catch any errors or omissions in the documentation, and to ensure that it is current with each release.

!!! tip
    Fire up `mkdocs serve --livereload` in your development environment to start the documentation server! This allows you to view the documentation locally and automatically rebuilds the documents as you make changes.

Commit any necessary changes to the documentation before proceeding with the release.

---

## Steps for All Releases

### Verify CI Build Status

Ensure that continuous integration testing on the `develop` branch is completing successfully.

### Create a Release Branch

Create a release branch off of `develop` (`git checkout -b release/3.0.1 develop`).

### Bump the Version

Update the package version using `invoke version`. This command shows the current version of the project or bumps the version of the project and writes the new version back to `pyproject.toml` (for the Nautobot Python package) if a valid bump rule is provided.

The new version should ideally be a valid semver string or a valid bump rule: `patch`, `minor`, `major`, `prepatch`, `preminor`, `premajor`, `prerelease`. Always try to use a bump rule when you can.

Display the current version with no arguments:

```no-highlight
invoke version
```

Example output:

```no-highlight
3.0.1.b1
```

To prepare for a patch release, use `patch`:

```no-highlight
invoke version -v patch
```

Example output:

```no-highlight
3.0.2
```

For minor versions, use `minor`:

```no-highlight
invoke version -v minor
```

Example output:

```no-highlight
3.1.0
```

And for major versions, use `major`:

```no-highlight
invoke version -v major
```

Example output:

```no-highlight
4.0.0
```

The `invoke version [-v <version>]` command internally runs the [`poetry version`](https://python-poetry.org/docs/cli/#version) command to handle the versioning process. However, there might be cases where you need to manually configure the version. Refer to the Poetry documentation linked above for detailed instructions. It provides information on how to set the version directly in the `pyproject.toml` file or update it using the `poetry version` command.

After updating the version correctly, be sure to `git add pyproject.toml`. You'll commit it after the next step.

### Update the Changelog

Generate release notes with `towncrier build --version <new-version-number>` and answer `yes` to the prompt `Is it okay if I remove those files? [Y/n]:`. This will update the release notes in `nautobot/docs/release-notes/version-<major.minor>.md`, stage that file in Git, and `git rm` all of the fragments that have now been incorporated into the release notes.

Run `invoke markdownlint` to make sure the generated release notes pass the linter checks, and manually review them for completeness/correctness as well.

!!! important
    The changelog must adhere to the [Keep a Changelog](https://keepachangelog.com/) style guide.

Check the git diff to verify the changes are correct (`git diff --cached`). You should see:

* a one-line change to `pyproject.toml` updating the version number (from the previous step)
* release-notes added to `nautobot/docs/release-notes/version-<major.minor>.md`
* all change fragments removed from the `changes/` folder

Commit (the traditional commit message is "Towncrier and version bump" but that's not required) and push the staged changes upstream to GitHub.

### Submit Release Pull Request

Submit a pull request titled **"Release vX.Y.Z"** to merge your release branch into `main`. Copy the documented release notes into the pull request's body.

### Merge Release Pull Request

Once CI has completed on the PR, and you have obtained the required approval(s), merge it.

!!! important
    Do not squash merge this branch into `main`. Make sure to select `Create a merge commit` when merging in GitHub.

### Create a New Release

Draft a [new release](https://github.com/nautobot/nautobot/releases/new) with the following parameters.

* **Tag:** Version to be released, prefixed with `v` (e.g. `v3.0.1`)
* **Target:** `main`
* **Title:** Version and date (e.g. `v3.0.1 - 2025-11-24`)
* **Release notes:** Follow the steps below:
    1. Click on **Generate release notes** button and you should see some release notes auto-generated by GitHub.
    2. Change the heading **What's Changed** to **Contributors**.
    3. Create a new **What's Changed** heading before the **Contributors** heading and here, copy and paste the changelog entries for the new release from `nautobot/docs/release-notes/version-<major.minor>.md` (or from your previous pull request).
    4. Change the entries under the **Contributors** heading to be a list of the usernames of the contributors, for example `* Updated dockerfile by @nautobot_user in https://github.com/nautobot/nautobot/pull/123` --> `* @nautobot_user`, removing duplicate usernames as you go.
    5. Leave the **New Contributors** list (if any) at the end of the release note as is.
    6. When done, the release note should look similar to any other recent Nautobot release, for example [v2.4.22](https://github.com/nautobot/nautobot/releases/tag/v2.4.22)
* **Set as the latest release** should be checked if this release will be the latest for Nautobot. It should **not** be checked for prereleases or for releases from an LTM (long-term maintenance) branch such as `ltm-2.4`.
* **Create a discussion for this release** should be checked as well.

Once you have verified that all of the above is correct, publish the release and wait for the release CI to run in GitHub Actions.

### Publish to PyPI Manually (if needed)

!!! tip
    This is normally done automatically by GitHub Actions after you create the release above. The below is only needed if the automated release fails for some reason.

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

### Publish Docker Images Manually (if needed)

!!! tip
    This is normally done automatically by GitHub Actions after you create the release above. The below is only needed if the automated release fails for some reason.

Build the images locally:

```no-highlight
for ver in 3.10 3.11 3.12 3.13; do
  export INVOKE_NAUTOBOT_PYTHON_VER=$ver
  invoke buildx --target final --tag networktocode/nautobot-py${INVOKE_NAUTOBOT_PYTHON_VER}:local
  invoke buildx --target final-dev --tag networktocode/nautobot-dev-py${INVOKE_NAUTOBOT_PYTHON_VER}:local
done
```

Test the images locally as needed - to do this you need to set the following in your `invoke.yml`:

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.postgres.yml"
    - "docker-compose.final.yml"  # or "docker-compose.final-dev.yml" as appropriate
```

!!! warning
    You should *not* include `docker-compose.dev.yml` in this test scenario!

Push the images to GitHub Container Registry and Docker Hub

```no-highlight
docker login
docker login ghcr.io
for ver in 3.10 3.11 3.12 3.13; do
  export INVOKE_NAUTOBOT_PYTHON_VER=$ver
  invoke docker-push main
done
```

### Bump the Development Version in `develop`

Create a new branch off of `main` (typically named `main-to-develop-post-<x.y.z>`) and use `invoke version -v prepatch` to bump the version in preparation for developing the next release. Then open a pull request from this branch to the `develop` branch to update the version and sync the release notes and changelog fragment updates from `main`.

For example, if you just released `v3.0.1`:

```no-highlight
invoke version -v prepatch
```

Example output:

```no-highlight
Bumping version from 3.0.1 to 3.0.2a0
```

!!! tip
    We normally use `beta` version numbers rather than `alpha` versions for `develop`, so you may need to manually edit `pyproject.toml` after the above, for example to change `"3.0.2a0"` to `"3.0.2b1"` to follow our convention.

!!! important
    Do not squash merge this branch into `develop`. Make sure to select `Create a merge commit` when merging in GitHub.

### Sync Changes into `next`

After the main-to-develop pull request is merged into `develop`, create a new branch off of `next` (typically named `develop-to-next-post-<x.y.z>`) and `git merge develop`. Resolve any merge conflicts as appropriate (if you're lucky, there may only be one, a version number clash in `pyproject.toml`), then open a pull request to `next`.

!!! important
    Do not squash merge this branch into `next`. Make sure to select `Create a merge commit` when merging in GitHub.
