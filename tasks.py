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

import sys
import toml
import os
from invoke import task
from invoke.exceptions import Exit
from time import sleep
import requests


DEFAULT_PYTHON_VERSION = "3.6"
PYTHON_VER = os.getenv("PYTHON_VER", DEFAULT_PYTHON_VERSION)

PROJECT_NAME = "nautobot_dev"
COMPOSE_DIR = os.path.join(os.path.dirname(__file__), "development/")
COMPOSE_FILE = os.path.join(COMPOSE_DIR, "docker-compose.yml")
OVERRIDE_FILENAME = os.getenv("OVERRIDE_FILENAME", "docker-compose.dev.yml")
COMPOSE_OVERRIDE_FILE = os.path.join(COMPOSE_DIR, OVERRIDE_FILENAME)
COMPOSE_COMMAND = (
    f'docker-compose --project-name {PROJECT_NAME} --project-directory "{COMPOSE_DIR}" -f "{COMPOSE_FILE}"'
)

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


@task(
    help={
        "cache": "Whether to use Docker's cache when building the image (defaults to enabled)",
        "cache_dir": "The directory to use for caching buildx output (defaults to /home/travis/.cache/docker for Travis)",
        "platforms": "Comma separated list of strings for which to build (defaults to linux/amd64)",
        "tag": "tags should be applied to the built image (defaults to networktocode/nautobot-dev:local)",
        "target": "the target from the dockerfile to build (defaults to dev)",
    }
)
def buildx(
    context,
    cache=True,
    cache_dir="/home/travis/.cache/docker",
    platforms="linux/amd64",
    tag=f"networktocode/nautobot-dev-py{PYTHON_VER}:local",
    target="dev",
):
    """Build Nautobot docker image."""
    print("Building Nautobot .. ")
    command = f"docker buildx build --platform {platforms} -t {tag} --target {target} --load -f ./docker/Dockerfile --build-arg PYTHON_VER={PYTHON_VER} ."
    if not cache:
        command += " --no-cache"
    else:
        command += (
            f" --cache-to type=local,dest={cache_dir}/{PYTHON_VER} --cache-from type=local,src={cache_dir}/{PYTHON_VER}"
        )

    context.run(command, env={"PYTHON_VER": PYTHON_VER})


@task(
    help={
        "branch": "Which branch we are pushing from",
        "commit": "The commit hash to tag the develop image with",
        "datestamp": "The datestamp to tag the develop image with",
    }
)
def push(context, branch, commit="", datestamp=""):
    """Tags and pushes docker images to the appropriate repos, intended for CI use only."""
    with open("pyproject.toml", "r") as pyproject:
        parsed_toml = toml.load(pyproject)

    nautobot_version = parsed_toml["tool"]["poetry"]["version"]
    docker_image_names = ["networktocode/nautobot", "ghcr.io/nautobot/nautobot"]
    docker_image_tags_main = [f"latest-py{PYTHON_VER}", f"v{nautobot_version}-py{PYTHON_VER}"]
    docker_image_tags_develop = [f"develop-latest-py{PYTHON_VER}", f"develop-py{PYTHON_VER}-{commit}-{datestamp}"]

    if PYTHON_VER == DEFAULT_PYTHON_VERSION:
        docker_image_tags_main += ["latest", f"v{nautobot_version}"]
        docker_image_tags_develop += ["develop-latest", f"develop-{commit}-{datestamp}"]
    if branch == "main":
        docker_image_tags = docker_image_tags_main
    elif branch == "develop":
        docker_image_tags = docker_image_tags_develop
    else:
        raise Exit(f"Unknown Branch ({branch}) Specified", 1)

    for image_name in docker_image_names:
        for image_tag in docker_image_tags:
            new_image = f"{image_name}:{image_tag}"
            tag_command = f"docker tag networktocode/nautobot-py{PYTHON_VER}:local {new_image}"
            push_command = f"docker push {new_image}"
            print(f"Tagging networktocode/nautobot-py{PYTHON_VER}:local as {new_image}")
            context.run(tag_command)
            print(f"Pushing {new_image}")
            context.run(push_command)


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


@task(help={"user": "name of the superuser to create"})
def createsuperuser(context, user="admin"):
    """Create a new Nautobot superuser account (default: "admin"), will prompt for password."""
    docker_compose(context, "run nautobot nautobot-server createsuperuser --username {user}", pty=True)


@task(help={"name": "name of the migration to be created; if unspecified, will autogenerate a name"})
def makemigrations(context, name=""):
    """Perform makemigrations operation in Django."""
    command = "run nautobot nautobot-server makemigrations"
    if name:
        command += f" --name {name}"
    docker_compose(context, command)


@task
def migrate(context):
    """Perform migrate operation in Django."""
    docker_compose(context, "run nautobot nautobot-server migrate")


@task
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
    docker_compose(context, "run nautobot nautobot-server post_upgrade")


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task(
    help={
        "autoformat": "Apply formatting recommendations automatically, rather than failing if formatting is incorrect."
    }
)
def black(context, autoformat=False, local=False):
    """Check Python code style with Black."""
    if autoformat:
        black_command = "black"
    else:
        black_command = "black --check --diff"
    command = f"{black_command} development/ nautobot/ tasks.py"
    if local:
        context.run(command)
    else:
        docker_compose(
            context,
            f"run --entrypoint '{command}' nautobot",
            pty=True,
        )


@task
def flake8(context, local=False):
    """Check for PEP8 compliance and other style issues."""
    command = "flake8 development/ nautobot/ tasks.py"
    if local:
        context.run(command)
    else:
        docker_compose(context, f"run --entrypoint '{command}' nautobot", pty=True)


@task
def hadolint(context, local=False):
    """Check Dockerfile for hadolint compliance and other style issues."""
    command = "hadolint docker/Dockerfile"
    if local:
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
    command = f"run --entrypoint 'coverage run -m nautobot.core.cli test {label} --failfast"
    if keepdb:
        command += " --keepdb"
    command += "' nautobot"
    docker_compose(context, command, pty=True)


@task
def unittest_coverage(context):
    """Report on code test coverage as measured by 'invoke unittest'."""
    docker_compose(context, "run --entrypoint 'coverage report --skip-covered --omit *migrations*' nautobot", pty=True)


@task
def integration_tests(context):
    """Some very generic high level integration tests."""
    session = requests.Session()
    retries = 1
    max_retries = 60

    start(context)
    while retries < max_retries:
        try:
            request = session.get("http://localhost:8080", timeout=300)
        except requests.exceptions.ConnectionError:
            print("Nautobot not ready yet sleeping for 5 seconds...")
            sleep(5)
            retries += 1
            continue
        if request.status_code == 200:
            print("Nautobot is ready...")
            break
        else:
            raise Exit(f"Nautobot returned and invalid status {request.status_code}", request.status_code)
    if retries >= max_retries:
        raise Exit("Timed Out waiting for Nautobot", 1)


@task
def tests(context):
    """Run all tests and linters."""
    black(context)
    flake8(context)
    hadolint(context)
    unittest(context)
