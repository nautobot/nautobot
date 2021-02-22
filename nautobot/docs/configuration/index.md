# Nautobot Configuration

This section describes how to get started with configuring Nautobot.

## Initializing the Configuration

An initial configuration can be created by executing `nautobot-server init`. This will generate a new configuration with all of the default settings provided for you, and will also generate a unique `SECRET_KEY`.

By default the file will be created at `$HOME/.nautobot/nautobot_config.py`:

```bash
$ nautobot-server init
Configuration file created at '/home/example/.nautobot/nautobot_config.py'
```

You may specify a different location for the configuration as the argument to `init`:

```bash
$ nautobot-server init /tmp/custom_config.py
Configuration file created at '/tmp/custom_config.py'
```

!!! note
    Throughout the documentation, the configuration file will be referred to by name as `nautobot_config.py`. If you use a custom file name, you must use that instead.

## Specifying your Configuration

If you place your configuration in the default location at `$HOME/.nautobot/nautobot_config.py`, you may utilize the `nautobot-server` command and it will use that location automatically.

If you do not wish to utilize the default location, you have two options:

### Config argument

You may provide the `--config` argument when executing `nautobot-server` to tell Nautobot where to find your configuration. For example, to start a shell with the configuration in an alternate location:

```bash
$ nautobot-server --config=/etc/nautobot_config.py nbshell
```

### Environment variable

You may also set the `NAUTOBOT_CONFIG` environment variable to the location of your configuration file so that you don't have to keep providing the `--config` argument. If set, this overrides the default location.

```bash
$ export NAUTOBOT_CONFIG=/etc/nautobot_config.py
$ nautobot-server nbshell
```

## File Storage

Nautobot is capable of storing various types of files. This includes [jobs](../additional-features/jobs.md), [Git repositories](../models/extras/gitrepository.md), and [image attachments](../models/extras/imageattachment.md). The `BASE_STORAGE_DIR` configuration setting specifies where these files will be stored on your file system; this variable defaults to the same `~/.nautobot/` directory used to store the default Nautobot configuration file, but may be overridden either in your configuration file or by setting the `NAUTOBOT_BASE_STORAGE_DIR` environment variable when using the default configuration.

## Configuration Parameters

While Nautobot has many configuration settings, only a few of them must be defined at the time of installation.

* [Required settings](required-settings.md)
* [Optional settings](optional-settings.md)

## Optional Authentication Configuration

* [LDAP Authentication](authentication/ldap.md)
* [Remote User Authentication](authentication/remote.md)
* [SSO Authentication](authentication/sso.md)

## Changing the Configuration

Configuration settings may be changed at any time. However, the WSGI service (e.g. Gunicorn) must be restarted before the changes will take effect. For example, if you're running Nautobot using `systemd:`

```
$ sudo systemctl restart nautobot
```

## Troubleshooting the Configuration

To facilitate troubleshooting and debugging of settings, try inspecting the settings from a shell. 

First get a shell and load the Django settings:

```bash
$ nautobot-server nbshell
### Nautobot interactive shell (jathy-mini.local)
### Python 3.9.1 | Django 3.1.3 | Nautobot 1.0.0b1
### lsmodels() will show available models. Use help(<model>) for more info.
>>> from django.conf import settings
```

Inspect the `SETTINGS_PATH` variable. Does it match the configuration you're expecting to be loading?

```bash
>>> settings.SETTINGS_PATH
'/home/example/.nautobot/nautobot_config.py'
```

If not, double check that you haven't set the `NAUTOBOT_CONFIG` environment variable, or if you did, that the path defined there is the correct one.

```no-highlight
$ echo $NAUTOBOT_CONFIG
```
