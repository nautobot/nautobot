# Getting Started

## Git Branches

The Nautobot project follows a branching model based on [Git-flow](https://nvie.com/posts/a-successful-git-branching-model/). As such, there are two persistent git branches:

* `main` - Serves as a snapshot of the current stable release
* `develop` - All development on the upcoming stable release occurs here

At any given time, there may additionally be zero or more long-lived branches of the form `develop-X.Y.Z`, where `X.Y.Z` is a future stable release later than the one currently being worked on in the main `develop` branch.

You will always base pull requests off of the `develop` branch, or off of `develop-X.Y.Z` if you're working on a feature targeted for a later release. **Never** target pull requests into the `main` branch, which receives merges only from the `develop` branch.

## Forking the Repo

When developing Nautobot, you'll be working on your own fork, so your first step will be to [fork the official GitHub repository](https://github.com/nautobot/nautobot/fork). You will then clone your GitHub fork locally for development.

!!! note
	It is highly recommended that you use SSH with GitHub. If you haven't already, make sure that you [setup Git](https://docs.github.com/en/github/getting-started-with-github/set-up-git) and [add an SSH key to your GitHub account](https://help.github.com/articles/generating-ssh-keys/) before proceeding.

In this guide, SSH will be used to interact with Git.

```no-highlight
$ git clone git@github.com:yourusername/nautobot.git
Cloning into 'nautobot'...
remote: Enumerating objects: 231, done.
remote: Counting objects: 100% (231/231), done.
remote: Compressing objects: 100% (147/147), done.
remote: Total 56705 (delta 134), reused 145 (delta 84), pack-reused 56474
Receiving objects: 100% (56705/56705), 27.96 MiB | 34.92 MiB/s, done.
Resolving deltas: 100% (44177/44177), done.
$ ls nautobot/
CHANGELOG.md     README.md    docs        nautobot.code-workspace  site
CONTRIBUTING.md  contrib      manage.py   poetry.lock              tasks.py
LICENSE.txt      development  mkdocs.yml  pyproject.toml           upgrade.sh
NOTICE           dist         nautobot    scripts
```

### About Remote Repos

Git refers to remote repositories as *remotes*. When you make your initial clone of your fork, Git defaults to naming this remote `origin`. Throughout this documentation, the following remote names will be used:

- `origin` - The default remote name used to refer to *your fork of Nautobot*
- `upstream` - The main remote used to refer to the *official Nautobot repository*

### Setting up your Remotes

Remote repos are managed using the `git remote` command.

Upon cloning Nautobot for the first time, you will have only a single remote:

```no-highlight
$ git remote -v
origin	git@github.com:yourusername/nautobot.git (fetch)
origin	git@github.com:yourusername/nautobot.git (push)
```

Add the official Nautobot repo as a the `upstream` remote:

```no-highlight
$ git remote add upstream git@github.com:nautobot/nautobot.git
```

View your remotes again to confirm you've got both `origin` pointing to your fork and `upstream` pointing to the official repo:

```no-highlight
$ git remote -v
origin	git@github.com:yourusername/nautobot.git (fetch)
origin	git@github.com:yourusername/nautobot.git (push)
upstream	git@github.com:nautobot/nautobot.git (fetch)
upstream	git@github.com:nautobot/nautobot.git (push)
```

You're now ready to proceed to the next steps.

!!! hint
	You will always **push** changes to `origin` (your fork) and **pull** changes from `upstream` (official repo).

### Creating a Branch

Before you make any changes, always create a new branch. In the majority of cases, you'll always want to create your branches from the `develop` branch.

Before you ever create a new branch, always  checkout the `develop` branch and make sure you you've got the latest changes from `upstream`.

```no-highlight
$ git checkout develop
$ git pull upstream develop
```

!!! warning
	If you do not do this, you run the risk of having merge conflicts in your branch, and that's never fun to deal with. Trust us on this one.

Now that you've got the latest upstream changes, create your branch. It's convention to always prefix your branch name with your GitHub username, separated by hyphens. For example:

```no-highlight
$ git checkout -b yourusername-myfeature
```

## Enabling Pre-Commit Hooks

Nautobot ships with a [Git pre-commit hook](https://githooks.com/) script that automatically checks for style compliance and missing database migrations prior to committing changes. This helps avoid erroneous commits that result in CI test failures.

!!! note
	This pre-commit hook currently only supports the Python Virtual Environment Workflow.

You are encouraged to enable it by creating a link to `scripts/git-hooks/pre-commit`:

```no-highlight
$ cd .git/hooks/
$ ln -s ../../scripts/git-hooks/pre-commit
```

## Setting up your Development Environment

Getting started with Nautobot development is pretty straightforward, and should feel very familiar to anyone with Django development experience. We can recommend either a [Docker Compose workflow](#docker-compose-workflow) (if you don't want to install dependencies such as PostgreSQL and Redis directly onto your system) or a [Python virtual environment workflow](#python-virtual-environment-workflow).

### Docker Compose Workflow

This workflow uses [Docker](https://docs.docker.com/get-docker/) and [Docker Compose](https://docs.docker.com/compose/) and assumes that you have them installed.

For the Docker Compose workflow, Nautobot uses [Invoke](http://docs.pyinvoke.org/en/latest/index.html) as a replacement for Make. Invoke was chosen because it is less arcane than make. Instead of a `Makefile`, Invoke reads the `tasks.py` in the project root.

!!! note
    Although the Docker Compose workflow uses containers, it is important to note that the containers are running the local repository code on your machine. Changes you make to your local code will be picked up and executed by the containers.

#### Install Invoke

Because it is used to execute all common Docker workflow tasks, Invoke must be installed for your user environment. On most systems, if you're installing without root/superuser permissions, the default will install into your local user environment.

```no-highlight
$ pip3 install invoke
```

If you run into issues, you may also deliberately tell `pip3` to install into your user environment by adding the `--user` flag:

```no-highlight
$ pip3 install --user invoke
```

Please see the [official documentation on Pip user installs](https://pip.pypa.io/en/stable/user_guide/#user-installs) for more information.

#### List Invoke Tasks

Now that you have an `invoke` command, list the tasks defined in `tasks.py`:

```no-highlight
$ invoke --list
Available tasks:

  black               Check Python code style with Black.
  build               Build all docker images.
  cli                 Launch a bash shell inside the running Nautobot container.
  createsuperuser     Create a new Nautobot superuser account (default: "admin"), will prompt for password.
  dumpdata            Dump database data into file, only for development environment use.
  debug               Start Nautobot and its dependencies in debug mode.
  destroy             Destroy all containers and volumes.
  flake8              Check for PEP8 compliance and other style issues.
  loaddata            Load data from file into database, only for development environment use.
  makemigrations      Perform makemigrations operation in Django.
  migrate             Perform migrate operation in Django.
  nbshell             Launch an interactive nbshell session.
  post-upgrade        Performs Nautobot common post-upgrade operations using a single entrypoint.
  restart             Gracefully restart all containers.
  start               Start Nautobot and its dependencies in detached mode.
  stop                Stop Nautobot and its dependencies.
  tests               Run all tests and linters.
  unittest            Run Nautobot unit tests.
  unittest-coverage   Report on code test coverage as measured by 'invoke unittest'.
  vscode              Launch Visual Studio Code with the appropriate Environment variables to run in a container.
```

#### Using Docker with Invoke

A development environment can be easily started up from the root of the project using the following commands:

- `invoke build` - Builds Nautobot docker images
- `invoke migrate` - Performs database migration operation in Django
- `invoke createsuperuser` - Creates a superuser account for the Nautobot application
- `invoke debug` - Starts Docker containers for Nautobot, PostgreSQL, Redis, Celery, and the RQ worker in debug mode and attaches their output to the terminal in the foreground. You may enter Control-C to stop the containers.

Additional useful commands for the development environment:

- `invoke start` - Starts all Docker containers to run in the background with debug disabled
- `invoke stop` - Stops all containers created by `invoke start`

!!! tip
    To learn about advanced use cases within the Docker Compose workflow, see the [Docker Compose Advanced Use Cases](docker-compose-advanced-use-cases.md/) page.

!!! note
    If you are making edits to Nautobot's documentation in the Docker Compose workflow or otherwise needing to serve the docs locally, it is necessary to run a Python virtual environment:
    
    - Follow the steps in the Nautobot docs to [install poetry](#install-poetry) 
    - `poetry shell`
    - `poetry install`
    - `mkdocs serve`

Proceed to the [Working in your Development Environment](#working-in-your-development-environment) section

### Python Virtual Environment Workflow

This workflow uses Python and Poetry to work with your development environment locally. It requires that you install the required system dependencies on your system yourself.

There are a few things you'll need:

- A Linux system or environment
- A MySQL or PostgreSQL server, which can be installed locally [per the documentation](../../installation/#installing-nautobot-dependencies)
- A Redis server, which can also be [installed locally](../../installation/#installing-nautobot-dependencies)
- A supported version of Python
- A recent version of [Poetry](https://python-poetry.org/docs/#installation)

#### Install Poetry

[Poetry](https://python-poetry.org/docs/) is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update/remove) them for you. It will also manage virtual environments automatically, and allow for publishing packages to the [Python Package Index](https://pypi.org).

You may install Poetry in your user environment by running:

```no-highlight
$ curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
```

For detailed installation instructions, please see the [official Poetry installation guide](https://python-poetry.org/docs/#installation).

#### Install Hadolint

[Hadolint](https://github.com/hadolint/hadolint) is a tool used to validate and lint Dockerfiles to ensure we are following best practices. On macOS with [Homebrew](https://brew.sh/) you can install Hadolint by running:

```no-highlight
$ brew install hadolint
```

#### Creating a Python Virtual Environment

A Python [virtual environment](https://docs.python.org/3/tutorial/venv.html) (or *virtualenv*) is like a container for a set of Python packages. A virtualenv allow you to build environments suited to specific projects without interfering with system packages or other projects. When installed per the documentation, Nautobot uses a virtual environment in production.

For Nautobot development, we have selected Poetry, which will transparently create a virtualenv for you, automatically install all dependencies required for Nautobot to operate, and will also install the `nautobot-server` CLI command that you will utilize to interact with Nautobot from here on out.

Bootstrap your virtual environment using `poetry install`:

```no-highlight
$ poetry install
```

!!! hint
    If you are doing development or testing using MySQL, you may quickly install the `mysqlclient` library along with Nautobot by running `poetry install --extras mysql`.

This will create automatically create a virtualenv in your home directory, which houses a virtual copy of the Python executable and its related libraries and tooling. When running Nautobot for development, it will be run using the Python binary at found within the virtualenv.

Once created, you may activate the virtual environment using `poetry shell`:

```no-highlight
$ poetry shell
Spawning shell within /home/example/.cache/pypoetry/virtualenvs/nautobot-Ams_xyDt-py3.8

$ . /home/example/.cache/pypoetry/virtualenvs/nautobot-Ams_xyDt-py3.8/bin/activate
(nautobot-Ams_xyDt-py3.8) $
```

Notice that the console prompt changes to indicate the active environment. This updates the necessary system environment variables to ensure that any Python scripts are run within the virtual environment.

Observe also that the `python` interpreter is bound within the virtualenv:

```no-highlight
(nautobot-Ams_xyDt-py3.8) $ which python
/home/example/.cache/pypoetry/virtualenvs/nautobot-Ams_xyDt-py3.8/bin/python
```

To exit the virtual shell, use `exit`:

```no-highlight
(nautobot-Ams_xyDt-py3.8) $ exit
$
```

#### Working with Poetry

Poetry automatically installs your dependencies. However, if you need to install any additional dependencies this can be done with `pip`. For example, if you really like using `ipython` for development:

```no-highlight
(nautobot-Ams_xyDt-py3.8) $ pip3 install ipython
Collecting ipython
  Using cached ipython-7.20.0-py3-none-any.whl (784 kB)
  ...
```

It may not always be convenient to enter into the virtual shell just to run programs. You may also execute a given command ad hoc within the project's virtual shell by using `poetry run`:

```
$ poetry run mkdocs serve
```

Check out the [Poetry usage guide](https://python-poetry.org/docs/basic-usage/) for more tips.

#### Configuring Nautobot

!!! note
	Unless otherwise noted, all following commands should be executed inside the virtualenv.

!!! hint
	Use `poetry shell` to enter the virtualenv.

Nautobot's configuration file is `nautobot_config.py`.

##### Initializing a Config

You may also initialize a new configuration using `nautobot-server init`:

```no-highlight
$ nautobot-server init
Configuration file created at '/home/example/.nautobot/nautobot_config.py'
```

You may also specify alternate file locations. Please refer to [Configuring Nautobot](../../configuration) for how to do that.

##### Using the Development Config

A `nautobot_config.py` suitable for development purposes can be found at `development/nautobot_config.py`. You may customize the values there or utilize environment variables to override the default values.

If you want to use this file, initialize a config first, then copy this file to the default location Nautobot expects to find its config:

```no-highlight
$ cp development/nautobot_config.py ~/.nautobot/nautobot_config.py
```

##### Required Settings

A newly created configuration includes sane defaults. If you need to customize them, edit your `nautobot_config.py` and update the following settings as required:

* [`ALLOWED_HOSTS`](../../configuration/required-settings/#allowed_hosts): This can be set to `["*"]` for development purposes and must be set if `DEBUG=False`
* [`DATABASES`](../../configuration/required-settings/#databases): Database connection parameters, if different from the defaults
* **Redis settings**: Redis configuration requires multiple settings including [`CACHEOPS_REDIS`](../../configuration/required-settings/#cacheops_redis) and [`RQ_QUEUES`](../../configuration/required-settings/#rq_queues). The defaults should be fine for development.
* [`DEBUG`](../../configuration/optional-settings/#debug): Set to `True` to enable verbose exception logging and, if installed, the [Django debug toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/)
* [`EXTRA_INSTALLED_APPS`](../../configuration/optional-settings/#extra-applications): Optionally provide a list of extra Django apps/plugins you may desire to use for development

## Working in your Development Environment

Below are common commands for working your development environment.

### Creating a Superuser

You'll need to create a administrative superuser account to be able to log into the Nautobot Web UI for the first time. Specifying an email address for the user is not required, but be sure to use a very strong password.

| Docker Compose Workflow | Virtual Environment Workflow   |
|-------------------------|--------------------------------|
| `invoke createsuperuser`| `nautobot-server createsuperuser` |

### Starting the Development Server

Django provides a lightweight HTTP/WSGI server for development use. The development server automatically reloads Python code for each request, as needed. You don’t need to restart the server for code changes to take effect. However, some actions like adding files don’t trigger a restart, so you’ll have to restart the server in these cases.

!!! danger
    **DO NOT USE THIS SERVER IN A PRODUCTION SETTING.** The development server is for development and testing purposes only. It is neither performant nor secure enough for production use.

You can start the Nautobot development server with the `invoke start` command (if using Docker), or the `nautobot-server runserver` management command:

| Docker Compose Workflow | Virtual Environment Workflow   |
|-------------------------|--------------------------------|
| `invoke start`          | `nautobot-server runserver`    |

For example:

```no-highlight
$ nautobot-server runserver
Performing system checks...

System check identified no issues (0 silenced).
November 18, 2020 - 15:52:31
Django version 3.1, using settings 'nautobot.core.settings'
Starting development server at http://127.0.0.1:8080/
Quit the server with CONTROL-C.
```

!!! warning
    Do not use `poetry run nautobot-server runserver` as it will crash unless you also pass the `--noreload` flag, which somewhat defeats the purpose of using the development server. It is recommended to use `nautobot-server runserver` from within an active virtualenv (e.g. `poetry shell`). This is a [known issue with Django and Poetry](https://github.com/python-poetry/poetry/issues/2435).

Please see the [official Django documentation on `runserver`](https://docs.djangoproject.com/en/stable/ref/django-admin/#runserver) for more information.

You can then log into the development server at `localhost:8080` with the [superuser](#creating-a-superuser) you created.

### Starting the Interactive Shell

Nautobot provides an [interactive Python shell](../../administration/nautobot-shell) that sets up the server environment and gives you direct access to the database models for debugging. Nautobot extends this slightly to automatically import models and other utilities.

Run the Nautobot interactive shell with `invoke nbshell` (Docker) or the `nautobot-server nbshell` management command:

| Docker Compose Workflow | Virtual Environment Workflow   |
|-------------------------|--------------------------------|
| `invoke nbshell`        | `nautobot-server nbshell`      |

For example:

```bash
$ nautobot-server nbshell
### Nautobot interactive shell (localhost)
### Python 3.9.1 | Django 3.1.3 | Nautobot 1.0.0b1
### lsmodels() will show available models. Use help(<model>) for more info.
>>>
```

### Post-upgrade Operations

There will be times where you're working with the bleeding edge of Nautobot from the `develop` branch or feature branches and will need to pull in database changes or run server operations.

Get into the habit of running `nautobot-server post_upgrade` (or `invoke post-upgrade` when using Docker) after you pull in a major set of changes from Nautobot, which performs a handful of common operations (such as `migrate`) from a single command:

| Docker Compose Workflow | Virtual Environment Workflow   |
|-------------------------|--------------------------------|
| `invoke post-upgrade`   | `nautobot-server post_upgrade` |

Please see the [documentation on the `nautobot-server post_upgrade` command](../administration/nautobot-server.md#post_upgrade) for more information.

### Reinstalling Nautobot

!!! note
    This mostly applies to working with Nautobot in a virtualenv, since Docker containers are typically rebuilt when the code changes.

Sometimes when files are renamed, moved, or deleted and you've been working in the same environment for a while, you can encounter weird behavior. If this happens, don't panic and nuke your environment.

First, use `pip3` to explicitly uninstall the Nautobot package from the environment:

```no-highlight
$ pip3 uninstall -y nautobot
Found existing installation: nautobot 1.0.0b2
Uninstalling nautobot-1.0.0b2:
  Successfully uninstalled nautobot-1.0.0b2
```

Then try to just have Poetry do the right thing by telling it to install again:

```no-highlight
$ poetry install
Installing dependencies from lock file

No dependencies to install or update

Installing the current project: nautobot (1.0.0-beta.2)
```

### Running Tests

Throughout the course of development, it's a good idea to occasionally run Nautobot's test suite to catch any potential errors. Tests come in two primary flavors: Unit tests and integration tests.

#### Unit Tests

Unit tests are automated tests written and run to ensure that a section of the Nautobot application (known as the "unit") meets its design and behaves as intended and expected. Most commonly as a developer of or contributor to Nautobot you will be writing unit tests to exercise the code you have written. Unit tests are not meant to test how the application behaves, only the individual blocks of code, therefore use of mock data and phony connections is common in unit test code. As a guiding principle, unit tests should be fast, because they will be executed quite often.

By Nautobot convention, unit tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `unit`. The base test case class `nautobot.utilities.testing.TestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing view and API test cases in the Nautobot test suite utilities inherit from this class.

!!! warning
    New unit tests **must always** inherit from `nautobot.utilities.testing.TestCase`. Do not use `django.test.TestCase`.

Wrong:
```python
from django.test import TestCase


class MyTestCase(TestCase):
    ...
```

Right:
```python
from nautobot.utilities.testing import TestCase


class MyTestCase(TestCase):
    ...
```

Unit tests are run using the `invoke unittest` command (if using the Docker development environment) or the `nautobot-server test` command:

| Docker Compose Workflow | Virtual Environment Workflow                                                    |
|-------------------------|---------------------------------------------------------------------------------|
| `invoke unittest`       | `nautobot-server --config=nautobot/core/tests/nautobot_config.py test nautobot` |

!!! info
    By default `invoke unittest` will start and run the unit tests inside the Docker development container; this ensures that PostgreSQL and Redis servers are available during the test. However, if you have your environment configured such that `nautobot-server` can run locally, outside of the Docker environment, you may wish to set the environment variable `INVOKE_NAUTOBOT_LOCAL=True` to execute these tests in your local environment instead.  See the [Invoke configuration](#invoke-configuration) for more information.

In cases where you haven't made any changes to the database (which is most of the time), you can append the `--keepdb` argument to this command to reuse the test database between runs. This cuts down on the time it takes to run the test suite since the database doesn't have to be rebuilt each time.

| Docker Compose Workflow    | Virtual Environment Workflow                                                             |
|----------------------------|------------------------------------------------------------------------------------------|
| `invoke unittest --keepdb` | `nautobot-server --config=nautobot/core/tests/nautobot_config.py test --keepdb nautobot` |

!!! note
    Using the `--keepdb` argument will raise errors if you've modified any model fields since the previous test run.

!!! warning
	In some cases when tests fail and exit uncleanly it may leave the test database in an inconsistent state. If you encounter errors about missing objects, remove `--keepdb` and run the tests again.

#### Integration Tests

Integration tests are automated tests written and run to ensure that the Nautobot application behaves as expected when being used as it would be in practice. By contrast to unit tests, where individual units of code are being tested, integration tests rely upon the server code actually running, and web UI clients or API clients to make real connections to the service to exercise actual workflows, such as navigating to the login page, filling out the username/passwords fields, and clicking the "Log In" button.

Integration testing is much more involved, and builds on top of the foundation laid by unit testing. As a guiding principle, integration tests should be comprehensive, because they are the last mile to asserting that Nautobot does what it is advertised to do. Without integration testing, we have to do it all manually, and that's no fun for anyone!

Running integrations tests requires the use of Docker at this time. They can be directly invoked using `nautobot-server test` just as unit tests can, however, a headless Firefox browser provided by Selenium is required. Because Selenium installation and setup is complicated, we have included a configuration for this to work out of the box using Docker.

The Selenium container is running a standalone, headless Firefox "web driver" browser that can be remotely controlled by Nautobot for use in integration testing.

Before running integration tests, the `selenium` container must be running. If you are using the Docker Compose workflow, it is automatically started for you. For the Virtual Environment workflow, you must start it manually.

| Docker Compose Workflow   | Virtual Environment Workflow      |
|---------------------------|-----------------------------------|
| (automatic)               | `invoke start --service selenium` |

By Nautobot convention, integration tests must be [tagged](https://docs.djangoproject.com/en/stable/topics/testing/tools/#tagging-tests) with `integration`. The base test case class `nautobot.utilities.testing.integration.SeleniumTestCase` has this tag, therefore any test cases inheriting from that class do not need to be explicitly tagged. All existing integration test cases in the Nautobot test suite utilities inherit from this class.

!!! warning
    New integration tests **must always** inherit from `nautobot.utilities.testing.integration.SeleniumTestCase` and added in the `integration` directory in the `tests` directory of an inner Nautobot application. Do not use any other base class for integration tests.

We never want to risk running the unit tests and integration tests at the same time. The isolation from each other is critical to a clean and managable continuous development cycle.

Wrong:
```python
from django.contrib.staticfiles.testing import StaticLiveServerTestCase


class MyIntegrationTestCase(StaticLiveServerTestCase):
    ...
```

Right:
```python
from nautobot.utilities.testing.integration import SeleniumTestCase


class MyIntegrationTestCase(SeleniumTestCase):
    ...
```

Integration tests are run using the `invoke integration-test` command. All integration tests must inherit from `nautobot.utilities.testing.integration.SeleniumTestCase`, which itself is tagged with `integration`. A custom test runner has been implemented to automatically skip any test case tagged with `integration` by default, so normal unit tests run without any concern. To run the integration tests the `--tag integration` argument must be passed to `nautobot-server test`.

| Docker Compose Workflow   | Virtual Environment Workflow                                                                      |
|---------------------------|---------------------------------------------------------------------------------------------------|
| `invoke integration-test` | `nautobot-server --config=nautobot/core/tests/nautobot_config.py test --tag integration nautobot` |

!!! info
    The same arguments supported by `invoke unittest` are supported by `invoke integration-test`. The key difference being the dependency upon the Selenium container, and inclusion of the `integration` tag.

!!! tip
    You may also use `invoke integration-test` in the Virtual Environment workflow given that the `selenium` container is running, and that the `INVOKE_NAUTOBOT_LOCAL=True` environment variable has been set.

##### Customizing Integration Test Executions

The following environment variables can be provided when running tests to customize where Nautobot looks for Selenium and where Selenium looks for Nautobot. If using the default setup documented above, there is no need to customize these.

- `NAUTOBOT_SELENIUM_URL` - The URL used by the Nautobot test runner to remotely control the headless Selenium Firefox node. You can provide your own, but it must be a [`Remote` WebDriver](https://selenium-python.readthedocs.io/getting-started.html#using-selenium-with-remote-webdriver). (Default: `http://localhost:4444/wd/hub`; for Docker: `http://selenium:4444/wd/hub`)
- `NAUTOBOT_SELENIUM_HOST` - The hostname used by the Selenium WebDriver to access Nautobot using Firefox. (Default: `host.docker.internal`; for Docker: `nautobot`)

### Verifying Code Style

To enforce best practices around consistent [coding style](style-guide.md), Nautobot uses [Flake8](https://flake8.pycqa.org/) and [Black](https://black.readthedocs.io/). You should run both of these commands and ensure that they pass fully with regard to your code changes before opening a pull request upstream.

| Docker Compose Workflow | Virtual Environment Workflow |
|-------------------------|------------------------------|
| `invoke flake8`         | `flake8`                     |
| `invoke black`          | `black`                      |

## Working on Documentation

Some features require documentation updates or new documentation to be written. The documentation files can be found in the `docs` directory. To preview these changes locally, you can use `mkdocs`.

### Installing `mkdocs`

If you are using the poetry-based workflow, `mkdocs` should already be installed in your environment. This section mostly applies if you are using Docker to manage your development environment.

The `mkdocs` command can be installed via pip, either globally or in your virtual environment.

```no-highlight
$ pip3 install mkdocs mkdocs-include-markdown-plugin
```

### Writing Documentation

Once the `mkdocs` command has been installed, you can preview the documentation
using `mkdocs serve`,  which should start a web server at `http://localhost:8001`.

Documentation is written in Markdown. If you need to add additional pages or sections to the documentation, you can add them to `mkdocs.yml` at the root of the repository.

## Submitting Pull Requests

Once you're happy with your work and have verified that all tests pass, commit your changes and push it upstream to your fork. Always provide descriptive (but not excessively verbose) commit messages. When working on a specific issue, be sure to reference it.

```no-highlight
$ git commit -m "Closes #1234: Add IPv5 support"
$ git push origin
```

Once your fork has the new commit, submit a [pull request](https://github.com/nautobot/nautobot/compare) to the Nautobot repo to propose the changes. Be sure to provide a detailed accounting of the changes being made and the reasons for doing so.

Once submitted, a maintainer will review your pull request and either merge it or request changes. If changes are needed, you can make them via new commits to your fork: The pull request will update automatically.

!!! note
    Remember, pull requests are entertained only for **accepted** issues. If an issue you want to work on hasn't been approved by a maintainer yet, it's best to avoid risking your time and effort on a change that might not be accepted.

## Troubleshooting

Below are common issues you might encounter in your development environment and how to address them.

### FATAL: sorry, too many clients already

When using `nautobot-server runserver` to do development you might run into a traceback that looks something like this:

```no-highlight
Exception Type: OperationalError at /extras/tags/
Exception Value: FATAL:  sorry, too many clients already
```

The `runserver` development server is multi-threaded by default, which means that every request is creating its own connection. If you are doing some local testing or development that is resulting in a lot of connections to the database, pass `--nothreading` to the runserver command to disable threading:

```no-highlight
$ nautobot-server runserver --nothreading
```
