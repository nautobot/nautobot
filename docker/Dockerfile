# syntax=docker/dockerfile:1
ARG PYTHON_VER
# Small hack to make the devcontainer work until https://github.com/devcontainers/cli/issues/275 is fixed.
ARG ARCH=${TARGETARCH:-amd64}

################################ Overview

# There are three end-target images for this Dockerfile:
# 1. "dev"
#    - a local Nautobot-core dev environment, used with the provided docker-compose files to mount the local
#      Nautobot source code into the Docker environment for live reloads and such while developing Nautobot.
#    - installs Python package dependencies (including dev dependencies) to a virtualenv in /opt/nautobot/
#    - installs Nautobot itself (and example apps) from /source/ in editable mode (to be overwritten by a volume mount)
#    - runs Nautobot dev server as "root" user using the "development/nautobot_config.py" file.
# 2. "final-dev"
#    - base image for Nautobot apps development
#    - installs Python package dependencies (including dev dependencies) to a virtualenv in /opt/nautobot/
#    - installs Nautobot itself as a built wheel
#    - runs Nautobot dev server as "nautobot" user using a freshly generated "nautobot_config.py" file.
# 3. "final"
#    - production-ready Nautobot environment
#    - installs Python package dependencies to a virtualenv in /opt/nautobot/
#    - installs Nautobot itself as a built wheel
#    - runs Nautobot uwsgi server as "nautobot" user using the same "nautobot_config.py" file as in final-dev.
#
# To create the above targets, we use the following intermediate stages to allow for parallelization and caching:
#
# - "system-dependencies" - system-level production dependencies (DB clients, Git, OpenSSL, etc.)
#   - "system-dev-dependencies" - system-level development dependencies (Poetry, dev versions of libraries, etc.)
#     - "system-dev-dependencies-$TARGETARCH" - system-level architecture-specific development dependencies (hadolint)
#       - "python-dependencies" - Python production dependencies (+ Poetry, though not included in the 'final' image)
#         - "python-dev-dependencies" - Python development dependencies (linters, example apps, debug toolbar, etc.)
#           - "build-nautobot" - Compilation of Nautobot static documentation as well as the Nautobot sdist and wheel

################################ Stage: system-dependencies (intermediate build target; basis for all images herein)

FROM python:${PYTHON_VER}-slim AS system-dependencies

ENV PYTHONUNBUFFERED=1 \
    NAUTOBOT_ROOT=/opt/nautobot \
    prometheus_multiproc_dir=/prom_cache

# DL3008 - Require pinned dependencies for apt install
# DL3009 - Delete the apt-get lists after installing something
# DL4006 - Set the SHELL option -o pipefail before RUN with a pipe in
# hadolint ignore=DL3008,DL3009,DL4006
RUN --mount=type=cache,target="/var/cache/apt",sharing=locked \
    --mount=type=cache,target="/var/lib/apt/lists",sharing=locked \
    apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y curl git mime-support libxml2 libxmlsec1-dev libxmlsec1-openssl libmariadb3 openssl && \
    apt-get autoremove -y

# DL3013 - pin all Python package versions
# DL3042 - run pip install with --no-cache-dir (https://github.com/hadolint/hadolint/issues/497)
# hadolint ignore=DL3013,DL3042
RUN --mount=type=cache,target="/root/.cache/pip",sharing=locked \
    --mount=type=cache,target="/tmp",sharing=locked \
    pip install --upgrade pip wheel

# timeout/interval=10s because `nautobot-server` can be slow to start - https://github.com/nautobot/nautobot/issues/4292
# start-period=5m because initial migrations can take several minutes to run on a fresh DB
HEALTHCHECK --interval=10s --timeout=10s --start-period=5m --retries=3 CMD nautobot-server health_check

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
    apt-get install --no-install-recommends -y build-essential libssl-dev pkg-config libldap-dev libsasl2-dev libmariadb-dev mariadb-client && \
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

# ################################ Stage: poetry (stub for poetry only)

# FROM python:${PYTHON_VER}-slim AS poetry
# # Install Poetry manually via its installer script;
# ADD https://install.python-poetry.org /tmp/install-poetry.py
# RUN python /tmp/install-poetry.py

# # Add uv sync location to the $PATH
# ENV PATH="${POETRY_HOME}/bin:${PATH}"

# RUN poetry config virtualenvs.create ${POETRY_VIRTUALENVS_CREATE} && \
#     poetry config installer.parallel "${POETRY_INSTALLER_PARALLEL}" && \
#     poetry config installer.no-binary lxml,pyuwsgi,xmlsec

################################ Stage: python-dependencies (intermediate build target)

# hadolint ignore=DL3006
FROM system-dev-dependencies-${ARCH} AS python-dependencies

COPY --from=ghcr.io/astral-sh/uv:0.6.8 /uv /uvx /bin/
ENV PATH="/root/.local/bin/:$PATH"

RUN uv pip install --system --no-binary lxml lxml
RUN uv pip install --system --no-binary pyuwsgi pyuwsgi
RUN uv pip install --system --no-binary xmlsec xmlsec

# The example_app is only a dev dependency, but Uv fails to install non-dev dependencies if its source is missing
COPY --chown=nautobot:nautobot pyproject.toml uv.lock README.md /source/
COPY --chown=nautobot:nautobot examples /source/examples

WORKDIR /source

# Install (non-development) Python dependencies of Nautobot
RUN --mount=type=cache,target="/root/.cache",sharing=locked \
    uv sync --color never --frozen && rm -rf /tmp/tmp*

# Verify that pyuwsgi was installed correctly, i.e. with SSL support
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN pyuwsgi --cflags | sed 's/ /\n/g' | grep -e "^-DUWSGI_SSL$"

################################ Stage: python-dev-dependencies (intermediate build target)

FROM python-dependencies AS python-dev-dependencies

# Add development-specific dependencies of Nautobot to the installation
RUN --mount=type=cache,target="/root/.cache",sharing=locked \
    uv sync --color never --group docs --frozen && rm -rf /tmp/tmp*

################################ Stage: build-nautobot (intermediate build target)

FROM python-dev-dependencies AS build-nautobot

COPY --chown=nautobot:nautobot mkdocs.yml /source/mkdocs.yml
COPY --chown=nautobot:nautobot docs /source/docs
COPY --chown=nautobot:nautobot nautobot /source/nautobot

# Build the rendered docs, this ensures that the docs are in the final image.
RUN uv run mkdocs build --no-directory-urls && \
    uv build --quiet

################################ Stage: dev (development environment for Nautobot core)

FROM python-dev-dependencies AS dev

COPY --chown=nautobot:nautobot nautobot /source/nautobot

COPY --from=build-nautobot --chown=nautobot:nautobot /source/nautobot/project-static/docs /source/nautobot/project-static/docs

RUN --mount=type=cache,target="/root/.cache",sharing=locked \
    uv sync --color never --frozen --all-groups && rm -rf /tmp/tmp*

ENV NAUTOBOT_INSTALLATION_METRICS_ENABLED=false

COPY --chown=nautobot:nautobot development/nautobot_config.py /opt/nautobot/nautobot_config.py

# Run Nautobot development server by default
EXPOSE 8080
CMD ["nautobot-server", "runserver", "0.0.0.0:8080", "--insecure"]

################################ Stage: final-dev (development environment for Nautobot plugins)

FROM python-dev-dependencies AS final-dev

COPY --from=build-nautobot --chown=nautobot:nautobot /source/dist /source/dist

# Install Nautobot wheel, and uninstall example apps as they're not included in the final-dev image
# DL3042 - run pip install with --no-cache-dir (https://github.com/hadolint/hadolint/issues/497)
# hadolint ignore=DL3042
RUN --mount=type=cache,target="/root/.cache",sharing=locked \
    uv pip install --no-deps /source/dist/*.whl && \
    uv pip uninstall -y example-app example-app-with-view-override && \
    rm -rf /source/*

USER nautobot

WORKDIR /opt/nautobot

# Don't send install metrics as this is a development target, not a deployment one
ENV NAUTOBOT_INSTALLATION_METRICS_ENABLED=false

RUN nautobot-server init

# switch to root user for final-dev stage: https://github.com/nautobot/nautobot/issues/4300
# hadolint ignore=DL3002
USER root

# Run Nautobot development server by default
EXPOSE 8080
CMD ["nautobot-server", "runserver", "0.0.0.0:8080", "--insecure"]

################################ Stage: final (production-ready image)

FROM system-dependencies AS final

ARG PYTHON_VER
COPY --from=python-dependencies /usr/local/lib/python${PYTHON_VER}/site-packages /usr/local/lib/python${PYTHON_VER}/site-packages
COPY --from=python-dependencies /usr/local/bin /usr/local/bin

COPY --from=build-nautobot --chown=nautobot:nautobot /source/dist /source/dist

COPY --from=final-dev --chown=nautobot:nautobot /opt/nautobot/nautobot_config.py /opt/nautobot/nautobot_config.py

# DL3042 - run pip install with --no-cache-dir (https://github.com/hadolint/hadolint/issues/497)
# hadolint ignore=DL3042
RUN --mount=type=cache,target="/root/.cache",sharing=locked \
    uv pip install --no-deps /source/dist/*.whl && \
    rm -rf /source/*

USER nautobot

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
