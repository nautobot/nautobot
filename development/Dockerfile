ARG PYTHON_VER=3.7
FROM python:${PYTHON_VER}

ENV PYTHONUNBUFFERED 1

# -------------------------------------------------------------------------------------
# Install Nautobot requirements
# -------------------------------------------------------------------------------------
# During image build process, only Nautobot's requirements are installed.
#
# Local source code is mounted as volume into container. This approach does not require
# to rebuild a container when source code change occurs.
# -------------------------------------------------------------------------------------

RUN pip install --upgrade pip

# Used if someone wants to override the entrypoint and provision a super user
COPY development/docker-entrypoint.sh /tmp/nautobot/docker-entrypoint.sh

COPY . /tmp/src
WORKDIR /tmp/src

# Install Nautobot as an "editable" package so that `nautobot-server` becomes available and changes can be immediately reflected during development.
RUN pip install --editable .
RUN pip install -r requirements-dev.txt

WORKDIR /opt/nautobot

ENTRYPOINT ["/tmp/nautobot/docker-entrypoint.sh"]
