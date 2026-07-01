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

| Panel | Type | Datasource | Query |
|---|---|---|---|
| Database health | Stat (binary) | Prometheus | `health_check_database_info` |
| Redis health | Stat (binary) | Prometheus | `health_check_redis_backend_info` |
| Web pods up | Stat | Prometheus | `count(up{job="nautobot-web"} == 1)` |
| Worker pods up | Stat | Prometheus | `count(up{job="nautobot-worker"} == 1)` |
| HTTP 5xx rate (5 min) | Time series | Prometheus | `sum(rate(django_http_responses_total_by_status_total{status=~"5.."}[5m]))` |
| Job failure rate (5 min) | Time series | Prometheus | `sum by (job_class_name) (rate(nautobot_worker_finished_jobs{status="FAILURE"}[5m]))` |

### 2. Job Execution

For diagnosing Job-side failures. Surfaces what Jobs are running, how fast they finish, and which exception classes dominate.

| Panel | Type | Datasource | Query |
|---|---|---|---|
| Started vs finished, per Job class | Time series | Prometheus | `sum by (job_class_name) (increase(nautobot_worker_started_jobs[$__rate_interval]))` overlaid with `sum by (job_class_name) (increase(nautobot_worker_finished_jobs[$__rate_interval]))` |
| Exception class distribution | Stacked bar | Prometheus | `sum by (exception_type) (increase(nautobot_worker_exception_jobs[1h]))` |
| Singleton conflict rate | Time series | Prometheus | `sum(rate(nautobot_worker_singleton_conflict[5m]))` |
| Queue depth (per queue) | Time series | Prometheus (via `celery-exporter`) | `celery_queue_length` |
| Failure heatmap | Heatmap | Prometheus | `sum by (job_class_name) (rate(nautobot_worker_finished_jobs{status="FAILURE"}[$__rate_interval]))` |
| Job runtime p50 / p95 / p99 (per task) | Time series | Prometheus (via `celery-exporter`) | `histogram_quantile(0.5, sum by (le, name) (rate(celery_task_runtime_seconds_bucket[5m])))` — repeat with `0.95` and `0.99` for the higher quantiles |
| Slowest Job runs (last 24h) | Table | PostgreSQL (direct) | See SQL below |

#### Monitoring Job Execution Duration

Nautobot's own `/metrics` exposes Job *counts* (`nautobot_worker_started_jobs`, `nautobot_worker_finished_jobs`) but not Job *durations*. Two complementary sources cover the duration question:

- **`celery-exporter`** — exposes `celery_task_runtime_seconds` as a Prometheus histogram, labeled by Celery task name. Use it for time-series quantiles, dashboards, and SLO computations. This is the right source whenever "how does this Job class's runtime look over time?" is the question.
- **Direct PostgreSQL** — `extras_jobresult.date_done - extras_jobresult.created` gives the exact per-run duration. Use it for ad-hoc "which specific runs were the slowest yesterday?" investigations and for tables where you need per-run granularity that a histogram cannot provide.

```sql
-- Slowest Job runs in the last 24 hours
SELECT name,
       EXTRACT(EPOCH FROM (date_done - created)) AS duration_seconds,
       created,
       status
FROM extras_jobresult
WHERE date_done IS NOT NULL
  AND created > NOW() - INTERVAL '24 hours'
ORDER BY duration_seconds DESC
LIMIT 20;
```

Pair the p99 runtime time series with the failure heatmap above on the same dashboard row — a Job that is suddenly running slower than usual very often fails next, and seeing the two trends side-by-side makes the connection visible.

### 3. Backing Stores

Redis and PostgreSQL signals on one page. Pair with the slowlog and `pg_stat_statements` queries in [Backing Stores](./backing-stores.md) when something flags here and you need to drill in.

| Panel | Type | Datasource | Query |
|---|---|---|---|
| Redis memory used / max | Gauge | Prometheus (via `redis_exporter`) | `redis_memory_used_bytes / redis_memory_max_bytes` |
| Redis evicted keys (rate) | Time series | Prometheus (via `redis_exporter`) | `rate(redis_evicted_keys_total[5m])` |
| Redis blocked clients | Time series | Prometheus (via `redis_exporter`) | `redis_blocked_clients` |
| PostgreSQL connections | Time series | Prometheus (via `postgres_exporter`) | `pg_stat_database_numbackends` |
| PostgreSQL transaction rate | Time series | Prometheus (via `postgres_exporter`) | `rate(pg_stat_database_xact_commit[5m])` and `rate(pg_stat_database_xact_rollback[5m])` |
| Replication lag (HA) | Time series | Prometheus (via `postgres_exporter`) | `pg_stat_replication_replay_lag` |
| PgBouncer pool saturation | Gauge | Prometheus (via `pgbouncer_exporter`) | `pgbouncer_pools_server_active_connections / max_server_connections` |
| Disk-fill projection (30 days) | Time series | Prometheus (via `node_exporter`) | `predict_linear(node_filesystem_avail_bytes{mountpoint=~".*postgres.*"}[7d], 30 * 24 * 3600)` |

### 4. Scheduled Jobs

For deployments where Beat-driven automation is operationally important.

| Panel | Type | Datasource | Query |
|---|---|---|---|
| Beat heartbeat freshness | Stat | Probe output | Derived from the Beat heartbeat-file probe — see [Health Checks — Nautobot Celery Beat](./health-checks.md#nautobot-celery-beat) |
| Schedules due but not fired | Table | PostgreSQL (direct) | `SELECT name, last_run_at, next_run_at FROM extras_scheduledjob WHERE enabled = true AND next_run_at < NOW() - INTERVAL '5 minutes';` |
| Scheduled-Job invocation count (24h) | Bar chart | Log aggregator | Query against `nautobot.extras.jobs` log records, grouped by Job name |

### 5. SLO Performance

For deployments that have defined explicit Service Level Objectives — see [SLAs and SLOs](./slas-and-slos.md) for the framing and starting values.

| Panel | Type | Datasource | Query (example: Job success SLO of 99% over 30 days) |
|---|---|---|---|
| Current SLI value (rolling window) | Stat | Prometheus | `sum(rate(nautobot_worker_finished_jobs{status="SUCCESS"}[30d])) / sum(rate(nautobot_worker_finished_jobs[30d]))` |
| Error budget remaining | Gauge | Prometheus | `1 - ((1 - sum(rate(...{status="SUCCESS"}[30d])) / sum(rate(...[30d]))) / 0.01)` (replace `0.01` with `1 - SLO`) |
| 1h burn rate | Time series | Prometheus | `(sum(rate(nautobot_worker_finished_jobs{status="FAILURE"}[1h])) / sum(rate(nautobot_worker_finished_jobs[1h]))) / 0.01` |
| 6h burn rate | Time series | Prometheus | Same with `[6h]` window |

A burn-rate panel rendered with horizontal threshold lines at `1×`, `6×`, and `14.4×` makes the budget-consumption picture readable at a glance and ties directly to the alert rules in [SLAs and SLOs — Error Budget Alerting](./slas-and-slos.md#error-budget-alerting).

### 6. View Latency

For the single most common Nautobot performance complaint — "page X is slow." Built on the histograms exposed by `django-prometheus`; see [Prometheus Metrics — View Latency Histograms](./prometheus-metrics.md#view-latency-histograms) for the metric anatomy.

| Panel | Type | Datasource | Query |
|---|---|---|---|
| Global p99 (last 5 min) | Stat | Prometheus | `histogram_quantile(0.99, sum by (le) (rate(django_http_requests_latency_including_middlewares_seconds_bucket[5m])))` |
| Top 10 slowest views by p99 (last 1h) | Table | Prometheus | `topk(10, histogram_quantile(0.99, sum by (le, view) (rate(django_http_requests_latency_seconds_by_view_method_bucket{view!=""}[1h]))))` |
| p99 latency over time, top-10 views | Time series | Prometheus | Same query as above, but rendered over the dashboard's time range |
| Latency heatmap (all views) | Heatmap | Prometheus | `sum by (le) (rate(django_http_requests_latency_seconds_by_view_method_bucket{view!=""}[5m]))` |
| Request rate per view | Time series | Prometheus | `sum by (view) (rate(django_http_requests_latency_seconds_by_view_method_count{view!=""}[5m]))` |

Combine the Top-10 table with the request-rate panel side-by-side: a view that takes 8 seconds once an hour is a different problem from a view that takes 800 ms 50 times per second, and operator priorities differ accordingly. The heatmap is the panel that catches *bimodal* latency distributions — a view that is usually fast but has a long tail — which a p99 time series alone hides behind a single line.

For the SLI/SLO framing of the same data, see [SLAs and SLOs — Worked Example: Device List Page SLO](./slas-and-slos.md#worked-example-device-list-page-slo); for per-request investigation of a specific slow view, see [Request Profiling](./request-profiling.md).

## Log Annotations on Metric Panels

Grafana lets you overlay log lines from a Loki / Elastic / Splunk datasource as [annotation](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/annotate-visualizations/) marks on top of any metric panel. The result is a metric trend with vertical bars where notable log events fired — the most common "why did this metric move?" question is answered without leaving the panel. The synergy is real: a counter going non-zero is informative, but the same counter going non-zero with a labeled `ERROR` mark from `nautobot.extras.plugins` on the same tick is diagnosable.

Three Nautobot recipes that consistently earn their keep on the dashboards above:

### Job Failures Overlaid on Job Execution

On the Job Execution dashboard's "Started vs finished" panel, add an annotation query against your log aggregator that pulls `levelname=ERROR` events from the Jobs framework and per-Job loggers:

```logql
{app="nautobot",component="worker"} | json | name=~"nautobot\\.jobs\\..*|nautobot\\.extras\\.jobs" | levelname="ERROR"
```

Each FAILURE traceback becomes a vertical mark on the panel exactly when the corresponding `nautobot_worker_finished_jobs{status="FAILURE"}` counter ticks, making the cause discoverable in one click.

### App Initialization Errors on Health Overview

After a deploy, web-pod availability sometimes flatlines because an App's `ready()` raised an exception during startup. Overlay an annotation query on the "Web pods up" panel pulling `nautobot.extras.plugins` ERROR events:

```logql
{app="nautobot"} | json | name="nautobot.extras.plugins" | levelname="ERROR"
```

The dip in the metric and the annotation arrive together, so the regression is attributable to the deploy rather than to "something with the cluster."

### Beat Schedule Disables on Scheduled Jobs

A drop in the Scheduled-Job invocation panel is ambiguous — Beat is broken, or Beat itself auto-disabled the schedule? An annotation query pulling `Disabling schedule` events from the Beat logger disambiguates:

```logql
{app="nautobot",component="beat"} |~ "Disabling schedule"
```

The pattern generalizes — any time a metric panel's question is "did Nautobot itself emit a corresponding event?", an annotation query is the cheapest way to answer it inside the panel.

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
