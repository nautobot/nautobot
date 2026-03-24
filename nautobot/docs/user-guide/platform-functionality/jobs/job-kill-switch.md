# Job Kill Switch

+++ 3.2.0

The Job Kill Switch gives operators the ability to terminate running or pending jobs and clean up stuck job records. It provides two distinct actions — **Terminate** and **Reap** — along with an **Active Jobs** view for quick visibility into what's currently running.

## Overview

When a job is running longer than expected, stuck in a pending state, or needs to be stopped for any reason, the kill switch provides a controlled way to cancel it. The feature records that the job was deliberately killed (as opposed to failing on its own) and maintains a full audit trail via the `JobKillRequest` model.

!!! note
    Nautobot uses Celery's state machine for job statuses. When a job is terminated or reaped, its status is set to `REVOKED` (Celery's equivalent of "cancelled"). This status is already part of Celery's `READY_STATES`, so terminated jobs are treated as complete throughout the system.

## Terminating a Job

The **Terminate Job** action immediately sends a kill signal to the underlying Celery worker. It does not check whether the worker is still alive — it simply fires the revoke command and marks the job as cancelled.

The button can be seen from the Job Result List action button or detail view button.

## Reaping a Job

The **Reap Job** action is a more cautious alternative to termination. Before cancelling the job, it checks whether the underlying Celery worker is still alive. If the worker is confirmed dead, the job is moved to `REVOKED`. If the worker is still active, the job is skipped.

## Terminate vs Reap

| | Terminate | Reap |
|---|---|---|
| Worker liveness check | No | Yes |
| Celery `revoke()` call | Yes | No |
| Use case | Kill a job immediately | Clean up a confirmed-dead job |
| `kill_type` | `terminate` | `reap` |
| `killed_by` | Current user | `null` |

## Active Jobs View

The Active Jobs view is a convenience page that shows all `JobResult` records currently in `STARTED` or `PENDING` status. It provides a quick overview of what's running or queued without needing to filter the full Job Results list.

Navigate to **Jobs > Active Jobs** to access it.

The view includes the same Terminate and Reap action buttons as the main Job Results list, so you can act on jobs directly from this page.

## Retry Behavior

Both Terminate and Reap support retrying after a previous failed attempt. If a `JobKillRequest` already exists for a job (e.g., from a failed termination), the existing record is updated in place — its status resets to `pending`, the error detail is cleared, and the action is re-attempted. You never need to manually clean up a failed kill request before trying again.

## Job Kill Request Records

Every termination or reap action creates a `JobKillRequest` record that tracks the lifecycle of the kill attempt. These records are available for operational debugging and observability.

Navigate to **Jobs > Job Kill Requests** to view all kill request records, or view them via the REST API at `/api/extras/job-kill-requests/`.

### Fields

| Field | Description |
|---|---|
| Job Result | The job that was targeted for termination. |
| Requested By | The user who initiated the action (null for reap actions). |
| Requested At | When the kill request was created. |
| Acknowledged At | When the termination was confirmed attempted. |
| Status | `pending`, `acknowledged`, or `failed`. |
| Error Detail | If the kill attempt failed, the error message. |

!!! note
    Job Kill Request records are read-only. They cannot be created, edited, or deleted through the UI — they are managed automatically by the terminate and reap actions.

## JobResult Kill Switch Fields

When a job is terminated or reaped, three additional fields are populated on the `JobResult`:

| Field | Description |
|---|---|
| `kill_type` | `terminate` (Terminate action) or `reap` (Reap action). |
| `killed_by` | The user who clicked Terminate, or null for reap actions. |
| `killed_at` | Timestamp of when the kill was initiated. |

These fields appear in the Job Result detail view summary panel and as columns in the Job Result list view table. They are null for jobs that complete or fail normally.

The Job Result list view also includes a `Worker` column showing the Celery worker hostname (e.g. `celery@worker-01`) that processed the job.

## REST API

### Terminate Endpoint

```
POST /api/extras/job-results/{id}/terminate/
```

- Returns `202 Accepted` when the termination request is successfully created or retried.
- Returns `200 OK` with a no-op message if the job is already in a terminal state.
- If the termination call fails, returns `500` with the error detail.

## Permissions

The kill switch uses existing Nautobot permissions. No new permissions are introduced.

- **Terminate / Reap**: Requires `extras.change_jobresult` permission.
- **View Kill Requests**: Requires `extras.view_jobkillrequest` permission.
- **View Active Jobs**: Requires `extras.view_jobresult` permission.
