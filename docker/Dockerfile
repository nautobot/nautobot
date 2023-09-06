# syntax=docker/dockerfile:1
ARG PYTHON_VER

################################ Overview

# There are three end-target images for this Dockerfile:
# 1. "dev"
#    - a local Nautobot-core dev environment, used with the provided docker-compose files to mount the local
#      Nautobot source code into the Docker environment for live reloads and such while developing Nautobot.
#    - installs Python package dependencies (including dev dependencies) to a virtualenv in /opt/nautobot/
#    - installs Node module dependencies (including dev dependencies) to /opt/nautobot/ui/node_modules/
#    - installs Nautobot itself (and example apps) from /source/ in editable mode (to be overwritten by a volume mount)
#    - pre-renders the 2.0 UI
#    - runs Nautobot dev server as "root" user using the "development/nautobot_config.py" file.
# 2. "final-dev"
#    - base image for Nautobot apps development
#    - installs Python package dependencies (including dev dependencies) to a virtualenv in /opt/nautobot/
#    - installs Node module dependencies (including dev dependencies) to /opt/nautobot/ui/node_modules/
#    - installs Nautobot itself as a built wheel
#    - pre-renders the 2.0 UI
#    - runs Nautobot dev server as "nautobot" user using a freshly generated "nautobot_config.py" file.
# 3. "final"
#    - production-ready Nautobot environment
#    - installs Python package dependencies to a virtualenv in /opt/nautobot/
#    - installs Node module dependencies to /opt/nautobot/ui/node_modules/
#    - installs Nautobot itself as a built wheel
#    - pre-renders the 2.0 UI
#    - runs Nautobot uwsgi server as "nautobot" user using the same "nautobot_config.py" file as in final-dev.
#
# To create the above targets, we use the following intermediate stages to allow for parallelization and caching:
#
# - "system-dependencies" - system-level production dependencies (DB clients, Git, OpenSSL, NodeJS(*), etc.)
#   - "system-dev-dependencies" - system-level development dependencies (Poetry, dev versions of libraries, etc.)
#     - "system-dev-dependencies-$TARGETARCH" - system-level architecture-specific development dependencies (hadolint)
#       - "python-dependencies" - Python production dependencies (+ Poetry, though not included in the 'final' image)
#         - "python-dev-dependencies" - Python development dependencies (linters, example apps, debug toolbar, etc.)
#           - "build-nautobot" - Compilation of Nautobot static documentation as well as the Nautobot sdist and wheel
#     - "node-dependencies" - NodeJS production dependencies
#       - "node-dev-dependencies" - NodeJS development dependencies (linters, etc.)
#
# (*) NodeJS is a prod dependency because, even though we ship a pre-compiled Nautobot 2.0 UI in the 'final' image,
#     there's a need to be able to re-build the UI after adding/removing/upgrading Nautobot Apps.

################################ Stage: system-dependencies (intermediate build target; basis for all images herein)

FROM python:${PYTHON_VER}-slim AS system-dependencies

ENV PYTHONUNBUFFERED=1 \
    NAUTOBOT_ROOT=/opt/nautobot \
    prometheus_multiproc_dir=/prom_cache

# DL3008 - Require pinned dependencies for apt install
# DL3009 - Delete the apt-get lists after installing something
# DL3013 - pin all Python package versions
# DL3042 - run pip install with --no-cache-dir (https://github.com/hadolint/hadolint/issues/497)
# DL4006 - Set the SHELL option -o pipefail before RUN with a pipe in
# hadolint ignore=DL3008,DL3009,DL3013,DL3042,DL4006
RUN --mount=type=cache,target="/root/.cache/pip",sharing=locked \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_18.x | bash - && \
    apt-get install --no-install-recommends -y git mime-support libxml2 libmariadb3 openssl nodejs && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/* && \
    npm install -g npm@latest && \
    rm -rf /root/.npm && \
    pip install --upgrade pip wheel && \
    rm -rf /tmp/tmp*

HEALTHCHECK --interval=5s --timeout=5s --start-period=5s --retries=1 CMD curl --fail http://localhost:8080/health/ || exit 1

# Generate nautobot user and its required dirs for later consumption
RUN mkdir /opt/nautobot /opt/nautobot/.cache /prom_cache /source && \
    groupadd --gid 999 --system nautobot && \
    useradd --uid 999 --gid 999 --system --shell /bin/bash --create-home --home-dir /opt/nautobot nautobot && \
    chown -R nautobot:nautobot /opt/nautobot /prom_cache /source

# Common entrypoint for all environments
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

################################ Stage: system-dev-dependencies (intermediate build target)

FROM system-dependencies AS system-dev-dependencies

# Install development/install-time OS dependencies
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential libssl-dev libxmlsec1-dev libxmlsec1-openssl pkg-config libldap-dev libsasl2-dev libmariadb-dev && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/*

################################ Stage: system-dev-dependencies-$ARCH (intermediate build target)

FROM system-dev-dependencies AS system-dev-dependencies-amd64

# Install hadolint for linting Dockerfiles
RUN curl -Lo /usr/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.10.0/hadolint-Linux-x86_64 && \
    chmod +x /usr/bin/hadolint

FROM system-dev-dependencies AS system-dev-dependencies-arm64

# Install hadolint for linting Dockerfiles
RUN curl -Lo /usr/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.10.0/hadolint-Linux-arm64 && \
    chmod +x /usr/bin/hadolint

################################ Stage: node-dependencies (intermediate build target)

FROM system-dev-dependencies AS node-dependencies

USER nautobot
COPY --chown=nautobot:nautobot nautobot/ui/package.json nautobot/ui/package-lock.json /opt/nautobot/ui/
WORKDIR /opt/nautobot/ui

# Install (non-development) Node dependencies of Nautobot UI
RUN npm install --omit=dev

################################ Stage: node-dev-dependencies (intermediate build target)

FROM node-dependencies AS node-dev-dependencies

# Install development Node dependencies of Nautobot UI
RUN npm install --include=dev

################################ Stage: python-dependencies (intermediate build target)

# hadolint ignore=DL3006
FROM system-dev-dependencies-$TARGETARCH AS python-dependencies

USER nautobot

# Install Poetry manually via its installer script;
# if we instead used "pip install poetry" it would install its own dependencies globally which may conflict with ours.
# https://python-poetry.org/docs/master/#installing-with-the-official-installer
# This also makes it so that Poetry will *not* be included in the "final" image since it's not installed to /usr/local/
RUN --mount=type=cache,target="/opt/nautobot/.cache",uid=999,gid=999,sharing=locked \
    curl -sSL https://install.python-poetry.org -o /tmp/install-poetry.py && \
    python /tmp/install-poetry.py --version 1.5.1 && \
    rm -f /tmp/install-poetry.py

# Add poetry install location to the $PATH
ENV PATH="${PATH}:/opt/nautobot/.local/bin"

RUN --mount=type=cache,target="/opt/nautobot/.cache",uid=999,gid=999,sharing=locked \
    python -m venv /opt/nautobot

ENV PATH="/opt/nautobot/bin:${PATH}"
ENV VIRTUAL_ENV="/opt/nautobot"

# Poetry 1.1.0 added parallel installation as an option;
# unfortunately it seems to have some issues with installing/updating "requests" and "certifi"
# while simultaneously atttempting to *use* those packages to install other packages.
# This is disabled by default (safer), but can be re-enabled by setting POETRY_PARALLEL=true
# pyuwsgi wheel doesn't support ssl so we build it from source
# https://github.com/nautobot/nautobot/issues/193
RUN poetry config installer.parallel "${POETRY_PARALLEL:-false}" && \
    poetry config installer.no-binary pyuwsgi

# The example_plugin is only a dev dependency, but Poetry fails to install non-dev dependencies if its source is missing
COPY --chown=nautobot:nautobot pyproject.toml poetry.lock README.md /source/
COPY --chown=nautobot:nautobot examples /source/examples

WORKDIR /source

# Install (non-development) Python dependencies of Nautobot
RUN --mount=type=cache,target="/opt/nautobot/.cache",uid=999,gid=999,sharing=locked \
    poetry install --no-root --only main --no-ansi --extras all && \
    rm -rf /tmp/tmp*

################################ Stage: python-dev-dependencies (intermediate build target)

FROM python-dependencies AS python-dev-dependencies

# Add development-specific dependencies of Nautobot to the installation
RUN --mount=type=cache,target="/opt/nautobot/.cache",uid=999,gid=999,sharing=locked \
    poetry install --no-root --no-ansi --extras all && \
    rm -rf /tmp/tmp*

################################ Stage: build-nautobot (intermediate build target)

FROM python-dev-dependencies AS build-nautobot

COPY --chown=nautobot:nautobot mkdocs.yml /source/mkdocs.yml
COPY --chown=nautobot:nautobot docs /source/docs
COPY --chown=nautobot:nautobot nautobot /source/nautobot

# Build the rendered docs, this ensures that the docs are in the final image.
RUN mkdocs build --no-directory-urls && \
    poetry build

################################ Stage: dev (development environment for Nautobot core)

FROM python-dev-dependencies AS dev

COPY --chown=nautobot:nautobot nautobot/ui /opt/nautobot/ui
COPY --from=node-dev-dependencies --chown=nautobot:nautobot /opt/nautobot/ui/node_modules /opt/nautobot/ui/node_modules

COPY --chown=nautobot:nautobot nautobot /source/nautobot

COPY --from=build-nautobot --chown=nautobot:nautobot /source/nautobot/project-static/docs /source/nautobot/project-static/docs

RUN --mount=type=cache,target="/opt/nautobot/.cache",uid=999,gid=999,sharing=locked \
    poetry install --no-ansi --extras all && \
    rm -rf /tmp/tmp*

ENV NAUTOBOT_INSTALLATION_METRICS_ENABLED=false

COPY --chown=nautobot:nautobot development/nautobot_config.py /opt/nautobot/nautobot_config.py

RUN nautobot-server build_ui && rm -rf /source/*

# switch to root user for dev stage: https://github.com/nautobot/nautobot/issues/4164
# hadolint ignore=DL3002
USER root

# Run Nautobot development server by default
EXPOSE 8080
CMD ["nautobot-server", "runserver", "0.0.0.0:8080", "--insecure"]

################################ Stage: final-dev (development environment for Nautobot plugins)

FROM python-dev-dependencies AS final-dev

COPY --chown=nautobot:nautobot nautobot/ui /opt/nautobot/ui
COPY --from=node-dev-dependencies --chown=nautobot:nautobot /opt/nautobot/ui/node_modules /opt/nautobot/ui/node_modules

COPY --from=build-nautobot --chown=nautobot:nautobot /source/dist /source/dist

# Install Nautobot wheel, and uninstall example apps as they're not included in the final-dev image
# DL3042 - run pip install with --no-cache-dir (https://github.com/hadolint/hadolint/issues/497)
# hadolint ignore=DL3042
RUN --mount=type=cache,target="/opt/nautobot/.cache",uid=999,gid=999,sharing=locked \
    pip install --no-deps /source/dist/*.whl && \
    pip uninstall -y example-plugin example-plugin-with-view-override && \
    rm -rf /source/*

WORKDIR /opt/nautobot

# Don't send install metrics as this is a development target, not a deployment one
ENV NAUTOBOT_INSTALLATION_METRICS_ENABLED=false

RUN nautobot-server init && \
    nautobot-server build_ui

# switch to root user for final-dev stage: https://github.com/nautobot/nautobot/issues/4300
# hadolint ignore=DL3002
USER root

# Run Nautobot development server by default
EXPOSE 8080
CMD ["nautobot-server", "runserver", "0.0.0.0:8080", "--insecure"]

################################ Stage: final (production-ready image)

FROM system-dependencies AS final

USER nautobot
ENV PATH="/opt/nautobot/bin:${PATH}"
ENV VIRTUAL_ENV="/opt/nautobot"

COPY --from=python-dependencies --chown=nautobot:nautobot /opt/nautobot/bin /opt/nautobot/bin
COPY --from=python-dependencies --chown=nautobot:nautobot /opt/nautobot/include /opt/nautobot/include
COPY --from=python-dependencies --chown=nautobot:nautobot /opt/nautobot/lib /opt/nautobot/lib
COPY --from=python-dependencies --chown=nautobot:nautobot /opt/nautobot/lib64 /opt/nautobot/lib64
COPY --from=python-dependencies --chown=nautobot:nautobot /opt/nautobot/pyvenv.cfg /opt/nautobot/pyvenv.cfg

COPY --from=build-nautobot --chown=nautobot:nautobot /source/dist /source/dist

COPY --from=final-dev --chown=nautobot:nautobot /opt/nautobot/nautobot_config.py /opt/nautobot/nautobot_config.py
COPY --from=final-dev --chown=nautobot:nautobot /opt/nautobot/ui /opt/nautobot/ui

# DL3042 - run pip install with --no-cache-dir (https://github.com/hadolint/hadolint/issues/497)
# hadolint ignore=DL3042
RUN --mount=type=cache,target="/opt/nautobot/.cache",uid=999,gid=999,sharing=locked \
    pip install --no-deps /source/dist/*.whl && \
    rm -rf /source/*

# Generate self-signed SSL certs
RUN openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj \
    '/C=US/ST=NY/L=NYC/O=Nautobot/CN=nautobot.local' \
    -keyout /opt/nautobot/nautobot.key -out /opt/nautobot/nautobot.crt

# Set up Nautobot to run in production
WORKDIR /opt/nautobot

# Run Nautobot server under uwsgi by default
COPY --chown=nautobot:nautobot docker/uwsgi.ini /opt/nautobot
EXPOSE 8080 8443
CMD ["nautobot-server", "start", "--ini", "/opt/nautobot/uwsgi.ini"]
