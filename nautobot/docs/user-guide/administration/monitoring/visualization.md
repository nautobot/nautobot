# Visualization

Once metrics flow into Prometheus and logs flow into your aggregator, the next step is making the signals easy to read at a glance. Alert rules tell you when something is wrong; dashboards show what "normal" looks like and where the trend is heading — context that turns a single page into an informed response. This page describes a recommended dashboard set for Nautobot built on top of [Grafana](https://grafana.com/grafana/), the de facto open-source visualization tool.

!!! note "Living section"
    The dashboards below are starting points based on what operators consistently find valuable. They are neither the only useful views nor exhaustive — extend them with the per-deployment panels that matter for your environment.

## Datasources

Grafana connects to the same sources that already produce Nautobot's monitoring signals. None of these are Nautobot-specific; configure them the same way you would for any Django + Celery deployment.

| Source | What it carries | Reference |
|---|---|---|
| Prometheus | Nautobot's `/metrics`, plus `redis_exporter`, `postgres_exporter`, `pgbouncer_exporter`, `celery-exporter` | [Prometheus Metrics](./prometheus-metrics.md), [Backing Stores](./backing-stores.md) |
| Loki / Splunk / Elastic / Datadog | Application logs from web, worker, and Beat `stdout` | [Logging](./logging.md) |
| PostgreSQL (direct) | Ad-hoc queries against `pg_stat_*` views and Nautobot tables | [Backing Stores — `pg_stat_statements`](./backing-stores.md#pg_stat_statements) |

In a typical deployment, most panels read from Prometheus, a smaller number of log-tier panels read from the aggregator, and one or two diagnostic panels read directly from PostgreSQL.

## Recommended Dashboard Set

A small set of focused dashboards works better than a single mega-dashboard. Each dashboard below answers a specific class of question, and the suggested PromQL is starting-point material — tune the labels, intervals, and grouping for your deployment.

### 1. Health Overview

The "is Nautobot OK right now?" dashboard. Designed to load in under a second and answer two questions: is the service up, and are the trends pointing the wrong way.

| Panel | Type | Query |
|---|---|---|
| Database health | Stat (binary) | `health_check_database_info` |
| Redis health | Stat (binary) | `health_check_redis_backend_info` |
| Web pods up | Stat | `count(up{job="nautobot-web"} == 1)` |
| Worker pods up | Stat | `count(up{job="nautobot-worker"} == 1)` |
| HTTP 5xx rate (5 min) | Time series | `sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))` |
| Job failure rate (5 min) | Time series | `sum by (job_class_name) (rate(nautobot_worker_finished_jobs{status="FAILURE"}[5m]))` |

### 2. Job Execution

For diagnosing Job-side failures. Surfaces what Jobs are running, how fast they finish, and which exception classes dominate.

| Panel | Type | Query |
|---|---|---|
| Started vs finished, per Job class | Time series | `sum by (job_class_name) (increase(nautobot_worker_started_jobs[$__rate_interval]))` overlaid with `sum by (job_class_name) (increase(nautobot_worker_finished_jobs[$__rate_interval]))` |
| Exception class distribution | Stacked bar | `sum by (exception_type) (increase(nautobot_worker_exception_jobs[1h]))` |
| Singleton conflict rate | Time series | `sum(rate(nautobot_worker_singleton_conflict[5m]))` |
| Queue depth (per queue) | Time series | `celery_queue_length` (from `celery-exporter`) |
| Failure heatmap | Heatmap | `sum by (job_class_name) (rate(nautobot_worker_finished_jobs{status="FAILURE"}[$__rate_interval]))` |

### 3. Backing Stores

Redis and PostgreSQL signals on one page. Pair with the slowlog and `pg_stat_statements` queries in [Backing Stores](./backing-stores.md) when something flags here and you need to drill in.

| Panel | Type | Query |
|---|---|---|
| Redis memory used / max | Gauge | `redis_memory_used_bytes / redis_memory_max_bytes` |
| Redis evicted keys (rate) | Time series | `rate(redis_evicted_keys_total[5m])` |
| Redis blocked clients | Time series | `redis_blocked_clients` |
| PostgreSQL connections | Time series | `pg_stat_database_numbackends` |
| PostgreSQL transaction rate | Time series | `rate(pg_stat_database_xact_commit[5m])` and `rate(pg_stat_database_xact_rollback[5m])` |
| Replication lag (HA) | Time series | `pg_stat_replication_replay_lag` |
| PgBouncer pool saturation | Gauge | `pgbouncer_pools_server_active_connections / max_server_connections` |
| Disk-fill projection (30 days) | Time series | `predict_linear(node_filesystem_avail_bytes{mountpoint=~".*postgres.*"}[7d], 30 * 24 * 3600)` |

### 4. Scheduled Jobs

For deployments where Beat-driven automation is operationally important.

| Panel | Type | Query |
|---|---|---|
| Beat heartbeat freshness | Stat | derived from the Beat heartbeat-file probe — see [Health Checks — Nautobot Celery Beat](./health-checks.md#nautobot-celery-beat) |
| Schedules due but not fired | Table | Direct PostgreSQL query: `SELECT name, last_run_at, next_run_at FROM extras_scheduledjob WHERE enabled = true AND next_run_at < NOW() - INTERVAL '5 minutes';` |
| Scheduled-Job invocation count (24h) | Bar chart | Aggregator query against `nautobot.extras.jobs` log records, grouped by Job name |

### 5. SLO Performance

For deployments that have defined explicit Service Level Objectives — see [SLAs and SLOs](./slas-and-slos.md) for the framing and starting values.

| Panel | Type | Query (example: Job success SLO of 99% over 30 days) |
|---|---|---|
| Current SLI value (rolling window) | Stat | `sum(rate(nautobot_worker_finished_jobs{status="SUCCESS"}[30d])) / sum(rate(nautobot_worker_finished_jobs[30d]))` |
| Error budget remaining | Gauge | `1 - ((1 - sum(rate(...{status="SUCCESS"}[30d])) / sum(rate(...[30d]))) / 0.01)` (replace `0.01` with `1 - SLO`) |
| 1h burn rate | Time series | `(sum(rate(nautobot_worker_finished_jobs{status="FAILURE"}[1h])) / sum(rate(nautobot_worker_finished_jobs[1h]))) / 0.01` |
| 6h burn rate | Time series | same with `[6h]` window |

A burn-rate panel rendered with horizontal threshold lines at `1×`, `6×`, and `14.4×` makes the budget-consumption picture readable at a glance and ties directly to the alert rules in [SLAs and SLOs — Error Budget Alerting](./slas-and-slos.md#error-budget-alerting).

## Panel Patterns

A few panel-type conventions that map well to Nautobot's metric shapes:

- **Binary up / down** (`health_check_*_info`, `up{job=...}`): use a **Stat** panel with green / red thresholds, not a time series. The chart looks the same any time you glance at it, which is the point.
- **Rate counters** (`*_total` series): wrap in `rate()` or `increase()` with a window matching your scrape interval — typically `[5m]` for fine grain, `[$__rate_interval]` for Grafana-managed windows. Plotting the raw counter is rarely useful.
- **Utilization** (memory, connections, pool slots): use a **Gauge** panel with thresholds at `0.7` (warning) and `0.9` (critical). Gauges communicate "how close to the limit" better than a time series.
- **Failure timelines** (`exception=...`, `status="FAILURE"`): use **stacked area** to see which exception classes contribute over time, not just the total.
- **Current state** (running Jobs, recent failures): use **Table** panels with explicit columns. Reduces visual scan time vs a time series with a thick line.

## Provisioning

Treat dashboards as code:

- Store the JSON definitions in source control alongside the rest of your monitoring stack.
- Use Grafana's [provisioning system](https://grafana.com/docs/grafana/latest/administration/provisioning/) (`provisioning/dashboards/`) to load them at startup, rather than hand-creating them through the UI.
- Parameterize environment-specific values with Grafana template variables (`$cluster`, `$tenant`, `$namespace`) so the same dashboard works across dev, staging, and production.

Avoid building everything from scratch — community Grafana dashboards for Prometheus, Redis, PostgreSQL, and Celery already exist in the [Grafana dashboard library](https://grafana.com/grafana/dashboards/). Nautobot-specific panels are most valuable when they sit alongside those existing dashboards rather than re-implementing what they already do well.

!!! info "On Our Radar"
    A maintained Grafana dashboard for Nautobot is on our radar. If and when one is published, this page will link to it as a vetted starting point — until then, the panel descriptions and queries above are the recommended foundation for building your own.

## Worked Example: A Compact Health View

A minimal four-panel "is Nautobot OK" overview, suitable as a 30-second-glance dashboard that lives on a wall display or a status page:

```text
+---------------------------+---------------------------+
| Database health           | Redis health              |
| health_check_database_    | health_check_redis_       |
| info                      | backend_info              |
+---------------------------+---------------------------+
| Job failure rate (1h)     | Workers up                |
| sum(rate(...{status=      | count(up{job=             |
| "FAILURE"}[1h]))          | "nautobot-worker"}==1)    |
+---------------------------+---------------------------+
```

- The two top stat panels swap green ↔ red on health-probe state. Set the thresholds at `< 1` red, `>= 1` green.
- The Job-failure panel renders a sparkline over the last hour, so the operator sees not just "we have failures" but "this just started."
- The workers-up panel turns red when worker count drops below the deployment's minimum (e.g. fewer than 2). Pair with the corresponding Tier 1 alert in [Alerting](./alerting.md).

This is enough to make "Nautobot is sick right now" visible at a glance; the deeper-dive dashboards above carry the investigative load when something is actually wrong.
