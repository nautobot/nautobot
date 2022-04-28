ARG PYTHON_VER
ARG PYUWSGI_VER

################################ Overview
# This builds the following hierarchy of images:
#
# python:${PYTHON_VER}-slim
#            |
#            V
#         (base)
#            |----------------------------------------------------------
#            V                                                          |
#     (dependencies)                                                    |
#            |                                                          V
#            |----------------> (build-nautobot) . . . . . . . . . >  final
#            V                        /\               .
# (dependencies-dev-python)            .               .
#            |                         .               .
#            |-----------------> (build-docs)          .
#            V                                         .
# (dependencies-dev-platform-ARCH)                     .
#            |                                         .
#            V                                         .
#    (dependencies-dev) < . . . . . . . . . . . . . . .
#       |          |
#       V          V
#      dev     final-dev
#
#  The design philosphy for this image hierarchy is:
#  
#  - pyproject.toml is the source of truth for dependencies
#  - Non-intermediate image targets (final, final-dev, dev) will not contain files they don't need
#      - EX: No dev dependencies in final image
#  - When changing source code only (no dependency changes):
#      - Dependencies will NOT need to be reinstalled (cached, time intensive)
#      - Docs will NOT need to be rebuilt
#      - Wheel will need to be rebuilt
#      - Each non-intermediate final image will need to be rebuilt
#  - When changing docs only (no dependency changes):
#      - Dependencies will NOT need to be reinstalled (cached, time intensive)
#      - Docs will need to be rebuilt
#      - Wheel will need to be rebuilt (due to packaging docs in wheel, container)
#      - Each non-intermediate final image will need to be rebuilt
#  - When changing dependencies (regardless of code changes):
#      - Dependencies will need to be reinstalled (cache will be invalid)
#      - Docs will need to be rebuilt
#      - Wheel will need to be rebuilt
#      - Each non-intermediate final image will need to be rebuilt
#  - Minimize repeating the same steps twice
#
# base (intermediate build target; basis for all other images herein)
#   adds OS-level dependencies for *running* Nautobot
#   installs Pip and wheel
#   creates required directories and adds Docker healthcheck and entrypoint script
#
# dependencies (intermediate build target)
#   adds OS-level dependencies for *installing* Nautobot, its dependencies, and its development dependencies
#   installs Poetry
#   copies Nautobot source files and packaging definition into the image
#   uses Pip/Poetry to install Nautobot's Python dependencies (but *not* development dependencies or Nautobot itself)
#
# dependencies-dev-python (intermediate build target)
#   uses Poetry to additionally install Nautobot's *development* dependencies
#
# build-docs (intermediate build target)
#   uses mkdocs to build docs static files for wheel and Docker image build
#
# build-nautobot (intermediate build target)
#   uses Poetry to build a Nautobot wheel (but not yet install it)
#
# dependencies-dev-platform-ARCH (intermediate build target)
#   installs Hadolint, Node.JS which have platform specific commands
#
# dependencies-dev (intermediate build target)
#   copies built Nautobot wheel and files from build-nautobot
#   installs Markdownlint 
#   adds files and configuration for Nautobot development server to run
#
# dev (development environment for Nautobot core)
#   uses Poetry to install Nautobot as editable
#     (at runtime the requirement is to mount the live Nautobot source code to /source/; it won't run without that)
#
# final-dev (development environment for Nautobot plugins)
#   uses Pip to install Nautobot as a wheel
#
# final (production-ready environment):
#   removes Poetry
#   copies all installed Python dependencies from "dependencies"
#   copies Nautobot wheel from "dependencies" and installs it
#   creates a self-signed SSL certificate
#   adds "nautobot" system user
#   sets up the system to run Nautobot in production with uwsgi

################################ Stage: base (intermediate build target; basis for all other images herein)

FROM python:${PYTHON_VER}-slim as base

ENV PYTHONUNBUFFERED=1 \
    NAUTOBOT_ROOT=/opt/nautobot \
    prometheus_multiproc_dir=/prom_cache

# Install all OS package upgrades and dependencies needed to run Nautobot in production
# hadolint ignore=DL3005,DL3008,DL3013
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y git mime-support curl libxml2 libmariadb3 openssl && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/* && \
    pip --no-cache-dir install --upgrade pip wheel

HEALTHCHECK --interval=5s --timeout=5s --start-period=5s --retries=1 CMD curl --fail http://localhost:8080/health/ || exit 1

# Generate required dirs for later consumption
RUN mkdir /opt/nautobot /prom_cache

# Common entrypoint for all environments
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]

################################ Stage: dependencies (intermediate build target)

FROM base as dependencies
ARG PYUWSGI_VER
ARG POETRY_PARALLEL

# Install development/install-time OS dependencies
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install --no-install-recommends -y build-essential libssl-dev libxmlsec1-dev libxmlsec1-openssl pkg-config libldap-dev libsasl2-dev libmariadb-dev && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry manually via its installer script;
# if we instead used "pip install poetry" it would install its own dependencies globally which may conflict with ours.
# https://python-poetry.org/docs/master/#installing-with-the-official-installer
# This also makes it so that Poetry will *not* be included in the "final" image since it's not installed to /usr/local/
RUN curl -sSL https://install.python-poetry.org -o /tmp/install-poetry.py && \
    python /tmp/install-poetry.py && \
    rm -f /tmp/install-poetry.py

# Add poetry install location to the $PATH
ENV PATH="${PATH}:/root/.local/bin"

# Poetry shouldn't create a venv as we want global install
# Poetry 1.1.0 added parallel installation as an option;
# unfortunately it seems to have some issues with installing/updating "requests" and "certifi"
# while simultaneously atttempting to *use* those packages to install other packages.
# This is disabled by default (safer), but can be re-enabled by setting POETRY_PARALLEL=true
RUN poetry config virtualenvs.create false && \
    poetry config installer.parallel ${POETRY_PARALLEL:-false}

COPY pyproject.toml poetry.lock README.md /source/

# The example_plugin is only a dev dependency, but Poetry fails to install non-dev dependencies if its source is missing
COPY examples /source/examples

WORKDIR /source

# Install (non-development) Python dependencies of Nautobot
# pyuwsgi wheel doesn't support ssl so we build it from source
# https://github.com/nautobot/nautobot/issues/193
RUN pip install --no-cache-dir --no-binary=pyuwsgi pyuwsgi==${PYUWSGI_VER} && \
    poetry install --no-root --no-dev --no-ansi --extras all

################################ Stage: dependencies-dev-python (intermediate build target)
# We need dev dependencies for building the docs but don't want them in the final build image
# We install more dependencies here and can copy where needed
# Improves caching as well when these dependencies don't change

FROM dependencies as dependencies-dev-python

# Development-specific dependencies of Nautobot
RUN poetry install --no-root --no-ansi --extras all

################################ Stage: build-docs (intermediate build target)
# Docs get built as their own stage because again we need dev dependencies as a base but
# want to collect the output of `mkdocs` for the `build-nautobot` stage

FROM dependencies-dev-python as build-docs

# Copy docs dependencies to build the rendered docs
COPY mkdocs.yml /source/
COPY docs /source/docs

# Build the rendered docs, this ensures that the docs are in the final image.
RUN mkdocs build --no-directory-urls

################################ Stage: build-nautobot (intermediate build target)

FROM dependencies as build-nautobot
# Copy in the Nautobot source code to build the wheel from
COPY nautobot /source/nautobot

# Copy in the built docs to bundle with the wheel
COPY --from=build-docs /source/nautobot/project-static/docs /source/nautobot/project-static/docs

# Build the wheel
RUN poetry build

################################ Stage: dependencies-dev-platform-ARCH (intermediate build target)

FROM dependencies-dev-python as dependencies-dev-platform-amd64

# Install hadolint for linting Dockerfiles
RUN curl -Lo /usr/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.10.0/hadolint-Linux-x86_64 && \
    chmod +x /usr/bin/hadolint

# Install NodeJS for installing markdownlint-cli

RUN curl -Lo /tmp/node.tar.xz https://nodejs.org/dist/v17.9.0/node-v17.9.0-linux-x64.tar.xz && \
    mkdir -p /usr/local/lib/nodejs && \
    tar -xf /tmp/node.tar.xz -C /usr/local/lib/nodejs && \
    rm -rf /tmp/node.tar.xz

ENV PATH="${PATH}:/usr/local/lib/nodejs/node-v17.9.0-linux-x64/bin"

FROM dependencies-dev-python as dependencies-dev-platform-arm64

# Install hadolint for linting Dockerfiles
RUN curl -Lo /usr/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.10.0/hadolint-Linux-arm64 && \
    chmod +x /usr/bin/hadolint

# Install NodeJS for installing markdownlint-cli

RUN curl -Lo /tmp/node.tar.xz https://nodejs.org/dist/v17.9.0/node-v17.9.0-linux-arm64.tar.xz && \
    mkdir -p /usr/local/lib/nodejs && \
    tar -xf /tmp/node.tar.xz -C /usr/local/lib/nodejs && \
    rm -rf /tmp/node.tar.xz

ENV PATH="${PATH}:/usr/local/lib/nodejs/node-v17.9.0-linux-arm64/bin"

################################ Stage: dependencies-dev (intermediate build target)

# hadolint ignore=DL3006
FROM dependencies-dev-platform-$TARGETARCH as dependencies-dev

RUN npm install --global markdownlint-cli@0.31.1

# Nautobot wheel build is no longer a direct previous layer
# /source from build-nautobot will include docs from build-docs as well
COPY --from=build-nautobot /source /source

# TODO Use nautobot init to generate the same config for all use cases
COPY development/nautobot_config.py /opt/nautobot/nautobot_config.py

# Run Nautobot development server by default
EXPOSE 8080
CMD ["nautobot-server", "runserver", "0.0.0.0:8080", "--insecure"]

################################ Stage: dev (development environment for Nautobot core)

FROM dependencies-dev as dev

RUN poetry install --no-ansi && \
    rm -rf /source

################################ Stage: final-dev (development environment for Nautobot plugins)

FROM dependencies-dev as final-dev

RUN pip install --no-deps --no-cache-dir /source/dist/*.whl && \
    rm -rf /source

################################ Stage: final (production-ready image)

FROM base as final
ARG PYTHON_VER

# Copy from "dependencies" the required python libraries and binaries
# Copy from "build-nautobot" the built Nautobot wheel
COPY --from=dependencies /usr/local/lib/python${PYTHON_VER}/site-packages /usr/local/lib/python${PYTHON_VER}/site-packages
COPY --from=dependencies /usr/local/bin /usr/local/bin
COPY --from=build-nautobot /source/dist/*.whl /tmp

# Install the Nautobot wheel
RUN pip install --no-deps --no-cache-dir /tmp/*.whl && \
    rm -rf /tmp/*.whl

# Generate self-signed SSL certs
RUN openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj \
    '/C=US/ST=NY/L=NYC/O=Nautobot/CN=nautobot.local' \
    -keyout /opt/nautobot/nautobot.key -out /opt/nautobot/nautobot.crt

# Configure uWSGI
COPY docker/uwsgi.ini /opt/nautobot
COPY docker/nautobot_config.append.py /opt/nautobot

# Make sure we don't run as a root user and make sure everything under /opt/nautobot and /prom_cache is owned by nautobot
RUN useradd --system --shell /bin/bash --create-home --home-dir /opt/nautobot nautobot && \
    chown -R nautobot:nautobot /opt/nautobot /prom_cache

# Set up Nautobot to run in production
USER nautobot

WORKDIR /opt/nautobot

RUN nautobot-server init && \
    cat /opt/nautobot/nautobot_config.append.py >> /opt/nautobot/nautobot_config.py && \
    rm -f /opt/nautobot/nautobot_config.append.py

# Run Nautobot server under uwsgi by default
EXPOSE 8080 8443
CMD ["nautobot-server", "start", "--ini", "/opt/nautobot/uwsgi.ini"]
