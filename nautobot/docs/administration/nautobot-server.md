# The Nautobot Server Command

Nautobot includes a command-line (CLI) management utility called `nautobot-server`, that is used as a single entrypoint for common administrative tasks.

## Background

For those familiar with Django applications, this CLI utility works exactly as a project's `manage.py` script would, except that it comes bundled with the Nautobot code and therefore it gets automatically installed in the `bin` directory of your application environment.

!!! important
    Since Nautobot is a Django application, there are a number of built-in management commands that will not be covered in this document. Please see the [official Django documentation on management commands](https://docs.djangoproject.com/en/stable/ref/django-admin/#available-commands) for more information.

## Getting Help

To see all available management commands:

```no-highlight
$ nautobot-server help
```

All management commands have a `-h/--help` flag to list all available arguments for that command, for example:

```no-highlight
$ nautobot-server migrate --help
```

## Available Commands

### `collectstatic`

`nautobot-server collectstatic`

Collect static files into [`STATIC_ROOT`](../../configuration/optional-settings/#static_root).

```no-highlight
$ nautobot-server collectstatic

965 static files copied to '/opt/nautobot/static'.
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `collectstatic`](https://docs.djangoproject.com/en/stable/ref/django-admin/#collectstatic) for more information.

### `createsuperuser`

`nautobot-server createsuperuser`

Creates a superuser account that has all permissions. 

```no-highlight
$ nautobot-server createsuperuser
Username (leave blank to use 'jathan'): example
Email address: example@localhost
Password:
Password (again):
Superuser created successfully.
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `createsuperuser`](https://docs.djangoproject.com/en/stable/ref/django-admin/#createsuperuser) for more information.

### `dbshell`

`nautobot-server dbshell`

A shell for your PostgreSQL database. This can be very useful in troubleshooting raw database issues.

!!! danger
    This is an advanced feature that gives you direct access to run raw SQL queries. Use this very cautiously as you can cause irreparable damage to your Nautobot installation.

```no-highlight
$ nautobot-server dbshell
psql (12.6 (Ubuntu 12.6-0ubuntu0.20.04.1))
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
Type "help" for help.

nautobot=> \conninfo
You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "::1") at port "5432".
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
nautobot=> \q
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `dbshell`](https://docs.djangoproject.com/en/stable/ref/django-admin/#dbshell) for more information.

### `generate_secret_key`

`nautobot-server generate_secret_key`

Generates a new [`SECRET_KEY`](../../configuration/required-settings/#secret_key) that can be used in your `nautobot_config.py`:

```no-highlight
$ nautobot-server generate_secret_key
e!j=vrlhz-!wl8p_3+q5s5cph29nzj$xm81eap-!&n!_9^du09
```

### `init`

`nautobot-server init [config_path]`

Generates a new configuration with all of the default settings provided for you, and will also generate a unique[`SECRET_KEY`](../../configuration/required-settings/#secret_key).

By default the file will be created at `$HOME/.nautobot/nautobot_config.py`:

```no-highlight
$ nautobot-server init
Configuration file created at '/home/example/.nautobot/nautobot_config.py
```

For more information on configuring Nautobot for the first time or on more advanced configuration patterns, please see the guide on [Nautobot Configuration](../../configuration).

### `invalidate`

`nautobot-server invalidate`

Invalidates cache for entire app, model or particular instance. Most commonly you will see us recommend clearing the entire cache using `invalidate all`:

```no-highlight
$ nautobot-server invalidate all
```

There are a number of other options not covered here.

!!! note
    This is a built-in management command provided by the [Cacheops plugin](https://github.com/Suor/django-cacheops) Nautobot for caching. Please see the official [Cacheops documentation on `invalidate`](https://github.com/Suor/django-cacheops#invalidation) for more information.

### `migrate`

`nautobot-server migrate [app_label] [migration_name]`

Initialize a new database or run any pending database migrations to an existing database.

```no-highlight
$ nautobot-server migrate
Wrapping model clean methods for custom validators failed because the ContentType table was not available or populated. This is normal during the execution of the migration command for the first time.
Operations to perform:
  Apply all migrations: admin, auth, circuits, contenttypes, dcim, extras, ipam, sessions, taggit, tenancy, users, virtualization
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
... (truncated for brevity of documentation) ...
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `migrate`](https://docs.djangoproject.com/en/stable/ref/django-admin/#migrate) for more information.

### `nbshell`

`nautobot-server nbshell`

An interactive Python shell with all of the database models and various other utilities already imported for you. This is immensely useful for direct access to manipulating database objects.

!!! danger
    This is an advanced feature that gives you direct access to the Django database models. Use this very cautiously as you can cause irreparable damage to your Nautobot installation.

```no-highlight
$ nautobot-server nbshell
### Nautobot interactive shell (localhost)
### Python 3.8.7 | Django 3.1.7 | Nautobot 1.0.0
### lsmodels() will show available models. Use help(<model>) for more info.
>>>
```

Please see the dedicated guide on the [Nautobot Shell](nautobot-shell.md) for more information.

### `post_upgrade`

`nautobot-server post_upgrade`

Performs common server post-upgrade operations using a single entrypoint.

This will run the following management commands with default settings, in order:

- `migrate`
- `trace_paths`
- `collectstatic`
- `remove_stale_contenttypes`
- `clearsessions`
- `invalidate all`

!!! note
    Commands listed here that are not covered in this document here are Django built-in commands. 

`--no-clearsessions`<br>
Do not automatically clean out expired sessions.

`--no-collectstatic`<br>
Do not automatically collect static files into a single location.

`--no-invalidate-all`<br>
Do not automatically invalidate cache for entire application.

`--no-migrate`<br>
Do not automatically perform any database migrations.

`--no-remove-stale-contenttypes`<br>
Do not automatically remove stale content types.

`--no-trace-paths`<br>
Do not automatically generate missing cable paths.

```no-highlight
$ nautobot-server post_upgrade
Performing database migrations...
Operations to perform:
  Apply all migrations: admin, auth, circuits, contenttypes, dcim, extras, ipam, sessions, taggit, tenancy, users, virtualization
Running migrations:
  No migrations to apply.

Generating cable paths...
Found no missing circuit termination paths; skipping
Found no missing console port paths; skipping
Found no missing console server port paths; skipping
Found no missing interface paths; skipping
Found no missing power feed paths; skipping
Found no missing power outlet paths; skipping
Found no missing power port paths; skipping
Finished.

Collecting static files...

0 static files copied to '/opt/nautobot/static', 965 unmodified.

Removing stale content types...

Removing expired sessions...

Invalidating cache...
```

### `renaturalize`

`nautobot-server renaturalize [app_label.ModelName [app_label.ModelName ...]]`

Recalculate natural ordering values for the specified models. 

This defaults to recalculating natural ordering on all models which have one or more fields of type `NaturalOrderingField`:

```no-highlight
$ nautobot-server renaturalize
Renaturalizing 21 models.
dcim.ConsolePort.name (_name)... 196
dcim.ConsoleServerPort.name (_name)... 0
dcim.PowerPort.name (_name)... 392
dcim.PowerOutlet.name (_name)... 0
dcim.Interface.name (_name)... 7161
dcim.FrontPort.name (_name)... 0
dcim.RearPort.name (_name)... 0
dcim.DeviceBay.name (_name)... 0
dcim.InventoryItem.name (_name)... 1
dcim.Device.name (_name)... 208
dcim.ConsolePortTemplate.name (_name)... 2
dcim.ConsoleServerPortTemplate.name (_name)... 0
dcim.PowerPortTemplate.name (_name)... 4
dcim.PowerOutletTemplate.name (_name)... 0
dcim.InterfaceTemplate.name (_name)... 221
dcim.FrontPortTemplate.name (_name)... 0
dcim.RearPortTemplate.name (_name)... 0
dcim.DeviceBayTemplate.name (_name)... 0
dcim.Rack.name (_name)... 156
dcim.Site.name (_name)... 22
virtualization.VMInterface.name (_name)... 0
Done.
```

You may optionally specify or more specific models (each prefixed with its app_label) to renaturalize:

```no-highlight
$ nautobot-server renaturalize dcim.Device
Renaturalizing 1 models.
dcim.Device.name (_name)... 208
Done.
```

### `runjob`

`nautobot-server runjob [job]`

Run a job (script, report) to validate or update data in Nautobot.

`--commit`<br>
Commit changes to DB (defaults to dry-run if unset).

```no-highlight
$ nautobot-server runjob local/example/MyJobWithVars --commit
```

Please see the [guide on Jobs](../additional-features/jobs.md) for more information on working with and running jobs.

### `start`

`nautobot-server start`

Directly invoke uWSGI to start a Nautobot server suitable for production use. This command behaves exactly as uWSGI does, but allows us to maintain a single entrypoint into the Nautobot application.

!!! note
    uWSGI offers an overwhelming amount of command-line arguments that could not possibly be covered here. Please see the [official uWSGI Options guide](https://uwsgi-docs.readthedocs.io/en/latest/Options.html) for more information.

```no-highlight
$ nautobot-server start --ini ./uwsgi.ini
[uWSGI] getting INI configuration from ./uwsgi.ini
[uwsgi-static] added mapping for /static => /opt/nautobot/static
*** Starting uWSGI 2.0.19.1 (64bit) on [Thu Mar 11 21:13:22 2021] ***
compiled with version: 8.3.1 20190311 (Red Hat 8.3.1-3) on 23 September 2020 02:39:40
os: Linux-5.4.0-52-generic #57-Ubuntu SMP Thu Oct 15 10:57:00 UTC 2020
nodename: jathan-nautobot-testing
machine: x86_64
clock source: unix
pcre jit disabled
detected number of CPU cores: 48
current working directory: /opt/nautobot
detected binary path: /usr/bin/python3.8
your processes number limit is 256070
your memory page size is 4096 bytes
detected max file descriptor number: 1024
building mime-types dictionary from file /etc/mime.types...567 entry found
lock engine: pthread robust mutexes
thunder lock: disabled (you can enable it with --thunder-lock)
uwsgi socket 0 bound to TCP address 0.0.0.0:9191 fd 7
Python version: 3.8.5 (default, Jan 27 2021, 15:41:15)  [GCC 9.3.0]
--- Python VM already initialized ---
Python main interpreter initialized at 0x2573e30
python threads support enabled
your server socket listen backlog is limited to 1024 connections
your mercy for graceful operations on workers is 60 seconds
mapped 636432 bytes (621 KB) for 15 cores
*** Operational MODE: preforking+threaded ***
WSGI app 0 (mountpoint='') ready in 0 seconds on interpreter 0x2573e30 pid: 112153 (default app)
spawned uWSGI master process (pid: 112153)
spawned uWSGI worker 1 (pid: 112159, cores: 3)
spawned uWSGI worker 2 (pid: 112162, cores: 3)
spawned uWSGI worker 3 (pid: 112165, cores: 3)
spawned uWSGI worker 4 (pid: 112168, cores: 3)
spawned uWSGI worker 5 (pid: 112171, cores: 3)
```

Please see the guide on [Deploying Nautobot](../installation/wsgi.md) for our recommended configuration for use with uWSGI.

### `trace_paths`

`nautobot-server trace_paths`

Generate any missing cable paths among all cable termination objects in Nautobot.

After upgrading the database or working with Cables, Circuits, or other related objects, there may be a need to rebuild cached cable paths.

`--force`<br>
Force recalculation of all existing cable paths.

`--no-input`<br>
Do not prompt user for any input/confirmation.

```no-highlight
$ nautobot-server trace_paths
Found no missing circuit termination paths; skipping
Found no missing console port paths; skipping
Found no missing console server port paths; skipping
Found no missing interface paths; skipping
Found no missing power feed paths; skipping
Found no missing power outlet paths; skipping
Found no missing power port paths; skipping
Finished.
```

!!! note
    This command is safe to run at any time. If it does detect any changes, it will exit cleanly.

### `webhook_receiver`

`nautobot-server webhook_receiver`

Start a simple listener to display received HTTP requests.

`--port PORT`<br>
Optional port number (default: `9000`)

`--no-headers`<br>
Hide HTTP request headers.

```no-highlight
$ nautobot-server webhook_receiver --port 9001 --no-headers
Listening on port http://localhost:9000. Stop with CONTROL-C.
```

Please see the guide on [Troubleshooting Webhooks](../models/extras/webhook.md#troubleshooting) for more information.
