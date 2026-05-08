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

## Permissions

Revoking a job requires two things: the right permission and the right relationship to the job.

### Required permission

The action checks `extras.run_job` and `extras.view_jobresult`. The reasoning: revoking is a job-execution concern. A user with broad view access to `JobResult` records should not implicitly gain the ability to terminate live workers. Conversely, a user trusted to run jobs is already trusted to stop their own.

### Who can revoke which jobs

| User                                  | Can revoke own jobs | Can revoke others' jobs |
|---------------------------------------|:-------------------:|:-----------------------:|
| Has `run_job`, not staff              |         Yes         |           No            |
| Has `run_job`, is staff               |         Yes         |           Yes           |
| No `run_job`, is staff                |         Yes         |           Yes           |
| No `run_job`, not staff               |         No          |           No            |

Two rules combine to produce the matrix:

1. **Run permission OR staff.** A user without `extras.run_job` cannot revoke anything unless they are staff. Staff bypass this gate so that operators handling incidents can clean up jobs without being granted general job-execution rights.
2. **Ownership OR staff.** Even with `run_job`, a user can only revoke jobs they themselves submitted. Staff bypass this gate as well, so that an operator can clean up a stuck job submitted by another user.

### Revocation via the UI

A running or pending job can be revoked from its `JobResult` detail view. Click the **Revoke Job** button to open the confirmation page, which indicates whether the job is currently running (and will be terminated) or whether its worker is gone (and the record will be reaped). Confirming the action moves the `JobResult` to `REVOKED` state and records the operator who initiated it.

The button is shown only when the job is in an unfinished state and the current user is permitted to revoke it. See [Permissions](#permissions) for details.

### Revocation via the API

Job revocation can also be triggered via the REST API. The endpoint is exposed on the `JobResult` viewset under `revoke`. Revocation is a two-step flow by design: a first call returns a confirmation preview describing what will happen, and a second call with `confirm=true` performs the action.

#### Preview a revocation

A `POST` without the `confirm` flag (or with `confirm=false`) returns details about the job and the action that would be taken. No worker is signaled and no `JobResult` is modified.

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{}' \
http://nautobot/api/extras/job-results/$JOB_RESULT_ID/revoke/
```

The response indicates whether the job is currently running (terminate path) or whether the worker has gone away (reap path):

```json
{
    "error": "Confirmation required",
    "message": "Are you sure you want to revoke '<job name>'?",
    "job_status": "RUNNING",
    "timestamp": "2026-05-08 12:34:56",
    "action_description": "This will REAP or TERMINATE the job.",
    "irreversible": "This action cannot be undone.",
    "confirm_instruction": "Set `confirm=True` to proceed.",
    "details": {
        "REAP": "No worker running; marks JobResult as revoked without signal.",
        "TERMINATE": "SIGKILL to worker; stops immediately, no cleanup."
    }
}
```

#### Confirm a revocation

A `POST` with `confirm=true` performs the revoke. On success the response is the updated `JobResult` (now in `REVOKED` state, with `revoked_by` and `date_done` set):

```no-highlight
curl -X POST \
-H "Authorization: Token $TOKEN" \
-H "Content-Type: application/json" \
-H "Accept: application/json; version=1.3; indent=4" \
-d '{"confirm": true}' \
http://nautobot/api/extras/job-results/$JOB_RESULT_ID/revoke/
```

#### Status codes

| Code | Meaning                                                                                          |
|------|--------------------------------------------------------------------------------------------------|
| 200  | Revocation succeeded; response body is the updated `JobResult`.                                  |
| 400  | Either confirmation is required (preview response) or the strategy reported an error.            |
| 403  | The caller lacks `extras.run_job` and is not staff, or is not the job owner and is not staff.    |
| 409  | The `JobResult` is already in a finished state and cannot be revoked.                            |

See [Permissions](#permissions) for the full rules on who can revoke which jobs.
