# Deploying Nautobot: Web Service and Worker

!!! warning
    As of Nautobot v1.0.0b2 these instructions are in a pre-release state and will be evolving rapidly!

Like most Django applications, Nautobot runs as a [WSGI application](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface) behind an HTTP server.

Nautobot comes preinstalled with [uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) to use as the WSGI server, however other WSGI servers are available and should work similarly well. [Gunicorn](http://gunicorn.org/) is a popular alternative.

This document will guide you through setting up uWSGI and establishing Nautobot web services to run on system startup.

Nautobot includes a `nautobot-server start` management command that directly invokes uWSGI. This command behaves exactly as uWSGI does, but allows us to maintain a single entrypoint into the Nautobot application.

```no-highlight
$ nautobot-server start --help
```

## Configuration

Copy and paste the following into `$NAUTOBOT_ROOT/uwsgi.ini`:

```ini
[uwsgi]
; The IP address (typically localhost) and port that the WSGI process should listen on
http-socket = 127.0.0.1:8001

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

;
; Advanced settings (disabled by default)
; Customize these for your environment if and only if you need them.
; Ref: https://uwsgi-docs.readthedocs.io/en/latest/Options.html
;

; Number of uWSGI workers to spawn. This should typically be 2n+1, where n is the number of CPU cores present.
; processes = 5
```

This configuration should suffice for most initial installations, you may wish to edit this file to change the bound IP
address and/or port number, or to make performance-related adjustments. See [uWSGI
documentation](https://uwsgi-docs.readthedocs.io/en/latest/Configuration.html) for the available configuration parameters.

## Setup systemd

We'll use `systemd` to control both uWSGI and Nautobot's background worker process.

!!! warning
    The following steps must be performed with root permissions.

### Nautobot service

First, copy and paste the following into `/etc/systemd/system/nautobot.service`:

```
[Unit]
Description=Nautobot WSGI Service
Documentation=https://nautobot.readthedocs.io/
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

### Nautobot Worker service

Next, copy and paste the following into `/etc/systemd/system/nautobot-worker.service`:

```
[Unit]
Description=Nautobot Request Queue Worker
Documentation=https://nautobot.readthedocs.io/
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
$ sudo systemctl daemon-reload
```

Then, start the `nautobot` and `nautobot-worker` services and enable them to initiate at boot time:

```no-highlight
$ sudo systemctl enable --now nautobot nautobot-worker
```

### Verify the service
You can use the command `systemctl status nautobot.service` to verify that the WSGI service is running:

```no-highlight
● nautobot.service - Nautobot WSGI Service
     Loaded: loaded (/etc/systemd/system/nautobot.service; enabled; vendor preset: enabled)
     Active: active (running) since Fri 2021-03-05 22:23:33 UTC; 35min ago
       Docs: https://nautobot.readthedocs.io/en/latest/
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
    If the Nautobot service fails to start, issue the command `journalctl -eu nautobot.service` to check for log messages that
    may indicate the problem.

Once you've verified that the WSGI service and worker are up and running, move on to [HTTP server setup](../http-server).
