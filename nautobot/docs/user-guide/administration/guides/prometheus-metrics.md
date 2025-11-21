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

!!! warning
    If having accurate long-term metrics in a multi-process environment is crucial to your deployment, it's recommended you use the `uwsgi` library instead of `gunicorn`. The issue lies in the way `gunicorn` tracks worker processes (vs `uwsgi`) which helps manage the metrics files created by the above configurations. If you're using Nautobot with gunicorn in a containerized environment following the one-process-per-container methodology, then you will likely not need to change to `uwsgi`. More details can be found in  [issue #3779](https://github.com/netbox-community/netbox/issues/3779#issuecomment-590547562).
