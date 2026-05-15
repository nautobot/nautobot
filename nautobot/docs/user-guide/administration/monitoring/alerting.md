# Alerting

This page describes a low-noise alert ruleset for production Nautobot. The recommendations assume that:

- Prometheus metrics are enabled (`NAUTOBOT_METRICS_ENABLED=True`); see [Prometheus Metrics](./prometheus-metrics.md).
- Health probes are wired into the orchestrator; see [Health Checks](./health-checks.md).
- Container `stdout` is shipped to a log aggregator with the logger name parsed as a structured field; see [Logging](./logging.md).

Alert primarily on health-checks and metrics. Use log keywords as a *secondary* signal, scoped to specific logger names.

!!! note "Living section"
    The rules and thresholds below are the starting points we currently recommend based on production deployments we've seen — they're not exhaustive and they're not deployment-tuned. Walk through your steady-state baseline before committing them to your alerting rules; what's "normal" depends heavily on Job mix, fleet size, and Beat schedule density. Contributions from your environment are welcome.

## Calibrating Thresholds

A useful threshold isolates the failure mode you want to alert on from the noise floor of healthy operation — and that floor varies dramatically by deployment. A small lab might see zero `WorkerLostError` lines in a quarter; a 100-pod production cluster might see one a day from routine pod rotation. The same `> 0 in 5 min` rule would page neither, then page constantly.

A practical recipe before committing any threshold below to production:

1. **Observe for a representative window.** Seven days is a useful default — it covers a full weekly cycle including weekends, scheduled cleanup Jobs, and any nightly batch automation.
2. **Take the p95 of the observed value during normal operation.** Use Prometheus's `quantile_over_time(0.95, metric[7d])` or your aggregator's equivalent.
3. **Apply a headroom multiplier.** For Tier 1 (paging) start at 2× the observed p95; for Tier 2 (dashboard) start at 1.5×. Tighten over time as the alert proves accurate.
4. **Skip the alert entirely if the p95 already exceeds what you'd want to alert on.** That means the signal is fundamentally noisy in your environment and needs further scoping (per-Job-class, per-tenant, per-queue) before becoming a rule.

The thresholds in the tier tables below are starting points sized for a typical mid-size deployment; nothing replaces measuring against your own baseline.

## Routing and Severity

Tier 1 alerts page the on-call engineer immediately — PagerDuty, OpsGenie, or a Slack channel with paging integration. Tier 2 alerts open a ticket or appear on a dashboard for next-business-day handling — email, a low-urgency Slack channel, or an issue tracker.

For any Tier 1 condition that affects more than half of available capacity (every web pod failing `/health/`, every worker heartbeat stale at once, the database itself unreachable), escalate to whoever owns incident command in your organization in addition to paging on-call. These are the cases where one engineer working alone is the bottleneck — getting the response team coordinated early is more valuable than starting the technical investigation thirty seconds sooner.

## Tier 1: Page

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

## Tier 2: Ticket or Dashboard

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

## Metrics-Based Alerts

Nautobot's `/metrics` endpoint exposes Job and health-check counters; see [Prometheus Metrics](./prometheus-metrics.md) for the full catalogue. The metrics most useful for alerting:

- `nautobot_worker_finished_jobs{status="..."}` — Job outcomes by status label.
- `nautobot_worker_exception_jobs{exception="..."}` — Job failures broken out by exception class. A previously-zero exception class going non-zero is almost always alert-worthy and is the single best signal for catching new failure modes.
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
        expr: health_check_database_info{status="unavailable"} == 1
        for: 1m
        labels: {severity: page}

      - alert: NautobotRedisUnavailable
        expr: health_check_redis_backend_info{status="unavailable"} == 1
        for: 1m
        labels: {severity: page}

      - alert: NautobotJobFailures
        expr: sum by (name) (increase(nautobot_worker_finished_jobs{status="FAILURE"}[5m])) > 0
        labels: {severity: page}
        annotations:
          summary: "Nautobot Job {{ $labels.name }} is failing"

      - alert: NautobotJobExceptionsByType
        expr: sum by (exception) (increase(nautobot_worker_exception_jobs[10m])) > 0
        labels: {severity: page}
        annotations:
          summary: "New Job exception class: {{ $labels.exception }}"

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

When a metric isn't available, anchor log-based queries on logger name plus level. The full set of Nautobot logger names is documented in [Logging — Logger namespace map](./logging.md#logger-namespace-map). The pattern is consistent across aggregators; the syntax below uses [LogQL](https://grafana.com/docs/loki/latest/query/) but Splunk SPL, Elastic KQL, etc. translate directly.

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

## Maintenance Windows

Scheduled cleanup Jobs, database maintenance, and deploy windows produce log lines and metric spikes that look like outages but are not — they need to be suppressed rather than alerted on. The mechanism depends on your alerting stack:

- **Alertmanager**: define silences via the [Alertmanager web UI](https://prometheus.io/docs/alerting/latest/management_api/) or the API, scoped by label selector (`job="nautobot-worker"`, `severity="page"`, or a custom `maintenance="db"` label).
- **Datadog / New Relic / Opsgenie**: equivalent downtime / muted-window primitives that take a label or tag selector and a time range.

A practical convention is to tag every scheduled maintenance Nautobot Job with a recognizable name (e.g. `Cleanup System Records`) and silence on `job_name="Cleanup System Records"` during its expected run window plus a small buffer. Avoid silencing entire severity tiers — you lose visibility into actual incidents that happen to coincide with the maintenance window.

## SLO-Based Alerts

Threshold-based alerts page when a single observation crosses a line. SLO-based alerts page when the rate of failure consumes an error budget faster than expected — a fundamentally different framing.

For example, instead of paging on every Tier 1 Job failure:

- **Define an availability objective**: 99.9% of Job runs in any 30-day window succeed.
- **Translate to an error budget**: 0.1% of Job runs may fail. For a 100,000-run-per-month deployment, that's 100 allowed failures.
- **Alert on burn rate**: if the failure rate over the last hour, projected forward, would consume the 30-day budget in under 6 hours, page.

The PromQL recipe is documented in the [Prometheus SRE workbook](https://sre.google/workbook/alerting-on-slos/) — substitute `nautobot_worker_finished_jobs{status="FAILURE"}` for the failure counter and the corresponding total counter. SLO-based alerts produce fewer pages overall and correlate better with user-perceived outages, at the cost of more setup and ongoing budget-management discipline.

## Multi-Tenant Deployments

When one Nautobot serves multiple customer tenants, or when a managed-services team operates many independent deployments behind a shared Prometheus and Alertmanager, alert rules need a tenant label to route correctly.

Typical patterns:

- **At scrape time**: add a `customer="..."` or `tenant="..."` label to each Nautobot's scrape target (Prometheus `relabel_configs`) so every series carries the identifier.
- **At rule time**: include the tenant label in the alert's `labels` block, then map labels to receivers in the Alertmanager `route` tree.

The same approach applies to log aggregators — promote the tenant label to a Loki label or an Elastic field, then build dashboards and queries per-tenant rather than pivoting the union after the fact.

## Worked Example: 3 a.m. Page

Walking through a typical paging incident clarifies how the signals on this page fit together. The scenario: at 3 a.m., the on-call engineer is paged for `NautobotJobFailures` on a production deployment.

1. **Read the alert annotation.** The `summary` line names the Job: `Network Sync` is failing.
2. **Open the metrics dashboard.** Confirm `nautobot_worker_finished_jobs{name="Network Sync", status="FAILURE"}` is increasing. Cross-check `nautobot_worker_started_jobs` to see whether new runs are still being kicked off (Beat is working) or whether the failures are stuck retries.
3. **Look at `nautobot_worker_exception_jobs{exception=...}`** for the same Job. The label tells you the exception class: `OperationalError` (database) vs `ConnectionError` (downstream device) vs `TimeoutError` (the Job itself running long).
4. **Jump to the aggregator.** Search `name="nautobot.jobs.network_sync"` with `levelname="ERROR"` over the last hour. Read the tracebacks to confirm the root cause.
5. **Cross-check the Job Result UI** when you need to coordinate with the Job author — `/extras/job-results/?status=failure&name=Network+Sync` shows the user-facing failure summary and the structured `JobLogEntry` rows.
6. **Decide remediation.** Database error: page the DB team or check `health_check_database_info`. Device error: page the network team. Timeout: temporarily disable the Job via the Job admin page (`/extras/jobs/`) and file a ticket for follow-up.

The progression — metric → exception class → log traceback → Job Result UI — is the standard investigative flow for any Nautobot-level alert. Going in the opposite order (starting from `/extras/job-results/` and clicking through) works but is slower, and is harder to scope when the failure spans multiple Job runs or originates outside Nautobot itself.

## Kubernetes Scrape-Target Pitfall

This section assumes you've already wired the per-component Kubernetes probes from [Health Checks — Kubernetes Deployments](./health-checks.md#kubernetes-deployments). The probes and the scrape-target configuration below are complementary: probes tell the kubelet when to restart, scrape configuration tells Prometheus where to fetch metrics from.

Every Celery worker Pod exposes its **own** `/metrics` endpoint with its own counters. The Nautobot `Service` VIP load-balances to web pods only and **does not** surface worker counters at all.

Use Pod-level service discovery so each worker becomes its own scrape target:

```yaml
# Prometheus Operator example
apiVersion: monitoring.coreos.com/v1
kind: PodMonitor
metadata:
  name: nautobot-workers
spec:
  selector:
    matchLabels:
      app.kubernetes.io/component: worker
  podMetricsEndpoints:
    - port: metrics
      path: /metrics
      interval: 30s
```

Without this, `nautobot_worker_*` series stay flat and Job-failure alerts never fire. Web-tier metrics are the canonical source for `health_check_*` and HTTP series, but **worker counters live exclusively on workers.**

!!! warning
    A common pitfall is to scrape the Nautobot `Service` only and assume workers are covered. They are not. Verify with `curl -s http://<worker-pod>:8001/metrics | grep nautobot_worker` against an individual worker Pod before trusting your dashboards.
