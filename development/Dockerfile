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

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY requirements_dev.txt /tmp/
RUN pip install -r /tmp/requirements_dev.txt

# Used if someone wants to override the entrypoint and provision a super user
COPY development/docker-entrypoint.sh /tmp/nautobot/docker-entrypoint.sh

WORKDIR /opt/nautobot

ENTRYPOINT ["/tmp/nautobot/docker-entrypoint.sh"]
