# Migrating to systemd

This document contains instructions for migrating from a legacy Nautobot deployment using [supervisor](http://supervisord.org/) to a systemd-based approach.

## Ubuntu

### Uninstall supervisord

```no-highlight
# apt-get remove -y supervisor
```

### Configure systemd

!!! note
    These instructions assume the presence of a Python virtual environment at `/opt/nautobot/venv`. If you have not created this environment, please refer to the [installation instructions](3-nautobot.md#set-up-python-environment) for direction.

We'll use systemd to control the daemonization of Nautobot services. First, copy `contrib/nautobot.service` and `contrib/nautobot-rq.service` to the `/etc/systemd/system/` directory:

```no-highlight
# cp contrib/*.service /etc/systemd/system/
```

!!! note
    You may need to modify the user that the systemd service runs as.  Please verify the user for httpd on your specific release and edit both files to match your httpd service under user and group.  The username could be "nobody", "nginx", "apache", "www-data", or something else.

Then, start the `nautobot` and `nautobot-rq` services and enable them to initiate at boot time:

```no-highlight
# systemctl daemon-reload
# systemctl start nautobot nautobot-rq
# systemctl enable nautobot nautobot-rq
```

You can use the command `systemctl status nautobot` to verify that the WSGI service is running:

```
# systemctl status nautobot.service
● nautobot.service - Nautobot WSGI Service
   Loaded: loaded (/etc/systemd/system/nautobot.service; enabled; vendor preset: enabled)
   Active: active (running) since Sat 2020-10-24 19:23:40 UTC; 25s ago
     Docs: https://nautobot.readthedocs.io/en/stable/
 Main PID: 11993 (gunicorn)
    Tasks: 6 (limit: 2362)
   CGroup: /system.slice/nautobot.service
           ├─11993 /opt/nautobot/venv/bin/python3 /opt/nautobot/venv/bin/gunicorn --pid /var/tmp/nautobot.pid --pythonpath /opt/nautobot/...
           ├─12015 /opt/nautobot/venv/bin/python3 /opt/nautobot/venv/bin/gunicorn --pid /var/tmp/nautobot.pid --pythonpath /opt/nautobot/...
           ├─12016 /opt/nautobot/venv/bin/python3 /opt/nautobot/venv/bin/gunicorn --pid /var/tmp/nautobot.pid --pythonpath /opt/nautobot/...
...
```

At this point, you should be able to connect to the HTTP service at the server name or IP address you provided. If you are unable to connect, check that the nginx service is running and properly configured. If you receive a 502 (bad gateway) error, this indicates that gunicorn is misconfigured or not running. Issue the command `journalctl -xe` to see why the services were unable to start.

!!! info
    Please keep in mind that the configurations provided here are bare minimums required to get Nautobot up and running. You may want to make adjustments to better suit your production environment.
