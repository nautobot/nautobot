# Nautobot Configuration

This section describes how to get started with configuring Nautobot.

## Initializing the Configuration

An initial configuration can be created by executing `nautobot-server init`. This will generate a new configuration with all of the default settings provided for you, and will also generate a unique [`SECRET_KEY`](required-settings.md#secret_key).

By default (if you haven't set [`NAUTOBOT_ROOT`](#nautobot-root-directory) to some other value), the file will be created at `$HOME/.nautobot/nautobot_config.py`:

```no-highlight
nautobot-server init
```

Example output:

```no-highlight
Configuration file created at '/opt/nautobot/nautobot_config.py'
```

!!! tip
    The [Nautobot Installation Docs](../installation/nautobot.md#choose-your-nautobot_root) example sets `NAUTOBOT_ROOT` to `/opt/nautobot`, so `nautobot_config.py` would be found at `/opt/nautobot/nautobot_config.py`.

You may specify a different location for the configuration as the argument to `init`:

```no-highlight
nautobot-server init /tmp/custom_config.py
```

```no-highlight
Configuration file created at '/tmp/custom_config.py'
```

!!! note
    Throughout the documentation, the configuration file will be referred to by name as `nautobot_config.py`. If you use a custom file name, you must use that instead.

## Specifying your Configuration

If you place your configuration in the default location at `$HOME/.nautobot/nautobot_config.py`, you may utilize the `nautobot-server` command and it will use that location automatically.

If you do not wish to utilize the default location, you have two options:

### Config argument

You may provide the `--config` argument when executing `nautobot-server` to tell Nautobot where to find your configuration. For example, to start a shell with the configuration in an alternate location:

```no-highlight
nautobot-server --config=/etc/nautobot_config.py nbshell
```

### Environment variable

You may also set the `NAUTOBOT_CONFIG` environment variable to the location of your configuration file so that you don't have to keep providing the `--config` argument. If set, this overrides the default location.

```no-highlight
export NAUTOBOT_CONFIG=/etc/nautobot_config.py
nautobot-server nbshell
```

## Nautobot Root Directory

By default, Nautobot will always read or store files in `~/.nautobot` to allow for installation without requiring superuser (root) permissions.

The `NAUTOBOT_ROOT` configuration setting specifies where these files will be stored on your file system. You may customize this location by setting the `NAUTOBOT_ROOT` environment variable. For example:

```no-highlight
export NAUTOBOT_ROOT=/opt/nautobot
```

This setting is also used in the [Nautobot deployment guide](../installation/nautobot.md) to make the `nautobot-server` command easier to find and use.

!!! note
    The `--config` argument and the `NAUTOBOT_CONFIG` environment variable will always take precedence over `NAUTOBOT_ROOT` for the purpose of telling Nautobot where your `nautobot_config.py` can be found.

!!! warning
    Do not override `NAUTOBOT_ROOT` in your `nautobot_config.py`. It will not work as expected. If you need to customize this setting, please always set the `NAUTOBOT_ROOT` environment variable.

## File Storage

Nautobot is capable of storing various types of files. This includes [Jobs](../additional-features/jobs.md), [Git repositories](../models/extras/gitrepository.md), [image attachments](../models/extras/imageattachment.md), and [static files](optional-settings.md#static_root) (CSS, JavaScript, etc.).

Each of the features requiring use of file storage default to being stored in `NAUTOBOT_ROOT`. If desired, you may customize each one individually. Please see each feature's respective documentation linked above for how to do that.

## Configuration Parameters

While Nautobot has many configuration settings, only a few of them must be defined at the time of installation. These configuration parameters may be set in `nautobot_config.py` or by default many of them may also be set by environment variables. Please see the following links for more information:

* [Required settings](required-settings.md)
* [Optional settings](optional-settings.md)

## Optional Authentication Configuration

* [LDAP Authentication](authentication/ldap.md)
* [Remote User Authentication](authentication/remote.md)
* [SSO Authentication](authentication/sso.md)

## Changing the Configuration

Configuration settings may be changed at any time. However, the WSGI service (e.g. uWSGI) must be restarted before the changes will take effect. For example, if you're running Nautobot using `systemd:`

```no-highlight
sudo systemctl restart nautobot nautobot-worker
```

## Advanced Configuration

### Troubleshooting the Configuration

To facilitate troubleshooting and debugging of settings, try inspecting the settings from a shell.

First get a shell and load the Django settings:

```no-highlight
nautobot-server nbshell
```

Output:

```no-highlight
### Nautobot interactive shell (localhost)
### Python 3.9.1 | Django 3.1.3 | Nautobot 1.0.0
### lsmodels() will show available models. Use help(<model>) for more info.
>>> from django.conf import settings
```

Inspect the `SETTINGS_PATH` variable. Does it match the configuration you're expecting to be loading?

```no-highlight
>>> settings.SETTINGS_PATH
'/home/example/.nautobot/nautobot_config.py'
```

If not, double check that you haven't set the `NAUTOBOT_CONFIG` environment variable, or if you did, that the path defined there is the correct one.

```no-highlight
echo $NAUTOBOT_CONFIG
```

### Adding your own dependencies

!!! warning
    Be cautious not to confuse extra applications with Nautobot plugins which are installed using the [`PLUGINS`](optional-settings.md#plugins) setting. They are similar, but distinctly different!

Nautobot, being a Django application, allows for installation of additional dependencies utilizing the [`INSTALLED_APPS`](https://docs.djangoproject.com/en/stable/ref/settings/#std:setting-INSTALLED_APPS) settings. Due to the highly specialized nature of Nautobot, *you cannot safely do this*.

For example, let's assume that you want to install the popular [`django-health-check`](https://django-health-check.readthedocs.io/en/latest/) plugin to your Nautobot deployment which requires you to add one or more `health_check` entries to your `INSTALLED_APPS`.

If you attempt to modify `INSTALLED_APPS` yourself, you might see an error such as this:

```python
Traceback (most recent call last):
  File "/usr/local/bin/nautobot-server", line 8, in <module>
    sys.exit(main())
  File "/usr/local/lib/python3.7/site-packages/nautobot/core/cli.py", line 53, in main
    initializer=_configure_settings,  # Called after defaults
  File "/usr/local/lib/python3.7/site-packages/nautobot/core/runner/runner.py", line 193, in run_app
    management.execute_from_command_line([runner_name, command] + command_args)
  File "/usr/local/lib/python3.7/site-packages/django/core/management/__init__.py", line 401, in execute_from_command_line
    utility.execute()
  File "/usr/local/lib/python3.7/site-packages/django/core/management/__init__.py", line 377, in execute
    django.setup()
  File "/usr/local/lib/python3.7/site-packages/django/__init__.py", line 24, in setup
    apps.populate(settings.INSTALLED_APPS)
  File "/usr/local/lib/python3.7/site-packages/django/apps/registry.py", line 95, in populate
    "duplicates: %s" % app_config.label)
django.core.exceptions.ImproperlyConfigured: Application labels aren't unique, duplicates: health_check
```

To make it work, you would simply specify `EXTRA_INSTALLED_APPS` instead:

```python
EXTRA_INSTALLED_APPS = [
    'health_check',
    ...
]
```

For more information on installing extra applications, please see the documentation on [Extra Applications](optional-settings.md#extra-applications).

For more information on installing or developing Nautobot plugins, please see the [documentation on Plugins](../plugins/index.md).
