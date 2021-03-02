# Gunicorn

!!! warning
    As of Nautobot v1.0.0b1 these instructions are in a pre-release state and will be evolving rapidly!

Like most Django applications, Nautobot runs as a [WSGI
application](https://en.wikipedia.org/wiki/Web_Server_Gateway_Interface) behind an HTTP server. This documentation shows
how to install and configure [Gunicorn](http://gunicorn.org/) (which is automatically installed with Nautobot) for this
role, however other WSGI servers are available and should work similarly well.
[uWSGI](https://uwsgi-docs.readthedocs.io/en/latest/) is a popular alternative.

## Configuration

Copy and paste the following into `/opt/nautobot/gunicorn.py`:

```python
# The IP address (typically localhost) and port that the Netbox WSGI process should listen on
bind = '127.0.0.1:8001'

# Number of gunicorn workers to spawn. This should typically be 2n+1, where
# n is the number of CPU cores present.
workers = 5

# Number of threads per worker process
threads = 3

# Timeout (in seconds) for a request to complete
timeout = 120

# The maximum number of requests a worker can handle before being respawned
max_requests = 5000
max_requests_jitter = 500
```

This configuration should suffice for most initial installations, you may wish to edit this file to change the bound IP
address and/or port number, or to make performance-related adjustments. See [Gunicorn
documentation](https://docs.gunicorn.org/en/stable/configure.html) for the available configuration parameters.

## Setup systemd

We'll use `systemd` to control both Gunicorn and Nautobot's background worker process. 

!!! warning
    The following steps must be performed with root permissions.

### Nautobot service

First, copy and paste the following into `/etc/systemd/system/nautobot.service`:

```
[Unit]
Description=Nautobot WSGI Service
Documentation=https://nautobot.readthedocs.io/en/latest/
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
Environment="NAUTOBOT_ROOT=/opt/nautobot"

User=nautobot
Group=nautobot
PIDFile=/var/tmp/nautobot.pid
WorkingDirectory=/opt/nautobot

ExecStart=/opt/nautobot/bin/gunicorn --pid /var/tmp/nautobot.pid --config /opt/nautobot/gunicorn.py nautobot.core.wsgi

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
Documentation=https://nautobot.readthedocs.io/en/latest/
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

Then, start the `nautobot` and `nautobot-worker` services and enable them to initiate at boot time:

```no-highlight
sudo systemctl start nautobot nautobot-worker
sudo systemctl enable nautobot nautobot-worker
```

### Verify the service
You can use the command `systemctl status nautobot` to verify that the WSGI service is running:

```no-highlight
$ sudo systemctl status nautobot.service
● nautobot.service - Nautobot WSGI Service
     Loaded: loaded (/etc/systemd/system/nautobot.service; enabled; vendor preset: enabled)
     Active: active (running) since Tue 2020-11-17 16:18:23 UTC; 3min 35s ago
       Docs: https://nautobot.readthedocs.io/
   Main PID: 22836 (gunicorn)
      Tasks: 6 (limit: 2345)
     Memory: 339.3M
     CGroup: /system.slice/nautobot.service
             ├─22836 /opt/nautobot/bin/python3 /opt/nautobot/bin/gunicorn --pid>
             ├─22854 /opt/nautobot/bin/python3 /opt/nautobot/bin/gunicorn --pid>
             ├─22855 /opt/nautobot/bin/python3 /opt/nautobot/bin/gunicorn --pid>
```

!!! note
    If the Nautobot service fails to start, issue the command `journalctl -eu nautobot` to check for log messages that
    may indicate the problem.

Once you've verified that the WSGI workers are up and running, move on to HTTP server setup.
