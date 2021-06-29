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
from invoke import Collection, task as invoke_task
from invoke.exceptions import Exit
import os
import requests
from time import sleep
import toml


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


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_NAUTOBOT_xxx
namespace = Collection("nautobot")
namespace.configure(
    {
        "nautobot": {
            "project_name": "nautobot",
            "python_ver": "3.6",
            "local": False,
            "compose_dir": os.path.join(os.path.dirname(__file__), "development/"),
            "compose_file": "docker-compose.yml",
            "compose_override_file": "docker-compose.dev.yml",
            "docker_image_names_main": [
                "networktocode/nautobot",
                "ghcr.io/nautobot/nautobot",
                "networktocode/nautobot-dev",
                "ghcr.io/nautobot/nautobot-dev",
            ],
            "docker_image_names_develop": [
                "networktocode/nautobot",
                "ghcr.io/nautobot/nautobot",
                "networktocode/nautobot-dev",
                "ghcr.io/nautobot/nautobot-dev",
            ],
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
    compose_command = f'docker-compose --project-name {context.nautobot.project_name} --project-directory "{context.nautobot.compose_dir}" -f "{compose_file_path}"'
    compose_override_path = os.path.join(context.nautobot.compose_dir, context.nautobot.compose_override_file)
    if os.path.isfile(compose_override_path):
        compose_command += f' -f "{compose_override_path}"'
    compose_command += f" {command}"

    # If `service` was passed as a kwarg, add it to the end.
    service = kwargs.pop("service", None)
    if service is not None:
        compose_command += f" {service}"

    print(f'Running docker-compose command "{command}"')
    return context.run(compose_command, env={"PYTHON_VER": context.nautobot.python_ver}, **kwargs)


def run_command(context, command, **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    if is_truthy(context.nautobot.local):
        context.run(command, **kwargs)
    else:
        # Check if Nautobot is running; no need to start another Nautobot container to run a command
        docker_compose_status = "ps --services --filter status=running"
        results = docker_compose(context, docker_compose_status, hide="out")
        if "nautobot" in results.stdout:
            compose_command = f"exec nautobot {command}"
        else:
            compose_command = f"run --entrypoint '{command}' nautobot"

        docker_compose(context, compose_command, pty=True)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers.",
        "cache": "Whether to use Docker's cache when building the image. (Default: enabled)",
    }
)
def build(context, force_rm=False, cache=True):
    """Build Nautobot docker image."""
    command = f"build --build-arg PYTHON_VER={context.nautobot.python_ver}"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"

    print(f"Building Nautobot with Python {context.nautobot.python_ver}...")
    docker_compose(context, command)


@task(
    help={
        "cache": "Whether to use Docker's cache when building the image. (Default: enabled)",
        "cache_dir": "Directory to use for caching buildx output. (Default: /home/travis/.cache/docker)",
        "platforms": "Comma-separated list of strings for which to build. (Default: linux/amd64)",
        "tag": "Tags to be applied to the built image. (Default: networktocode/nautobot-dev:local)",
        "target": "Build target from the Dockerfile. (Default: dev)",
    }
)
def buildx(
    context,
    cache=False,
    cache_dir="",
    platforms="linux/amd64",
    tag="networktocode/nautobot-dev-py3.6:local",
    target="dev",
):
    """Build Nautobot docker image using the experimental buildx docker functionality (multi-arch capablility)."""
    print(f"Building Nautobot with Python {context.nautobot.python_ver} for {platforms}...")
    command = f"docker buildx build --platform {platforms} -t {tag} --target {target} --load -f ./docker/Dockerfile --build-arg PYTHON_VER={context.nautobot.python_ver} ."
    if not cache:
        command += " --no-cache"
    else:
        command += f" --cache-to type=local,dest={cache_dir}/{context.nautobot.python_ver} --cache-from type=local,src={cache_dir}/{context.nautobot.python_ver}"

    context.run(command, env={"PYTHON_VER": context.nautobot.python_ver})


@task(
    help={
        "branch": "Source branch used to push.",
        "commit": "Commit hash used to tag the image.",
        "datestamp": "Datestamp used to tag the develop image.",
    }
)
def docker_push(context, branch, commit="", datestamp=""):
    """Tags and pushes docker images to the appropriate repos, intended for CI use only."""
    with open("pyproject.toml", "r") as pyproject:
        parsed_toml = toml.load(pyproject)

    nautobot_version = parsed_toml["tool"]["poetry"]["version"]

    docker_image_tags_main = [
        f"latest-py{context.nautobot.python_ver}",
        f"{nautobot_version}-py{context.nautobot.python_ver}",
    ]
    docker_image_tags_develop = [
        f"develop-py{context.nautobot.python_ver}",
        f"develop-py{context.nautobot.python_ver}-{commit}-{datestamp}",
    ]

    if context.nautobot.python_ver == "3.6":
        docker_image_tags_main += ["latest", f"{nautobot_version}"]
        docker_image_tags_develop += ["develop", f"develop-{commit}-{datestamp}"]
    if branch == "main":
        docker_image_names = context.nautobot.docker_image_names_main
        docker_image_tags = docker_image_tags_main
    elif branch == "develop":
        docker_image_names = context.nautobot.docker_image_names_develop
        docker_image_tags = docker_image_tags_develop
    else:
        raise Exit(f"Unknown Branch ({branch}) Specified", 1)

    for image_name in docker_image_names:
        for image_tag in docker_image_tags:
            if image_name.endswith("-dev"):
                local_image = f"networktocode/nautobot-dev-py{context.nautobot.python_ver}:local"
            else:
                local_image = f"networktocode/nautobot-py{context.nautobot.python_ver}:local"
            new_image = f"{image_name}:{image_tag}"
            tag_command = f"docker tag {local_image} {new_image}"
            push_command = f"docker push {new_image}"
            print(f"Tagging {local_image} as {new_image}")
            context.run(tag_command)
            print(f"Pushing {new_image}")
            context.run(push_command)

    print("\nThe following Images have been pushed:\n")
    for image_name in docker_image_names:
        for image_tag in docker_image_tags:
            new_image = f"{image_name}:{image_tag}"
            print(new_image)


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task(help={"service": "If specified, only affect this service."})
def debug(context, service=None):
    """Start Nautobot and its dependencies in debug mode."""
    print("Starting Nautobot in debug mode...")
    docker_compose(context, "up", service=service)


@task(help={"service": "If specified, only affect this service."})
def start(context, service=None):
    """Start Nautobot and its dependencies in detached mode."""
    print("Starting Nautobot in detached mode...")
    docker_compose(context, "up --detach", service=service)


@task(help={"service": "If specified, only affect this service."})
def restart(context, service=None):
    """Gracefully restart containers."""
    print("Restarting Nautobot...")
    docker_compose(context, "restart", service=service)


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
@task
def nbshell(context):
    """Launch an interactive nbshell session."""
    command = "nautobot-server nbshell"

    run_command(context, command, pty=True)


@task(help={"container": "Name of the container to shell into"})
def cli(context, container="nautobot"):
    """Launch a bash shell inside the running Nautobot container."""
    docker_compose(context, f"exec {container} bash", pty=True)


@task(
    help={
        "user": "Name of the superuser to create. (Default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    command = f"nautobot-server createsuperuser --username {user}"

    run_command(context, command)


@task(help={"name": "Use this name for migration file(s). If unspecified, a name will be generated."})
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = "nautobot-server makemigrations"

    if name:
        command += f" --name {name}"

    run_command(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    command = "nautobot-server migrate"

    run_command(context, command)


@task(help={})
def post_upgrade(context):
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

    run_command(context, command)


@task(help={"format": "Output serialization format for dumped data. (Choices: json, xml, yaml)"})
def dumpdata(context, format="json"):
    """Dump data from database to db_output file."""
    command = f"nautobot-server dumpdata --exclude extras.job --indent 4 --output db_output.{format} --format {format}"
    run_command(context, command)


@task(help={"file_name": "Name and path of file to load."})
def loaddata(context, file_name):
    """Load data from file."""
    command = f"nautobot-server loaddata {file_name}"
    run_command(context, command)


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect.",
    }
)
def black(context, autoformat=False):
    """Check Python code style with Black."""
    if autoformat:
        black_command = "black"
    else:
        black_command = "black --check --diff"

    command = f"{black_command} development/ examples/ nautobot/ tasks.py"

    run_command(context, command)


@task
def flake8(context):
    """Check for PEP8 compliance and other style issues."""
    command = "flake8 development/ examples/ nautobot/ tasks.py"
    run_command(context, command)


@task
def hadolint(context):
    """Check Dockerfile for hadolint compliance and other style issues."""
    command = "hadolint docker/Dockerfile"
    run_command(context, command)


@task
def check_migrations(context):
    """Check for missing migrations."""
    command = "nautobot-server --config=nautobot/core/tests/nautobot_config.py makemigrations --dry-run --check"

    run_command(context, command)


@task(
    help={
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
        "label": "Specify a directory or module to test instead of running all Nautobot tests.",
        "failfast": "Fail as soon as a single test fails don't run the entire test suite.",
        "buffer": "Discard output from passing tests.",
        "tag": "Run only tests with the specified tag. Can be used multiple times.",
        "exclude_tag": "Do not run tests with the specified tag. Can be used multiple times.",
        "verbose": "Enable verbose test output.",
        "append": "Append coverage data to .coverage, otherwise it starts clean each time.",
    },
    iterable=["tag", "exclude_tag"],
)
def unittest(
    context,
    keepdb=False,
    label="nautobot",
    failfast=False,
    buffer=True,
    exclude_tag=None,
    tag=None,
    verbose=False,
    append=False,
):
    """Run Nautobot unit tests."""

    append_arg = " --append" if append else ""
    command = f"coverage run{append_arg} --module nautobot.core.cli test {label} --config=nautobot/core/tests/nautobot_config.py"
    # booleans
    if keepdb:
        command += " --keepdb"
    if failfast:
        command += " --failfast"
    if buffer:
        command += " --buffer"
    if verbose:
        command += " --verbosity 2"

    # lists
    if tag:
        for individual_tag in tag:
            command += f" --tag {individual_tag}"
    if exclude_tag:
        for individual_exclude_tag in exclude_tag:
            command += f" --tag {individual_exclude_tag}"

    run_command(context, command)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    command = "coverage report --skip-covered --include 'nautobot/*' --omit *migrations*"

    run_command(context, command)


@task(
    help={
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
        "label": "Specify a directory or module to test instead of running all Nautobot tests.",
        "failfast": "Fail as soon as a single test fails don't run the entire test suite.",
        "buffer": "Discard output from passing tests.",
        "tag": "Run only tests with the specified tag. Can be used multiple times.",
        "exclude_tag": "Do not run tests with the specified tag. Can be used multiple times.",
        "verbose": "Enable verbose test output.",
        "append": "Append coverage data to .coverage, otherwise it starts clean each time.",
    },
    iterable=["tag", "exclude_tag"],
)
def integration_test(
    context,
    keepdb=False,
    label="nautobot",
    failfast=False,
    buffer=True,
    tag=None,
    exclude_tag=None,
    verbose=False,
    append=False,
):
    """Run Nautobot integration tests."""

    # Enforce "integration" tag
    tag.append("integration")

    unittest(
        context,
        keepdb=keepdb,
        label=label,
        failfast=failfast,
        buffer=buffer,
        tag=tag,
        exclude_tag=exclude_tag,
        verbose=verbose,
        append=append,
    )


@task(
    help={
        "lint-only": "Only run linters; unit tests will be excluded.",
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
    }
)
def tests(context, lint_only=False, keepdb=False):
    """Run all tests and linters."""
    black(context)
    flake8(context)
    hadolint(context)
    check_migrations(context)
    if not lint_only:
        unittest(context, keepdb=keepdb)
