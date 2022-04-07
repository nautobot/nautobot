ARG PYTHON_VER

################################ Overview
# This builds the following hierarchy of images:
#
# python:${PYTHON_VER}-slim
#           |
#           V
#         (base) --> (install-dependencies) --> dev --> final-dev
#           |                  |
#           V                  V
#         final <..... (install-nautobot)
#
# base (intermediate build target; basis for all other images herein)
#   adds OS-level packaging dependencies for *running* Nautobot
#
# install-dependencies (intermediate build target)
#   adds OS-level packaging dependencies for *installing* Nautobot, its dependencies, and its development dependencies
#   installs Pip and Poetry
#   uses Pip and Poetry to install Nautobot's Python dependencies (but *not* development dependencies)
#   uses Poetry to build a Nautobot wheel for later use by the "install-nautobot" and "final-dev" images
#
# dev (development environment for Nautobot core)
#   uses Poetry to additionally install Nautobot's *development* dependencies
#   uses Poetry to install Nautobot itself in editable (develop) mode
#     (at runtime the intent is to mount the live Nautobot source over the Poetry-installed Nautobot)
#   is capable of running Nautobot dev server
#
# install-nautobot (intermediate build target):
#   uses Pip to install the Nautobot wheel previously built in "install-dependencies"
#   creates a self-signed SSL certificate for later use by the "final" image
#
# final (production-ready environment):
#   adds "nautobot" system user
#   copies all installed Python packages, including Nautobot itself, from "install-nautobot"
#   copies the self-signed SSL certificate from "install-nautobot"
#   sets up the system to run Nautobot in production with uwsgi
#
# final-dev (development environment for Nautobot plugins)
#   as "dev", but replaces the editable install of Nautobot with a wheel-based install of Nautobot

################################ Stage: base (intermediate build target; basis for all other images herein)

FROM python:${PYTHON_VER}-slim as base

ENV PYTHONUNBUFFERED=1 \
    NAUTOBOT_ROOT=/opt/nautobot \
    prometheus_multiproc_dir=/prom_cache

# Install all OS package upgrades and dependencies needed to run Nautobot in production
# hadolint ignore=DL3005,DL3008,DL3013
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y git mime-support curl libxml2 libmariadb3 && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/* && \
    pip --no-cache-dir install --upgrade pip wheel

HEALTHCHECK --interval=5s --timeout=5s --start-period=5s --retries=1 CMD curl --fail http://localhost:8080/health/ || exit 1

################################ Stage: install-dependencies (intermediate build target)

FROM base as install-dependencies

# Modify the PATH here because otherwise poetry fails 100% of the time. WAT??
ENV PATH="${PATH}:/root/.local/bin"

# Install development/install-time OS dependencies
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install --no-install-recommends -y openssl build-essential libssl-dev libxmlsec1-dev libxmlsec1-openssl pkg-config libldap-dev libsasl2-dev libmariadb-dev && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/*

# Install Poetry manually from GitHub because otherwise it installs its own
# dependencies globally which may conflict with ours.
# https://python-poetry.org/docs/#osx-linux-bashonwindows-install-instructions
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/install-poetry.py -o /tmp/install-poetry.py && \
    python /tmp/install-poetry.py && \
    rm -f /tmp/install-poetry.py

# Poetry shouldn't create a venv as we want global install
# Poetry 1.1.0 added parallel installation as an option;
# unfortunately it seems to have some issues with installing/updating "requests" and "certifi"
# while simultaneously atttempting to *use* those packages to install other packages.
# For now we disable it.
RUN poetry config virtualenvs.create false && \
    poetry config installer.parallel false

# Install (non-development) Python dependencies of Nautobot
COPY pyproject.toml poetry.lock /source/
COPY examples /source/examples
WORKDIR /source
# pyuwsgi doesn't support ssl so we build it from source
# https://github.com/nautobot/nautobot/issues/193
RUN pip install --no-cache-dir --no-binary=pyuwsgi pyuwsgi==2.0.20 && \
    poetry install --no-root --no-dev --no-ansi --extras all

# Generate required dirs for later consumption
RUN mkdir /opt/nautobot /prom_cache

# Copy nautobot source and poetry info to container to reduce cache invalidations
COPY README.md /source/
COPY nautobot /source/nautobot

# Build the wheel for later use by other images
RUN poetry build

################################ Stage: dev (development environment for Nautobot core)
# nautobot will be installed in editable mode in /source

FROM install-dependencies as dev

# Install hadolint for linting Dockerfiles
RUN curl -Lo /usr/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.0.0/hadolint-Linux-x86_64 && \
    chmod +x /usr/bin/hadolint

# Used if someone wants to override the entrypoint and provision a super user
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh

# TODO Use nautobot init to generate the same config for all use cases
COPY development/nautobot_config.py /opt/nautobot/nautobot_config.py

# Common docker entrypoint for migrations, superuser creations, etc.
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nautobot-server", "runserver", "0.0.0.0:8080", "--insecure"]

# Install development-specific dependencies of Nautobot as well as Nautobot itself in editable mode
RUN poetry install --no-ansi --extras all

################################ Stage: install-nautobot (intermediate build target)

FROM install-dependencies as install-nautobot

# hadolint ignore=DL3013,SC2102
RUN for whl in /source/dist/nautobot*.whl; do pip install --no-deps --no-cache-dir ${whl}[all]; done

# Generate self signed ssl certificates for later use
RUN openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj \
    '/C=US/ST=NY/L=NYC/O=Nautobot/CN=nautobot.local' \
    -keyout /opt/nautobot/nautobot.key -out /opt/nautobot/nautobot.crt

################################ Stage: final (production-ready image)

FROM base as final
ARG PYTHON_VER

# Make sure we don't run as a root user
RUN useradd --system --shell /bin/bash --create-home --home-dir /opt/nautobot nautobot

# Copy from install-nautobot the required python libraries and binaries
COPY --from=install-nautobot /usr/local/lib/python${PYTHON_VER}/site-packages /usr/local/lib/python${PYTHON_VER}/site-packages
COPY --from=install-nautobot /usr/local/bin /usr/local/bin

# Setup the entrypoint
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh

# Copy SSL certs
COPY --from=install-nautobot /opt/nautobot/nautobot.key /opt/nautobot/nautobot.crt /opt/nautobot/

# Configure uWSGI
COPY docker/uwsgi.ini /opt/nautobot
COPY docker/nautobot_config.append.py /opt/nautobot

# Make sure everything under /opt/nautobot and /prom_cache is owned by nautobot
RUN mkdir /prom_cache && chown -R nautobot:nautobot /opt/nautobot /prom_cache

# Set up Nautobot to run in production
USER nautobot

WORKDIR /opt/nautobot

RUN nautobot-server init && \
    cat /opt/nautobot/nautobot_config.append.py >> /opt/nautobot/nautobot_config.py && \
    rm -f /opt/nautobot/nautobot_config.append.py

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nautobot-server", "start", "--ini", "/opt/nautobot/uwsgi.ini"]

################################ Stage: final-dev (development environment for Nautobot plugins)
# This image will contain the development dependencies (including poetry) as well as nautobot installed
# as a system package

FROM dev as final-dev

# Nautobot was installed in editable mode so reinstall as a system package (all dependencies are already there)
# hadolint ignore=DL3013,SC2102
RUN for whl in /source/dist/nautobot*.whl; do pip install --force-reinstall --no-deps --no-cache-dir ${whl}[all]; done && \
    rm -rf /source
