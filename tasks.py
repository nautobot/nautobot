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

from contextlib import contextmanager
import os
from pathlib import Path
import re
import sys
from typing import Iterable
from typing import Mapping
from typing import Optional
from typing import Union

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

_DOCKER_NAUTOBOT_PATH = Path("/opt/nautobot")
_DOCKER_SOURCE_PATH = Path("/source")
_ROOT_PATH = Path(__file__).parent.absolute().resolve()

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
        ```shell
        # To launch customized Nautobot server, you can update your `.env` file and run:
        invoke cli -c='nautobot-server runserver 0.0.0.0:8080 --insecure' --docker-arg='--service-ports'
        ```
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
        pty=not (input_file or output_file),
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
        "pattern": "Specify a pattern to match test names against.",
    },
    iterable=["tag", "exclude_tag", "label", "pattern"],
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
    pattern=None,
):
    """Run Nautobot unit tests."""
    if not skip_docs_build:
        # First build the docs so they are available.
        build_and_check_docs(context)

    if not label:
        label = ["nautobot"]

    def get_command():
        yield "coverage run"

        if append:
            yield "--append"

        yield "--module nautobot.core.cli test"

        yield from label

        yield "--config=nautobot/core/tests/nautobot_config.py"

        if context.nautobot.get("cache_test_fixtures", False) or cache_test_fixtures:
            yield "--cache-test-fixtures"
        if keepdb:
            yield "--keepdb"
        if failfast:
            yield "--failfast"
        if buffer:
            yield "--buffer"
        if verbose:
            yield "--verbosity 2"
        if performance_report or performance_snapshot or (tag and "performance" in tag):
            yield "--testrunner nautobot.core.tests.runner.NautobotPerformanceTestRunner"
            yield "--slowreport"
            if performance_snapshot:
                yield "--slowreportpath report.yml"

        yield from (f"--tag='{item}'" for item in (tag or []))
        yield from (f"--exclude-tag='{item}'" for item in (exclude_tag or []))
        yield from (f"-k='{item}'" for item in (pattern or []))

    _run(context, get_command())


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
        "pattern": "Specify a pattern to match test names against.",
    },
    iterable=["tag", "exclude_tag", "label", "pattern"],
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
    pattern=None,
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
        pattern=pattern,
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
        "pattern": "Specify a pattern to match test names against.",
    },
    iterable=["tag", "exclude_tag", "label", "pattern"],
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
    pattern=None,
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
        pattern=pattern,
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
