# Prometheus Metrics

Nautobot supports optionally exposing native Prometheus metrics from the application. [Prometheus](https://prometheus.io/) is a popular time series metric platform used for monitoring.

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

Metrics by default do not require authentication to view. Authentication can be toggled with the `METRICS_AUTHENTICATION` configuration setting. If set to `True`, this will require the user to be logged in or to use an API token. See [REST API Authentication](../../platform-functionality/rest-api/authentication.md) for more details on API authentication.

### Sample Telegraf configuration

```toml
[[inputs.prometheus]]
urls = ["http://localhost/metrics"]
metric_version=2
http_headers = {"Authorization" = "Token 0123456789abcdef0123456789abcdef01234567"}
```

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

Additionally, there are a number of metrics custom to Nautobot specifically:

| Name                                 | Description                                                                | Type    | Exposed By |
|--------------------------------------|----------------------------------------------------------------------------|---------|------------|
| `health_check_database_info`         | Result of the last database health check                                   | Gauge   | Web Server |
| `health_check_redis_backend_info`    | Result of the last redis health check                                      | Gauge   | Web Server |
| `nautobot_app_metrics_processing_ms` | The time it took to collect custom app metrics from all installed apps     | Gauge   | Web Server |
| `nautobot_worker_started_jobs`       | The amount of jobs that were started                                       | Counter | Worker     |
| `nautobot_worker_finished_jobs`      | The amount of jobs that were finished (incl. status label)                 | Counter | Worker     |
| `nautobot_worker_exception_jobs`     | The amount of jobs that ran into an exception (incl. exception type label) | Counter | Worker     |
| `nautobot_worker_singleton_conflict` | The amount of jobs that encountered a closed singleton lock                | Counter | Worker     |

!!! note
    Due to the multitude of possible deployment scenarios (web server and worker co-hosted on the same machine or not, different possible entrypoint commands for both contexts) some of the metrics exposed for specific components may also be present on the other component. It is up to the operator to account for this when working with the resulting metrics.

These for example give you the option to identify the individual failure/exception rates of specific jobs. Note that all of these metrics are per instance. Thus, you need to do perform aggregations in your visualizations in order to get a complete picture if you are using multiple web servers and/or workers.

For the exhaustive list of exposed metrics, visit the `/metrics` endpoint on your Nautobot instance. For further information about the different metrics types, see the [relevant Prometheus documentation](https://prometheus.io/docs/concepts/metric_types/).

## Multi Processing Notes

When deploying Nautobot in a multi-process manner (e.g. running multiple uWSGI workers) the Prometheus client library requires the use of a shared directory to collect metrics from all worker processes. To configure this, first create or designate a local directory to which the worker processes have read and write access, and then configure your WSGI service (e.g. uWSGI) to define this path as the `prometheus_multiproc_dir` environment variable.

Since the files stored in the designated directory are not meant to be long-lived, it is recommended to use a temporary directory such as `/tmp/nautobot_prometheus` or an `emptyDir` in Kubernetes environments for this purpose. Additionally, in order to avoid scraping delays induced by the processing of orphaned files, this directory must be wiped on a regular basis. In order to avoid removal of files that are still in use, it is recommended to do this before the uWSGI process starts.

> Note: the below code snippets are meant to be examples of how to perform the necessary cleanup. The exact implementation may vary based on your specific deployment and operational needs.

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
