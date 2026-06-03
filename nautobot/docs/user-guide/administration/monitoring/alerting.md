# Alerting

This page describes a low-noise alert ruleset for production Nautobot. The recommendations assume that:

- Container `stdout` is shipped to a log aggregator with the logger name parsed as a structured field; see [Logging](./logging.md).
- Prometheus metrics are enabled (`NAUTOBOT_METRICS_ENABLED=True`); see [Prometheus Metrics](./prometheus-metrics.md).
- Health probes are wired into the orchestrator; see [Health Checks](./health-checks.md).

Alert primarily on health-checks and metrics. Use log keywords as a *secondary* signal, scoped to specific logger names.

!!! note "Living section"
    The rules and thresholds below are the starting points we currently recommend based on production deployments we've seen — they're not exhaustive and they're not deployment-tuned.
    Make sure to walk through your steady-state baseline and adapt thresholds for your actual production environment needs before committing them to your alerting rules; what's "normal" depends heavily on Job mix, fleet size, and Beat schedule density. Contributions from your environment are welcome.

## Before You Write a Rule

Every alert rule on this page is the product of five decisions: where the condition is observed, what severity tier should fire, what shape the rule takes, what baseline it was measured against, and whether maintenance windows should suppress it.

The table below is the index for those decisions — each row points to the section that elaborates. Treat it as the reference scaffold; the rest of the page is the practical illustration of how to deal with each decision.

| Decision | Choices | Where it's covered |
|---|---|---|
| Where is the condition observed? | Prometheus metric / log line / orchestrator probe / SLO burn-rate | [Tier 1 Alerts](#tier-1-alerts-page-on-call), [Tier 2 Alerts](#tier-2-alerts-ticket-or-dashboard), [Metrics-Based Alerts](#metrics-based-alerts), [Log-Based Alerts](#log-based-alerts), [View Latency Alerts](#view-latency-alerts), [SLO-Based Alerts](#slo-based-alerts) |
| What severity tier should fire? | Page (Tier 1) / Ticket or Dashboard (Tier 2) | [Tier 1 Alerts](#tier-1-alerts-page-on-call), [Tier 2 Alerts](#tier-2-alerts-ticket-or-dashboard), [Routing and Severity](#routing-and-severity) |
| What rule shape fits the signal? | Fixed threshold / regression from baseline / burn-rate / new-class detection | [Calibrating Thresholds](#calibrating-thresholds), [View Latency Alerts](#view-latency-alerts), [SLO-Based Alerts](#slo-based-alerts) |
| What baseline did I measure against? | p95 over 7 days × headroom multiplier | [Calibrating Thresholds — Worked Example](#worked-example-queue-depth-threshold) |
| Should maintenance windows suppress it? | Yes (silence by label) / No | [Maintenance Windows](#maintenance-windows) |

## Tier 1 Alerts: Page on-Call

Indicative list of the most critical signals that should page the on-call engineer immediately. These are the conditions that indicate a likely outage or severe degradation in service, and require immediate attention.

| Signal | Source | Threshold |
|---|---|---|
| Web `/health/` failing | HTTP probe | non-200 for 2 consecutive checks (≥1 minute) |
| `nautobot-server health_check` failing on web pod | exec probe | ≥3 failures in 5 minutes |
| Celery worker heartbeat file stale | filesystem | mtime > 60 seconds old |
| Celery Beat heartbeat file stale | filesystem | mtime > 30 seconds old (Beat ticks every ~5 seconds) |
| `nautobot_worker_finished_jobs{status="FAILURE"}` | Prometheus | rate > 0 for any production Job class for 5 minutes |
| `health_check_database_info` | Prometheus | unavailable for 1 minute |
| `health_check_redis_backend_info` | Prometheus | unavailable for 1 minute |
| Web 5xx rate | log search | `level=ERROR AND logger:django.request AND status_code:5*` rate ≥ 1/min — see [Logging — Reading the Logger Name in Your Aggregator](./logging.md#reading-the-logger-name-in-your-aggregator) for how to extract `logger` as a queryable field |

## Tier 2 Alerts: Ticket or Dashboard

Indicative list of signals that should open a ticket or appear on a dashboard for next-business-day handling. These are the conditions that indicate a likely issue that should be investigated and resolved, but do not require immediate attention.

| Signal | Threshold |
|---|---|
| Celery `RETRY` rate | > N retries / 5 min for the same task |
| Soft-time-limit hits | any |
| `nautobot_worker_singleton_conflict` | > 0 (schedule overlap; either tune cron or shorten Job) |
| `nautobot.extras.plugins` `ERROR` | any (App health post-deploy) |
| `nautobot.core.celery.schedulers` `Disabling schedule` | any (an admin-defined schedule was auto-disabled) |
| Git sync Job failures | any (`status="FAILURE"` on the Job) |
| Login failure spike on `nautobot.auth.login` | rate spike (security signal) |
| Redis memory utilization (via `redis_exporter`) | `redis_memory_used_bytes / redis_memory_max_bytes > 0.8` |
| PgBouncer pool saturation (via `pgbouncer_exporter`) | `pgbouncer_pools_server_active_connections / max_server_connections > 0.9` |

For Redis and PostgreSQL alerting in detail, see [Backing Stores](./backing-stores.md). For Celery-specific signals (queue depth, Beat drift), see [Celery and Jobs](./celery-jobs.md).

## Calibrating Thresholds

A useful threshold isolates the failure mode you want to alert on from the noise floor of healthy operation — and that floor varies dramatically by deployment. A small lab might see zero `WorkerLostError` lines in a quarter; a 100-pod production cluster might see one a day from routine pod rotation. The same `> 0 in 5 min` rule would page neither, then page constantly.

A practical recipe before committing any threshold below to production:

1. **Observe for a representative window.** Seven days is a useful default — it covers a full weekly cycle including weekends, scheduled cleanup Jobs, and any nightly batch automation.
2. **Take the p95 of the observed value during normal operation.** Use Prometheus's `quantile_over_time(0.95, metric[7d])` or your aggregator's equivalent.
3. **Apply a headroom multiplier.** For Tier 1 (paging) start at 2× the observed p95; for Tier 2 (dashboard) start at 1.5×. Tighten over time as the alert proves accurate.
4. **Skip the alert entirely if the p95 already exceeds what you'd want to alert on.** That means the signal is fundamentally noisy in your environment and needs further scoping (per-Job-class, per-tenant, per-queue) before becoming a rule.

### Worked Example: Queue-Depth Threshold

Suppose you want a Tier-2 alert for the `celery` queue backlog (`celery_queue_length{queue="celery"}` from `celery-exporter` — see [Celery and Jobs — Queue Depth](./celery-jobs.md#queue-depth)).

1. **Observe.** Let the metric run for seven days against a deployment that is operating normally.
2. **Take the p95.** In the Prometheus expression browser:

    ```promql
    quantile_over_time(0.95, celery_queue_length{queue="celery"}[7d])
    ```

    Assume the result is `28` — for 95% of the week, the queue had 28 or fewer pending tasks.

3. **Apply the headroom multiplier.** This is a Tier-2 alert (ticket, not page), so `1.5 × 28 = 42`. Round to a clean number — `50` — to avoid the appearance of false precision.
4. **Sanity-check against step 4.** A p95 of 28 is well below "obviously bad" for queue depth, so the alert is meaningful. If p95 had come back as `2,000` — i.e. the queue is routinely deep — the threshold would need to be per-queue or paired with a duration filter, not a flat number.

The resulting rule:

```yaml
- alert: NautobotQueueBacklog
  expr: celery_queue_length{queue="celery"} > 50
  for: 10m
  labels: {severity: ticket}
  annotations:
    summary: "Queue 'celery' backlogged ({{ $value }} pending)"
```

The same recipe applies to any threshold-shaped metric — Redis memory utilization, PgBouncer pool saturation, web 5xx rate. The constants in the tier tables below are the values that have worked for typical mid-size deployments; replace them with your own baseline-derived numbers before committing to production.

## Routing and Severity

Tier 1 alerts page the on-call engineer immediately — PagerDuty, OpsGenie, or a Slack channel with paging integration. Tier 2 alerts open a ticket or appear on a dashboard for next-business-day handling — email, a low-urgency Slack channel, or an issue tracker.

For any Tier 1 condition that affects more than half of available capacity (every web pod failing `/health/`, every worker heartbeat stale at once, the database itself unreachable), escalate to whoever owns incident command in your organization in addition to paging on-call. These are the cases where one engineer working alone is the bottleneck — getting the response team coordinated early is more valuable than starting the technical investigation thirty seconds sooner.

## Metrics-Based Alerts

Nautobot's `/metrics` endpoint exposes Job and health-check counters; see [Prometheus Metrics](./prometheus-metrics.md) for the full catalogue. The `nautobot_worker_*` counters below live on the **worker** process and require an explicit opt-in — see [Enabling Worker Metrics](./prometheus-metrics.md#enabling-worker-metrics) — without which these alert rules will never fire because the series do not exist. The metrics most useful for alerting:

- `nautobot_worker_finished_jobs{status="..."}` — Job outcomes by status label.
- `nautobot_worker_exception_jobs{exception_type="..."}` — Job failures broken out by exception class. A previously-zero exception class going non-zero is almost always alert-worthy and is the single best signal for catching new failure modes.
- `nautobot_worker_singleton_conflict` — singleton Jobs blocked by a still-running invocation.
- `health_check_database_info`, `health_check_redis_backend_info` — last health-check result.
- `django_http_responses_total_by_status_total{status=~"5.."}` — server-error rate.
- `django_db_errors_total` — ORM error rate.

### Sample PromQL Rules

```yaml
groups:
  - name: nautobot.tier1
    rules:
      - alert: NautobotDatabaseUnavailable
        # health_check_database_info is a label-less Gauge: -1 unknown, 0 down, 1 up.
        # `<= 0` catches both "down" and "unknown" (a worker that has not yet run the check).
        expr: health_check_database_info <= 0
        for: 1m
        labels: {severity: page}

      - alert: NautobotRedisUnavailable
        expr: health_check_redis_backend_info <= 0
        for: 1m
        labels: {severity: page}

      - alert: NautobotJobFailures
        expr: sum by (job_class_name) (increase(nautobot_worker_finished_jobs{status="FAILURE"}[5m])) > 0
        labels: {severity: page}
        annotations:
          summary: "Nautobot Job {{ $labels.job_class_name }} is failing"

      - alert: NautobotJobExceptionsByType
        expr: sum by (exception_type) (increase(nautobot_worker_exception_jobs[10m])) > 0
        labels: {severity: page}
        annotations:
          summary: "New Job exception class: {{ $labels.exception_type }}"

      - alert: NautobotHTTP5xx
        expr: |
          sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))
            / sum(rate(django_http_responses_total_by_status_total[5m])) > 0.02
        for: 5m
        labels: {severity: page}

      - alert: NautobotWorkersInsufficient
        # Workers are horizontally scaled; alert on falling below minimum redundancy
        # rather than `up == 0` (which only fires when *all* workers are down).
        expr: count(up{job="nautobot-worker"} == 1) < 2
        for: 2m
        labels: {severity: page}
```

## Log-Based Alerts

When a metric isn't available, anchor log-based queries on logger name plus level. The full set of Nautobot logger names is documented in [Logging — Logger Namespace Map](./logging.md#logger-namespace-map). The pattern is consistent across aggregators; the syntax below uses [LogQL](https://grafana.com/docs/loki/latest/query/) but Splunk SPL, Elastic KQL, etc. translate directly.

```logql
# Database OperationalErrors from the web tier
sum(rate({app="nautobot",component="web"} |= "OperationalError" [5m])) > 0

# App initialization errors (post-deploy regression detector)
sum(rate(
  {app="nautobot"} | json
  | name=~"nautobot\\.extras\\.plugins"
  | levelname="ERROR"
[10m])) > 0

# Beat auto-disabling schedules
sum(rate({app="nautobot",component="beat"} |~ "Disabling schedule" [10m])) > 0

# Login failure spike (security)
sum(rate(
  {app="nautobot"} | json
  | name="nautobot.auth.login" | levelname="WARNING"
[5m])) > 5
```

The pattern is the same in any aggregator: anchor on `logger` (or `name`) plus `level`. Free-text grep across stdout will surface the routine warnings listed in [Logging — Known Noise](./logging.md#known-noise) and bury real failures.

## View Latency Alerts

View Latency Alerts track the response time of individual Nautobot views (UI pages and REST API endpoints) and are most useful for catching slowdowns that affect a specific view rather than the service as a whole. View-level latency lends itself to two complementary alert shapes, both built on the per-view histogram exposed by [`django-prometheus`](./prometheus-metrics.md#view-latency-histograms):

**Fixed-threshold (Tier 2)** — p99 of a named critical view exceeds your target for 10 minutes. Use when you have an absolute target for that view.

```yaml
- alert: NautobotDeviceListSlow
  expr: |
    histogram_quantile(
      0.99,
      sum by (le) (
        rate(django_http_requests_latency_seconds_by_view_method_bucket{view="dcim:device_list",method="GET"}[5m])
      )
    ) > 2
  for: 10m
  labels: {severity: ticket}
  annotations:
    summary: "Device list p99 > 2s for 10 minutes (current: {{ $value }}s)"
```

**Regression (Tier 2)** — a view's p99 over the last 5 minutes is more than 2× its own p99 over the prior 24 hours. Catches "this view got slower" without committing to an absolute number, useful for views without an agreed-upon target.

```yaml
- alert: NautobotViewLatencyRegression
  expr: |
    (
      histogram_quantile(0.99, sum by (le, view) (rate(django_http_requests_latency_seconds_by_view_method_bucket{view!=""}[5m])))
      / histogram_quantile(0.99, sum by (le, view) (rate(django_http_requests_latency_seconds_by_view_method_bucket{view!=""}[24h])))
    ) > 2
  for: 15m
  labels: {severity: ticket}
  annotations:
    summary: "View {{ $labels.view }} is 2x slower than its 24h baseline"
```

!!! tip
    Threshold latency alerts are inherently noisier than counter-based alerts — they fire on transient slowness that does not always justify a ticket. For deployments running an SLO-based pipeline, the burn-rate form in [SLAs and SLOs — Worked Example: Device List Page SLO](./slas-and-slos.md#worked-example-device-list-page-slo) is the more disciplined choice. Use the rules in this section as starting points until the SLO pipeline is in place.

## Maintenance Windows

Scheduled cleanup Jobs, database maintenance, and deploy windows produce log lines and metric spikes that look like outages but are not — they need to be suppressed rather than alerted on. The mechanism depends on your alerting stack:

- **Alertmanager**: define silences via the [Alertmanager web UI](https://prometheus.io/docs/alerting/latest/management_api/) or the API, scoped by label selector (`job="nautobot-worker"`, `severity="page"`, or a custom `maintenance="db"` label).
- **Datadog / New Relic / Opsgenie**: equivalent downtime / muted-window primitives that take a label or tag selector and a time range.

A practical convention is to tag every scheduled maintenance Nautobot Job with a recognizable name (e.g. the bundled `Logs Cleanup` Job) and silence on `job_name="Logs Cleanup"` during its expected run window plus a small buffer. Avoid silencing entire severity tiers — you lose visibility into actual incidents that happen to coincide with the maintenance window.

## SLO-Based Alerts

Threshold-based alerts fire on a single observation crossing a line; SLO-based alerts fire on the *rate* of error-budget consumption. They produce fewer pages overall and correlate better with user-perceived outages, at the cost of more setup and ongoing budget-management discipline.

For a fuller treatment — candidate Service Level Indicators for Nautobot, suggested starting SLO values, the burn-rate alerting math with PromQL recipes against Nautobot's exposed metrics, and how SLO alerts coexist with the threshold-based tiers above — see [SLAs and SLOs](./slas-and-slos.md).

## Worked Example: 3 a.m. Page

Walking through a typical paging incident clarifies how the signals on this page fit together. The scenario: at 3 a.m., the on-call engineer is paged for `NautobotJobFailures` on a production deployment.

1. **Read the alert annotation.** The `summary` line names the Job: `Nautobot Job NetworkSync is failing` — the label value is the Python class name, which the Job's `Meta.name` would surface in the UI as `Network Sync`.
2. **Open the metrics dashboard.** Confirm `nautobot_worker_finished_jobs{job_class_name="NetworkSync", status="FAILURE"}` is increasing. Cross-check `nautobot_worker_started_jobs` to see whether new runs are still being kicked off (Beat is working) or whether the failures are stuck retry jobs.
3. **Look at `nautobot_worker_exception_jobs{exception_type=...}`** for the same Job. The label tells you the exception class: `OperationalError` (database) vs `ConnectionError` (downstream device) vs `TimeoutError` (the Job itself running long).
4. **Jump to the aggregator.** Search `name="nautobot.jobs.network_sync"` with `levelname="ERROR"` over the last hour. Read the tracebacks to confirm the root cause.
5. **Cross-check the Job Result UI** when you need to coordinate with the Job author — `/extras/job-results/?status=failure&name=Network+Sync` (the UI filters on the human `Meta.name`) shows the user-facing failure summary and the structured `JobLogEntry` rows.
6. **Decide remediation.** Database error: page the DB team or check `health_check_database_info`. Device error: page the network team. Timeout: temporarily disable the Job via the Job admin page (`/extras/jobs/`) and file a ticket for follow-up.

The progression `metric → exception class → log traceback → Job Result UI` is the standard investigative flow for any Nautobot-level alert. Going in the opposite order (starting from `/extras/job-results/` and clicking through) works but is slower, and is harder to scope when the failure spans multiple Job runs or originates outside Nautobot itself.
