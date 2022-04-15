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

For more information see the [django-prometheus](https://github.com/korfuri/django-prometheus) docs.

## Metric Types

Nautobot makes use of the [django-prometheus](https://github.com/korfuri/django-prometheus) library to export a number of different types of metrics, including:

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

For the exhaustive list of exposed metrics, visit the `/metrics` endpoint on your Nautobot instance.

## Multi Processing Notes

When deploying Nautobot in a multi-process manner (e.g. running multiple uWSGI workers) the Prometheus client library requires the use of a shared directory to collect metrics from all worker processes. To configure this, first create or designate a local directory to which the worker processes have read and write access, and then configure your WSGI service (e.g. uWSGI) to define this path as the `prometheus_multiproc_dir` environment variable.

!!! warning
    If having accurate long-term metrics in a multi-process environment is crucial to your deployment, it's recommended you use the `uwsgi` library instead of `gunicorn`. The issue lies in the way `gunicorn` tracks worker processes (vs `uwsgi`) which helps manage the metrics files created by the above configurations. If you're using Nautobot with gunicorn in a containerized environment following the one-process-per-container methodology, then you will likely not need to change to `uwsgi`. More details can be found in  [issue #3779](https://github.com/netbox-community/netbox/issues/3779#issuecomment-590547562).

!!! note
    Metrics from the celery worker are not available from Nautobot at this time.  However, additional tools such as [flower](https://flower.readthedocs.io/en/latest/) can be used to monitor the celery workers until these metrics are exposed through Nautobot.
