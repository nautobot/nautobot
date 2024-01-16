# Docker Compose Advanced Use Cases

This section describes some of the more advanced use cases for the [Docker Compose development workflow](getting-started.md#docker-compose-workflow).

## Invoke Configuration

The Invoke tasks have some default [configuration](http://docs.pyinvoke.org/en/stable/concepts/configuration.html) which you may want to override. Configuration properties include:

- `project_name`: The name that all Docker containers will be grouped together under (default: `nautobot`, resulting in containers named `nautobot_nautobot_1`, `nautobot_redis_1`, etc.)
- `python_ver`: the Python version which is used to build the Docker container (default: `3.8`)
- `local`: run the commands in the local environment vs the Docker container (default: `False`)
- `compose_dir`: the full path to the directory containing the Docker Compose YAML files (default: `"<nautobot source directory>/development"`)
- `compose_files`: the Docker Compose YAML file(s) to use (default: `["docker-compose.yml", "docker-compose.postgres.yml", "docker-compose.dev.yml"]`)
- `docker_image_names_main` and `docker_image_names_develop`: Used when [building Docker images for publication](release-checklist.md#publish-docker-images); you shouldn't generally need to change these.

These setting may be overridden several different ways (from highest to lowest precedence):

- Command line argument on the individual commands (see `invoke $command --help`) if available
- Using environment variables such as `INVOKE_NAUTOBOT_PYTHON_VER`; the variables are prefixed with `INVOKE_NAUTOBOT_` and must be uppercase; note that Invoke does not presently support environment variable overriding of list properties such as `compose_files`.
- Using an `invoke.yml` file (see [`invoke.yml.example`](https://github.com/nautobot/nautobot/blob/main/invoke.yml.example))

## Working with Docker Compose

The files related to the Docker development environment can be found inside of the `development` directory at the root of the project.

In this directory you'll find the following core files:

- `docker-compose.yml` - Docker service containers and their relationships to the Nautobot container
- `docker-compose.debug.yml` - Docker compose override file used to start the Nautobot container for use with [Visual Studio Code's dev container integration](#microsoft-visual-studio-code-integration).
- `docker-compose.dev.yml` - Docker compose override file used to mount the Nautobot source code inside the container at `/source` and the `nautobot_config.py` from the same directory as `/opt/nautobot/nautobot_config.py` for the active configuration.
- `docker-compose.final.yml` - Docker compose override file used to start/build the `final` (production) Docker images for local testing.
- `docker-compose.final-dev.yml` - Docker compose override file used to start/build the `final-dev` (app development environment) Docker images for local testing.
- `docker-compose.keycloak.yml` - Docker compose override file used to setup an SSO auth backend for Nautobot.
- `docker-compose.mysql.yml` - Docker compose override file used to add a MySQL container as the database backend for Nautobot.
- `docker-compose.postgres.yml` - Docker compose override file used to add a Postgres container as the database backend for Nautobot.
- `dev.env` - Environment variables used to setup the container services
- `nautobot_config.py` - Nautobot configuration file

In addition to the `development` directory, additional non-development-specific Docker-related files are located in the `docker` directory at the root of the project.

In the `docker` directory you will find the following files:

- `Dockerfile` - Docker container definition for Nautobot containers
- `docker-entrypoint.sh` - Commands and operations ran once Nautobot container is started including database migrations and optionally creating a superuser
- `uwsgi.ini` - The [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) ini file used in the production docker container

## Docker Compose Overrides

If you require changing any of the defaults found in `docker-compose.yml`, create a file inside the `development` directory called `docker-compose.override.yml` and add this file to the `compose_files` setting in your `invoke.yml` file, for example:

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.postgres.yml"
    - "docker-compose.dev.yml"
    - "docker-compose.override.yml"
```

This file will override any configuration in the main `docker-compose.yml` file, without making changes to the repository.

Please see the [official documentation on extending Docker Compose](https://docs.docker.com/compose/extends/) for more information.

### Override Environment Variables

A common use case is for developers to override the default environment variables in the development containers. This can be accomplished with the `env_file` property. Create `invoke.yml` as described above, then create `development/docker-compose.override.yml` with the following contents:

```yaml
---
services:
  nautobot:
    env_file:
      - "override.env"
```

Environment variables can be added to `development/override.env` using the [env file syntax](https://docs.docker.com/compose/environment-variables/env-file/):

```bash
NAUTOBOT_SUPERUSER_PASSWORD=changeme
NAUTOBOT_SUPERUSER_API_TOKEN=1111111111111111111111111111111111111111
```

This file can be used to add new environment variables or override default environment variables found in `development/dev.env` but it cannot override any environment variables defined in any docker compose yml files.

### Automatically Creating a Superuser

+/- 2.1.2

The Nautobot docker compose development environment automatically bootstraps the database with a default superuser with a static password and API token. This is performed by the `docker-entrypoint.sh` script. The `docker-entrypoint.sh` script is copied in during the Docker image build and will read from the default `dev.env` as the `env_file` until you override it as seen above.

The following environment variables can be used to disable or modify this behavior:

```bash
NAUTOBOT_CREATE_SUPERUSER=true
NAUTOBOT_SUPERUSER_NAME=admin
NAUTOBOT_SUPERUSER_EMAIL=admin@example.com
NAUTOBOT_SUPERUSER_PASSWORD=admin
NAUTOBOT_SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
```

### Using MySQL instead of PostgreSQL

By default the Docker development environment is configured to use a PostgreSQL container as the database backend. For development or testing purposes, you might optionally choose to use MySQL instead. In order to do so, you need to make the following changes to your environment:

- Set up `invoke.yml` as described above and use it to override the postgres docker compose file:

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.mysql.yml"
    - "docker-compose.dev.yml"
```

Then `invoke stop` (if you previously had the docker environment running with Postgres) and `invoke start` and you should now be running with MySQL.

### SSO Auth Backend with Keycloak

Keycloak and its database are run in the same docker compose project as Nautobot. A separate database is used to ensure you are able to have two separate instances of Postgres, one for Nautobot and one for Keycloak, and allows you to use a MySQL database for Nautobot but maintain Keycloaks required Postgres DB. This setup is meant for local development and testing, and should not be used as a reference for deploying Keycloak in production.

The `invoke.yml` file must be updated to add `development/docker-compose.keycloak.yml` to the docker compose project and to enable OIDC. These setting are solely for local development inside the Nautobot repository and is not applicable to any other deployment. An example `invoke.yml` file:

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.postgres.yml"
    - "docker-compose.dev.yml"
    - "docker-compose.keycloak.yml"
```

#### Validating Setup

Once all steps are completed Nautobot should now have the `Continue to SSO` button on the login screen and should immediately redirect the user to sign in with Keycloak.

#### Keycloak Login Credentials

Keycloak admin console is reachable via `http://localhost:8087/admin/` with user `admin` and password `admin`. The below users are pre-configured within Keycloak, at this time their permissions are not directly mapped to any permissions provided by default by Nautobot. This will be a later enhancement to the local development environment.

| Username         | Password  |
+------------------+-----------+
| nautobot_unpriv  | unpriv123 |
| nautobot_admin   | admin123  |
| nautobot_auditor | audit123  |

## Microsoft Visual Studio Code Integration

For users of Microsoft Visual Studio Code, several files are included to ease development and integrate with the [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers). The following related files are found relative to the root of the project:

- `.devcontainer/devcontainer.json` - Configuration for the [`Dev Containers`](https://code.visualstudio.com/docs/devcontainers/containers) extension
- `nautobot.code-workspace` - VS Code workspace configuration for Nautobot
- `development/docker-compose.debug.yml` - Docker Compose file with debug configuration for VS Code

### Dev Containers Setup

+/- 2.1.2

#### ARM64 Build Argument

Due to a bug in Dev Containers, when using VS Code to build your docker containers, docker cannot automatically determine the CPU architecture. To work around this bug, we have set a default value of `amd64` (x86_64). If you're running on another architecture like Apple Silicon or Raspberry Pi you will need to override this setting.

!!! info
    If you're unsure what architecture you're using you can run `uname -m` in a terminal. If this command outputs `x86_64` you're on an `amd64` architecture. If it outputs `aarch64` or `arm64`, you're on `arm64`. These are the only supported CPU architectures for VS Code Dev Containers.

If running on an `arm64` architecture, create a `docker-compose.override.yml` file in the `development` directory with the following content:

```yml title="development/docker-compose.override.yml"
---
version: "3.9"
services:
  nautobot:
    build:
      args:
        ARCH: arm64
```

Then add this file to the list of docker compose files in `.devcontainer/devcontainer.json`:

```json title=".devcontainer/devcontainer.json"
{
    "name": "Nautobot Dev Container",
    "dockerComposeFile": [
        "../development/docker-compose.yml",
        "../development/docker-compose.postgres.yml",
        "../development/docker-compose.dev.yml",
        "../development/docker-compose.override.yml"
    ]
    ...
```

#### PYTHON_VER Environment Variable

The `PYTHON_VER` environment variable must be set in the `development/.env` file or the container build will fail. An example file exists and can be used as-is if you don't need to change the default version:

```bash
cp development/.env.example development/.env
```

### Using Dev Containers

To open VS Code in the development container, first open VS Code in your local copy of the Nautobot Git repository. Open the command palette (`Ctrl+Shift+P` or `Cmd+Shift+P`) and select **Reopen in Container** to build and start the development containers. Once your window is connected to the container, you can open the workspace file `nautobot.code-workspace` which enables support for Run/Debug.

To start Nautobot, select **Run Without Debugging** or **Start Debugging** from the Run menu. Once Nautobot has started, you will be prompted to open a browser to connect to Nautobot.

!!! note
    You can run tests with `nautobot-server --config=nautobot/core/tests/nautobot_config.py test nautobot` while inside the Container.

### Special Workflow for Containers on Remote Servers

A slightly different workflow is needed when your development container is running on a remotely-connected server (such as with SSH). VS Code will not offer the **Reopen in Container** option on a remote server.

To work with remote containers, after `invoke build` use `docker-compose` as follows to start the containers. This prevents the HTTP service from automatically starting inside the container:

```no-highlight
cd development
docker compose -f docker-compose.yml -f docker-compose.debug.yml up
```

- Now open the VS Code Docker extension. In the `CONTAINERS/development` section, right click on a running container and select the **Attach Visual Studio Code** menu item.
- The **Select the container to attach VS Code** input field provides a list of running containers.
- Click on `development_nautobot_1` to use VS Code inside the container. The `devcontainer` will startup now.
- As a last step open the folder `/opt/nautobot` in VS Code.

### Remote Debugging Configuration

Using the Remote-Attach functionality of VS Code debugger is an alternative to debugging in a development container. This allows a local VS Code instance to connect to a remote container and debug the code running in the container the same way as when debugging locally.

Follow the steps below to configure VS Code to debug Nautobot and Celery Worker running in a remote container:

1. **Configure `invoke.yml` to use the `docker-compose.vscode-rdb.yml` file**

    This overrides the container settings without touching the original `docker-compose.yml` file.

    Your `invoke.yml` file should look something like this:

    ```yaml
    ---
    nautobot:
      compose_files:
        - "docker-compose.yml"
        - "docker-compose.postgres.yml"
        - "docker-compose.dev.yml"
        - "docker-compose.vscode-rdb.yml"
    ```

    If you already have a custom `invoke.yml` file, append `docker-compose.vscode-rdb.yml` to the end of the `compose_files` list.

    See the [docker compose override](#docker-compose-overrides) documentation for more details.

2. **VS Code debug configuration**

    If you have opened the workspace file `nautobot.code-workspace` then there are two debug
    configurations for remote debugging already available.

    If you add nautobot to an existing VS Code workspace (Menu: _File > Add Folder to Workspace..._)
    then copy the `launch:` values to the `.vscode/launch.json` file.

    - Debug Configurations for Remote Debugging:

      ```json
      {
        "version": "0.2.0",
        "configurations": [
          {
            "name": "Python: Remote Attach",
            ...
          },
          {
            "name": "Python: Remote Attach Celery Worker",
            ...
          }
        ]
      }
      ```

It is now possible to debug the containerized Nautobot and Celery Worker using the VS Code debugger.

After restarting the Celery-Worker container you need to restart the debug session.
