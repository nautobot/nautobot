# Alerting

This page describes a low-noise alert ruleset for production Nautobot. The recommendations assume that:

- Prometheus metrics are enabled (`NAUTOBOT_METRICS_ENABLED=True`); see [Prometheus Metrics](./prometheus-metrics.md).
- Health probes are wired into the orchestrator; see [Health Checks](./health-checks.md).
- Container `stdout` is shipped to a log aggregator with the logger name parsed as a structured field; see [Logging](./logging.md).

Alert primarily on health-checks and metrics. Use log keywords as a *secondary* signal, scoped to specific logger names.

!!! note "Living section"
    The rules and thresholds below are the starting points we currently recommend based on production deployments we've seen — they're not exhaustive and they're not deployment-tuned. Walk through your steady-state baseline before committing them to your alerting rules; what's "normal" depends heavily on Job mix, fleet size, and Beat schedule density. Contributions from your environment are welcome.

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
