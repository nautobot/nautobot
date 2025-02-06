# Nautobot Health Checks

In a production deployment of Nautobot, you'll want health checks (also termed liveness checks, readiness checks, etc.) for each distinct component of the Nautobot system, to be able to detect if any component fails and ideally respond automatically. While this topic can be (and is) the subject of multiple books, this document attempts to provide some basic "best practices" guidelines. If you're deploying Nautobot as part of a larger enterprise system, of course you'll want to follow your organization's experts and their guidance, but if you're "on your own", you can do worse than starting here.

## Health Check Approaches

In general the following commands or HTTP requests can serve as health checks for the various components of a Nautobot system.

### Nautobot HTTP Server

In addition to simply monitoring the existence of the `nautobot-server` process ID, two more in-depth approaches are possible here.

An HTTP `GET` request to `<server>/health/` should return an HTTP `200 OK` response so long as:

- the server is running
- and the server can connect to the database
- and all Django migrations have been applied (check added in Nautobot 2.2)
- and the server can connect to Redis
- and the server can write to an appropriate location on the filesystem
- and the server is not too busy handling other requests to respond to this request.

Similarly, but not identically, the CLI command `nautobot-server health_check` should run and return an exit code of `0` (success) so long as:

- the command can connect to the database
- and all Django migrations have been applied (check added in Nautobot 2.2)
- and the command can connect to Redis
- and the command can write to an appropriate location on the filesystem

Note the differences between these two. In some situations you'll want to use both for different types of checks. More on this later in this document.

??? info "Background information"
    Nautobot uses the [django-health-check](https://github.com/KristianOellegaard/django-health-check) project and some custom health checks (database connection and cache availability). Additional health checks are available as part of that  project and can be added to the [`EXTRA_INSTALLED_APPS`](../configuration/settings.md#extra-applications) configuration variable as desired.

### Nautobot Celery Worker

In addition to monitoring the existence of a given Celery worker process ID, you can use the fact that Celery provides a [`celery inspect ping` CLI command](https://docs.celeryq.dev/en/stable/reference/cli.html#celery-inspect) that sends a short message to a given Celery worker(s) and reports back on whether it receives a response(s). Nautobot wraps this with the `nautobot-server` CLI command, so in general you can run `nautobot-server celery inspect ping --destination <worker name>` to confirm whether a given worker is able to receive and respond to Celery control messages.

!!! tip
    A Celery worker's name defaults to `celery@$HOSTNAME`, but you can override it by starting the worker with the `-n <name>` argument if needed.

### Nautobot Celery Beat

In addition to monitoring the Celery Beat process ID, you can use the fact that Nautobot's custom Celery Beat scheduler respects the [`CELERY_BEAT_HEARTBEAT_FILE`](../configuration/settings.md#celery_beat_heartbeat_file) configuration setting, which specifies a filesystem path that will be repeatedly [`touch`ed](https://en.wikipedia.org/wiki/Touch_(command)) to update its last-modified timestamp so long as the scheduler is running. You can check this timestamp against the current system time to detect whether the Celery Beat scheduler is firing as expected. One way is using the `find` command with it's `-mmin` parameter, and checking whether it finds the expected file with a recent enough modification time (here, 0.1 minutes, or 6 seconds) or not:

```shell
[ $(find $NAUTOBOT_CELERY_BEAT_HEARTBEAT_FILE -mmin -0.1 | wc -l) -eq 1 ] || false
```

### Databases

#### PostgreSQL

PostgreSQL provides the [`pg_isready` CLI command](https://www.postgresql.org/docs/current/app-pg-isready.html) to check whether the database server is running and accepting connections.

#### MySQL

While MySQL provides the [`mysqladmin ping` CLI command](https://dev.mysql.com/doc/refman/8.0/en/mysqladmin.html), it's important to note that this command only checks whether the database server is running - it still exits with return code `0` if the server is running but not accepting connections. Therefore you might in some cases wish to run a command that actually connects to the database, such as `mysql --execute "SHOW DATABASES;"`.

### Redis

Redis provides the [`redis-cli ping` CLI command](https://redis.io/commands/ping/) for detecting whether the Redis server is alive. It will output `PONG` on success and exit with return code `0`. Note though that it may also exit with code `0` in cases where the server has started but is not yet ready to receive or serve data.

!!! tip
    If you have the Redis server configured to require a password, you will need to set the `REDISCLI_AUTH` environment variable to this password before `redis-cli ping` will be successful.

## Deployments with systemd

For systemd deployments, the underlying services of PostgreSQL/MySQL and Redis integrate natively with systemd's `sd_notify` API to provide additional status information to the system, and `uwsgi` does as well. We recommend following the standard deployment patterns provided by your OS for PostgreSQL/MySQL and Redis. For the Nautobot service and Celery/Beat services, follow the Nautobot installation documentation at [Setup systemd](../installation/services.md#setup-systemd).

## Kubernetes Deployments

Kubernetes (k8s) distinguishes between "startup", "readiness", and "liveness" probes. In brief:

- Startup probes detect whether a container has finished starting up.
- Readiness probes detect whether a container is ready to accept traffic.
- Liveness probes detect whether a container needs to be restarted.

For more details, refer to the [Kubernetes documentation](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/). A working example can be found in the [Nautobot Helm charts](https://github.com/nautobot/helm-charts) repository.

### Nautobot Server Container in k8s

For the Nautobot web server, you'll probably want to use `nautobot-server health_check` as a liveness probe (since it won't fail if the Nautobot server is too busy handling many HTTP requests, unlike the `/health/` endpoint) and use an HTTP request to `/health/` as a startup probe and a readiness probe (since it won't report success unless the Nautobot server is running and responding to HTTP requests). For example:

```yaml
startupProbe:
  httpGet:
    path: "/health/"
    port: "http"
  periodSeconds: 10
  failureThreshold: 30

readinessProbe:
  httpGet:
    path: "/health/"
    port: "http"
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

livenessProbe:
  exec:
    command:
      - "nautobot-server"
      - "health_check"
  periodSeconds: 10
  timeoutSeconds: 10  # the CLI command takes a few seconds to start up
  failureThreshold: 3
```

### Celery Worker Container in k8s

The Celery worker container can use `nautobot-server celery inspect ping` for both liveness and readiness probes:

```yaml
readinessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "nautobot-server celery inspect ping --destination celery@$HOSTNAME"
  periodSeconds: 60
  timeoutSeconds: 10
  failureThreshold: 3

livenessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "nautobot-server celery inspect ping --destination celery@$HOSTNAME"
  periodSeconds: 60
  timeoutSeconds: 10
  failureThreshold: 3
```

### Celery Beat Container in k8s

The Celery Beat container doesn't need a readiness probe, but can benefit from a liveness probe:

```yaml
livenessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "[ $(find $NAUTOBOT_CELERY_BEAT_HEARTBEAT_FILE -mmin -0.1 | wc -l) -eq 1 ] || false"
  initialDelaySeconds: 30
  periodSeconds: 5
  timeoutSeconds: 5
  failureThreshold: 3
```

### Redis Container in k8s

```yaml
readinessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "redis-cli -h localhost ping | grep PONG"
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

livenessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "redis-cli -h localhost ping"
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### PostgreSQL Container in k8s

```yaml
readinessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "pg_isready -d $POSTGRES_DB -U $POSTGRES_USER"
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

livenessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "pg_isready -d $POSTGRES_DB -U $POSTGRES_USER"
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### MySQL Container in k8s

```yaml
readinessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - 'mysql -u $MYSQL_USER --password=$MYSQL_PASSWORD -h localhost --execute "SHOW DATABASES;"'
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

livenessProbe:
  exec:
    command:
      - "/bin/bash"
      - "-c"
      - "mysqladmin -u $MYSQL_USER --password=$MYSQL_PASSWORD -h localhost ping"
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

## Docker Compose Deployments

Docker Compose supports a single `healthcheck` for each container.

### Nautobot Server Container in Docker Compose

We recommend the CLI-based health-check rather than the HTTP health-check here because the former will not fail when all request-handler workers are busy.

```yaml
healthcheck:
  interval: 10s
  timeout: 10s
  start_period: 5m  # in Nautobot 2.2 and later, this won't report success until all migrations have run
  retries: 3
  test: "nautobot-server health_check"
```

### Celery Worker Container in Docker Compose

```yaml
healthcheck:
  interval: 60s
  timeout: 10s
  start_period: 30s
  retries: 3
  test: "nautobot-server celery inspect ping --destination celery@$$HOSTNAME"
```

### Celery Beat Container in Docker Compose

```yaml
healthcheck:
  interval: 5s
  timeout: 5s
  start_period: 30s
  retries: 3
  test: '[ "$$(find /tmp/nautobot_celery_beat_heartbeat -mmin -0.1 | wc -l)" != "" ] || false'
```

### Redis Container in Docker Compose

```yaml
healthcheck:
  interval: 10s
  timeout: 5s
  retries: 3
  test: "redis-cli -h localhost ping | grep PONG"
```

!!! tip
    If you have the Redis server configured to require a password, you will need to set the `REDISCLI_AUTH` environment variable to this password before `redis-cli ping` will be successful.

### PostgreSQL Container in Docker Compose

```yaml
healthcheck:
  interval: 10s
  timeout: 5s
  start_period: 30s
  retries: 3
  test: "pg_isready -d $$POSTGRES_DB -U $$POSTGRES_USER"
```

### MySQL Container in Docker Compose

```yaml
healthcheck:
  interval: 10s
  timeout: 5s
  start_period: 30s
  retries: 3
  test: 'mysql -h localhost -u $$MYSQL_USER --password=$$MYSQL_PASSWORD --execute "SHOW DATABASES;"'
```
