---
render_macros: true
---

# Required Configuration Settings

## Redis Settings

[Redis](https://redis.io/) is an in-memory data store similar to memcached. It is required to support Nautobot's
caching, task queueing, and webhook features. The connection settings are explained here, allowing Nautobot to connect
to different Redis instances/databases per feature.

!!! warning
    It is highly recommended to keep the Redis databases for caching and tasks separate. Using the same database number on the same Redis instance for both may result in queued background tasks being lost during cache flushing events. For this reason, the default settings utilize database `1` for caching and database `0` for tasks.

!!! tip
    The default Redis settings in your `nautobot_config.py` should be suitable for most deployments and should only require customization for more advanced configurations.

### Task Queuing with Celery

+++ 1.1.0

Out of the box you do not need to make any changes to utilize task queueing with Celery. All of the default settings are sufficient for most installations.

In the event you do need to make customizations to how Celery interacts with the message broker such as for more advanced clustered deployments, the following settings may be changed:

* [`CELERY_BROKER_URL`](./optional-settings.md#celery_broker_url)
* [`CELERY_BROKER_USE_SSL`](./optional-settings.md#celery_broker_use_ssl)
* [`CELERY_REDIS_BACKEND_USE_SSL`](./optional-settings.md#celery_redis_backend_use_ssl)

#### Configuring Celery for High Availability

High availability clustering of Redis for use with Celery can be performed using Redis Sentinel. Please see documentation section on configuring [Celery for Redis Sentinel](../../administration/guides/caching.md#celery-sentinel-configuration) for more information.

<!-- markdownlint-disable blanks-around-lists -->

{% with header="##", required=true %}

{% include "/user-guide/administration/configuration/render-settings-fragment.j2" %}

{% endwith %}

<!-- markdownlint-enable blanks-around-lists -->
