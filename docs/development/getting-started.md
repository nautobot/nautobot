# Getting Started

## Forking the Repo

Assuming you'll be working on your own fork, your first step will be to fork the [official git repository](https://github.com/netbox-community/netbox). (If you're a maintainer who's going to be working directly with the official repo, skip this step.) You can then clone your GitHub fork locally for development:

```no-highlight
$ git clone https://github.com/youruseraccount/netbox.git
Cloning into 'netbox'...
remote: Enumerating objects: 231, done.
remote: Counting objects: 100% (231/231), done.
remote: Compressing objects: 100% (147/147), done.
remote: Total 56705 (delta 134), reused 145 (delta 84), pack-reused 56474
Receiving objects: 100% (56705/56705), 27.96 MiB | 34.92 MiB/s, done.
Resolving deltas: 100% (44177/44177), done.
$ ls netbox/
base_requirements.txt  contrib          docs         mkdocs.yml  NOTICE     requirements.txt  upgrade.sh
CHANGELOG.md           CONTRIBUTING.md  LICENSE.txt  netbox      README.md  scripts
```

The NetBox project utilizes three persistent git branches to track work:

* `master` - Serves as a snapshot of the current stable release
* `develop` - All development on the upcoming stable release occurs here
* `feature` - Tracks work on an upcoming major release

Typically, you'll base pull requests off of the `develop` branch, or off of `feature` if you're working on a new major release. **Never** merge pull requests into the `master` branch, which receives merged only from the `develop` branch.

## Enabling Pre-Commit Hooks

NetBox ships with a [git pre-commit hook](https://githooks.com/) script that automatically checks for style compliance and missing database migrations prior to committing changes. This helps avoid erroneous commits that result in CI test failures. You are encouraged to enable it by creating a link to `scripts/git-hooks/pre-commit`:

```no-highlight
$ cd .git/hooks/
$ ln -s ../../scripts/git-hooks/pre-commit
```

## Setting up a Development Environment

Getting started with NetBox development is pretty straightforward, and should feel very familiar to anyone with Django development experience. We can recommend either a [Docker Compose workflow](#docker-development-environment-workflow) (if you don't want to install dependencies such as PostgreSQL and Redis directly onto your system) or a [Python virtual environment workflow](#python-virtual-environment-workflow)

### Docker Development Environment Workflow

A development environment can be easily started up from the root of the project by installing the [Invoke](http://docs.pyinvoke.org/en/latest/invoke.html) Python library and then using the following commands:

- `invoke build` - builds Netbox docker image.
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
  netbox:
    env_file:
      - "override.env"
    entrypoint: "/tmp/grimlock/docker-entrypoint.sh"
    command: "python /opt/grimlock/netbox/manage.py runserver 0.0.0.0:8000 --insecure"

```

The `docker-entrypoint.sh` copied in during the Docker image build, but not set as the entrypoint until you override the entrypoint as seen above. The `docker-entrypoint.sh` will run any migrations and then look for specific variables set to create the super user. The **override.env** should look like the following:

```bash
# Super user information, but creation is disabled by default
SKIP_SUPERUSER=false
SUPERUSER_NAME=admin
SUPERUSER_EMAIL=admin@example.com
SUPERUSER_PASSWORD=admin
SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
```

!!! warning
    Please name the **.env** file ``override.env`` to prevent credentials from being checked into Git. ``override.env`` is set in the ``.gitignore`` file.

These will create the user with the specified username, email, password, and API token.

After these two files are created, you can use the normal **invoke** commands to manage the development containers.

### Python Virtual Environment Workflow

There are a few things you'll need:

- A Linux system or environment
- A PostgreSQL server, which can be installed locally [per the documentation](/installation/1-postgresql/)
- A Redis server, which can also be [installed locally](/installation/2-redis/)
- A supported version of Python

#### Creating a Python Virtual Environment

A [virtual environment](https://docs.python.org/3/tutorial/venv.html) is like a container for a set of Python packages. They allow you to build environments suited to specific projects without interfering with system packages or other projects. When installed per the documentation, NetBox uses a virtual environment in production.

Create a virtual environment using the `venv` Python module:

```no-highlight
$ mkdir ~/.venv
$ python3 -m venv ~/.venv/netbox
```

This will create a directory named `.venv/netbox/` in your home directory, which houses a virtual copy of the Python executable and its related libraries and tooling. When running NetBox for development, it will be run using the Python binary at `~/.venv/netbox/bin/python`.

!!! info
    Keeping virtual environments in `~/.venv/` is a common convention but entirely optional: Virtual environments can be created wherever you please.

Once created, activate the virtual environment:

```no-highlight
$ source ~/.venv/netbox/bin/activate
(netbox) $
```

Notice that the console prompt changes to indicate the active environment. This updates the necessary system environment variables to ensure that any Python scripts are run within the virtual environment.

#### Installing Dependencies

With the virtual environment activated, install the project's required Python packages using the `pip` module:

```no-highlight
(netbox) $ python -m pip install -r requirements.txt
Collecting Django==3.1 (from -r requirements.txt (line 1))
  Cache entry deserialization failed, entry ignored
  Using cached https://files.pythonhosted.org/packages/2b/5a/4bd5624546912082a1bd2709d0edc0685f5c7827a278d806a20cf6adea28/Django-3.1-py3-none-any.whl
...
```

#### Configuring NetBox

Within the `netbox/netbox/` directory, copy `configuration.example.py` to `configuration.py` and update the following parameters:

* `ALLOWED_HOSTS`: This can be set to `['*']` for development purposes
* `DATABASE`: PostgreSQL database connection parameters
* `REDIS`: Redis configuration, if different from the defaults
* `SECRET_KEY`: Set to a random string (use `generate_secret_key.py` in the parent directory to generate a suitable key)
* `DEBUG`: Set to `True`
* `DEVELOPER`: Set to `True` (this enables the creation of new database migrations)

#### Starting the Development Server

Django provides a lightweight, auto-updating HTTP/WSGI server for development use. NetBox extends this slightly to automatically import models and other utilities. Run the NetBox development server with the `nbshell` management command:

```no-highlight
$ python netbox/manage.py runserver
Performing system checks...

System check identified no issues (0 silenced).
November 18, 2020 - 15:52:31
Django version 3.1, using settings 'netbox.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

This ensures that your development environment is now complete and operational. Any changes you make to the code base will be automatically adapted by the development server.

## Running Tests

Throughout the course of development, it's a good idea to occasionally run NetBox's test suite to catch any potential errors. Tests are run using the `test` management command:

```no-highlight
$ python netbox/manage.py test
```

In cases where you haven't made any changes to the database (which is most of the time), you can append the `--keepdb` argument to this command to reuse the test database between runs. This cuts down on the time it takes to run the test suite since the database doesn't have to be rebuilt each time. (Note that this argument will cause errors if you've modified any model fields since the previous test run.)

```no-highlight
$ python netbox/manage.py test --keepdb
```

## Submitting Pull Requests

Once you're happy with your work and have verified that all tests pass, commit your changes and push it upstream to your fork. Always provide descriptive (but not excessively verbose) commit messages. When working on a specific issue, be sure to reference it.

```no-highlight
$ git commit -m "Closes #1234: Add IPv5 support"
$ git push origin
```

Once your fork has the new commit, submit a [pull request](https://github.com/netbox-community/netbox/compare) to the NetBox repo to propose the changes. Be sure to provide a detailed accounting of the changes being made and the reasons for doing so.

Once submitted, a maintainer will review your pull request and either merge it or request changes. If changes are needed, you can make them via new commits to your fork: The pull request will update automatically.

!!! note
    Remember, pull requests are entertained only for **accepted** issues. If an issue you want to work on hasn't been approved by a maintainer yet, it's best to avoid risking your time and effort on a change that might not be accepted.
