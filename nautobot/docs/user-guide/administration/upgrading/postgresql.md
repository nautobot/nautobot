# Upgrading PostgreSQL

Just like Nautobot itself, PostgreSQL has a release and maintenance cycle, and older versions eventually reach their end-of-life/end-of-support date, and so you will need to upgrade to a newer supported version. Additionally, updates to the Django framework underlying Nautobot may also force your hand when upgrading Nautobot, as new versions of Django adopted by Nautobot may drop support for legacy versions of PostgreSQL.

Upgrading between minor/patch versions of PostgreSQL is generally seamless, but new _major_ versions of PostgreSQL generally will not run against a database built by an older major version; instead, you will need to migrate the data to a new database. The rest of this document provides some basic guidance on how to proceed in such a case.

!!! tip
    In general we recommend that you upgrade PostgreSQL as a _separate_ step from upgrading Nautobot in order to reduce the complexity of the upgrade and allow easier troubleshooting and recovery should anything go wrong in the process.

!!! warning
    The specific steps to follow to perform an upgrade of PostgreSQL will vary depending on your deployment pattern; the below guides are intended as examples and do not claim to be comprehensive. Always make sure you have a valid [backup](database-backup.md) before attempting to upgrade!

## Upgrading a Docker-Based Installation

If you're running PostgreSQL in a Docker container (such as through Docker Compose or Kubernetes), with the database as a persistent volume mount, it's typically necessary to export and re-import the contents of the database (although there do exist various third-party Docker images that will run the `pg_upgrade` command to perform an in-place upgrade of the database). The approximate steps for an export and re-import might be as follows:

1. Stop all Nautobot-related Docker containers except for the PostgreSQL container.
2. Run `pg_dump ...` in the existing PostgreSQL Docker container to export the database to a text file.
3. Use `docker cp ...` to copy this text dump out of the container to an appropriate location as a backup.
4. Stop the existing PostgreSQL Docker container.
5. Create a new PostgreSQL Docker container (using the appropriate image for the newer version of PostgreSQL) with a new persistent volume mount for the database.
6. Use `docker cp ...` to copy the database dump into the new container.
7. Run `psql ...` to populate the new database from the exported text file.
8. Start Nautobot and related containers.

An example might include commands like the following:

```no-highlight title="2. In the old PostgreSQL container"
pg_dump --username nautobot nautobot > /tmp/nautobot.sql
```

```no-highlight title="3. On the host system"
docker cp nautobot-db-1:/tmp/nautobot.sql /backups/nautobot.sql
```

```no-highlight title="6. On the host system"
docker cp /backups/nautobot.sql nautobot-new-db-1:/tmp/nautobot.sql
```

```no-highlight title="7. In the new PostgreSQL container"
psql --username nautobot -X --set ON_ERROR_STOP=on nautobot < /tmp/nautobot.sql
```

Refer to the [PostgreSQL documentation for `pg_dump`](https://www.postgresql.org/docs/current/backup-dump.html) for more examples and guidance.

## Upgrading a Server-Based Installation

If you're running PostgreSQL directly on Linux as a system service, as an alternative to `pg_dump` and restore, it may be preferable to use the `pg_upgrade` command to migrate the database from an old installation to a new installation. The approximate steps might be as follows:

1. Stop Nautobot web server, Celery worker, and Celery beat system services.
2. Stop the existing PostgreSQL system service.
3. Back up the current database.
4. Install the new version of PostgreSQL, coexisting with the old version rather than replacing it, and ensure that the new version's system service is not running at this time.
5. Run *the new version's* `pg_upgrade` command, pointing to the old and new PostgreSQL binary and data directories.
6. Start the new PostgreSQL system service.
7. Start Nautobot and related system services.

Refer to the [PostgreSQL documentation for `pg_upgrade`](https://www.postgresql.org/docs/current/pgupgrade.html) for more examples and guidance.
