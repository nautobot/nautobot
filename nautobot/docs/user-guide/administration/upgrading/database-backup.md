# Backing up the Nautobot Database

Before any upgrade of Nautobot, and as a general best practice, you'll want to back up the underlying database. This is important both from a general high-availability and error-recovery standpoint, and also specifically in case of any Nautobot update that includes database changes (which is most of them) as in general Nautobot does not guarantee that all database changes made during an upgrade will be reversible. If anything goes wrong during a Nautobot update, your database may be left in a bad/invalid state and your best recourse will be to restore from backup.

## Backing up PostgreSQL

Refer to [Backup and Restore](https://www.postgresql.org/docs/current/backup.html) in the PostgreSQL documentation for the various approaches to database backup that are recommended with PostgreSQL.

## Backing up MySQL

Refer to [Backup and Recovery](https://dev.mysql.com/doc/refman/8.1/en/backup-and-recovery.html) in the MySQL documentation for the various approaches to database backup that are recommended with MySQL.
