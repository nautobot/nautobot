# Upgrading to a New Nautobot Release

## Review the Release Notes

Prior to upgrading your Nautobot instance, be sure to carefully review all [release notes](../release-notes/index.md) that
have been published since your current version was released. Although the upgrade process typically does not involve
additional work, certain releases may introduce breaking or backward-incompatible changes. These are called out in the
release notes under the release in which the change went into effect.

The below sub-sections describe some key changes that deployers should be aware of, but are not intended to be a replacement for reading the release notes carefully and in depth.

### Updating from Nautobot 1.0.x to 1.1.x

#### Migration from RQ to Celery

Prior to version 1.1.0, Nautobot utilized RQ as the primary background task worker. As of Nautobot 1.1.0, RQ is now *deprecated*, as Celery has been introduced to eventually replace RQ for executing background tasks within Nautobot. All Nautobot **core** usage of RQ has been migrated to use Celery.

RQ support for custom tasks was not removed in order to give plugin authors time to migrate, however, to continue to utilize advanced Nautobot features such as Git repository synchronization, webhooks, jobs, etc. you must migrate your `nautobot-worker` deployment from RQ to Celery.

Please see the section on [migrating to Celery from RQ](./services.md#migrating-to-celery-from-rq) for more information on how to easily migrate your deployment.

### Updating from Nautobot 1.1.x to 1.2.x

#### Introduction of Celery Beat Scheduler

As of Nautobot v1.2.0, Nautobot supports deferring ("scheduling") Jobs. To facilitate this, a new service called `celery-scheduler` is now required. Please review the [service installation documentation](./services.md#celery-beat-scheduler) to find out how to set it up.

### Updating from Nautobot 1.2.x to 1.3.x

#### Revision of Recommended MySQL UTF-8 Encoding

The recommended database encoding settings have been revised to rely upon the default UTF-8 encoding provided by MySQL for collation of data in the database. Previously we were recommending in our documentation that the collation encoding be set explicitly to `utf8mb4_bin`. We are now recommending `utf8mb4_0900_ai_ci` which is configured by default on unmodified MySQL database server deployments.

The collation encoding is used to inform MySQL how characters are sorted in the database. This is important when it comes to retrieving data that has special characters or special byte-encoding such as accents or ligatures, and also including emojis. In some cases, with the `utf8mb4_bin` encoding we were previously recommending, case-insensitive searching may return inconsistent or incorrect results.

!!! danger
    It is **strongly recommended** that you backup your database before executing this query and that you perform this in a non-production environment to identify any potential issues prior to updating your production environment.

If you have an existing MySQL database, you may update your database to use the recommended encoding by using `nautobot-server dbshell` to launch a database shell and executing the following command:

```no-highlight
nautobot-server dbshell
```

Example output:

```no-highlight
mysql> ALTER DATABASE nautobot COLLATE utf8mb4_0900_ai_ci;
Query OK, 1 row affected (0.07 sec)
```

Please see the [official MySQL documentation on migrating collation encoding settings](https://dev.mysql.com/blog-archive/mysql-8-0-collations-migrating-from-older-collations/) for more information on troubleshooting any issues you may encounter.

## Update Prerequisites to Required Versions

Nautobot v1.3.0 and later requires the following:

| Dependency | Minimum Version |
| ---------- | --------------- |
| Python     | 3.7             |
| PostgreSQL | 9.6             |
| Redis      | 4.0             |

Nautobot v1.1.0 and later can optionally support the following:

> *Nautobot v1.1.0 added support for MySQL 8.0 as a database backend as an alternative to PostgreSQL.*

| Dependency | Minimum Version |
| ---------- | --------------- |
| MySQL      | 8.0             |

!!! tip
    If you wish to migrate from PostgreSQL to MySQL, we recommend creating a new Nautobot installation based on MySQL and then [migrating the database contents to the new installation](./migrating-from-postgresql.md), rather than attempting an in-place upgrade or migration.

## Install the Latest Release

As with the initial installation, you can upgrade Nautobot by installing the Python package directly from the Python Package Index (PyPI).

!!! warning
    Unless explicitly stated, all steps requiring the use of `pip3` or `nautobot-server` in this document should be performed as the `nautobot` user!

Upgrade Nautobot using `pip3`:

```no-highlight
pip3 install --upgrade nautobot
```

## Upgrade your Optional Dependencies

If you do not have any optional dependencies, you may skip this step.

Once the new code is in place, verify that any optional Python packages required by your deployment (e.g. `napalm` or
`django-auth-ldap`) are listed in `local_requirements.txt`.

Then, upgrade your dependencies using `pip3`:

```no-highlight
pip3 install --upgrade -r $NAUTOBOT_ROOT/local_requirements.txt
```

## Run the Post Upgrade Operations

Finally, run Nautobot's `post_upgrade` management command:

```no-highlight
nautobot-server post_upgrade
```

This command performs the following actions:

* Applies any database migrations that were included in the release
* Generates any missing cable paths among all cable termination objects in the database
* Collects all static files to be served by the HTTP service
* Deletes stale content types from the database
* Deletes all expired user sessions from the database
* Clears all cached data to prevent conflicts with the new release

## Restart the Nautobot Services

Finally, with root permissions, restart the web and background services:

```no-highlight
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```
