# Monitoring Celery and Jobs

Nautobot Jobs run as Celery tasks. Most production surprises with Nautobot at scale come from Celery defaults that work for short-lived web background tasks but bite under Nautobot's typical workload of long-running network-automation Jobs. This page covers the configuration knobs, the visibility-timeout pitfall, and the signals you need beyond the basic Tier-1 alerts in [Alerting](./alerting.md).

For multi-queue worker deployments, see [Task Queues](../guides/celery-queues.md). For per-Job logging from inside Job code, see [Job Logging](../../../development/jobs/job-logging.md).

## The Redis `visibility_timeout` foot-gun

When the broker is Redis (Nautobot's default), Celery does not delete a task from the queue when a worker picks it up. The broker holds the task under a **visibility timeout** and only deletes it after the worker acks. If the task runs longer than the visibility timeout (**default: 3600 seconds / 1 hour**), the broker concludes the worker died and **redelivers the task to another worker**.

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

## Worker silent-death

A Celery worker that hits an OOM kill, a C-extension segfault, or wedges on a syscall can leave the process technically *alive* (zombie or stuck in a kernel wait) while no longer pulling tasks off the queue. A bare process-existence check passes; `nautobot-server celery inspect ping` may stall and time out depending on which thread is wedged.

The **file-based heartbeat probe is the only check that proves the Python interpreter is still executing the worker loop** — it requires the worker to actively `touch` `$CELERY_WORKER_HEARTBEAT_FILE` every cycle. In Kubernetes, wire it as the **liveness** probe so the kubelet restarts a stuck worker.

```python
# nautobot_config.py
CELERY_HEALTH_PROBES_AS_FILES = True
```

See [Health Checks — Nautobot Celery Worker](./health-checks.md#nautobot-celery-worker) for the full probe configuration (shell check, Kubernetes YAML, Docker Compose), and [Health Checks — Celery Worker Container in k8s](./health-checks.md#celery-worker-container-in-k8s) for an important caveat about Celery 5.6.1 affecting Nautobot 3.0.4 and 3.0.5.

## Celery configuration tuning

Nautobot exposes Celery's full configuration surface through `nautobot_config.py` — any `CELERY_*` setting Celery accepts can be overridden. The defaults that ship with Celery target short-lived web background tasks; for Nautobot's typical long-running network-automation workload, the following overrides are usually appropriate:

| Setting | Default | Recommended for Nautobot | Why |
|---|---|---|---|
| `worker_prefetch_multiplier` | `4` | `1` | Long-running Jobs cause head-of-line blocking when a worker reserves multiple tasks ahead. With `1`, each worker pulls one task at a time. See [Task Queues](../guides/celery-queues.md#queuing-optimizations). |
| `task_acks_late` | `False` | `True` *for idempotent Jobs only* | Task is acked **after** completion; if the worker crashes mid-task, the broker redelivers. Safer against worker death — but the Job runs again, so it must be idempotent. |
| `task_reject_on_worker_lost` | `False` | `True` (paired with above) | Required companion to `acks_late`; ensures the lost task is rejected back to the queue rather than vanishing. |
| `worker_max_tasks_per_child` | unset | `1000` | Recycles the worker process every N tasks. Bounds memory growth from leaks. |
| `worker_max_memory_per_child` | unset | `200000` (200 MB) | Recycles worker if RSS exceeds threshold. Catches the same class of bug on a memory rather than count basis. |
| `task_soft_time_limit` / `task_time_limit` | unset | site-specific (e.g. `1800` / `2100`) | Global ceiling that catches runaway tasks. Per-Job overrides are still set on the Job class. |

!!! warning
    `task_acks_late=True` is a foot-gun if your Jobs are not idempotent. A Nautobot Job that calls `Device.objects.create(...)` will create a duplicate device on retry. Audit Jobs for `get_or_create` / unique-constraint patterns before enabling, or scope `acks_late` to a specific queue and route only safe Jobs to it.

See the [Celery optimizing guide](https://docs.celeryq.dev/en/stable/userguide/optimizing.html) for the full configuration reference.

## Queue depth — the silent backlog signal

The Tier-1 alerts in [Alerting](./alerting.md) catch *failures*. They do not catch a slow-but-functional pipeline where producers outpace consumers. The only direct signal for that is queue depth.

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

## Beat schedule drift

Nautobot's Celery Beat scheduler ([`NautobotDatabaseScheduler`](https://github.com/nautobot/nautobot/blob/develop/nautobot/core/celery/schedulers.py)) ticks every few seconds and fires `ScheduledJob` rows whose cron expression matches. If the scheduler process is killed mid-tick, blocked on the database, or generally slow, **scheduled runs are missed and not backfilled** — Beat does not have a "make-up runs" feature.

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
