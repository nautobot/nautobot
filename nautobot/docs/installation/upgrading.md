# Upgrading to a New Nautobot Release

## Review the Release Notes

Prior to upgrading your Nautobot instance, be sure to carefully review all [release notes](../../release-notes/) that
have been published since your current version was released. Although the upgrade process typically does not involve
additional work, certain releases may introduce breaking or backward-incompatible changes. These are called out in the
release notes under the release in which the change went into effect.

!!! note
    As of Nautobot v1.2.0, Nautobot supports deferring ("scheduling") Jobs. To facilitate this, a new service called `celery-scheduler` is now required. Please review the [service installation documentation](./services.md) to find out how to set it up.

## Update Prerequisites to Required Versions

Nautobot v1.0.0 and later requires the following:

| Dependency | Minimum Version |
|------------|-----------------|
| Python     | 3.6             |
| PostgreSQL | 9.6             |
| Redis      | 4.0             |

Nautobot v1.1.0 and later can optionally support the following:

> *Nautobot v1.1.0 added support for MySQL 8.0 as a database backend as an alternative to PostgreSQL.*

| Dependency | Minimum Version |
|------------|-----------------|
| MySQL      | 8.0             |

!!! tip
    If you wish to migrate from PostgreSQL to MySQL, we recommend creating a new Nautobot installation based on MySQL and then [migrating the database contents to the new installation](./migrating-from-postgresql.md), rather than attempting an in-place upgrade or migration.

## Install the Latest Release

As with the initial installation, you can upgrade Nautobot by installing the Python package directly from the Python Package Index (PyPI).

!!! warning
    Unless explicitly stated, all steps requiring the use of `pip3` or `nautobot-server` in this document should be performed as the `nautobot` user!

Upgrade Nautobot using `pip3`:

```no-highlight
$ pip3 install --upgrade nautobot
```

## Upgrade your Optional Dependencies

If you do not have any optional dependencies, you may skip this step.

Once the new code is in place, verify that any optional Python packages required by your deployment (e.g. `napalm` or
`django-auth-ldap`) are listed in `local_requirements.txt`. 

Then, upgrade your dependencies using `pip3`:

```no-highlight
$ pip3 install --upgrade -r $NAUTOBOT_ROOT/local_requirements.txt
```

## Run the Post Upgrade Operations

Finally, run Nautobot's `post_upgrade` management command:

```no-highlight
$ nautobot-server post_upgrade
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
$ sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```
