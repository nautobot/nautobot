# Installing Nautobot System Dependencies

The documentation assumes that you are running one of the following:

- Ubuntu 20.04+
- Debian 11+
- Fedora, RHEL/CentOS 8.2+ and derivatives
    - Delimited by `Fedora/RHEL` tabs in the docs, but also includes other derivatives of RHEL such as RockyLinux or AlmaLinux

## Install System Packages

Install the prerequisite system libraries and utilities.

This will install:

- Git
- Python 3
- Pip
- Redis server and client

=== "Ubuntu/Debian"

    ```bash title="Install system dependencies"
    sudo apt update -y
    sudo apt install -y git python3 python3-pip python3-venv python3-dev redis-server
    ```

=== "Fedora/RHEL"

    ```bash title="Install system dependencies"
    sudo dnf check-update
    sudo dnf install -y git python3 python3-devel python3-pip redis
    ```

## Database Setup

In this step you'll set up your database server, create a database and database user for use by Nautobot, and verify your connection to the database.

You must select either MySQL (MariaDB is **not** supported) or PostgreSQL. PostgreSQL is used by default with Nautobot, so if you just want to get started or don't have a preference, please stick with PostgreSQL.

Please follow the steps for your selected database backend below.

<!--
We intentionally use explicit <h3> tags inside the tabbed block below rather than ### markdown.
This is done so that these subheads don't get included in the page table of contents, where it would be confusing
to have multiple "Install PostgreSQL", "Create a PostgreSQL Database", etc. entries.
-->

=== "Ubuntu/Debian"

    === "PostgreSQL"

        <h3>Install PostgreSQL</h3>

        This will install the PostgreSQL database server and client.

        ```no-highlight title="Install Postgres"
        sudo apt install -y postgresql
        ```

        <h3>Create a PostgreSQL Database</h3>

        At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This is done with the following commands.

        !!! danger
            **Do not use the password from the example.** Choose a strong, random password to ensure secure database authentication for your Nautobot installation.

        ```no-highlight title="Enter into Postgres"
        sudo -u postgres psql
        ```

        ??? example "Example of Entering Postgres"

            ```no-highlight title="Entering Postgres DB"
            psql (16.3 (Ubuntu 16.3-0ubuntu0.24.04.1))
            Type "help" for help.

            postgres=#
            ```

        ```no-highlight title="Create the Nautobot DB"
        CREATE DATABASE nautobot;
        CREATE USER nautobot WITH PASSWORD 'insecure_password';
        GRANT ALL PRIVILEGES ON DATABASE nautobot TO nautobot;
        \connect nautobot
        GRANT CREATE ON SCHEMA public TO nautobot;
        \q
        ```

        ??? example "Example Postgres DB Creation Output"
            ```no-highlight title="Example output of creating the DB"
            postgres=# CREATE DATABASE nautobot;
            CREATE DATABASE
            postgres=# CREATE USER nautobot WITH PASSWORD 'insecure_password';
            CREATE ROLE
            postgres=# GRANT ALL PRIVILEGES ON DATABASE nautobot TO nautobot;
            GRANT
            postgres=# \connect nautobot
            You are now connected to database "nautobot" as user "postgres".
            nautobot=# GRANT CREATE ON SCHEMA public TO nautobot;
            GRANT
            nautobot=# \q
            ```

        <h3>Verify PostgreSQL Service Status</h3>

        You can verify that authentication works issuing the following command and providing the configured password. (Replace `localhost` with your database server if using a remote database.)

        If successful, you will enter a `nautobot` prompt. Type `\conninfo` to confirm your connection, or type `\q` to exit.

        ```no-highlight title="Connect to the Nautobot DB"
        psql --username nautobot --password --host localhost nautobot
        ```

        ??? example "Example Postgres Connection Output"

            ```no-highlight title="Example output"
            Password for user nautobot:
            psql (16.3 (Ubuntu 16.3-0ubuntu0.24.04.1))
            SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off)
            Type "help" for help.

            nautobot=> \conninfo
            You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "::1") at port "5432".
            SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, compression: off)
            nautobot=> \q
            ```

    === "MySQL"

        <h3>Install MySQL</h3>

        This will install the MySQL database server and client. Additionally, MySQL requires that the MySQL development libraries and the `pkg-config` package are both installed so that we may compile the Python `mysqlclient` library during the Nautobot installation steps.

        ```no-highlight title="Install MySQL required packages"
        sudo apt install -y libmysqlclient-dev mysql-server pkg-config
        ```

        <h3>Create a MySQL Database</h3>

        At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This is done with the following commands.

        !!! note
            Replace `localhost` below with your database server if using a remote database.

        !!! danger
            **Do not use the password from the example.** Choose a strong, random password to ensure secure database authentication for your Nautobot installation.

        ```no-highlight title="Connect to MySQL"
        sudo -u root mysql
        ```

        ```no-highlight title="Create the Nautobot DB"
        CREATE DATABASE nautobot;
        CREATE USER 'nautobot'@'localhost' IDENTIFIED BY 'insecure_password';
        GRANT ALL ON nautobot.* TO 'nautobot'@'localhost';
        \q
        ```

        ??? example "Example MySQL output"

            ```no-highlight title="Example MySQL DB creation output."
            Welcome to the MySQL monitor.  Commands end with ; or \g.
            Your MySQL connection id is 11
            Server version: 8.0.37-0ubuntu0.24.04.1 (Ubuntu)

            Copyright (c) 2000, 2024, Oracle and/or its affiliates.

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

        <h3>Verify MySQL Service Status</h3>

        You can verify that authentication works issuing the following command and providing the configured password.

        If successful, you will enter a `mysql>` prompt. Type `status` to confirm your connection, or type `\q` to exit.

        !!! note
            Replace `localhost` below with your database server if using a remote database.

        ```no-highlight title="Test the MySQL DB connection"
        mysql --user nautobot --password --host localhost nautobot
        ```

        Then after the password prompt you can use `status` and `\q` commands

        ``` no title="Check the status and quit"
        status
        \q
        ```

        ??? example "Example Verification of MySQL database"

            ```no-highlight title="Example test output"
            Enter password:
            Welcome to the MySQL monitor.  Commands end with ; or \g.
            Your MySQL connection id is 13
            Server version: 8.0.37-0ubuntu0.24.04.1 (Ubuntu)

            Copyright (c) 2000, 2024, Oracle and/or its affiliates.

            Oracle is a registered trademark of Oracle Corporation and/or its
            affiliates. Other names may be trademarks of their respective
            owners.

            Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

            mysql> status
            --------------
            mysql  Ver 8.0.37-0ubuntu0.24.04.1 for Linux on x86_64 ((Ubuntu))

            Connection id:          13
            Current database:       nautobot
            Current user:           nautobot@localhost
            SSL:                    Not in use
            Current pager:          stdout
            Using outfile:          ''
            Using delimiter:        ;
            Server version:         8.0.37-0ubuntu0.24.04.1 (Ubuntu)
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

=== "Fedora/RHEL"

    === "PostgreSQL"

        <h3>Install PostgreSQL</h3>

        This will install the PostgreSQL database server and client.

        ```no-highlight title="Install Postgres"
        sudo dnf install -y postgresql-server
        ```

        <h3>Initialize PostgreSQL</h3>

        Fedora/RHEL and related distros typically require a manual step to generate the initial configurations required by PostgreSQL.

        ```no-highlight title="Setup initial required configurations"
        sudo postgresql-setup --initdb
        ```

        <h3>Configure Authentication</h3>

        Fedora/RHEL and related distros typically configure PostgreSQL to use [`ident`](https://www.postgresql.org/docs/current/auth-ident.html) host-based authentication by default. Because Nautobot will need to authenticate using a username and password, we must update `pg_hba.conf` to support [`md5` password](https://www.postgresql.org/docs/current/auth-password.html) authentication.

        !!! tip
            Under many distros, you may be able to use the more secure `scram-sha-256` as an alternative to `md5`, but this option may not be available by default; enabling it is beyond the scope of this documentation.

        As root, edit `/var/lib/pgsql/data/pg_hba.conf` and change `ident` to `md5` for the lines below.

        Before:

        ```no-highlight title="Before /var/lib/pgsql/data/pg_hba.conf"
        # IPv4 local connections:
        host    all             all             127.0.0.1/32            ident
        # IPv6 local connections:
        host    all             all             ::1/128                 ident
        ```

        After:

        ```no-highlight title="After /var/lib/pgsql/data/pg_hba.conf"
        # IPv4 local connections:
        host    all             all             127.0.0.1/32            md5
        # IPv6 local connections:
        host    all             all             ::1/128                 md5
        ```

        <h3>Start PostgreSQL</h3>

        Start the service and enable it to run at system startup:

        ```no-highlight title="Start and enable the Postgres service at start up"
        sudo systemctl enable --now postgresql
        ```

        <h3>Create a PostgreSQL Database</h3>

        At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This
        is done with the following commands.

        !!! danger
            **Do not use the password from the example.** Choose a strong, random password to ensure secure database authentication for your Nautobot installation.

        ```no-highlight title="Enter into Postgres"
        sudo -u postgres psql
        ```

        Create the database and grant permissions to the Nautobot user.

        ```no-highlight title="Create Nautobot DB"
        CREATE DATABASE nautobot;
        CREATE USER nautobot WITH PASSWORD 'insecure_password';
        GRANT ALL PRIVILEGES ON DATABASE nautobot TO nautobot;
        \connect nautobot
        GRANT CREATE ON SCHEMA public TO nautobot;
        \q
        ```

        ??? example "Example Database creation output."

            ```no-highlight title="Example DB creation output"
            postgres=# CREATE DATABASE nautobot;
            CREATE DATABASE
            postgres=# CREATE USER nautobot WITH PASSWORD 'insecure_password';
            CREATE ROLE
            postgres=# GRANT ALL PRIVILEGES ON DATABASE nautobot TO nautobot;
            GRANT
            postgres=# \connect nautobot
            You are now connected to database "nautobot" as user "postgres".
            nautobot=# GRANT CREATE ON SCHEMA public TO nautobot;
            GRANT
            nautobot=# \q
            ```

        <h3>Verify PostgreSQL Service Status</h3>

        You can verify that authentication works issuing the following command and providing the configured password. (Replace `localhost` with your database server if using a remote database.)

        If successful, you will enter a `nautobot` prompt. Type `\conninfo` to confirm your connection, or type `\q` to exit.

        ```no-highlight title="Test connection to Nautobot DB"
        psql --username nautobot --password --host localhost nautobot
        ```

        ??? example "Example Verification Output"

            ```no-highlight
            Password for user nautobot:
            psql (16.3)
            Type "help" for help.

            nautobot=> \conninfo
            You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "::1") at port "5432".
            nautobot=> \q
            ```

    === "MySQL"

        <h3>Install MySQL</h3>

        This will install the MySQL database server and client. Additionally, MySQL requires that `gcc` and the MySQL development libraries are installed so that we may compile the Python `mysqlclient` library during the Nautobot installation steps.

        ```no-highlight title="Install MySQL packages"
        sudo dnf install -y gcc mysql-server mysql-devel
        ```

        !!! tip
            If you get an error about `Unable to find a match: mysql-devel`, you may need to enable additional sources for packages. On at least CentOS 9 and AlmaLinux 9, the command `sudo dnf config-manager --set-enabled crb` is the way to enable the necessary repository.

        <h3>Start MySQL</h3>

        Start the service and enable it to run at system startup:

        ```no-highlight title="Start and enable at start up of the MySQL service"
        sudo systemctl enable --now mysql
        ```

        !!! tip
            Depending on your Linux distribution, the service may be named `mysqld` instead of `mysql`. If you get an error with the above command, try `sudo systemctl enable --now mysqld` instead.

        <h3>Create a MySQL Database</h3>

        At a minimum, we need to create a database for Nautobot and assign it a username and password for authentication. This is done with the following commands.

        !!! note
            Replace `localhost` below with your database server if using a remote database.

        !!! danger
            **Do not use the password from the example.** Choose a strong, random password to ensure secure database authentication for your Nautobot installation.

        ```no-highlight title="Connect to MySQL"
        sudo -u root mysql
        ```

        ```no-highlight title="Create Nautobot DB"
        CREATE DATABASE nautobot;
        CREATE USER 'nautobot'@'localhost' IDENTIFIED BY 'insecure_password';
        GRANT ALL ON nautobot.* TO 'nautobot'@'localhost';
        \q
        ```

        ??? example "Example Creation of MySQL DB"

            ```no-highlight title="Example output creation of DB"
            Welcome to the MySQL monitor.  Commands end with ; or \g.
            Your MySQL connection id is 8
            Server version: 8.0.37 Source distribution

            Copyright (c) 2000, 2024, Oracle and/or its affiliates. All rights reserved.

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

        <h3>Verify MySQL Service Status</h3>

        You can verify that authentication works issuing the following command and providing the configured password.

        If successful, you will enter a `mysql>` prompt. Type `status` to confirm your connection, or type `\q` to exit.

        !!! note
            Replace `localhost` below with your database server if using a remote database.

        ```no-highlight
        mysql --user nautobot --password --host localhost nautobot
        ```

        ??? example "Example MySQL Verification"

            ```no-highlight
            Enter password:
            Welcome to the MySQL monitor.  Commands end with ; or \g.
            Your MySQL connection id is 10
            Server version: 8.0.37 Source distribution

            Copyright (c) 2000, 2024, Oracle and/or its affiliates. All rights reserved.

            Oracle is a registered trademark of Oracle Corporation and/or its
            affiliates. Other names may be trademarks of their respective
            owners.

            Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

            mysql> status
            --------------
            mysql  Ver 8.0.37 for Linux on x86_64 (Source distribution)

            Connection id:          10
            Current database:       nautobot
            Current user:           nautobot@localhost
            SSL:                    Not in use
            Current pager:          stdout
            Using outfile:          ''
            Using delimiter:        ;
            Server version:         8.0.37 Source distribution
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

### Troubleshooting

<!-- pyml disable-next-line no-inline-html,proper-names -->
<h4>django.db.utils.NotSupportedError: conversion between UTF8 and SQL_ASCII is not supported</h4>

Django requires the database encoding for PostgreSQL databases to be set to UTF-8. If you receive the error `django.db.utils.NotSupportedError: conversion between UTF8 and SQL_ASCII is not supported`, you will need to drop and re-create the `nautobot` database with the correct encoding.

## Redis Setup

=== "Ubuntu/Debian"

    Since Redis was already installed, let's just verify that it's working using `redis-cli`:

    ```no-highlight title="Test Redis connection"
    redis-cli ping
    ```

    ??? example "Example Redis check output"

        ```no-highlight title="redis-cli ping output"
        PONG
        ```

=== "Fedora/RHEL"

    <h3>Start Redis</h3>

    Start the service and enable it to run at system startup:

    ```no-highlight title="Enable Redis to start on boot and start Redis now"
    sudo systemctl enable --now redis
    ```

    <h3>Verify Redis Service Status</h3>

    Use the `redis-cli` utility to ensure the Redis service is functional:

    ```no-highlight title="Test Redis connection"
    redis-cli ping
    ```

    ??? example "Example Redis check output"

        ```no-highlight
        PONG
        ```

## Deploy Nautobot

Now that Nautobot dependencies are installed and configured, you're ready to [Install Nautobot](nautobot.md)!
