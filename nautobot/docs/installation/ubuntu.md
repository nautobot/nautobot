# Ubuntu

This installation guide assumes that you are running Ubuntu version 20.04 on your system.

## Install System Packages

Install the prerequisite system libraries and utilities.

This will install:

- Git
- Python 3
- Pip
- PostgreSQL database server and client
- Redis server and client

```
$ sudo apt update -y
$ sudo apt install -y git python3 python3-pip python3-venv python3-dev postgresql redis-server
```

## Database Setup

In this step you'll create a database and database user for use by Nautobot and verify your connection to the database.

### Create a Database

At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This
is done with the following commands.

!!! danger
    **Do not use the password from the example.** Choose a strong, random password to ensure secure database
    authentication for your Nautobot installation.

```no-highlight
$ sudo -u postgres psql
psql (12.5 (Ubuntu 12.5-0ubuntu0.20.04.1))
Type "help" for help.

postgres=# CREATE DATABASE nautobot;
CREATE DATABASE
postgres=# CREATE USER nautobot WITH PASSWORD 'insecure_password';
CREATE ROLE
postgres=# GRANT ALL PRIVILEGES ON DATABASE nautobot TO nautobot;
GRANT
postgres=# \q
```

## Verify Service Status

You can verify that authentication works issuing the following command and providing the configured password. (Replace `localhost` with your database server if using a remote database.)

If successful, you will enter a `nautobot` prompt. Type `\conninfo` to confirm your connection, or type `\q` to exit.

```no-highlight
$ psql --username nautobot --password --host localhost nautobot
Password for user nautobot:
psql (12.5 (Ubuntu 12.5-0ubuntu0.20.04.1))
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
Type "help" for help.

nautobot=> \conninfo
You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "127.0.0.1") at port "5432".
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
nautobot=> \q
```

## Redis Setup

Since Redis was already installed, let's just verify that it's working using `redis-cli`:

```
$ redis-cli ping
PONG
```

## Setup the Nautobot User Environment

### Create the Nautobot System User

Create a system user account named `nautobot`. We'll configure the WSGI and HTTP services to run under this account.
Later we will also change some files and directories to be owned by `nautobot`.

```no-highlight
$ sudo useradd --create-home --system --shell /bin/bash nautobot
```

{!docs/installation/pip-install.md!}
