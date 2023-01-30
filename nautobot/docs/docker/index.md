# Nautobot Docker Images

Nautobot is packaged as a Docker image for use in a production environment. The published image is based on the `python:3.7-slim` image to maintain the most compatibility with Nautobot deployments. The Docker image and deployment strategies are being actively developed, check back here or join the **#nautobot** channel on [Network to Code's Slack community](https://slack.networktocode.com/) for the most up to date information.

## Platforms

Nautobot docker images are currently provided for both `linux/amd64` and `linux/arm64` architectures. Please note ARM64 support is untested by our automated tests and should be considered in an alpha state.

## Tags

A set of Docker images are built for each Nautobot release and published to both [Docker Hub](https://hub.docker.com/r/networktocode/nautobot/) and the [GitHub Container Registry](https://github.com/nautobot/nautobot/pkgs/container/nautobot).

Additionally, GitHub Actions are used to automatically build images corresponding to each commit to the `develop` and `next` branches; these images are only published to the GitHub Container Registry.

To get a specific tagged image from Docker Hub or the GitHub Container Registry run:

```no-highlight
docker image pull networktocode/nautobot:${TAG}
```

or

```no-highlight
docker pull ghcr.io/nautobot/nautobot:${TAG}
```

The following tags are available on both Docker Hub and the GitHub Container Registry:

| Tag                                                           | Nautobot Version      | Python Version | Example        |
| ------------------------------------------------------------- | --------------------- | -------------- | -------------- |
| `${NAUTOBOT_VER}`                                             | As specified          | 3.7            | `1.2.7`        |
| `${NAUTOBOT_VER}-py${PYTHON_VER}`                             | As specified          | As specified   | `1.2.7-py3.8`  |
| `${NAUTOBOT_MAJOR_VER}.${NAUTOBOT_MINOR_VER}`                 | As specified          | 3.7            | `1.2`          |
| `${NAUTOBOT_MAJOR_VER}.${NAUTOBOT_MINOR_VER}-py${PYTHON_VER}` | As specified          | As specified   | `1.2-py3.8`    |
| `stable`                                                      | Latest stable release | 3.7            | `stable`       |
| `stable-py${PYTHON_VER}`                                      | Latest stable release | As specified   | `stable-py3.8` |

The following additional tags are only available from the GitHub Container Registry:

| Tag                                                  | Nautobot Branch              | Python Version |
| ---------------------------------------------------- | ---------------------------- | -------------- |
| `latest`                                             | `develop`, the latest commit | 3.7            |
| `latest-py${PYTHON_VER}`                             | `develop`, the latest commit | As specified   |
| `develop`                                            | `develop`, the latest commit | 3.7            |
| `develop-py${PYTHON_VER}`                            | `develop`, the latest commit | As specified   |
| `develop-${GIT_SHA:0:7}-$(date +%s)`                 | `develop`, a specific commit | 3.7            |
| `develop-${GIT_SHA:0:7}-$(date +%s)-py${PYTHON_VER}` | `develop`, a specific commit | As specified   |
| `next`                                               | `next`, the latest commit    | 3.7            |
| `next-py${PYTHON_VER}`                               | `next`, the latest commit    | As specified   |
| `next-${GIT_SHA:0:7}-$(date +%s)`                    | `next`, a specific commit    | 3.7            |
| `next-${GIT_SHA:0:7}-$(date +%s)-py${PYTHON_VER}`    | `next`, a specific commit    | As specified   |

Currently images are pushed for the following python versions:

* 3.7
* 3.8
* 3.9
* 3.10

!!! info
    Developer images `networktocode/nautobot-dev:${TAG}` and `ghcr.io/nautobot/nautobot-dev:${TAG}` are also provided with the same tags as above. These images provide the development dependencies needed to build Nautobot; they can be used as a base for development to develop your own Nautobot apps but should **NOT** be used in production.

## Getting Started

Nautobot requires a MySQL or PostgreSQL database and Redis instance before it will start. Because of this the quickest and easiest way to get Nautobot running is with `docker-compose`, which will install and configure PostgreSQL and Redis containers for you automatically.

## Configuration

Most configuration parameters are available via environment variables which can be passed to the container. If you desire you can inject your own `nautobot_config.py` by overriding `/opt/nautobot/nautobot_config.py` using [docker volumes](https://docs.docker.com/storage/volumes/) by adding `-v /local/path/to/custom/nautobot_config.py:/opt/nautobot/nautobot_config.py` to your docker run command, for example:

```no-highlight
docker run --name nautobot -v /local/path/to/custom/nautobot_config.py:/opt/nautobot/nautobot_config.py networktocode/nautobot
```

Or if you are using docker-compose:

```yaml
services:
  nautobot:
    image: "networktocode/nautobot"
    volumes:
      - /local/path/to/custom/nautobot_config.py:/opt/nautobot/nautobot_config.py:ro
```

### Docker only configuration

The entry point for the Docker container has some additional features that can be configured via additional environment variables. The following are all optional variables:

#### `NAUTOBOT_CREATE_SUPERUSER`

Default: unset

Enables creation of a super user specified by [`NAUTOBOT_SUPERUSER_NAME`](#nautobot_superuser_name), [`NAUTOBOT_SUPERUSER_EMAIL`](#nautobot_superuser_email), [`NAUTOBOT_SUPERUSER_PASSWORD`](#nautobot_superuser_password), and [`NAUTOBOT_SUPERUSER_API_TOKEN`](#nautobot_superuser_api_token).

---

#### `NAUTOBOT_DOCKER_SKIP_INIT`

Default: unset

When starting, the container attempts to connect to the database and run database migrations and upgrade steps necessary when upgrading versions. In normal operation this is harmless to run on every startup and validates the database is operating correctly. However, in certain circumstances such as database maintenance when the database is in a read-only mode it may make sense to start Nautobot but skip these steps. Setting this variable to `true` will start Nautobot without running these initial steps.

!!! note
    Setting this value to anything other than "false" (case-insensitive) will prevent migrations from occurring.

---

#### `NAUTOBOT_SUPERUSER_API_TOKEN`

Default: unset

If [`NAUTOBOT_CREATE_SUPERUSER`](#nautobot_create_superuser) is true, `NAUTOBOT_SUPERUSER_API_TOKEN` specifies the API token of the super user to be created; alternatively the `/run/secrets/superuser_api_token` file contents are read for the token. Either the variable or the file is required if `NAUTOBOT_CREATE_SUPERUSER` is true.

---

#### `NAUTOBOT_SUPERUSER_EMAIL`

Default: `admin@example.com`

If [`NAUTOBOT_CREATE_SUPERUSER`](#nautobot_create_superuser) is true, `NAUTOBOT_SUPERUSER_EMAIL` specifies the email address of the super user to be created.

---

#### `NAUTOBOT_SUPERUSER_NAME`

Default: `admin`

If [`NAUTOBOT_CREATE_SUPERUSER`](#nautobot_create_superuser) is true, `NAUTOBOT_SUPERUSER_NAME` specifies the username of the super user to be created.

---

#### `NAUTOBOT_SUPERUSER_PASSWORD`

Default: unset

If [`NAUTOBOT_CREATE_SUPERUSER`](#nautobot_create_superuser) is true, `NAUTOBOT_SUPERUSER_PASSWORD` specifies the password of the super user to be created; alternatively the `/run/secrets/superuser_password` file contents are read for the password. Either the variable or the file is required if `NAUTOBOT_CREATE_SUPERUSER` is true.

---

### uWSGI

The docker container uses [uWSGI](https://uwsgi-docs.readthedocs.io/) to serve Nautobot. A default configuration is [provided](https://github.com/nautobot/nautobot/blob/main/docker/uwsgi.ini), and can be overridden by injecting a new `uwsgi.ini` file at `/opt/nautobot/uwsgi.ini`. There are a couple of environment variables provided to override some uWSGI defaults:

#### `NAUTOBOT_UWSGI_BUFFER_SIZE`

+++ 1.3.9

Default: `4096`

Max: `65535`

The max size of non-body request payload, roughly the size of request headers for uWSGI. Request headers that might contain lengthy query parameters, for example GraphQL or Relationship filtered lookups, might go well over the default limit. Increasing this limit will have an impact on running memory usage. Please see [the uWSGI documentation](https://uwsgi-docs.readthedocs.io/en/latest/Options.html?highlight=buffer-size#buffer-size) for more information.

This can also be overridden by appending `-b DESIRED_BUFFER_SIZE`, ex: `-b 8192`, to the entry command in all Nautobot containers running uWSGI if you are on a release before `1.3.9`.

---

#### `NAUTOBOT_UWSGI_LISTEN`

Default: `128`

The socket listen queue size of uWSGI. In production environments it is recommended to increase this value to 1024 or higher, however depending on your platform, this may require additional kernel parameter settings, please see [the uWSGI documentation](https://uwsgi-docs.readthedocs.io/en/latest/articles/TheArtOfGracefulReloading.html#the-listen-queue) for more information.

Please see the [official uWSGI documentation on `listen`](https://uwsgi-docs.readthedocs.io/en/latest/Options.html?highlight=listen#listen) for more information.

---

#### `NAUTOBOT_UWSGI_PROCESSES`

Default: `3`

The number of worker processes uWSGI will spawn.

Please see the [official uWSGI documentation on `processes`](https://uwsgi-docs.readthedocs.io/en/latest/Options.html?highlight=processes#processes) for more information.

---

### SSL

Self signed SSL certificates are included by default with the container. For a production deployment you should utilize your own signed certificates, these can be injected into the container at runtime using [docker volumes](https://docs.docker.com/storage/volumes/). The public certificate should be placed at `/opt/nautobot/nautobot.crt` and the private key should be at `/opt/nautobot/nautobot.key`. Using a `docker run` these can be injected using the `-v` parameter:

```no-highlight
docker run --name nautobot -v /local/path/to/custom/nautobot.crt:/opt/nautobot/nautobot.crt -v /local/path/to/custom/nautobot.key:/opt/nautobot/nautobot.key networktocode/nautobot
```

Or if you are using `docker-compose`:

```yaml
services:
  nautobot:
    image: "networktocode/nautobot"
    volumes:
      - /local/path/to/custom/nautobot.crt:/opt/nautobot/nautobot.crt:ro
      - /local/path/to/custom/nautobot.key:/opt/nautobot/nautobot.key:ro
```

### Nautobot Plugins

At this time adding Nautobot plugins to the existing Docker image is not supported, however, you can use the Nautobot image as the base within your `Dockerfile` to install your own plugins, here is an example dockerfile:

```dockerfile
FROM networktocode/nautobot

RUN pip install nautobot-chatops

COPY nautobot_config.py /opt/nautobot/nautobot_config.py
```

## Building the Image

If you have a [development environment](../development/getting-started.md#setting-up-your-development-environment) you can use `invoke` to build the Docker image. By default `invoke build` will build the `dev` image:

```no-highlight
invoke build
```

After some output and a prompt is returned:

```no-highlight
docker images
```

Example output:

```no-highlight
REPOSITORY                                       TAG                              IMAGE ID       CREATED          SIZE
local/nautobot-dev                               local-py3.7                      0d93eec7dfea   5 minutes ago    1.31GB
```

If you need to build or test the `final` image, you must set your `invoke.yml` to use `docker-compose.final.yml` in place of `docker-compose.dev.yml`:

```yaml
---
nautobot:
  compose_files:
    - "docker-compose.yml"
    - "docker-compose.postgres.yml"
    - "docker-compose.final.yml"
```

Then you can re-run the `invoke build` command:

```no-highlight
invoke build
```

Example output:

```no-highlight
...
```

```no-highlight
docker images

```

Example output:

```no-highlight
REPOSITORY                                       TAG                              IMAGE ID       CREATED          SIZE
local/nautobot-final                             local-py3.7                      e03e752fcc6b   27 minutes ago   629MB
```

Similarly, you can use `docker-compose.final-dev.yml` if you wish to build and test the `final-dev` image.

## Docker Compose

An [example library for using Docker Compose](https://github.com/nautobot/nautobot-docker-compose/) to build out all of the components for Nautobot can be found within the Nautobot community. Please see [https://github.com/nautobot/nautobot-docker-compose/](https://github.com/nautobot/nautobot-docker-compose/) for examples on the base application, LDAP integration, and using plugins.
