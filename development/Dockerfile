ARG PYTHON_VER=3.7
FROM python:${PYTHON_VER}

ENV PYTHONUNBUFFERED 1

# -------------------------------------------------------------------------------------
# Install NetBox requirements
# -------------------------------------------------------------------------------------
# During image build process, only NetBox's requirements are installed.
#
# Local source code is mounted as volume into container. This approach does not require
# to rebuild a container when source code change occurs.
# -------------------------------------------------------------------------------------

RUN pip install --upgrade pip

COPY requirements.txt /tmp/
RUN pip install -r /tmp/requirements.txt

COPY requirements_dev.txt /tmp/
RUN pip install -r /tmp/requirements_dev.txt

COPY development/docker-entrypoint.sh /tmp/grimlock/docker-entrypoint.sh

ENTRYPOINT [ "/tmp/grimlock/docker-entrypoint.sh" ]