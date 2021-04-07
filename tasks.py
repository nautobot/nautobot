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
from invoke import Collection, task as invoke_task


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


DEFAULT_PYTHON_VER = "3.7"

# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_NAUTOBOT_xxx
namespace = Collection("nautobot")
namespace.configure(
    {
        "nautobot": {
            "python_ver": DEFAULT_PYTHON_VER,
            "local": False,
            "compose_dir": os.path.join(os.path.dirname(__file__), "development/"),
            "compose_file": "docker-compose.yml",
            "compose_override_file": "docker-compose.override.yml",
        }
    }
)


def task(function=None, *args, **kwargs):
    """Task decorator to override the default Invoke task decorator."""

    def task_wrapper(function=None):
        """Wrapper around invoke.task to add the task to the namespace as well."""
        if args or kwargs:
            task_func = invoke_task(*args, **kwargs)(function)
        else:
            task_func = invoke_task(function)
        namespace.add_task(task_func)
        return task_func

    if function:
        # The decorator was called with no arguments
        return task_wrapper(function)
    # The decorator was called with arguments
    return task_wrapper


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker-compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker-compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    compose_file_path = os.path.join(context.nautobot.compose_dir, context.nautobot.compose_file)
    compose_command = f'docker-compose --project-directory "{context.nautobot.compose_dir}" -f "{compose_file_path}"'
    compose_override_path = os.path.join(context.nautobot.compose_dir, context.nautobot.compose_override_file)
    if os.path.isfile(compose_override_path):
        compose_command += f' -f "{compose_override_path}"'
    compose_command += f" {command}"
    print(f'Running docker-compose command "{command}"')
    return context.run(compose_command, env={"PYTHON_VER": context.nautobot.python_ver}, **kwargs)


def run_command(context, command, local=None):
    """Wrapper to run a command locally or inside the nautobot container."""
    if local is None:
        local = context.nautobot.local
    if is_truthy(local):
        context.run(command)
    else:
        docker_compose(context, f"run --entrypoint '{command}' nautobot", pty=True)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers",
        "cache": "Whether to use Docker's cache when building the image (defaults to enabled)",
        "python-ver": "The version of Python to build the container with (default: 3.7)",
    }
)
def build(context, force_rm=False, cache=True, python_ver=None):
    """Build Nautobot docker image."""
    if python_ver is None:
        python_ver = context.nautobot.python_ver
    else:
        context.nautobot.python_ver = python_ver

    command = f"build --build-arg PYTHON_VER={python_ver}"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    print(f"Building Nautobot with Python {python_ver}...")
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
    command = "code nautobot.code-workspace"

    context.run(command)


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task(help={"local": "run this task locally vs inside the docker container (default: False)"}, optional=["local"])
def nbshell(context, local=None):
    """Launch an interactive nbshell session."""
    command = "nautobot-server nbshell"

    run_command(context, command, local)


@task
def cli(context):
    """Launch a bash shell inside the running Nautobot container."""
    docker_compose(context, "exec nautobot bash", pty=True)


@task(
    help={
        "user": "name of the superuser to create (default: admin)",
        "local": "run this task locally vs inside the docker container (default: False)",
    },
    optional=["local"],
)
def createsuperuser(context, user="admin", local=None):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command, local)


@task(
    help={
        "name": "name of the migration to be created; if unspecified, will autogenerate a name",
        "local": "run this task locally vs inside the docker container (default: False)",
    },
    optional=["local"],
)
def makemigrations(context, name="", local=None):
    """Perform makemigrations operation in Django."""
    command = "nautobot-server makemigrations"

    if name:
        command += f" --name {name}"

    run_command(context, command, local)


@task(help={"local": "run this task locally vs inside the docker container (default: False)"}, optional=["local"])
def migrate(context, local=None):
    """Perform migrate operation in Django."""
    command = "nautobot-server migrate"

    run_command(context, command, local)


@task(
    help={
        "local": "run this task locally vs inside the docker container (default: False)",
    },
    optional=["local"],
)
def post_upgrade(context, local=None):
    """
    Performs Nautobot common post-upgrade operations using a single entrypoint.

    This will run the following management commands with default settings, in order:

    - migrate
    - trace_paths
    - collectstatic
    - remove_stale_contenttypes
    - clearsessions
    - invalidate all
    """
    command = "nautobot-server post_upgrade"

    run_command(context, command, local)


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect.",
        "local": "run this task locally vs inside the docker container (default: False)",
    },
    optional=["local"],
)
def black(context, autoformat=False, local=None):
    """Check Python code style with Black."""
    if autoformat:
        black_command = "black"
    else:
        black_command = "black --check --diff"

    command = f"{black_command} development/ nautobot/ tasks.py"

    run_command(context, command, local)


@task(help={"local": "run this task locally vs inside the docker container (default: False)"}, optional=["local"])
def flake8(context, local=None):
    """Check for PEP8 compliance and other style issues."""
    command = "flake8 development/ nautobot/ tasks.py"

    run_command(context, command, local)


@task(help={"local": "run this task locally vs inside the docker container (default: False)"}, optional=["local"])
def check_migrations(context, local=None):
    """Check for missing migrations."""
    command = "nautobot-server --config=nautobot/core/tests/nautobot_config.py makemigrations --dry-run --check"

    run_command(context, command, local)


@task(
    help={
        "keepdb": "save and re-use test database between test runs for faster re-testing.",
        "label": "specify a directory or module to test instead of running all Nautobot tests",
        "failfast": "fail as soon as a single test fails don't run the entire test suite",
        "local": "run this task locally vs inside the docker container (default: False)",
    },
    optional=["local"],
)
def unittest(context, keepdb=False, label="nautobot", failfast=False, local=None):
    """Run Nautobot unit tests."""
    command = f"coverage run -m nautobot.core.cli test {label} --config=nautobot/core/tests/nautobot_config.py"

    if keepdb:
        command += " --keepdb"
    if failfast:
        command += " --failfast"
    run_command(context, command, local)


@task(help={"local": "run this task locally vs inside the docker container (default: False)"}, optional=["local"])
def unittest_coverage(context, local=None):
    """Report on code test coverage as measured by 'invoke unittest'."""
    command = "coverage report --skip-covered --include 'nautobot/*' --omit *migrations*"

    run_command(context, command, local)


@task(
    help={
        "lint-only": "only run linters, unit tests will be excluded",
        "local": "run tests locally vs inside the docker container (default: False)",
    },
    optional=["local"],
)
def tests(context, lint_only=False, local=None):
    """Run all tests and linters."""
    black(context, local=local)
    flake8(context, local)
    check_migrations(context, local)
    if not lint_only:
        unittest(context, local=local)
