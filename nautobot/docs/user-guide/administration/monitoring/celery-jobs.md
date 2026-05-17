# Celery and Jobs

Nautobot Jobs run as Celery tasks. This page covers the configuration knobs and the signals you need to properly monitor Jobs execution and alert on failures.

!!! note
    - For multi-queue worker deployments, see [Task Queues](../guides/celery-queues.md).
    - For per-Job logging from inside Job code, see [Job Logging](../../../development/jobs/job-logging.md).

## Queue Depth

The health checks and the log-based alerts will catch failures but they will not catch a slow-but-functional pipeline where producers outpace consumers. The only direct signal for that is queue depth — the silent backlog.

Two ways to measure on a Redis-backed Nautobot:

```bash
# Direct probe — each Celery queue is a Redis list
redis-cli LLEN celery
redis-cli LLEN priority
redis-cli LLEN $YOUR_CUSTOM_QUEUE
```

For Prometheus, deploy a `celery-exporter` — it exports `celery_queue_length{queue="..."}`. Scrape it, then:

```yaml
- alert: NautobotQueueBacklog
  expr: celery_queue_length{queue=~"celery|priority"} > 100
  for: 10m
  labels: {severity: ticket}
  annotations:
    summary: "Queue {{ $labels.queue }} is backlogged ({{ $value }} pending)"
```

The threshold is site-specific — tune to your steady state. Pair with a counter-rate alert (`rate(nautobot_worker_started_jobs[10m])` falling to zero while queue length is non-zero) to catch the case where workers have stopped consuming entirely.

## Job Execution Duration

Job runtime is the leading indicator for several of the failure modes covered elsewhere on this page. A Job class whose p99 runtime is trending up will, in order, push queue depth up (more workers tied up per unit of incoming work), increase the rate of `nautobot_worker_singleton_conflict` (the next scheduled invocation collides with one still running), and eventually hit Celery's hard / soft time limits or the Redis broker's visibility timeout. Watching runtime gives you a chance to act before any of those bite.

Nautobot's own `/metrics` exposes Job *counts* but not Job *durations*. Two complementary sources cover the duration question:

- **`celery-exporter`** — exposes `celery_task_runtime_seconds` as a Prometheus histogram, labeled by Celery task name. The right source for quantile time series and trend alerts. See [Visualization — Monitoring Job Execution Duration](./visualization.md#monitoring-job-execution-duration) for panel recipes.
- **Direct database query** against `extras_jobresult` — `date_done - created` gives the exact per-run duration. Useful when investigating a specific slow run rather than a trend.

When the trend has flagged a Job and you need to know *which stage* of its execution slowed down, the cleanest instrumentation is from inside the Job itself — `self.logger.info("…", extra={"stage": "validate", "elapsed_ms": elapsed})` markers land in your aggregator as queryable fields and break the runtime down without a code redeploy for each investigation. See [Make Each Line Pivotable in the Aggregator](#make-each-line-pivotable-in-the-aggregator) below for the full `extra=` pattern.

## Beat Schedule Drift

Nautobot's Celery Beat scheduler ([`NautobotDatabaseScheduler`](https://github.com/nautobot/nautobot/blob/develop/nautobot/core/celery/schedulers.py)) ticks every few seconds and fires `ScheduledJob` rows whose cron expression matches. If the scheduler process is killed mid-tick, blocked on the database, or generally slow, scheduled runs are missed and not backfilled — Beat does not have a "make-up runs" feature.

Two complementary detections:

1. **Heartbeat file** — already wired into the orchestrator probe described in [Health Checks — Nautobot Celery Beat](./health-checks.md#nautobot-celery-beat). Catches the case where Beat stops entirely.
2. **Per-schedule liveness** — query the [`ScheduledJob`](../../platform-functionality/jobs/job-scheduling-and-approvals.md) model for entries whose firing window has passed without a run. The natural place to do this is from inside a Nautobot Job, using the ORM:

    ```python
    from datetime import timedelta
    from django.utils import timezone
    from nautobot.extras.models import ScheduledJob

    threshold = timezone.now() - timedelta(minutes=5)
    stale = ScheduledJob.objects.filter(
        enabled=True,
        next_run_at__lt=threshold,
    ).values_list("name", "last_run_at", "next_run_at", "total_run_count")

    for name, last_run_at, next_run_at, total_run_count in stale:
        self.logger.warning(
            "Schedule %s missed its window (next_run_at=%s, last_run_at=%s, total_run_count=%d)",
            name, next_run_at, last_run_at, total_run_count,
        )
    ```

    Wrap that in a periodic Nautobot Job and the scheduler reports its own drift through the standard Job-result and aggregator channels. If on the other hand you prefer drift to show up as a metric rather than a log line — so it lands on Grafana dashboards alongside Nautobot's other counters and can drive Prometheus alert rules directly — expose the same query as a gauge through Nautobot's [custom app metrics extension point](../../../development/apps/api/prometheus.md). The mechanism is a small Nautobot app with a `metrics.py` at its root:

    ```python
    # metrics.py
    from datetime import timedelta
    from django.utils import timezone
    from prometheus_client.metrics_core import GaugeMetricFamily
    from nautobot.extras.models import ScheduledJob


    def metric_beat_schedule_drift():
        threshold = timezone.now() - timedelta(minutes=5)
        gauge = GaugeMetricFamily(
            "nautobot_beat_schedule_drift_seconds",
            "Seconds past next_run_at for enabled ScheduledJobs that have not fired.",
            labels=["schedule_name"],
        )
        for name, next_run_at in ScheduledJob.objects.filter(
            enabled=True, next_run_at__lt=threshold,
        ).values_list("name", "next_run_at"):
            gauge.add_metric([name], (timezone.now() - next_run_at).total_seconds())
        yield gauge


    metrics = [metric_beat_schedule_drift]
    ```

    The gauge appears on the web-tier `/metrics` endpoint and is recomputed on each scrape, so keep the underlying query cheap — the `enabled=True, next_run_at__lt=threshold` filter above is already index-friendly and well-bounded for typical `ScheduledJob` counts.

## Operator UIs

| Tool | Purpose |
|---|---|
| [`/worker-status/`](../guides/celery-queues.md) | Built-in staff-only page (Nautobot 2.3+) showing live Celery worker and queue state. Useful for triage; **do not poll for alerts** — it runs a live `inspect` query and may impact performance. |
| [Flower](https://github.com/mher/flower) | Open-source Celery monitoring UI. Exposes Prometheus metrics that Nautobot's `/metrics` does not — runtime histograms, per-worker load, prefetch wait times. Run as a sidecar against the same Redis broker, behind your auth proxy, with `--purge_offline_workers=60` for autoscaled environments. |

!!! warning
    [Flower](https://flower.readthedocs.io/en/latest/) is not a replacement for the Nautobot UI as it focuses on the operator/observability tier and complements rather than replaces Nautobot's own [`/metrics`](./prometheus-metrics.md) endpoint. It also exposes per-task histograms that Nautobot's worker metrics do not; their analysis is not in the scope of this guide but more details can be found in the respective [Flower documentation](https://flower.readthedocs.io/en/latest/prometheus-integration.html#available-metrics).

## Streaming Job Lifecycle Events

When an external system needs to react to Job start or completion — ticket updates, notification fan-out, downstream automation — prefer the [Job Events](../../platform-functionality/events.md#job-events) topics (`nautobot.jobs.job.started`, `nautobot.jobs.job.completed`) over polling the Job Result UI or scraping `nautobot.extras.jobs` log lines. Payloads carry `job_result_id`, `job_name`, `user_name`, and (on completion) `job_output` and `einfo` for failure tracebacks. Register `SyslogEventBroker` to fold them into your log pipeline (see [Streaming Event Notifications to Logs](./logging.md#streaming-event-notifications-to-logs)) or `RedisEventBroker` for a dedicated Pub/Sub channel.

## Logging from Inside Jobs

!!! note "Audience"
    This section is written for **Job authors** — the developers writing the Python code that runs as a Nautobot Job. Operators and SREs consuming Nautobot's outputs do not need to act on it, but it is included here so that operator-facing alerting concerns can inform how Jobs are instrumented in the first place. Share it with whoever owns Job code in your organization.

How a Job author writes log lines determines what an operator can alert on. The choices below have outsized impact on whether Job logs land in your aggregator as queryable signal or as undifferentiated noise. For the full Job-logging API surface, see [Job Logging](../../../development/jobs/job-logging.md); this section focuses on the choices that affect ingestion and alerting.

### Prefer `self.logger` Over `logging.getLogger()`

`self.logger` (provided by the `Job` base class) writes to both the `JobLogEntry` database table — visible in the Job Result UI — and the worker's `nautobot.jobs.<module>` Python logger that your aggregator already collects. A module-level `logging.getLogger(__name__)` reaches only the worker stdout, so log lines emitted that way are invisible in the Job Result UI. Default to `self.logger` and reach for the module-level logger only outside of Job methods (e.g. helper modules that may be called from non-Job code paths).

### Make Each Line Pivotable in the Aggregator

Three knobs determine how filterable a Job log line is downstream:

| Knob | Where it lands | Notes |
|---|---|---|
| `extra={"key": "value", ...}` | Worker stdout (and `JobLogEntry` message in serialized form) | The only mechanism that produces queryable fields in an aggregator. Include `job_result_id`, a short `stage` label, and any object identifier the operator would want to pivot on. |
| `extra={"object": instance}` | `JobLogEntry.obj` — clickable link in Job Result UI | UI-only — does not appear as a field in worker stdout. |
| `extra={"grouping": "validate"}` | `JobLogEntry.grouping` — collapses related entries in UI | UI-only. Defaults to the calling function name if omitted. |

Example:

```python
self.logger.info(
    "Updated interface %s on %s",
    interface.name,
    device.name,
    extra={
        "object": device,
        "grouping": "interface-sync",
        "job_result_id": str(self.job_result.pk),
        "stage": "apply",
    },
)
```

When the worker is configured for JSON output (see [Switching to JSON Output](./logging.md#switching-to-json-output)), `job_result_id` and `stage` arrive at your aggregator as first-class fields you can filter and group on — no regex parsing required.

### Choose Levels for Alerting, Not Narration

Aggregator alert rules typically anchor on logger name plus level. If every step of a Job emits at `INFO`, the operator has to fall back to text matching to find anything actionable.

| Level | Use for | Operator default |
|---|---|---|
| `DEBUG` | Detailed diagnostics; off in production | Ignored |
| `INFO` | Successful milestones (start, finish, key transitions) | Not alerted |
| `WARNING` | Expected-but-noteworthy condition the operator should see (record skipped, retry needed, deprecated input) | Aggregated dashboard signal |
| `ERROR` | Operator action required; Job continues with reduced scope | Alert routed to ops queue |
| `CRITICAL` | Job cannot continue; aborting | Page on-call |

Inside `except` blocks, use `self.logger.exception("...")` — it emits at `ERROR` and attaches the traceback automatically. Do not manually `str(exc)` and log at `INFO`; that strips the traceback and downgrades the severity.

### Aggregate Per-Record Loops

A Job that emits one `INFO` line per device in a 10,000-device loop produces 10,000 rows in `JobLogEntry` and 10,000 lines in worker stdout. The legitimate `ERROR` lines for the 4 failures are buried, the database table grows for nothing, and the UI is unusable. Prefer one summary line per phase plus per-record lines only at `WARNING` or above:

```python
self.logger.info("Sync complete: %d processed, %d updated, %d skipped, %d failed",
                 total, updated, skipped, failed,
                 extra={"job_result_id": str(self.job_result.pk), "stage": "summary"})
```

This makes "did this run go well" answerable from a single log line per Job run, rather than requiring a count query in your aggregator.

### Never `print()`

`print()` output is captured by Celery into the worker's stdout, but the resulting line has no level, no logger name, and no `extra` fields. Your aggregator can't distinguish it from third-party library noise, and it never reaches `JobLogEntry`. Treat it as a code-review smell.

### `SANITIZER_PATTERNS` Does Not Protect Worker stdout

[`SANITIZER_PATTERNS`](../configuration/settings.md#sanitizer_patterns) is applied inside `JobResult.log()` — that is, only on the path into `JobLogEntry` (and on `JobResult.result` / `traceback` / `exc_message`). It does not run inside the Python logging handler chain, which means a credential interpolated into a log message reaches the worker stdout — and therefore your aggregator — unredacted, regardless of whether you used `self.logger`, a module-level logger, or `print()`. Redact secrets in the Job before logging; treat the sanitizer as a UI-side safety net, not a perimeter.

### What This Unlocks for the Operator

When Job authors follow the above, the operator side becomes:

- **Aggregator alert rule**: `logger:nautobot.jobs.<module> AND level:ERROR` — anchored on logger name and level, no text matching required. Pivot on `extra.stage` and `extra.job_result_id` to scope incidents.
- **Lifecycle signal**: subscribe to [`nautobot.jobs.job.completed`](../../platform-functionality/events.md#job-events) and alert on non-null `einfo`. See [Streaming Job Lifecycle Events](#streaming-job-lifecycle-events) above.
- **Metric signal**: `nautobot_worker_finished_jobs{status="FAILURE"}` from [Prometheus Metrics](./prometheus-metrics.md) — for SLO dashboards rather than per-incident routing.

The three signals are complementary: the metric tells you *how many*, the event tells you *which run*, and the logs tell you *why*.
