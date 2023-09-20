# The Nautobot Server Command

Nautobot includes a command-line (CLI) management utility called `nautobot-server`, that is used as a single entrypoint for common administrative tasks.

## Background

For those familiar with Django applications, this CLI utility works exactly as a project's `manage.py` script would, except that it comes bundled with the Nautobot code and therefore it gets automatically installed in the `bin` directory of your application environment.

!!! important
    Since Nautobot is a Django application, there are a number of built-in management commands that will not be covered in this document. Please see the [official Django documentation on management commands](https://docs.djangoproject.com/en/stable/ref/django-admin/#available-commands) for more information.

!!! important
    Django does not recognize `nautobot-server`. Anywhere `python manage.py` is mentioned, it is safe to replace with `nautobot-server`.

## Getting Help

To see all available management commands as the Nautobot user:

```no-highlight
nautobot-server help
```

All management commands have a `-h/--help` flag to list all available arguments for that command, for example:

```no-highlight
nautobot-server migrate --help
```

## Available Commands

### `audit_dynamic_groups`

`nautobot-server audit_dynamic_groups`

After upgrading your Nautobot instance from v1.x to v2.x, breaking changes made to model filter fields will, in some cases, invalidate existing `DynamicGroup` instances' filter data. `nautobot-server audit_dynamic_groups` is a helper command to assist you in cleaning up `DynamicGroup` filter data by spotting invalid filters and outputting them to the command line interface.

```no-highlight
nautobot-server audit_dynamic_groups
```

Example output:

If you have invalid filters in your `DynamicGroup` instances, the following output should be expected:

```no-highlight
>>> Auditing existing DynamicGroup data for invalid filters ...

    DynamicGroup instance with name `Test DP` and content type `dcim | rack` has an invalid filter `site`
    DynamicGroup instance with name `Test DP` and content type `dcim | rack` has an invalid filter `length`
    DynamicGroup instance with name `Test DP` and content type `dcim | rack` has an invalid filter `region`
    DynamicGroup instance with name `Test DP 1` and content type `ipam | IP address` has an invalid filter `site`
    DynamicGroup instance with name `Test DP 1` and content type `ipam | IP address` has an invalid filter `length`
    DynamicGroup instance with name `Test DP 2` and content type `dcim | device` has an invalid filter `site`
    DynamicGroup instance with name `Test DP 2` and content type `dcim | device` has an invalid filter `region`
    DynamicGroup instance with name `Test DP 3` and content type `dcim | device redundancy group` has an invalid filter `site`
    DynamicGroup instance with name `Test DP 3` and content type `dcim | device redundancy group` has an invalid filter `length`
    DynamicGroup instance with name `Test DP 3` and content type `dcim | device redundancy group` has an invalid filter `region`
    DynamicGroup instance with name `Test DP 4` and content type `example_plugin | another example model` has an invalid filter `site`

>>> Please fix the broken filters stated above according to the documentation available at:
<nautobot-home>/static/docs/user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1.html#ui-graphql-and-rest-api-filter-changes
```

If your filter data is valid, you should see a success message at the end of the output:

```no-highlight
>>> Auditing existing DynamicGroup data for invalid filters ...


>>> All DynamicGroup filters are validated successfully!
```

### `build_ui`

`nautobot-server build_ui`

Build or rebuild the UI for the Nautobot server environment and installed Nautobot Apps. This command is normally run as part of [`nautobot-server post_upgrade`](#post_upgrade) rather than being invoked directly by an administrator.

Here are some commonly used flags:

1. `--npm-install` - Install UI packages.
2. `--no-render-apps` - Do not render Nautobot App imports.
3. `--no-npm-build` - Do not compile UI.

### `celery`

`nautobot-server celery`

Celery command entrypoint which serves as a thin wrapper to the `celery` command that includes the Nautobot Celery application context. This allows us to execute Celery commands without having to worry about the chicken-and-egg problem with bootstrapping the Django settings.

Most commonly you will be using this command to start the Celery worker process:

```no-highlight
nautobot-server celery worker --loglevel INFO --pidfile $(pwd)/nautobot-celery.pid -n worker1
```

Output:

```no-highlight
celery@worker1 v5.1.1 (sun-harmonics)

[config]
.> app:         nautobot:0x10c357eb0
.> transport:   redis://localhost:6379/0
.> results:     redis://localhost:6379/0
.> concurrency: 8 (prefork)
.> task events: OFF (enable -E to monitor tasks in this worker)

[queues]
.> celery           exchange=celery(direct) key=celery


[tasks]
  . nautobot.core.tasks.get_releases
  . nautobot.extras.datasources.git.pull_git_repository_and_refresh_data
  . nautobot.extras.jobs.run_job
  . nautobot.extras.tasks.delete_custom_field_data
  . nautobot.extras.tasks.process_webhook
  . nautobot.extras.tasks.provision_field
  . nautobot.extras.tasks.update_custom_field_choice_data

[2021-07-01 21:32:40,680: INFO/MainProcess] Connected to redis://localhost:6379/0
[2021-07-01 21:32:40,690: INFO/MainProcess] mingle: searching for neighbors
[2021-07-01 21:32:41,713: INFO/MainProcess] mingle: all alone
[2021-07-01 21:32:41,730: INFO/MainProcess] celery@worker1 ready.
```

!!! note
    The internals of this command are built into Celery. Please see the [official Celery workers guide](https://docs.celeryq.dev/en/stable/userguide/workers.html) for more information.

### `collectstatic`

`nautobot-server collectstatic`

Collect static files into [`STATIC_ROOT`](../configuration/optional-settings.md#static_root).

```no-highlight
nautobot-server collectstatic
```

Output:

```no-highlight
965 static files copied to '/opt/nautobot/static'.
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `collectstatic`](https://docs.djangoproject.com/en/stable/ref/django-admin/#collectstatic) for more information.

### `createsuperuser`

`nautobot-server createsuperuser`

Creates a superuser account that has all permissions.

```no-highlight
nautobot-server createsuperuser
```

This provides the following output:

```no-highlight
Username (leave blank to use 'jathan'): example
Email address: example@localhost
Password:
Password (again):
Superuser created successfully.
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `createsuperuser`](https://docs.djangoproject.com/en/stable/ref/django-admin/#createsuperuser) for more information.

### `dbshell`

`nautobot-server dbshell`

A shell for your database. This can be very useful in troubleshooting raw database issues.

!!! danger
    This is an advanced feature that gives you direct access to run raw SQL queries. Use this very cautiously as you can cause irreparable damage to your Nautobot installation.

```no-highlight
nautobot-server dbshell
```

Output:

```no-highlight
psql (12.6 (Ubuntu 12.6-0ubuntu0.20.04.1))
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
Type "help" for help.

nautobot=> \conninfo
You are connected to database "nautobot" as user "nautobot" on host "localhost" (address "::1") at port "5432".
SSL connection (protocol: TLSv1.3, cipher: TLS_AES_256_GCM_SHA384, bits: 256, compression: off)
nautobot=> \q
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `dbshell`](https://docs.djangoproject.com/en/stable/ref/django-admin/#dbshell) for more information.

### `dumpdata`

+/- 1.3.0
    - `extras.job` should now be included in the dump (removed `--exclude extras.job` from the example usage)
    - `django_rq` should now be excluded from the dump (added `--exclude django_rq` to the example usage)

+/- 1.5.23
    - We do not recommend at this time using `--natural-primary` as this can result in inconsistent or incorrect data for data models that use GenericForeignKeys, such as `Cable`, `Note`, `ObjectChange`, and `Tag`.
    - We also do not recommend at this time using `--natural-foreign` as it can potentially result in errors if any data models incorrectly implement their `natural_key()` and/or `get_by_natural_key()` API methods.
    - `contenttypes` must not be excluded from the dump (it could be excluded previously due to the use of `--natural-foreign`).

+/- 2.0.0
    - `django_rq` is no longer part of Nautobot's dependencies and so no longer needs to be explicitly excluded.

```no-highlight
nautobot-server dumpdata \
  --exclude auth.permission \
  --format json \
  --indent 2 \
  --traceback \
  > nautobot_dump.json
```

Use this command to generate a JSON dump of the database contents.

One example of using this command would be to [export data from PostgreSQL](../migration/migrating-from-postgresql.md#export-data-from-postgresql) and then [import the data dump into MySQL](../migration/migrating-from-postgresql.md#import-the-database-dump-into-mysql).

!!! warning
    While this command *can* be used in combination with `nautobot-server loaddata` as a way to do database backup-and-restore, it's not generally the most efficient or straightforward way to do so. Refer to [Database Backup](../upgrading/database-backup.md) for recommendations.

### `fix_custom_fields`

`nautobot-server fix_custom_fields`

Adds/Removes any custom fields which should or should not exist on an object. This command should not be run unless a custom fields jobs has failed:

```no-highlight
nautobot-server fix_custom_fields
```

Example output:

```no-highlight
Processing ContentType dcim | device
Processing ContentType dcim | location
Processing ContentType dcim | rack
Processing ContentType dcim | cable
Processing ContentType dcim | power feed
Processing ContentType circuits | circuit
Processing ContentType ipam | prefix
... (truncated for brevity of documentation) ...
```

### `generate_secret_key`

`nautobot-server generate_secret_key`

Generates a new [`SECRET_KEY`](../configuration/required-settings.md#secret_key) that can be used in your `nautobot_config.py`:

```no-highlight
nautobot-server generate_secret_key
```

Output:

```no-highlight
e!j=vrlhz-!wl8p_3+q5s5cph29nzj$xm81eap-!&n!_9^du09
```

### `generate_test_data`

+++ 1.5.0

`nautobot-server generate_test_data [--flush] --seed SEED`

Populate the database with various data as a baseline for testing (automated or manual).

`--flush`  
Flush any existing data from the database before generating new data.

!!! danger
    Running this command with the `--flush` argument will clear all existing data in your database. You have been warned.

`--seed SEED`  
String to use as a random generator seed for reproducible results.

```no-highlight
nautobot-server generate_test_data --flush --seed "Nautobot"
```

Sample output:

```no-highlight
Flushing all existing data from the database...
Seeding the pseudo-random number generator with seed "Nautobot"...
Creating Statuses...
Creating TenantGroups...
Creating Tenants...
Creating RIRs...
Creating RouteTargets...
Creating VRFs...
Creating IP/VLAN Roles...
Creating VLANGroups...
Creating VLANs...
Database populated successfully!
```

### `health_check`

`nautobot-server health_check`

Run health checks and exit 0 if everything went well.

```no-highlight
nautobot-server health_check
```

Output

```no-highlight
DatabaseBackend          ... working
DefaultFileStorageHealthCheck ... working
RedisBackend             ... working
```

Please see the [healthcheck documentation](../guides/healthcheck.md) for more information.

### `init`

`nautobot-server init [--disable-installation-metrics] [config_path]`

Generates a new configuration with all of the default settings provided for you, and will also generate a unique[`SECRET_KEY`](../configuration/required-settings.md#secret_key).

By default the file will be created at `$HOME/.nautobot/nautobot_config.py`:

```no-highlight
nautobot-server init
```

Output:

```no-highlight
Nautobot would like to send anonymized installation metrics to the project's maintainers.
These metrics include the installed Nautobot version, the Python version in use, an anonymous "deployment ID", and a list of one-way-hashed names of enabled Nautobot Apps and their versions.
Allow Nautobot to send these metrics? [y/n]: y
Installation metrics will be sent when running 'nautobot-server post_upgrade'. Thank you!
Configuration file created at /home/example/.nautobot/nautobot_config.py
```

+++ 1.6.0
    The `nautobot-server init` command will now prompt you to set the initial value for the [`INSTALLATION_METRICS_ENABLED`](../configuration/optional-settings.md#installation_metrics_enabled) setting. See the [send_installation_metrics](#send_installation_metrics) command for more information about the feature that this setting toggles.

For more information on configuring Nautobot for the first time or on more advanced configuration patterns, please see the guide on [Nautobot Configuration](../configuration/index.md).

### `loaddata`

`nautobot-server loaddata --traceback nautobot_dump.json`

To import the data that was exported with `nautobot-server dumpdata ...` see the following documentation:

- [Remove auto-populated records from the database](../migration/migrating-from-postgresql.md#remove-auto-populated-records-from-the-mysql-database)
- [Import the database dump](../migration/migrating-from-postgresql.md#import-the-database-dump-into-mysql)
- [Rebuild cached cable path traces](../migration/migrating-from-postgresql.md#rebuild-cached-cable-path-traces)

### `migrate`

`nautobot-server migrate [app_label] [migration_name]`

Initialize a new database or run any pending database migrations to an existing database.

```no-highlight
nautobot-server migrate
```

Output:

```no-highlight
Wrapping model clean methods for custom validators failed because the ContentType table was not available or populated. This is normal during the execution of the migration command for the first time.
Operations to perform:
  Apply all migrations: admin, auth, circuits, contenttypes, dcim, extras, ipam, sessions, taggit, tenancy, users, virtualization
Running migrations:
  Applying contenttypes.0001_initial... OK
  Applying auth.0001_initial... OK
  Applying admin.0001_initial... OK
... (truncated for brevity of documentation) ...
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `migrate`](https://docs.djangoproject.com/en/stable/ref/django-admin/#migrate) for more information.

### `nbshell`

`nautobot-server nbshell`

An interactive Python shell with all of the database models and various other utilities already imported for you. This is immensely useful for direct access to manipulating database objects.

!!! danger
    This is an advanced feature that gives you direct access to the Django database models. Use this very cautiously as you can cause irreparable damage to your Nautobot installation.

```no-highlight
nautobot-server nbshell
```

Prompt provided:

```no-highlight
# Shell Plus Model Imports
from constance.backends.database.models import Constance
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.sessions.models import Session
from django_celery_beat.models import ClockedSchedule, CrontabSchedule, IntervalSchedule, PeriodicTask, PeriodicTasks, SolarSchedule
from django_celery_results.models import ChordCounter, GroupResult, TaskResult
from example_plugin.models import AnotherExampleModel, ExampleModel
from nautobot.circuits.models import Circuit, CircuitTermination, CircuitType, Provider, ProviderNetwork
from nautobot.dcim.models.cables import Cable, CablePath
from nautobot.dcim.models.device_component_templates import ConsolePortTemplate, ConsoleServerPortTemplate, DeviceBayTemplate, FrontPortTemplate, InterfaceTemplate, PowerOutletTemplate, PowerPortTemplate, RearPortTemplate
from nautobot.dcim.models.device_components import ConsolePort, ConsoleServerPort, DeviceBay, FrontPort, Interface, InventoryItem, PowerOutlet, PowerPort, RearPort
from nautobot.dcim.models.devices import Device, DeviceRedundancyGroup, DeviceType, Manufacturer, Platform, VirtualChassis
from nautobot.dcim.models.locations import Location, LocationType
from nautobot.dcim.models.power import PowerFeed, PowerPanel
from nautobot.dcim.models.racks import Rack, RackGroup, RackReservation
from nautobot.extras.models.change_logging import ObjectChange
from nautobot.extras.models.customfields import ComputedField, CustomField, CustomFieldChoice
from nautobot.extras.models.datasources import GitRepository
from nautobot.extras.models.groups import DynamicGroup, DynamicGroupMembership
from nautobot.extras.models.jobs import Job, JobHook, JobLogEntry, JobResult, ScheduledJob, ScheduledJobs
from nautobot.extras.models.models import ConfigContext, ConfigContextSchema, CustomLink, ExportTemplate, FileAttachment, FileProxy, GraphQLQuery, HealthCheckTestModel, ImageAttachment, Note, Webhook
from nautobot.extras.models.relationships import Relationship, RelationshipAssociation
from nautobot.extras.models.roles import Role
from nautobot.extras.models.secrets import Secret, SecretsGroup, SecretsGroupAssociation
from nautobot.extras.models.statuses import Status
from nautobot.extras.models.tags import Tag, TaggedItem
from nautobot.ipam.models import IPAddress, Prefix, RIR, RouteTarget, Service, VLAN, VLANGroup, VRF
from nautobot.tenancy.models import Tenant, TenantGroup
from nautobot.users.models import AdminGroup, ObjectPermission, Token, User
from nautobot.virtualization.models import Cluster, ClusterGroup, ClusterType, VMInterface, VirtualMachine
from social_django.models import Association, Code, Nonce, Partial, UserSocialAuth
# Shell Plus Django Imports
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Avg, Case, Count, F, Max, Min, Prefetch, Q, Sum, When
from django.utils import timezone
from django.urls import reverse
from django.db.models import Exists, OuterRef, Subquery
# Django version 3.2.18
# Nautobot version 2.0.0a2
# Example Nautobot App version 1.0.0
Python 3.8.16 (default, Mar 23 2023, 04:48:11)
[GCC 10.2.1 20210110] on linux
Type "help", "copyright", "credits" or "license" for more information.
(InteractiveConsole)
>>>
```

Please see the dedicated guide on the [Nautobot Shell](nautobot-shell.md) for more information.

### `pre_migrate`

--- 2.0.0

`nautobot-server pre_migrate`

Performs pre-migration validation checks for Nautobot 2.0. Only available in Nautobot 1.5.23 and later versions of Nautobot 1.x.

### `post_upgrade`

`nautobot-server post_upgrade`

Performs common server post-upgrade operations using a single entrypoint.

This will run the following management commands with default settings, in order:

+/- 1.6.0
    Added the [`send_installation_metrics`](#send_installation_metrics) command to the list of commands run by `post_upgrade`.

- `migrate`
- `trace_paths`
- `build_ui`
- `collectstatic`
- `remove_stale_contenttypes`
- `clearsessions`
- `send_installation_metrics`
- `refresh_content_type_cache`
- `refresh_dynamic_group_member_caches`

!!! note
    Commands listed here that are not covered in this document here are Django built-in commands.

--- 2.0.0
    With the removal of `django-cacheops` from Nautobot, this command no longer runs `invalidate all`.

+++ 2.0.0
    Added [`build_ui`](#build_ui) to this command's default behavior.

`--no-build-ui`
Do not automatically rebuild the new UI.

`--no-clearsessions`  
Do not automatically clean out expired sessions.

`--no-collectstatic`  
Do not automatically collect static files into a single location.

`--no-migrate`  
Do not automatically perform any database migrations.

`--no-remove-stale-contenttypes`  
Do not automatically remove stale content types.

`--no-trace-paths`  
Do not automatically generate missing cable paths.

--- 2.0.0
    With the removal of `django-cacheops` from Nautobot, the `--no-invalidate-all` flag was removed from this command.

`--no-refresh-content-type-cache`  
Do not automatically refresh the content type cache.

`--no-refresh-dynamic-group-member-caches`  
Do not automatically refresh the dynamic group member lists.

```no-highlight
nautobot-server post_upgrade
```

Example Output:

```no-highlight
Performing database migrations...
Operations to perform:
  Apply all migrations: admin, auth, circuits, contenttypes, dcim, extras, ipam, sessions, taggit, tenancy, users, virtualization
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

0 static files copied to '/opt/nautobot/static', 965 unmodified.

Removing stale content types...

Removing expired sessions...
```

### `refresh_dynamic_group_member_caches`

+++ 1.6.0

`nautobot-server refresh_dynamic_group_member_caches`

Refresh the cached members of all Dynamic Groups. This is useful to periodically update the cached list of members of a Dynamic Group without having to wait for caches to expire, which defaults to one hour.

### `refresh_content_type_caches`

+++ 1.6.0

`nautobot-server refresh_content_type_caches`

Refresh the cached ContentType object property available via `Model._content_type_cached`. If content types are added or removed, this command will update the cache to reflect the current state of the database, but should already be done through the `post_upgrade` command.

### `remove_stale_scheduled_jobs`

+++ 1.3.10

`nautobot-server remove_stale_scheduled_jobs [max-age of days]`

Delete non-recurring scheduled jobs that were scheduled to run more than `max-age` days ago.

### `renaturalize`

`nautobot-server renaturalize [app_label.ModelName [app_label.ModelName ...]]`

Recalculate natural ordering values for the specified models.

This defaults to recalculating natural ordering on all models which have one or more fields of type `NaturalOrderingField`:

```no-highlight
nautobot-server renaturalize
```

Example output:

```no-highlight
Renaturalizing 21 models.
dcim.ConsolePort.name (_name)... 196
dcim.ConsoleServerPort.name (_name)... 0
dcim.PowerPort.name (_name)... 392
dcim.PowerOutlet.name (_name)... 0
dcim.Interface.name (_name)... 7161
dcim.FrontPort.name (_name)... 0
dcim.RearPort.name (_name)... 0
dcim.DeviceBay.name (_name)... 0
dcim.InventoryItem.name (_name)... 1
dcim.Device.name (_name)... 208
dcim.ConsolePortTemplate.name (_name)... 2
dcim.ConsoleServerPortTemplate.name (_name)... 0
dcim.PowerPortTemplate.name (_name)... 4
dcim.PowerOutletTemplate.name (_name)... 0
dcim.InterfaceTemplate.name (_name)... 221
dcim.FrontPortTemplate.name (_name)... 0
dcim.RearPortTemplate.name (_name)... 0
dcim.DeviceBayTemplate.name (_name)... 0
dcim.Rack.name (_name)... 156
virtualization.VMInterface.name (_name)... 0
Done.
```

You may optionally specify or more specific models (each prefixed with its app_label) to renaturalize:

```no-highlight
nautobot-server renaturalize dcim.Device
```

Example output:

```no-highlight
Renaturalizing 1 models.
dcim.Device.name (_name)... 208
Done.
```

### `runjob`

`nautobot-server runjob [job]`

Run a job (script, report) to validate or update data in Nautobot.

`--commit`  
Commit changes to DB (defaults to dry-run if unset). `--username` is mandatory if using this argument.

`--username <username>`  
User account to impersonate as the requester of this job.

```no-highlight
nautobot-server runjob --commit --username someuser local/example/MyJobWithNoVars
```

Note that there is presently no option to provide input parameters (`data`) for jobs via the CLI.

Please see the [guide on Jobs](../../platform-functionality/jobs/index.md) for more information on working with and running jobs.

### `send_installation_metrics`

+++ 1.6.0

`nautobot-server send_installation_metrics`

Send anonymized installation metrics to the Nautobot maintainers. This management command is called by [`post_upgrade`](#post_upgrade) and is not intended to be run manually.

If the [`INSTALLATION_METRICS_ENABLED`](../configuration/optional-settings.md#installation_metrics_enabled) setting is `True`, this command will send a list of all installed [apps](../../../development/apps/index.md) and their versions, as well as the currently installed Nautobot and Python versions, to the Nautobot maintainers. A randomized UUID will be generated and saved in the [`DEPLOYMENT_ID`](../configuration/optional-settings.md#deployment_id) setting to anonymously but uniquely identify this installation. The plugin names will be one-way hashed with SHA256 to further anonymize the data sent. This enables tracking the installation metrics of publicly released apps without disclosing the names of any private apps.

The following is an example of the data that is sent:

```py
{
    "deployment_id": "1de3dacf-f046-4a98-8d4a-17419080db79",
    "nautobot_version": "1.6.0b1",
    "python_version": "3.10.12",
    "installed_apps": {
        # "example_plugin" hashed by sha256
        "3ffee4622af3aad6f78257e3ae12da99ca21d71d099f67f4a2e19e464453bee7": "1.0.0"
    }
}
```

### `start`

`nautobot-server start`

Directly invoke uWSGI to start a Nautobot server suitable for production use. This command behaves exactly as uWSGI does, but allows us to maintain a single entrypoint into the Nautobot application.

!!! note
    uWSGI offers an overwhelming amount of command-line arguments that could not possibly be covered here. Please see the [official uWSGI Options guide](https://uwsgi-docs.readthedocs.io/en/latest/Options.html) for more information.

```no-highlight
nautobot-server start --ini ./uwsgi.ini
```

Example output:

```no-highlight
[uWSGI] getting INI configuration from ./uwsgi.ini
[uwsgi-static] added mapping for /static => /opt/nautobot/static
*** Starting uWSGI 2.0.19.1 (64bit) on [Thu Mar 11 21:13:22 2021] ***
compiled with version: 8.3.1 20190311 (Red Hat 8.3.1-3) on 23 September 2020 02:39:40
os: Linux-5.4.0-52-generic #57-Ubuntu SMP Thu Oct 15 10:57:00 UTC 2020
nodename: jathan-nautobot-testing
machine: x86_64
clock source: unix
pcre jit disabled
detected number of CPU cores: 48
current working directory: /opt/nautobot
detected binary path: /usr/bin/python3.8
your processes number limit is 256070
your memory page size is 4096 bytes
detected max file descriptor number: 1024
building mime-types dictionary from file /etc/mime.types...567 entry found
lock engine: pthread robust mutexes
thunder lock: disabled (you can enable it with --thunder-lock)
uwsgi socket 0 bound to TCP address 0.0.0.0:9191 fd 7
Python version: 3.8.5 (default, Jan 27 2021, 15:41:15)  [GCC 9.3.0]
--- Python VM already initialized ---
Python main interpreter initialized at 0x2573e30
python threads support enabled
your server socket listen backlog is limited to 1024 connections
your mercy for graceful operations on workers is 60 seconds
mapped 636432 bytes (621 KB) for 15 cores
*** Operational MODE: preforking+threaded ***
WSGI app 0 (mountpoint='') ready in 0 seconds on interpreter 0x2573e30 pid: 112153 (default app)
spawned uWSGI master process (pid: 112153)
spawned uWSGI worker 1 (pid: 112159, cores: 3)
spawned uWSGI worker 2 (pid: 112162, cores: 3)
spawned uWSGI worker 3 (pid: 112165, cores: 3)
spawned uWSGI worker 4 (pid: 112168, cores: 3)
spawned uWSGI worker 5 (pid: 112171, cores: 3)
```

Please see the guide on [Deploying Nautobot Services](../installation/services.md) for our recommended configuration for use with uWSGI.

### `startplugin`

`nautobot-server startplugin <name> [directory]`

Create a new plugin with `name`.

This command is similar to the django-admin [startapp](https://docs.djangoproject.com/en/stable/ref/django-admin/#startapp) command, but with a default template directory (`--template`) of `nautobot/core/templates/plugin_template`. This command assists with creating a basic file structure for beginning development of a new Nautobot plugin.

Without passing in the destination directory, `nautobot-server startplugin` will use your current directory and the `name` argument provided to create a new directory. We recommend providing a directory so that the plugin can be installed or published easily. Here is an example:

```no-highlight
mkdir -p ~/myplugin/myplugin
nautobot-server startplugin myplugin ~/myplugin/myplugin
```

Additional options such as `--name` or `--extension` can be found in the Django [documentation](https://docs.djangoproject.com/en/stable/ref/django-admin/#startapp).

### `trace_paths`

`nautobot-server trace_paths`

Generate any missing cable paths among all cable termination objects in Nautobot.

After upgrading the database or working with Cables, Circuits, or other related objects, there may be a need to rebuild cached cable paths.

`--force`  
Force recalculation of all existing cable paths.

`--no-input`  
Do not prompt user for any input/confirmation.

```no-highlight
nautobot-server trace_paths
```

Example output:

```no-highlight
Found no missing circuit termination paths; skipping
Found no missing console port paths; skipping
Found no missing console server port paths; skipping
Found no missing interface paths; skipping
Found no missing power feed paths; skipping
Found no missing power outlet paths; skipping
Found no missing power port paths; skipping
Finished.
```

!!! note
    This command is safe to run at any time. If it does detect any changes, it will exit cleanly.

### `webhook_receiver`

`nautobot-server webhook_receiver`

Start a simple listener to display received HTTP requests.

`--port PORT`  
Optional port number (default: `9000`)

`--no-headers`  
Hide HTTP request headers.

```no-highlight
nautobot-server webhook_receiver --port 9001 --no-headers
```

Example output:

```no-highlight
Listening on port http://localhost:9000. Stop with CONTROL-C.
```

Please see the guide on [Troubleshooting Webhooks](../../platform-functionality/webhook.md#troubleshooting) for more information.
