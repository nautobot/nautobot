# Managing Jobs

_A guide for administrators and power users who need to enable, configure, or retire Jobs after they've been installed._

From this point forward we assume the Job *code* is already present in Nautobot.  
The sections below walk through the operational tasks you perform **after** installation—enabling or hiding a job, overriding its metadata, steering it to Celery or Kubernetes queues, and eventually deleting or archiving the record.  
Required permissions for each action are listed at the end of the page.

!!! tip "Job record vs Job class"
    A **Job class** is the Python code on disk; a **Job record** is the database row that stores its metadata and enabled state.

    Editing code updates the class immediately, but the record keeps the **previous values** until you refresh it (e.g., with `nautobot-server post_upgrade` or a Git repo resync).  
    Conversely, overriding a field in the record never changes the source code—clear the override flag to revert to whatever the class defines.

## Enabling and disabling Jobs

When a new Job record is created for a newly discovered Job class, it defaults to `enabled = False`, which prevents the Job from being run unintentionally. This provides security and oversight for new installations.

!!! important
    When upgrading from a Nautobot release before 1.3 to Nautobot 1.3.0 or later, Jobs previously run or scheduled will automatically have their records set to `enabled = True`.

To enable or disable a Job:

1. Navigate to **Jobs > Jobs**.
2. Select a Job from the list.
3. Click the **Edit** button.
4. In the **Job** section, toggle the **Enabled** checkbox as needed.
5. Click **Update**.

## Overriding Job metadata

Sometimes you need to change how a Job appears or behaves without touching its source code—for example, hiding a vendor‑specific Job from general users or increasing the timeout for a long‑running audit Job. You can accomplish this by ***overriding*** metadata attributes directly on the Job record.

### Editable attributes  

| Attribute | Purpose | Typical use‑case |
|-----------|---------|------------------|
| **grouping** | UI category the Job is listed under. | Organize third-party Jobs into "Compliance" or "Local Automations." |
| **name** | Display name in the Jobs list. | Rename technical Job names to user-friendly descriptions. |
| **description** | Markdown or HTML description shown on Job detail page. | Add instructions or documentation links. |
| **dryrun_default** | Default state of **Dry-Run** checkbox. | Audit or reporting Jobs that rarely commit changes. |
| **has_sensitive_variables** | Avoid storing sensitive input data. | Jobs that accept credentials or sensitive data. |
| **hidden** | Hide Job from the main Job listings. | Helper Jobs executed only by buttons or hooks. |
| **soft_time_limit / time_limit** | Override Celery task soft/hard kill timeouts (in seconds). | Long-running imports or external API syncs. |
| **job_queues** | Restrict Job execution to specific Job Queues. | Route intensive Jobs to isolated or Kubernetes workers. |
| **is_singleton** | Prevent multiple simultaneous executions. | Inventory synchronization Jobs. |

### How to set or clear an override  

1. Navigate to **Jobs > Jobs** and select the Job.
2. Click **Edit**.
3. Tick the **`*_override`** box beside the field.
4. Set the desired new value, then click **Update**.
5. A **blue pencil icon** indicates overridden fields in the Jobs list.

To revert to the original Job class value, clear the override checkbox and save. On next refresh, the original value defined in the Job class will reapply.

!!! note
    Overrides only apply in the database and never update Job source code.

### Best‑practice tips  

- **Combine edits:** If enabling a Job, also set metadata overrides (e.g., grouping) simultaneously for cleaner change history.
- **Document changes:** Clearly document why overrides are set in the description field to help future administrators.
- **Use queues:** If Jobs consistently exceed default time limits, consider separate queues instead of global limit increases.
- **Periodic audits:** After major upgrades, review overridden Jobs (blue pencil icons) and consider removing unnecessary overrides.
- **Limit overrides:** If multiple overrides accumulate, consider adjusting defaults directly in Job code instead.

!!! note "Job Queues (v2.4+)"
    As of Nautobot v2.4, the `task_queues` attribute is deprecated. Use `job_queues`, which references [Job Queues](./jobqueue.md). Queues appear sorted alphabetically.

## Assigning Job queues (Celery or Kubernetes)

Jobs in Nautobot can execute on **Celery** (default) or **Kubernetes** backends. You manage routing with **Job Queues**.

Each Job has two queue configuration options:

- **Default Job Queue:** Used when no queue is specified at runtime.
- **Eligible Queues:** Limits queue selection options for users when running the Job.

Common scenarios:

- **Default Celery worker:** Leave **Eligible Queues** blank to always use default Celery.
- **Kubernetes execution:** Create a Kubernetes Job Queue (**Jobs > Job Queues**), add it to **Eligible Queues**, and optionally set as default.
- **Dedicated resource queue:** Create a dedicated Celery queue (`high-resource-jobs`) for CPU-intensive tasks, then assign these Jobs to that queue.

!!! tip
    Refer to [Job Queues](./jobqueue.md) and [Kubernetes Job Support](./kubernetes-job-support.md) for detailed queue setup instructions.

## Viewing installed vs uninstalled Jobs

By default, Nautobot shows only installed Jobs (with corresponding Python code present).

To view uninstalled Jobs (Job records remaining without corresponding Python code):

1. Go to **Jobs > Jobs**.
2. Click **Filter**.
3. Set **Installed** to **No**, then click **Apply**.

Uninstalled Jobs appear greyed-out and cannot run or schedule executions, but historical data (`JobResult`, `ScheduledJob`) is retained for audit.

## Deleting or archiving Jobs

Use this procedure when permanently retiring a Job:

- **Delete Job record:** Removes Job from Nautobot UI and API. Associated Job Buttons, Hooks, and Scheduled Jobs are automatically disabled. Code files are unaffected.
- **Remove code only (keep record):** The Job appears as `installed = False` (see above) but remains in the database.

### Impact on JobResults and ScheduledJobs

- Existing **JobResults** and **ScheduledJobs** retain historical data but their foreign-key references to the Job become `NULL`.
- Reinstalling the same Job does not automatically reconnect historical data.

### Approval Workflow

ScheduledJob can have approval workflow that requires additional user approval before each execution. To protect jobs that make massive production changes. For more information on approvals, [please refer to the section on scheduling and approvals](job-scheduling-and-approvals.md#job-approvals).

### Recommended deletion steps

1. **Disable** the Job.
2. Verify no active ScheduledJobs reference it (**ScheduledJobs > Filter by Job name**).
3. Delete the Job (**Actions > Delete**).
4. Separately remove code files or Git commits.
5. Optionally, remove orphaned JobResults via **Admin > Job results**.

## Permissions checklist

| Task                      | Required permission(s)                                   |
|---------------------------|----------------------------------------------------------|
| Enable/Disable Job        | `extras.change_job`                                      |
| Override metadata         | `extras.change_job`                                      |
| Assign Job Queues         | `extras.change_job` + permissions on specific Job Queues |
| Delete Job                | `extras.delete_job`                                      |
| Run Job                   | `extras.run_job`                                         |
| Approve scheduled Job     | `extras.change_approvalworkflowstage` + `extras.view_approvalworkflowstage` + (`extras.change_scheduledjob` or `extras.delete_scheduledjob`) |
