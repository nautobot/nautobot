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
# Poetry 1.1.0 added parallel installation as an option;
# unfortunately it seems to have some issues with installing/updating "requests" and "certifi"
# while simultaneously atttempting to *use* those packages to install other packages.
# For now we disable it.
RUN poetry config installer.parallel false

# Used if someone wants to override the entrypoint and provision a super user
COPY development/docker-entrypoint.sh /tmp/nautobot/docker-entrypoint.sh

COPY pyproject.toml poetry.lock /opt/nautobot/
WORKDIR /opt/nautobot

RUN poetry install --no-root

COPY . /opt/nautobot

RUN poetry install

# Install additional requirements from local_requirements.txt
RUN if [ -f local_requirements.txt ] ; then cat local_requirements.txt | grep -E '^[^# ]' | cut -d= -f1 | xargs -n 1 poetry add ; fi


ENTRYPOINT ["/tmp/nautobot/docker-entrypoint.sh"]
