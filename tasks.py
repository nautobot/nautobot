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
import sys
import time
from contextlib import contextmanager
from enum import Enum
from enum import auto
from functools import partial
from multiprocessing import Pool
from pathlib import Path
from typing import Iterable, List
from typing import Mapping
from typing import Optional
from typing import Tuple
from typing import Union
from xml.etree import ElementTree

from dotenv import dotenv_values
from dotenv import load_dotenv
from invoke.collection import Collection
from invoke.exceptions import Exit
from invoke.tasks import task

try:
    # Override built-in print function with rich's pretty-printer function, if available
    from rich import print  # pylint: disable=redefined-builtin
except ModuleNotFoundError:
    # Avoid typing error
    print = print

# Regex to match ANSI escape sequences, to be able to remove them from the output
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_DOCKER_NAUTOBOT_PATH = Path("/opt/nautobot")
_DOCKER_SOURCE_PATH = Path("/source")
# Magic constant for relativising tests times, to get some singinificant bits
_MAGIC_CONSTANT = 420
# Repository root path
_ROOT_PATH = Path(__file__).parent.absolute().resolve()
# Maximum worker count is limited by the number of Redist databases (16)
_MAX_PARALLEL_WORKER_COUNT = 6
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



# Custom dotenv file, allows to override default values
load_dotenv(_ROOT_PATH / ".env")

# Use pyinvoke configuration for default values, see: http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Defaults can be overwritten in invoke.yml "nautobot" key, or by the environment variables INVOKE_NAUTOBOT_xxx
_INVOKE_PROJECT_DEFAULTS = {
    "local": False,
    "project_name": "nautobot",
    "python_ver": "3.8",
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
# Defaults can be overwritten in invoke.yml "docker" key, or by the environment variables INVOKE_DOCKER_xxx
_INVOKE_DOCKER_DEFAULTS = {
    # Autodetect for service, "local", "exec" or "run"
    "action": None,
    "service": "nautobot",
    "path_separator": ":",
}
# Defaults can be overwritten in invoke.yml "run" key, or by the environment variables INVOKE_RUN_xxx
_INVOKE_RUN_DEFAULTS = {
    "echo": True,
    "pty": True,
}


def _is_truthy(arg):
    """Convert "truthy" strings into Booleans.

    Examples:
        >>> _is_truthy('yes')
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


def _get_source_path(context):
    """Return the path to the source directory."""
    if _is_truthy(context.nautobot.local):
        return _ROOT_PATH
    else:
        return _DOCKER_SOURCE_PATH


def _get_ui_path(context):
    """Return the path to the UI directory."""
    if _is_truthy(context.nautobot.local):
        return _ROOT_PATH / "nautobot/ui"
    else:
        return _DOCKER_NAUTOBOT_PATH / "ui"


def _is_compose_included(context, name):
    return f"docker-compose.{name}.yml" in context.nautobot.compose_files


def _resolve_docker_action(context, docker_action=None, service="nautobot") -> str:
    """Resolve the default docker command invocation action and keep track of it for `service` in `context`.

    Possible return values are "local", "exec", or "run".
    "exec" and "run" are invoked using docker compose.

    Service is used when calling `_run()`.
    """
    if not service:
        service = context.docker.service

    if docker_action is None:
        if context.docker.action is not None:
            if context.docker.service == service:
                return context.docker.action

        if _is_truthy(context.nautobot.local):
            result = "local"
        else:
            ps_result = _docker_compose(context, "ps --services --filter status=running", hide=True)
            result = "exec" if service in ps_result.stdout else "run"
    else:
        result = docker_action

    if result in ("local", "exec", "run"):
        context.docker.action = result
        context.docker.service = service
        return result

    raise ValueError(f"Invalid docker action: {docker_action}")


@contextmanager
def _cd(context, workdir: Optional[Union[Path, str]] = None):
    """Change directory to package root dir or `workdir` if specified.

    To keep output clean if not needed to change directory.
    """
    if workdir:
        workdir = Path(workdir).absolute().resolve()
    else:
        workdir = _ROOT_PATH

    if Path(context.cwd).absolute() == workdir:
        yield
    else:
        with context.cd(workdir):
            yield


def _docker_compose(
    context,
    command: Union[str, Iterable[str]],
    service: Optional[Union[str, Iterable[str]]] = None,
    service_command="",
    env=None,
    hide=False,
    **kwargs,
):
    """Helper function for running a specific docker compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """

    def get_command():
        yield "docker compose"

        if isinstance(command, str):
            yield command
        else:
            yield from command

        if service:
            yield "--"
            if isinstance(service, str):
                yield service
            else:
                yield from service
            yield service_command

    compose_command = " ".join(item for item in get_command() if item)

    env = {
        "COMPOSE_FILE": context.docker.path_separator.join(
            f"development/{filename}" for filename in context.nautobot.compose_files
        ),
        "COMPOSE_PATH_SEPARATOR": context.docker.path_separator,
        "COMPOSE_PROJECT_NAME": context.nautobot.project_name,
        "PYTHON_VER": context.nautobot.python_ver,
        **(env or {}),
        **dotenv_values(_ROOT_PATH / ".env"),
    }

    with _cd(context):
        return context.run(compose_command, env=env, hide=hide, **kwargs)


def _run(
    context,
    command: Union[str, Iterable[str]],
    service="",
    docker_action: Optional[str] = None,
    docker_args: Optional[Union[str, Iterable[str]]] = None,
    env: Optional[Mapping[str, str]] = None,
    workdir: Union[str, Path] = "",
    hide=False,
    root=False,
    **kwargs,
):
    """Wrapper to run a command locally or inside the nautobot container."""

    def get_docker_command():
        if docker_action == "exec":
            yield "exec"
        elif docker_action == "run":
            yield "run --rm --entrypoint=''"
        else:
            raise ValueError(f"Invalid docker action: {docker_action}")

        # Pass environment variables names to docker container
        # Values are passed later in `_docker_compose` using context `env` not to expose it to CLI
        # Pass `env` argument:
        yield from (f"--env='{key}'" for key in (env or {}))
        # Pass custom `.env` file:
        yield from (f"--env='{key}'" for key in (dotenv_values(_ROOT_PATH / ".env")))

        if workdir:
            yield f"--workdir='{workdir}'"

        if root:
            yield "--user=root"

        if docker_args:
            if isinstance(docker_args, str):
                yield docker_args
            else:
                yield from docker_args

    if env:
        kwargs["env"] = env

    docker_action = _resolve_docker_action(context, docker_action, service)
    if not service:
        service = context.docker.service

    if not isinstance(command, str):
        command = " ".join(item for item in command if item)

    if docker_action == "local":
        with _cd(context, workdir):
            context.run(command, hide=hide, **kwargs)
    else:
        if workdir and isinstance(workdir, str):
            workdir = _DOCKER_SOURCE_PATH / workdir

        _docker_compose(context, get_docker_command(), service, command, hide=hide, **kwargs)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
def _get_build_args(context, cache: bool, force_rm: bool, local_user: bool, pull: bool) -> Iterable[str]:
    yield f"--build-arg PYTHON_VER={context.nautobot.python_ver}"
    yield "--build-arg POETRY_INSTALLER_PARALLEL=true"

    if not cache:
        yield "--no-cache"

    if force_rm:
        yield "--force-rm"

    if local_user:
        yield f"--build-arg NAUTOBOT_UID={os.getuid()}"
        yield f"--build-arg NAUTOBOT_GID={os.getgid()}"

    if pull:
        yield "--pull"


@task(
    help={
        "cache": "Whether to use Docker's cache when building the image. (default: enabled)",
        "force_rm": "Always remove intermediate containers.",
        "local_user": "If specified, use the local user's UID/GID in the container. (default: enabled)",
        "pull": "Whether to pull Docker images when building the image. (default: disabled)",
        "service": "If specified, only build this service (default: build all).",
    }
)
def build(context, cache=True, force_rm=False, local_user=True, pull=False, service=""):
    """Build Nautobot docker image."""
    print(f"Building Nautobot with Python {context.nautobot.python_ver}...")

    def get_command():
        yield "build"
        yield from _get_build_args(context, cache, force_rm, local_user, pull)

    _docker_compose(context, get_command(), service=service, pty=False)


@task
def build_dependencies(context):
    """Determine preferred/default target architecture"""
    output = context.run("docker buildx inspect default", env={"PYTHON_VER": context.nautobot.python_ver}, hide=True)
    result = re.search(r"Platforms: ([^,\n]+)", output.stdout)

    build_kwargs = {
        "dependencies_base_branch": "local",
        "tag": f"ghcr.io/nautobot/nautobot-dependencies:local-py{context.nautobot.python_ver}",
        "target": "dependencies",
        "pull": False,
    }

    if result and len(result.groups()):
        build_kwargs["platforms"] = result.group(1)
    else:
        print("Failed to identify platform building for, falling back to default.")

    buildx(context, **build_kwargs)


@task(
    help={
        "cache": "Whether to use Docker's cache when building the image. (default: disabled)",
        "cache_dir": "Directory to use for caching buildx output. (default: current directory)",
        "local_user": "If specified, use the local user's UID/GID in the container. (default: disabled)",
        "platforms": "Comma-separated list of strings for which to build. (default: linux/amd64)",
        "pull": "Whether to pull Docker images when building the image. (default: disabled)",
        "tag": "Tags to be applied to the built image. (default: depends on the --target)",
        "target": "Build target from the Dockerfile. (default: dev)",
    }
)
def buildx(
    context,
    cache=False,
    cache_dir=".",
    local_user=False,
    platforms="linux/amd64",
    pull=False,
    tag="",
    target="dev",
):
    """Build Nautobot docker image using the experimental buildx docker functionality (multi-arch capability)."""
    print(f"Building Nautobot {target} target with Python {context.nautobot.python_ver} for {platforms}...")

    if not tag:
        if target == "dev":
            pass
        elif target == "final-dev":
            tag = f"networktocode/nautobot-dev-py{context.nautobot.python_ver}:local"
        elif target == "final":
            tag = f"networktocode/nautobot-py{context.nautobot.python_ver}:local"
        else:
            print(f"Not sure what should be the standard tag for target {target}, will not tag.")

    def get_command():
        yield "docker buildx build ."
        yield f"--platform='{platforms}'"
        yield f"--target='{target}'"
        yield "--load"
        yield "--file ./docker/Dockerfile"

        yield from _get_build_args(context, cache=cache, force_rm=False, local_user=local_user, pull=pull)

        if tag:
            yield f"--tag='{tag}'"

        if cache:
            yield f"--cache-to='type=local,dest={cache_dir}/{context.nautobot.python_ver}'"
            yield f"--cache-from='type=local,src={cache_dir}/{context.nautobot.python_ver}'"

    with _cd(context):
        context.run(" ".join(get_command()), pty=False)


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
    return version_match and version_match.group(1)


@task(
    help={
        "branch": "Source branch used to push.",
    }
)
def docker_push(context, branch):
    """Tags and pushes docker images to the appropriate repos, intended for release use only.

    Before running this command, you **must** be on the `main` branch and **must** have run
    the appropriate set of `invoke buildx` commands. Refer to the developer release-checklist docs for details.
    """
    nautobot_version = get_nautobot_version()

    docker_image_tags_main = [
        f"stable-py{context.nautobot.python_ver}",
        f"{nautobot_version}-py{context.nautobot.python_ver}",
    ]

    if context.nautobot.python_ver == "3.8":
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
            with _cd(context):
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
@task(help={"service": "If specified, only affect this service."}, iterable=["service"])
def debug(context, service=None):
    """Start Nautobot and its dependencies in debug mode."""
    print("Starting Nautobot in debug mode...")
    _docker_compose(context, "up", service=service)


@task(help={"service": "If specified, only affect this service."}, iterable=["service"])
def start(context, service=None):
    """Start Nautobot and its dependencies in detached mode."""
    print("Starting Nautobot in detached mode...")
    _docker_compose(context, "up --detach", service=service)


@task(help={"service": "If specified, only affect this service."}, iterable=["service"])
def restart(context, service=None):
    """Gracefully restart containers."""
    print("Restarting Nautobot...")
    _docker_compose(context, "restart", service=service)


@task(help={"service": "If specified, only affect this service."}, iterable=["service"])
def stop(context, service=None):
    """Stop Nautobot and its dependencies."""
    print("Stopping Nautobot...")
    if service:
        _docker_compose(context, "stop", service=service)
    else:
        _docker_compose(context, "down --remove-orphans")


@task
def destroy(context):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...")
    _docker_compose(context, "down --remove-orphans --volumes")


@task(
    help={
        "service": "If specified, only display logs for this service (default: all)",
        "follow": "Flag to follow logs (default: False)",
        "tail": "Tail N number of lines (default: all)",
    },
    iterable=["service"],
)
def logs(context, service=None, follow=False, tail=0):
    """View the logs of a docker compose service."""

    def get_command():
        yield "logs"

        if follow:
            yield "--follow"

        if tail:
            yield f"--tail={tail}"

    _docker_compose(context, get_command(), service=service)


@task
def export_docker_compose(context):
    """Export docker compose configuration to `compose.yaml` file.

    Useful to:

    - Debug docker compose configuration.
    - Allow using `docker compose` command directly without invoke.
    """
    _docker_compose(context, "convert > compose.yaml")


@task(name="ps", help={"all": "Show all, including stopped containers"})
def ps_task(context, _all=False):
    """List containers."""
    _docker_compose(context, f"ps {'--all' if _all else ''}")


@task
def vscode(context):
    """Launch Visual Studio Code with the appropriate Environment variables to run in a container."""
    command = "code nautobot.code-workspace"

    with _cd(context):
        context.run(command, env={"PYTHON_VER": context.nautobot.python_ver})


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task(
    help={
        "code": "Python code to run (default: empty)",
        "input-file": "Python file to execute and quit (default: empty)",
        "output-file": "Ouput file, overwrite if exists (default: empty)",
    }
)
def nbshell(context, code="", input_file="", output_file=""):
    """Launch an interactive shell session, or run commands."""
    pty = not (code or input_file)
    if pty:
        if output_file:
            raise ValueError("`output-file` argument requires `input-file` or `code` argument")
    else:
        if code and input_file:
            raise ValueError("Cannot specify both, `code` and `input-file` arguments")

    def get_command():
        yield "nautobot-server shell_plus"

        if input_file:
            yield f"< '{input_file}'"

        if output_file:
            yield f"> '{output_file}'"

        if code:
            yield '<<< "$NBSHELL_CODE"'

    _run(context, get_command(), pty=pty, env={"NBSHELL_CODE": code})


@task(
    help={
        "command": "Command to run (default: bash).",
        "docker-arg": "Additional arguments to pass to docker command (default: empty)",
        "input-file": "File to run command with (default: empty)",
        "output-file": "Ouput file, overwrite if exists (default: empty)",
        "root": "Launch shell as root (default: disabled)",
        "run": "Whether to run command in a new container (default: auto-detect)",
        "service": "Docker compose service name to run command in (default: nautobot).",
    },
    iterable=["docker_arg"],
)
def cli(
    context,
    command="bash",
    docker_arg=None,
    input_file="",
    output_file="",
    root=False,
    run=False,
    service="nautobot",
):
    """Launch a bash shell inside the running Nautobot (or other) Docker container.

    Examples:
        >>> # To launch customized Nautobot server, you can update your `.env` file and run:
        >>> inv cli -c='nautobot-server runserver 0.0.0.0:8080 --insecure' --docker-arg='--service-ports'
    """
    context.nautobot.local = False

    def get_command():
        yield command

        if input_file:
            yield f"< '{input_file}'"

        if output_file:
            yield f"> '{output_file}'"

    _run(
        context,
        get_command(),
        service=service,
        root=root,
        docker_action="run" if run else None,
        docker_args=docker_arg,
    )


@task(
    help={
        "user": "Name of the superuser to create. (default: admin)",
    }
)
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    _run(context, f"nautobot-server createsuperuser --username {user}")


@task(help={"name": "Use this name for migration file(s). If unspecified, a name will be generated."})
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = "nautobot-server makemigrations"

    if name:
        command += f" --name {name}"

    _run(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    _run(context, "nautobot-server migrate")


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
    """
    _run(context, "nautobot-server post_upgrade")


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
        "--indent=2",
        "--format={format}",
        "--natural-foreign",
        "--natural-primary",
        f"--output='{filepath}'",
        *(model or []),
    ]
    _run(context, command_tokens)


@task(
    help={
        "db-name": "Database name to connect to (default: read from environment)",
        "query": "SQL command to execute and quit (default: empty)",
        "input-file": "SQL file to execute and quit (default: empty)",
        "output-file": "Ouput file, overwrite if exists (default: empty)",
    }
)
def dbshell(context, query="", input_file="", output_file="", db_name=""):
    """Start database CLI inside the running `db` container.

    Doesn't use `nautobot-server dbshell`, using started `db` service container only.

    Prerequisites:
        - Started `db` container.
    """
    pty = not (query or input_file)
    if pty:
        if output_file:
            raise ValueError("`output-file` argument requires `input-file` or `query` argument")
    else:
        if query and input_file:
            raise ValueError("Cannot specify both, `query` and `input-file` arguments")

    env = {}
    dev_env = dotenv_values(_ROOT_PATH / "development/dev.env")

    def get_command():
        if _is_compose_included(context, "mysql"):
            env["MYSQL_PWD"] = dev_env.get("MYSQL_PASSWORD", "")

            yield "mysql"
            yield f"--user='{dev_env.get('MYSQL_USER')}'"
            yield f"--database='{db_name or dev_env.get('MYSQL_DATABASE')}'"
            yield f"--execute='{query}'" if query else ""
        elif _is_compose_included(context, "postgres"):
            yield "psql"
            yield f"--username='{dev_env.get('POSTGRES_USER')}'"
            yield f"--dbname='{db_name or dev_env.get('POSTGRES_DB')}'"
            yield f"--command='{query}'" if query else ""
        else:
            raise ValueError("Unsupported database backend.")

        if input_file:
            yield f"< '{input_file}'"
        if output_file:
            yield f"> '{output_file}'"

    _run(context, get_command(), service="db", docker_action="exec", env=env, pty=pty)


@task(
    help={
        "input-file": "SQL dump file to replace the existing database with. This can be generated using `invoke backup-db` (default: `dump.sql`).",
    }
)
def import_db(context, input_file="dump.sql"):
    """Stop Nautobot containers and replace the current database with the dump into the running `db` container.

    Prerequisites:
        - Started `db` container.
    """
    stop(context, service=["nautobot", "celery_worker", "celery_beat"])

    env = {}
    dev_env = dotenv_values(_ROOT_PATH / "development/dev.env")

    def get_command():
        if _is_compose_included(context, "mysql"):
            env["MYSQL_PWD"] = dev_env.get("MYSQL_PASSWORD", "")

            yield "mysql"
            yield f"--user='{dev_env.get('MYSQL_USER')}'"
            yield f"--database='{dev_env.get('MYSQL_DATABASE')}'"
        elif _is_compose_included(context, "postgres"):
            yield "psql"
            yield f"--username='{dev_env.get('POSTGRES_USER')}'"
            yield "postgres"
        else:
            raise ValueError("Unsupported database backend.")

        yield f"< '{input_file}'"

    _run(context, get_command(), service="db", docker_action="exec", env=env, pty=False)

    print("Database import complete, you can start Nautobot now: `invoke start`")


@task(
    help={
        "db-name": "Database name to backup (default: read from environment)",
        "output-file": "Ouput file, overwrite if exists (default: `dump.sql`)",
        "readable": "Flag to dump database data in more readable format (default: `True`)",
    }
)
def backup_db(context, db_name="", output_file="dump.sql", readable=True):
    """Dump database into `output-file` file from running `db` container.

    Prerequisites:
        - Started `db` container.
    """
    env = {}
    dev_env = dotenv_values(_ROOT_PATH / "development/dev.env")

    def get_command():
        if _is_compose_included(context, "mysql"):
            env["MYSQL_PWD"] = dev_env.get("MYSQL_PASSWORD", "")

            yield "mysqldump"
            yield "--user=root"
            yield "--add-drop-database"

            if readable:
                yield "--skip-extended-insert"

            yield "--databases"
            yield db_name or dev_env.get("MYSQL_DATABASE") or ""
        elif _is_compose_included(context, "postgres"):
            yield "pg_dump"
            yield "--clean"
            yield "--create"
            yield "--if-exists"
            yield f"--username='{dev_env.get('POSTGRES_USER')}'"
            yield f"--dbname='{db_name or dev_env.get('POSTGRES_DB')}'"

            if readable:
                yield "--inserts"
        else:
            raise ValueError("Unsupported database backend.")

        if output_file:
            yield f"> '{output_file}'"

    _run(context, get_command(), service="db", docker_action="exec", env=env, pty=False)

    print(50 * "=")
    print("The database backup has been successfully completed and saved to the file:")
    print(output_file)
    print("If you want to import this database backup, please execute the following command:")
    print(f"invoke import-db --input-file '{output_file}'")
    print(50 * "=")


@task(help={"filepath": "Name and path of file to load."})
def loaddata(context, filepath="db_output.json"):
    """Load data from file."""
    command = f"nautobot-server loaddata {filepath}"
    _run(context, command)


@task
def build_and_check_docs(context):
    """Build docs for use within Nautobot."""
    build_nautobot_docs(context)
    build_example_plugin_docs(context)


@task
def build_nautobot_docs(context):
    "Build Nautobot docs."
    _run(context, "mkdocs build --no-directory-urls --strict")


@task
def build_example_plugin_docs(context):
    """Build Example Plugin docs."""
    command = "mkdocs build --no-directory-urls --strict"
    _run(context, command, workdir="examples/example_plugin")


@task(name="help")
def help_task(context):
    """Print the help of available tasks."""
    for task_name in sorted(namespace.task_names):
        print(50 * "-")
        print(f"invoke --help {task_name}")
        context.run(f"invoke --help {task_name}")


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

    _run(context, command)


@task
def flake8(context):
    """Check for PEP8 compliance and other style issues."""
    _run(context, "flake8 development/ examples/ nautobot/ tasks.py")


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
        _run(context, command)
        # Lint Python files discovered recursively in the development/ and examples/ directories
        command = "nautobot-server pylint --recursive development/ examples/"
        _run(context, command)
    else:
        command = "nautobot-server pylint "
        if recursive:
            command += "--recursive "
        command += " ".join(target)
        _run(context, command)


@task
def yamllint(context):
    """Run yamllint to validate formatting applies to YAML standards."""
    # TODO: enable for directories other than nautobot/docs and fix all warnings
    command = "yamllint nautobot/docs --format standard"
    _run(context, command)


@task
def serve_docs(context):
    """Runs local instance of mkdocs serve (ctrl-c to stop)."""
    if _is_truthy(context.nautobot.local):
        _run(context, "mkdocs serve")
    else:
        start(context, service="mkdocs")


@task
def hadolint(context):
    """Check Dockerfile for hadolint compliance and other style issues."""
    command = "hadolint docker/Dockerfile"
    _run(context, command)


@task
def markdownlint(context):
    """Lint Markdown files."""
    source_path = _get_source_path(context)

    command = (
        "npx",
        "--",
        "markdownlint-cli",
        f"--ignore='{source_path / 'nautobot/project-static'}'",
        f"--ignore='{source_path / 'nautobot/ui/node_modules'}'",
        f"--config='{source_path / '.markdownlint.yml'}'",
        f"--rules='{source_path / 'scripts/use-relative-md-links.js'}'",
        f"'{source_path / 'nautobot'}'",
        f"'{source_path / 'examples'}'",
        f"{source_path}/*.md",
    )

    _run(context, command, workdir=_get_ui_path(context))


@task
def check_migrations(context):
    """Check for missing migrations."""
    command = (
        "nautobot-server",
        "--config=nautobot/core/tests/nautobot_config.py",
        "makemigrations",
        "--dry-run",
        "--check",
    )

    _run(context, command)


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
        current_major, current_minor = [int(v) for v in nautobot_version.split(".")[:2]]
        assert current_major == 2, f"check_schemas version calc must be updated to handle version {current_major}"
        api_versions = [f"{current_major}.{minor}" for minor in range(0, current_minor + 1)]

    for api_vers in api_versions:
        command = f"nautobot-server spectacular --api-version {api_vers} --validate --fail-on-warn --file /dev/null"
        _run(context, command)


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
        "docker_action": "Specify, whether to use `local` or docker compose `exec` or `run` command. Defaults to None (autodetect).",
        "group_index": "Parallel tests group index.",
        "fixture_file": "Path to a fixture file to use for tests.",
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
    docker_action=None,
    group_index=None,
    fixture_file=None,
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
    if fixture_file:
        command += f" --fixture-file={fixture_file}"
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

    docker_action = _resolve_docker_action(context, docker_action)
    env = {"NAUTOBOT_TEST_OUTPUT_DIR": str(_get_tests_results_path(context, docker_action))}

    if group_index is not None:
        env["NAUTOBOT_TEST_GROUP_INDEX"] = str(group_index)

    _run(context, command, env=env, docker_action=docker_action)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    command = "coverage report --skip-covered --include 'nautobot/*' --omit *migrations*"

    _run(context, command)


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
    if not tag:
        tag = []
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
        "dataset": "File (.sql.tar.gz) to start from that will untar to 'nautobot.sql'",
        "db_engine": "mysql or postgres",
        "db_name": "Temporary database to create, test, and destroy",
    },
)
def migration_test(context, dataset, db_engine="postgres", db_name="nautobot_migration_test"):
    """Test database migration from a given dataset to latest Nautobot schema."""
    with _cd(context):
        if _resolve_docker_action(context, None, service="db") == "local":
            _run(context, f"tar zxvf {dataset}")
        else:
            # DB must be running, else will fail with errors like:
            # dropdb: error: could not connect to database template1: could not connect to server: No such file or directory
            start(context, service="db")
            source_file = os.path.basename(dataset)
            context.run(f"docker cp '{dataset}' nautobot-db-1:/tmp/{source_file}")
            _run(context, f"tar zxvf /tmp/{source_file}")

        if db_engine == "postgres":
            common_args = "-U $NAUTOBOT_DB_USER --no-password -h localhost"
            _run(context, f"sh -c 'dropdb --if-exists {common_args} {db_name}'")
            _run(context, f"sh -c 'createdb {common_args} {db_name}'")
            _run(context, f"sh -c 'psql {common_args} -d {db_name} -f nautobot.sql'")
        else:
            # "weird historical idiosyncrasy in MySQL where 'localhost' means a UNIX socket, and '127.0.0.1' means TCP/IP"
            base_command = "mysql --user=$NAUTOBOT_DB_USER --password=$NAUTOBOT_DB_PASSWORD --host 127.0.0.1"
            _run(context, f"sh -c '{base_command} -e \"DROP DATABASE IF EXISTS {db_name};\"'")
            _run(context, f"sh -c '{base_command} -e \"CREATE DATABASE {db_name};\"'")
            _run(context, f"sh -c '{base_command} {db_name} < nautobot.sql'")

        _run(context, command="nautobot-server migrate", service="nautobot", env={"NAUTOBOT_DB_NAME": db_name})


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
    if not tag:
        tag = []
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
        "label": "Specify a directory to test instead of running all Nautobot UI tests.",
    },
)
def unittest_ui(
    context,
    label=None,
):
    """Run Nautobot UI unit tests."""
    command = "npm run test -- --watchAll=false"
    if label:
        command += f" {label}"
    _run(context, command, service="nodejs")


@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect.",
    }
)
def prettier(context, autoformat=False):
    """Check Node.JS code style with Prettier."""

    command = (
        "npx",
        "--",
        "prettier",
        "--write" if autoformat else "--check",
        "./",
    )

    _run(context, command, workdir=_get_ui_path(context))


@task(
    help={
        "autoformat": "Apply some recommendations automatically, rather than failing if formatting is incorrect. Not all issues can be fixed automatically.",
    }
)
def eslint(context, autoformat=False):
    """Check for ESLint rule compliance and other style issues."""
    command = (
        "npx eslint",
        "--max-warnings 0",
        "--fix" if autoformat else "",
        "./",
    )

    _run(context, command, service="nautobot", workdir=_get_ui_path(context), env={"NODE_ENV": "test"})


@task(
    help={
        "failfast": "fail as soon as a single test fails don't run the entire test suite",
        "keepdb": "Save and re-use test database between test runs for faster re-testing.",
        "lint-only": "Only run linters; unit tests will be excluded.",
    }
)
def tests(context, failfast=False, keepdb=False, lint_only=False):
    """Run all linters and unit tests."""
    black(context)
    flake8(context)
    prettier(context)
    eslint(context)
    hadolint(context)
    markdownlint(context)
    yamllint(context)
    pylint(context)
    check_migrations(context)
    check_schema(context)
    build_and_check_docs(context)
    if not lint_only:
        unittest(context, failfast, keepdb=keepdb)


def _get_tests_results_path(context, docker_action: str) -> Path:
    """Return the directory to store tests results in, different for docker and local runs."""
    if _resolve_docker_action(context, docker_action) == "local":
        return _ROOT_PATH / _TESTS_RESULTS_DIR_NAME
    else:
        return Path("/source") / _TESTS_RESULTS_DIR_NAME


def _remove_ansi_escapes(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return _ANSI_ESCAPE_RE.sub("", text)


def _print_tests_results(context, estimations, results, real_time):
    """Print tests results summary."""

    print()
    print(50 * "=")
    for result in results:
        group_index, returncode, group_time = result
        print(f"group {group_index:2}: {'SUCCESS' if returncode == 0 else 'FAILURE'}")
        print(f"group {group_index:2}: relative time: {round(estimations[group_index])}")
        print(f"group {group_index:2}: real time (s): {round(group_time)}")

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


def _distribute_tests(distribution: DistributionType, worker_count) -> Tuple[List[List[str]], List[float]]:
    """Split tests into groups for parallelization.

    Returns a list of groups of tests modules and a list of estimated times for each group.
    Groups are sorted by the estimated times from the slowest to the fastest to start the slowest group first.

    There are two ways to distribute tests:

    `NAMES`:

    - Uses `_NAMES_DISTRIBUTION` to group tests by module names.
    - Each item in `_NAMES_DISTRIBUTION` results in one group of tests.
    - `_TESTS_TIMES_PATH` is used when reducing groups to worker count.

    `TIMES`:

    - Uses `_TESTS_TIMES_PATH` to group tests by their times.
    - `worker_count` define the number of groups to create.
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
    group_count = len(_NAMES_DISTRIBUTION) if distribution == DistributionType.NAMES else worker_count

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

    def sort_groups(groups, estimations) -> Tuple[List[List[str]], List[float]]:
        sorted_groups = sorted(groups, key=lambda group: estimations[groups.index(group)], reverse=True)
        sorted_estimations = [estimations[groups.index(group)] for group in sorted_groups]
        return sorted_groups, sorted_estimations

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

        if group_count > worker_count:
            # Reduce number of groups to worker_count
            sorted_groups, sorted_estimations = sort_groups(groups, estimations)

            groups = [[] for _ in range(worker_count)]
            estimations = [0.0 for _ in range(worker_count)]

            for group_index, group in enumerate(sorted_groups):
                fastest_group_index = estimations.index(min(estimations))
                groups[fastest_group_index] += group
                estimations[fastest_group_index] += sorted_estimations[group_index]
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

    if obsoleted:
        print(f"WARNING: {_TESTS_TIMES_PATH} is obsolete, please update it by running `inv sum-tests-times`.")

    return sort_groups(groups, estimations)


def _invoke_unittest_group(docker_action, args):
    start_time = time.time()
    group_index, labels = args

    command = [
        "invoke",
        "unittest",
        "--failfast",
        "--skip-docs-build",
        "--cache-test-fixtures",
        f"--fixture-file=development/factory_dump_{group_index}.json",
        "--keepdb",
        "--no-buffer",
        f"--docker-action={docker_action}",
        f"--group-index={group_index}",
        *(f"--label={label}" for label in labels),
    ]

    with subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        for line in iter(process.stdout.readline, ""):  # type: ignore
            print(f"group {group_index:2}: {_remove_ansi_escapes(line)}", end="")
        for line in iter(process.stderr.readline, ""):  # type: ignore
            print(f"group {group_index:2}: STDERR: {_remove_ansi_escapes(line)}", end="")

        process.communicate()
        if process.returncode != 0:
            print(50 * "=")
            print(f"group {group_index} FAILED with return code {process.returncode}")
            print(50 * "=")

        return group_index, process.returncode, time.time() - start_time


@task(
    name="unittest-parallel",
    help={
        "worker_count": "Number of parallel worker_count to use (default: 3)",
        "docker-action": "Default docker compose execution method 'local', 'exec' or 'run' (default: 'exec')",
        "distribution": "Distribution method `names` or `times` (default: `names`)",
    },
)
def unittest_parallel(context, worker_count=3, docker_action=None, distribution="names"):
    """Parallelize unit tests."""

    if worker_count > _MAX_PARALLEL_WORKER_COUNT:
        raise ValueError(f"Maximum value for worker_count is {_MAX_PARALLEL_WORKER_COUNT}.")

    start_time = time.time()

    docker_action = _resolve_docker_action(context, docker_action)
    if docker_action != "local":
        # Experienced conflicts with running containers in parallel, stopping them first
        stop(context)
        if docker_action == "exec":
            start(context, service=["nautobot"])
        elif docker_action == "run":
            # Only start the required containers, nautobot does not need to be running
            start(context, service=["db", "redis", "selenium"])

    # Cleanup tests results
    _run(context, f"rm -rf {_get_tests_results_path(context, docker_action)}", docker_action=docker_action)

    groups, estimations = _distribute_tests(DistributionType[distribution.upper()], worker_count)
    if worker_count > len(groups):
        worker_count = len(groups)

    print(f"Tests distribution by {distribution} with {worker_count} worker_count:")
    for group_index, labels in enumerate(groups):
        print(f"group {group_index:2}: relative time: {round(estimations[group_index])}, tests:")
        print("\n".join(f"  {label}" for label in labels))

    with Pool(worker_count) as pool:
        results = pool.map(partial(_invoke_unittest_group, docker_action), enumerate(groups))

    summary = _print_tests_results(context, estimations, results, time.time() - start_time)
    if any(result[1] != 0 for result in results) or summary["errors"] > 0 or summary["failures"] > 0:
        raise Exit("Some tests failed, please check the logs for more information.")


@task
def sum_tests_times(context):
    """Summarize the time it takes to run each test file.

    Use this to rebuild the file `_TESTS_TIMES_PATH` file after successfully running `invoke unittest-parallel`.
    Resulting file contains tests time summary for each test file and should be committed to the repository.
    See `_distribute_tests` docstring for more information.
    `time` key for each test is relativised to avoid frequent changes.
    """
    files = []
    sum_time = 0.0
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
        item_time = float(root.attrib.get("time", 0.0))
        item["time"] += item_time
        sum_time += item_time

    # Magic value other times will relate to, based on average time of all tests and a magic constant
    relative_to = sum_time / len(files) / _MAGIC_CONSTANT

    def relativise(value: float) -> int:
        "Keep only 4 bits of precision relative to `relative_to` magic value"
        if value == 0.0:
            return 0
        integer = round(value / relative_to)
        if integer == 0:
            return 1
        shift_len = len(bin(integer)) - 4 - 2  # `- 2` for `0b` prefix
        if shift_len > 0:
            return (integer >> shift_len) << shift_len
        else:
            return integer

    files.sort(key=lambda item: item["file"])

    for item in files:
        item["time"] = relativise(item["time"])

    _TESTS_TIMES_PATH.write_text(json.dumps(files, indent=4), encoding="utf-8")

    print(f"Tests times written to `{_TESTS_TIMES_PATH}`. Commit this file for later use.")

    print("Top 10 slowest tests:")
    files.sort(key=lambda item: item["time"], reverse=True)
    for item in files[:10]:
        print(f"{item['file']}: {item['time']}")


@task(help={"version": "The version number or the rule to update the version."})
def version(context, version=None):  # pylint: disable=redefined-outer-name
    """
    Show the version of Nautobot Python and NPM packages or bump them when a valid bump rule is
    provided.

    The version number or rules are those supported by `poetry version`.
    """
    if version is None:
        version = ""

    _run(context, f"poetry version --short {version}")
    _run(context, f"npm --prefix nautobot/ui version {version}")


# Must be at the end of the module to include all tasks
namespace = Collection.from_module(sys.modules[__name__], name="nautobot")
namespace.configure(
    {
        "nautobot": _INVOKE_PROJECT_DEFAULTS,
        "docker": _INVOKE_DOCKER_DEFAULTS,
        "run": _INVOKE_RUN_DEFAULTS,
    }
)
