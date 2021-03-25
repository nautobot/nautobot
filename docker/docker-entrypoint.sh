#!/bin/bash
# Runs on every start of the Nautobot Docker container

# Stop when an error occures
set -e

# Try to connect to the DB
DB_WAIT_TIMEOUT=${DB_WAIT_TIMEOUT-3}
MAX_DB_WAIT_TIME=${MAX_DB_WAIT_TIME-30}
CUR_DB_WAIT_TIME=0
while ! nautobot-server migrate 2>&1 && [ "${CUR_DB_WAIT_TIME}" -lt "${MAX_DB_WAIT_TIME}" ]; do
  echo "⏳ Waiting on DB... (${CUR_DB_WAIT_TIME}s / ${MAX_DB_WAIT_TIME}s)"
  sleep "${DB_WAIT_TIMEOUT}"
  CUR_DB_WAIT_TIME=$(( CUR_DB_WAIT_TIME + DB_WAIT_TIMEOUT ))
done
if [ "${CUR_DB_WAIT_TIME}" -ge "${MAX_DB_WAIT_TIME}" ]; then
  echo "❌ Waited ${MAX_DB_WAIT_TIME}s or more for the DB to become ready."
  exit 1
fi

# Collect Static files (still required for uwsgi static files)
nautobot-server collectstatic --no-input

# Create Superuser if required
if [ "$CREATE_SUPERUSER" == "true" ]; then
  if [ -z ${SUPERUSER_NAME+x} ]; then
    SUPERUSER_NAME='admin'
  fi
  if [ -z ${SUPERUSER_EMAIL+x} ]; then
    SUPERUSER_EMAIL='admin@example.com'
  fi
  if [ -f "/run/secrets/superuser_password" ]; then
    SUPERUSER_PASSWORD="$(< /run/secrets/superuser_password)"
  elif [ -z ${SUPERUSER_PASSWORD+x} ]; then
    echo "❌ SUPERUSER_PASSWORD is required to be defined when creating superuser"
    exit 1
  fi
  if [ -f "/run/secrets/superuser_api_token" ]; then
    SUPERUSER_API_TOKEN="$(< /run/secrets/superuser_api_token)"
  elif [ -z ${SUPERUSER_API_TOKEN+x} ]; then
    echo "❌ SUPERUSER_API_TOKEN is required to be defined when creating superuser"
    exit 1
  fi

  nautobot-server shell --interface python << END
from django.contrib.auth import get_user_model
from nautobot.users.models import Token
u = get_user_model().objects.filter(username='${SUPERUSER_NAME}')
if not u:
    u=get_user_model().objects.create_superuser('${SUPERUSER_NAME}', '${SUPERUSER_EMAIL}', '${SUPERUSER_PASSWORD}')
    Token.objects.create(user=u, key='${SUPERUSER_API_TOKEN}')
else:
    u = u[0]
    if u.email != '${SUPERUSER_EMAIL}':
        u.email = '${SUPERUSER_EMAIL}'
    if not u.check_password('${SUPERUSER_PASSOWRD}'):
        u.set_password('${SUPERUSER_PASSWORD}')
    u.save()
    t = Token.objects.filter(user=u)
    if t:
        t = t[0]
        if t.key != '${SUPERUSER_API_TOKEN}':
            t.key = '${SUPERUSER_API_TOKEN}'
            t.save()
END

  echo "💡 Superuser Username: ${SUPERUSER_NAME}, E-Mail: ${SUPERUSER_EMAIL}"
fi

if [ "$NAUTOBOT_UWSGI_PROCESSES" == "true" ]; then
  sed -i "s@.*processes = .*\$@processes = $NAUTOBOT_UWSGI_PROCESSES@" /opt/nautobot/uwsgi.ini
fi


# Launch whatever is passed by docker
# (i.e. the RUN instruction in the Dockerfile)
#
# shellcheck disable=SC2068
exec $@
