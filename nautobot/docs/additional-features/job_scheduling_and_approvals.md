# Job Scheduling and Approvals

Oftentimes jobs will need to be run at a later date or periodically, or require approval from someone before they can be started. To this end, Nautobot offers facilities for scheduling and approving jobs.

## Job Scheduling

Jobs can be scheduled to be run immediately, at some point in the future, or at an interval.

Jobs can be scheduled through the UI or the API.

### Scheduling via the UI

The Job Scheduling views can be accessed via the navigation at `Extensibility > Jobs`, selecting a Job as appropriate.

The UI allows you to select a scheduling type. Further fields will be displayed as appropriate for that schedule type.

If the job requires no approval, it will then be added to the queue of scheduled jobs or run immediately. Otherwise, the job will be added to the approval quere where it can be approved by other users.

### Scheduling via the API

Jobs can also be scheduled via the REST API. The endpoint used for this is the regular job endpoint, filling the `schedule` parameter will act just as scheduling in the UI.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; indent=4" \
http://nautobot/api/extras/jobs/local/example/MyJobWithNoVars/run/ \
--data '{"schedule": {"name": "test", "interval": "future", "start_time": "2030-01-01T01:00:00.000Z"}}'
```

## Job Approvals

Jobs that have `approval_required` set to `True` on their `Meta` object require another user to approve a scheduled job.

Jobs can be approved via the UI and API by any user that has the rights to run a job.

!!! note
    Jobs that are past their scheduled run date can still be approved, but the approver will be asked to confirm the operation.

## Approval via the UI

The queue of jobs that need approval can be found under `Extensibility > Job Approval Queue`. There, any job that needs approval before it gets run is listed. To approve a job, select it and click the button to approve. Please note that you will be  asked for confirmation if a job is being approved that is past its scheduled datetime.

## Approval via the API

Approvals can also be given via the REST API. The endpoints to approve, deny, and dry run a scheduled job are found on the scheduleb job endpoint under `approve`, `deny`, and `dry-run`, respectively.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; indent=4" \
http://nautobot/api/extras/scheduled-jobs/$JOB_ID/approve?force=true
```

The approval endpoint additionally provides a `force` query parameter that needs to be set if a job is past its scheduled datetime. This mimics the confirmation dialog in the UI.
