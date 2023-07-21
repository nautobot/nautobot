# Jobs

Jobs are a way for users to execute custom logic on demand from within the Nautobot UI. Jobs can interact directly with Nautobot data to accomplish various data creation, modification, and validation tasks, such as:

* Automatically populate new devices and cables in preparation for a new location deployment
* Create a range of new reserved prefixes or IP addresses
* Fetch data from an external source and import it to Nautobot
* Check and report whether all top-of-rack switches have a console connection
* Check and report whether every router has a loopback interface with an assigned IP address
* Check and report whether all IP addresses have a parent prefix

...and so on. Jobs are Python code and exist outside of the official Nautobot code base, so they can be updated and changed without interfering with the core Nautobot installation. And because they're completely customizable, there's practically no limit to what a job can accomplish.

+/- 2.0.0
    Backwards compatibility with NetBox scripts and reports has been removed. This includes removal of automatic calls to the `post_run()` and `test_*()` methods.

!!! note
    Jobs unify and supersede the functionality previously provided in NetBox by "custom scripts" and "reports". User input is supported via [job variables](../../../development/jobs/index.md#variables).

## Managing Jobs

As of Nautobot 1.3, each Job class installed in Nautobot is represented by a corresponding Job data record in the Nautobot database. These data records are refreshed when the `nautobot-server migrate` or `nautobot-server post_upgrade` command is run, or (for Jobs from a Git repository) when a Git repository is enabled or re-synced in Nautobot. These data records make it possible for an administrative user (or other user with appropriate access privileges) to exert a level of administrative control over the Jobs created and updated by Job authors.

### Enabling Jobs for Running

When a new Job record is created for a newly discovered Job class, it defaults to `enabled = False`, which prevents the Job from being run by any user. This is intended to provide a level of security and oversight regarding the installation of new Jobs into Nautobot.

!!! important
    One exception to this default is when upgrading from a Nautobot release before 1.3 to Nautobot 1.3.0 or later. In this case, at the time of the upgrade, any Job class that shows evidence of having been run or scheduled under the older Nautobot version (that is, there is at least one JobResult and/or ScheduledJob record that references this Job class) will result in the creation of a Job database record with `enabled = True`. The reasoning for this feature is the assertion that because the Job has been run or scheduled previously, it has presumably already undergone appropriate review at that time, and so it should remain possible to run it as it was possible before the upgrade.

An administrator or user with `extras.change_job` permission can edit the Job to change it to `enabled = True`, permitting running of the Job, when they have completed any appropriate review of the new Job to ensure that it meets their standards. Similarly, an obsolete or no-longer-used Job can be prevented from inadvertent execution by changing it back to `enabled = False`.

 By default when a Job is installed into Nautobot it is installed in a disabled state. In order to enable a Job:

* Navigate to Jobs > Jobs menu
* Select a job that has been installed
* Select **Edit** button
* In the second section titled **Job**, select the **Enabled** checkbox
* Select **Update** button at the bottom

#### Enabling Job Hooks

 Job hooks are enabled in a similar fashion, but by using the **default** filters when navigating to the Jobs page the Job Hooks will not be visible. To enable job hooks:

* Navigate to Jobs > Jobs menu
* Select the **Filter** button to bring up the Filter Jobs context
* Look for **Is job hook receiver** and change the drop down to **Yes**
* Select **Apply** button
* Select a job that has been installed
* Select **Edit** button
* In the second section titled **Job**, select the **Enabled** checkbox
* Select **Update** button at the bottom

### Overriding Metadata

An administrator or user with `extras.change_job` permission can also edit a Job database record to optionally override any or all of the following metadata attributes defined by the Job module or class:

* `grouping`
* `name`
* `description`
* `approval_required`
* `dryrun_default`
* `has_sensitive_variables`
* `hidden`
* `soft_time_limit`
* `time_limit`
* `task_queues`

This is done by setting the corresponding "override" flag (`grouping_override`, `name_override`, etc.) to `True` then providing a new value for the attribute in question. An overridden attribute will remain set to its overridden value even if the underlying Job class definition changes and `nautobot-server <migrate|post_upgrade>` gets run again. Conversely, clearing the "override" flag for an attribute and saving the database record will revert the attribute to the underlying value defined within the Job class source code.

### Deleting Jobs

When a previously installed Job class is removed, after running `nautobot-server <migrate|post_upgrade>` or refreshing the providing Git repository, the Job database record will *not* be automatically deleted, but *will* be flagged as `installed = False` and can no longer be run or scheduled.

An administrator or user with `extras.delete_job` permissions *may* delete such a Job database record if desired, but be aware that doing so will result in any existing JobResult or ScheduledJob records that originated from this Job losing their association to the Job; this association will not be automatically restored even if the Job is later reinstalled or reintroduced.

## Running Jobs

!!! note
    To run any job, a user must be assigned the `extras.run_job` permission. This is achieved by assigning the user (or group) a permission on the `extras > job` object and specifying the `run` action in the admin UI as shown below.

    Similarly, to [approve a job request by another user](./job-scheduling-and-approvals.md), a user must be assigned the `extras.approve_job` permission via the same process. Job approvers also need the `extras.change_scheduledjob` and/or `extras.delete_scheduledjob` permissions as job approvals are implemented via the `ScheduledJob` data model.

    ![Adding the run action to a permission](../../../media/admin_ui_run_permission.png)

### Jobs and `class_path`

+/- 2.0.0
    The `class_path` concept has been simplified compared to Nautobot 1.x.

It is a key concept to understand the 2 `class_path` elements:

* `module_name`: which is the importable Python path to the job definition (with `.` in place of `/` in the directory path, and not including the `.py` file extension, as per Python syntax standards).
    * For a plugin-provided job, this might be something like `my_plugin_name.jobs.my_job_filename` or `nautobot_golden_config.jobs`
    * For a locally installed job, this would match the file name, such as `my_job_filename`
    * For a Git-provided job, this includes the repository's defined `slug`, such as `my_repository.jobs.my_job_filename`
* `JobClassName`: which is the name of the class inheriting from `nautobot.extras.jobs.Job` contained in the above file.

The `class_path` is often represented as a string in the format of `<module_name>.<JobClassName>`, such as `example.MyJobWithNoVars` or `nautobot_golden_config.jobs.BackupJob`. Understanding the definitions of these elements will be important in running jobs programmatically.

+/- 1.3.0
    With the addition of Job database models, it is now generally possible and preferable to refer to a job by its UUID primary key, similar to other Nautobot database models, rather than its `class_path`.

### Via the Web UI

Jobs can be run via the web UI by navigating to the job, completing any required form data (if any), and clicking the "Run Job" button.

Once a job has been run, the latest [`JobResult`](./models.md#job-results) for that job will be summarized in the job list view.

### Via the API

--- 2.0.0
    The `commit` parameter was removed. All job input should be provided via the `data` parameter.

To run a job via the REST API, issue a POST request to the job's endpoint `/api/extras/jobs/<uuid>/run/`. You can optionally provide JSON data to specify any required user input `data`, optional `task_queue`, and/or provide optional scheduling information as described in [the section on scheduling and approvals](./job-scheduling-and-approvals.md).

For example, to run a job with no user inputs:

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/jobs/$JOB_ID/run/
```

Or to run a job that expects user inputs:

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/jobs/$JOB_ID/run/ \
--data '{"data": {"string_variable": "somevalue", "integer_variable": 123}}'
```

When providing input data, it is possible to specify complex values contained in `ObjectVar`s, `MultiObjectVar`s, and `IPAddressVar`s.

* `ObjectVar`s can be specified by either using their primary key directly as the value, or as a dictionary containing a more complicated query that gets passed into the Django ORM as keyword arguments.
* `MultiObjectVar`s can be specified as a list of primary keys.
* `IPAddressVar`s can be provided as strings in CIDR notation.

#### Jobs with Files

To run a job that contains `FileVar` inputs via the REST API, you must use `multipart/form-data` content type requests instead of `application/json`. This also requires a slightly different request payload than the example above. The `task_queue` and `schedule` data are flattened and prefixed with underscore to differentiate them from job-specific data. Job specific data is also flattened and not located under the top-level `data` dictionary key.

An example of running a job with both `FileVar` (named `myfile`) and `StringVar` (named `interval`) input:

```no-highlight
curl -X POST \
-H 'Authorization: Token $TOKEN' \
-H 'Content-Type: multipart/form-data' \
-H "Accept: application/json; version=1.3; indent=4" \
'http://nautobot/api/extras/jobs/$JOB_ID/run/' \
-F '_schedule_interval="immediately"' \
-F '_schedule_start_time="2022-10-18T17:31:23.698Z"' \
-F 'interval="3"' \
-F 'myfile=@"/path/to/my/file.txt"' \
```

### Via the CLI

Jobs can be run from the CLI by invoking the management command:

```no-highlight
nautobot-server runjob [--username <username>] [--local] [--data <data>] <class_path>
```

!!! note
    [See above](#jobs-and-class_path) for `class_path` definitions.

+++ 1.3.10
    The `--data` and `--local` parameters were added.

    The `--data` parameter must be a JSON string, e.g. `--data='{"string_variable": "somevalue", "integer_variable": 123}'`

Using the same example shown in the API:

```no-highlight
nautobot-server runjob --username myusername example.MyJobWithNoVars
```

!!! warning
    The `--username <username>` must be supplied to specify the user that will be identified as the requester of the job.

    Note that `nautobot-server` commands, like all management commands and other direct interactions with the Django database, are not gated by the usual Nautobot user authentication flow. It is possible to specify any existing `--username` with the `nautobot-server runjob` command in order to impersonate any defined user in Nautobot. Use this power wisely and be cautious who you allow to access it.
