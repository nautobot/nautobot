# Optional Configuration Settings

## Administratively Configurable Settings

+++ 1.2.0

A number of settings can alternatively be configured via the Nautobot Admin UI. To do so, these settings must **not** be defined in your `nautobot_config.py`, as any settings defined there will take precedence over any values defined in the Admin UI. Settings that are currently configurable via the Admin UI include:

[[% for property, attrs in settings_data.properties.items() %]]
[[% if attrs.is_constance_config|default(false) %]]* [`[[ property ]]`](#[[ property|lower ]])[[% endif %]]
[[% endfor %]]

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

[[% for property, attrs in settings_data.properties.items() if not attrs.is_required_setting|default(false) %]]

---

## `[[ property ]]`

[[% if attrs.version_added|default(None) %]]
+++ [[ attrs.version_added ]]
[[% endif %]]
[[% with default = attrs.default|default(None) %]]
[[% if default is string %]]Default: `"[[ default ]]"`
[[% elif default is boolean %]]Default: `[[ default|title ]]`
[[% elif default is mapping and default != {} %]]Default:

```json
[[ default|tojson(4) ]]
```

[[% else %]]Default: `[[ default ]]`
[[% endif %]]
[[% endwith %]]

[[% if attrs.environment_variable|default(None) %]]Environment variable: `[[ attrs.environment_variable ]]`[[% endif %]]

[[ attrs.description|default("") ]]

[[ attrs.details|default("") ]]

[[% if attrs.is_constance_config|default(false) %]]
!!! tip
    If you do not set a value for this setting in your `nautobot_config.py`, it can be configured dynamically by an admin user via the Nautobot Admin UI. If you do have a value for this setting in `nautobot_config.py`, it will override any dynamically configured value.
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

---

## UI_RACK_VIEW_TRUNCATE_FUNCTION

+++ 1.4.0

Default:

```py
def UI_RACK_VIEW_TRUNCATE_FUNCTION(device_display_name):
    return str(device_display_name).split(".")[0]
```

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
