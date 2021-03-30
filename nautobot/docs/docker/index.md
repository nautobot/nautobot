# Nautobot Docker Images

Nautobot is packaged as a docker image for use in a production environment.  The published image is based on the `python:3.6-slim` docker image to maintain the most compatibility with Nautobot deployments.  The docker image and deployment strategies are being actively developed, check back here or join the **#nautobot** Slack channel on [Network to Code](https://networktocode.slack.com) for the most up to date information.

## Tags

We publish the docker image to both the Github container registry as well as docker hub.  The image can be pulled with either:

```
docker image pull networktocode/nautobot
docker image pull ghcr.io/nautobot/nautobot
```

The following tags are available:

* `vX.Y.Z` these images are built with the same baseline as the released Python packages
* `latest` these images are built from the latest code in the main branch (should be the latest released version)
* `latest-dev` these images are built from the latest code in the develop branch on each commit
* `develop-${GIT_SHA:0:7}-$(date +%s)` tags for each commit to the develop branch

## Getting Started

## Configuration

Most configuration parameters are available via environment variables which can be passed to the container.  If you desire you can inject your own `nautobot_config.py` by overriding `/opt/nautobot/nautobot_config.py`.

### Plugins

At this time adding plugins to the existing docker image is not supported, however, you can use this docker image as the base for your Dockerfile to install your own plugins:

## Building the Image

If you have a [development environment](/development/getting-started/#setting-up-your-development-environment) you can use invoke to build the docker images.  By default `invoke build` will build the development containers:

```
$ invoke build
...
$ docker images
REPOSITORY                                                                TAG                    IMAGE ID       CREATED          SIZE
networktocode/nautobot-dev                                                latest                 25487d93fc1f   16 seconds ago   630MB
```

If you need to build/use the production image set the `OVERRIDE_FILENAME`:

```
$ export OVERRIDE_FILENAME=docker-compose.test.yml
$ invoke build
...
$ docker images
REPOSITORY                                                                TAG                    IMAGE ID       CREATED          SIZE
networktocode/nautobot                                                    latest                 0a24d68da987   55 seconds ago   337MB
```

If you do not have a development environment created you can also build the container using the regular `docker build` command:

```
$ docker build -t networktocode/nautobot -f ./docker/Dockerfile --build-arg PYTHON_VER=3.6 .
```
