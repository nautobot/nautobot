ARG PYTHON_VER
################################ Stage: base
# Install all OS package upgrades and dependencies once from which we will base other containers
FROM python:${PYTHON_VER}-slim as base

ENV PYTHONUNBUFFERED=1 \
    NAUTOBOT_ROOT=/opt/nautobot \
    prometheus_multiproc_dir=/prom_cache

# Install all OS package upgrades and dependencies
# hadolint ignore=DL3005,DL3008,DL3013
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y git mime-support curl && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/* && \
    pip --no-cache-dir install --upgrade pip wheel

HEALTHCHECK --interval=5s --timeout=5s --start-period=5s --retries=1 CMD curl --fail http://localhost:8080/health/ || exit 1

################################ Stage: dev
# The dev container is used for development purposes but also to build the .whl for the final image
# nautobot will be installed in editable mode in /source 
FROM base as dev

# Modify the PATH here because otherwise poetry fails 100% of the time. WAT??
ENV PATH="${PATH}:/root/.poetry/bin"

# Install development OS dependencies
# hadolint ignore=DL3008
RUN apt-get update && \
    apt-get install --no-install-recommends -y openssl && \
    apt-get install --no-install-recommends -y default-libmysqlclient-dev gcc && \
    apt-get autoremove -y && \
    apt-get clean all && \
    rm -rf /var/lib/apt/lists/*

# Install hadolint for linting Dockerfiles
RUN curl -Lo /usr/bin/hadolint https://github.com/hadolint/hadolint/releases/download/v2.0.0/hadolint-Linux-x86_64 && \
    chmod +x /usr/bin/hadolint

# Install Poetry manually from GitHub because otherwise it installs its own
# dependencies globally which may conflict with ours.
# https://python-poetry.org/docs/#osx-linux-bashonwindows-install-instructions
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py -o /tmp/get-poetry.py && \
    python /tmp/get-poetry.py && \
    rm -f /tmp/get-poetry.py

# Poetry shouldn't create a venv as we want global install
# Poetry 1.1.0 added parallel installation as an option;
# unfortunately it seems to have some issues with installing/updating "requests" and "certifi"
# while simultaneously atttempting to *use* those packages to install other packages.
# For now we disable it.
RUN /root/.poetry/bin/poetry config virtualenvs.create false && \
    /root/.poetry/bin/poetry config installer.parallel false

# Keep the project source code from NAUTOBOT_ROOT
COPY pyproject.toml poetry.lock /source/
COPY examples /source/examples
WORKDIR /source

# -------------------------------------------------------------------------------------
# Install Nautobot requirements
# -------------------------------------------------------------------------------------
# During image build process, only Nautobot's requirements are installed.
#
# Local source code is mounted as volume into container. This approach does not require
# to rebuild a container when source code change occurs.
# -------------------------------------------------------------------------------------
RUN poetry install --no-root --no-ansi --extras mysql

# Generate required dirs and self signed ssl certificates
RUN mkdir /opt/nautobot /prom_cache && openssl req -new -newkey rsa:4096 -days 365 -nodes -x509 -subj \
    '/C=US/ST=NY/L=NYC/O=Nautobot/CN=nautobot.local' \
    -keyout /opt/nautobot/nautobot.key -out /opt/nautobot/nautobot.crt

# Used if someone wants to override the entrypoint and provision a super user
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh

# TODO Use nautobot init to generate the same config for all use cases
COPY development/nautobot_config.py /opt/nautobot/nautobot_config.py

# Common docker entrypoint for migrations, superuser creations, etc.
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nautobot-server", "runserver", "0.0.0.0:8080", "--insecure"]

# Copy nautobot source and poetry info to container to reduce cache invalidations
COPY poetry.lock pyproject.toml README.md /source/
COPY nautobot /source/nautobot

# Build the whl for use in the final container and install for the dev container
RUN poetry build && \
    poetry install --no-ansi

################################ Stage: cleaninstall
# Build an image with required dependencies to pull the installation from
FROM base as cleaninstall

# hadolint ignore=DL3008
RUN apt-get update && apt-get install --no-install-recommends -y build-essential libssl-dev

# pyuwsgi doesn't support ssl so we build it from source
# https://github.com/nautobot/nautobot/issues/193
RUN pip install --no-cache-dir --no-binary=pyuwsgi pyuwsgi

COPY --from=dev /source/dist/*.whl /tmp

RUN pip install --no-cache-dir /tmp/nautobot*.whl

################################ Stage: final
# This image will be the production ready image
FROM base as final
ARG PYTHON_VER

# Make sure we don't run as a root user
RUN useradd --system --shell /bin/bash --create-home --home-dir /opt/nautobot nautobot

# Copy from base the required python libraries and binaries
COPY --from=cleaninstall /usr/local/lib/python${PYTHON_VER}/site-packages /usr/local/lib/python${PYTHON_VER}/site-packages
COPY --from=cleaninstall /usr/local/bin /usr/local/bin

# Setup the entrypoint
COPY docker/docker-entrypoint.sh /docker-entrypoint.sh

# Copy SSL certs after the directory exists
COPY --from=dev /opt/nautobot/nautobot.key /opt/nautobot/nautobot.crt /opt/nautobot/

# Configure uWSGI
COPY docker/uwsgi.ini /opt/nautobot
COPY docker/nautobot_config.append.py /opt/nautobot

# Make sure everything under /opt/nautobot is owned by nautobot
RUN mkdir /prom_cache && chown -R nautobot:nautobot /opt/nautobot /prom_cache

USER nautobot

WORKDIR /opt/nautobot

RUN nautobot-server init && \
    cat /opt/nautobot/nautobot_config.append.py >> /opt/nautobot/nautobot_config.py && \
    rm -f /opt/nautobot/nautobot_config.append.py

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nautobot-server", "start", "--ini", "/opt/nautobot/uwsgi.ini"]

################################ Stage: final-dev
# This image will contain the development dependencies (including poetry) as well as nautobot installed
# as a system package
FROM dev as final-dev

# Nautobot was installed in editable mode so reinstall as a system package (all dependencies are already there)
RUN pip install --force-reinstall --no-deps --no-cache-dir /source/dist/*.whl && \
    rm -rf /source
