# Migrating from PostgreSQL to MySQL

This document explains how to migrate the contents of an existing Nautobot PostgreSQL database to a new MySQL database.

## Export data from PostgreSQL

In your existing installation of Nautobot with PostgreSQL, run the following command to generate a JSON dump of the database contents. This may take several minutes to complete depending on the size of your database. From the Postgres host `(nautobot-postgres) $`:

```no-highlight
nautobot-server dumpdata \
    --exclude auth.permission \
    --format json \
    --indent 2 \
    --traceback \
    > nautobot_dump.json
```

+/- 1.5.23
    - We do not recommend at this time using `--natural-primary` as this can result in inconsistent or incorrect data for data models that use GenericForeignKeys, such as `Cable`, `Note`, `ObjectChange`, and `Tag`.
    - We also do not recommend at this time using `--natural-foreign` as it can potentially result in errors if any data models incorrectly implement their `natural_key()` and/or `get_by_natural_key()` API methods.
    - `contenttypes` must not be excluded from the dump (it could be excluded previously due to the use of `--natural-foreign`).

!!! warning
    Because of the different SQL dialects used by PostgreSQL and MySQL, Django's JSON database dump format is being used as the go-between for migrating your database contents from the one system to the other. This is a different case than general database backup and recovery; for best practices there, please refer to [Database Backup](../upgrading/database-backup.md).

This will result in a file named `nautobot_dump.json`.

## Create the MySQL database

Create the MySQL database for Nautobot, ensuring that it is utilizing the default character set (`utf8mb4`) and default collation (`utf8mb4_0900_ai_ci`) settings for case-insensitivity. It is required that MySQL will be case-insensitive. Because these encodings are the defaults, if your MySQL installation has not been modified, there will be nothing for you to do other than make sure.

In very rare cases, there may be problems when importing your data from the case-sensitive PostgreSQL database dump that will need to be handled on a case-by-case basis. Please refer to the [instructions](../installation/install_system.md#database-setup) as necessary if you are unsure how to set up MySQL and create the Nautobot database.

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

## Remove auto-populated records from the MySQL database

A side effect of the `nautobot-server migrate` command is that it will populate the `ContentType`, `Job`, and `Status` tables with a number of predefined records. Depending on what Nautobot App(s) you have installed, the app(s) may also have auto-created database records of their own, such as `CustomField` or `Tag` records, in response to `nautobot-server migrate`. This is normally useful for getting started quickly with Nautobot, but since we're going to be importing data from our other database, these records will likely conflict with the records to be imported. Therefore we need to remove them, using the `nautobot-server nbshell` command in our MySQL instance of Nautobot (`(nautobot-mysql) $` shell prompt):

```no-highlight
nautobot-server nbshell
```

Enter the following Python commands into the shell:

```python
from django.apps import apps
for model in apps.get_models():
    if model._meta.managed and model.objects.exists():
        print(f"Deleting objects of {model}")
        print(model.objects.all().delete())
```

Example output:

```no-highlight
...
# Django version 3.2.16
# Nautobot version 2.0.0a0
# Example Nautobot App version 1.0.0
Python 3.8.16 (default, Mar 23 2023, 04:48:11)
[GCC 10.2.1 20210110] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>> from django.apps import apps
>>> for model in apps.get_models():
...     if model._meta.managed and model.objects.exists():
...         print(f"Deleting objects of {model}")
...         print(model.objects.all().delete())
...
Deleting objects of <class 'django.contrib.auth.models.Permission'>
(465, {'auth.Permission': 465})
Deleting objects of <class 'django.contrib.contenttypes.models.ContentType'>
(186, {'extras.CustomField_content_types': 1, 'extras.Status_content_types': 68, 'contenttypes.ContentType': 117})
Deleting objects of <class 'nautobot.extras.models.customfields.CustomField'>
(1, {'extras.CustomField': 1})
Deleting objects of <class 'nautobot.extras.models.statuses.Status'>
(20, {'extras.Status': 20})
Deleting objects of <class 'nautobot.extras.models.jobs.Job'>
(6, {'extras.Job': 6})
```

Press Control-D to exit the `nbshell` when you are finished.

## Import the database dump into MySQL

Use the `nautobot-server loaddata` command to import the database dump that you previously created. This may take several minutes to complete depending on the size of your database. This is from the MySQL host with the prompt (`(nautobot-mysql) $`):

```no-highlight
nautobot-server loaddata --traceback nautobot_dump.json
```

Assuming that the command ran to completion with no errors, you should now have a fully populated clone of your original database in MySQL.

## Rebuild cached cable path traces

Because cable path traces contain cached data which includes denormalized references to other database objects, it's possible that this cached data will be inaccurate after doing a `loaddata`. Fortunately there is [a `nautobot-server` command](../tools/nautobot-server.md#trace_paths) to force rebuilding of these caches, and we recommend doing so after the import is completed:

```no-highlight
nautobot-server trace_paths --force --no-input
```
