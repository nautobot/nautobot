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

from distutils.util import strtobool
import os
from invoke import task


def is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True
    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg
    return bool(strtobool(arg))


PYTHON_VER = os.getenv("PYTHON_VER", "3.7")

COMPOSE_DIR = os.path.join(os.path.dirname(__file__), "development/")
COMPOSE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.yml")
COMPOSE_OVERRIDE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.override.yml")
COMPOSE_COMMAND = f'docker-compose --project-directory "{COMPOSE_DIR}" -f "{COMPOSE_FILE}"'

if os.path.isfile(COMPOSE_OVERRIDE_FILE):
    COMPOSE_COMMAND += f' -f "{COMPOSE_OVERRIDE_FILE}"'

INVOKE_LOCAL = is_truthy(os.getenv("INVOKE_LOCAL", False)) 

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
@task(
    help={
        "force_rm": "Always remove intermediate containers",
        "cache": "Whether to use Docker's cache when building the image (defaults to enabled)",
    }
)
def build(context, force_rm=False, cache=True):
    """Build Nautobot docker image."""
    print("Building Nautobot .. ")
    command = f"build --build-arg PYTHON_VER={PYTHON_VER}"
    if not cache:
        command += " --no-cache"
    if force_rm:
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
    command = "nautobot-server nbshell"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, f"run nautobot {command}", pty=True)


@task
def cli(context):
    """Launch a bash shell inside the running Nautobot container."""
    docker_compose(context, "exec nautobot bash", pty=True)


@task(help={"user": "name of the superuser to create"})
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, f"run nautobot {command}", pty=True)


@task(help={"name": "name of the migration to be created; if unspecified, will autogenerate a name"})
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = "run nautobot nautobot-server makemigrations"
    if name:
        command += f" --name {name}"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    command = "nautobot-server migrate"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, f"run nautobot {command}")


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect."
    }
)
def black(context, autoformat=False):
    """Check Python code style with Black."""
    if autoformat:
        black_command = "black"
    else:
        black_command = "black --check --diff"
    command = f"{black_command} development/ nautobot/ tasks.py"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(
            context,
            f"run --entrypoint '{command}' nautobot",
            pty=True,
        )


@task
def flake8(context):
    """Check for PEP8 compliance and other style issues."""
    command = "flake8 development/ nautobot/ tasks.py"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, f"run --entrypoint '{command}' nautobot", pty=True)


@task
def check_migrations(context):
    """Check for missing migrations."""
    command = "nautobot-server --config=nautobot/core/tests/nautobot_config.py makemigrations --dry-run --check"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, f"run --entrypoint '{command}' nautobot", pty=True)


@task(
    help={
        "keepdb": "save and re-use test database between test runs for faster re-testing.",
        "label": "specify a directory or module to test instead of running all Nautobot tests",
    }
)
def unittest(context, keepdb=False, label="nautobot"):
    """Run Nautobot unit tests."""
    command = f"coverage run -m nautobot.core.cli test {label} --config=nautobot/core/tests/nautobot_config.py"
    if keepdb:
        command += " --keepdb"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, f"run --entrypoint '{command}' nautobot", pty=True)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    command = "coverage report --skip-covered --omit *migrations*"
    if INVOKE_LOCAL:
        context.run(command)
    else:
        docker_compose(context, f"run --entrypoint '{command}' nautobot", pty=True)


@task
def tests(context):
    """Run all tests and linters."""
    black(context)
    flake8(context)
    check_migrations(context)
    unittest(context)
