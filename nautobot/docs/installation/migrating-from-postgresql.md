# Migrating from PostgreSQL to MySQL

This document explains how to migrate the contents of an existing Nautobot PostgreSQL database to a new MySQL database.

## Export data from PostgreSQL

In your existing installation of Nautobot with PostgreSQL, run the following command to generate a JSON dump of the database contents. This may take several minutes to complete depending on the size of your database. From the Postgres host `(nautobot-postgres) $`:

```no-highlight
nautobot-server dumpdata \
    --natural-foreign \
    --natural-primary \
    --exclude contenttypes \
    --exclude auth.permission \
    --exclude django_rq \
    --format json \
    --indent 2 \
    --traceback \
    > nautobot_dump.json
```

This will result in a file named `nautobot_dump.json`.

## Create the MySQL database

Create the MySQL database for Nautobot, ensuring that it is utilizing the default character set (`utf8mb4`) and default collation (`utf8mb4_0900_ai_ci`) settings for case-insensitivity. It is required that MySQL will be case-insensitive. Because these encodings are the defaults, if your MySQL installation has not been modified, there will be nothing for you to do other than make sure.

In very rare cases, there may problems when importing your data from the case-sensitive PostgreSQL database dump that will need to be handled on a case-by-case basis. Please refer to the instructions for [CentOS/RHEL](./centos.md) or [Ubuntu](./ubuntu.md) as necessary if you are unsure how to set up MySQL and create the Nautobot database.

### Confirming database encoding

To confirm that your MySQL database has the correct encoding, you may start up a database shell using `nautobot-server dbshell` and run the following command with the prompt `(nautobot-mysql) $`

```no-highlight
nautobot-server dbshell
mysql> SELECT @@character_set_database, @@collation_database;
+--------------------------+----------------------+
| @@character_set_database | @@collation_database |
+--------------------------+----------------------+
| utf8mb4                  | utf8mb4_0900_ai_ci   |
+--------------------------+----------------------+
1 row in set (0.00 sec)
```

## Apply database migrations to the MySQL database

With Nautobot pointing to the MySQL database (we recommend creating a new Nautobot installation for this purpose), run `nautobot-server migrate` to create all of Nautobot's tables in the MySQL database `(nautobot-mysql) $`:

```no-highlight
nautobot-server migrate
```

## Remove the auto-populated Status records from the MySQL database

A side effect of the `nautobot-server migrate` command is that it will populate the `Status` table with a number of predefined records. This is normally useful for getting started quickly with Nautobot, but since we're going to be importing data from our other database, these records will likely conflict with the records to be imported. Therefore we need to remove them, using the `nautobot-server nbshell` command in our MySQL instance of Nautobot (`(nautobot-mysql) $` shell prompt):

```no-highlight
nautobot-server nbshell
```

Example output:

```no-highlight
### Nautobot interactive shell (32cec46b2b7e)
### Python 3.9.7 | Django 3.1.13 | Nautobot 1.1.3
### lsmodels() will show available models. Use help(<model>) for more info.
>>> Status.objects.all().delete()
(67, {'extras.Status_content_types': 48, 'extras.Status': 19})
>>>
```

Press Control-D to exit the `nbshell` when you are finished.

## Import the database dump into MySQL

Use the `nautobot-server loaddata` command to import the database dump that you previously created. This may take several minutes to complete depending on the size of your database. This is from the MySQL host with the prompt (`(nautobot-mysql) $`):

```no-highlight
nautobot-server loaddata --traceback nautobot_dump.json
```

Assuming that the command ran to completion with no errors, you should now have a fully populated clone of your original database in MySQL.
