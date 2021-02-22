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

# Install Poetry manually from GitHub because otherwise it installs its own
# dependencies globally which may conflict with ours.
# https://python-poetry.org/docs/#osx-linux-bashonwindows-install-instructions
RUN curl -sSL https://raw.githubusercontent.com/python-poetry/poetry/master/get-poetry.py | python -

# Modify the PATH here because otherwise poetry fails 100% of the time. WAT??
ENV PATH="${PATH}:/root/.poetry/bin"

# Poetry shouldn't create a venv as we want global install
RUN poetry config virtualenvs.create false

# Used if someone wants to override the entrypoint and provision a super user
COPY development/docker-entrypoint.sh /tmp/nautobot/docker-entrypoint.sh

COPY . /tmp/src
WORKDIR /tmp/src

RUN poetry install

WORKDIR /opt/nautobot

ENTRYPOINT ["/tmp/nautobot/docker-entrypoint.sh"]
