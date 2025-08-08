# Job Scheduling and Approvals

Oftentimes jobs will need to be run at a later date or periodically, or require approval from someone before they can be started. To this end, Nautobot offers facilities for scheduling and approving jobs.

## Job Scheduling

Jobs can be scheduled to be run immediately, at some point in the future, or at an interval.

Jobs can be scheduled through the UI or the API.

!!! warning
    A Job **must** be [enabled](./managing-jobs.md#enabling-and-disabling-jobs) and cannot have [has_sensitive_variables](../../../development/jobs/job-structure.md#class-metadata-attributes) set to `True` in order to be scheduled. If these requirements are not met, a warning banner will appear on the run Job view with the reason why Job Scheduling is not an option.

### Scheduling via the UI

The Job Scheduling views can be accessed via the navigation at `Jobs > Jobs`, selecting a Job as appropriate.

The UI allows you to select a scheduling type. Further fields will be displayed as appropriate for that schedule type.

If `Recurring custom` is chosen, you can schedule the recurrence in the `Crontab` field in [crontab](https://en.wikipedia.org/wiki/Cron#Overview) syntax.

If the job requires no approval, it will then be added to the queue of scheduled jobs or run immediately. Otherwise, the job will be added to the approval dashboard where it can be approved by users in the group(s) identified by the relevant approval workflow.

### Scheduling via the API

Jobs can also be scheduled via the REST API. The endpoint used for this is the regular job endpoint; specifying the optional `schedule` parameter will act just as scheduling in the UI.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/jobs/$JOB_ID/run/ \
--data '{"schedule": {"name": "test", "interval": "future", "start_time": "2030-01-01T01:00:00.000Z"}}'
```

For custom interval, a `crontab` parameter must be added.

`start_time` becomes optional when `interval` is set to `custom`.

`--data '{"schedule": {"name": "test", "interval": "custom", "start_time": "2030-01-01T01:00:00.000Z", "crontab": "*/15 * * * *"}}'`

## Job Approvals

Scheduled jobs that have `approval_required` set to `True` require approval from another user(s) before execution. This field is automatically set on the backend during job submission. If an `ApprovalWorkflowDefinition` is applicable to the specific `ScheduledJob`, an `ApprovalWorkflow` is created automatically and `approval_required` is set accordingly. For more details, see the [approval workflow documentation](../approval-workflow.md).

!!! warning
    Requiring approval for the execution of Job Hooks on a `JobHookReceiver` subclass is not currently supported. Support for approval of Job Hooks may be added in a future release.

Scheduled jobs can be approved or denied via the UI/API by user that has the `extras.change_approvalworkflowstage` and `extras.view_approvalworkflowstage` permission for the job in question, as well as the appropriate `extras.change_scheduledjob` permissions.

!!! note
    Scheduled jobs that are past their scheduled run date can still be approved, but the approver will be asked to confirm the operation.

### Approval via the UI

The queue of jobs that need approval can be found under `Approvals > Approval Dashboard`. This view displays all current task approval requests that require approval before they can be run. This includes those associated with `ScheduledJob`. To approve workflow with a scheduled job, click the button to approve. Please note that you will be asked for confirmation if a job is being approved that is past its scheduled date and time.

### Approval via the API

Approvals can also be given via the REST API. The endpoints to approve, deny, comment are found on the approval workflow stage endpoint under `approve`, `deny`, `comment` respectively. You can list pending or completed approvals using the `pending_approvals` filter. Additionally, you may include a comment in the request body when approving or denying a workflow.

#### Approve/Deny a Workflow

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{"comment": "Approved for deployment"}' \
http://nautobot/api/extras/approval-workflow-stages/$APPROVAL_WORKFLOW_STAGE_ID/approve
```

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{"comment": "Deny reason"}' \
http://nautobot/api/extras/approval-workflow-stages/$APPROVAL_WORKFLOW_STAGE_ID/deny
```

#### Comment on an Approval Workflow Stage

The `comment` endpoint allows a user to attach a non-approval comment to a specific stage within an approval workflow. This endpoint does not change the state of the stage, and is intended for adding informational messages, questions, or updates related to the approval process.

- This will attach a comment to the specified stage.
- The stage state will remain unchanged.
- The user must have the `change_approvalworkflowstage` permission.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{"comments": "Waiting for additional testing."}' \
http://nautobot/api/extras/approval-workflow-stages/$APPROVAL_WORKFLOW_STAGE_ID/comment
```

#### List Pending/Done Approvals

Retrieves a list of approval workflow stages filtered by their status relative to the current user using the `pending_approvals` query parameter on the standard list endpoint:

- `?pending_approvals=true` — Returns stages pending approval by the current user.

```no-highlight
curl -X GET \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/approval-workflow-stages/?pending_approvals=true
```

- `?pending_approvals=false` — Returns stages the current user has already approved/denied.

```no-highlight
curl -X GET \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/approval-workflow-stages/?pending_approvals=false
```

If the parameter is omitted, all stages are returned regardless of approval status.
