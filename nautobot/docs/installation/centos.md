# Installing Nautobot Dependencies on CentOS/RHEL

This installation guide assumes that you are running CentOS or RHEL version 8.2+ on your system.

## Install System Packages

Install the prerequisite system libraries and utilities.

This will install:

- Git
- Python 3
- Pip
- Redis server and client

```no-highlight
sudo dnf check-update
sudo dnf install -y git python38 python38-devel python38-pip redis
```

## Database Setup

In this step you'll set up your database server, create a database and database user for use by Nautobot, and verify your connection to the database.

You must select either MySQL or PostgreSQL. PostgreSQL is used by default with Nautobot, so if you just want to get started or don't have a preference, please stick with PostgreSQL.

Please follow the steps for your selected database backend below.

### PostgreSQL Setup

#### Install PostgreSQL

This will install the PostgreSQL database server and client.

```no-highlight
sudo dnf install -y postgresql-server
```

#### Initialize PostgreSQL

CentOS/RHEL requires a manual step to generate the initial configurations required by PostgreSQL.

```no-highlight
sudo postgresql-setup --initdb
```

#### Configure Authentication

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

#### Start PostgreSQL

Start the service and enable it to run at system startup:

```no-highlight
sudo systemctl enable --now postgresql
```

#### Create a PostgreSQL Database

At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This
is done with the following commands.

!!! danger
    **Do not use the password from the example.** Choose a strong, random password to ensure secure database authentication for your Nautobot installation.

```no-highlight
sudo -u postgres psql
```

Example output:

```no-highlight
psql (10.15)
Type "help" for help.
```

```no-highlight
postgres=# CREATE DATABASE nautobot;
CREATE DATABASE
postgres=# CREATE USER nautobot WITH PASSWORD 'insecure_password';
CREATE ROLE
postgres=# GRANT ALL PRIVILEGES ON DATABASE nautobot TO nautobot;
GRANT
postgres=# \q
```

### Verify PostgreSQL Service Status

You can verify that authentication works issuing the following command and providing the configured password. (Replace `localhost` with your database server if using a remote database.)

If successful, you will enter a `nautobot` prompt. Type `\conninfo` to confirm your connection, or type `\q` to exit.

```no-highlight
psql --username nautobot --password --host localhost nautobot
```

Example output:

```no-highlight
Password for user nautobot:
psql (10.15)
Type "help" for help.

nautobot=> \conninfo
You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "127.0.0.1") at port "5432".
nautobot=> \q
```

### MySQL Setup

#### Install MySQL

This will install the MySQL database server and client. Additionally, MySQL requires that `gcc` and the MySQL development libraries are installed so that we may compile the Python `mysqlclient` library during the Nautobot installation steps.

```no-highlight
sudo dnf install -y gcc mysql-server mysql-devel
```

#### Start MySQL

Start the service and enable it to run at system startup:

```no-highlight
sudo systemctl enable --now mysql
```

#### Create a MySQL Database

At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This is done with the following commands.

!!! note
    Replace `localhost` below with your database server if using a remote database.

!!! danger
    **Do not use the password from the example.** Choose a strong, random password to ensure secure database authentication for your Nautobot installation.

```no-highlight
sudo -u root mysql
```

Example output:

```no-highlight
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 8
Server version: 8.0.21 Source distribution

Copyright (c) 2000, 2020, Oracle and/or its affiliates. All rights reserved.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> CREATE DATABASE nautobot;
Query OK, 1 row affected (0.00 sec)

mysql> CREATE USER 'nautobot'@'localhost' IDENTIFIED BY 'insecure_password';
Query OK, 0 rows affected (0.00 sec)

mysql> GRANT ALL ON nautobot.* TO 'nautobot'@'localhost';
Query OK, 0 rows affected (0.00 sec)

mysql> \q
Bye
```

#### Verify MySQL Service Status

You can verify that authentication works issuing the following command and providing the configured password.

If successful, you will enter a `mysql>` prompt. Type `status` to confirm your connection, or type `\q` to exit.

!!! note
    Replace `localhost` below with your database server if using a remote database.

```no-highlight
mysql --user nautobot --password --host localhost nautobot
```

Example output:

```no-highlight
Enter password:
Welcome to the MySQL monitor.  Commands end with ; or \g.
Your MySQL connection id is 10
Server version: 8.0.21 Source distribution

Copyright (c) 2000, 2020, Oracle and/or its affiliates. All rights reserved.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> status
--------------
mysql  Ver 8.0.21 for Linux on x86_64 (Source distribution)

Connection id:          10
Current database:       nautobot
Current user:           nautobot@localhost
SSL:                    Not in use
Current pager:          stdout
Using outfile:          ''
Using delimiter:        ;
Server version:         8.0.21 Source distribution
Protocol version:       10
Connection:             Localhost via UNIX socket
Server characterset:    utf8mb4
Db     characterset:    utf8mb4
Client characterset:    utf8mb4
Conn.  characterset:    utf8mb4
UNIX socket:            /var/lib/mysql/mysql.sock
Binary data as:         Hexadecimal
Uptime:                 4 min 12 sec

Threads: 2  Questions: 12  Slow queries: 0  Opens: 151  Flush tables: 3  Open tables: 69  Queries per second avg: 0.047
--------------

mysql> \q
Bye
```

## Redis Setup

### Start Redis

Start the service and enable it to run at system startup:

```no-highlight
sudo systemctl enable --now redis
```

### Verify Redis Service Status

Use the `redis-cli` utility to ensure the Redis service is functional:

```no-highlight
redis-cli ping
```

Example output:

```no-highlight
PONG
```

## Deploy Nautobot

Now that Nautobot dependencies are installed and configured, you're ready to [Install Nautobot](nautobot.md)!
