# Installing Apps

The instructions below detail the process for installing and enabling a Nautobot app.

You must be **absolutely** sure to install the app within Nautobot's virtual environment.

!!! note
    If you installed Nautobot in a production environment, you'll want to sudo to the nautobot user first using `sudo -iu nautobot`.

## Install the Package

Download and install the app package per its installation instructions. Apps published via PyPI are typically installed using `pip3`.

```no-highlight title="Pip install the package"
pip3 install <package>
```

## Enable the App

In your `nautobot_config.py`, add the app's name to the `PLUGINS` list:

```python title="Update PLUGINS list in nautobot_config.py"
PLUGINS = [
    'app_name',
]
```

## Configure the App

If the app requires any configuration, define it in `nautobot_config.py` under the `PLUGINS_CONFIG` parameter. The available configuration parameters should be detailed in the app's README file.

```python title="Update PLUGINS_CONFIG in nautobot_config.py"
PLUGINS_CONFIG = {
    'app_name': {
        'setting_name': 'value',
        'buzz': 'bazz'
    }
}
```

## Run `nautobot-server post_upgrade`

After installing or upgrading a app, you should always run [`nautobot-server post_upgrade`](../tools/nautobot-server.md#post_upgrade). This command will ensure that any necessary post-installation tasks are run, for example:

* Migrating the database to include any new or updated data models from the app
* Collecting any static files provided by the app
* Etc.

```no-highlight title="Run the post_upgrade command"
nautobot-server post_upgrade
```

??? example "Example post_upgrade output"

    ```no-highlight title="Example Output of post_upgrade Command"
    # nautobot-server post_upgrade
    Performing database migrations...
    Operations to perform:
      Apply all migrations: admin, auth, circuits, contenttypes, db, dcim, extras, ipam,
    nautobot_app_example, sessions, social_django, taggit, tenancy, users, virtualization
    Running migrations:
      No migrations to apply.

    Generating cable paths...
    Found no missing circuit termination paths; skipping
    Found no missing console port paths; skipping
    Found no missing console server port paths; skipping
    Found no missing interface paths; skipping
    Found no missing power feed paths; skipping
    Found no missing power outlet paths; skipping
    Found no missing power port paths; skipping
    Finished.

    Collecting static files...

    0 static files copied to '/opt/nautobot/static', 972 unmodified.

    Removing stale content types...

    Removing expired sessions...

    Invalidating cache...

    ```

## Restart the WSGI Service

Restart the WSGI service to load the new app:

```no-highlight title="Restart Nautobot services"
sudo systemctl restart nautobot nautobot-worker nautobot-scheduler
```

## Verify that the App is Installed

In the Nautobot UI, navigate to **Apps -> Installed Apps**. The newly installed app should appear in the displayed table if everything is configured correctly. You can also click on the app's name in this table to view more detailed information about this app.
