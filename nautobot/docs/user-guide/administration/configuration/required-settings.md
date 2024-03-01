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
{% for property, attrs in settings_data.properties.items() if attrs.is_required_setting|default(false) %}

---

## `{{ property }}`

{% if attrs.version_added|default(None) %}
+++ {{ attrs.version_added }}
{% endif %}

{% if attrs.default_literal|default(None) %}
**Default:**

{{ attrs.default_literal }}
{% else %}
{% with default = attrs.default|default(None) %}
**Default:**
{% if default is string %}`"{{ default }}"`
{% elif default is boolean %}`{{ default|title }}`
{% elif default is mapping and default != {} %}

```python
{{ default|pprint }}
```

{% else %}`{{ default }}`
{% endif %}
{% endwith %}
{% endif %}

{% if attrs.enum|default(None) %}
**Permitted Values:**

{% for enum in attrs.enum %}
* `{{ enum|pprint }}`
{% endfor %}
{% endif %}

{% if attrs.environment_variable|default(None) %}
**Environment Variable:** `{{ attrs.environment_variable }}`
{% elif attrs.properties|default(None) != None and attrs.properties.default|default(None) != None %}
{% for property_attrs in attrs.properties.default.properties.values() if property_attrs.environment_variable|default(None) %}
{% if loop.first %}
**Environment Variables:**

{% endif %}
* `{{ property_attrs.environment_variable }}`
{% endfor %}
{% elif attrs.properties|default(None) != None %}
{% for property_attrs in attrs.properties.values() if property_attrs.environment_variable|default(None) %}
{% if loop.first %}
**Environment Variables:**

{% endif %}
* `{{ property_attrs.environment_variable }}`
{% endfor %}
{% endif %}

{{ attrs.description|default("") }}

{{ attrs.details|default("") }}

{% if attrs.see_also|default({}) %}
**See Also:**

{% for text, url in attrs.see_also.items() %}
* [{{ text }}]({{ url }})
{% endfor %}
{% endif %}

{% endfor %}
