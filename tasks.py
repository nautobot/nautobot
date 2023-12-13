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
import re

from invoke import Collection, task as invoke_task
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


# Base directory path from this file.
BASE_DIR = os.path.join(os.path.dirname(__file__))

# Base directory path for Nautobot UI.
NAUTOBOT_UI_DIR = os.path.join(BASE_DIR, "nautobot/ui")


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


# Use pyinvoke configuration for default values, see http://docs.pyinvoke.org/en/stable/concepts/configuration.html
# Variables may be overwritten in invoke.yml or by the environment variables INVOKE_NAUTOBOT_xxx
namespace = Collection("nautobot")
namespace.configure(
    {
        "nautobot": {
            "project_name": "nautobot",
            "python_ver": "3.8",
            "local": False,
            "compose_dir": os.path.join(BASE_DIR, "development/"),
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
    """Helper function for running a specific docker compose command with all appropriate parameters and environment.

    Args:
        context (obj): Used to run specific commands
        command (str): Command string to append to the "docker compose ..." command, such as "build", "up", etc.
        **kwargs: Passed through to the context.run() call.
    """
    compose_command_tokens = [
        "docker compose",
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

    print(f'Running docker compose command "{command}"')
    compose_command = " ".join(compose_command_tokens)
    env = kwargs.pop("env", {})
    env.update({"PYTHON_VER": context.nautobot.python_ver})
    if "hide" not in kwargs:
        print_command(compose_command, env=env)
    return context.run(compose_command, env=env, **kwargs)


def run_command(context, command, service="nautobot", **kwargs):
    """Wrapper to run a command locally or inside the provided container."""
    if is_truthy(context.nautobot.local):
        env = kwargs.pop("env", {})
        if "hide" not in kwargs:
            print_command(command, env=env)
        context.run(command, pty=True, env=env, **kwargs)
    else:
        # Check if Nautobot is running; no need to start another Nautobot container to run a command
        docker_compose_status = "ps --services --filter status=running"
        results = docker_compose(context, docker_compose_status, hide="out")

        root = kwargs.pop("root", False)
        if service in results.stdout:
            compose_command = f"exec {'--user=root ' if root else ''}{service} {command}"
        else:
            compose_command = f"run {'--user=root ' if root else ''}--rm --entrypoint '{command}' {service}"

        docker_compose(context, compose_command, pty=True)


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task(
    help={
        "force_rm": "Always remove intermediate containers.",
        "cache": "Whether to use Docker's cache when building the image. (Default: enabled)",
        "poetry_parallel": "Enable/disable poetry to install packages in parallel. (Default: True)",
        "pull": "Whether to pull Docker images when building the image. (Default: disabled)",
        "service": "If specified, only build this service.",
    }
)
def build(context, force_rm=False, cache=True, poetry_parallel=True, pull=False, service=None):
    """Build Nautobot docker image."""
    command = f"build --build-arg PYTHON_VER={context.nautobot.python_ver}"

    if not cache:
        command += " --no-cache"
    if force_rm:
        command += " --force-rm"
    if poetry_parallel:
        command += " --build-arg POETRY_INSTALLER_PARALLEL=true"
    if pull:
        command += " --pull"

    print(f"Building Nautobot with Python {context.nautobot.python_ver}...")

    docker_compose(context, command, service=service, env={"DOCKER_BUILDKIT": "1", "COMPOSE_DOCKER_CLI_BUILD": "1"})


@task(
    help={
        "poetry_parallel": "Enable/disable poetry to install packages in parallel. (Default: True)",
    }
)
def build_dependencies(context, poetry_parallel=True):
    # Determine preferred/default target architecture
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
        command_tokens.append("--build-arg POETRY_INSTALLER_PARALLEL=true")

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
        docker_compose(context, "down")
    else:
        docker_compose(context, "stop", service=service)


@task
def destroy(context):
    """Destroy all containers and volumes."""
    print("Destroying Nautobot...")
    docker_compose(context, "down --volumes")


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
    """Launch an interactive Nautobot shell."""
    command = "nautobot-server nbshell"

    run_command(context, command, pty=True)


@task(
    help={
        "service": "Name of the service to shell into",
        "root": "Launch shell as root",
    }
)
def cli(context, service="nautobot", root=False):
    """Launch a bash shell inside the running Nautobot (or other) Docker container."""
    context.nautobot.local = False
    command = "bash"

    run_command(context, command, service=service, pty=True, root=root)


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
        docker_command = f"run --workdir='/source/examples/example_plugin' --entrypoint '{command}' nautobot"
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
def ruff(context, output_format="text"):
    """Run ruff to perform static analysis and linting."""
    command = f"ruff --output-format {output_format} development/ examples/ nautobot/ tasks.py"
    run_command(context, command)


@task
def yamllint(context):
    """Run yamllint to validate formatting applies to YAML standards."""
    # TODO: enable for directories other than nautobot/docs and fix all warnings
    command = "yamllint nautobot/docs --format standard"
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
    if is_truthy(context.nautobot.local):
        command = (
            "cd nautobot/ui && npx -- markdownlint-cli "
            "--ignore ../../nautobot/project-static --ignore ../../nautobot/ui/node_modules "
            "--config ../../.markdownlint.yml --rules ../../scripts/use-relative-md-links.js "
            "../../nautobot ../../examples ../../*.md"
        )
        run_command(context, command)
    else:
        command = (
            "npx -- markdownlint-cli "
            "--ignore /source/nautobot/project-static --ignore /source/nautobot/ui/node_modules "
            "--config /source/.markdownlint.yml --rules /source/scripts/use-relative-md-links.js "
            "/source/nautobot /source/examples /source/*.md"
        )
        docker_command = f"run --workdir='/opt/nautobot/ui' --entrypoint '{command}' nautobot"
        docker_compose(context, docker_command, pty=True)


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
        current_major, current_minor = [int(v) for v in nautobot_version.split(".")[:2]]
        assert current_major == 2, f"check_schemas version calc must be updated to handle version {current_major}"
        api_versions = [f"{current_major}.{minor}" for minor in range(0, current_minor + 1)]

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
    },
    iterable=["tag", "exclude_tag"],
)
def unittest(
    context,
    cache_test_fixtures=False,
    keepdb=False,
    label="nautobot",
    failfast=False,
    buffer=True,
    exclude_tag=None,
    tag=None,
    verbose=False,
    append=False,
    skip_docs_build=False,
    performance_report=False,
    performance_snapshot=False,
):
    """Run Nautobot unit tests."""
    if not skip_docs_build:
        # First build the docs so they are available.
        build_and_check_docs(context)

    append_arg = " --append" if append else ""
    command = f"coverage run{append_arg} --module nautobot.core.cli test {label}"
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

    run_command(context, command)


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
    iterable=["tag", "exclude_tag"],
)
def integration_test(
    context,
    cache_test_fixtures=False,
    keepdb=False,
    label="nautobot",
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
        "dataset": "File (.sql.tar.gz) to start from that will untar to 'nautobot.sql'",
        "db_engine": "mysql or postgres",
        "db_name": "Temporary database to create, test, and destroy",
    },
)
def migration_test(context, dataset, db_engine="postgres", db_name="nautobot_migration_test"):
    """Test database migration from a given dataset to latest Nautobot schema."""
    if is_truthy(context.nautobot.local):
        run_command(context, command=f"tar zxvf {dataset}")
    else:
        # DB must be running, else will fail with errors like:
        # dropdb: error: could not connect to database template1: could not connect to server: No such file or directory
        start(context, service="db")
        source_file = os.path.basename(dataset)
        context.run(f"docker cp '{dataset}' nautobot-db-1:/tmp/{source_file}")
        run_command(context, command=f"tar zxvf /tmp/{source_file}", service="db")

    if db_engine == "postgres":
        common_args = "-U $NAUTOBOT_DB_USER --no-password -h localhost"
        run_command(context, command=f"sh -c 'dropdb --if-exists {common_args} {db_name}'", service="db")
        run_command(context, command=f"sh -c 'createdb {common_args} {db_name}'", service="db")
        run_command(context, command=f"sh -c 'psql {common_args} -d {db_name} -f nautobot.sql'", service="db")
    else:
        # "weird historical idiosyncrasy in MySQL where 'localhost' means a UNIX socket, and '127.0.0.1' means TCP/IP"
        base_command = "mysql --user=$NAUTOBOT_DB_USER --password=$NAUTOBOT_DB_PASSWORD --host 127.0.0.1"
        run_command(context, command=f"sh -c '{base_command} -e \"DROP DATABASE IF EXISTS {db_name};\"'", service="db")
        run_command(context, command=f"sh -c '{base_command} -e \"CREATE DATABASE {db_name};\"'", service="db")
        run_command(context, command=f"sh -c '{base_command} {db_name} < nautobot.sql'", service="db")

    if is_truthy(context.nautobot.local):
        run_command(context, command="nautobot-server migrate", env={"NAUTOBOT_DB_NAME": db_name})
    else:
        # We MUST use "docker-compose run ..." here as "docker-compose exec" doesn't support an `--env` flag.
        docker_compose(
            context,
            command=f"run --rm --env NAUTOBOT_DB_NAME={db_name} --entrypoint 'nautobot-server migrate' nautobot",
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
    iterable=["tag", "exclude_tag"],
)
def performance_test(
    context,
    cache_test_fixtures=False,
    keepdb=False,
    label="nautobot",
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
    run_command(context, command, service="nodejs")


@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect.",
    }
)
def prettier(context, autoformat=False):
    """Check Node.JS code style with Prettier."""
    prettier_command = "npx prettier"

    if autoformat:
        arg = "--write"
    else:
        arg = "--check"

    if is_truthy(context.nautobot.local):
        run_command(context, f"cd nautobot/ui && {prettier_command} {arg} .")
    else:
        docker_compose(
            context,
            f"run --workdir='/opt/nautobot/ui' --entrypoint '{prettier_command} {arg} /source/nautobot/ui' nautobot",
        )


@task(
    help={
        "autoformat": "Apply some recommendations automatically, rather than failing if formatting is incorrect. Not all issues can be fixed automatically.",
    }
)
def eslint(context, autoformat=False):
    """Check for ESLint rule compliance and other style issues."""
    eslint_command = "npx eslint --max-warnings 0"

    if autoformat:
        eslint_command += " --fix"

    if is_truthy(context.nautobot.local):
        # babel-preset-react-app / eslint requires setting environment variable for either
        # `NODE_ENV` or `BABEL_ENV` to 'test'|'development'|'production'
        run_command(context, f"cd nautobot/ui && NODE_ENV=test {eslint_command} .")
    else:
        # TODO: we should really run against /source/nautobot/ui, not /opt/nautobot/ui, but eslint aborts if we do:
        #   ESLint couldn't find the config "@react-app" to extend from.
        #   Please check that the name of the config is correct.
        # Probably this is because we don't install node_modules under /source/nautobot/ui normally...?
        #
        # babel-preset-react-app / eslint requires setting environment variable for either
        # `NODE_ENV` or `BABEL_ENV` to 'test'|'development'|'production'
        docker_compose(
            context,
            "run --workdir='/opt/nautobot/ui' -e NODE_ENV=test "
            f"--entrypoint '{eslint_command} /opt/nautobot/ui' nodejs",
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
    prettier(context)
    eslint(context)
    hadolint(context)
    markdownlint(context)
    yamllint(context)
    ruff(context)
    pylint(context)
    check_migrations(context)
    check_schema(context)
    build_and_check_docs(context)
    if not lint_only:
        unittest(context, keepdb=keepdb)


@task(help={"version": "The version number or the rule to update the version."})
def version(context, version=None):  # pylint: disable=redefined-outer-name
    """
    Show the version of Nautobot Python and NPM packages or bump them when a valid bump rule is
    provided.

    The version number or rules are those supported by `poetry version`.
    """
    if version is None:
        version = ""

    run_command(context, f"poetry version --short {version}")
    run_command(context, f"npm --prefix nautobot/ui version {version}")
