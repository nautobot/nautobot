# Optional Configuration Settings

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
can specify additional apps with ease.

## ADMINS

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

## ALLOWED_URL_SCHEMES

Default: `('file', 'ftp', 'ftps', 'http', 'https', 'irc', 'mailto', 'sftp', 'ssh', 'tel', 'telnet', 'tftp', 'vnc', 'xmpp')`

A list of permitted URL schemes referenced when rendering links within Nautobot. Note that only the schemes specified in this list will be accepted: If adding your own, be sure to replicate all of the default values as well (excluding those schemes which are not desirable).

---

## BANNER_TOP

## BANNER_BOTTOM

Default: `""` (Empty string)

Setting these variables will display custom content in a banner at the top and/or bottom of the page, respectively. HTML is allowed. To replicate the content of the top banner in the bottom banner, set:

```python
BANNER_TOP = 'Your banner text'
BANNER_BOTTOM = BANNER_TOP
```

---

## BANNER_LOGIN

Default: `""` (Empty string)

This defines custom content to be displayed on the login page above the login form. HTML is allowed.

---

## CACHEOPS_DEFAULTS

Default: `{'timeout': 900}` (15 minutes, in seconds)

!!! warning
    It is an error to set the timeout value to `0`. If you wish to disable caching, please use [`CACHEOPS_ENABLED`](#cacheops_enabled).

Various defaults for caching, the most important of which being the cache timeout. The `timeout` is the number of seconds that cache entries will be retained before expiring.

---

## CACHEOPS_ENABLED

Default: `True`

A boolean that turns on/off caching.

If set to `False`, all caching is bypassed and Nautobot operates as if there is no cache.

---

## CACHEOPS_REDIS

Default: `'redis://localhost:6379/1'`

The Redis connection string to use for caching.

---

## CHANGELOG_RETENTION

Default: `90`

The number of days to retain logged changes (object creations, updates, and deletions). Set this to `0` to retain changes in the database indefinitely.

!!! warning
    If enabling indefinite changelog retention, it is recommended to periodically delete old entries. Otherwise, the database may eventually exceed capacity.

---

## CORS_ALLOW_ALL_ORIGINS

Default: `False`

If `True`, all origins will be allowed. Other settings restricting allowed origins will be ignored.

Setting this to `True` can be dangerous, as it allows any website to make cross-origin requests to yours. Generally you'll want to restrict the list of allowed origins with [`CORS_ALLOWED_ORIGINS`](#cors_allowed_origins) or [`CORS_ALLOWED_ORIGIN_REGEXES`](#cors_allowed_origin_regexes).

Previously this setting was called `CORS_ORIGIN_ALLOW_ALL`, which still works as an alias, with the new name taking precedence.

---

## CORS_ALLOWED_ORIGINS

Default: `[]` (Empty list)

A list of origins that are authorized to make cross-site HTTP requests.

An Origin is defined by [the CORS RFC Section 3.2](https://tools.ietf.org/html/rfc6454#section-3.2) as a URI `scheme + hostname + port`, or one of the special values `'null'` or `'file://'`. Default ports (HTTPS = 443, HTTP = 80) are optional here.

The special value `null` is sent by the browser in ["privacy-sensitive contexts"](https://tools.ietf.org/html/rfc6454#section-6), such as when the client is running from a `file://` domain. The special value `file://` is sent accidentally by some versions of Chrome on Android as per this bug.

Example:

```python
CORS_ALLOWED_ORIGINS = [
    "https://example.com",
    "https://sub.example.com",
    "http://localhost:8080",
    "http://127.0.0.1:9000"
]
```

Previously this setting was called `CORS_ORIGIN_WHITELIST`, which still works as an alias, with the new name taking precedence.

---

## CORS_ALLOWED_ORIGIN_REGEXES

Default: `[]`

A list of strings representing regexes that match Origins that are authorized to make cross-site HTTP requests. Useful when [`CORS_ALLOWED_ORIGINS`](#cors_allowed_origins) is impractical, such as when you have a large number of subdomains.

Example:

```python
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://\w+\.example\.com$",
]
```

Previously this setting was called `CORS_ORIGIN_REGEX_WHITELIST`, which still works as an alias, with the new name taking precedence.

---

## CSRF_TRUSTED_ORIGINS

Default: `[]`

A list of hosts (fully-qualified domain names (FQDNs) or subdomains) that are considered trusted origins for cross-site secure requests such as HTTPS POST.

For more information, please see the [official Django documentation on `CSRF_TRUSTED_ORIGINS`](https://docs.djangoproject.com/en/stable/ref/settings/#csrf-trusted-origins) and more generally the [official Django documentation on CSRF protection](https://docs.djangoproject.com/en/stable/ref/csrf/#how-it-works)

---

## DEBUG

Default: `False`

This setting enables debugging. Debugging should be enabled only during development or troubleshooting. Note that only
clients which access Nautobot from a recognized [internal IP address](#internal_ips) will see debugging tools in the user interface.

!!! warning
    Never enable debugging on a production system, as it can expose sensitive data to unauthenticated users and impose a
    substantial performance penalty.

Please see the [official Django documentation on `DEBUG`](https://docs.djangoproject.com/en/stable/ref/settings/#debug) for more information.

---

## DOCS_ROOT

Default: `$BASE_DIR/docs`

The filesystem path to Nautobot's documentation. This is used when presenting context-sensitive documentation in the web UI. By default, this will be the `docs` directory within the root Nautobot installation path. (Set this to `None` to disable the embedded documentation.)

!!! warning
    The `BASE_DIR` variable is internal to Nautobot and is referenced here to represent the fully qualified file path where the Nautobot library code is installed. Please do not modify the value of `BASE_DIR` as it can have unintended side effects.

---

## ENFORCE_GLOBAL_UNIQUE

Default: `False`

By default, Nautobot will permit users to create duplicate prefixes and IP addresses in the global table (that is, those which are not assigned to any VRF). This behavior can be disabled by setting `ENFORCE_GLOBAL_UNIQUE` to `True`.

---

## EXEMPT_VIEW_PERMISSIONS

Default: `[]` (Empty list)

A list of Nautobot models to exempt from the enforcement of view permissions. Models listed here will be viewable by all users, both authenticated and anonymous.

List models in the form `<app>.<model>`. For example:

```python
EXEMPT_VIEW_PERMISSIONS = [
    'dcim.site',
    'dcim.region',
    'ipam.prefix',
]
```

To exempt _all_ models from view permission enforcement, set the following. (Note that `EXEMPT_VIEW_PERMISSIONS` must be an iterable.)

```python
EXEMPT_VIEW_PERMISSIONS = ['*']
```

!!! note
    Using a wildcard will not affect certain potentially sensitive models, such as user permissions. If there is a need to exempt these models, they must be specified individually.

---

## EXTERNAL_AUTH_DEFAULT_GROUPS

Default: `[]` (Empty list)

The list of group names to assign a new user account when created using 3rd-party authentication.

---

## EXTERNAL_AUTH_DEFAULT_PERMISSIONS

Default: `{}` (Empty dictionary)

A mapping of permissions to assign a new user account when created using SSO authentication. Each key in the dictionary will be the permission name specified as `<app_label>.<action>_<model>`, and the value should be set to the permission [constraints](../administration/permissions.md#constraints), or `None` to allow all objects.

### Example Permissions

| Permission | Description |
|---|---|
| `{'dcim.view_device': {}}` or `{'dcim.view_device': None}` | Users can view all devices |
| `{'dcim.add_device': {}}` | Users can add devices, see note below |
| `{'dcim.view_device': {"site__name__in":  ["HQ"]}}` | Users can view all devices in the HQ site |

!!! warning
    Permissions can be complicated! Be careful when restricting permissions to also add any required prerequisite permissions.

    For example, when adding Devices the Device Role, Device Type, Site, and Status fields are all required fields in order for the UI to function properly. Users will also need view permissions for those fields or the corresponding field selections in the UI will be unavailable and potentially prevent objects from being able to be created or edited.

The following example gives a user a reasonable amount of access to add devices to a single site (HQ in this case):

```python
{
    'dcim.add_device': {"site__name__in":  ["HQ"]},
    'dcim.view_device': {"site__name__in":  ["HQ"]},
    'dcim.view_devicerole': None,
    'dcim.view_devicetype': None,
    'extras.view_status': None,
    'dcim.view_site': {"name__in":  ["HQ"]},
    'dcim.view_manufacturer': None,
    'dcim.view_region': None,
    'dcim.view_rack': None,
    'dcim.view_rackgroup': None,
    'dcim.view_platform': None,
    'virtualization.view_cluster': None,
    'virtualization.view_clustergroup': None,
    'tenancy.view_tenant': None,
    'tenancy.view_tenantgroup': None,
}
```

Please see [the object permissions page](../administration/permissions.md) for more information.

---


## FORCE_SCRIPT_NAME

Default: `None`

If not `None`, this will be used as the value of the `SCRIPT_NAME` environment variable in any HTTP request. This setting can be used to override the server-provided value of `SCRIPT_NAME`, which is most commonly used for hosting Nautobot in a subdirectory (e.g. *example.com/nautobot/*).

!!! important
    To host Nautobot under a subdirectory you must set this value to match the same prefix configured on your HTTP server. For example, if you configure NGINX to serve Nautobot at `/nautobot/`, you must set `FORCE_SCRIPT_NAME = "/nautobot/"`.

Please see the [official Django documentation on `FORCE_SCRIPT_NAME`](https://docs.djangoproject.com/en/stable/ref/settings/#force-script-name) for more information.

---

## GIT_ROOT

Default: `os.path.join(NAUTOBOT_ROOT, "git")`

The file path to a directory where cloned [Git repositories](../models/extras/gitrepository.md) will be located.

The value of this variable can also be customized by setting the environment variable `NAUTOBOT_GIT_ROOT` to a directory path of your choosing.

---

## GRAPHQL_CUSTOM_FIELD_PREFIX

Default: `cf`

By default, all custom fields in GraphQL will be prefixed with `cf`. A custom field name `my_field` will appear in GraphQL as `cf_my_field` by default. It's possible to change or remove the prefix by setting the value of `GRAPHQL_CUSTOM_FIELD_PREFIX`.

---

## HIDE_RESTRICTED_UI

Default: `False`

When set to `True`, users with limited permissions will only be able to see items in the UI they have access too.

---

## HTTP_PROXIES

Default: `None` (Disabled)

A dictionary of HTTP proxies to use for outbound requests originating from Nautobot (e.g. when sending webhook requests). Proxies should be specified by schema (HTTP and HTTPS) as per the [Python requests library documentation](https://2.python-requests.org/en/master/user/advanced/). For example:

```python
HTTP_PROXIES = {
    'http': 'http://10.10.1.10:3128',
    'https': 'http://10.10.1.10:1080',
}
```

---

## INTERNAL_IPS

Default: `('127.0.0.1', '::1')`

A list of IP addresses recognized as internal to the system, used to control the display of debugging output. For
example, the [Django debugging toolbar](https://django-debug-toolbar.readthedocs.io/), if installed,
will be viewable only when a client is accessing Nautobot from one of the listed IP
addresses (and [`DEBUG`](#debug) is true).

---

## JOBS_ROOT

Default: `os.path.join(NAUTOBOT_ROOT, "jobs")`

The file path to a directory where [Jobs](../additional-features/jobs.md) can be discovered.

The value of this variable can also be customized by setting the environment variable `NAUTOBOT_JOBS_ROOT` to a directory path of your choosing.

!!! note
    This directory **must** contain an `__init__.py` file.

---

## LOGGING

Default: `{}` (Empty dictionary)

By default, all messages of INFO severity or higher will be logged to the console. Additionally, if [`DEBUG`](#debug) is False and email access has been configured, ERROR and CRITICAL messages will be emailed to the users defined in [`ADMINS`](#admins).

The Django framework on which Nautobot runs allows for the customization of logging format and destination. Please consult the [Django logging documentation](https://docs.djangoproject.com/en/stable/topics/logging/) for more information on configuring this setting. Below is an example which will write all INFO and higher messages to a local file and log DEBUG and higher messages from Nautobot itself and from the RQ worker process to the console with added verbosity and colorization:

```python
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'normal': {
            'format': '%(asctime)s.%(msecs)03d %(levelname)-7s %(name)s : %(message)s',
            'datefmt': '%H:%M:%S',
        },
        'verbose': {
            'format': '%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-20s %(filename)-15s %(funcName)30s() :\n  %(message)s',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'file': {'level': 'INFO', 'class': 'logging.FileHandler', 'filename': '/var/log/nautobot.log', 'formatter': 'normal'},
        'normal_console': {'level': 'INFO', 'class': 'rq.utils.ColorizingStreamHandler', 'formatter': 'normal'},
        'verbose_console': {'level': 'DEBUG', 'class': 'rq.utils.ColorizingStreamHandler', 'formatter': 'verbose'},
    },
    'loggers': {
        'django': {'handlers': ['file', 'normal_console'], 'level': 'INFO'},
        'nautobot': {'handlers': ['file', 'verbose_console'], 'level': 'DEBUG'},
        'rq.worker': {'handlers': ['file', 'verbose_console'], 'level': 'DEBUG'},
    },
}
```

### Available Loggers

* `django.*` - Generic Django operations (HTTP requests/responses, etc.)
* `nautobot.<app>.<module>` - Generic form for model- or module-specific log messages
* `nautobot.auth.*` - Authentication events
* `nautobot.api.views.*` - Views which handle business logic for the REST API
* `nautobot.jobs.*` - Job execution (`* = JobClassName`)
* `nautobot.graphql.*` - [GraphQL](../additional-features/graphql.md) initialization and operation.
* `nautobot.plugins.*` - Plugin loading and activity
* `nautobot.views.*` - Views which handle business logic for the web UI
* `rq.worker` - Background task handling

---

## MAINTENANCE_MODE

Default: `False`

Setting this to `True` will display a "maintenance mode" banner at the top of every page. Additionally, Nautobot will no longer update a user's "last active" time upon login. This is to allow new logins when the database is in a read-only state. Recording of login times will resume when maintenance mode is disabled.

---

## MAX_PAGE_SIZE

Default: `1000`

A web user or API consumer can request an arbitrary number of objects by appending the "limit" parameter to the URL (e.g. `?limit=1000`). This parameter defines the maximum acceptable limit. Setting this to `0` or `None` will allow a client to retrieve _all_ matching objects at once with no limit by specifying `?limit=0`.

---

## MEDIA_ROOT

Default: `os.path.join(NAUTOBOT_ROOT, "media")`

The file path to the location where media files (such as [image attachments](../models/extras/imageattachment.md)) are stored.

Please see the [official Django documentation on `MEDIA_ROOT`](https://docs.djangoproject.com/en/stable/ref/settings/#media-root) for more information.

---

## METRICS_ENABLED

Default: `False`

Toggle the availability Prometheus-compatible metrics at `/metrics`. See the [Prometheus Metrics](../additional-features/prometheus-metrics.md) documentation for more details.

---

## NAPALM_USERNAME

## NAPALM_PASSWORD

Default: `""` (Empty string)

Nautobot will use these credentials when authenticating to remote devices via the [NAPALM library](https://napalm-automation.net/), if installed. Both parameters are optional.

!!! note
    If SSH public key authentication has been set up on the remote device(s) for the system account under which Nautobot runs, these parameters are not needed.

---

## NAPALM_ARGS

Default: `{}` (Empty dictionary)

A dictionary of optional arguments to pass to NAPALM when instantiating a network driver. See the NAPALM documentation for a [complete list of optional arguments](https://napalm.readthedocs.io/en/latest/support/#optional-arguments). An example:

```python
NAPALM_ARGS = {
    'api_key': '472071a93b60a1bd1fafb401d9f8ef41',
    'port': 2222,
}
```

Some platforms (e.g. Cisco IOS) require an argument named `secret` to be passed in addition to the normal password. If desired, you can use the configured `NAPALM_PASSWORD` as the value for this argument:

```python
NAPALM_USERNAME = 'username'
NAPALM_PASSWORD = 'MySecretPassword'
NAPALM_ARGS = {
    'secret': NAPALM_PASSWORD,
    # Include any additional args here
}
```

---

## NAPALM_TIMEOUT

Default: `30`

The amount of time (in seconds) to wait for NAPALM to connect to a device.

---

## NAUTOBOT_ROOT

Default: `~/.nautobot/`

The filesystem path to use to store Nautobot files (Jobs, uploaded images, Git repositories, etc.).

This setting is used internally in the core settings to provide default locations for [features that require file storage](../../configuration/#file-storage), and the [default location of the `nautobot_config.py`](../../configuration/#specifying-your-configuration).

!!! warning
    Do not override `NAUTOBOT_ROOT` in your `nautobot_config.py`. It will not work as expected. If you need to customize this setting, please always set the `NAUTOBOT_ROOT` environment variable.

---

## PAGINATE_COUNT

Default: `50`

The default maximum number of objects to display per page within each list of objects.

---

## PLUGINS

Default: `[]` (Empty list)

A list of installed [Nautobot plugins](../../plugins) to enable. Plugins will not take effect unless they are listed here.

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

---

## RACK_ELEVATION_DEFAULT_UNIT_HEIGHT

Default: `22`

Default height (in pixels) of a unit within a rack elevation. For best results, this should be approximately one tenth of `RACK_ELEVATION_DEFAULT_UNIT_WIDTH`.

---

## RACK_ELEVATION_DEFAULT_UNIT_WIDTH

Default: `220`

Default width (in pixels) of a unit within a rack elevation.

---

## RELEASE_CHECK_TIMEOUT

Default: `86400` (24 hours)

The number of seconds to retain the latest version that is fetched from the GitHub API before automatically invalidating it and fetching it from the API again.

!!! warning
    This must be set to at least one hour (`3600` seconds). Setting it to a value lower than this is an error.

---

## RELEASE_CHECK_URL

Default: `None` (disabled)

This parameter defines the URL of the repository that will be checked periodically for new Nautobot releases. When a new release is detected, a message will be displayed to administrative users on the home page. This can be set to the official repository (`'https://api.github.com/repos/nautobot/nautobot/releases'`) or a custom fork. Set this to `None` to disable automatic update checks.

!!! note
    The URL provided **must** be compatible with the [GitHub REST API](https://docs.github.com/en/rest).

---
## SESSION_COOKIE_AGE

Default: `1209600` (2 weeks, in seconds)

The age of session cookies, in seconds.

---

## SESSION_ENGINE

Default: `'django.contrib.sessions.backends.db'`

Controls where Nautobot stores session data.

To use file-based sessions, set this to `'django.contrib.sessions.backends.file'`.

See the official Django documentation on [Configuring the session](https://docs.djangoproject.com/en/stable/topics/http/sessions/#configuring-sessions) engine for more details.

---

## SESSION_FILE_PATH

Default: `None`

HTTP session data is used to track authenticated users when they access Nautobot. By default, Nautobot stores session data in its PostgreSQL database. However, this inhibits authentication to a standby instance of Nautobot without write access to the database. Alternatively, a local file path may be specified here and Nautobot will store session data as files instead of using the database. Note that the Nautobot system user must have read and write permissions to this path.

When the default value (`None`) is used, Nautobot will use the standard temporary directory for the system.

If you set this value, you must also enable file-based sessions as explained above using [`SESSION_ENGINE`](#session_engine).

---

## SOCIAL_AUTH_ENABLED

Default: `False`

Enables the social authentication backend to facilifate single-sign on (SSO) for common services like SAML, OAuth2, etc. This setting is required to be enabled to use the SSO for authentication.

See the guide on [Single Sign On Authentication](../authentication/sso) for more details.

---

## STATIC_ROOT

Default: `os.path.join(NAUTOBOT_ROOT, "static")`

The location where static files (such as CSS, JavaScript, fonts, or images) used to serve the web interface will be staged by the `nautobot-server collectstatic` command.

Please see the [official Django documentation on `STATIC_ROOT`](https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-STATIC_ROOT) for more information.

---

## STORAGE_BACKEND

Default: `None` (local storage)

The backend storage engine for handling uploaded files (e.g. image attachments). Nautobot supports integration with the [`django-storages`](https://django-storages.readthedocs.io/en/stable/) package, which provides backends for several popular file storage services. If not configured, local filesystem storage will be used.

The configuration parameters for the specified storage backend are defined under the [`STORAGE_CONFIG`](#storage_config) setting.

---

## STORAGE_CONFIG

Default: `{}` (Empty dictionary)

A dictionary of configuration parameters for the storage backend configured as [`STORAGE_BACKEND`](#storage_backend). The specific parameters to be used here are specific to each backend; see the [`django-storages` documentation](https://django-storages.readthedocs.io/en/stable/) for more detail.

If [`STORAGE_BACKEND`](#storage_backend) is not defined, this setting will be ignored.

---

## TIME_ZONE

Default: `"UTC"`

The time zone Nautobot will use when dealing with dates and times. It is recommended to use UTC time unless you have a specific need to use a local time zone. Please see the [list of available time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

Please see the [official Django documentation on `TIME_ZONE`](https://docs.djangoproject.com/en/stable/ref/settings/#time-zone) for more information.

---

## Date and Time Formatting

You may define custom formatting for date and times. For detailed instructions on writing format strings, please see [the Django documentation](https://docs.djangoproject.com/en/stable/ref/templates/builtins/#date). Default formats are listed below.

```python
DATE_FORMAT = 'N j, Y'               # June 26, 2016
SHORT_DATE_FORMAT = 'Y-m-d'          # 2016-06-26
TIME_FORMAT = 'g:i a'                # 1:23 p.m.
DATETIME_FORMAT = 'N j, Y g:i a'     # June 26, 2016 1:23 p.m.
SHORT_DATETIME_FORMAT = 'Y-m-d H:i'  # 2016-06-26 13:23
```
