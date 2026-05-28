# Job Revocation

+++ 3.2.0

The Job Revocation gives operators the ability to terminate running or pending jobs and clean up stuck job records.

## Overview

Sometimes a job is taking longer than expected and needs to be cancelled. Sometimes a worker crashed mid-job and the `JobResult` is left sitting in `STARTED` forever, even though nothing is actually running. Sometimes a job might have been incorrectly enqueued to a queue that doesn't actually have any workers servicing it. Job Revocation handles such situations through a single user action (clicking `Revoke Job` on a `JobResult`) and moves the JobResult to `REVOKED` state, doing any appropriate additional actions as described below.
When an operator terminates a job, Nautobot first asks the backend whether any worker still holds the task. There are three possible answers:

1. **A worker is processing the task**. Nautobot sends a hard kill (SIGKILL on Celery) to stop it immediately. The worker tears the task down, and the `JobResult` is updated with the user who initiated the kill, the time, and a final status of `REVOKED`.
2. **No worker has the task**. The job is "reaped": the `JobResult` is marked `REVOKED` directly, with no kill signal sent.
3. **The backend can't be reached**. Treated the same as "no worker has the task" - the job is reaped. The DB write is the source of truth; if a worker comes back later and tries to run the job, a worker-startup hook checks the broker queue against the `REVOKED` jobs in the database and skips them.

In all cases the `JobResult` ends up with `revoked_by`, `revoked_by_user_name`, and `date_done` recorded, so the operator who killed the job is auditable.

### Reap vs. terminate

The distinction matters because the two paths have very different costs and side effects:

- A terminate sends a kill signal across the network to a live worker process. The worker is mid-task, possibly holding database transactions, possibly partway through writing changes. SIGKILL is a hard stop — there is no chance for the job to clean up. This is what users expect when they click "Revoke Job" but it's the more disruptive of the two.
- A reap is a database-only operation - no worker involvement. The job is already not running (because no worker has it); the operator is just cleaning up the bookkeeping. This is the quiet, safe path, and it's what runs whenever a worker has gone away without finishing the jobs it was given.

Both paths converge on the same final state: a `REVOKED` `JobResult` with all attribution. Exception is `terminated_at` it's only set when `JobResult` is terminated.

### Worker restart recovery

There's one edge case worth knowing about: a job can be marked `REVOKED` in the database while its Celery message is still sitting in the broker queue. If the worker that was supposed to run it has been down, the message has not been consumed yet. When the worker comes back online, it would normally pick the message up and run the job, ignoring the database state. To prevent this, a `worker_ready` signal handler runs once at worker startup. It reads every queue the worker is consuming, finds messages whose `JobResult` is already `REVOKED` in the database, and adds those task IDs to Celery's in-memory revoked set. When the worker dequeues those messages it sees them in the revoked set and discards them. This closes the gap between "operator clicked Revoke Job" and "worker comes back online" — the kill survives a restart.

### Permissions

Revoking requires `extras.run_job` and `extras.view_jobresult`. Users can revoke jobs they submitted. Staff can additionally revoke jobs submitted by other users. Staff without `run_job` cannot revoke anything.

### Revocation via the UI

A running or pending job can be revoked from its `JobResult` detail view. Click the **Revoke Job** button to open the confirmation page, which indicates whether the job is currently running (and will be terminated) or whether its worker is gone (and the record will be reaped). Confirming the action moves the `JobResult` to `REVOKED` state and records the operator who initiated it.

The button is shown only when the job is in an unfinished state and the current user is permitted to revoke it. See [Permissions](#permissions) for details.

### Revocation via the API

Job revocation can also be triggered via the REST API. The endpoint is exposed on the `JobResult` viewset under `revoke`.

The API supports a two-step workflow:

- `GET` returns a preview of the revoke operation and what action will be taken.
- `POST` performs the actual revoke operation.

#### Preview a revocation

A `GET` request returns details about the job and the action that would be taken. No worker is signaled and no `JobResult` is modified.

```no-highlight
curl -X GET \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/job-results/$JOB_RESULT_ID/revoke/
```

The `action` field indicates the path the server would take:

- `TERMINATE` - the worker is alive and would receive a `SIGKILL`.
- `REAP` - no worker is running; the `JobResult` would be marked revoked without signaling anything.
- `None` - the job has already reached a ready state; no action would be taken.

```json
{
    "message": "Are you sure you want to revoke '<jobresult_name>'?",
    "action": "TERMINATE",
    "action_description": "SIGKILL to worker. Stops immediately, no cleanup.",
    "job_status": "RUNNING",
    "irreversible": "This action cannot be undone.",
    "timestamp": "'2026-05-14T11:00:12.060393+00:00'"
}
```

If the `JobResult` is already in a finished state, the preview endpoint still returns `200 OK`, since no state-changing operation is attempted. The `irreversible` field is omitted because there is nothing to undo.

Example response for a finished job:

```json
{
    "message": "Job '<jobresult_name>' is already finished.",
    "action": "None",
    "action_description": "Job is already finished. Nothing to do.",
    "job_status": "SUCCESS",
    "timestamp": "2026-05-14T11:00:12.060393+00:00"
}
```

#### Perform a revocation

A `POST` request performs the revoke.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Accept: application/json; version=1.3; indent=4" \
http://nautobot/api/extras/job-results/$JOB_RESULT_ID/revoke/
```

On success the response is the updated `JobResult` (now in `REVOKED` state, with `revoked_by` and `date_done` set)

If the `JobResult` is already in a finished state, the request returns 409 Conflict.

```json
{
    "detail": "Job is already finished. Nothing to do."
}
```

#### A note on the `status` field after a `TERMINATE`

When the action is `TERMINATE`, the revoke is delivered to the Celery worker asynchronously: Nautobot sends `SIGKILL` and returns immediately, while the worker writes `status = "REVOKED"` back through the result backend a moment later. The `JobResult` returned in the API response is read immediately after the signal is sent, so its `status` field will often still show the prior value (e.g. `STARTED` or `PENDING`) not because the revoke failed, but because the status update hasn't propagated yet.

The authoritative signal that a revoke succeeded is the presence of `revoked_by` and `date_terminated` on the returned `JobResult`. If those fields are set, the revoke was accepted and recorded; the `status` field will catch up on a subsequent read.

For `REAP` (no live worker), the `status` field is updated synchronously and will already read `REVOKED` in the response.

API clients that need the final `status` immediately should poll the `JobResult` detail endpoint until `status` reaches a terminal value, rather than relying on the response body of the `revoke` call.

#### Status codes

| Code | Meaning                                                                              |
|------|--------------------------------------------------------------------------------------|
| 200  | Preview returned successfully (`GET`) or revocation succeeded (`POST`).              |
| 500  | The revoke strategy reported an error or the queue type is unsupported.              |
| 403  | The caller lacks proper permissions. See [Permissions](#permissions) for full rules. |
| 409  | A `POST` revoke request was made for a JobResult already in a finished state.        |
| 500  | The revoke strategy reported an error or the queue type is unsupported.              |
