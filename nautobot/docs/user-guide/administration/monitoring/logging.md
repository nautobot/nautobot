# Logging

Nautobot uses Python's standard `logging` module, configured via Django's [`LOGGING`](https://docs.djangoproject.com/en/stable/topics/logging/) dictionary. By default, every Nautobot process writes to the standard streams of the container or service, where your platform collects them.

For Job-specific logging (the `self.logger.*` API surfaced in the Job Result UI), see [Job Logging](../../../development/jobs/job-logging.md).

## Configuration

The defaults are defined in [`nautobot/core/settings.py`](https://github.com/nautobot/nautobot/blob/develop/nautobot/core/settings.py) and are driven by two environment variables:

| Variable | Default | Effect |
|---|---|---|
| `NAUTOBOT_DEBUG` | `False` | Drives the default log level (`DEBUG` if true, `INFO` otherwise) and the formatter (verbose vs. compact). **Always `False` in production.** |
| `NAUTOBOT_LOG_DEPRECATION_WARNINGS` | `False` | When true, deprecation warnings raised by Nautobot are also logged at `WARNING` level. Useful when planning a major upgrade; noisy at steady state. Must be set as an environment variable — not in `nautobot_config.py`. |

For full configuration options, including [`SANITIZER_PATTERNS`](../configuration/settings.md#sanitizer_patterns) for redaction of credentials in Job log entries, see [Configuration Settings](../configuration/settings.md).

### Switching to JSON output

Most modern log aggregators prefer JSON. Override `LOGGING` in `nautobot_config.py` after Nautobot's defaults are loaded:

```python
import logging.config

LOGGING["formatters"]["json"] = {
    "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
    "format": "%(asctime)s %(levelname)s %(name)s %(message)s %(funcName)s %(filename)s %(lineno)d",
}
LOGGING["handlers"]["json_console"] = {
    "class": "logging.StreamHandler",
    "formatter": "json",
}
for logger_name in ("django", "nautobot"):
    LOGGING["loggers"][logger_name]["handlers"] = ["json_console"]

logging.config.dictConfig(LOGGING)
```

Add `python-json-logger` to your image. Output then carries `name` (logger), `levelname`, `message`, and other fields that your aggregator parses automatically.

### Reading the logger name in your aggregator

Nautobot **always emits the logger name** — both formatters above include `%(name)s` (or the JSON `name` field). The question is just whether your aggregator sees it as a structured field it can pivot on, or as plain text inside the line body.

In the default text format, the logger name is right there in the line (`14:32:15.123 INFO    nautobot.extras.jobs : ...`) — searchable with `grep`, but not directly filterable as `logger="..."`. To make it a queryable field, pick one of the two approaches below.

**Switch to JSON output** (recommended — see above). Each line becomes one JSON object with `name`, `levelname`, and `message` as fields. In Loki:

```logql
{app="nautobot"} | json | name="nautobot.extras.jobs" | levelname="ERROR"
{app="nautobot"} | json | name=~"nautobot\\.extras\\..*" | levelname=~"ERROR|CRITICAL"
```

Splunk SPL, Elastic KQL, and Datadog log search use the same idea — extract once, filter on a field. Keep `name` as a field rather than promoting it to a label, since logger names like `nautobot.jobs.<module>` can have high cardinality.

**Parse the default text format on ingest** when you can't change Nautobot's `LOGGING`. A Promtail / Alloy pipeline that turns the default `"<time> <level>  <logger> :\n  <message>"` shape into structured fields:

```yaml
pipeline_stages:
  - multiline:
      firstline: '^\d{2}:\d{2}:\d{2}\.\d{3}'
      max_lines: 200
  - regex:
      expression: '^(?P<time>\d{2}:\d{2}:\d{2}\.\d{3})\s+(?P<level>\S+)\s+(?P<logger>\S+)\s+:\s*\n?\s*(?P<msg>.*)$'
  - labels:
      level:
  - structured_metadata:
      logger:
```

The same approach works in Vector and Fluent Bit — the regex is the load-bearing part.

## Forwarding to remote collectors

The default path — write to stdout, let your platform's log-collector sidecar ship the lines — is the recommended one and is orthogonal to Nautobot configuration. The recipes below cover the cases where Nautobot itself has to push logs to a remote endpoint: no sidecar is available, or you want a specific subset of records (auth, job lifecycle) on a dedicated channel.

### Remote syslog from `LOGGING`

Add a `SysLogHandler` to `nautobot_config.py` and route the loggers you care about to it. The example below ships everything Nautobot and Django log to a remote syslog receiver on UDP 514; swap `socktype` for `socket.SOCK_STREAM` to use TCP.

```python
import logging.config
import socket
from logging.handlers import SysLogHandler

LOGGING["handlers"]["remote_syslog"] = {
    "class": "logging.handlers.SysLogHandler",
    "address": ("logs.example.com", 514),
    "socktype": socket.SOCK_DGRAM,
    "facility": SysLogHandler.LOG_LOCAL0,
    "formatter": "normal",   # or "json" if you defined one above
}
for logger_name in ("django", "nautobot"):
    LOGGING["loggers"][logger_name]["handlers"].append("remote_syslog")

logging.config.dictConfig(LOGGING)
```

Keep the existing `console` handler alongside so container stdout is still captured — `SysLogHandler` is best-effort, and a temporary network blip will silently drop records.

### Splunk

Splunk accepts syslog directly on a configured input — point the handler above at that receiver, or at an intermediary that re-emits to Splunk. **HEC (HTTP Event Collector) is not configured inside Nautobot**: it terminates on a Splunk forwarder or load balancer in front of the indexer, not on a Python logging handler. If your platform team requires HEC end-to-end, that intermediary is a deployment concern outside the scope of this page.

### Redis and other event streams

For shipping **structured business or security events** (record changes, user events, job lifecycle) rather than raw log lines, use the [Event Notifications](../../platform-functionality/events.md) system instead of `LOGGING`. The bundled `RedisEventBroker` publishes each event to Redis Pub/Sub under its topic name — register it in `nautobot_config.py` the same way as `SyslogEventBroker`:

```python
from nautobot.core.events import register_event_broker, RedisEventBroker

register_event_broker(RedisEventBroker(url="redis://events.example.com:6379/0"))
```

Other event-stream targets — Kafka, NATS, RabbitMQ — are reachable through the same extension point: subclass `nautobot.core.events.EventBroker` and register your implementation. The topics and payload shapes are stable across brokers; only the publish mechanics change. Prefer this path over piping log lines into an event bus, since log text is line-oriented and unstructured while event payloads carry typed JSON.

## Log streams

| Stream | Source process | Where it lands by default | What it carries |
|---|---|---|---|
| Web | `nautobot-server` (uWSGI / gunicorn) | `stdout`/`stderr` of the web container | Django request handling, REST API, GraphQL, authentication, ORM warnings |
| Celery worker | `nautobot-server celery worker` | `stdout`/`stderr` of the worker container | Celery task lifecycle, broker connect/reconnect, Job log records (also persisted to the database) |
| Celery Beat | `nautobot-server celery beat` | `stdout`/`stderr` of the Beat container | Scheduler startup, scheduled-Job firing, schedule disable events |
| `JobLogEntry` (database) | `NautobotDatabaseHandler` | `extras_joblogentry` table → Job Result UI | Per-Job structured records: level, message, grouping, associated object |
| `ObjectChange` (database) | model signals | `extras_objectchange` table → Change Log UI | User CRUD on data — *not* operational |

Ship the **container `stdout`** of the web, worker, and Beat processes to your aggregator. The database-backed Job log and Change Log are intended for end-users; do not mirror them to your SIEM unless you have a specific reason.

### Streaming event notifications to logs

Nautobot's [Event Notifications](../../platform-functionality/events.md) system publishes record-change and Job lifecycle topics to pluggable brokers. Registering `SyslogEventBroker` in `nautobot_config.py` emits each event through Python logging under `nautobot.events.<topic>` with a JSON payload — the same pipeline that already ships your operational logs will pick it up. Use this when you want structured Nautobot events in the same aggregator as everything else, without standing up a separate Redis Pub/Sub consumer.

The two topic groups that most deployments will care about:

- **[User Events](../../platform-functionality/events.md#user-events)** (`nautobot.users.user.login`, `…logout`, `…change_password`, `nautobot.admin.user.change_password`) — the audit signal your SIEM or compliance team needs. Payloads carry the affected user record; emit these to satisfy login/logout and password-change tracking requirements that text-grepping `nautobot.auth.*` would otherwise have to approximate.
- **[Job Events](../../platform-functionality/events.md#job-events)** (`nautobot.jobs.job.started`, `…completed`) — a structured "did automation actually run" signal. Payloads carry `job_result_id`, `job_name`, `user_name`, and (on completion) `job_output` and `einfo` (stacktrace on failure). Prefer this over scraping `nautobot.extras.jobs` log lines when an external system needs to react to job lifecycle.

## Logger namespace map

Loggers in Nautobot are named by Python module (`logging.getLogger(__name__)`). When building alert rules in your aggregator, **filter on logger name plus level** rather than free-text grep — it eliminates routine warnings that would otherwise bury real failures.

| Subsystem | Logger name(s) |
|---|---|
| Authentication | `nautobot.auth.login`, `nautobot.auth.logout` |
| REST API | `nautobot.core.api.serializers`, `nautobot.core.api.fields`, `nautobot.core.api.mixins` |
| GraphQL | `nautobot.core.graphql.schema` |
| Celery / Beat scheduler | `nautobot.core.celery`, `nautobot.core.celery.schedulers` |
| Jobs framework | `nautobot.extras.jobs` |
| Apps (plugins) loading | `nautobot.extras.plugins`, `nautobot.apps.config` |
| Git repository sync | `nautobot.core.utils.git` |
| Deprecations | `nautobot.core.utils.deprecation` |
| Job code (per Job) | `nautobot.jobs.<module>` (set by `get_task_logger(self.__module__)`) |

## Common failure patterns

!!! note "Living section"
    The patterns below are the ones we currently see most often in production deployments — they're a useful starting point, not an exhaustive catalogue, and we expect the list to grow as more operators share their experience. If you've hit a recurring pattern that isn't covered here, a docs contribution is very welcome.

The exact text of any individual log line is not part of Nautobot's API and may shift between releases. Treat the patterns below as alerting starting points — and prefer the metric-based or probe-based equivalents listed in [Alerting](./alerting.md) where one exists.

### Database connectivity and capacity

Surfaces through Django's `db.backends` logger and Python's stdlib `OperationalError`/`ProgrammingError` propagation. Note that Nautobot intentionally suppresses database errors during config bootstrap, so the *first* sign of a database problem is usually a 500 traceback from a request, not a friendly message.

- `OperationalError: could not connect to server` — PostgreSQL unreachable
- `OperationalError: FATAL: too many connections for role` — pool exhausted
- `psycopg2.errors.DeadlockDetected`, `LockNotAvailable` — contention
- `django.db.utils.InterfaceError: connection already closed` — typically after worker fork or stale `CONN_MAX_AGE`

!!! tip
    If you see `too many connections`, check the connection pooler before Nautobot — see [Backing Stores — PostgreSQL connection topology](./backing-stores.md#connection-topology).

### Job execution failures

Job results carry both a Celery task status and an application log level — see the [`JobResult`](../../platform-functionality/jobs/models.md#job-results) model. The Celery statuses are `PENDING`, `RECEIVED`, `STARTED`, `SUCCESS`, `FAILURE`, `RETRY`, `REVOKED`, `IGNORED`, `REJECTED`.

Representative log lines from `nautobot.extras.jobs`:

```text
Job <name> is not enabled to be run!
Job <name> is a singleton and already running.
The hard time limit ... is less than or equal to the soft time limit ...
JobHook <name> is enabled, but the underlying Job implementation is missing
```

And from `nautobot.core.celery.schedulers`:

```text
Removing schedule <name> for argument deserialization error
Disabling schedule <name> that was removed from database
Disabling schedule <name> with missing user
```

Prefer the metric `nautobot_worker_finished_jobs{status="FAILURE"}` (and `nautobot_worker_exception_jobs{exception=...}`) over text matching — see [Prometheus Metrics](./prometheus-metrics.md).

### Celery worker and broker

```text
consumer: Cannot connect to redis://...: Connection refused.
Trying again in N.NN seconds... (M/M)              # one or two during a Redis restart is normal
WorkerLostError: Worker exited prematurely: signal 9 (SIGKILL)
MissingHeartbeatException
No celery workers running on queue <name>          # web logs this when inspect-ping fails (1 s timeout)
```

For Celery-specific reliability tuning and the visibility-timeout pitfall, see [Celery and Jobs](./celery-jobs.md).

### App initialization (plugins)

Apps register at startup. Hard failures crash the process loudly (Django dies on import); soft failures are logged from `nautobot.extras.plugins`:

```text
ERROR  - There was a conflict with filter set field <name>...
ERROR  - There was a name conflict with existing table column <name>...
WARN   - <plugin> table extension is missing default_columns attribute
```

Scope app-startup alerts to `logger:nautobot.extras.plugins AND level:ERROR` to avoid the cosmetic `default_columns` warning.

### Git repository sync

Triggered by the **Git Repositories** sync action — runs as a Job, so most output flows through `JobLogEntry`. The underlying utility logs to `nautobot.core.utils.git`:

```text
Branch <name> does not exist at <url>. <git_error>
```

## Known noise — do not alert on these

!!! note "Living section"
    This list captures the routine messages we've observed in healthy deployments so far. It will grow over time as more deployments report back; if a message keeps showing up in your environment without a real underlying issue, it's a good candidate to add here.

Some messages appear routinely in healthy deployments and should be excluded from alert rules:

| Message / pattern | Why it's benign |
|---|---|
| `Cannot export Prometheus metrics from worker, no available ports in range.` | Worker-level metrics export is best-effort; web `/metrics` is unaffected. |
| `Deleting unmanaged (leftover?) Git repository clone at ...` | Cleanup of stale `GIT_ROOT` clones; expected after repository removal. |
| `Substantial drift from celery@...` (Celery library) | Single occurrences during worker restart. Alert only on sustained drift. |
| Deprecation warnings (when `LOG_DEPRECATION_WARNINGS=True`) | Pre-upgrade signal only — leave **off** in steady-state production. |
| `Unable to find peer model ... to create GraphQL relationship` | An app declares a GraphQL relation to a model not installed in this deployment. |
| `<plugin> table extension is missing default_columns attribute` | Cosmetic — the app author should fix it, but the UI works. |

!!! tip
    A useful rule of thumb: if a message appears in a healthy deployment more than once an hour, it belongs in this list — not in your alert ruleset. Anchoring queries on logger name (e.g. `logger:nautobot.extras.jobs`) plus level rather than free-text grep dramatically cuts this noise.
