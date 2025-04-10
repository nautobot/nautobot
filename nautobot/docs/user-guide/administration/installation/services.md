# Deploying Nautobot: Web Service and Workers

## Services Overview

Like most Django applications, Nautobot runs as a [WSGI application](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface) behind an HTTP server.

Nautobot comes preinstalled with [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) to use as the WSGI server, however other WSGI servers are available and should work similarly well. [Gunicorn](http://gunicorn.org/) is a popular alternative.

Additionally, certain Nautobot features (including Git repository synchronization, Webhooks, Jobs, etc.) depend on the presence of Nautobot's [Celery](https://docs.celeryq.dev/en/stable/) background worker process, which is not automatically started with Nautobot and is run as a separate service.

This document will guide you through setting up uWSGI and establishing Nautobot web and Celery worker services to run on system startup.

### Web Service

Nautobot includes a `nautobot-server start` management command that directly invokes uWSGI. This command behaves exactly as uWSGI does, but allows us to maintain a single entrypoint into the Nautobot application.

```no-highlight title="Show help for the nautobot-server start command"
nautobot-server start --help
```

### Worker Service

Nautobot requires at least one worker to consume background tasks required for advanced background features. A `nautobot-server celery` command is included that directly invokes Celery. This command behaves exactly as the Celery command-line utility does, but launches it through Nautobot's environment to share Redis and database connection settings transparently.

```no-highlight title="Show help for the Nautobot worker service"
nautobot-server celery --help
```

--- 2.0.0 "RQ removed from Nautobot"
    Support for RQ has been completely removed from Nautobot.

#### Advanced Task Queue Configuration

You may want to deploy multiple workers and/or multiple queues. For more information see the [task queues](../guides/celery-queues.md) documentation.

+++ 2.3.0 "Worker status view added"
    In Nautobot 2.3.0, `staff` accounts can access a new worker status page at `/worker-status/` to view the status of the Celery worker(s) and the configured queues. The link to this page appears in the "User" dropdown at the bottom of the navigation menu, under the link to the "Profile" page. Use this page with caution as it runs a live query against the Celery worker(s) and may impact performance of your web service.

## Configuration

As the `nautobot` user, copy and paste the following into the file:

=== "Vim"

    ```no-highlight title="Edit uwsgi file with Vim"
    vim $NAUTOBOT_ROOT/uwsgi.ini
    ```

=== "Nano"

    ```no-highlight title="Edit uwsgi file with Nano"
    nano $NAUTOBOT_ROOT/uwsgi.ini
    ```

```ini title="$NAUTOBOT_ROOT/uwsgi.ini"
[uwsgi]
; The IP address (typically localhost) and port that the WSGI process should listen on
socket = 127.0.0.1:8001

; Fail to start if any parameter in the configuration file isn’t explicitly understood by uWSGI
strict = true

; Enable master process to gracefully re-spawn and pre-fork workers
master = true

; Allow Python app-generated threads to run
enable-threads = true

;Try to remove all of the generated file/sockets during shutdown
vacuum = true

; Do not use multiple interpreters, allowing only Nautobot to run
single-interpreter = true

; Shutdown when receiving SIGTERM (default is respawn)
die-on-term = true

; Prevents uWSGI from starting if it is unable load Nautobot (usually due to errors)
need-app = true

; By default, uWSGI has rather verbose logging that can be noisy
disable-logging = true

; Assert that critical 4xx and 5xx errors are still logged
log-4xx = true
log-5xx = true

; Enable HTTP 1.1 keepalive support
http-keepalive = 1

;
; Advanced settings (disabled by default)
; Customize these for your environment if and only if you need them.
; Ref: https://uwsgi-docs.readthedocs.io/en/latest/Options.html
;

; Number of uWSGI workers to spawn. This should typically be 2n+1, where n is the number of CPU cores present.
; processes = 5

; If using subdirectory hosting e.g. example.com/nautobot, you must uncomment this line. Otherwise you'll get double paths e.g. example.com/nautobot/nautobot/.
; Ref: https://uwsgi-docs.readthedocs.io/en/latest/Changelog-2.0.11.html#fixpathinfo-routing-action
; route-run = fixpathinfo:

; If hosted behind a load balancer uncomment these lines, the harakiri timeout should be greater than your load balancer timeout.
; Ref: https://uwsgi-docs.readthedocs.io/en/latest/HTTP.html?highlight=keepalive#http-keep-alive
; harakiri = 65
; add-header = Connection: Keep-Alive
; http-keepalive = 1
```

This configuration should suffice for most initial installations, you may wish to edit this file to change the bound IP
address and/or port number, or to make performance-related adjustments. See [uWSGI
documentation](https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html) for the available configuration parameters.

!!! note
    If you are deploying uWSGI behind a load balancer be sure to configure the harakiri timeout and keep alive appropriately.

## Setup systemd

We'll use `systemd` to control both uWSGI and Nautobot's background worker processes.

!!! warning
    The following steps must be performed with root permissions.

### Nautobot Service

First, we'll establish the `systemd` unit file for the Nautobot web service. Copy and paste the following into the Nautobot service file.

=== "Vim"

    ```no-highlight title="Edit Nautobot service file with Vim"
    sudo vim /etc/systemd/system/nautobot.service
    ```

=== "Nano"

    ```no-highlight title="Edit Nautobot service file with Nano"
    sudo nano /etc/systemd/system/nautobot.service
    ```

```ini title="/etc/systemd/system/nautobot.service"
[Unit]
Description=Nautobot WSGI Service
Documentation=https://docs.nautobot.com/projects/core/en/stable/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment="NAUTOBOT_ROOT=/opt/nautobot"

User=nautobot
Group=nautobot
PIDFile=/var/tmp/nautobot.pid
WorkingDirectory=/opt/nautobot

ExecStart=/opt/nautobot/bin/nautobot-server start --pidfile /var/tmp/nautobot.pid --ini /opt/nautobot/uwsgi.ini
ExecStop=/opt/nautobot/bin/nautobot-server start --stop /var/tmp/nautobot.pid
ExecReload=/opt/nautobot/bin/nautobot-server start --reload /var/tmp/nautobot.pid

Restart=on-failure
RestartSec=30
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Nautobot Background Services

Next, we will setup the `systemd` units for the Celery worker and Celery Beat scheduler.

#### Celery Worker

The Celery worker service consumes tasks from background task queues and is required for taking advantage of advanced
Nautobot features including [Jobs](../../platform-functionality/jobs/index.md), [Custom
Fields](../../platform-functionality/customfield.md), and [Git Repositories](../../platform-functionality/gitrepository.md), among others.

To establish the `systemd` unit file for the Celery worker, copy and paste the following into the Celery service definition.

=== "Vim"

    ```no-highlight title="Edit worker service with Vim"
    sudo vim /etc/systemd/system/nautobot-worker.service
    ```

=== "Nano"

    ```no-highlight title="Edit worker service with Nano"
    sudo nano /etc/systemd/system/nautobot-worker.service
    ```

```ini title="/etc/systemd/system/nautobot-worker.service"
[Unit]
Description=Nautobot Celery Worker
Documentation=https://docs.nautobot.com/projects/core/en/stable/
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
Environment="NAUTOBOT_ROOT=/opt/nautobot"

User=nautobot
Group=nautobot
PIDFile=/var/tmp/nautobot-worker.pid
WorkingDirectory=/opt/nautobot

ExecStart=/opt/nautobot/bin/nautobot-server celery worker --loglevel INFO --pidfile /var/tmp/nautobot-worker.pid

Restart=always
RestartSec=30
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### Celery Beat Scheduler

The Celery Beat scheduler enables the periodic execution of and scheduling of background tasks. It is required to take advantage of the [job scheduling and approval](../../platform-functionality/jobs/job-scheduling-and-approvals.md) features.

!!! warning
    You should only have a single instance of the scheduler running. Having more than one scheduler will cause multiple task executions.

!!! warning
    It's important that the [`TIME_ZONE`](../configuration/settings.md#time_zone) setting on your Nautobot servers and Celery Beat server match to prevent scheduled jobs from running at the wrong time. See the [time zones](../configuration/time-zones.md) documentation for more information.

To establish the `systemd` unit file for the Celery Beat scheduler, copy and paste the following into the scheduler service file.

=== "Vim"

    ```no-highlight title="Edit scheduler service file with Vim"
    sudo vim /etc/systemd/system/nautobot-scheduler.service
    ```

=== "Nano"

    ```no-highlight title="Edit scheduler service file with Nano"
    sudo nano /etc/systemd/system/nautobot-scheduler.service
    ```

```ini title="/etc/systemd/system/nautobot-scheduler.service"
[Unit]
Description=Nautobot Celery Beat Scheduler
Documentation=https://docs.nautobot.com/projects/core/en/stable/
After=network-online.target
Wants=network-online.target

[Service]
Type=exec
Environment="NAUTOBOT_ROOT=/opt/nautobot"

User=nautobot
Group=nautobot
PIDFile=/var/tmp/nautobot-scheduler.pid
WorkingDirectory=/opt/nautobot

ExecStart=/opt/nautobot/bin/nautobot-server celery beat --loglevel INFO --pidfile /var/tmp/nautobot-scheduler.pid

Restart=always
RestartSec=30
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

#### Migrating to Celery from RQ

??? abstract "Details of migrating an existing Nautobot installation from RQ to Celery"
    Prior to migrating, you need to determine whether you have any Apps installed that run custom background tasks that still rely on the RQ worker. There are a few ways to do this. Two of them are:

    * Ask your developer or administrator if there are any Apps running background tasks still using the RQ worker
    * If you are savvy with code, search your code for the `@job` decorator or for `from django_rq import job`

    If you're upgrading from Nautobot version 1.0.x and are NOT running Apps that use the RQ worker, all you really need to do are two things.

    First, you must replace the contents of `/etc/systemd/system/nautobot-worker.service` with the `systemd` unit file provided just above.

    Next, you must update any custom background tasks that you may have written. If you do not have any custom background tasks, then you may continue on to the next section to reload your worker service to use Celery.

    To update your custom tasks, you'll need to do the following.

    * Replace each import `from django_rq import job` with `from nautobot.core.celery import nautobot_task`
    * Replace each decorator of `@job` with `@nautobot_task`

    For example:

    ```diff title="Diff of tasks for celery vs rq"
    diff --git a/task_example.py b/task_example.py
    index f84073fb5..52baf6096 100644
    --- a/task_example.py
    +++ b/task_example.py
    @@ -1,6 +1,6 @@
    -from django_rq import job
    +from nautobot.core.celery import nautobot_task


    -@job("default")
    +@nautobot_task
     def example_task(*args, **kwargs):
         return "examples are cool!"
    (END)
    ```

    !!! warning
        Failure to account for the RQ to Celery migration may break your custom background tasks.

### Configure systemd

Because we just added new service files, you'll need to reload the systemd daemon:

```no-highlight title="Reload the systemd daemon"
sudo systemctl daemon-reload
```

Then, start the `nautobot`, `nautobot-worker`, and `nautobot-scheduler` services and enable them to initiate at boot time:

```no-highlight title="Enable Nautobot services"
sudo systemctl enable --now nautobot nautobot-worker nautobot-scheduler
```

### Verify the service

You can use the command `systemctl status nautobot.service` to verify that the WSGI service is running:

```no-highlight title="Validate services are running"
● nautobot.service - Nautobot WSGI Service
     Loaded: loaded (/etc/systemd/system/nautobot.service; enabled; preset: enabled)
     Active: active (running) since Mon 2024-07-29 20:44:21 UTC; 5s ago
       Docs: https://docs.nautobot.com/projects/core/en/stable/
   Main PID: 7340 (nautobot-server)
      Tasks: 2 (limit: 4658)
     Memory: 135.2M (peak: 135.5M)
        CPU: 3.445s
     CGroup: /system.slice/nautobot.service
             ├─7340 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start --pidfile /var/tmp/nautobot.pid
             └─7351 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start --pidfile /var/tmp/nautobot.pid
```

!!! note
    If the Nautobot service fails to start, issue the command `journalctl -eu nautobot.service` to check for log messages that may indicate the problem.

Once you've verified that the WSGI service and worker are up and running, move on to [HTTP server setup](http-server.md).

## Troubleshooting

### Operational Error: Incorrect string value

When using MySQL as a database backend, if you encounter a server error along the lines of `Incorrect string value: '\\xF0\\x9F\\x92\\x80' for column`, it is because you are running afoul of the legacy implementation of Unicode (aka `utf8`) encoding in MySQL. This often occurs when using modern Unicode glyphs like the famous poop emoji.

Please see the [configuration guide on MySQL Unicode settings](../configuration/settings.md#databases) for instructions on how to address this.

Please see [Computed fields with fallback value that is unicode results in OperationalError (#645)](https://github.com/nautobot/nautobot/issues/645) for more details.

### SVG images not rendered

When serving Nautobot directly from uWSGI on RedHat or CentOS there may be a problem rendering .svg images to include the Nautobot logo. On the RedHat based operating systems there is no file `/etc/mime.types` by default, unfortunately, uWSGI looks for this file to serve static files (see [Serving static files with uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/StaticFiles.html#mime-types)). To work around this copy the file `/etc/mime.types` from a known good system for example an Ubuntu/Debian system or even the Nautobot container to `/opt/nautobot/mime.types`. Then add the following line to your `uwsgi.ini` file and restart the Nautobot services:

```no-highlight title="Add MIME file settings to uwsgi.ini"
mime-file = /opt/nautobot/mime.types
```

Alternatively, host Nautobot behind Nginx as instructed in [HTTP server setup](http-server.md).

### Test Redis Connectivity

??? info "Test Redis Connectivity with Python"

    From a nautobot shell (`nautobot-server shell_plus`) use the following Python commands to test connectivity to your Redis server. If successful, python should not return any exceptions.

    ```py title="Test Redis Connectivity via Python"
    import os
    import redis
    from nautobot.core.settings_funcs import parse_redis_connection

    connection = parse_redis_connection(0)
    client = redis.from_url(connection)
    client.ping() # test basic connectivity
    client.keys() # retrieve a list of keys in the redis database
    client.auth(password=os.getenv("NAUTOBOT_REDIS_PASSWORD")) # test password authentication
    ```
