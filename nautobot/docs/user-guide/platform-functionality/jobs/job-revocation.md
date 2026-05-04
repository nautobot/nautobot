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
