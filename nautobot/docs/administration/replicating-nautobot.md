# Replicating Nautobot

## Replicating the Database

Nautobot employs a [PostgreSQL](https://www.postgresql.org/) database, so general PostgreSQL best practices apply here. The database can be written to a file and restored using the `pg_dump` and `psql` utilities, respectively.

!!! note
    The examples below assume that your database is named `nautobot`.

### Export the Database

Use the `pg_dump` utility to export the entire database to a file:

```no-highlight
pg_dump nautobot > nautobot.sql
```

When replicating a production database for development purposes, you may find it convenient to exclude changelog data, which can easily account for the bulk of a database's size. To do this, exclude the `extras_objectchange` table data from the export. The table will still be included in the output file, but will not be populated with any data.

```no-highlight
pg_dump --exclude-table-data=extras_objectchange nautobot > nautobot.sql
```

### Load an Exported Database

When restoring a database from a file, it's recommended to delete any existing database first to avoid potential conflicts.

!!! warning
    The following will destroy and replace any existing instance of the database.

```no-highlight
psql -c 'drop database nautobot'
psql -c 'create database nautobot'
psql nautobot < nautobot.sql
```

Keep in mind that PostgreSQL user accounts and permissions are not included with the dump: You will need to create those manually if you want to fully replicate the original database (see the [installation docs](../installation/index.md#installing-nautobot-dependencies)). When setting up a development instance of Nautobot, it's strongly recommended to use different credentials anyway.

### Export the Database Schema

If you want to export only the database schema, and not the data itself (e.g. for development reference), do the following:

```no-highlight
pg_dump -s nautobot > nautobot_schema.sql
```

---

## Replicating Uploaded Media

By default, Nautobot stores uploaded files (such as image attachments) in its media directory. To fully replicate an instance of Nautobot, you'll need to copy both the database and the media files.

!!! note
    These operations are not necessary if your installation is utilizing a [remote storage backend](../configuration/optional-settings.md#storage_backend).

### Archive the Media Directory

Execute the following command (which may need to be changed if you're using non-default storage path settings):

```no-highlight
tar -czf nautobot_media.tar.gz $NAUTOBOT_ROOT/media/
```

### Restore the Media Directory

To extract the saved archive into a new installation, run the following from the installation root:

```no-highlight
tar -xf nautobot_media.tar.gz
```

---

## Cache Invalidation

If you are migrating your instance of Nautobot to a different machine, be sure to first invalidate the cache on the original instance by issuing the `invalidate all` management command (within the Python virtual environment):

```no-highlight
nautobot-server invalidate all
```
