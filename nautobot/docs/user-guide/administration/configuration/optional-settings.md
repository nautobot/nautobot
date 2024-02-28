# Optional Configuration Settings

## Administratively Configurable Settings

+++ 1.2.0

A number of settings can alternatively be configured via the Nautobot Admin UI. To do so, these settings must **not** be defined in your `nautobot_config.py`, as any settings defined there will take precedence over any values defined in the Admin UI. Settings that are currently configurable via the Admin UI include:

* [ALLOW_REQUEST_PROFILING](#allow_request_profiling)
* [BANNER_BOTTOM](#banner_bottom)
* [BANNER_LOGIN](#banner_login)
* [BANNER_TOP](#banner_top)
* [CHANGELOG_RETENTION](#changelog_retention)
* [DEPLOYMENT_ID](#deployment_id)
* [DEVICE_NAME_AS_NATURAL_KEY](#device_name_as_natural_key)
* [DYNAMIC_GROUPS_MEMBER_CACHE_TIMEOUT](#dynamic_groups_member_cache_timeout)
* [JOB_CREATE_FILE_MAX_SIZE](#job_create_file_max_size)
* [LOCATION_NAME_AS_NATURAL_KEY](#location_name_as_natural_key)
* [MAX_PAGE_SIZE](#max_page_size)
* [NETWORK_DRIVERS](#network_drivers)
* [PAGINATE_COUNT](#paginate_count)
* [PER_PAGE_DEFAULTS](#per_page_defaults)
* [PREFER_IPV4](#prefer_ipv4)
* [RACK_ELEVATION_DEFAULT_UNIT_HEIGHT](#rack_elevation_default_unit_height)
* [RACK_ELEVATION_DEFAULT_UNIT_WIDTH](#rack_elevation_default_unit_width)
* [RELEASE_CHECK_TIMEOUT](#release_check_timeout)
* [RELEASE_CHECK_URL](#release_check_url)
* [SUPPORT_MESSAGE](#support_message)

## Extra Applications

A need may arise to allow the user to register additional settings. These will automatically apply
based on keynames prefixed with `EXTRA_` assuming the base key (the latter part of the setting name) is
of type list or tuple.

For example, to register additional `INSTALLED_APPS`, you would simply specify this in your custom
(user) configuration::

```python
EXTRA_INSTALLED_APPS = [
    'foo.bar',
]
```

This will ensure your default setting's `INSTALLED_APPS` do not have to be modified, and the user
can specify additional apps with ease.  Similarly, additional `MIDDLEWARE` can be added using `EXTRA_MIDDLEWARE`.

[[% for property, attrs in settings_data.properties.items() %]]
[[% if not attrs.required_setting|default(false) %]]

---

## `[[ property ]]`

[[% if attrs.version_added|default(None) %]]
+++ [[ attrs.version_added ]]
[[% endif %]]
[[% with default = attrs.default|default(None) %]]
[[% if default is string %]]Default: `"[[ default ]]"`
[[% elif default is boolean %]]Default: `[[ default|title ]]`
[[% else %]]Default: `[[ default ]]`
[[% endif %]]
[[% endwith %]]

[[% if attrs.environment_variable|default(None) %]]Environment variable: `[[ attrs.environment_variable ]]`[[% endif %]]

[[ attrs.description|default("") ]]

[[ attrs.details|default("") ]]

[[% endif %]]
[[% endfor %]]

---

## BRANDING_FILEPATHS

+++ 1.2.0

Default:

```python
{
    "logo": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_LOGO", None),  # Navbar logo
    "favicon": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_FAVICON", None),  # Browser favicon
    "icon_16": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_16", None),  # 16x16px icon
    "icon_32": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_32", None),  # 32x32px icon
    "icon_180": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_180", None),  # 180x180px icon - used for the apple-touch-icon header
    "icon_192": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_192", None),  # 192x192px icon
    "icon_mask": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_ICON_MASK", None),  # mono-chrome icon used for the mask-icon header
    "header_bullet": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_HEADER_BULLET", None),  # bullet image used for various view headers
    "nav_bullet": os.getenv("NAUTOBOT_BRANDING_FILEPATHS_NAV_BULLET", None)   # bullet image used for nav menu headers
}
```

A set of filepaths relative to the [`MEDIA_ROOT`](#media_root) which locate image assets used for custom branding. Each of these assets takes the place of the corresponding stock Nautobot asset. This allows for instance, providing your own navbar logo and favicon.

These environment variables may be used to specify the values:

* `NAUTOBOT_BRANDING_FILEPATHS_LOGO`
* `NAUTOBOT_BRANDING_FILEPATHS_FAVICON`
* `NAUTOBOT_BRANDING_FILEPATHS_ICON_16`
* `NAUTOBOT_BRANDING_FILEPATHS_ICON_32`
* `NAUTOBOT_BRANDING_FILEPATHS_ICON_180`
* `NAUTOBOT_BRANDING_FILEPATHS_ICON_192`
* `NAUTOBOT_BRANDING_FILEPATHS_ICON_MASK`

+++ 2.1.0
    <!-- markdownlint-disable MD037 -->
    * `NAUTOBOT_BRANDING_FILEPATHS_HEADER_BULLET`
    * `NAUTOBOT_BRANDING_FILEPATHS_NAV_BULLET`
    <!-- markdownlint-enable MD037 -->

If a custom image asset is not provided for any of the above options, the stock Nautobot asset is used.

---

## BRANDING_URLS

+++ 1.2.0

Default:

```python
{
    "code": os.getenv("NAUTOBOT_BRANDING_URLS_CODE", "https://github.com/nautobot/nautobot"),  # Code link in the footer
    "docs": os.getenv("NAUTOBOT_BRANDING_URLS_DOCS", "<STATIC_URL>docs/index.html"),  # Docs link in the footer
    "help": os.getenv("NAUTOBOT_BRANDING_URLS_HELP", "https://github.com/nautobot/nautobot/wiki"),  # Help link in the footer
}
```

A set of URLs that correspond to helpful links in the right of the footer on every web page.

These environment variables may be used to specify the values:

* `NAUTOBOT_BRANDING_URLS_CODE`
* `NAUTOBOT_BRANDING_URLS_DOCS`
* `NAUTOBOT_BRANDING_URLS_HELP`

If a custom URL is not provided for any of the links, the default link within the Nautobot community is used.

---

## CELERY_WORKER_REDIRECT_STDOUTS_LEVEL

+++ 2.0.0

Environment Variable: `NAUTOBOT_CELERY_WORKER_REDIRECT_STDOUTS_LEVEL`

Default: `WARNING`

The log level of log messages generated by redirected job stdout and stderr. Can be one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`.

---

## EXTERNAL_AUTH_DEFAULT_GROUPS

Default: `[]` (Empty list)

The list of group names to assign a new user account when created using 3rd-party authentication.

---

## INSTALLATION_METRICS_ENABLED

+++ 1.6.0

Default: `True` for existing Nautobot deployments, user-specified when running `nautobot-server init` for a new deployment.

Environment Variable: `NAUTOBOT_INSTALLATION_METRICS_ENABLED`

When set to `True`, Nautobot will send anonymized installation metrics to the Nautobot maintainers when running the [`post_upgrade`](../tools/nautobot-server.md#post_upgrade) or [`send_installation_metrics`](../tools/nautobot-server.md#send_installation_metrics) management commands. See the documentation for the [`send_installation_metrics`](../tools/nautobot-server.md#send_installation_metrics) management command for more details.

---

## LOG_DEPRECATION_WARNINGS

--- 1.5.3
    This setting was moved to [environment variable only](#nautobot_log_deprecation_warnings) as it conflicts with app startup due to import-time order.

---

## NETWORK_DRIVERS

+++ 1.6.0

Default: `{}` (Empty dictionary)

An optional dictionary to extend or override the default `Platform.network_driver` translations provided by [netutils](https://netutils.readthedocs.io/en/latest/user/lib_use_cases_lib_mapper/). For example, to add support for a custom `Platform.network_driver` value of `"my_network_driver"` for Netmiko and PyATS drivers:

```python
NETWORK_DRIVERS = {
    "netmiko": {"my_network_driver": "cisco_ios"},
    "pyats": {"my_network_driver": "iosxe"},
}
```

The default top-level keys are `ansible`, `hier_config`, `napalm`, `netmiko`, `netutils_parser`, `ntc_templates`, `pyats`, `pyntc`, and `scrapli`, but you can also add additional keys if you have an alternative network driver that you want your Nautobot instance to include.

!!! tip
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## PAGINATE_COUNT

Default: `50`

The default maximum number of objects to display per page within each list of objects. Applies to both the UI and the REST API.

+++ 1.2.0
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## PER_PAGE_DEFAULTS

Default: `[25, 50, 100, 250, 500, 1000]`

The options displayed in the web interface dropdown to limit the number of objects per page. For proper user experience, this list should include the [`PAGINATE_COUNT`](#paginate_count) and [`MAX_PAGE_SIZE`](#max_page_size) values as options.

---

## PLUGINS

Default: `[]` (Empty list)

A list of installed [Nautobot plugins](../../../apps/index.md) to enable. Plugins will not take effect unless they are listed here.

!!! warning
    Plugins extend Nautobot by allowing external code to run with the same access and privileges as Nautobot itself. Only install plugins from trusted sources. The Nautobot maintainers make absolutely no guarantees about the integrity or security of your installation with plugins enabled.

---

## PLUGINS_CONFIG

Default: `{}` (Empty dictionary)

This parameter holds configuration settings for individual Nautobot plugins. It is defined as a dictionary, with each key using the name of an installed plugin. The specific parameters supported are unique to each plugin: Reference the plugin's documentation to determine the supported parameters. An example configuration is shown below:

```python
PLUGINS_CONFIG = {
    'plugin1': {
        'foo': 123,
        'bar': True
    },
    'plugin2': {
        'foo': 456,
    },
}
```

Note that a plugin must be listed in `PLUGINS` for its configuration to take effect.

---

## PREFER_IPV4

Default: `False`

When determining the primary IP address for a device, IPv6 is preferred over IPv4 by default. Set this to True to prefer IPv4 instead.

+++ 1.2.0
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## RACK_ELEVATION_DEFAULT_UNIT_HEIGHT

Default: `22`

Default height (in pixels) of a unit within a rack elevation. For best results, this should be approximately one tenth of `RACK_ELEVATION_DEFAULT_UNIT_WIDTH`.

+++ 1.2.0
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## RACK_ELEVATION_DEFAULT_UNIT_WIDTH

Default: `220`

Default width (in pixels) of a unit within a rack elevation.

+++ 1.2.0
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## REDIS_LOCK_TIMEOUT

Default: `600`

Environment Variable: `NAUTOBOT_REDIS_LOCK_TIMEOUT`

Maximum duration of a Redis lock created when calling `/api/ipam/prefixes/{id}/available-prefixes/` or `/api/ipam/prefixes/{id}/available-ips/` to avoid inadvertently allocating the same prefix or IP to multiple simultaneous callers. Default is set to 600 seconds (10 minutes) to be longer than any theoretical API call time. This is to prevent a deadlock scenario where the server did not gracefully exit the `with` block when acquiring the Redis lock.

---

## RELEASE_CHECK_TIMEOUT

Default: `86400` (24 hours)

The number of seconds to retain the latest version that is fetched from the GitHub API before automatically invalidating it and fetching it from the API again.

!!! warning
    This must be set to at least one hour (`3600` seconds). Setting it to a value lower than this is an error.

+++ 1.2.0
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## RELEASE_CHECK_URL

Default: `None` (disabled)

This parameter defines the URL of the repository that will be checked periodically for new Nautobot releases. When a new release is detected, a message will be displayed to administrative users on the home page. This can be set to the official repository (`'https://api.github.com/repos/nautobot/nautobot/releases'`) or a custom fork. Set this to `None` to disable automatic update checks.

!!! note
    The URL provided **must** be compatible with the [GitHub REST API](https://docs.github.com/en/rest).

+++ 1.2.0
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## SANITIZER_PATTERNS

+++ 1.3.4

Default:

```python
[
    (re.compile(r"(https?://)?\S+\s*@", re.IGNORECASE), r"\1{replacement}@"),
    (
        re.compile(r"(username|password|passwd|pwd|secret|secrets)([\"']?(?:\s+is.?|:)?\s+)\S+[\"']?", re.IGNORECASE),
        r"\1\2{replacement}",
    ),
]
```

List of (regular expression, replacement pattern) tuples used by the `nautobot.core.utils.logging.sanitize()` function. As of Nautobot 1.3.4 this function is used primarily for sanitization of Job log entries, but it may be used in other scopes in the future.

This pattern catches patterns such as:

| Pattern Match Examples |
| --- |
| Password is1234 |
| Password: is1234 |
| Password is: is1234 |
| Password is is1234 |
| secret is: is1234 |
| secret is is1234 |
| secrets is: is1234 |
| secrets is is1234 |
| {"username": "is1234"} |
| {"password": "is1234"} |
| {"secret": "is1234"} |
| {"secrets": "is1234"} |

!!! info
    is1234 would be replaced in the Job logs with `(redacted)`.

---

## STORAGE_BACKEND

Default: `None` (local storage)

The backend storage engine for handling uploaded files (e.g. image attachments). Nautobot supports integration with the [`django-storages`](https://django-storages.readthedocs.io/en/stable/) package, which provides backends for several popular file storage services. If not configured, local filesystem storage will be used.

!!! tip
    For an example of using `django-storages` with AWS S3 buckets, visit the [django-storages with S3](../guides/s3-django-storage.md) user-guide.

The configuration parameters for the specified storage backend are defined under the [`STORAGE_CONFIG`](#storage_config) setting.

> See also: [`JOB_FILE_IO_STORAGE`](#job_file_io_storage)

---

## STORAGE_CONFIG

Default: `{}` (Empty dictionary)

A dictionary of configuration parameters for the storage backend configured as [`STORAGE_BACKEND`](#storage_backend). The specific parameters to be used here are specific to each backend; see the [`django-storages` documentation](https://django-storages.readthedocs.io/en/stable/) for more detail.

If [`STORAGE_BACKEND`](#storage_backend) is not defined, this setting will be ignored.

---

## STRICT_FILTERING

+++ 1.4.0

Default: `True`

Environment Variable: `NAUTOBOT_STRICT_FILTERING`

If set to `True` (default), UI and REST API filtering of object lists will fail if an unknown/unrecognized filter parameter is provided as a URL parameter. (For example, `/dcim/devices/?ice_cream_flavor=chocolate` or `/api/dcim/locations/?ice_cream_flavor=chocolate`). UI list (table) views will report an error message in this case and display no filtered objects; REST API list endpoints will return a 400 Bad Request response with an explanatory error message.

If set to `False`, unknown/unrecognized filter parameters will be discarded and ignored, although Nautobot will log a warning message.

!!! warning
    Setting this to `False` can result in unexpected filtering results in the case of user error, for example `/dcim/devices/?has_primry_ip=false` (note the typo `primry`) will result in a list of all devices, rather than the intended list of only devices that lack a primary IP address. In the case of Jobs or external automation making use of such a filter, this could have wide-ranging consequences.

---

## SUPPORT_MESSAGE

+++ 1.6.4

+++ 2.0.2

Default: `""`

A message to include on error pages (status code 403, 404, 500, etc.) when an error occurs. You can configure this to direct users to the appropriate contact(s) within your organization that provide support for Nautobot. Markdown formatting is supported within this message, as well as [a limited subset of HTML](../../platform-functionality/template-filters.md#render_markdown).

If unset, the default message that will appear is `If further assistance is required, please join the #nautobot channel on [Network to Code's Slack community](https://slack.networktocode.com) and post your question.`

!!! tip
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.

---

## TEST_FACTORY_SEED

+++ 1.5.0

Default: `None`

Environment Variable: `NAUTOBOT_TEST_FACTORY_SEED`

When [`TEST_USE_FACTORIES`](#test_use_factories) is set to `True`, this configuration provides a fixed seed string for the pseudo-random generator used to populate test data into the database, providing for reproducible randomness across consecutive test runs. If unset, a random seed will be used each time.

---

## TEST_USE_FACTORIES

+++ 1.5.0

Default: `False`

Environment Variable: `NAUTOBOT_TEST_USE_FACTORIES`

If set to `True`, the Nautobot test runner will call `nautobot-server generate_test_data ...` before executing any test cases, pre-populating the test database with various pseudo-random instances of many of Nautobot's data models.

!!! warning
    This functionality requires the installation of the [`factory-boy`](https://pypi.org/project/factory-boy/) Python package, which is present in Nautobot's own development environment, but is _not_ an inherent dependency of the Nautobot package when installed otherwise, such as into a plugin's development environment.

!!! info
    Setting this to `True` is a requirement for all Nautobot core tests as of 1.5.0, and it is set accordingly in `nautobot/core/tests/nautobot_config.py`, but defaults to `False` otherwise so as to remain backwards-compatible with plugins that also may use the Nautobot test runner in their own test environments, but have not yet updated their tests to account for the presence of this test data.

    Because this test data can obviate the need to manually construct complex test data, and the random factor can improve test robustness, plugin developers are encouraged to set this to `True` in their configuration, ensure that their development environments include the `factory-boy` Python package as a test dependency, and update their tests as needed.

---

## TEST_PERFORMANCE_BASELINE_FILE

+++ 1.5.0

Default: `nautobot/core/tests/performance_baselines.yml`

Environment Variable: `TEST_PERFORMANCE_BASELINE_FILE`

[`TEST_PERFORMANCE_BASELINE_FILE`](#test_performance_baseline_file) is set to a certain file path, this file path should point to a .yml file that conforms to the following format:

```yaml
tests:
  - name: >-
      test_run_job_with_sensitive_variables_and_requires_approval
      (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 4.799533
  - name: test_run_missing_schedule (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 4.367563
  - name: test_run_now_missing_args (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 4.363194
  - name: >-
      test_create_object_with_constrained_permission
      (nautobot.extras.tests.test_views.GraphQLQueriesTestCase)
    execution_time: 3.474244
  - name: >-
      test_run_now_constrained_permissions
      (nautobot.extras.tests.test_views.JobTestCase)
    execution_time: 2.727531
...
```

and store the performance baselines with the `name` of the test and the baseline `execution_time`. This file should provide the baseline times that all performance-related tests are running against.

---

## UI_RACK_VIEW_TRUNCATE_FUNCTION

+++ 1.4.0

Default:

```py
def UI_RACK_VIEW_TRUNCATE_FUNCTION(device_display_name):
    return str(device_display_name).split(".")[0]
```

This setting function is used to perform the rack elevation truncation feature. This provides a way to tailor the truncation behavior to best suit the needs of the installation.

The function must take only one argument: the device display name, as a string, attempting to be rendered on the rack elevation.

The function must return only one argument: a string of the truncated device display name.

## Environment-Variable-Only Settings

!!! warning
    The following settings are **only** configurable as environment variables, and not via `nautobot_config.py` or similar.

---

### GIT_SSL_NO_VERIFY

Default: Unset

If you are using a self-signed git repository, you will need to set the environment variable `GIT_SSL_NO_VERIFY="1"`
in order for the repository to sync.

!!! warning
    This _must_ be specified as an environment variable. Setting it in `nautobot_config.py` will not have the desired effect.

---

## NAUTOBOT_LOG_DEPRECATION_WARNINGS

+++ 1.5.2

+/- 1.5.3
    This was previously available as a config file setting but changed to environment-variable only. Also `DEBUG = True` will no longer work to log deprecation warnings.

Default: `False`

This can be set to `True` to allow deprecation warnings raised by Nautobot to (additionally) be logged as `WARNING` level log messages. (Deprecation warnings are normally silent in Python, but can be enabled globally by [various means](https://docs.python.org/3/library/warnings.html) such as setting the `PYTHONWARNINGS` environment variable. However, doing so can be rather noisy, as it will also include warnings from within Django about various code in various package dependencies of Nautobot's, etc. This configuration setting allows a more targeted enablement of only warnings from within Nautobot itself, which can be useful when vetting various Nautobot apps (plugins) for future-proofness against upcoming changes to Nautobot.)

!!! caution
    In Nautobot 2.0, deprecation warnings will be logged by default; a future release of Nautobot 1.5.x will also enable default logging of deprecation warnings.

---

### NAUTOBOT_ROOT

Default: `~/.nautobot/`

The filesystem path to use to store Nautobot files (Jobs, uploaded images, Git repositories, etc.).

This setting is used internally in the core settings to provide default locations for [features that require file storage](index.md#file-storage), and the [default location of the `nautobot_config.py`](index.md#specifying-your-configuration).

!!! warning
    Do not override `NAUTOBOT_ROOT` in your `nautobot_config.py`. It will not work as expected. If you need to customize this setting, please always set the `NAUTOBOT_ROOT` environment variable.

## Django Configuration Settings

While the [official Django documentation](https://docs.djangoproject.com/en/stable/ref/settings/) documents all Django settings, the below is provided where either the setting is common in Nautobot deployments and/or there is a supported `NAUTOBOT_*` environment variable.

### ADMINS

Default: `[]` (Empty list)

Nautobot will email details about critical errors to the administrators listed here. This should be a list of (name, email) tuples. For example:

```python
ADMINS = [
    ['Hank Hill', 'hhill@example.com'],
    ['Dale Gribble', 'dgribble@example.com'],
]
```

Please see the [official Django documentation on `ADMINS`](https://docs.djangoproject.com/en/stable/ref/settings/#admins) for more information.

---

### LOGGING

Default:

```python
{
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "normal": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s :\n  %(message)s",
            "datefmt": "%H:%M:%S",
        },
        "verbose": {
            "format": "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() :\n  %(message)s",
            "datefmt": "%H:%M:%S",
        },
    },
    "handlers": {
        "normal_console": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "normal",
        },
        "verbose_console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "django": {"handlers": ["normal_console"], "level": "INFO"},
        "nautobot": {
            "handlers": ["verbose_console" if DEBUG else "normal_console"],
            "level": LOG_LEVEL,
        },
    },
}
```

+/- 1.4.10
    While running unit or integration tests via `nautobot-server test ...`, LOGGING will be set to `{}` instead of the above defaults, as verbose logging to the console is typically not desirable while running tests.

+/- 2.0.0
    Unit/integration test logging was modified to send all nautobot logs to a `NullHandler` to prevent logs falling through to the last resort logger and being output to stderr.

This translates to:

* all messages from Django and from Nautobot of INFO severity or higher will be logged to the console.
* if [`DEBUG`](#debug) is True, Nautobot DEBUG messages will also be logged, and all Nautobot messages will be logged with a more verbose format including the filename and function name that originated each log message.

The above default log formatters split each log message across two lines of output for greater readability, which is useful for local observation and troubleshooting, but you may find it impractical to use in production environments that expect one line per log message. Fortunately, the Django framework on which Nautobot runs allows for extensive customization of logging format and destination. Please consult the [Django logging documentation](https://docs.djangoproject.com/en/stable/topics/logging/) for more information on configuring this setting.

Below is an example configuration extension which will additionally write all INFO and higher messages to a local file:

```python
LOGGING["handlers"]["file"] = {
    "level": "INFO",
    "class": "logging.FileHandler",
    "filename": "/var/log/nautobot.log",
    "formatter": "normal",
}
LOGGING["loggers"]["django"]["handlers"] += ["file"]
LOGGING["loggers"]["nautobot"]["handlers"] += ["file"]
```

Additional examples are available in the [`/examples/logging`](https://github.com/nautobot/nautobot/tree/develop/examples/logging) directory in the Nautobot repository.

#### Available Loggers

* `django.*` - Generic Django operations (HTTP requests/responses, etc.)
* `nautobot.<app>.<module>` - Generic form for model- or module-specific log messages
* `nautobot.auth.*` - Authentication events
* `nautobot.extras.jobs.*` - Job execution (`* = JobClassName`)
* `nautobot.core.graphql.*` - [GraphQL](../../platform-functionality/graphql.md) initialization and operation.
* `nautobot.extras.plugins.*` - Plugin loading and activity
* `nautobot.core.views.generic.*` - Generic views which handle business logic for the web UI

---

### SESSION_EXPIRE_AT_BROWSER_CLOSE

Default: `False`

Environment Variable: `NAUTOBOT_SESSION_EXPIRE_AT_BROWSER_CLOSE`

If this is set to True, Nautobot will use browser-length cookies - cookies that expire as soon as the user closes their browser.

By default, `SESSION_EXPIRE_AT_BROWSER_CLOSE` is set to False, which means session cookies will be stored in users’ browsers for as long as [`SESSION_COOKIE_AGE`](#session_cookie_age).

Please see the [official Django documentation on `SESSION_EXPIRE_AT_BROWSER_CLOSE`](https://docs.djangoproject.com/en/stable/ref/settings/#session-expire-at-browser-close) for more information.

---

### SESSION_COOKIE_AGE

Default: `1209600` (2 weeks, in seconds)

Environment Variable: `NAUTOBOT_SESSION_COOKIE_AGE`

The age of session cookies, in seconds.

Please see the [official Django documentation on `SESSION_COOKIE_AGE`](https://docs.djangoproject.com/en/stable/ref/settings/#session-cookie-age) for more information.

---

### SESSION_ENGINE

Default: `'django.contrib.sessions.backends.db'`

Controls where Nautobot stores session data.

To use cache-based sessions, set this to `'django.contrib.sessions.backends.cache'`.
To use file-based sessions, set this to `'django.contrib.sessions.backends.file'`.

See the official Django documentation on [Configuring the session](https://docs.djangoproject.com/en/stable/topics/http/sessions/#configuring-sessions) engine for more details.

---

### SESSION_FILE_PATH

Default: `None`

Environment Variable: `NAUTOBOT_SESSION_FILE_PATH`

HTTP session data is used to track authenticated users when they access Nautobot. By default, Nautobot stores session data in its database. However, this inhibits authentication to a standby instance of Nautobot without write access to the database. Alternatively, a local file path may be specified here and Nautobot will store session data as files instead of using the database. Note that the Nautobot system user must have read and write permissions to this path.

When the default value (`None`) is used, Nautobot will use the standard temporary directory for the system.

If you set this value, you must also enable file-based sessions as explained above using [`SESSION_ENGINE`](#session_engine).

---

### STATIC_ROOT

Default: `os.path.join(NAUTOBOT_ROOT, "static")`

The location where static files (such as CSS, JavaScript, fonts, or images) used to serve the web interface will be staged by the `nautobot-server collectstatic` command.

Please see the [official Django documentation on `STATIC_ROOT`](https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-STATIC_ROOT) for more information.

---

### TIME_ZONE

Default: `"UTC"`

Environment Variable: `NAUTOBOT_TIME_ZONE`

!!! warning
    Scheduled jobs will run in the time zone configured in this setting. If you change this setting from the default UTC, you must change it on the Celery Beat server and all Nautobot web servers or your scheduled jobs may run in the wrong time zone.

The time zone Nautobot will use when dealing with dates and times. It is recommended to use UTC time unless you have a specific need to use a local time zone. Please see the [list of available time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

Please see the [official Django documentation on `TIME_ZONE`](https://docs.djangoproject.com/en/stable/ref/settings/#time-zone) for more information.
