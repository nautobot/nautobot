# Prometheus Metrics

[Prometheus](https://prometheus.io/) is a popular time series metric platform used for monitoring. Nautobot supports optionally exposing native Prometheus metrics from the application and additionally, Nautobot App developers can also expose [custom metrics](../../../development/apps/api/prometheus.md) from their apps.

!!! note
    This page describes the system metrics Nautobot exposes and how to enable them.

    - For example alert rules built on top of these metrics, see [Alerting](./alerting.md).
    - For backing-store metrics that complement Nautobot's own — exposed via `redis_exporter` and `postgres_exporter` — see [Backing Stores](./backing-stores.md).
    - For the broader monitoring picture, see the [Monitoring overview](./index.md).
    - For application metrics (e.g. model counts), see [Capacity Metrics App](https://docs.nautobot.com/projects/capacity-metrics/en/stable/).

## Configuration

Metrics are not exposed by default. Metric exposition can be toggled with the `METRICS_ENABLED` configuration setting which exposes metrics at the `/metrics` HTTP endpoint, e.g. `https://nautobot.local/metrics`.

In addition to the `METRICS_ENABLED` setting, database and/or caching metrics can also be enabled by changing the database engine and/or caching backends from `django.db.backends` / `django_redis.cache` to `django_prometheus.db.backends` / `django_prometheus.cache.backends.redis`:

```python
DATABASES = {
    "default": {
        # Other settings...
        "ENGINE": "django_prometheus.db.backends.postgresql",  # use "django_prometheus.db.backends.mysql" with MySQL
    }
}

# Other settings...
CACHES = {
    "default": {
        # Other settings...
        "BACKEND": "django_prometheus.cache.backends.redis.RedisCache",
    }
}
```

+++ 2.2.1
    In case the `/metrics` endpoint is not performant or not required, you can disable specific apps with the [`METRICS_DISABLED_APPS`](../configuration/settings.md#metrics_disabled_apps) configuration setting.

For more information see the [`django-prometheus`](https://github.com/korfuri/django-prometheus) docs.

## Authentication

+++ 2.1.5

Metrics by default do not require authentication to view. Authentication can be toggled with the [`METRICS_AUTHENTICATED`](../configuration/settings.md#metrics_authenticated) configuration setting. If set to `True`, this will require the user to be logged in or to use an API token. See [REST API Authentication](../../platform-functionality/rest-api/authentication.md) for more details on API authentication.

## Enabling Worker Metrics

The `nautobot_worker_*` counters listed further below are incremented from inside Job execution code, which runs on the Celery worker process, not the web server. Worker metric exposition is disabled by default: the worker does not stand up an HTTP endpoint for Prometheus scraping unless you opt in explicitly. As a result, those counters never appear on the web tier's `/metrics` and have no endpoint of their own until configured.

Set [`CELERY_WORKER_PROMETHEUS_PORTS`](../configuration/settings.md#celery_worker_prometheus_ports) in `nautobot_config.py`, or its environment-variable form `NAUTOBOT_CELERY_WORKER_PROMETHEUS_PORTS` (a comma-separated list of port numbers):

```python
# nautobot_config.py
CELERY_WORKER_PROMETHEUS_PORTS = [9876, 9877, 9878]
```

The list defines a port walk: each worker process tries the ports in order and binds the first one that is free. This handles the case of multiple worker processes on the same host as each takes a different port from the list. If every listed port is already taken, the worker logs `Cannot export Prometheus metrics from worker, no available ports in range.` and continues running without metric exposition.

!!! warning
    The endpoint lives at the root path (`/`) of the chosen port, not at `/metrics` as on the web tier. The worker uses `prometheus_client.start_http_server()`, which serves the entire response from `/`. To verify a worker is exposing metrics:

    ```bash
    curl http://<worker-host>:<port>/ | grep nautobot_worker
    ```

The counters only show non-zero values after at least one Job has actually run on that specific worker.

For the broader Kubernetes scrape-target story and the common pitfall of pointing Prometheus at the Nautobot `Service` VIP instead of individual worker Pods, see [Kubernetes Scrape-Target Pitfall](#kubernetes-scrape-target-pitfall) below.

## Scraping the Endpoint

Any Prometheus-compatible scraper can pull `/metrics`. The example below uses Telegraf with the `inputs.prometheus` plugin; the same pattern applies to Prometheus itself, the OpenTelemetry Collector, Grafana Alloy, or Datadog's OpenMetrics check. For unauthenticated endpoints, drop the `http_headers` line.

```toml
[[inputs.prometheus]]
urls = ["http://localhost/metrics"]
metric_version=2
http_headers = {"Authorization" = "Token 0123456789abcdef0123456789abcdef01234567"}
```

### Kubernetes Scrape-Target Pitfall

!!! warning
    A common pitfall is to scrape the Nautobot `Service` only and assume workers are covered - they are not. Every Celery worker Pod exposes its own `/metrics` endpoint with its own counters. The Nautobot `Service` VIP load-balances to web pods only and does not surface worker counters at all.

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

Without this, `nautobot_worker_*` series stay flat and Job-failure alerts never fire. Web-tier metrics are the canonical source for `health_check_*` and HTTP series, but worker counters live exclusively on workers.

## Metric Types

Nautobot makes use of the [`django-prometheus`](https://github.com/korfuri/django-prometheus) library to export a number of different types of metrics, including:

- Per model insert, update, and delete counters
- Per view request counters
- Per view request latency histograms
- Request body size histograms
- Response body size histograms
- Response code counters
- Database connection, execution, and error counters
- Cache hit, miss, and invalidation counters
- Django middleware latency histograms
- Other Django related metadata metrics

### View Latency Histograms

Two of the histograms in the list above are the load-bearing series for the "is Nautobot fast enough?" question that drives most operator-side performance work:

| Series | Scope | Labels |
|---|---|---|
| `django_http_requests_latency_including_middlewares_seconds` | Full round-trip time (middleware + view + response rendering) | (none) |
| `django_http_requests_latency_seconds_by_view_method` | View-only processing time | `view`, `method` |

!!! info
    - For headline numbers (a single "Nautobot p99"), use the global histogram.
    - For the per-view question that drives most investigation — "which page is slow?" — use the `_by_view_method` histogram with `histogram_quantile`:

```promql
# p99 latency, per Nautobot view, over the last 5 minutes
histogram_quantile(
  0.99,
  sum by (le, view) (
    rate(django_http_requests_latency_seconds_by_view_method_bucket{view!=""}[5m])
  )
)
```

The `view` label uses Django's view-name format — `dcim:device_list`, `dcim:device`, `extras:jobresult`, and so on. Filter out `view=""` (unmatched URLs, typically 404s) from aggregations to keep results interpretable.

Middleware time is small relative to view time for Nautobot — the ORM and database dominate — so dashboards and SLOs framed around `_by_view_method` are reasonable proxies for user-perceived latency. Reach for the `_including_middlewares` histogram only when you specifically need to attribute time to middleware (e.g., a regression after adding an auth backend).

!!! info
    - For dashboards built on these histograms, see [Visualization — View Latency](./visualization.md#6-view-latency).
    - For per-view SLOs and burn-rate alerts, see [SLAs and SLOs — Worked Example: Device List Page SLO](./slas-and-slos.md#worked-example-device-list-page-slo) and [Alerting — View Latency Alerts](./alerting.md#view-latency-alerts).

Additionally, there are a number of metrics custom to Nautobot specifically:

| Name                                 | Description                                                                | Type    | Labels | Exposed By |
|--------------------------------------|----------------------------------------------------------------------------|---------|--------|------------|
| `health_check_database_info`         | Result of the last database health check. Value is `1` (up), `0` (down), or `-1` (unknown — check has not run yet on this process). | Gauge   | (none) | Web Server |
| `health_check_redis_backend_info`    | Result of the last Redis health check. Same value semantics as the database check above. | Gauge   | (none) | Web Server |
| `nautobot_app_metrics_processing_ms` | The time it took to collect custom app metrics from all installed apps. Useful for detecting an App with a slow custom-metric collector — a sustained increase points at the App, not Nautobot core. | Gauge   | (none) | Web Server |
| `nautobot_worker_started_jobs`       | The amount of jobs that were started                                       | Counter | `job_class_name`, `module_name` | Worker |
| `nautobot_worker_finished_jobs`      | The amount of jobs that were finished                                      | Counter | `job_class_name`, `module_name`, `status` | Worker |
| `nautobot_worker_exception_jobs`     | The amount of jobs that ran into an exception                              | Counter | `job_class_name`, `module_name`, `exception_type` | Worker |
| `nautobot_worker_singleton_conflict` | The amount of jobs that encountered a closed singleton lock                | Counter | `job_class_name`, `module_name` | Worker |

!!! info "Label semantics"
    Use these labels in `sum by (...)` aggregations and in alert annotations.

    - `job_class_name` is the Python class name (e.g. `MyDeviceSync`), not the human-readable `Meta.name` (e.g. `My Device Sync`).
    - `status` values match Celery's task-state strings (`SUCCESS`, `FAILURE`, `REJECTED`, `IGNORED`).
    - `exception_type` is the short class name of the raised exception (e.g. `OperationalError`).

Due to the multitude of possible deployment scenarios (web server and worker co-hosted on the same machine or not, different possible entrypoint commands for both contexts) some of the metrics exposed for specific components may also be present on the other component. It is up to the operator to account for this when working with the resulting metrics.

These for example give you the option to identify the individual failure/exception rates of specific jobs. Note that all of these metrics are per instance. Thus, you need to perform aggregations in your visualizations in order to get a complete picture if you are using multiple web servers and/or workers.

!!! note
    - For example PromQL alert rules built on `nautobot_worker_finished_jobs`, `nautobot_worker_exception_jobs`, and the health-check gauges, see [Alerting — Sample PromQL Rules](./alerting.md#sample-promql-rules).
    - For Celery-specific reliability tuning that drives several of these counters, see [Celery and Jobs](./celery-jobs.md).
    - For the exhaustive list of exposed metrics, visit the `/metrics` endpoint on your Nautobot instance.
    - For further information about the different metrics types, see the [relevant Prometheus documentation](https://prometheus.io/docs/concepts/metric_types/).

## Multi Processing Notes

When deploying Nautobot in a multi-process manner (e.g. running multiple uWSGI workers) the Prometheus client library requires the use of a shared directory to collect metrics from all worker processes. To configure this, first create or designate a local directory to which the worker processes have read and write access, and then configure your WSGI service (e.g. uWSGI) to define this path as the `prometheus_multiproc_dir` environment variable.

Since the files stored in the designated directory are not meant to be long-lived, it is recommended to use a temporary directory such as `/tmp/nautobot_prometheus` or an `emptyDir` in Kubernetes environments for this purpose. Additionally, in order to avoid scraping delays induced by the processing of orphaned files, this directory must be wiped on a regular basis. In order to avoid removal of files that are still in use, it is recommended to do this before the uWSGI process starts.

!!! note
    The code snippets below are meant to be examples of how to perform the necessary cleanup. The exact implementation may vary based on your specific deployment and operational needs.

Indicatively, you could use the `hook-accepting1` uWSGI hook to perform this:

```ini
; uwsgi.ini
; Before first worker starts accept request
hook-accepting1 = exec:bash -c 'if [[ $prometheus_multiproc_dir ]]; then rm $prometheus_multiproc_dir/*.db; else echo "No prometheus multi_proc_dir"; fi'
```

For environments where it's not enough to rely on cleanups based on worker restarts, a more fitting approach is to clean up in a periodic manner, while uWSGI is running. You can use a cron job or similar scheduled task to clean up orphan files, for example:

1. Create a Python script that scans the multiproc directory and removes files belonging to PIDs that are no longer running.

    ```python
    import os
    import re
    import shutil
    import time
    from contextlib import suppress

    import uwsgi
    from prometheus_client import multiprocess

    # Minimum age of files to consider for cleanup (e.g., 1 hour)
    MIN_AGE_SECONDS = 3600

    def cleanup_orphaned_prom_metric_files(metrics_dir):
        """
        Scans the multiproc directory and removes files
        belonging to PIDs that are no longer running.
        """
        if not os.path.exists(metrics_dir):
            return

        # Pattern to find PIDs in filenames (e.g., gauge_multiproc_123.db)
        pid_pattern = re.compile(r'.+_(\d+)\.db$')

        # Get list of currently running PIDs
        active_pids = set()
        for pid in os.listdir('/proc'):
            if pid.isdigit():
                active_pids.add(int(pid))

        for filename in os.listdir(metrics_dir):
            match = pid_pattern.match(filename)
            if match:
                try:
                    file_pid = int(match.group(1))
                except ValueError:
                    continue

                # If the PID from the file is not in the active PID list
                # Only consider files older than 1 hour to avoid race conditions
                file_path = os.path.join(metrics_dir, filename)
                file_mtime = os.path.getmtime(file_path)
                file_age_seconds = time.time() - file_mtime
                if (file_pid not in active_pids) and (file_age_seconds > MIN_AGE_SECONDS):
                    try:
                        # 1. Tell the client to "forget" the process
                        multiprocess.mark_process_dead(file_pid)
                        # 2. Delete the physical file, ignore if it was already removed
                        with suppress(FileNotFoundError):
                           os.remove(file_path)
                        print(f"Cleaned up orphaned metric file: {filename}")
                    except OSError as e:
                        print(f"Error deleting {filename}: {e}")

    # Schedule this script to run at regular intervals using uWSGI's `timer` feature.
    def cleanup_timer(signum):
        cleanup_orphaned_prom_metric_files(os.getenv('prometheus_multiproc_dir'))

    # Register only on the first worker to avoid multiple workers trying to clean up at the same time
    if uwsgi.worker_id() == 0:
        uwsgi.register_signal(99, "", cleanup_timer)
        uwsgi.add_timer(99, 3600) # this is 1 hour in seconds

    ```

2. Copy the file to a specific path (eg. `/opt/nautobot/media/prometheus_cleanup.py`) and import it from uwsgi.ini file.

    ```ini
    pythonpath = /opt/nautobot/media
    py-import = prometheus_cleanup
    ```

The implementation described above is a mere example. The same functionality can be achieved with a different approach, for example by using a separate script that is executed by a cron job or similar scheduled task instead of using uWSGI's `timer` feature. Another interesting approach would be to introduce uWSGI mules ([documentation](https://uwsgi.readthedocs.io/en/latest/Mules.html)) to avoid interrupting the main uwsgi process. The important part is to ensure that the cleanup process is running at regular intervals to prevent the accumulation of orphaned metric files.

Relevant documentation:

- [Prometheus client library multi-process mode](https://prometheus.github.io/client_python/multiprocess/)
- [Django Prometheus multi-process mode documentation](https://github.com/django-commons/django-prometheus/blob/master/documentation/exports.md)
