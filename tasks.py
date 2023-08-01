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

import json
import os
import re
import subprocess
import time
from enum import Enum, auto
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import List, Tuple
from xml.etree import ElementTree

from invoke import Collection
from invoke import task as invoke_task
from invoke.exceptions import Exit

try:
    # Override built-in print function with rich's pretty-printer function, if available
    from rich import print  # pylint: disable=redefined-builtin
    from rich.console import Console
    from rich.markup import escape

    console = Console()

    HAS_RICH = True
except ModuleNotFoundError:
    HAS_RICH = False


# Regex to match ANSI escape sequences, to be able to remove them from the output
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
# Repository root path
_ROOT_PATH = Path(__file__).parent.absolute().resolve()
# Path to the file containing tests modules with their execution times
_TESTS_TIMES_PATH = _ROOT_PATH / "nautobot/core/tests/tests-times.json"
# Name of the directory containing test results
_TESTS_RESULTS_DIR_NAME = ".test-results"
# List of names used for NAMES Distribution
# One test group will be created for each item
_NAMES_DISTRIBUTION = [
    "circuits",
    "core",
    "dcim",
    "dcim/tests/test_api.py",
    "dcim/tests/test_views.py",
    "extras",
    "extras/tests/test_api.py",
    "extras/tests/test_jobs.py",
    "extras/tests/test_views.py",
    "ipam",
    "tenancy",
    "users",
    "utilities",
    "virtualization",
]
# List of patterns to match tests files to skip, these are not used in parallelized unittests.
# Django test discovery will skip these tests for `invoke unittests` without tags.
# Unable to use Django discovery for parallelized tests, so we need to skip them manually.
#     (First we need to distribute tests and then run them)
_SKIP_TESTS_NAMES = [
    "/example_jobs/",
    "/integration/",
    "nautobot/core/tests/test_cli.py",
]


class DistributionType(Enum):
    NAMES = auto()
    TIMES = auto()


def is_truthy(arg):
    """
    Convert "truthy" strings into Booleans.

    Examples:
        >>> is_truthy('yes')
        True

    Args:
        arg (str): Truthy string (True values are y, yes, t, true, on and 1; false values are n, no,
        f, false, off and 0. Raises ValueError if val is anything else.
    """
    if isinstance(arg, bool):
        return arg

    val = str(arg).lower()
    if val in ("y", "yes", "t", "true", "on", "1"):
        return True
    elif val in ("n", "no", "f", "false", "off", "0"):
        return False
    else:
        raise ValueError(f"Invalid truthy value: `{arg}`")


def _resolve_default_exec(context, default_exec=None) -> str:
    """Resolve the default execution method.

    Possible return values are "local", "exec", or "run".
    "exec" and "run" are executed using docker compose.
    """
    if default_exec is None:
        if is_truthy(context.nautobot.local):
            result = "local"
        else:
            docker_compose_status = "ps --services --filter status=running"
            ps_result = docker_compose(context, docker_compose_status, hide="out")
            result = "exec" if "nautobot" in ps_result.stdout else "run"
    else:
        result = default_exec

    if result in ("local", "exec", "run"):
        return result

    raise ValueError(f"Invalid --default-exec: {default_exec}")


def _get_tests_results_path(context, default_exec: str) -> Path:
    """Return the directory to store tests results in, different for docker and local runs."""
    if _resolve_default_exec(context, default_exec) == "local":
        return _ROOT_PATH / _TESTS_RESULTS_DIR_NAME
    else:
        return Path("/source") / _TESTS_RESULTS_DIR_NAME


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_NAUTOBOT_xxx
namespace = Collection("nautobot")
namespace.configure(
    {
        "nautobot": {
            "project_name": "nautobot",
            "python_ver": "3.7",
            "local": False,
            "compose_dir": os.path.join(os.path.dirname(__file__), "development/"),
            "compose_files": [
                "docker-compose.yml",
                "docker-compose.postgres.yml",
                "docker-compose.dev.yml",
            ],
            # Image names to use when building from "main" branch
            "docker_image_names_main": [
                # Production containers - not containing development tools
                "networktocode/nautobot",
                "ghcr.io/nautobot/nautobot",
                # Development containers - include development tools like linters
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


def print_command(command, env=None):
    r"""
    >>> command = "docker buildx build . --platform linux/amd64 --target final --load -f ./docker/Dockerfile --build-arg PYTHON_VER=3.9 -t networktocode/nautobot-py3.9:local --no-cache"
    >>> print_command(command)
    docker buildx build . \
        --platform linux/amd64 \
        --target final \
        --load \
        -f ./docker/Dockerfile \
        --build-arg PYTHON_VER=3.9 \
        -t networktocode/nautobot-py3.9:local \
        --no-cache
    >>> env = {"PYTHON_VER": "3.9"}
    >>> print_command(command, env=env)
    PYTHON_VER=3.9 \
    docker buildx build . \
        --platform linux/amd64 \
        --target final \
        --load \
        -f ./docker/Dockerfile \
        --build-arg PYTHON_VER=3.9 \
        -t networktocode/nautobot-py3.9:local \
        --no-cache
    """
    # Everywhere we have a `--foo`, a `-f`, a `--foo bar`, or a `-f bar`, wrap to a new line
    formatted_command = re.sub(r"\s+(--?\w+(\s+[^-]\S*)?)", r" \\\n    \1", command)
    formatted_env = ""
    if env:
        formatted_env = " \\\n".join(f"{var}={value}" for var, value in env.items()) + " \\\n"
    if HAS_RICH:
        console.print(f"[dim]{escape(formatted_env)}{escape(formatted_command)}[/dim]", soft_wrap=True)
    else:
        print(f"{formatted_env}{formatted_command}")


def docker_compose(context, command, **kwargs):
    """Helper function for running a specific docker-compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker-compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    compose_command_tokens = [
        "docker-compose",
        f'--project-name "{context.nautobot.project_name}"',
        f'--project-directory "{context.nautobot.compose_dir}"',
    ]

    for compose_file in context.nautobot.compose_files:
        compose_file_path = os.path.join(context.nautobot.compose_dir, compose_file)
        compose_command_tokens.append(f'-f "{compose_file_path}"')

    compose_command_tokens.append(command)

    # If `service` was passed as a kwarg, add it to the end.
    service = kwargs.pop("service", None)
    if service is not None:
        compose_command_tokens.append(service)

    print(f'Running docker-compose command "{command}"')
    compose_command = " ".join(compose_command_tokens)
    env = kwargs.pop("env", {})
    env.update({"PYTHON_VER": context.nautobot.python_ver})
    if "hide" not in kwargs:
        print_command(compose_command, env=env)
    return context.run(compose_command, env=env, **kwargs)


def run_command(context, command, default_exec=None, **kwargs):
    """Wrapper to run a command locally or inside the nautobot container."""
    task_env = kwargs.pop("task_env", {})
    default_exec = _resolve_default_exec(context, default_exec)
    if default_exec == "local":
        env = kwargs.pop("env", {})
        env.update(task_env)
        if "hide" not in kwargs:
            print_command(command, env=env)
        context.run(command, pty=True, env=env, **kwargs)
    else:
        # Check if Nautobot is running; no need to start another Nautobot container to run a command
        env_args = " ".join(f"-e {key}" for key in task_env)
        if default_exec == "exec":
            compose_command = f"exec {env_args} -- nautobot {command}"
        elif default_exec == "run":
            compose_command = f"run {env_args} --rm --entrypoint '{command}' -- nautobot"

        docker_compose(context, compose_command, pty=True, env=task_env)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers.",
        "cache": "Whether to use Docker's cache when building the image. (Default: enabled)",
        "poetry_parallel": "Enable/disable poetry to install packages in parallel. (Default: True)",
        "pull": "Whether to pull Docker images when building the image. (Default: disabled)",
        "skip_docs_build": "Skip (re)build of documentation after building the image.",
    }
)
def build(context, force_rm=False, cache=True, poetry_parallel=True, pull=False, skip_docs_build=False):
    """Build Nautobot docker image."""
    command = f"build --build-arg PYTHON_VER={context.nautobot.python_ver}"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"
    if poetry_parallel:
        command += " --build-arg POETRY_PARALLEL=true"
    if pull:
        command += " --pull"

    print(f"Building Nautobot with Python {context.nautobot.python_ver}...")

    docker_compose(context, command, env={"DOCKER_BUILDKIT": "1", "COMPOSE_DOCKER_CLI_BUILD": "1"})

    if not skip_docs_build:
        # Build the docs so they are available. Skip if you're using a `final-dev` or `final` image instead of `dev`.
        build_nautobot_docs(context)


@task(
    help={
        "poetry_parallel": "Enable/disable poetry to install packages in parallel. (Default: True)",
    }
)
def build_dependencies(context, poetry_parallel=True):
    """Determine preferred/default target architecture"""
    output = context.run("docker buildx inspect default", env={"PYTHON_VER": context.nautobot.python_ver}, hide=True)
    result = re.search(r"Platforms: ([^,\n]+)", output.stdout)

    build_kwargs = {
        "dependencies_base_branch": "local",
        "poetry_parallel": poetry_parallel,
        "tag": f"ghcr.io/nautobot/nautobot-dependencies:local-py{context.nautobot.python_ver}",
        "target": "dependencies",
    }

    if len(result.groups()) < 1:
        print("Failed to identify platform building for, falling back to default.")

    else:
        build_kwargs["platforms"] = result.group(1)

    buildx(context, **build_kwargs)


@task(
    help={
        "cache": "Whether to use Docker's cache when building the image. (Default: enabled)",
        "cache_dir": "Directory to use for caching buildx output. (Default: current directory)",
        "platforms": "Comma-separated list of strings for which to build. (Default: linux/amd64)",
        "tag": "Tags to be applied to the built image. (Default: depends on the --target)",
        "target": "Build target from the Dockerfile. (Default: dev)",
        "poetry_parallel": "Enable/disable poetry to install packages in parallel. (Default: False)",
    }
)
def buildx(
    context,
    cache=False,
    cache_dir="",
    platforms="linux/amd64",
    tag=None,
    target="dev",
    poetry_parallel=False,
):
    """Build Nautobot docker image using the experimental buildx docker functionality (multi-arch capability)."""
    print(f"Building Nautobot {target} target with Python {context.nautobot.python_ver} for {platforms}...")
    if tag is None:
        if target == "dev":
            pass
        if target == "final-dev":
            tag = f"networktocode/nautobot-dev-py{context.nautobot.python_ver}:local"
        elif target == "final":
            tag = f"networktocode/nautobot-py{context.nautobot.python_ver}:local"
        else:
            print(f"Not sure what should be the standard tag for target {target}, will not tag.")
    command_tokens = [
        "docker buildx build .",
        f"--platform {platforms}",
        f"--target {target}",
        "--load",
        "-f ./docker/Dockerfile",
        f"--build-arg PYTHON_VER={context.nautobot.python_ver}",
    ]
    if tag is not None:
        command_tokens.append(f"-t {tag}")
    if not cache:
        command_tokens.append("--no-cache")
    else:
        command_tokens += [
            f"--cache-to type=local,dest={cache_dir}/{context.nautobot.python_ver}",
            f"--cache-from type=local,src={cache_dir}/{context.nautobot.python_ver}",
        ]
    if poetry_parallel:
        command_tokens.append("--build-arg POETRY_PARALLEL=true")

    command = " ".join(command_tokens)
    env = {"PYTHON_VER": context.nautobot.python_ver}

    print_command(command, env=env)
    context.run(command, env=env)


def get_nautobot_version():
    """Directly parse `pyproject.toml` and extract the version."""
    with open("pyproject.toml", "r") as fh:
        content = fh.read()

    version_match = re.findall(r"version = \"(.*)\"\n", content)
    return version_match[0]


def get_dependency_version(dependency_name):
    """Get the version of a given direct dependency from `pyproject.toml`."""
    with open("pyproject.toml", "r") as fh:
        content = fh.read()

    version_match = re.search(rf'^{dependency_name} = .*"[~^]?([0-9.]+)"', content, flags=re.MULTILINE)
    return version_match.group(1)


@task(
    help={
        "branch": "Source branch used to push.",
        "commit": "Commit hash used to tag the image.",
        "datestamp": "Datestamp used to tag the develop image.",
    }
)
def docker_push(context, branch, commit="", datestamp=""):
    """Tags and pushes docker images to the appropriate repos, intended for release use only.

    Before running this command, you **must** be on the `main` branch and **must** have run
    the appropriate set of `invoke buildx` commands. Refer to the developer release-checklist docs for details.
    """
    nautobot_version = get_nautobot_version()

    docker_image_tags_main = [
        f"stable-py{context.nautobot.python_ver}",
        f"{nautobot_version}-py{context.nautobot.python_ver}",
    ]

    if context.nautobot.python_ver == "3.7":
        docker_image_tags_main += ["stable", f"{nautobot_version}"]
    if branch == "main":
        docker_image_names = context.nautobot.docker_image_names_main
        docker_image_tags = docker_image_tags_main
    else:
        raise Exit(f"Unknown Branch ({branch}) Specified", 1)

    for image_name in docker_image_names:
        for image_tag in docker_image_tags:
            if image_name.endswith("-dev"):
                # Use the development image as the basis for this tag and push
                local_image = f"networktocode/nautobot-dev-py{context.nautobot.python_ver}:local"
            else:
                # Use the production image as the basis for this tag and push
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


@task(help={"service": "If specified, only affect this service."})
def stop(context, service=None):
    """Stop Nautobot and its dependencies."""
    print("Stopping Nautobot...")
    if not service:
        docker_compose(context, "down --remove-orphans")
    else:
        docker_compose(context, "stop", service=service)


@task
def destroy(context):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...")
    docker_compose(context, "down --remove-orphans --volumes")


@task
def vscode(context):
    """Launch Visual Studio Code with the appropriate Environment variables to run in a container."""
    command = "code nautobot.code-workspace"

    context.run(command, env={"PYTHON_VER": context.nautobot.python_ver})


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task
def nbshell(context):
    """Launch an interactive nbshell session."""
    command = "nautobot-server nbshell"

    run_command(context, command, pty=True)


@task(help={"service": "Name of the service to shell into"})
def cli(context, service="nautobot"):
    """Launch a bash shell inside the running Nautobot (or other) Docker container."""
    docker_compose(context, f"exec {service} bash", pty=True)


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


@task(
    help={
        "filepath": "Path to the file to create or overwrite",
        "format": "Output serialization format for dumped data. (Choices: json, xml, yaml)",
        "model": "Model to include, such as 'dcim.device', repeat as needed",
    },
    iterable=["model"],
)
def dumpdata(context, format="json", model=None, filepath=None):  # pylint: disable=redefined-builtin
    """Dump data from database to db_output file."""
    if not filepath:
        filepath = f"db_output.{format}"
    command_tokens = [
        "nautobot-server dumpdata",
        f"--indent 2 --format {format} --natural-foreign --natural-primary",
        f"--output {filepath}",
    ]
    if model is not None:
        command_tokens += [" ".join(model)]
    run_command(context, " \\\n    ".join(command_tokens))


@task(help={"filepath": "Name and path of file to load."})
def loaddata(context, filepath="db_output.json"):
    """Load data from file."""
    command = f"nautobot-server loaddata {filepath}"
    run_command(context, command)


@task()
def build_and_check_docs(context):
    """Build docs for use within Nautobot."""
    build_nautobot_docs(context)
    build_example_plugin_docs(context)


def build_nautobot_docs(context):
    "Build Nautobot docs."
    command = "mkdocs build --no-directory-urls --strict"
    run_command(context, command)


def build_example_plugin_docs(context):
    """Build Example Plugin docs."""
    command = "mkdocs build --no-directory-urls --strict"
    if is_truthy(context.nautobot.local):
        local_command = f"cd examples/example_plugin && {command}"
        print_command(local_command)
        context.run(local_command, pty=True)
    else:
        docker_command = f"run --rm --workdir='/source/examples/example_plugin' --entrypoint '{command}' nautobot"
        docker_compose(context, docker_command, pty=True)


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


@task(
    help={
        "target": "Module or file or directory to inspect, repeatable",
        "recursive": "Must be set if target is a directory rather than a module or file name",
    },
    iterable=["target"],
)
def pylint(context, target=None, recursive=False):
    """Perform static analysis of Nautobot code."""
    if not target:
        # Lint everything
        # Lint the installed nautobot package and the file tasks.py in the current directory
        command = "nautobot-server pylint nautobot tasks.py"
        run_command(context, command)
        # Lint Python files discovered recursively in the development/ and examples/ directories
        command = "nautobot-server pylint --recursive development/ examples/"
        run_command(context, command)
    else:
        command = "nautobot-server pylint "
        if recursive:
            command += "--recursive "
        command += " ".join(target)
        run_command(context, command)


@task
def serve_docs(context):
    """Runs local instance of mkdocs serve (ctrl-c to stop)."""
    if is_truthy(context.nautobot.local):
        run_command(context, "mkdocs serve")
    else:
        start(context, service="mkdocs")


@task
def hadolint(context):
    """Check Dockerfile for hadolint compliance and other style issues."""
    command = "hadolint docker/Dockerfile"
    run_command(context, command)


@task
def markdownlint(context):
    """Lint Markdown files."""
    command = "markdownlint --ignore nautobot/project-static --config .markdownlint.yml --rules scripts/use-relative-md-links.js nautobot examples *.md"
    run_command(context, command)


@task
def check_migrations(context):
    """Check for missing migrations."""
    command = "nautobot-server --config=nautobot/core/tests/nautobot_config.py makemigrations --dry-run --check"

    run_command(context, command)


@task(
    help={
        "api_version": "Check a single specified API version only.",
    },
)
def check_schema(context, api_version=None):
    """Render the REST API schema and check for problems."""
    if api_version is not None:
        api_versions = [api_version]
    else:
        nautobot_version = get_nautobot_version()
        # logic equivalent to nautobot.core.settings REST_FRAMEWORK_ALLOWED_VERSIONS - keep them in sync!
        current_major, current_minor = nautobot_version.split(".")[:2]
        assert current_major == "1", f"check_schemas version calc must be updated to handle version {current_major}"
        api_versions = [f"{current_major}.{minor}" for minor in range(2, int(current_minor) + 1)]

    for api_vers in api_versions:
        command = f"nautobot-server spectacular --api-version {api_vers} --validate --fail-on-warn --file /dev/null"
        run_command(context, command)


@task(
    help={
        "cache_test_fixtures": "Save test database to a json fixture file to re-use on subsequent tests.",
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
        "label": "Specify a directory or module to test instead of running all Nautobot tests.",
        "failfast": "Fail as soon as a single test fails don't run the entire test suite.",
        "buffer": "Discard output from passing tests.",
        "tag": "Run only tests with the specified tag. Can be used multiple times.",
        "exclude_tag": "Do not run tests with the specified tag. Can be used multiple times.",
        "verbose": "Enable verbose test output.",
        "append": "Append coverage data to .coverage, otherwise it starts clean each time.",
        "skip_docs_build": "Skip (re)build of documentation before running the test.",
        "performance_report": "Generate Performance Testing report in the terminal. Has to set GENERATE_PERFORMANCE_REPORT=True in settings.py",
        "performance_snapshot": "Generate a new performance testing report to report.yml. Has to set GENERATE_PERFORMANCE_REPORT=True in settings.py",
        "default_exec": "Specify, whether to use `local` or docker compose `exec` or `run` command. Defaults to None (autodetect).",
        "group_index": "Parallel tests group index.",
    },
    iterable=["tag", "exclude_tag", "label"],
)
def unittest(
    context,
    cache_test_fixtures=False,
    keepdb=False,
    label=None,
    failfast=False,
    buffer=True,
    exclude_tag=None,
    tag=None,
    verbose=False,
    append=False,
    skip_docs_build=False,
    performance_report=False,
    performance_snapshot=False,
    default_exec=None,
    group_index=None,
):
    """Run Nautobot unit tests."""
    if not skip_docs_build:
        # First build the docs so they are available.
        build_and_check_docs(context)

    if not label:
        label = ["nautobot"]
    append_arg = " --append" if append else ""
    command = f"coverage run{append_arg} --module nautobot.core.cli test {' '.join(label)}"
    command += " --config=nautobot/core/tests/nautobot_config.py"
    # booleans
    if context.nautobot.get("cache_test_fixtures", False) or cache_test_fixtures:
        command += " --cache-test-fixtures"
    if keepdb:
        command += " --keepdb"
    if failfast:
        command += " --failfast"
    if buffer:
        command += " --buffer"
    if verbose:
        command += " --verbosity 2"
    if performance_report or (tag and "performance" in tag):
        command += " --slowreport"
    if performance_snapshot:
        command += " --slowreport --slowreportpath report.yml"
    # change the default testrunner only if performance testing is running
    if "--slowreport" in command:
        command += " --testrunner nautobot.core.tests.runner.NautobotPerformanceTestRunner"
    # lists
    if tag:
        for individual_tag in tag:
            command += f" --tag {individual_tag}"
    if exclude_tag:
        for individual_exclude_tag in exclude_tag:
            command += f" --tag {individual_exclude_tag}"

    default_exec = _resolve_default_exec(context, default_exec)
    env = {"NAUTOBOT_TEST_OUTPUT_DIR": str(_get_tests_results_path(context, default_exec))}

    if group_index is not None:
        env["NAUTOBOT_TEST_GROUP_INDEX"] = str(group_index)

    run_command(context, command, task_env=env, default_exec=default_exec)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    command = "coverage report --skip-covered --include 'nautobot/*' --omit *migrations*"

    run_command(context, command)


@task(
    help={
        "cache_test_fixtures": "Save test database to a json fixture file to re-use on subsequent tests",
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
        "label": "Specify a directory or module to test instead of running all Nautobot tests.",
        "failfast": "Fail as soon as a single test fails don't run the entire test suite.",
        "buffer": "Discard output from passing tests.",
        "tag": "Run only tests with the specified tag. Can be used multiple times.",
        "exclude_tag": "Do not run tests with the specified tag. Can be used multiple times.",
        "verbose": "Enable verbose test output.",
        "append": "Append coverage data to .coverage, otherwise it starts clean each time.",
        "skip_docs_build": "Skip (re)build of documentation before running the test.",
        "performance_report": "Generate Performance Testing report in the terminal. Set GENERATE_PERFORMANCE_REPORT=True in settings.py before using this flag",
        "performance_snapshot": "Generate a new performance testing report to report.yml. Set GENERATE_PERFORMANCE_REPORT=True in settings.py before using this flag",
    },
    iterable=["tag", "exclude_tag", "label"],
)
def integration_test(
    context,
    cache_test_fixtures=False,
    keepdb=False,
    label=None,
    failfast=False,
    buffer=True,
    tag=None,
    exclude_tag=None,
    verbose=False,
    append=False,
    skip_docs_build=False,
    performance_report=False,
    performance_snapshot=False,
):
    """Run Nautobot integration tests."""

    # Enforce "integration" tag
    tag.append("integration")

    unittest(
        context,
        cache_test_fixtures=cache_test_fixtures,
        keepdb=keepdb,
        label=label,
        failfast=failfast,
        buffer=buffer,
        tag=tag,
        exclude_tag=exclude_tag,
        verbose=verbose,
        append=append,
        skip_docs_build=skip_docs_build,
        performance_report=performance_report,
        performance_snapshot=performance_snapshot,
    )


@task(
    help={
        "cache_test_fixtures": "Save test database to a json fixture file to re-use on subsequent tests.",
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
        "label": "Specify a directory or module to test instead of running all Nautobot tests.",
        "failfast": "Fail as soon as a single test fails don't run the entire test suite.",
        "buffer": "Discard output from passing tests.",
        "tag": "Run only tests with the specified tag. Can be used multiple times.",
        "exclude_tag": "Do not run tests with the specified tag. Can be used multiple times.",
        "verbose": "Enable verbose test output.",
        "append": "Append coverage data to .coverage, otherwise it starts clean each time.",
        "skip_docs_build": "Skip (re)build of documentation before running the test.",
        "performance_snapshot": "Generate a new performance testing report to report.json. Set GENERATE_PERFORMANCE_REPORT=True in settings.py before using this flag",
    },
    iterable=["tag", "exclude_tag", "label"],
)
def performance_test(
    context,
    cache_test_fixtures=False,
    keepdb=False,
    label=None,
    failfast=False,
    buffer=True,
    tag=None,
    exclude_tag=None,
    verbose=False,
    append=False,
    skip_docs_build=False,
    performance_snapshot=False,
):
    """
    Run Nautobot performance tests.
    Prerequisite:
        Has to set GENERATE_PERFORMANCE_REPORT=True in settings.py
    """
    # Enforce "performance" tag
    tag.append("performance")

    unittest(
        context,
        cache_test_fixtures=cache_test_fixtures,
        keepdb=keepdb,
        label=label,
        failfast=failfast,
        buffer=buffer,
        tag=tag,
        exclude_tag=exclude_tag,
        verbose=verbose,
        append=append,
        skip_docs_build=skip_docs_build,
        performance_report=True,
        performance_snapshot=performance_snapshot,
    )


@task(
    help={
        "lint-only": "Only run linters; unit tests will be excluded.",
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
    }
)
def tests(context, lint_only=False, keepdb=False):
    """Run all linters and unit tests."""
    black(context)
    flake8(context)
    hadolint(context)
    markdownlint(context)
    pylint(context)
    check_migrations(context)
    check_schema(context)
    build_and_check_docs(context)
    if not lint_only:
        unittest(context, keepdb=keepdb)


def _remove_ansi_escapes(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return _ANSI_ESCAPE_RE.sub("", text)


def _invoke_unittest_group(default_exec: str, args):
    """Run `invoke unittest` in a subprocess for specified group index."""
    start_time = time.time()

    index, labels = args
    command = [
        "invoke",
        "unittest",
        "--failfast",
        "--skip-docs-build",
        "--cache-test-fixtures",
        "--keepdb",
        "--no-buffer",
        f"--default-exec={default_exec}",
        f"--group-index={index}",
        *(f"--label={label}" for label in labels),
    ]

    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        for line in iter(process.stdout.readline, ""):
            print(f"group {index:2}: {_remove_ansi_escapes(line)}", end="")
        for line in iter(process.stderr.readline, ""):
            print(f"group {index:2}: STDERR: {_remove_ansi_escapes(line)}", end="")

        process.communicate()
        if process.returncode != 0:
            print(50 * "=")
            print(f"ERROR: group {index} failed with return code {process.returncode}")
            print(50 * "=")

        return index, process.returncode, time.time() - start_time


def _print_tests_results(context, estimations, results, real_time):
    """Print tests results summary."""

    print()
    print(50 * "=")
    for result in results:
        index, returncode, group_time = result
        print(f"group {index:2}: {'SUCCESS' if returncode == 0 else 'FAILURE'}")
        print(f"group {index:2}: expected time (s): {round(estimations[index])}")
        print(f"group {index:2}: real time (s):     {round(group_time)}")

    print(50 * "=")

    summary = {
        "tests": 0,
        "errors": 0,
        "failures": 0,
        "time": 0.0,
    }

    for file in _get_tests_results_path(context, "local").glob("*.xml"):
        try:
            tree = ElementTree.parse(file)
        except ElementTree.ParseError:
            print(50 * "=")
            print(f"ERROR: Failed to parse {file}")
            print(50 * "=")
            continue
        root = tree.getroot()
        summary["tests"] += int(root.attrib.get("tests", 0))
        summary["errors"] += int(root.attrib.get("errors", 0))
        summary["failures"] += int(root.attrib.get("failures", 0))
        summary["time"] += float(root.attrib.get("time", 0.0))

    print("Tests Results Summary:")
    print("---------------------")
    print(f"Tests:    {summary['tests']}")
    print(f"Errors:   {summary['errors']}")
    print(f"Failures: {summary['failures']}")
    print(f"Tests time (s): {round(summary['time'])}")
    print(f"Real time (s):  {round(real_time)}")
    print(50 * "=")

    return summary


def _distribute_tests(distribution: DistributionType, workers) -> Tuple[List[List[str]], List[float]]:
    """Split tests into groups for parallelization.

    Returns a list of groups of tests modules and a list of estimated times for each group.
    Groups are sorted by the estimated times from the slowest to the fastest to start the slowest group first.

    There are two ways to distribute tests:

    `NAMES`:

    - Uses `_NAMES_DISTRIBUTION` to group tests by module names.
    - Each item in `_NAMES_DISTRIBUTION` results in one group of tests.
    - `_TESTS_TIMES_PATH` is used just for estimations of the tests times and doesn't affect the distribution.

    `TIMES`:

    - Uses `_TESTS_TIMES_PATH` to group tests by their times.
    - `workers` define the number of groups to create.
    - `_NAMES_DISTRIBUTION` is not used.
    - modules in each group are sorted by their times from the fastest to the slowest to fail fast.

    `TIMES` distribution is better, however randomly distributed tests can fail sometimes.
    """

    nautobot_path = _ROOT_PATH / "nautobot"
    root_dir = f"{str(_ROOT_PATH)}/"

    # Read all tests files removing the ones we want to skip
    all_tests_files = [
        str(path).replace(root_dir, "")
        for path in nautobot_path.rglob("test_*.py")
        if all(skip_name not in str(path) for skip_name in _SKIP_TESTS_NAMES)
    ]

    # Load stored tests times
    tests_times = json.loads(_TESTS_TIMES_PATH.read_text(encoding="utf-8"))

    # For NAMES distribution, group count is specified by the number of names in the distribution
    group_count = len(_NAMES_DISTRIBUTION) if distribution == DistributionType.NAMES else workers

    groups = [[] for _ in range(group_count)]
    estimations = [0.0 for _ in range(group_count)]

    obsoleted = []

    def add_file(filename: str, estimation: float, group_index=None) -> None:
        """Add file to the group and remove it from all_tests_files.

        If group_index is not specified, add to the group with the lowest estimation.
        """
        if group_index is None:
            group_index = estimations.index(min(estimations))
        try:
            all_tests_files.remove(filename)
        except ValueError:
            print(f"WARNING: {filename} was not found in all_tests_files, skipping.")
            obsoleted.append(filename)
            return
        groups[group_index].append(filename[:-3].replace("/", "."))
        estimations[group_index] += estimation

    if distribution == DistributionType.NAMES:
        # Sort more specific items first
        names = sorted(_NAMES_DISTRIBUTION, reverse=True)
        tests_times_len = len(tests_times)
        for index, name in enumerate(names):
            for item in tests_times[:]:
                if item["file"].startswith(f"nautobot/{name}"):
                    add_file(item["file"], item["time"], index)
                    tests_times.remove(item)

        if tests_times:
            raise ValueError(f"Tests not found in _NAMES_DISTRIBUTION: {tests_times}")

        avg = sum(estimations) / tests_times_len

        for index, name in enumerate(names):
            for filename in all_tests_files[:]:
                if filename.startswith(f"nautobot/{name}"):
                    print(f"WARNING: Test not found in tests_times, adding: {filename}")
                    obsoleted.append(filename)
                    add_file(filename, avg, index)
    elif distribution == DistributionType.TIMES:
        # Sort stored tests by time from slowest to fastest
        tests_times.sort(key=lambda item: item["time"], reverse=True)
        for file in tests_times:
            # Add the next slowest test to the group with the lowest total times
            add_file(file["file"], file["time"])

        avg = sum(estimations) / len(tests_times)

        for filename in all_tests_files[:]:
            print(f"WARNING: Test not found in tests_times, adding: {filename}")
            obsoleted.append(filename)
            add_file(filename, avg)

        # Run faster tests first to fail fast
        for modules in groups:
            modules.reverse()
    else:
        raise NotImplementedError("Only NAMES or TIMES distribution is supported at this time.")

    if all_tests_files:
        for filename in all_tests_files:
            print(f"ERROR: Not distributed: {filename}")
        raise RuntimeError("Not all tests were distributed, please check the logs for more information.")

    sorted_groups = sorted(groups, key=lambda group: estimations[groups.index(group)], reverse=True)
    sorted_estimations = [estimations[groups.index(group)] for group in sorted_groups]

    if obsoleted:
        print(f"WARNING: {_TESTS_TIMES_PATH} is obsolete, please update it by running `inv sum-tests-times`.")

    return sorted_groups, sorted_estimations


@task(
    name="unittest-parallel",
    help={
        "workers": "Number of parallel workers to use (default: 3)",
        "default-exec": "Default docker compose execution method 'local', 'exec' or 'run' (default: 'exec')",
        "distribution": "Distribution method `names` or `times` (default: `names`)",
    },
)
def unittest_parallel(context, workers=3, default_exec=None, distribution="names"):
    """Parallelize unit tests."""
    start_time = time.time()

    default_exec = _resolve_default_exec(context, default_exec)
    if default_exec != "local":
        # Experienced conflicts with running containers in parallel, stopping them first
        stop(context)
        if default_exec == "exec":
            docker_compose(context, "up --detach -- nautobot")
        elif default_exec == "run":
            # Only start the required containers, nautobot does not need to be running
            docker_compose(context, "up --detach -- db redis selenium")

    # Cleanup tests results
    run_command(context, f"rm -rf {_get_tests_results_path(context, default_exec)}", default_exec=default_exec)

    groups, estimations = _distribute_tests(DistributionType[distribution.upper()], workers)
    print(f"Tests distribution by {distribution} with {workers} workers:")
    for index, labels in enumerate(groups):
        print(f"group {index:2}: expected time: {round(estimations[index])} seconds, tests:")
        print("\n".join(f"  {label}" for label in labels))

    if workers > len(groups):
        workers = len(groups)
    with Pool(workers) as pool:
        results = pool.map(partial(_invoke_unittest_group, default_exec), enumerate(groups))

    _print_tests_results(context, estimations, results, time.time() - start_time)


@task
def sum_tests_times(context):
    """Summarize the time it takes to run each test file.

    Use this to rebuild the file in `_TESTS_TIMES_PATH` file after successfully running `invoke unittest-parallel`.
    Commit this file for later use.
    This file contains tests time summary for each test file rounded to the nearest second to avoid frequent changes.
    See `_distribute_tests` docstring for more information.
    """
    files = []

    for file in _get_tests_results_path(context, "local").glob("*.xml"):
        try:
            tree = ElementTree.parse(file)
        except ElementTree.ParseError:
            print(50 * "=")
            print(f"ERROR: Failed to parse {file}")
            print(50 * "=")
            continue
        root = tree.getroot()
        filename = root.attrib.get("file")
        if filename == "unittest/loader.py":
            continue
        try:
            item = next(item for item in files if item["file"] == filename)
        except StopIteration:
            item = {"file": filename, "time": 0.0}
            files.append(item)
        item["time"] += float(root.attrib.get("time", 0.0))

    files.sort(key=lambda item: item["file"])
    # Round to the nearest second to avoid unnecessary changes to the file
    for item in files:
        item["time"] = round(item["time"] + 0.5)
    _TESTS_TIMES_PATH.write_text(json.dumps(files, indent=4), encoding="utf-8")

    print(f"Tests times written to `{_TESTS_TIMES_PATH}`. Commit this file for later use.")

    print("Top 10 slowest tests:")
    files.sort(key=lambda item: item["time"], reverse=True)
    for item in files[:10]:
        print(f"{item['file']}: {item['time']}")


@task(
    help={
        "service": "If specified, only display logs for this service (default: all)",
        "follow": "Flag to follow logs (default: False)",
        "tail": "Tail N number of lines (default: all)",
    }
)
def logs(context, service="", follow=False, tail=0):
    """View the logs of a docker compose service."""
    command = "logs "

    if follow:
        command += "--follow "
    if tail:
        command += f"--tail={tail} "

    docker_compose(context, command, service=service)


@task
def export_docker_compose(context):
    """Export docker compose configuration to `compose.yaml` file.

    Useful to:

    - Debug docker compose configuration.
    - Allow using `docker compose` command directly without invoke.
    """
    docker_compose(context, "convert > compose.yaml")


@task(name="ps", help={"all": "Show all, including stopped containers"})
def ps_task(context, _all=False):
    """List containers."""
    docker_compose(context, f"ps {'--all' if _all else ''}")
