<h1>Getting Started</h1>

This guide documents the process of installing NetBox on an Ubuntu 14.04 server with [nginx](https://www.nginx.com/) and [gunicorn](http://gunicorn.org/).

[TOC]

# PostgreSQL

## Installation

The following packages are needed to install PostgreSQL:

* postgresql
* libpq-dev
* python-psycopg2

```
# apt-get install postgresql libpq-dev python-psycopg2
```

## Configuration

At a minimum, we need to create a database for NetBox and assign it a username and password for authentication. This is done with the following commands.

DO NOT USE THE PASSWORD FROM THE EXAMPLE.

```
# sudo -u postgres psql
psql (9.3.13)
Type "help" for help.

postgres=# CREATE DATABASE netbox;
CREATE DATABASE
postgres=# CREATE USER netbox WITH PASSWORD 'J5brHrAXFLQSif0K';
CREATE ROLE
postgres=# GRANT ALL PRIVILEGES ON DATABASE netbox TO netbox;
GRANT
postgres=# \q
```

You can verify that authentication works using the following command:

```
# psql -U netbox -h localhost -W
```

---

# NetBox

## Dependencies

* python2.7
* python-dev
* git
* python-pip
* libxml2-dev
* libxslt1-dev
* libffi-dev

```
# apt-get install python2.7 python-dev git python-pip libxml2-dev libxslt1-dev libffi-dev
```

## Clone the Git Repository

Create the base directory for the NetBox installation. For this guide, we'll use `/opt/netbox`.

```
# mkdir -p /opt/netbox/
# cd /opt/netbox/
```

Next, clone the NetBox git repository into the current directory:

```
# git clone https://github.com/digitalocean/netbox.git .
Cloning into '.'...
remote: Counting objects: 1994, done.
remote: Compressing objects: 100% (150/150), done.
remote: Total 1994 (delta 80), reused 0 (delta 0), pack-reused 1842
Receiving objects: 100% (1994/1994), 472.36 KiB | 0 bytes/s, done.
Resolving deltas: 100% (1495/1495), done.
Checking connectivity... done.
```

Install the necessary Python packages using pip. (If you encounter any compilation errors during this step, ensure that you've installed all of the required dependencies.)

```
# pip install -r requirements.txt
```

## Configuration

Move into the NetBox configuration directory and make a copy of `configuration.example.py` named `configuration.py`.

```
# cd netbox/netbox/
# cp configuration.example.py configuration.py
```

Open `configuration.py` with your preferred editor and set the following variables:
 
* ALLOWED_HOSTS
* DATABASE
* SECRET_KEY

### ALLOWED_HOSTS

This is a list of the valid hostnames by which this server can be reached. You must specify at least one name or IP address.

Example:

```
ALLOWED_HOSTS = ['netbox.example.com', '192.0.2.123']
```

### DATABASE

This parameter holds the database configuration details. You must define the username and password used when you configured PostgreSQL. If the service is running on a remote host, replace `localhost` with its address.

Example:

```
DATABASE = {
    'NAME': 'netbox',               # Database name
    'USER': 'netbox',               # PostgreSQL username
    'PASSWORD': 'J5brHrAXFLQSif0K', # PostgreSQL password
    'HOST': 'localhost',            # Database server
    'PORT': '',                     # Database port (leave blank for default)
}
```

### SECRET_KEY

Generate a random secret key of at least 50 alphanumeric characters. This key must be unique to this installation and must not be shared outside the local system.

Example:

```
SECRET_KEY = '^6-ub1!t@ty5tomzkp6-ag0_y$kckdk2lmbx2$ya2r+ikk5&#d'
```

DO NOT COPY AND PASTE THE KEY FROM THE EXAMPLE.

## Run Migrations

Before NetBox can run, we need to install the database schema. This is done by running `./manage.py migrate` from the `netbox` directory (`/opt/netbox/netbox/` in our example):

```
# ./manage.py migrate
Operations to perform:
  Apply all migrations: dcim, sessions, admin, ipam, utilities, auth, circuits, contenttypes, extras, secrets, users
Running migrations:
  Rendering model states... DONE
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
  ...
```

If this step results in a PostgreSQL authentication error, ensure that the username and password created in the database match what has been specified in `configuration.py`

## Create a Super User

NetBox does not come with any predefined user accounts. You'll need to create a super user to be able to log into NetBox:

```
# ./manage.py createsuperuser
Username: admin
Email address: admin@example.com
Password: 
Password (again): 
Superuser created successfully.
```

## Collect Static Files

```
# ./manage.py collectstatic

You have requested to collect static files at the destination
location as specified in your settings:

    /opt/netbox/netbox/static

This will overwrite existing files!
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: yes
```

## Test the Application

At this point, NetBox should be able to run. We can verify this by starting a development instance:

```
# ./manage.py runserver 0.0.0.0:8000 --insecure
Performing system checks...

System check identified no issues (0 silenced).
June 17, 2016 - 16:17:36
Django version 1.9.7, using settings 'netbox.settings'
Starting development server at http://0.0.0.0:8000/
Quit the server with CONTROL-C.
```

Now if we navigate to the name or IP of the server (as defined in `ALLOWED_HOSTS`) we should be greeted with the NetBox home page. Note that this built-in web service is for development and testing purposes only. It is not suited for production use.

If the test service does not run, or you cannot reach the NetBox home page, something has gone wrong. Do not proceed with the rest of this guide until the installation has been corrected.

---

TODO
