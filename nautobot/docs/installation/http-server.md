# Configuring an HTTP Server

!!! warning
    As of Nautobot v1.0.0b2 these instructions are in a pre-release state and will be evolving rapidly!

This documentation provides example configurations for both [NGINX](https://www.nginx.com/resources/wiki/) and
[Apache](https://httpd.apache.org/docs/current/), though any HTTP server which supports WSGI should be compatible.

## Obtain an SSL Certificate

To enable HTTPS access to Nautobot, you'll need a valid SSL certificate. You can purchase one from a trusted commercial
provider, obtain one for free from [Let's Encrypt](https://letsencrypt.org/getting-started/), or generate your own
(although self-signed certificates are generally untrusted). Both the public certificate and private key files need to
be installed on your Nautobot server in a secure location that is readable only by the `root` user.

!!! warning
    The command below can be used to generate a self-signed certificate for testing purposes,
    however it is strongly recommended to use a certificate from a trusted authority in production.

Two files will be created: the public certificate (`nautobot.crt`) and the private key (`nautobot.key`). The certificate is published to the world, whereas the private key must be kept secret at all times.

!!! info
    Some Linux installations have changed the location for SSL certificates from `/etc/ssl/` to `/etc/pki/tls/`. The
    command below may need to be changed to reflect the certificate location.

    The following command will prompt you for additional details of the certificate; all of which are optional.

```no-highlight
$ sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/nautobot.key \
  -out /etc/ssl/certs/nautobot.crt
```

## HTTP Server Installation

Any HTTP server of your choosing is supported. For your convenience, setup guides for the most common options are
provided here.

!!! warning
    The following steps must be performed with root permissions.

### NGINX

[NGINX](https://www.nginx.com/resources/wiki/) is a free, open source, high-performance HTTP server and reverse proxy
and is by far the most popular choice.

#### Install NGINX

Begin by installing NGINX:

```no-highlight
$ sudo apt install -y nginx
```

#### Configure NGINX

Once NGINX is installed, copy and paste the following NGINX configuration into
`/etc/nginx/sites-available/nautobot.conf` for Ubuntu or `/etc/nginx/conf.d/nautobot.conf` for CentOS/RHEL: 

```
server {
    listen 443 ssl;

    # CHANGE THIS TO YOUR SERVER'S NAME
    server_name nautobot.example.com;

    ssl_certificate /etc/ssl/certs/nautobot.crt;
    ssl_certificate_key /etc/ssl/private/nautobot.key;

    client_max_body_size 25m;

    location /static/ {
        alias /opt/nautobot/static/;
    }

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    # Redirect HTTP traffic to HTTPS
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
```

- Be sure to replace `nautobot.example.com` with the domain name or IP address of your installation. This should match
the value configured for `ALLOWED_HOSTS` in `nautobot_config.py`.
- If the file location of SSL certificates had to be changed in the [Obtain an SSL
  Certificate](#obtain-an-ssl-certificate) step above, then the location will need to be changed in the NGINX
  configuration you pasted.

#### Enable Nautobot

!!! note
    If you are installing on CentOS/RHEL, please continue to [Restart NGINX](#restart-nginx) step below.

To enable the Nautobot site, you'll need to delete `/etc/nginx/sites-enabled/default` and create a symbolic link in the
`sites-enabled` directory to the configuration file you just created:

```no-highlight
$ sudo rm -f /etc/nginx/sites-enabled/default
$ sudo ln -s /etc/nginx/sites-available/nautobot.conf /etc/nginx/sites-enabled/nautobot.conf
```

#### Restart NGINX

Finally, restart the `nginx` service to use the new configuration.

```no-highlight
$ sudo systemctl restart nginx
```

## Confirm Connectivity

At this point, you should be able to connect to the HTTPS service at the server name or IP address you provided.

!!! info
    Please keep in mind that the configurations provided here are bare minimums required to get Nautobot up and running. You may want to make adjustments to better suit your production environment.

!!! warning
    Certain components of Nautobot (such as the display of rack elevation diagrams) rely on the use of embedded objects. Ensure that your HTTP server configuration does not override the `X-Frame-Options` response header set by Nautobot.

## Troubleshooting

### Unable to Connect
If you are unable to connect to the HTTP server, check that:

- NGINX/Apache is running and configured to listen on the correct port.
- Access is not being blocked by a firewall somewhere along the path. (Try connecting locally from the server itself.)

### 502 Bad Gateway

If you are able to connect but receive a 502 (bad gateway) error, check the following:

- The uWSGI worker processes are running (`systemctl status nautobot` should show a status of `active (running)`)
- NGINX/Apache is configured to connect to the port on which uWSGI is listening (default is `8001`).
- SELinux may be preventing the reverse proxy connection. You may need to allow HTTP network connections with the
  command `setsebool -P httpd_can_network_connect 1`. For further information, view the [SELinux
  troubleshooting](selinux-troubleshooting.md) guide.
