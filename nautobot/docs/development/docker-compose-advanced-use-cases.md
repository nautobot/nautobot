# Docker Compose Advanced Use Cases

This section describes some of the more advanced use cases for the [Docker Compose development workflow](getting-started.md#docker-compose-workflow).

## Invoke Configuration

The Invoke tasks have some default [configuration](http://docs.pyinvoke.org/en/stable/concepts/configuration.html) which you may want to override. Configuration properties include:

- `project_name`: The name that all Docker containers will be grouped together under (default: `nautobot`, resulting in containers named `nautobot_nautobot_1`, `nautobot_redis_1`, etc.)
- `python_ver`: the Python version which is used to build the Docker container (default: `3.7`)
- `local`: run the commands in the local environment vs the Docker container (default: `False`)
- `compose_dir`: the full path to the directory containing the Docker Compose YAML files (default: `"<nautobot source directory>/development"`)
- `compose_files`: the Docker Compose YAML file(s) to use (default: `["docker-compose.yml", "docker-compose.dev.yml"]`)
- `docker_image_names_main` and `docker_image_names_develop`: Used when [building Docker images for publication](release-checklist.md#publish-docker-images); you shouldn't generally need to change these.

These setting may be overridden several different ways (from highest to lowest precedence):

- Command line argument on the individual commands (see `invoke $command --help`) if available
- Using environment variables such as `INVOKE_NAUTOBOT_PYTHON_VER`; the variables are prefixed with `INVOKE_NAUTOBOT_` and must be uppercase; note that Invoke does not presently support environment variable overriding of list properties such as `compose_files`.
- Using an `invoke.yml` file (see [`invoke.yml.example`](https://github.com/nautobot/nautobot/blob/main/invoke.yml.example))

## Working with Docker Compose

The files related to the Docker development environment can be found inside of the `development` directory at the root of the project.

In this directory you'll find the following core files:

- `docker-compose.yml` - Docker service containers and their relationships to the Nautobot container
- `docker-compose.build.yml` - Docker compose override file used to start/build the production docker images for local testing.
- `docker-compose.debug.yml` - Docker compose override file used to start the Nautobot container for use with [Visual Studio Code's dev container integration](#microsoft-visual-studio-code-integration).
- `docker-compose.dev.yml` - Docker compose override file used to mount the Nautobot source code inside the container at `/source` and the `nautobot_config.py` from the same directory as `/opt/nautobot/nautobot_config.py` for the active configuration.
- `dev.env` - Environment variables used to setup the container services
- `nautobot_config.py` - Nautobot configuration file

In addition to the `development` directory, additional non-development-specific Docker-related files are located in the `docker` directory at the root of the project.

In the `docker` directory you will find the following files:

- `Dockerfile` - Docker container definition for Nautobot containers
- `docker-entrypoint.sh` - Commands and operations ran once Nautobot container is started including database migrations and optionally creating a superuser
- `uwsgi.ini` - The [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) ini file used in the production docker container

## Docker-Compose Overrides

If you require changing any of the defaults found in `docker-compose.yml`,  create a file inside the `development` directory called `docker-compose.override.yml` and add this file to the `compose_files` setting in your `invoke.yml` file, for example:


```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.dev.yml"
    - "docker-compose.override.yml"
```

This file will override any configuration in the main `docker-compose.yml` file, without making changes to the repository.

Please see the [official documentation on extending Docker Compose](https://docs.docker.com/compose/extends/) for more information.

### Automatically Creating a Superuser

There may be times where you want to bootstrap Nautobot with a superuser account and API token already created for quick access or for running within a CI/CD pipeline. By using a custom `invoke.yml` as described above, in combination with custom `docker-compose.override.yml` and `override.env` files, you can automatically bootstrap Nautobot with a user and token.

Create `invoke.yml` as described above, then create `development/docker-compose.override.yml` with the following contents:

```yaml
---
services:
  nautobot:
    env_file:
      - "override.env"
```

The `docker-entrypoint.sh` script will run any migrations and then look for specific variables set to create the superuser. The `docker-entrypoint.sh` script is copied in during the Docker image build and will read from the default `dev.env` as the `env_file` until you override it as seen above.

 Any variables defined in this file will override the defaults. The `override.env` should look like the following:

```bash
# Superuser information. NAUTOBOT_CREATE_SUPERUSER defaults to false.
NAUTOBOT_CREATE_SUPERUSER=true
NAUTOBOT_SUPERUSER_NAME=admin
NAUTOBOT_SUPERUSER_EMAIL=admin@example.com
NAUTOBOT_SUPERUSER_PASSWORD=admin
NAUTOBOT_SUPERUSER_API_TOKEN=0123456789abcdef0123456789abcdef01234567
```

The variables defined above within `override.env` will signal the `docker-entrypoint.sh` script to create the superuser with the specified username, email, password, and API token.

After these two files are created, you can use the `invoke` tasks to manage the development containers.

## Microsoft Visual Studio Code Integration

For users of Microsoft Visual Studio Code, several files are included to ease development and integrate with the [VS Code Remote - Containers extension](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers). The following related files are found relative to the root of the project:

- `.devcontainers/devcontainer.json` - Dev. container definition
- `nautobot.code-workspace` - VS Code workspace configuration for Nautobot
- `development/docker-compose.debug.yml` - Docker Compose file with debug configuration for VS Code

After opening the project directory in VS Code in a supported environment, you will be prompted by VS Code to **Reopen in Container** and **Open Workspace**. Select **Reopen in Container** to build and start the development containers. Once your window is connected to the container, you can open the workspace which enables support for Run/Debug.

To start Nautobot, select **Run Without Debugging** or **Start Debugging** from the Run menu. Once Nautobot has started, you will be prompted to open a browser to connect to Nautobot.

!!! note
    You can run tests with `nautobot-server --config=nautobot/core/tests/nautobot_config.py test nautobot` while inside the Container.

### Special Workflow for Containers on Remote Servers

A slightly different workflow is needed when your development container is running on a remotely-connected server (such as with SSH). VS Code will not offer the **Reopen in Container** option on a remote server.

To work with remote containers, after `invoke build` use `docker-compose` as follows to start the containers. This prevents the HTTP service from automatically starting inside the container:

```no-highlight
$ cd development
$ docker-compose -f docker-compose.yml -f docker-compose.debug.yml up
```

- Now open the VS Code Docker extension. In the `CONTAINERS/development` section, right click on a running container and select the **Attach Visual Studio Code** menu item.
- The **Select the container to attach VS Code** input field provides a list of running containers.
- Click on `development_nautobot_1` to use VS Code inside the container. The `devcontainer` will startup now.
- As a last step open the folder `/opt/nautobot` in VS Code.
