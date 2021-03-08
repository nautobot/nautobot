# Getting Started

## Forking the Repo

Assuming you'll be working on your own fork, your first step will be to fork the [official git repository](https://github.com/nautobot/nautobot). You can then clone your GitHub fork locally for development:

(If you're a maintainer who's going to be working directly with the official repo, you may skip this step.)

```no-highlight
$ git clone https://github.com/youruseraccount/nautobot.git
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

The Nautobot project utilizes three persistent git branches to track work:

* `main` - Serves as a snapshot of the current stable release
* `develop` - All development on the upcoming stable release occurs here
* `feature` - Tracks work on an upcoming major release

Typically, you'll base pull requests off of the `develop` branch, or off of `feature` if you're working on a new major release. **Never** merge pull requests into the `main` branch, which receives merged only from the `develop` branch.

## Enabling Pre-Commit Hooks

Nautobot ships with a [git pre-commit hook](https://githooks.com/) script that automatically checks for style compliance and missing database migrations prior to committing changes. This helps avoid erroneous commits that result in CI test failures. You are encouraged to enable it by creating a link to `scripts/git-hooks/pre-commit`:

```no-highlight
$ cd .git/hooks/
$ ln -s ../../scripts/git-hooks/pre-commit
```

## Setting up a Development Environment

Getting started with Nautobot development is pretty straightforward, and should feel very familiar to anyone with Django development experience. We can recommend either a [Docker Compose workflow](#docker-development-environment-workflow) (if you don't want to install dependencies such as PostgreSQL and Redis directly onto your system) or a [Python virtual environment workflow](#python-virtual-environment-workflow).

### Docker Development Environment Workflow

A development environment can be easily started up from the root of the project by installing the [Invoke](http://docs.pyinvoke.org/en/latest/invoke.html) Python library and then using the following commands:

- `invoke build` - builds Nautobot docker image.
- `invoke createsuperuser` - creates a super user for the Django application.
- `invoke debug` - starts linux system, postgreSQL, redis and work from docker compose and attaches their output to the shell (enter Control-C to stop the containers).

Additional useful commands for the development environment:

- `invoke start` - starts all docker compose containers to run in the background.
- `invoke stop` - stops all containers created by `invoke start`.

#### Docker-Compose Override

To modify the docker compose file without making changes to the repository, create a file inside ```./development``` called ```docker-compose.override.yml```.
This file will override any configuration in the main docker-compose file. Docker documentation can be found [here](https://docs.docker.com/compose/extends/).

#### Docker-Compose Override - Automatically Create Super User

There may be times where you want to bootstrap Nautobot with an already created user and token for either quick access or running within a CI/CD pipeline. Below will detail the steps required to bootstrap Nautobot with a user and token.

```bash
edit development/docker-compose.override.yml
```

```yaml
---
services:
  nautobot:
    env_file:
      - "override.env"
```

The `docker-entrypoint.sh` copied in during the Docker image build, but not set as the entrypoint until you override the entrypoint as seen above. The `docker-entrypoint.sh` will run any migrations and then look for specific variables set to create the super user. The **override.env** should look like the following:

```bash
# Super user information, but creation is disabled by default
CREATE_SUPERUSER=true
SUPERUSER_NAME=admin
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=admin
SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
```

!!! warning
    Please name the **.env** file ``override.env`` to prevent credentials from being checked into Git. ``override.env`` is set in the ``.gitignore`` file.

These will create the user with the specified username, email, password, and API token.

After these two files are created, you can use the normal **invoke** commands to manage the development containers.

### Docker Development - Microsoft Visual Studio Code

The `devcontainer.json` and `nautobot.code-workspace` files are provided to ease development when using VS Code and the Remote-Containers extension. After opening the project directory in VS Code in a
supported environment, you will be prompted by VS Code to "Reopen in Container" and "Open Workspace". Select "Reopen in Container" to build and start the dev containers. Once your window is
connected to the container, you can open the workspace which enables support for Run/Debug.

To start Nautobot, select "Run Without Debugging" or "Start Debugging" from the Run menu. Once Nautobot has started, you will be prompted to open a browser to connect to Nautobot.

#### Special Workflow for Containers on Remote Servers

A slightly different workflow is needed when the container is running on a ssh connected server. VScode will not offer the "Reopen in Container" option on a remote connected server.

After `invoke build` use `docker-compose` as follows to start the containers. This prevents the HTTP service from automatically starting inside the container.

```bash
# change current directory
cd development

# Start all services using docker-compose
docker-compose -f docker-compose.yml -f docker-compose.debug.yml up
```

Now open the VScode `Docker` extension. In the `CONTAINERS/development` section
right click on a running container and select the `Attach Visual Studio Code` menu item.

The `Select the container to attach VScode` input field provides a list of running containers.

Click on `development_nautobot_1` to use VScode inside the container.

The `devcontainer` will startup now. As a last step open the folder `/opt/nautobot` in VScode.

### Python Virtual Environment Workflow

There are a few things you'll need:

- A Linux system or environment
- A PostgreSQL server, which can be installed locally [per the documentation](/installation/#installing-nautobot-dependencies)
- A Redis server, which can also be [installed locally](/installation/#installing-nautobot-dependencies)
- A supported version of Python
- A recent version of [Poetry](https://python-poetry.org/docs/#installation)

#### What is Poetry?

Poetry is a tool for dependency management and packaging in Python. It allows you to declare the libraries your project depends on and it will manage (install/update) them for you. It will also manage virtual environments, and allow for publishing packages to the [Python Package Index](https://pypi.org).

You may install Poetry by running:

```bash
$ curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -
```

For detailed installation instructions, please see the [official Poetry installation guide](https://python-poetry.org/docs/#installation).

#### Creating a Python Virtual Environment

A [virtual environment](https://docs.python.org/3/tutorial/venv.html) is like a container for a set of Python packages. They allow you to build environments suited to specific projects without interfering with system packages or other projects. When installed per the documentation, Nautobot uses a virtual environment in production.

For Nautobot development, we have selected Poetry, which will transparently create a virtualenv for you, automatically install all dependencies required for Nautobot to operate, and will also install the `nautobot-server` CLI command that you will utilize to interact with Nautobot from here on out.

Bootstrap your virtual environment using `poetry install`.

```bash
$ poetry install
```

This will create automatically create a virtualenv in your home directory, which houses a virtual copy of the Python executable and its related libraries and tooling. When running Nautobot for development, it will be run using the Python binary at found within the virtualenv.

Once created, you may activate the virtual environment using `poetry shell`:

```bash
$ poetry shell
Spawning shell within /home/example/.cache/pypoetry/virtualenvs/nautobot-Ams_xyDt-py3.8

$ . /home/example/.cache/pypoetry/virtualenvs/nautobot-Ams_xyDt-py3.8/bin/activate
(nautobot-Ams_xyDt-py3.8) $
```

Notice that the console prompt changes to indicate the active environment. This updates the necessary system environment variables to ensure that any Python scripts are run within the virtual environment.

Observe also that the `python` interpreter is bound within the virtualenv:

```bash
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
$ poetry run nautobot-server
```

Check out the [Poetry usage guide](https://python-poetry.org/docs/basic-usage/) for more tips.

#### Configuring Nautobot

Initialize a new configuration using `nautobot-server init`:

```bash
$ nautobot-server init
Configuration file created at '/home/example/.nautobot/nautobot_config.py'
```

You may also specify alternate file locations. Please refer to [Configuring Nautobot](../../configuration) for how to do that.

The newly created configuration includes sane defaults. If you need to customize them, edit your `nautobot_config.py` and update the following settings as required:

* `ALLOWED_HOSTS`: This can be set to `['*']` for development purposes and must be set if `DEBUG=False`
* `DATABASES`: PostgreSQL database connection parameters, if different from the defaults
* `REDIS`: Redis configuration, if different from the defaults
* `DEBUG`: Set to `True` to enable verbose exception logging and, if installed, the [Django debug toolbar](https://django-debug-toolbar.readthedocs.io/en/latest/)
* `EXTRA_INSTALLED_APPS`: Optionally provide a list of extra Django apps/plugins you may desire to use for development

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

Django provides an interactive Python shell that sets up the server environment and gives you direct access to the database models for debugging. Nautobot extends this slightly to automatically import models and other utilities.

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

In cases where you haven't made any changes to the database (which is most of the time), you can append the `--keepdb` argument to this command to reuse the test database between runs. This cuts down on the time it takes to run the test suite since the database doesn't have to be rebuilt each time. (Note that this argument will cause errors if you've modified any model fields since the previous test run.)

```no-highlight
$ nautobot-server test --keepdb
```

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
