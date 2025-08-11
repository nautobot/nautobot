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

You can also provide a specific subcommand to list available arguments for that command, for example:

```no-highlight
nautobot-server help migrate
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
    DynamicGroup instance with name `Test DP 4` and content type `example_app | another example model` has an invalid filter `site`

>>> Please fix the broken filters stated above according to the documentation available at:
https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1/#ui-graphql-and-rest-api-filter-changes
```

If your filter data is valid, you should see a success message at the end of the output:

```no-highlight
>>> Auditing existing DynamicGroup data for invalid filters ...


>>> All DynamicGroup filters are validated successfully!
```

### `audit_graphql_queries`

`nautobot-server audit_graphql_queries`

After upgrading your Nautobot instance from v1.x to v2.x, breaking changes made to model filter fields will, in some cases, invalidate existing `GraphQLQuery` instances' query data. `nautobot-server audit_graphql_queries` is a helper command to assist you in cleaning up `GraphQLQuery` query data by spotting invalid query filters and outputting them to the command line interface.

```no-highlight
nautobot-server audit_graphql_queries
```

Example output:

If you have invalid query data in your `GraphQLQuery` instances, the following output should be expected:

```no-highlight
>>> Auditing existing GraphQLQuery data for invalid queries ...

>>> The following GraphQLQuery instances have invalid query data:

    GraphQLQuery with name `Wrong Query` has invalid query data: [{'message': 'Unknown argument "site" on field "racks" of type "Query".', 'locations': [{'line': 2, 'column': 19}]}]
    GraphQLQuery with name `Wrong Query 1` has invalid query data: [{'message': 'Unknown argument "site" on field "device" of type "Query".', 'locations': [{'line': 2, 'column': 14}]}]
    GraphQLQuery with name `Wrong Query 2` has invalid query data: [{'message': "{'location': ['Select a valid choice. Location 01 is not one of the available choices.']}", 'locations': [{'line': 5, 'column': 8}], 'path': ['devices']}]

>>> Please fix the outdated query data stated above according to the documentation available at:
https://docs.nautobot.com/projects/core/en/stable/user-guide/administration/upgrading/from-v1/upgrading-from-nautobot-v1/#ui-graphql-and-rest-api-filter-changes
```

If your query data is valid, you should see a success message at the end of the output:

```no-highlight
>>> Auditing existing GraphQLQuery data for invalid queries ...

>>> All GraphQLQuery queries are validated successfully!
```

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

Collect static files into [`STATIC_ROOT`](../configuration/settings.md#static_root).

```no-highlight
nautobot-server collectstatic
```

Output:

```no-highlight
965 static files copied to '/opt/nautobot/static'.
```

!!! note
    This is a built-in Django command. Please see the [official documentation on `collectstatic`](https://docs.djangoproject.com/en/stable/ref/django-admin/#collectstatic) for more information.

### `check_job_approval_status`

`nautobot-server check_job_approval_status`

Checks for scheduled jobs and jobs that require approval.

```no-highlight
nautobot-server check_job_approval_status
```

Output (when failed):
```no-highlight
nautobot.core.management.commands.check_job_approval_status.ApprovalRequiredScheduledJobsError: These need to be approved (and run) or denied before upgrading to Nautobot v3, as the introduction of the approval workflows feature means that future scheduled-job approvals will be handled differently.
Refer to the documentation: https://docs.nautobot.com/projects/core/en/stable/user-guide/platform-functionality/jobs/job-scheduling-and-approvals/#approval-via-the-ui
Below is a list of affected scheduled jobs:
    - ID: 0f8a0670-459b-430f-8c5e-a631888509d4, Name: test2
```

Output (with warning):
```no-highlight
Following jobs still have `approval_required=True`.
These jobs will no longer trigger approval automatically.
After upgrading to Nautobot 3.x, you should add an approval workflow definition(s) covering these jobs.
Refer to the documentation: https://docs.nautobot.com/projects/core/en/next/user-guide/platform-functionality/approval-workflow/
Affected jobs (Names):
    - ExampleDryRunJob
    - Example Job of Everything
    - Export Object List
```

Output (when pass):
```no-highlight
No approval_required jobs or scheduled jobs found.
```
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

!!! warning
    - We do not recommend using `--natural-primary` as this can result in inconsistent or incorrect data for data models that use GenericForeignKeys, such as `Cable`, `Note`, `ObjectChange`, and `Tag`.
    - We also do not recommend using `--natural-foreign` as it can potentially result in errors if any data models incorrectly implement their `natural_key()` and/or `get_by_natural_key()` API methods.
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

`nautobot-server fix_custom_fields [app_label.ModelName [app_label.ModelName ...]]`

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

You may optionally specify one or more specific models (each prefixed with its app_label) to fix:

```no-highlight
nautobot-server fix_custom_fields circuits.Circuit dcim.Location
```

Example output:

```no-highlight
Processing ContentType circuits | circuit
Processing ContentType dcim | location
```

### `generate_secret_key`

`nautobot-server generate_secret_key`

Generates a new [`SECRET_KEY`](../configuration/settings.md#secret_key) that can be used in your `nautobot_config.py`:

```no-highlight
nautobot-server generate_secret_key
```

Output:

```no-highlight
e!j=vrlhz-!wl8p_3+q5s5cph29nzj$xm81eap-!&n!_9^du09
```

### `generate_test_data`

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

Please see the [health-checks documentation](../guides/health-checks.md) for more information.

### `init`

`nautobot-server init [--disable-installation-metrics] [config_path]`

Generates a new configuration with all of the default settings provided for you, and will also generate a unique [`SECRET_KEY`](../configuration/settings.md#secret_key).

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
  Applying ipam.0050_vlangroup_range...                          OK    (   0.1s)
    Affected ipam.vlangroup                               20 rows  0.003s/record
  Applying dcim.0063_interfacevdcassignment_virtualdevicecont... OK    (   0.2s)
    Affected dcim.interfacevdcassignment                   0 rows
    Affected dcim.virtualdevicecontext                     0 rows
  Applying dcim.0064_virtualdevicecontext_status_data_migrati...
... (truncated for brevity of documentation) ...
```

!!! note
    This is a built-in Django command, although Nautobot has enhanced it to provide additional output when run. Please see the [official documentation on `migrate`](https://docs.djangoproject.com/en/stable/ref/django-admin/#migrate) for more information.

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
from constance.models import Constance
from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Group, Permission
...
# Shell Plus Django Imports
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth import get_user_model
...
# Django version 4.2.15
# Nautobot version 2.3.3b1
...
Python 3.12.6 (main, Sep 12 2024, 21:12:08) [GCC 12.2.0] on linux
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

- `migrate`
- `trace_paths`
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
    Added `build_ui` to this command's default behavior.

+/- 2.0.3
    Changed the `--build_ui` flag's value to be False by default.

--- 2.1.1
    Removed the `--build_ui` flag.

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

`nautobot-server refresh_dynamic_group_member_caches`

Refresh the cached members of all Dynamic Groups. This can also be achieved by running the `Refresh Dynamic Group Caches` system Job.

### `refresh_content_type_caches`

`nautobot-server refresh_content_type_caches`

Refresh the cached ContentType object property available via `Model._content_type_cached`. If content types are added or removed, this command will update the cache to reflect the current state of the database, but should already be done through the `post_upgrade` command.

### `remove_stale_scheduled_jobs`

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

`nautobot-server runjob --username <username> [--local] [--data <data>] <job>`

Run a job (script, report) to validate or update data in Nautobot. The Job name must be in the Python module form: `<module_name>.<JobClassName>`. You can find this under the Job's detail view on the "Class Path" row.

`--username <username>`  
User account to impersonate as the requester of this job.

```no-highlight
nautobot-server runjob --username someuser example_app.jobs.MyJobWithNoVars
```

`--local`
Run the job on the local system and not on a worker.

`--data <data>`
JSON string that populates the `data` variable of the job.

```no-highlight
nautobot-server runjob --username someuser --local --data '{"my_boolvar": false}' example_app.jobs.MyJobWithVars
```

Please see the [guide on Jobs](../../platform-functionality/jobs/index.md) for more information on working with and running jobs.

### `send_installation_metrics`

`nautobot-server send_installation_metrics`

Send anonymized installation metrics to the Nautobot maintainers. This management command is called by [`post_upgrade`](#post_upgrade) and is not intended to be run manually.

If the [`INSTALLATION_METRICS_ENABLED`](../configuration/settings.md#installation_metrics_enabled) setting is `True`, this command will send a list of all installed [Apps](../../../development/apps/index.md) and their versions, as well as the currently installed Nautobot and Python versions, to the Nautobot maintainers. A randomized UUID will be generated and saved in the [`DEPLOYMENT_ID`](../configuration/settings.md#deployment_id) setting to anonymously but uniquely identify this installation. The App names will be one-way hashed with SHA256 to further anonymize the data sent. This enables tracking the installation metrics of publicly released apps without disclosing the names of any private apps.

The following is an example of the data that is sent:

```py
{
    "deployment_id": "1de3dacf-f046-4a98-8d4a-17419080db79",
    "nautobot_version": "2.1.2",
    "python_version": "3.10.12",
    "installed_apps": {
        # "example_app" hashed by sha256
        "ded1fb19a53a47aa4fe26b72b4ab9297b631e4d4f852b03b3788d5dbc292ae8d": "1.0.0"
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
    This command is safe to run at any time. If it does not detect any changes, it will exit cleanly.

### `validate_models`

`nautobot-server validate_models`

Validate all instances of a given model(s) by running a 'full_clean()' or 'validated_save()' on each object.

!!! warning
    Depending on the number of records in your database, this may take a long time to run.

```no-highlight
nautobot-server validate_models
```

Example output:

```no-highlight
Validating 171 models.
auth.Permission
circuits.ProviderNetwork
circuits.Provider
circuits.CircuitType
circuits.Circuit
circuits.CircuitTermination
dcim.Interface
dcim.Manufacturer
dcim.DeviceFamily
dcim.DeviceTypeToSoftwareImageFile
dcim.DeviceType
dcim.Platform
<omitted for brevity>
```

You can validate a specific subset of models by providing a space separated list of models as shown here:

```no-highlight
nautobot-server validate_models dcim.Manufacturer dcim.Device
```

```no-highlight
Validating 2 models.
dcim.Manufacturer
dcim.Device
```

`--save`  
Run `validated_save()` instead of `full_clean()` for slower but more thorough data validation.

### `version`

`nautobot-server version`

Report the Nautobot version and Django version, as well as the current configuration file in use.

```no-highlight
nautobot-server version
```

Example output:

```no-highlight
Nautobot version: 2.2.0a1
Django version: 3.2.24
Configuration file: /opt/nautobot/nautobot_config.py
```

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

Please see the guide on [Troubleshooting Webhooks](../../platform-functionality/webhook.md#troubleshooting-webhooks) for more information.
