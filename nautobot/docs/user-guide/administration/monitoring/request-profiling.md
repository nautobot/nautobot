# Request Profiling

Nautobot offers advanced request profiling through [`django-silk`](https://github.com/jazzband/django-silk). This allows administrators to collect debug information about user activities, which can be used to troubleshoot issues with the system.

Request Profiling captures the **per-request** picture: SQL queries issued, cache calls made, and a Python cProfile trace of the call stack. It is complementary to the aggregate views in the rest of this section:

- [Prometheus Metrics](./prometheus-metrics.md) — Django request-latency histograms across all traffic.
- [Backing Stores — `pg_stat_statements`](./backing-stores.md#pg_stat_statements) — aggregate slow-query stats across the whole database, independent of which view issued them.
- [Backing Stores — Redis Slowlog](./backing-stores.md#redis-slowlog) — slow Redis commands, also without per-request attribution.

Use Request Profiling when you have a specific slow URL or Job and need to trace it back to a query plan or a tight Python loop. Use the aggregate tools when you don't yet know *which* request to look at. See the [Monitoring overview](./index.md) for the broader picture.

## User Setting

Request profiling may be enabled by individual users in their profile within the web interface. This can be found under the "Advanced Settings" section.

![user advanced settings](../../../media/user-guide/administration/guides/request-profiling/advanced-settings-light.png#only-light){ .on-glb }
![user advanced settings](../../../media/user-guide/administration/guides/request-profiling/advanced-settings-dark.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/users/advanced-settings/`"

Once a user enables request profiling, all subsequent HTTP requests made by that specific user to the system will be logged by `django-silk`. This setting will persist until the user either logs out or disables the setting in their profile.

### User Setting Notes

- While this feature may be visible within the profile configuration, you will only be able to toggle on/off, once the global configuration option `ALLOW_REQUEST_PROFILING` has been enabled (described further on).

- *Warning!* Enabling request profiling on a user will impact the overall performance of Nautobot greatly! It is recommended to disable request profiling for the user when not actively being used.

- `django-silk` persists each profiled request — including SQL queries, the cProfile trace, and downloadable `.prof` binaries — to its own database tables and on-disk media. A long-running profiling session can accumulate substantial data; bound it with `SILKY_MAX_RECORDED_REQUESTS` and / or periodically run silk's `silk_clear_request_log` management command. See the [`django-silk` configuration reference](https://github.com/jazzband/django-silk#configuration) for the full list of retention knobs.

## Silk UI

Nautobot administrators with super-user permissions can access the `django-silk` UI at the `/silk/` URL.

![silk ui](../../../media/user-guide/administration/guides/request-profiling/silk-ui.png#only-light){ .on-glb }
![silk ui](../../../media/user-guide/administration/guides/request-profiling/silk-ui.png#only-dark){ .on-glb }
[//]: # "`https://next.demo.nautobot.com/silk/`"

From there, administrators can view details of individual requests, including timing, SQL queries, and cProfile artifacts.

## Configuration

The Nautobot configuration comes out of the box with `django-silk` set up to support the above functionality. Those settings are described below, but it is not the intention of the Nautobot docs to describe all `django-silk` settings. Django-silk provides several other parameters that knowledgeable users may also be able to use, depending on the use case.

### `ALLOW_REQUEST_PROFILING`

Default: `False`

Global setting to allow or deny users from enabling request profiling on their login session.

---

### `SILKY_PYTHON_PROFILER`

Default: `True`

Enables use of the built-in Python cProfile profiler.

---

### `SILKY_PYTHON_PROFILER_BINARY`

Default: `True`

Generates a binary `.prof` file for each profiled request, which can be downloaded.

---

### `SILKY_PYTHON_PROFILER_EXTENDED_FILE_NAME`

Default: `True`

Adds part of the request URL path to the profile file name to make it easier to identify specific requests.

---

### `SILKY_INTERCEPT_FUNC`

Default: `nautobot.core.settings.silk_request_logging_intercept_logic`

This defines a custom function that filters requests to be profiled. Notably, the default looks for the user session flag described above.

---

### `SILKY_AUTHENTICATION`

Default: `True`

Users must be authenticated to access the `django-silk` UI.

---

### `SILKY_AUTHORISATION`

Default: `True`

Users must have permissions to access the `django-silk` UI. Used in combination with `SILKY_AUTHENTICATION`.

---

### `SILKY_PERMISSIONS`

Default: `nautobot.core.settings.silk_user_permissions`

This ensures the users must be a superuser of the system to access the `django-silk` UI. Used in combination with `SILKY_AUTHENTICATION` and `SILKY_AUTHORISATION`.
