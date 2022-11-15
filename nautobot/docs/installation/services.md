# Deploying Nautobot: Web Service and Workers

## Services Overview

Like most Django applications, Nautobot runs as a [WSGI application](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface) behind an HTTP server.

Nautobot comes preinstalled with [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) to use as the WSGI server, however other WSGI servers are available and should work similarly well. [Gunicorn](http://gunicorn.org/) is a popular alternative.

Additionally, certain Nautobot features (including Git repository synchronization, Webhooks, Jobs, etc.) depend on the presence of Nautobot's [Celery](https://docs.celeryq.dev/en/stable/) background worker process, which is not automatically started with Nautobot and is run as a separate service.

This document will guide you through setting up uWSGI and establishing Nautobot web and Celery worker services to run on system startup.

### Web Service

Nautobot includes a `nautobot-server start` management command that directly invokes uWSGI. This command behaves exactly as uWSGI does, but allows us to maintain a single entrypoint into the Nautobot application.

```no-highlight
nautobot-server start --help
```

### Worker Service

Nautobot requires at least one worker to consume background tasks required for advanced background features. A `nautobot-server celery` command is included that directly invokes Celery. This command behaves exactly as the Celery command-line utility does, but launches it through Nautobot's environment to share Redis and database connection settings transparently.

```no-highlight
nautobot-server celery --help
```

+/- 1.1.0
    Prior to version 1.1.0, Nautobot utilized RQ as the primary background task worker. As of Nautobot 1.1.0, RQ is now *deprecated*. RQ and the `@job` decorator for custom tasks are still supported for now, but users should [migrate the primary worker to Celery](#migrating-to-celery-from-rq) and then, *only if still required*, [run RQ concurrently with the Celery worker](#concurrent-celery-and-rq-nautobot-workers). RQ and the `@job` decorator will no longer be documented, and support for RQ will be removed in a future release.

#### Advanced Task Queue Configuration

You may want to deploy multiple workers and/or multiple queues. For more information see the [task queues](../administration/celery-queues.md) documentation.

## Configuration

As the `nautobot` user, copy and paste the following into `$NAUTOBOT_ROOT/uwsgi.ini`:

```ini
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

First, we'll establish the `systemd` unit file for the Nautobot web service. Copy and paste the following into `/etc/systemd/system/nautobot.service`:

```ini
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

+/- 1.1.0
    Prior to version 1.1.0, Nautobot utilized RQ as the primary background task worker. As of Nautobot 1.1.0, RQ is now *deprecated* and has been replaced with Celery. RQ can still be used by plugins for now, but will be removed in a future release. Please [migrate your deployment to utilize Celery as documented below](#migrating-to-celery-from-rq).

Next, we will setup the `systemd` units for the Celery worker and Celery Beat scheduler.

#### Celery Worker

+++ 1.1.0

The Celery worker service consumes tasks from background task queues and is required for taking advantage of advanced
Nautobot features including [Jobs](../additional-features/jobs.md), [Custom
Fields](../models/extras/customfield.md), and [Git Repositories](../models/extras/gitrepository.md), among others.

To establish the `systemd` unit file for the Celery worker, copy and paste the following into `/etc/systemd/system/nautobot-worker.service`:

```ini
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

+++ 1.2.0

The Celery Beat scheduler enables the periodic execution of and scheduling of background tasks. It is required to take
advantage of the [job scheduling and approval](../additional-features/job-scheduling-and-approvals.md) features.

To establish the `systemd` unit file for the Celery Beat scheduler, copy and paste the following into `/etc/systemd/system/nautobot-scheduler.service`:

```ini
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

Prior to migrating, you need to determine whether you have any plugins installed that run custom background tasks that still rely on the RQ worker. There are a few ways to do this. Two of them are:

* Ask your developer or administrator if there are any plugins running background tasks still using the RQ worker
* If you are savvy with code, search your code for the `@job` decorator or for `from django_rq import job`

If you're upgrading from Nautobot version 1.0.x and are NOT running plugins that use the RQ worker, all you really need to do are two things.

First, you must replace the contents of `/etc/systemd/system/nautobot-worker.service` with the `systemd` unit file provided just above.

Next, you must update any custom background tasks that you may have written. If you do not have any custom background tasks, then you may continue on to the next section to reload your worker service to use Celery.

To update your custom tasks, you'll need to do the following.

* Replace each import `from django_rq import job` with `from nautobot.core.celery import nautobot_task`
* Replace each decorator of `@job` with `@nautobot_task`

For example:

```diff
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

If you are using plugins that use custom background tasks but have not yet made the change described above, you must run the [RQ worker concurrently with the Celery worker](#concurrent-celery-and-rq-nautobot-workers) until the plugin can be updated.

!!! warning
    Failure to account for the Celery-to-RQ migration may break your custom background tasks

#### Concurrent Celery and RQ Nautobot Workers

If you must run the Celery and RQ workers concurrently, you must also configure the (deprecated) RQ worker.

Copy and paste the following into `/etc/systemd/system/nautobot-rq-worker.service`:

```ini
[Unit]
Description=Nautobot Request Queue Worker
Documentation=https://docs.nautobot.com/projects/core/en/stable/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment="NAUTOBOT_ROOT=/opt/nautobot"

User=nautobot
Group=nautobot
WorkingDirectory=/opt/nautobot

ExecStart=/opt/nautobot/bin/nautobot-server rqworker

Restart=on-failure
RestartSec=30
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Configure systemd

Because we just added new service files, you'll need to reload the systemd daemon:

```no-highlight
sudo systemctl daemon-reload
```

Then, start the `nautobot`, `nautobot-worker`, and `nautobot-scheduler` services and enable them to initiate at boot time:

```no-highlight
sudo systemctl enable --now nautobot nautobot-worker nautobot-scheduler
```

If you are also running the RQ worker, repeat the above command for the RQ service:

```no-highlight
sudo systemctl enable --now nautobot-rq-worker
```

!!! tip
    If you are running the concurrent RQ worker, you must remember to enable/check/restart the `nautobot-rq-worker` process as needed, oftentimes in addition to the `nautobot-worker` process.

### Verify the service

You can use the command `systemctl status nautobot.service` to verify that the WSGI service is running:

```no-highlight
● nautobot.service - Nautobot WSGI Service
     Loaded: loaded (/etc/systemd/system/nautobot.service; enabled; vendor preset: enabled)
     Active: active (running) since Fri 2021-03-05 22:23:33 UTC; 35min ago
       Docs: https://docs.nautobot.com/projects/core/en/stable/
   Main PID: 6992 (nautobot-server)
      Tasks: 16 (limit: 9513)
     Memory: 221.1M
     CGroup: /system.slice/nautobot.service
             ├─6992 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start />
             ├─7007 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start />
             ├─7010 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start />
             ├─7013 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start />
             ├─7016 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start />
             └─7019 /opt/nautobot/bin/python3 /opt/nautobot/bin/nautobot-server start />
```

!!! note
    If the Nautobot service fails to start, issue the command `journalctl -eu nautobot.service` to check for log messages that may indicate the problem.

Once you've verified that the WSGI service and worker are up and running, move on to [HTTP server setup](http-server.md).

## Troubleshooting

### Operational Error: Incorrect string value

When using MySQL as a database backend, if you encounter a server error along the lines of `Incorrect string value: '\\xF0\\x9F\\x92\\x80' for column`, it is because you are running afoul of the legacy implementation of Unicode (aka `utf8`) encoding in MySQL. This often occurs when using modern Unicode glyphs like the famous poop emoji.

Please see the [configuration guide on MySQL Unicode settings](../configuration/required-settings.md#mysql-unicode-settings) for instructions on how to address this.

Please see [Computed fields with fallback value that is unicode results in OperationalError (#645)](https://github.com/nautobot/nautobot/issues/645) for more details.

### SVG images not rendered

When serving Nautobot directly from uWSGI on RedHat or CentOS there may be a problem rendering .svg images to include the Nautobot logo. On the RedHat based operating systems there is no file `/etc/mime.types` by default, unfortunately, uWSGI looks for this file to serve static files (see [Serving static files with uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/StaticFiles.html#mime-types)). To work around this copy the file `/etc/mime.types` from a known good system for example an Ubuntu/Debian system or even the Nautobot container to /opt/nautobot/mime.types. Then add the following line to your `uwsgi.ini` file and restart the Nautobot services:

```no-highlight
mime-file = /opt/nautobot/mime.types
```

Alternatively, host Nautobot behind Nginx as instructed in [HTTP server setup](http-server.md).
