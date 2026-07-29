# Reproducing the OTLP-gRPC + uWSGI + profiling worker segfault

This documents how to reproduce (and verify the fix for) the crash where uWSGI worker processes
segfault (SIGSEGV / "signal 11", surfacing as HTTP 502) when **all** of the following are true:

1. OpenTelemetry Django instrumentation is on (`OTEL_PYTHON_DJANGO_INSTRUMENT=True`).
2. The OTLP exporter uses **gRPC** (`OTEL_EXPORTER_OTLP_PROTOCOL=grpc`, the default) against an endpoint.
3. The server runs under **uWSGI pre-fork** (multiple workers), not the `runserver` dev server.
4. A request is **profiled by django-silk** (request profiling enabled).

## Why it crashes

`instrument()` used to build the OTLP gRPC exporter in the uWSGI **master** process, before uWSGI
forks its workers. gRPC's C-core spawns background polling threads and epoll fds when the channel is
constructed; after `fork()` those live only in the master, so each worker inherits a broken channel.
django-silk's cProfile hook then reaches into gRPC's C layer on the request path and the worker
segfaults. A live collector is not required - constructing the channel is enough to poison the fork.

The fix (`nautobot/core/cli/opentelemetry.py`) splits setup: `instrument()` installs the
auto-instrumentors + tracer provider pre-fork, and `install_exporters()` builds the OTLP exporters
**per worker after fork** (via the uWSGI postfork hook in `nautobot/core/wsgi.py` and the Celery
`worker_process_init` handler in `nautobot/core/celery/__init__.py`).

## Setup

1. Enable the observability stack and the repro override in your `invoke.yml` `compose_files`
   (order matters - the repro override must come last):

   ```yaml
   nautobot:
     compose_files:
       - "docker-compose.yml"
       - "docker-compose.postgres.yml"
       - "docker-compose.dev.yml"
       - "docker-compose.observability.yml"
       - "docker-compose.otel-segfault-repro.yml"
   ```

   `docker-compose.observability.yml` provides the `otel` collector (gRPC on `otel:4317`).
   `docker-compose.otel-segfault-repro.yml` runs the `nautobot` service under uWSGI and sets
   `OTEL_PYTHON_DJANGO_INSTRUMENT=True`. `development/dev.env` already supplies the endpoint/protocol.

2. Force django-silk to profile every request by adding to `development/nautobot_config.py`:

   ```python
   ALLOW_REQUEST_PROFILING = True  # hard setting; overrides the Constance default
   SILKY_INTERCEPT_FUNC = lambda request: request.path != "/health/"  # profile everything else
   ```

   (Alternatively, log in and toggle "Advanced Settings -> request profiling" in your user profile,
   which sets the per-session `silk_record_requests` flag.)

3. Rebuild and start:

   ```no-highlight
   invoke stop && invoke build && invoke start
   ```

## Run

```no-highlight
development/otel_segfault_repro.sh -n 24
```

The script fires N requests at `/api/status/` and reports HTTP 200 count + worker segfaults observed
(by grepping the `nautobot` container logs for `signal 11` / `SIGSEGV`). Exit 1 = reproduced, 0 = clean.

- **Expected on the unpatched build:** most requests fail and workers segfault (mirrors the ~23/24
  crash rate seen in the field).
- **Expected with the fix:** 24/24 HTTP 200, 0 segfaults, and spans still arrive in the collector
  (check Tempo/Grafana), proving the per-worker channel exports.

## Answering the two open questions

- **Does it still crash against a live collector?** The collector being up or down does not matter -
  channel construction poisons the fork either way. To confirm with nothing on 4317, stop the
  collector and re-run:

  ```no-highlight
  docker compose stop otel
  development/otel_segfault_repro.sh -n 24 --no-collector
  ```

- **Does `lazy-apps` avoid it?** With `--lazy-apps=true`, uWSGI loads the app per worker after fork.
  Restart the stack with `REPRO_LAZY_APPS=true` set for the `nautobot` service (the override honors
  it) and re-run:

  ```no-highlight
  REPRO_LAZY_APPS=true invoke stop && REPRO_LAZY_APPS=true invoke start
  development/otel_segfault_repro.sh -n 24 --lazy-apps
  ```

  Note: `lazy-apps` only helps because it moves app (and, with the fix, exporter) creation past the
  fork; it is not a substitute for the code fix, which is transport- and server-agnostic.
