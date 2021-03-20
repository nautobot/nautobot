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

  black             Check Python code style with Black
  build             Build all docker images.
  cli               Launch a bash shell inside the running Nautobot container.
  coverage-report   Run coverage report
  coverage-run      Run tests
  createsuperuser   Create a new superuser in django (default: admin), will prompt for password.
  debug             Start Nautobot and its dependencies in debug mode.
  destroy           Destroy all containers and volumes.
  flake8            Check PEP8 compliance and other style issues
  makemigrations    Run Make Migration in Django.
  migrate           Perform migrate operation in Django.
  nbshell           Launch a nbshell session.
  start             Start Nautobot and its dependencies in detached mode.
  stop              Stop Nautobot and its dependencies.
  tests             Run all tests
  vscode            Launch Visual Studio Code with the appropriate Environment variables to run in a container.
```

#### Using Docker with Invoke

A development environment can be easily started up from the root of the project using the following commands:

- `invoke build` - Builds Nautobot docker images
- `invoke createsuperuser` - Creates a superuser account for the Nautobot application
- `invoke debug` - Starts Docker containers for Nautobot, PostgreSQL, Redis, and the Jobs worker in debug mode and attaches their output to the terminal in the foreground. You may enter Control-C to stop the containers.

Additional useful commands for the development environment:

- `invoke start` - Starts all Docker containers to run in the background with debug disabled
- `invoke stop` - Stops all containers created by `invoke start`

#### Working with Docker Compose

The files related to the Docker container environment used for development can be found inside of the `development` directory at the root of the project.

In this directory you'll find the following core files:

- `Dockerfile` - Docker container definition for Nautobot

- `docker-compose.yml` - Docker service containers and their relationships to the Nautobot container
- `docker-entrypoint.sh` - Commands and operations ran once Nautobot container is started including database migrations and optionally creating a superuser
- `dev.env` - Environment variables used to setup the container services
- `nautobot_config.py` - Nautobot configuration file

#### Docker-Compose Overrides

If you require changing any of the defaults found in `docker-compose.yml`,  create a file inside the```development``` directory called ```docker-compose.override.yml```.

This file will override any configuration in the main `docker-compose.yml` file, without making changes to the repository.

Please see the [official documentation on extending Docker Compose](https://docs.docker.com/compose/extends/) for more information.

##### Automatically Creating a SuperUser

There may be times where you want to bootstrap Nautobot with a a superuser account and API token already created for quick access or for running within a CI/CD pipeline. Below will detail the steps required to bootstrap Nautobot with a user and token.

Create `development/docker-compose.override.yml` with the following contents:

```yaml
---
services:
  nautobot:
    env_file:
      - "override.env"
```

The `docker-entrypoint.sh` script will run any migrations and then look for specific variables set to create the superuser. The `docker-entrypoint.sh` script is copied in during the Docker image build and will read from the default `dev.env` as the `env_file` until you override it as seen above.

 Any variables defined in this file will override the defaults. The `override.env` should look like the following:

```bash
# Superuser information. CREATE_SUPERUSER defaults to false.
CREATE_SUPERUSER=true
SUPERUSER_NAME=admin
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=admin
SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
```

!!! warning
    Please name the **.env** file ``override.env`` to prevent credentials from accidentally being checked into Git as ``override.env`` is set in the ``.gitignore`` file.

The variables defined above within `override.env` will signal the `docker-entrypoint.sh` script to create the superuser with the specified username, email, password, and API token.

After these two files are created, you can use the `invoke` tasks to manage the development containers.

#### Microsoft Visual Studio Code Integration

For users of Microsoft Visual Studio Code, several files are included to ease development and integrate with the [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers). The following related files are found relative to the root of the project:

- `.devcontainers/devcontainer.json` - Dev. container definition
- `nautobot.code-workspace` - VS Code workspace configuration for Nautobot
- `development/docker-compose.debug.yml` - Docker Compose file with debug configuration for VS Code

After opening the project directory in VS Code in a supported environment, you will be prompted by VS Code to **Reopen in Container** and **Open Workspace**. Select **Reopen in Container** to build and start the development containers. Once your window is connected to the container, you can open the workspace which enables support for Run/Debug.

To start Nautobot, select **Run Without Debugging** or **Start Debugging** from the Run menu. Once Nautobot has started, you will be prompted to open a browser to connect to Nautobot.

##### Special Workflow for Containers on Remote Servers

A slightly different workflow is needed when your development container is running on a remotely-connected server (such as with SSH). VS Code will not offer the **Reopen in Container** option on a remote server.

To work with remote containers, after `invoke build` use `docker-compose` as follows to start the containers. This prevents the HTTP service from automatically starting inside the container:

```no-highlight
$ cd development
$ docker-compose -f docker-compose.yml -f docker-compose.debug.yml up
```

- Now open the VS Code Docker extension. In the `CONTAINERS/development` section, right click on a running container and select the **Attach Visual Studio Code** menu item.
- The **Select the container to attach VS Code** input field provides a list of running containers.
- Click on `development_nautobot_1` to use VS Code inside the container. The `devcontainer` will startup now.
- As a last step open the folder `/opt/nautobot` in VS Code.

### Python Virtual Environment Workflow

This workflow uses Python and Poetry to work with your development environment locally. It requires that you install the required system dependencies on your system yourself.

There are a few things you'll need:

- A Linux system or environment
- A PostgreSQL server, which can be installed locally [per the documentation](../../installation/#installing-nautobot-dependencies)
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

#### Creating a Python Virtual Environment

A Python [virtual environment](https://docs.python.org/3/tutorial/venv.html) (or *virtualenv*) is like a container for a set of Python packages. A virtualenv allow you to build environments suited to specific projects without interfering with system packages or other projects. When installed per the documentation, Nautobot uses a virtual environment in production.

For Nautobot development, we have selected Poetry, which will transparently create a virtualenv for you, automatically install all dependencies required for Nautobot to operate, and will also install the `nautobot-server` CLI command that you will utilize to interact with Nautobot from here on out.

Bootstrap your virtual environment using `poetry install`:

```no-highlight
$ poetry install
```

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
```
(nautobot-Ams_xyDt-py3.8) $ exit
$
```

#### Working with Poetry

Poetry automatically installs your dependencies. However, if you need to install any additional dependencies this can be done with `pip`. For example, if you really like using `ipython` for development:

```no-highlight
(nautobot-Ams_xyDt-py3.8) $ python -m pip install ipython
Collecting ipython
  Using cached ipython-7.20.0-py3-none-any.whl (784 kB)
  ...
```

It may not always be convenient to enter into the virtual shell just to run programs. You may also execute a given command ad hoc within the project's virtual shell by using `poetry run`:

```
$ poetry run mkdocs serve
```

Check out the [Poetry usage guide](https://python-poetry.org/docs/basic-usage/) for more tips.	

!!! note
	Unless otherwise noted, all following commands should be executed inside the virtualenv.

!!! hint
	Use `poetry shell` to enter the virtualenv.

#### Configuring Nautobot

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
* [`DATABASES`](../../configuration/required-settings/#databases): PostgreSQL database connection parameters, if different from the defaults
* **Redis settings**: Redis configuration requires multiple settings including [`CACHEOPS_REDIS`](../../configuration/required-settings/#cacheops_redis) and [`RQ_QUEUES`](../../configuration/required-settings/#rq_queues). The defaults should be fine for development.
* [`DEBUG`](../../configuration/optional-settings/#debug): Set to `True` to enable verbose exception logging and, if installed, the [Django debug toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/)
* [`EXTRA_INSTALLED_APPS`](../../configuration/optional-settings/#extra-applications): Optionally provide a list of extra Django apps/plugins you may desire to use for development

#### Starting the Development Server

Django provides a lightweight, auto-updating HTTP/WSGI server for development use.

Run the Nautobot development server with the `runserver` management command:

```no-highlight
$ nautobot-server runserver
Performing system checks...

System check identified no issues (0 silenced).
November 18, 2020 - 15:52:31
Django version 3.1, using settings 'nautobot.core.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

This ensures that your development environment is now complete and operational. Any changes you make to the code base will be automatically adapted by the development server.

#### Starting the Interactive Shell

Nautobot provides an [interactive Python shell](../../administration/nautobot-shell) that sets up the server environment and gives you direct access to the database models for debugging. Nautobot extends this slightly to automatically import models and other utilities.

Run the Nautobot interactive shell with the `nbshell` management command:

```bash
$ nautobot-server nbshell
### Nautobot interactive shell (localhost)
### Python 3.9.1 | Django 3.1.3 | Nautobot 1.0.0b1
### lsmodels() will show available models. Use help(<model>) for more info.
>>>
```

## Running Tests

Throughout the course of development, it's a good idea to occasionally run Nautobot's test suite to catch any potential errors. Tests are run using the `test` management command:

```no-highlight
$ nautobot-server test
```

In cases where you haven't made any changes to the database (which is most of the time), you can append the `--keepdb` argument to this command to reuse the test database between runs. This cuts down on the time it takes to run the test suite since the database doesn't have to be rebuilt each time.

!!! note
	Using the `--keepdb` argument will cause errors if you've modified any model fields since the previous test run.

```no-highlight
$ nautobot-server test --keepdb
```

!!! warning
	In some cases when tests fail and exit uncleanly it may leave the test database in an inconsistent state. If you encounter errors about missing objects, remove `--keepdb` and run the tests again.

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
