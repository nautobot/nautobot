"""Tasks for use with Invoke.

(c) 2020 Network To Code
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
COMPOSE_COMMAND = f"docker-compose --project-directory \"{COMPOSE_DIR}\" -f \"{COMPOSE_FILE}\""

if os.path.isfile(COMPOSE_OVERRIDE_FILE):
    COMPOSE_COMMAND += f' -f "{COMPOSE_OVERRIDE_FILE}"'

GRIMLOCK_ROOT = "/opt/grimlock/"
MANAGE_COMMAND = os.path.join(GRIMLOCK_ROOT, "netbox/manage.py")

ENV_VARS = {
    "PYTHON_VER": PYTHON_VER,
}


# ------------------------------------------------------------------------------
# BUILD
# ------------------------------------------------------------------------------
@task
def build(context, python_ver=PYTHON_VER):
    """Build all docker images.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Building Grimlock .. ")

    context.run(
        f"{COMPOSE_COMMAND} build"
        f" --build-arg python_ver={python_ver}",
        env={"PYTHON_VER": python_ver},
    )


# ------------------------------------------------------------------------------
# START / STOP / DEBUG
# ------------------------------------------------------------------------------
@task
def debug(context, python_ver=PYTHON_VER):
    """Start NetBox and its dependencies in debug mode.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Starting NetBox in debug mode.. ")

    context.run(
        f"{COMPOSE_COMMAND} up",
        env={"PYTHON_VER": python_ver},
    )


@task
def start(context, python_ver=PYTHON_VER):
    """Start NetBox and its dependencies in detached mode.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Starting Netbox in detached mode .. ")

    context.run(
        f"{COMPOSE_COMMAND} up -d",
        env={"PYTHON_VER": python_ver},
    )


@task
def stop(context, python_ver=PYTHON_VER):
    """Stop NetBox and its dependencies.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Stopping Netbox .. ")

    context.run(
        f"{COMPOSE_COMMAND} stop",
        env={"PYTHON_VER": python_ver},
    )


@task
def destroy(context, python_ver=PYTHON_VER):
    """Destroy all containers and volumes.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    print("Destroying Netbox .. ")

    # Removes volumes associated with the COMPOSE_PROJECT_NAME
    context.run(
        f"{COMPOSE_COMMAND} down --volumes",
        env={"PYTHON_VER": python_ver},
    )


@task
def vscode(context):
    """Launch Visual Studio Code with the appropriate Environment variables to run in a container.

    Args:
        context (obj): Used to run specific commands
    """
    context.run("code grimlock.code-workspace", env=ENV_VARS)


# ------------------------------------------------------------------------------
# ACTIONS
# ------------------------------------------------------------------------------
@task
def nbshell(context, python_ver=PYTHON_VER):
    """Launch a nbshell session.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"{COMPOSE_COMMAND} exec netbox python {MANAGE_COMMAND} nbshell",
        env={"PYTHON_VER": python_ver},
        pty=True,
    )


@task
def cli(context, python_ver=PYTHON_VER):
    """Launch a bash shell inside the running NetBox container.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"{COMPOSE_COMMAND} exec netbox bash",
        env={"PYTHON_VER": python_ver},
        pty=True,
    )


@task
def createsuperuser(context, user="admin", python_ver=PYTHON_VER):
    """Create a new superuser in django (default: admin), will prompt for password.

    Args:
        context (obj): Used to run specific commands
        user (str): name of the superuser to create
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"{COMPOSE_COMMAND} run netbox python {MANAGE_COMMAND} createsuperuser --username {user}",
        env={"PYTHON_VER": python_ver},
        pty=True,
    )


@task
def makemigrations(context, name="", python_ver=PYTHON_VER):
    """Run Make Migration in Django.

    Args:
        context (obj): Used to run specific commands
        name (str): Name of the migration to be created
        python_ver (str): Will use the Python version docker image to build from
    """
    if name:
        context.run(
            f"{COMPOSE_COMMAND} run netbox python {MANAGE_COMMAND} makemigrations --name {name}",
            env={"PYTHON_VER": python_ver},
        )
    else:
        context.run(
            f"{COMPOSE_COMMAND} run netbox python {MANAGE_COMMAND} makemigrations",
            env={"PYTHON_VER": python_ver},
        )


@task
def migrate(context, python_ver=PYTHON_VER):
    """Perform migrate operation in Django.

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"{COMPOSE_COMMAND} run netbox python {MANAGE_COMMAND} migrate",
        env={"PYTHON_VER": python_ver},
    )


# ------------------------------------------------------------------------------
# TESTS
# ------------------------------------------------------------------------------
@task
def pycodestyle(context, python_ver=PYTHON_VER):
    """Check PEP8 compliance

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"{COMPOSE_COMMAND} run netbox"
        " pycodestyle --ignore=W504,E501 --exclude=netbox/scripts,netbox/reports,netbox/jobs,netbox/git"
        " contrib/ development/ netbox/ tasks.py\"",
        env={"PYTHON_VER": python_ver},
        pty=True,
    )


@task
def coverage_run(context, dir="netbox/", python_ver=PYTHON_VER):
    """Run tests

    Args:
        context (obj): Used to run specific commands
        dir (str): Used to indicate tested directory
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"{COMPOSE_COMMAND} run netbox"
        f" coverage run --source='netbox/' netbox/manage.py test {dir}",
        env={"PYTHON_VER": python_ver},
        pty=True,
    )


@task
def coverage_report(context, python_ver=PYTHON_VER):
    """Run coverage report

    Args:
        context (obj): Used to run specific commands
        python_ver (str): Will use the Python version docker image to build from
    """
    context.run(
        f"{COMPOSE_COMMAND} run netbox"
        f" coverage report --skip-covered --omit *migrations*",
        env={"PYTHON_VER": python_ver},
        pty=True,
    )
