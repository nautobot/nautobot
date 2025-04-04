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

=== "Ubuntu/Debian"

    ```no-highlight title="Create SSL certificate"
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/ssl/private/nautobot.key \
      -out /etc/ssl/certs/nautobot.crt
    ```

=== "Fedora/RHEL"

    ```no-highlight title="Create SSL certificate"
    sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
      -keyout /etc/pki/tls/private/nautobot.key \
      -out /etc/pki/tls/certs/nautobot.crt
    ```

## HTTP Server Installation

Any HTTP server of your choosing is supported. For your convenience, setup instructions for NGINX are provided here.

!!! warning
    The following steps must be performed with root permissions.

### NGINX

[NGINX](https://www.nginx.com/resources/wiki/) is a free, open source, high-performance HTTP server and reverse proxy.

#### Install NGINX

Begin by installing NGINX:

=== "Ubuntu/Debian"

    ```no-highlight title="Install NGINX"
    sudo apt install -y nginx
    ```

=== "Fedora/RHEL"

    ```no-highlight title="Install NGINX"
    sudo dnf install -y nginx
    ```

#### Configure NGINX

!!! note
    If the file location of SSL certificates had to be changed in the [Obtain an SSL Certificate](#obtain-an-ssl-certificate) step above, then the location will need to be changed in the NGINX configuration below.

=== "Ubuntu/Debian"
    Once NGINX is installed, copy and paste the following NGINX configuration into `/etc/nginx/sites-available/nautobot.conf`:

    === "Vim"

        ```no-highlight title="Edit NGINX config with Vim"
        sudo vim /etc/nginx/sites-available/nautobot.conf
        ```

    === "Nano"

        ```no-highlight title="Edit NGINX config with Nano"
        sudo nano /etc/nginx/sites-available/nautobot.conf
        ```

    ```nginxconf title="/etc/nginx/sites-available/nautobot.conf"
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

=== "Fedora/RHEL"
    Once NGINX is installed, copy and paste the following NGINX configuration for the Nautobot NGINX site.

    === "Vim"

        ```no-highlight title="Edit Nautobot site config with Vim"
        sudo vim /etc/nginx/conf.d/nautobot.conf
        ```

    === "Nano"

        ```no-highlight title="Edit Nautobot site config with Nano"
        sudo nano /etc/nginx/conf.d/nautobot.conf
        ```

    ```nginxconf title="/etc/nginx/conf.d/nautobot.conf"
    server {
        listen 443 ssl http2 default_server;
        listen [::]:443 ssl http2 default_server;

        server_name _;

        ssl_certificate /etc/pki/tls/certs/nautobot.crt;
        ssl_certificate_key /etc/pki/tls/private/nautobot.key;

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

=== "Ubuntu/Debian"

    To enable the Nautobot site, you'll need to delete `/etc/nginx/sites-enabled/default` and create a symbolic link in the
    `sites-enabled` directory to the configuration file you just created:

    ```no-highlight title="Link Nautobot NGINX site config"
    sudo rm -f /etc/nginx/sites-enabled/default
    sudo ln -s /etc/nginx/sites-available/nautobot.conf /etc/nginx/sites-enabled/nautobot.conf
    ```

=== "Fedora/RHEL"

    Run the following command to disable the default site that comes with the `nginx` package:

    ```no-highlight title="Link Nautobot NGINX site config"
    sudo sed -i 's@ default_server@@' /etc/nginx/nginx.conf
    ```

#### Add NGINX User Account to Nautobot Group

The NGINX service needs to be able to read the files in `/opt/nautobot/static/` (CSS files, fonts, etc.) to serve them to users. There are various ways this could be accomplished (including changing the `STATIC_ROOT` configuration in Nautobot to a different location then re-running `nautobot-server collectstatic`), but we'll go with the simple approach of adding the appropriate user to the `nautobot` user group and opening `$NAUTOBOT_ROOT` to be readable by members of that group.

=== "Ubuntu/Debian"

    The NGINX user is usually `www-data`. To add the user, you'll need to use `usermod` like this:

    ```no-highlight title="Add www-data user to nautobot group"
    sudo usermod -aG nautobot www-data
    ```

=== "Fedora/RHEL"

    The NGINX user is usually `nginx`. To add the user, you'll need to use `usermod` like this:

    ```no-highlight title="Add nginx user to nautobot group"
    sudo usermod -aG nautobot nginx
    ```

!!! info
    If the `usermod` command fails with a `does not exist` error, check what user NGINX is using by examining `/etc/nginx/nginx.conf`.

#### Set Permissions for `NAUTOBOT_ROOT`

Ensure that the `NAUTOBOT_ROOT` permissions are set to `750`, allowing other members of the `nautobot` user group (including the `nginx` account) to read and execute files in this directory:

```no-highlight title="Update access permissions to 750 for $NAUTOBOT_ROOT"
chmod 750 $NAUTOBOT_ROOT
```

#### Restart NGINX

Finally, restart the `nginx` service to use the new configuration.

```no-highlight title="Restart NGINX"
sudo systemctl restart nginx
```

!!! info
    If the restart fails, and you changed the default key location, check to make sure the `nautobot.conf` file you pasted has the updated key location. For example, CentOS requires keys to be in `/etc/pki/tls/` instead of `/etc/ssl/`.

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
- Confirm that a firewall isn't obstructing access to NGINX. Connect from the server itself as a first check. If blocked, consider verifying firewall settings (e.g., `sudo ufw status` or `sudo firewall-cmd --list-all`).
- Additionally, if SELinux is enabled, ensure that it's not restricting NGINX’s operations. You might need to adjust SELinux policies or set the right context for NGINX files and processes.

This addition brings attention to SELinux, which is especially pertinent in environments like CentOS or RHEL, where SELinux is often enabled by default and could be a non-obvious blocker to NGINX operations.

### Static Media Failure

If you get a *Static Media Failure; The following static media file failed to load: css/base.css*, verify that the permissions on the `$NAUTOBOT_ROOT` directory are correctly set and that the `nginx` account is a member of the `nautobot` group, as described above.

### 502 Bad Gateway

If you are able to connect but receive a 502 (bad gateway) error, check the following:

- The uWSGI worker processes are running (`systemctl status nautobot` should show a status of `active (running)`)
- NGINX is configured to connect to the port on which uWSGI is listening (default is `8001`).
- SELinux may be preventing the reverse proxy connection. You may need to allow HTTP network connections with the command `setsebool -P httpd_can_network_connect 1`. For further information, view the [SELinux troubleshooting](../guides/selinux-troubleshooting.md) guide.
