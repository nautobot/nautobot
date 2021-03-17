# Installing Nautobot Dependencies on CentOS/RHEL

This installation guide assumes that you are running CentOS or RHEL version 8.2+ on your system.

## Install System Packages

Install the prerequisite system libraries and utilities.

This will install:

- Git
- Python 3
- Pip
- PostgreSQL database server and client
- Redis server and client

```no-highlight
$ sudo yum check-update
$ sudo yum install -y git python38 python38-devel python38-pip postgresql-server redis
```

## Database Setup

In this step you'll setup PostgreSQL, create a database and database user for use by Nautobot, and verify your
connection to the database.

### Initialize Postgres

CentOS/RHEL requires a manual step to generate the initial configurations required by PostgreSQL.

```no-highlight
$ sudo postgresql-setup --initdb
```

### Configure Authentication

CentOS/RHEL configures PostgreSQL to use [`ident`](https://www.postgresql.org/docs/current/auth-ident.html) host-based authentication by default. Because Nautobot will need to authenticate using a username and password, we must update `pg_hba.conf` to support [`md5` password](https://www.postgresql.org/docs/current/auth-password.html) authentication.

As root, edit `/var/lib/pgsql/data/pg_hba.conf` and change `ident` to `md5` for the lines below.

Before: 
```no-highlight
# IPv4 local connections:
host    all             all             127.0.0.1/32            ident
# IPv6 local connections:
host    all             all             ::1/128                 ident
```

After:
```no-highlight
# IPv4 local connections:
host    all             all             127.0.0.1/32            md5
# IPv6 local connections:
host    all             all             ::1/128                 md5
```

### Start PostgreSQL

Start the service and enable it to run at system startup:

```no-highlight
$ sudo systemctl enable --now postgresql
```

### Create a Database

At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This
is done with the following commands.

!!! danger
    **Do not use the password from the example.** Choose a strong, random password to ensure secure database
    authentication for your Nautobot installation.

```no-highlight
$ sudo -u postgres psql
psql (10.15)
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
psql (10.15)
Type "help" for help.

nautobot=> \conninfo
You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "127.0.0.1") at port "5432".
nautobot=> \q
```

## Redis Setup

### Start Redis

Start the service and enable it to run at system startup:

```no-highlight
$ sudo systemctl enable --now redis
```

### Verify Service Status

Use the `redis-cli` utility to ensure the Redis service is functional:

```no-highlight
$ redis-cli ping
PONG
```

## Deploy Nautobot

Now that Nautobot dependencies are installed and configured, you're ready to [Install Nautobot](../nautobot)!
