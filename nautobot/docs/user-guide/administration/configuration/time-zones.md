# Time Zones

Nautobot supports the [`TIME_ZONE`](optional-settings.md#time_zone) setting, which will set the default time zone for Nautobot. This is used to display the time in the Nautobot UI footer and for scheduling jobs. We do not recommend changing this from the default of UTC to avoid any issues with daylight savings time changes. Whether you decide to change this setting or leave it at the default of UTC, it's important to make sure that the time zones match on all of your Nautobot services, including the database server, Nautobot server, Celery Beat and any worker servers. This includes setting the system time zone on all of the servers and the configured time zone on all of the service configurations. A common misconfiguration is the Celery Beat and worker servers' `TIME_ZONE` setting. Since these services are running within the Nautobot process they also need this configuration set, either by setting the `NAUTOBOT_TIME_ZONE` environment variable or using the same `nautobot_config.py` file as the Nautobot server. You should also change the Database service's configured time zone to match the Nautobot server's time zone.

## MySQL Time Zone Configuration

The MySQL database's default time zone can be configured through the configuration file usually found in `/etc/mysql/my.cnf` or `/etc/my.cnf`:

```ini
[mysqld]
default-time-zone = "+00:00"
```

This can also be changed with a SQL query:

```sql
SET GLOBAL time_zone = '+00:00';
```

## PostgreSQL Time Zone Configuration

The PostgreSQL database's default time zone can be configured through the configuration file. The location of this file can be found with the SQL query `SHOW config_file;`.

```no-highlight
timezone = UTC
```

!!! info
    The SQL command `SET TIME ZONE` only sets the time zone for the session.
