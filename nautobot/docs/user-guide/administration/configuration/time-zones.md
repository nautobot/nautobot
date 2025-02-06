# Time Zones

Time zones affect several aspects of the of your Nautobot implementation to include:

* Logging timestamps across all services
* Changelogging timestamps in the database
* The UI time presented
* Scheduling of jobs

It's important to make sure that the time zones match on all of your Nautobot services, including the database server, Nautobot server, Celery Beat and any worker. This includes setting the system time zone on all of the servers and the configured time zone on all of the service configurations.

We highly recommend using UTC across all spaces to avoid any issues with daylight savings time changes or misalignment in timestamps. Leverage NTP across all servers and services to ensure the times are synchronized.

## Nautobot Application Configuration

Nautobot supports the [`TIME_ZONE`](settings.md#time_zone) setting, which will set the default time zone for the Nautobot service, worker, and scheduler.

A common misconfiguration is the Celery Beat and worker servers' `TIME_ZONE` setting. Since these services are running within the Nautobot process they also need this configuration set, either by setting the `NAUTOBOT_TIME_ZONE` environment variable or using the same `nautobot_config.py` file as the Nautobot server. You should also change the Database service's configured time zone to match the Nautobot server's time zone.

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

## Server Configuration

While outside the scope of this document to provide the time configuration for every flavor of server, included is an example for Ubuntu, please see your own operating system guide for further information.

```bash
timedatectl set-ntp yes
timedatectl set-timezone UTC
```
