# HTTP Server Setup

!!! warning
    As of Nautobot v1.0.0b1 these instructions are in a pre-release state and will be evolving rapidly!

This documentation provides example configurations for both [nginx](https://www.nginx.com/resources/wiki/) and [Apache](https://httpd.apache.org/docs/current/), though any HTTP server which supports WSGI should be compatible.

!!! info
    For the sake of brevity, only Ubuntu 20.04 instructions are provided here. These tasks are not unique to Nautobot and should carry over to other distributions with minimal changes. Please consult your distribution's documentation for assistance if needed.

## Obtain an SSL Certificate

To enable HTTPS access to Nautobot, you'll need a valid SSL certificate. You can purchase one from a trusted commercial provider, obtain one for free from [Let's Encrypt](https://letsencrypt.org/getting-started/), or generate your own (although self-signed certificates are generally untrusted). Both the public certificate and private key files need to be installed on your Nautobot server in a location that is readable by the `nautobot` user.

The command below can be used to generate a self-signed certificate for testing purposes, however it is strongly recommended to use a certificate from a trusted authority in production. Two files will be created: the public certificate (`nautobot.crt`) and the private key (`nautobot.key`). The certificate is published to the world, whereas the private key must be kept secret at all times.

!!! info
    Some Linux installations have changed the location for ssl certificates from `/etc/ssl/` to `/etc/pki/tli/`. The command below may need to be changed to reflect the certificate location.

```no-highlight
sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
-keyout /etc/ssl/private/nautobot.key \
-out /etc/ssl/certs/nautobot.crt
```

The above command will prompt you for additional details of the certificate; all of these are optional.

## HTTP Server Installation

### Option A: nginx

Begin by installing nginx:

```no-highlight
sudo apt install -y nginx
```

Once nginx is installed, copy the nginx configuration file provided by Nautobot to `/etc/nginx/sites-available/nautobot.conf`. Be sure to replace `nautobot.example.com` with the domain name or IP address of your installation. (This should match the value configured for `ALLOWED_HOSTS` in `nautobot_config.py`.)

If the location of ssl certificates had to be changed in `Obtain an SSL Certificate` step, then the location will need to be changed in the `nginx.conf` file as well.

!!! info
    Redhat based systems running nginx will need to create the directory structure and update the default `nginx.conf` file. To do this, create the `sites-available` and `sites-enabled` directories.

    ```no-highlight
    mkdir -p /etc/nginx/{sites-available,sites-enabled}
    ```

    Edit the `/etc/nginx.conf` file. In the `http` section, add:

    ```no-highlight
    include /etc/nginx/sites-enabled/*.conf;
    server_names_hash_bucket_size 64;
    ```

```no-highlight
sudo cp /opt/nautobot/contrib/nginx.conf /etc/nginx/sites-available/nautobot.conf
```

Then, delete `/etc/nginx/sites-enabled/default` and create a symlink in the `sites-enabled` directory to the configuration file you just created.

```no-highlight
sudo rm /etc/nginx/sites-enabled/default
sudo ln -s /etc/nginx/sites-available/nautobot.conf /etc/nginx/sites-enabled/nautobot.conf
```

Finally, restart the `nginx` service to use the new configuration.

```no-highlight
sudo systemctl restart nginx
```

### Option B: Apache

Begin by installing Apache:

```no-highlight
sudo apt install -y apache2
```

Next, copy the default configuration file to `/etc/apache2/sites-available/`. Be sure to modify the `ServerName` parameter appropriately.

If the location of ssl certificates had to be changed in `Obtain an SSL Certificate` step, then the location will need to be changed in the `apache.conf` file as well.

```no-highlight
sudo cp /opt/nautobot/contrib/apache.conf /etc/apache2/sites-available/nautobot.conf
```

Finally, ensure that the required Apache modules are enabled, enable the `nautobot` site, and reload Apache:

```no-highlight
sudo a2enmod ssl proxy proxy_http headers
sudo a2ensite nautobot
sudo systemctl restart apache2
```

## Confirm Connectivity

At this point, you should be able to connect to the HTTPS service at the server name or IP address you provided.

!!! info
    Please keep in mind that the configurations provided here are bare minimums required to get Nautobot up and running. You may want to make adjustments to better suit your production environment.

!!! warning
    Certain components of Nautobot (such as the display of rack elevation diagrams) rely on the use of embedded objects. Ensure that your HTTP server configuration does not override the `X-Frame-Options` response header set by Nautobot.

## Troubleshooting

If you are unable to connect to the HTTP server, check that:

* Nginx/Apache is running and configured to listen on the correct port.
* Access is not being blocked by a firewall somewhere along the path. (Try connecting locally from the server itself.)

If you are able to connect but receive a 502 (bad gateway) error, check the following:

* The WSGI worker processes (gunicorn) are running (`systemctl status nautobot` should show a status of "active (running)")
* Nginx/Apache is configured to connect to the port on which gunicorn is listening (default is 8001).
* SELinux is not preventing the reverse proxy connection. You may need to allow HTTP network connections with the command `setsebool -P httpd_can_network_connect 1`
