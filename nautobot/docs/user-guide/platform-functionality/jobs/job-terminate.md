# Job Terminate

+++ 3.2.0

The Job Terminate gives operators the ability to terminate running or pending jobs and clean up stuck job records.

## Overview

Long-running or stuck jobs are a normal part of operating Nautobot. Sometimes a job is taking longer than expected and needs to be cancelled. Sometimes a worker crashed mid-job and the `JobResult` is left sitting in `STARTED` forever, even though nothing is actually running. Job Terminate handles both situations through a single user action(clicking `Terminate` on a `JobResult`) and decides what to do based on whether a worker is still alive.
When an operator terminates a job, Nautobot first asks the backend whether any worker still holds the task. There are three possible answers:

1. **A worker is processing the task**. Nautobot sends a hard kill (SIGKILL on Celery) to stop it immediately. The worker tears the task down, and the `JobResult` is updated with the user who initiated the kill, the time, and a final status of `REVOKED`.
2. **No worker has the task**. The job is "reaped": the `JobResult` is marked `REVOKED` directly, with no kill signal sent.
3. **The backend can't be reached**. Treated the same as "no worker has the task" - the job is reaped. The DB write is the source of truth; if a worker comes back later and tries to run the job, a worker-startup hook checks the broker queue against the `REVOKED` jobs in the database and skips them.

In all cases the `JobResult` ends up with `terminated_by`, `terminated_by_user_name`, `terminated_at`, and `date_done` recorded, so the operator who killed the job is auditable.

### Reap vs. terminate

The distinction matters because the two paths have very different costs and side effects:
- A terminate sends a kill signal across the network to a live worker process. The worker is mid-task, possibly holding database transactions, possibly partway through writing changes. SIGKILL is a hard stop — there is no chance for the job to clean up. This is what users expect when they click "Terminate," but it's the more disruptive of the two.
- A reap is a database-only operation. No network traffic, no signals, no worker involvement. The job is already not running (because no worker has it); the operator is just cleaning up the bookkeeping. This is the quiet, safe path, and it's what runs whenever a worker has gone away without finishing the jobs it was given.
Both paths converge on the same final state: a `REVOKED` `JobResult` with full attribution.

### Worker restart recovery

There's one edge case worth knowing about: a job can be marked `REVOKED` in the database while its Celery message is still sitting in the broker queue. If the worker that was supposed to run it has been down, the message has not been consumed yet. When the worker comes back online, it would normally pick the message up and run the job, ignoring the database state. To prevent this, a `worker_ready` signal handler runs once at worker startup. It reads every queue the worker is consuming, finds messages whose `JobResult` is already `REVOKED` in the database, and adds those task IDs to Celery's in-memory revoked set. When the worker dequeues those messages it sees them in the revoked set and discards them. This closes the gap between "operator clicked Terminate" and "worker comes back online" — the kill survives a restart.
