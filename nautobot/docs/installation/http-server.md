# Configuring an HTTP Server

This documentation provides example configurations for [NGINX](https://www.nginx.com/resources/wiki/) though any HTTP server which supports WSGI should be compatible.

## Obtain an SSL Certificate

To enable HTTPS access to Nautobot, you'll need a valid SSL certificate. You can purchase one from a trusted commercial
provider, obtain one for free from [Let's Encrypt](https://letsencrypt.org/getting-started/), or generate your own
(although self-signed certificates are generally untrusted). Both the public certificate and private key files need to
be installed on your Nautobot server in a secure location that is readable only by the `root` user.

!!! warning
    The command below can be used to generate a self-signed certificate for testing purposes, however it is strongly recommended to use a certificate from a trusted authority in production.

Two files will be created: the public certificate (`nautobot.crt`) and the private key (`nautobot.key`). The certificate is published to the world, whereas the private key must be kept secret at all times.

!!! info
    Some Linux installations, including CentOS, have changed the location for SSL certificates from `/etc/ssl/` to `/etc/pki/tls/`. The command below may need to be changed to reflect the certificate location.

    The following command will prompt you for additional details of the certificate; all of which are optional.

```no-highlight
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nautobot.key \
  -out /etc/ssl/certs/nautobot.crt
```

## HTTP Server Installation

Any HTTP server of your choosing is supported. For your convenience, setup instructions for NGINX are provided here.

!!! warning
    The following steps must be performed with root permissions.

### NGINX

[NGINX](https://www.nginx.com/resources/wiki/) is a free, open source, high-performance HTTP server and reverse proxy
and is by far the most popular choice.

#### Install NGINX

Begin by installing NGINX:

On Ubuntu:

```no-highlight
sudo apt install -y nginx
```

On CentOS/RHEL:

```no-highlight
sudo dnf install -y nginx
```

#### Configure NGINX

Once NGINX is installed, copy and paste the following NGINX configuration into
`/etc/nginx/sites-available/nautobot.conf` for Ubuntu or `/etc/nginx/conf.d/nautobot.conf` for CentOS/RHEL:

!!! note
    If the file location of SSL certificates had to be changed in the [Obtain an SSL Certificate](#obtain-an-ssl-certificate) step above, then the location will need to be changed in the NGINX configuration below.

```nginxconf
server {
    listen 443 ssl http2 default_server;
    listen [::]:443 ssl http2 default_server;

    server_name _;

    ssl_certificate /etc/ssl/certs/nautobot.crt;
    ssl_certificate_key /etc/ssl/private/nautobot.key;

    client_max_body_size 25m;

    location /static/ {
        alias /opt/nautobot/static/;
    }

    # For subdirectory hosting, you'll want to toggle this (e.g. `/nautobot/`).
    # Don't forget to set `FORCE_SCRIPT_NAME` in your `nautobot_config.py` to match.
    # location /nautobot/ {
    location / {
        include uwsgi_params;
        uwsgi_pass  127.0.0.1:8001;
        uwsgi_param Host $host;
        uwsgi_param X-Real-IP $remote_addr;
        uwsgi_param X-Forwarded-For $proxy_add_x_forwarded_for;
        uwsgi_param X-Forwarded-Proto $http_x_forwarded_proto;

        # If you want subdirectory hosting, uncomment this. The path must match
        # the path of this location block (e.g. `/nautobot`). For NGINX the path
        # MUST NOT end with a trailing "/".
        # uwsgi_param SCRIPT_NAME /nautobot;
    }

}

server {
    # Redirect HTTP traffic to HTTPS
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 301 https://$host$request_uri;
}
```

#### Enable Nautobot

On Ubuntu:

To enable the Nautobot site, you'll need to delete `/etc/nginx/sites-enabled/default` and create a symbolic link in the
`sites-enabled` directory to the configuration file you just created:

```no-highlight
sudo rm -f /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/nautobot.conf /etc/nginx/sites-enabled/nautobot.conf
```

On CentOS:

Run the following command to disable the default site that comes with the `nginx` package:

```no-highlight
sudo sed -i 's@ default_server@@' /etc/nginx/nginx.conf
```

#### Restart NGINX

Finally, restart the `nginx` service to use the new configuration.

```no-highlight
sudo systemctl restart nginx
```

!!! info
    If the restart fails, and you changed the default key location, check to make sure the `nautobot.conf` file you pasted has the updated key location. For example, CentOS requires keys to be in `/etc/pki/tls/` instead of `/etc/ssl/`.

## Confirm Permissions for NAUTOBOT_ROOT

Ensure that the `NAUTOBOT_ROOT` permissions are set to `755`.
If permissions need to be changed, as the `nautobot` user run:

```no-highlight
chmod 755 $NAUTOBOT_ROOT
```

## Confirm Connectivity

At this point, you should be able to connect to the HTTPS service at the server name or IP address you provided. If you used a self-signed certificate, you will likely need to explicitly allow connectivity in your browser.

!!! info
    Please keep in mind that the configurations provided here are bare minimums required to get Nautobot up and running. You may want to make adjustments to better suit your production environment.

!!! warning
    Certain components of Nautobot (such as the display of rack elevation diagrams) rely on the use of embedded objects. Ensure that your HTTP server configuration does not override the `X-Frame-Options` response header set by Nautobot.

## Troubleshooting

### Unable to Connect

If you are unable to connect to the HTTP server, check that:

- NGINX is running and configured to listen on the correct port.
- Access is not being blocked by a firewall somewhere along the path. (Try connecting locally from the server itself.)

### Static Media Failure

If you get a *Static Media Failure; The following static media file failed to load: css/base.css*, verify the permissions on the `$NAUTOBOT_ROOT` directory are `755`.

Example of correct permissions (at the `[root@localhost ~]#` prompt)

```no-highlight
ls -l /opt/
```

Example output:

```no-highlight
total 4
drwxr-xr-x. 11 nautobot nautobot 4096 Apr  5 11:24 nautobot
[root@localhost ~]#
```

If the permissions are not correct, modify them accordingly.

Example of modifying the permissions:

```no-highlight
ls -l /opt/
```

Example output:

```no-highlight
total 4
drwx------. 11 nautobot nautobot 4096 Apr  5 10:00 nautobot
```

At the prompt `[nautobot@localhost ~]$` execute:

```no-highlight
chmod 755 $NAUTOBOT
```

Then to verify that the user has the permissions to the directory execute at the `[nautobot@localhost ~]$` prompt:

```no-highlight
ls -l /opt/
```

Example output shows that the user and group are both `nautobot` below:

```no-highlight
total 4
drwxr-xr-x. 11 nautobot nautobot 4096 Apr  5 11:24 nautobot
```

### 502 Bad Gateway

If you are able to connect but receive a 502 (bad gateway) error, check the following:

- The uWSGI worker processes are running (`systemctl status nautobot` should show a status of `active (running)`)
- NGINX is configured to connect to the port on which uWSGI is listening (default is `8001`).
- SELinux may be preventing the reverse proxy connection. You may need to allow HTTP network connections with the
  command `setsebool -P httpd_can_network_connect 1`. For further information, view the [SELinux
  troubleshooting](selinux-troubleshooting.md) guide.
