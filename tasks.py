"""Tasks for use with Invoke.

(c) 2020-2021 Network To Code
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at
  http://www.apache.org/licenses/LICENSE-2.0
Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import os
from invoke import task


PYTHON_VER = os.getenv("PYTHON_VER", "3.7")

COMPOSE_DIR = os.path.join(os.path.dirname(__file__), "development/")
COMPOSE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.yml")
COMPOSE_OVERRIDE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.override.yml")
COMPOSE_COMMAND = f'docker-compose --project-directory "{COMPOSE_DIR}" -f "{COMPOSE_FILE}"'

if os.path.isfile(COMPOSE_OVERRIDE_FILE):
    COMPOSE_COMMAND += f' -f "{COMPOSE_OVERRIDE_FILE}"'


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker-compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker-compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    print(f'Running docker-compose command "{command}"')
    return context.run(f"{COMPOSE_COMMAND} {command}", env={"PYTHON_VER": PYTHON_VER}, **kwargs)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task
def build(context, nocache=False, forcerm=False):
    """Build all docker images.

    Args:
        context (obj): Used to run specific commands
        nocache (bool): Do not use cache when building the image
        forcerm (bool): Always remove intermediate containers
    """
    print("Building Nautobot .. ")
    command = f"build --build-arg PYTHON_VER={PYTHON_VER}"
    if nocache:
        command += " --no-cache"
    if forcerm:
        command += " --force-rm"
    docker_compose(context, command)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task
def debug(context):
    """Start Nautobot and its dependencies in debug mode."""
    print("Starting Nautobot in debug mode...")
    docker_compose(context, "up")


@task
def start(context):
    """Start Nautobot and its dependencies in detached mode."""
    print("Starting Nautobot in detached mode...")
    docker_compose(context, "up --detach")


@task
def restart(context):
    """Gracefully restart all containers."""
    print("Restarting Nautobot...")
    docker_compose(context, "restart")


@task
def stop(context):
    """Stop Nautobot and its dependencies."""
    print("Stopping Nautobot...")
    docker_compose(context, "down")


@task
def destroy(context):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...")
    docker_compose(context, "down --volumes")


@task
def vscode(context):
    """Launch Visual Studio Code with the appropriate Environment variables to run in a container."""
    context.run("code nautobot.code-workspace", env={"PYTHON_VER": PYTHON_VER})


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task
def nbshell(context):
    """Launch an interactive nbshell session."""
    docker_compose(context, "run nautobot nautobot-server nbshell", pty=True)


@task
def cli(context):
    """Launch a bash shell inside the running Nautobot container."""
    docker_compose(context, "exec nautobot bash", pty=True)


@task
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password.

    Args:
        context (obj): Used to run specific commands
        user (str): name of the superuser to create
    """
    docker_compose(context, "run nautobot nautobot-server createsuperuser --username {user}", pty=True)


@task
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django.

    Args:
        context (obj): Used to run specific commands
        name (str): Name of the migration to be created (if not specified, will autogenerate a name)
    """
    command = "run nautobot nautobot-server makemigrations"
    if name:
        command += f" --name {name}"
    docker_compose(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    docker_compose(context, "run nautobot nautobot-server migrate")


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task
def black(context):
    """Check Python code style with Black."""
    docker_compose(
        context,
        "run --entrypoint 'black --check --diff contrib/ development/ nautobot/ tasks.py' nautobot",
        pty=True,
    )


@task
def flake8(context):
    """Check for PEP8 compliance and other style issues."""
    docker_compose(context, "run --entrypoint 'flake8 contrib/ development/ nautobot/ tasks.py' nautobot", pty=True)


@task
def unittest(context, label="nautobot", keepdb=False):
    """Run Nautobot unit tests.

    Args:
        context (obj): Used to run specific commands
        label (str): Indicate a directory or module to test instead of running all Nautobot tests
        keepdb (bool): Save and re-use test database between test runs for faster re-testing.
    """
    command = f"run --entrypoint 'coverage run scripts/test_runner.py test {label}"
    if keepdb:
        command += " --keepdb"
    command += "' nautobot"
    docker_compose(context, command, pty=True)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    docker_compose(context, "run --entrypoint 'coverage report --skip-covered --omit *migrations*' nautobot", pty=True)


@task
def tests(context):
    """Run all tests and linters."""
    black(context)
    flake8(context)
    unittest(context)
