# Nautobot Docker Images

Nautobot is packaged as a Docker image for use in a production environment. The published image is based on the `python:3.6-slim` image to maintain the most compatibility with Nautobot deployments. The Docker image and deployment strategies are being actively developed, check back here or join the **#nautobot** Slack channel on [Network to Code](https://networktocode.slack.com) for the most up to date information.

## Tags

The Docker image is published to Docker Hub.

To get the image from Docker Hub run:

```no-highlight
docker image pull networktocode/nautobot
```

The following tags are available:

* `X.Y.Z` these images are built with the same baseline as the released Python packages based on the default python version (3.6) docker container
* `latest` these images are built from the latest code in the main branch (should be the latest released version) based on the default python version (3.6) docker container
* `X.Y.Z-py${PYTHON_VER}` these images are built with the same baseline as the released Python packages based on the python version ($PYTHON_VER) docker container
* `latest-py${PYTHON_VER}` these images are built from the latest code in the main branch (should be the latest released version) based on the python version ($PYTHON_VER) docker container
* `develop` these images are built from the latest code in the develop branch on each commit based on the default python version (3.6) docker container
* `develop-${GIT_SHA:0:7}-$(date +%s)` tags for each commit to the develop branch based on the default python version (3.6) docker container
* `develop-py${PYTHON_VER}` these images are built from the latest code in the develop branch on each commit based on the python version ($PYTHON_VER) docker container
* `develop-${GIT_SHA:0:7}-$(date +%s)-py${PYTHON_VER}` tags for each commit to the develop branch based on the python version ($PYTHON_VER) docker container

To pull a specific tag you can append the image name with `:tag` for example, to pull the 1.0.0 image:

```no-highlight
$ docker image pull networktocode/nautobot:1.0.0
```

Currently images are pushed for the following python versions:

* 3.6
* 3.7
* 3.8
* 3.9 _For Testing Only_

!!! info
    A dev image `networktocode/nautobot-dev` and `nautobot/nautobot-dev` is also provided with the same tags, this image provides the development dependencies needed to build Nautobot.  This container can be used as a base for development to develop additional Nautobot plugins but should **NOT** be used in production.

## Getting Started

Nautobot requires a PostgreSQL database and Redis instance before it will start. Because of this the quickest and easiest way to get Nautobot running is with `docker-compose`.

## Configuration

Most configuration parameters are available via environment variables which can be passed to the container.  If you desire you can inject your own `nautobot_config.py` by overriding `/opt/nautobot/nautobot_config.py` using [docker volumes](https://docs.docker.com/storage/volumes/) by adding `-v /local/path/to/custom/nautobot_config.py:/opt/nautobot/nautobot_config.py` to your docker run command, for example:

```no-highlight
$ docker run --name nautobot -v /local/path/to/custom/nautobot_config.py:/opt/nautobot/nautobot_config.py nautobot/nautobot
```

Or if you are using docker-compose:

```yaml
services:
  nautobot:
    image: "nautobot/nautobot"
    volumes:
      - /local/path/to/custom/nautobot_config.py:/opt/nautobot/nautobot_config.py:ro
```

### uWSGI

The docker container uses [uWSGI](https://uwsgi-docs.readthedocs.io/) to serve Nautobot.  A default configuration is [provided](/docker/uwsgi.ini), and can be overridden by injecting a new `uwsgi.ini` file at `/opt/nautobot/uwsgi.ini`.  There are a couple of environment variables provided to override some uWSGI defaults:

#### `NAUTOBOT_UWSGI_LISTEN`

Default: `128`

The socket listen queue size of uWSGI.  In production environments it is recommended to increase this value to 1024 or higher, however depending on your platform, this may require additional kernel parameter settings, please see [the uWSGI documentation](https://uwsgi-docs.readthedocs.io/en/latest/articles/TheArtOfGracefulReloading.html#the-listen-queue) for more information.

Please see the [official uWSGI documentation on `listen`](https://uwsgi-docs.readthedocs.io/en/latest/Options.html?highlight=listen#listen) for more information.

---

#### `NAUTOBOT_UWSGI_PROCESSES`

Default: `3`

The number of worker processes uWSGI will spawn.

Please see the [official uWSGI documentation on `processes`](https://uwsgi-docs.readthedocs.io/en/latest/Options.html?highlight=processes#processes) for more information.

---

### SSL

Self signed SSL certificates are included by default with the container.  For a production deployment you should utilize your own signed certificates, these can be injected into the container at runtime using [docker volumes](https://docs.docker.com/storage/volumes/).  The public certificate should be placed at `/opt/nautobot/nautobot.crt` and the private key should be at `/opt/nautobot/nautobot.key`.  Using a `docker run` these can be injected using the `-v` parameter:

```no-highlight
$ docker run --name nautobot -v /local/path/to/custom/nautobot.crt:/opt/nautobot/nautobot.crt -v /local/path/to/custom/nautobot.key:/opt/nautobot/nautobot.key nautobot/nautobot
```

Or if you are using `docker-compose`:

```yaml
services:
  nautobot:
    image: "nautobot/nautobot"
    volumes:
      - /local/path/to/custom/nautobot.crt:/opt/nautobot/nautobot.crt:ro
      - /local/path/to/custom/nautobot.key:/opt/nautobot/nautobot.key:ro
```

### Nautobot Plugins

At this time adding Nautobot plugins to the existing Docker image is not supported, however, you can use the Nautobot image as the base within your `Dockerfile` to install your own plugins, here is an example dockerfile:

```dockerfile
FROM nautobot/nautobot

RUN pip install nautobot-chatops

COPY nautobot_config.py /opt/nautobot/nautobot_config.py
```

## Building the Image

If you have a [development environment](/development/getting-started/#setting-up-your-development-environment) you can use invoke to build the docker images.  By default `invoke build` will build the development containers:

```no-highlight
$ invoke build
...
$ docker images
REPOSITORY                                                                TAG                    IMAGE ID       CREATED          SIZE
networktocode/nautobot-dev                                                local                  25487d93fc1f   16 seconds ago   630MB
```

If you need to build or test the final image set the `INVOKE_NAUTOBOT_COMPOSE_OVERRIDE_FILE` environment variable:

```no-highlight
$ export INVOKE_NAUTOBOT_COMPOSE_OVERRIDE_FILE=docker-compose.build.yml
$ invoke build
...
$ docker images
REPOSITORY                                                                TAG                    IMAGE ID       CREATED          SIZE
networktocode/nautobot                                                    local                  0a24d68da987   55 seconds ago   337MB
```

If you do not have a development environment created you can also build the container using the regular `docker build` command:

```no-highlight
$ docker build -t networktocode/nautobot -f ./docker/Dockerfile --build-arg PYTHON_VER=3.6 .
```
