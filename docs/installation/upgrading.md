# Upgrading to a New Nautobot Release

## Review the Release Notes

Prior to upgrading your Nautobot instance, be sure to carefully review all [release notes](../../release-notes/) that have been published since your current version was released. Although the upgrade process typically does not involve additional work, certain releases may introduce breaking or backward-incompatible changes. These are called out in the release notes under the release in which the change went into effect.

## Update Dependencies to Required Versions

Nautobot v1.0.0 and later requires the following:

| Dependency | Minimum Version |
|------------|-----------------|
| Python     | 3.6             |
| PostgreSQL | 9.6             |
| Redis      | 4.0             |

## Install the Latest Release

As with the initial installation, you can upgrade Nautobot by either downloading the latest release package or by cloning the `master` branch of the git repository.

### Option A: Download a Release

Download the [latest stable release](https://github.com/nautobot/nautobot/releases) from GitHub as a tarball or ZIP archive. Extract it to your desired path. In this example, we'll use `/opt/nautobot`.

Download and extract the latest version:

```no-highlight
wget https://github.com/nautobot/nautobot/archive/vX.Y.Z.tar.gz
sudo tar -xzf vX.Y.Z.tar.gz -C /opt
sudo ln -sfn /opt/nautobot-X.Y.Z/ /opt/nautobot
```

Copy `local_requirements.txt`, `configuration.py`, and `ldap_config.py` (if present) from the current installation to the new version:

```no-highlight
sudo cp /opt/nautobot-X.Y.Z/local_requirements.txt /opt/nautobot/
sudo cp /opt/nautobot-X.Y.Z/nautobot_root/nautobot/core/configuration.py /opt/nautobot/nautobot_root/nautobot/core/
sudo cp /opt/nautobot-X.Y.Z/nautobot_root/nautobot/core/ldap_config.py /opt/nautobot/nautobot_root/nautobot/core/
```

Be sure to replicate your uploaded media as well. (The exact action necessary will depend on where you choose to store your media, but in general moving or copying the media directory will suffice.)

```no-highlight
sudo cp -pr /opt/nautobot-X.Y.Z/nautobot_root/media/ /opt/nautobot/nautobot_root/
```

Also make sure to copy or link any jobs (formerly "custom scripts" and "reports") that you've made. Note that if these are stored outside the project root, you will not need to copy them. (Check the `SCRIPTS_ROOT` and `REPORTS_ROOT` parameters in the configuration file above if you're unsure.)

!!! note
    When migrating to this release, note that `SCRIPTS_ROOT` and `REPORTS_ROOT` are deprecated and these files should be consolidated into a single shared `JOBS_ROOT` directory.

```no-highlight
sudo cp /opt/nautobot-X.Y.Z/nautobot_root/scripts/*.py /opt/nautobot/nautobot_root/jobs/
sudo cp /opt/nautobot-X.Y.Z/nautobot_root/reports/*.py /opt/nautobot/nautobot_root/jobs/
# If you have any script data files (YAML, JSON) stored in the SCRIPTS_ROOT directory, be sure to copy those as well
```

If you followed the original installation guide to set up gunicorn, be sure to copy its configuration as well:

```no-highlight
sudo cp /opt/nautobot-X.Y.Z/gunicorn.py /opt/nautobot/
```

### Option B: Clone the Git Repository

This guide assumes that Nautobot is installed at `/opt/nautobot`. Pull down the most recent iteration of the master branch:

```no-highlight
cd /opt/nautobot
sudo git checkout master
sudo git pull origin master
```

## Run the Upgrade Script

Once the new code is in place, verify that any optional Python packages required by your deployment (e.g. `napalm` or `django-auth-ldap`) are listed in `local_requirements.txt`. Then, run the upgrade script:

```no-highlight
sudo ./upgrade.sh
```

This script performs the following actions:

* Destroys and rebuilds the Python virtual environment
* Installs all required Python packages (listed in `requirements.txt`)
* Installs any additional packages from `local_requirements.txt`
* Applies any database migrations that were included in the release
* Collects all static files to be served by the HTTP service
* Deletes stale content types from the database
* Deletes all expired user sessions from the database
* Clears all cached data to prevent conflicts with the new release

!!! note
    If the upgrade script prompts a warning about unreflected database migrations, this indicates that some change has
    been made to your local codebase and should be investigated. Never attempt to create new migrations unless you are
    intentionally modifying the database schema.

## Restart the Nautobot Services

!!! warning
    If you are upgrading from an installation that does not use a Python virtual environment (any release prior to v2.7.9), you'll need to update the systemd service files to reference the new Python and gunicorn executables before restarting the services. These are located in `/opt/nautobot/venv/bin/`. See the example service files in `/opt/nautobot/contrib/` for reference.

Finally, restart the gunicorn and RQ services:

```no-highlight
sudo systemctl restart nautobot nautobot-rq
```

!!! note
    If upgrading from an installation that uses supervisord, please see the instructions for [migrating to systemd](migrating-to-systemd.md). The use of supervisord is no longer supported.
