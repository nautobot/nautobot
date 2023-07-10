# Installing Nautobot Dependencies on Ubuntu

This installation guide assumes that you are running Ubuntu version 20.04 on your system.

## Install System Packages

Install the prerequisite system libraries and utilities.

This will install:

- Git
- Python 3
- Pip
- Redis server and client

```no-highlight
sudo apt update -y
sudo apt install -y git python3 python3-pip python3-venv python3-dev redis-server
```

## Database Setup

In this step you'll set up your database server, create a database and database user for use by Nautobot, and verify your connection to the database.

You must select either MySQL or PostgreSQL. PostgreSQL is used by default with Nautobot, so if you just want to get started or don't have a preference, please stick with PostgreSQL.

Please follow the steps for your selected database backend below.

### PostgreSQL Setup

#### Install PostgreSQL

This will install the PostgreSQL database server and client.

```no-highlight
sudo apt install -y postgresql
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

#### Verify PostgreSQL Service Status

You can verify that authentication works issuing the following command and providing the configured password. (Replace `localhost` with your database server if using a remote database.)

If successful, you will enter a `nautobot` prompt. Type `\conninfo` to confirm your connection, or type `\q` to exit.

```no-highlight
psql --username nautobot --password --host localhost nautobot
```

Example output:

```no-highlight
Password for user nautobot:
psql (12.5 (Ubuntu 12.5-0ubuntu0.20.04.1))
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
Type "help" for help.

nautobot=> \conninfo
You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "127.0.0.1") at port "5432".
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
nautobot=> \q
```

### MySQL Setup

#### Install MySQL

This will install the MySQL database server and client. Additionally, MySQL requires that the MySQL development libraries are installed so that we may compile the Python `mysqlclient` library during the Nautobot installation steps.

```no-highlight
sudo apt install -y libmysqlclient-dev mysql-server
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
Your MySQL connection id is 11
Server version: 8.0.25-0ubuntu0.20.04.1 (Ubuntu)

Copyright (c) 2000, 2021, Oracle and/or its affiliates.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> CREATE DATABASE nautobot;
Query OK, 1 row affected (0.00 sec)

mysql> CREATE USER 'nautobot'@'localhost' IDENTIFIED BY 'insecure_password';
Query OK, 0 rows affected (0.01 sec)

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
Your MySQL connection id is 13
Server version: 8.0.25-0ubuntu0.20.04.1 (Ubuntu)

Copyright (c) 2000, 2021, Oracle and/or its affiliates.

Oracle is a registered trademark of Oracle Corporation and/or its
affiliates. Other names may be trademarks of their respective
owners.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

mysql> status
--------------
mysql  Ver 8.0.25-0ubuntu0.20.04.1 for Linux on x86_64 ((Ubuntu))

Connection id:          13
Current database:       nautobot
Current user:           nautobot@localhost
SSL:                    Not in use
Current pager:          stdout
Using outfile:          ''
Using delimiter:        ;
Server version:         8.0.25-0ubuntu0.20.04.1 (Ubuntu)
Protocol version:       10
Connection:             Localhost via UNIX socket
Server characterset:    utf8mb4
Db     characterset:    utf8mb4
Client characterset:    utf8mb4
Conn.  characterset:    utf8mb4
UNIX socket:            /var/run/mysqld/mysqld.sock
Binary data as:         Hexadecimal
Uptime:                 26 min 31 sec

Threads: 2  Questions: 29  Slow queries: 0  Opens: 193  Flush tables: 3  Open tables: 112  Queries per second avg: 0.018
--------------

mysql> \q
Bye
```

## Redis Setup

Since Redis was already installed, let's just verify that it's working using `redis-cli`:

```no-highlight
redis-cli ping
```

Example output:

```no-highlight
PONG
```

## Deploy Nautobot

Now that Nautobot dependencies are installed and configured, you're ready to [Install Nautobot](nautobot.md)!
