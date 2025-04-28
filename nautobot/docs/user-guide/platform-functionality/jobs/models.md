# Job Models

## Job

The Job data model provides a database representation of metadata describing a specific installed Job class. It also serves as an anchor point for other data models (JobResult and ScheduledJob in particular) to link against.

For any given Job record, most of its fields are populated initially from data defined in the source code of the corresponding job class. These fields may be explicitly overridden by editing the Job record via the Nautobot UI or REST API if desired. This is generally accomplished by setting a value for the desired field (e.g. `grouping`) and also setting the corresponding `override` flag (e.g. `grouping_override`) to `True`. If the `override` flag for a field is cleared (set back to `False`) then the corresponding flag will automatically revert to the original value defined by the Job class source code when the record is saved.

!!! note
    For metadata fields that are not explicitly overridden, changes in the job source code will be detected and reflected in the corresponding database records when `nautobot-server migrate` or `nautobot-server post_upgrade` is next run; changes are not detected "live" while the server is running.

    For jobs stored in Git repositories, re-syncing the Git repository will also refresh the Job records corresponding to this repository.

Records of this type store the following data as read-only (not modifiable via the UI or REST API):

* The source of the job (local installation, Git repository, App)
* The name of the module containing the Job class
* The name of the Job class
* Whether the job class is installed presently
* Whether the job is self-described as "read-only"
* Whether the job is a [Job Hook Receiver](../../../development/jobs/job-extensions.md#job-hook-receivers)
* Whether the job is a [Job Button Receiver](../../../development/jobs/job-extensions.md#job-button-receivers)

!!! note
    As presently implemented, after a job is uninstalled, when the database is next refreshed, the corresponding Job database record will *not* be deleted - only its `installed` flag will be set to False. This allows existing `JobResult` and `ScheduledJob` records to continue to reference the Job that they originated from.

    An administrator or sufficiently privileged user can manually delete uninstalled Job records if desired, though this will result in the foreign-key from the corresponding `JobResult` and `ScheduledJob` records (if any exist) becoming null. In any case, for tracking and auditing purposes, deleting a Job does **not** automatically delete its related `JobResult` and `ScheduledJob` records.

For any Job that is loaded into Nautobot, the Job must be enabled to run. See [Enabling Jobs for Running](./managing-jobs.md#enabling-jobs) for more details.

## Job Log Entry

Log messages from [Jobs](./index.md) are stored in as `JobLogEntry` objects. This allows more performant querying of log messages and even allows viewing of logs while the job is still running.

Records of this type store the following data:

* A reference to the `JobResult` object that created the log.
* Timestamps indicating when the log message was created.
* The logging level of the log message.
* The log message.
* If provided, the string format of the logged object and it's absolute url.

## Job Results

Nautobot provides a generic data model for storing and reporting the results of background tasks, such as the execution of custom jobs or the synchronization of data from a Git repository.

Records of this type store the following data:

* A reference to the job model that the task was associated with
* A reference to the user who initiated the task
* If initiated by a scheduled job, a reference to that scheduled job instance
* The arguments that were passed to the task (allowing for later queuing of the task for re-execution if desired)
* Timestamps indicating when the task was created and when it completed
* An overall status such as "pending", "running", "errored", or "completed".
* A block of structured data representing the return value from the `.run()` method (often rendered as JSON).

+/- 2.3.0
    The Additional Data tab has been removed, you can now find the data in the Advanced Tab.

## Understanding Job Class Paths

+/- 2.0.0
    The `class_path` concept has been simplified compared to Nautobot 1.x.

It is a key concept to understand the 2 `class_path` elements:

* `module_name`: which is the importable Python path to the job class definition (with `.` in place of `/` in the directory path, and not including the `.py` file extension, as per Python syntax standards).
    * For an App-provided job, this might be something like `my_app_name.jobs.my_job_filename` or `nautobot_golden_config.jobs`
    * For a locally installed job, this would match the file name, such as `my_job_filename`
    * For a Git-provided job, this includes the repository's defined `slug`, such as `my_repository.jobs.my_job_filename`
* `JobClassName`: which is the name of the class inheriting from `nautobot.extras.jobs.Job` contained in the above file.

The `class_path` is often represented as a string in the format of `<module_name>.<JobClassName>`, such as `example.MyJobWithNoVars` or `nautobot_golden_config.jobs.BackupJob`. Understanding the definitions of these elements will be important in running jobs programmatically.

+/- 2.0.0
    The Job database model `name` field is now enforced to be globally unique and so is also an option for uniquely identifying Job records.
