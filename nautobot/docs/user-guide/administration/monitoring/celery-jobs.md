# Celery and Jobs

Nautobot Jobs run as Celery tasks. Most production surprises with Nautobot at scale come from Celery defaults that work for short-lived web background tasks but bite under Nautobot's typical workload of long-running network-automation Jobs. This page covers the configuration knobs, the visibility-timeout pitfall, and the signals you need beyond the basic Tier-1 alerts in [Alerting](./alerting.md).

For multi-queue worker deployments, see [Task Queues](../guides/celery-queues.md). For per-Job logging from inside Job code, see [Job Logging](../../../development/jobs/job-logging.md).

## Visibility Timeout for Long-Running Jobs

When the broker is Redis (Nautobot's default), Celery does not delete a task from the queue when a worker picks it up. The broker holds the task under a visibility timeout and only deletes it after the worker acks. If the task runs longer than the visibility timeout (default: 3600 seconds, or 1 hour), the broker concludes the worker died and redelivers the task to another worker.

The result is a long-running Nautobot Job running twice in parallel, on different workers, racing to write the same database. Symptoms include duplicate `JobLogEntry` rows, `IntegrityError` tracebacks, and half-applied changes.

!!! warning
    `task_acks_late=True` does **not** prevent this. The visibility timeout is a broker-level mechanism that ignores ack semantics on Redis (and SQS). If your Jobs can run longer than an hour, you must raise the visibility timeout explicitly.

The fix:

```python
# nautobot_config.py
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": 21600,  # 6 hours — set above your longest-running Job
}
```

Pick a value that comfortably exceeds your slowest Job's wall-clock runtime. Real-world Nautobot deployments running fleet-wide compliance Jobs against thousands of devices have seen 4+ hour runtimes.

You can detect this in production *before* it bites by alerting on [`nautobot_worker_started_jobs`](./prometheus-metrics.md#metric-types) going up without a corresponding [`nautobot_worker_finished_jobs`](./prometheus-metrics.md#metric-types) increase for a given task name over a long window — that's a Job that has been redelivered or is stuck.

## Worker Silent Death

A Celery worker that hits an OOM kill, a C-extension segfault, or wedges on a syscall can leave the process technically alive (zombie or stuck in a kernel wait) while no longer pulling tasks off the queue. A bare process-existence check passes; `nautobot-server celery inspect ping` may stall and time out depending on which thread is wedged.

The file-based heartbeat probe is the only check that proves the Python interpreter is still executing the worker loop — it requires the worker to actively `touch` `$CELERY_WORKER_HEARTBEAT_FILE` every cycle. In Kubernetes, wire it as the liveness probe so the kubelet restarts a stuck worker.

```python
# nautobot_config.py
CELERY_HEALTH_PROBES_AS_FILES = True
```

See [Health Checks — Nautobot Celery Worker](./health-checks.md#nautobot-celery-worker) for the full probe configuration (shell check, Kubernetes YAML, Docker Compose), and [Health Checks — Celery Worker Container in k8s](./health-checks.md#celery-worker-container-in-k8s) for an important caveat about Celery 5.6.1 affecting Nautobot 3.0.4 and 3.0.5.

## Queue Depth

The Tier-1 alerts in [Alerting](./alerting.md) catch failures. They do not catch a slow-but-functional pipeline where producers outpace consumers. The only direct signal for that is queue depth — the silent backlog.

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

## Beat Schedule Drift

Nautobot's Celery Beat scheduler ([`NautobotDatabaseScheduler`](https://github.com/nautobot/nautobot/blob/develop/nautobot/core/celery/schedulers.py)) ticks every few seconds and fires `ScheduledJob` rows whose cron expression matches. If the scheduler process is killed mid-tick, blocked on the database, or generally slow, scheduled runs are missed and not backfilled — Beat does not have a "make-up runs" feature.

Two complementary detections:

1. **Heartbeat file** — already covered by the Tier-1 alert in [Alerting](./alerting.md). Fires if Beat stops entirely.
2. **Per-schedule liveness** — query the database for schedules whose window has passed without a run:

    ```sql
    SELECT name, last_run_at, next_run_at, total_run_count
    FROM extras_scheduledjob
    WHERE enabled = true
      AND next_run_at < NOW() - INTERVAL '5 minutes';
    ```

    Wrap as a Nautobot Job that emits a `WARNING` and you have a self-monitoring scheduler.

## Operator UIs

| Tool | Purpose |
|---|---|
| [`/worker-status/`](../guides/celery-queues.md) | Built-in staff-only page (Nautobot 2.3+) showing live Celery worker and queue state. Useful for triage; **do not poll for alerts** — it runs a live `inspect` query and may impact performance. |
| [Flower](https://github.com/mher/flower) | Open-source Celery monitoring UI. Exposes Prometheus metrics that Nautobot's `/metrics` does not — runtime histograms, per-worker load, prefetch wait times. Run as a sidecar against the same Redis broker, behind your auth proxy, with `--purge_offline_workers=60` for autoscaled environments. |

Flower is not a replacement for the Nautobot UI — the UI knows about [`JobResult`](../../platform-functionality/jobs/models.md#job-results) rows and ties to model permissions. Flower is for the operator/observability tier and complements (rather than replaces) Nautobot's own [`/metrics`](./prometheus-metrics.md) endpoint — Flower exposes per-task histograms that Nautobot's worker metrics do not.

## Streaming Job Lifecycle Events

When an external system needs to react to Job start or completion — ticket updates, notification fan-out, downstream automation — prefer the [Job Events](../../platform-functionality/events.md#job-events) topics (`nautobot.jobs.job.started`, `nautobot.jobs.job.completed`) over polling the Job Result UI or scraping `nautobot.extras.jobs` log lines. Payloads carry `job_result_id`, `job_name`, `user_name`, and (on completion) `job_output` and `einfo` for failure tracebacks. Register `SyslogEventBroker` to fold them into your log pipeline (see [Streaming event notifications to logs](./logging.md#streaming-event-notifications-to-logs)) or `RedisEventBroker` for a dedicated Pub/Sub channel.

## Logging from Inside Jobs

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

When the worker is configured for JSON output (see [Switching to JSON output](./logging.md#switching-to-json-output)), `job_result_id` and `stage` arrive at your aggregator as first-class fields you can filter and group on — no regex parsing required.

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
