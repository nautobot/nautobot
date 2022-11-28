# Jobs

+++ 1.3.0

The Job data model provides a database representation of metadata describing a specific installed Job. It also serves as an anchor point for other data models (JobResult and ScheduledJob in particular) to link against.

For any given Job record, most of its fields are populated initially from data defined in the source code of the corresponding job class. These fields may be explicitly overridden by editing the Job record via the Nautobot UI or REST API if desired. This is generally accomplished by setting a value for the desired field (e.g. `grouping`) and also setting the corresponding `override` flag (e.g. `grouping_override`) to `True`. If the `override` flag for a field is cleared (set back to `False`) then the corresponding flag will automatically revert to the original value defined by the Job class source code when the record is saved.

!!! note
    For metadata fields that are not explicitly overridden, changes in the job source code will be detected and reflected in the corresponding database records when `nautobot-server migrate` or `nautobot-server post_upgrade` is next run; changes are not detected "live" while the server is running.

    For jobs stored in Git repositories, re-syncing the Git repository will also refresh the Job records corresponding to this repository.

Records of this type store the following data as read-only (not modifiable via the UI or REST API):

* The source of the job (local installation, Git repository, plugin)
* The name of the module containing the Job
* The name of the Job class
* Whether the job is installed presently
* Whether the job is a [Job Hook Receiver](jobhook.md#job-hook-receivers)

!!! note
    As presently implemented, after a job is uninstalled, when the database is next refreshed, the corresponding Job database record will *not* be deleted - only its `installed` flag will be set to False. This allows existing `JobResult` and `ScheduledJob` records to continue to reference the Job that they originated from.

    An administrator or sufficiently privileged user can manually delete uninstalled Job records if desired, though this will result in the foreign-key from the corresponding `JobResult` and `ScheduledJob` records (if any exist) becoming null. In any case, for tracking and auditing purposes, deleting a Job does **not** automatically delete its related `JobResult` and `ScheduledJob` records.
