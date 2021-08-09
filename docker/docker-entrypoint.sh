#!/bin/bash
# Runs on every start of the Nautobot Docker container

# Stop when an error occures
set -e

# Try to connect to the DB
DB_WAIT_TIMEOUT=${DB_WAIT_TIMEOUT-3}
MAX_DB_WAIT_TIME=${MAX_DB_WAIT_TIME-30}
CUR_DB_WAIT_TIME=0
if [ ! "$NAUTOBOT_DOCKER_SKIP_INIT" ]; then
  while ! nautobot-server post_upgrade --no-invalidate-all 2>&1 && [ "${CUR_DB_WAIT_TIME}" -lt "${MAX_DB_WAIT_TIME}" ]; do
    echo "⏳ Waiting on DB... (${CUR_DB_WAIT_TIME}s / ${MAX_DB_WAIT_TIME}s)"
    sleep "${DB_WAIT_TIMEOUT}"
    CUR_DB_WAIT_TIME=$(( CUR_DB_WAIT_TIME + DB_WAIT_TIMEOUT ))
  done
  if [ "${CUR_DB_WAIT_TIME}" -ge "${MAX_DB_WAIT_TIME}" ]; then
    echo "❌ Waited ${MAX_DB_WAIT_TIME}s or more for the DB to become ready."
    exit 1
  fi
fi

# Run a quick healthcheck and bail if something fails, --deploy will warn on potential issues for production
echo "⏳ Running initial systems check..."
nautobot-server check --deploy
RC=$?
if [[ $RC != 0 ]]; then
	echo -e "❌ Nautobot systems check failed!"
	exit $RC
fi

# Create Superuser if required
if [ "$NAUTOBOT_CREATE_SUPERUSER" == "true" ]; then
  if [ -z ${NAUTOBOT_SUPERUSER_NAME+x} ]; then
    NAUTOBOT_SUPERUSER_NAME='admin'
  fi
  if [ -z ${NAUTOBOT_SUPERUSER_EMAIL+x} ]; then
    NAUTOBOT_SUPERUSER_EMAIL='admin@example.com'
  fi
  if [ -f "/run/secrets/superuser_password" ]; then
    NAUTOBOT_SUPERUSER_PASSWORD="$(< /run/secrets/superuser_password)"
  elif [ -z ${NAUTOBOT_SUPERUSER_PASSWORD+x} ]; then
    echo "❌ NAUTOBOT_SUPERUSER_PASSWORD is required to be defined when creating superuser"
    exit 1
  fi
  if [ -f "/run/secrets/superuser_api_token" ]; then
    NAUTOBOT_SUPERUSER_API_TOKEN="$(< /run/secrets/superuser_api_token)"
  elif [ -z ${NAUTOBOT_SUPERUSER_API_TOKEN+x} ]; then
    echo "❌ NAUTOBOT_SUPERUSER_API_TOKEN is required to be defined when creating superuser"
    exit 1
  fi

  nautobot-server shell --interface python << END
from django.contrib.auth import get_user_model
from nautobot.users.models import Token
u = get_user_model().objects.filter(username='${NAUTOBOT_SUPERUSER_NAME}')
if not u:
    u=get_user_model().objects.create_superuser('${NAUTOBOT_SUPERUSER_NAME}', '${NAUTOBOT_SUPERUSER_EMAIL}', '${NAUTOBOT_SUPERUSER_PASSWORD}')
    Token.objects.create(user=u, key='${NAUTOBOT_SUPERUSER_API_TOKEN}')
else:
    u = u[0]
    if u.email != '${NAUTOBOT_SUPERUSER_EMAIL}':
        u.email = '${NAUTOBOT_SUPERUSER_EMAIL}'
    if not u.check_password('${NAUTOBOT_SUPERUSER_PASSWORD}'):
        u.set_password('${NAUTOBOT_SUPERUSER_PASSWORD}')
    u.save()
    t = Token.objects.filter(user=u)
    if t:
        t = t[0]
        if t.key != '${NAUTOBOT_SUPERUSER_API_TOKEN}':
            t.key = '${NAUTOBOT_SUPERUSER_API_TOKEN}'
            t.save()
END

  echo "💡 Superuser Username: ${NAUTOBOT_SUPERUSER_NAME}, E-Mail: ${NAUTOBOT_SUPERUSER_EMAIL}"
fi

if [ "$NAUTOBOT_UWSGI_PROCESSES" ]; then
  sed -i "s@.*processes = .*\$@processes = $NAUTOBOT_UWSGI_PROCESSES@" /opt/nautobot/uwsgi.ini
fi

if [ "$NAUTOBOT_UWSGI_LISTEN" ]; then
  sed -i "s@.*listen = .*\$@listen = $NAUTOBOT_UWSGI_LISTEN@" /opt/nautobot/uwsgi.ini
fi

# Launch whatever is passed by docker
# (i.e. the RUN instruction in the Dockerfile)
#
# shellcheck disable=SC2068
exec $@
