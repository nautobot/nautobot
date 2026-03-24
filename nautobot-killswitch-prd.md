# PRD: Job Kill Switch

> **Scope:** Applies to Nautobot Jobs running on both the Celery and Kubernetes backends. How a job gets killed differs by backend, but the result is always the same: a terminal failure state with a clear record of what happened.

> **Status mapping:** Nautobot uses Celery's state machine directly. The PRD refers to "Cancelled" conceptually, but the actual terminal state is `REVOKED` (`JobResultStatusChoices.STATUS_REVOKED`), which is already in Celery's `READY_STATES`. Similarly, "Running" maps to `STARTED` and "Pending" maps to `PENDING`.

## Use Cases

- An operator needs to stop a long-running or hung job before it completes naturally.
- A job is stuck in `STARTED` status but the underlying worker or pod is no longer alive; an operator needs to move it to a terminal state to unblock re-runs or monitoring.
- A job was queued and is in `PENDING` status but should never be executed; an operator needs to cancel it without waiting for a worker to pick it up.
- An operator needs a clear audit trail indicating that a job was killed deliberately, not that it failed on its own.

## What

### Requirements

- A **Terminate Job** button is available from the Job Result list view and the Job Result detail view.
- The Terminate Job button is available only when the job is in a non-terminal state (`STARTED` or `PENDING`).
- For Celery-backed jobs, termination is performed via `control.revoke` with `terminate=True` and `signal="SIGKILL"`.
- For Kubernetes-backed jobs, termination is performed via the Kubernetes Python client (`BatchV1Api().delete_namespaced_job()`).
- After termination is initiated, the `JobResult` moves to `REVOKED`. If the termination attempt fails (e.g. the revoke call raises, or the pod delete returns an error), the error is surfaced to the user — the job is not moved to any new state. If the job is already in a terminal state when termination is requested, the request is a no-op and the user is informed.
- Any buffered log lines that can be flushed before termination should be flushed. Lines that cannot be recovered are acknowledged as acceptable data loss.
- The `JobResult` records that the job was killed (as opposed to failing on its own) — see `kill_type` field below.
- A **Reap Job** action exists to check whether a job's underlying worker is still alive before cancelling it. This is a per-job action available from the list view dropdown.
- A **Active Jobs view** shows all `JobResult` records currently in `STARTED` or `PENDING` state across both backends. See the Active Jobs View section for full spec.

### Non-Requirements

- **Graceful shutdown / drain:** The kill is hard termination. There is no requirement to wait for a job to reach a safe stopping point or to send a SIGTERM before SIGKILL.
- **Partial rollback of side effects:** External API calls or config pushes already fired before the kill are not rolled back. Recording that they occurred is a separate concern and out of scope for this feature.
- **Kill by job name or job class:** Only individual `JobResult` records are targeted. Bulk kill by job type is not in scope.
- **Permission model changes:** This feature uses the existing Nautobot permissions model. No new permissions are introduced beyond constraining the kill action to users who can already change a `JobResult`.
- **Kill history / kill log model:** The kill event is recorded on the `JobResult` itself. A separate audit log model for kill events is not introduced.
- **Automatic reaping on a schedule:** The reap action is triggered manually per-job from the UI. There is no scheduled/periodic task or bulk reap action registered at install time.
- **Bulk reap:** There is no bulk "Cancel Dead Jobs" action. Reaping is done one job at a time to allow operators to review each case.

## Model: `JobResult` (additions)

### Fields (additions only)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `kill_type` | `CharField(max_length=32, choices=KillTypeChoices)` | No | `None` / `null` | How the job was killed. Null for jobs that complete or fail normally. Read-only via API after being set. |
| `killed_by` | `ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)` | No | `None` / `null` | The user who initiated the kill action. Null for jobs terminated by the reap workflow or by normal completion. |
| `killed_at` | `DateTimeField(null=True, blank=True)` | No | `None` / `null` | Timestamp at which the kill was initiated. Managed automatically by the kill logic; not user-settable. |

### Properties

| Property | Type | Description |
|---|---|---|
| `is_killable` | `bool` | Returns `True` if `status` is `STARTED` or `PENDING`. Derived from `status`; not stored. |
| `backend` | `str` | Returns `"celery"` or `"kubernetes"` based on how the job was dispatched. Derived from existing job execution metadata; not stored. |

### `KillTypeChoices`

| Value | Label | Description |
|---|---|---|
| `terminate` | Terminate | Kill was initiated by a logged-in user via the UI or API. Job moves to `REVOKED` on success. If the termination call fails, the error is returned to the user and the job status does not change. |
| `reap` | Reap | The job was stuck in a non-terminal state, but no active worker or pod was found running it. A reap action moves it to `REVOKED` to clear the stuck state. |

### Constraints & Validation

- `kill_type` is `null` if and only if `killed_at` is `null`. They are always set together.
- `killed_by` may be `null` even when `kill_type` is set (reap workflow runs without a user context).
- `killed_at` cannot be set to a time before the `JobResult.date_created` timestamp.
- Once `kill_type` is set, it cannot be changed by any subsequent write. Enforce in the model's `save()` or via API serializer read-only logic.
- The kill action is only allowed when `status in (STATUS_STARTED, STATUS_PENDING)`. Attempts to kill a job in any other status return a no-op info message.

## Model: `JobKillRequest` (new)

Provide Standard List and detail view

### Design Rationale

TODO: Is this needed? I can go either way.

When a user clicks Terminate Job, the system can't always kill the process synchronously — the worker needs to pick up the signal and act on it. Rather than adding a flag to `JobResult` that would need cleaning up if something goes wrong mid-flight, a `JobKillRequest` record captures the intent to terminate as its own entity.

This separation has a few practical benefits: it survives worker restarts (the intent is durable), it lets the UI show a "Termination Pending" state before the worker has confirmed anything, and it makes the termination flow independently testable. The `JobResult` itself stays clean — it only reflects what actually happened, not what was requested.

### Fields

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `id` | `UUIDField(primary_key=True)` | Yes | auto | Primary key. |
| `job_result` | `OneToOneField(JobResult, on_delete=CASCADE)` | Yes | — | The `JobResult` targeted for termination. One-to-one enforces that only one kill request can exist per job. |
| `requested_by` | `ForeignKey(User, null=True, blank=True, on_delete=SET_NULL)` | No | `null` | User who requested the kill. Null when initiated by the reap workflow. |
| `requested_at` | `DateTimeField(auto_now_add=True)` | Yes | auto | Timestamp the kill request was created. Managed automatically. |
| `acknowledged_at` | `DateTimeField(null=True, blank=True)` | No | `null` | Timestamp at which the worker or reap workflow confirmed termination was attempted. Null until acknowledged. |
| `status` | `CharField(max_length=32, choices=KillRequestStatus)` | Yes | `pending` | Lifecycle state of the kill request itself. |
| `error_detail` | `TextField(null=True, blank=True)` | No | `null` | If the kill attempt encounters an error (e.g., pod already gone, revoke call fails), the error is recorded here. |

### Properties

| Property | Type | Description |
|---|---|---|
| `is_pending` | `bool` | Returns `True` if `status == "pending"`. |

### `KillRequestStatus` Choices

| Value | Label | Description |
|---|---|---|
| `pending` | Pending | Kill has been requested but not yet acknowledged by a worker. |
| `acknowledged` | Acknowledged | Worker or reap workflow has attempted termination. |
| `failed` | Failed | The termination call itself failed (see `error_detail`). The `JobResult` status does **not** change — it remains in its current state for the user to retry or take manual action. |

### Constraints & Validation

- `job_result` is in a non-terminal state at the time the `JobKillRequest` is created or updated. If the job is already terminal, the terminate/reap action returns a no-op.
- `acknowledged_at` cannot be set before `requested_at`.
- A `JobKillRequest` for a given `job_result` cannot be created if one already exists (enforced by `OneToOneField`). However, an existing `JobKillRequest` is **updatable in place** on retry — its status resets to `pending`, `error_detail` clears, and the termination re-attempts. This allows retrying after a failed kill attempt without deleting and recreating the record.
- The view is strictly read-only. There is no create, edit, or delete actions exposed in the UI.
- Users with permission to view `JobResult` records is able to view `JobKillRequest` records.

## Backend-Specific Kill Logic

### Celery

A `terminate_job()` service function for the following steps:

TODO: Is this the optimal way?

1. Create a `JobKillRequest` with `status=pending`, or update an existing one in place if retrying after a previous failure (reset status to `pending`, clear `acknowledged_at` and `error_detail`).
2. Look up the Celery task ID — this is `str(job_result.pk)`, matching the ID set by `JobResult.enqueue_job()` via `apply_async(task_id=str(job_result.id))`.
3. Call `app.control.revoke(task_id, terminate=True, signal="SIGKILL")`. Note: `revoke()` is fire-and-forget — it sends a message to the broker and does not confirm worker receipt.
4. On success: update `JobKillRequest.status` to `acknowledged`, set `acknowledged_at`, then set `JobResult.status` to `REVOKED`, populate `kill_type`, `killed_by`, `killed_at`, and `date_done`.
5. Flush any buffered log entries associated with the job before or immediately after step 3 where possible.

If `revoke` raises, the exception is recorded in `JobKillRequest.error_detail`, `KillRequestStatus` is set to `failed`, and the error is surfaced to the caller. `JobResult.status` does not change — the job remains in its current state for the user to act on.

**Note on pending jobs with no workers:** `revoke()` succeeds silently — the revoke message is stored in the broker. If a worker later starts, it will skip the task. The job is marked as `REVOKED` immediately.

### Kubernetes

TODO: Is this the optimal way?

1. Derive the Kubernetes job name from `JobResult` metadata.
2. Call `kubectl delete job <job-name> --namespace <ns>` (or equivalent Python client call).
3. Update `JobKillRequest.status` to `acknowledged` and set `acknowledged_at`.
4. Set `JobResult.status` to `REVOKED`, populate `kill_type`, `killed_by`, and `killed_at`.
5. Log lines in the pod's in-memory buffer at the time of deletion are considered lost. This is acceptable per the data loss table below.

**Acknowledged data loss for Kubernetes:**

| Data | Risk | Disposition |
|---|---|---|
| Buffered log lines | Medium | Accepted as unrecoverable; noted in `error_detail` if detectable |
| Partial object changes | High | DB transaction is rolled back by Django on worker exit; accepted |
| External side effects | High | Already fired; not rolled back; out of scope |
| `JobResult` final status | Low | Explicitly set by this feature |
| Celery task metadata | N/A | Not applicable |

If `kubectl delete` raises or returns non-zero, the error is recorded in `error_detail`, `KillRequestStatus` is set to `failed`, and the error is surfaced to the caller. `JobResult.status` does not change.

## Reap Dead Jobs

Reaping is a per-job action that checks whether the underlying worker is still alive before cancelling. Unlike Terminate (which immediately sends a `revoke()` regardless of worker state), Reap is a cautious operation — it only cancels jobs whose workers are confirmed dead.

### Service Function

A `reap_dead_jobs(queryset=None)` service function for the following:

TODO: Overly prescriptive, feel free to change.

1. Accept an optional queryset of `JobResult` records. If None, query all records with `status in (PENDING, STARTED)`.
2. Filter to only non-terminal jobs (in case the caller passes a broader queryset).
3. Call `app.control.inspect().active()` to get all active task IDs across all Celery workers.
4. If inspection fails or returns None (e.g., no workers responding, broker unreachable), skip all records and return an error — do not reap when liveness cannot be determined.
5. For each job: if `str(job_result.pk)` is found in the active task set, skip it (worker is alive).
6. For confirmed-dead jobs: create or update a `JobKillRequest` with `status=acknowledged` and `requested_by=None`, then set `JobResult.status=REVOKED`, `kill_type=reap`, `killed_at=now()`. If a `JobKillRequest` already exists, it is updated in place rather than deleted and recreated.
7. Return a summary dict: `{cancelled: N, skipped: N, errors: [...]}`.

Provide a button the List view, when `is_killable` is `True`.

### Terminate vs Reap

| | Terminate | Reap |
|---|---|---|
| Worker liveness check | No | Yes |
| Celery `revoke()` call | Yes | No |
| Use case | Operator wants to kill a job immediately | Operator suspects a job is stuck and wants to confirm before cancelling |
| `kill_type` | `terminate` | `reap` |
| `killed_by` | Current user | `null` |

## Active Jobs View

Convert the Django admin view to a standard view. Keep permissions the same

## JobResult Table Columns (additions)

The Job Result list view table includes the following additional columns to surface kill switch metadata:

| Column | Description |
|---|---|
| Kill Type | Displays `kill_type` value (`Terminate`, `Reap`) or `—` if null. |
| Killed By | Displays the username of the `killed_by` user, or `—` if null. |
| Killed At | Displays the `killed_at` timestamp, or `—` if null. |

These columns also appear on the Job Result detail view summary panel.

## JobKillRequest UI View

A read-only UI view exists for `JobKillRequest` records to support operational debugging and observability.

## View Considerations

- Add Terminate & Reap button on list view when `is_killable` is `True` at render time.
- On the detail view, the button renders as an inline `<form>` with a submit button
- Error / Race Condition handling: If the job has already moved to a terminal state between render and click, the UI view returns a Django info message (e.g. "This job has already completed and cannot be terminated.") and redirects. If a kill request already exists, a warning message is shown. If failed a message is shown

## API Considerations

- A new API action endpoint is exposed: `POST /api/extras/job-results/{id}/terminate/`.
- The API endpoint returns `202 Accepted` when the termination request is successfully created or retried.
- The API endpoint returns `200 OK` with a no-op message if the job is already in a terminal state. No record is modified.
- The response body for `202` includes the `JobKillRequest` id and `status`.
- If the termination call fails, the error detail is included in the response (`500`) so the caller can surface it to the user. The `JobKillRequest` is saved with `status=failed` and `error_detail`.
- `kill_type`, `killed_by`, and `killed_at` on `JobResult` are read-only via the API. They are not writable via `PATCH` or `PUT`.
- The `JobKillRequest` model is exposed as a read-only API resource at `/api/extras/job-kill-requests/` for observability. No write operations beyond creation via the `/terminate/` action.
- A UI reap action endpoint is exposed: `POST /extras/job-results/{id}/reap/`. This endpoint checks worker liveness for a single job and cancels it if the worker is confirmed dead, redirecting back to the detail page with Django messages for feedback.

## Acceptance Criteria

- A user with permission to change a `JobResult` sees a Terminate Job button on the Job Result list view for jobs where `is_killable` is `True` at render time. TODO: is this the correct permission?
- Clicking the Reap Job button on a job whose worker is confirmed dead moves it to `REVOKED` with `kill_type=reap`.
- Clicking the Reap Job button on a job whose worker is still alive skips the job and surfaces a warning message.

- The Terminate Job button is not rendered for jobs in terminal states (`SUCCESS`, `FAILURE`, `REVOKED`).
- If a job moves to a terminal state between page render and the user clicking Terminate Job, the UI displays a clear message (e.g. "This job has already completed") and refreshes the displayed status rather than showing an error.
- Clicking the Terminate Job button displays a browser `confirm()` dialog before any action is taken.
- Confirming termination of both Celery and Kubernetes-backed job results.
- If the termination call fails (revoke raises, pod delete errors), the error is surfaced to the user and `JobResult.status` does not change.
- Requesting termination on a job already in a terminal state returns a no-op response and surfaces a message to the user; the record is not modified.
    - `202` for a job in `STARTED` or `PENDING` status,  returns `200` with a no-op message for a job already in a terminal state.
- A user with permission to change a `JobResult` sees a Reap Job button in the row-level dropdown for jobs where `is_killable` is `True`.
- The Active Jobs view displays all `JobResult` records in `STARTED` or `PENDING` state across both Celery and Kubernetes backends.
- The Terminate Job button is available per-row in the Active Jobs view and behaves identically to the button in the main Job Results list view, including race condition handling.
- The Job Result list view table includes `Kill Type`, `Killed By`, and `Killed At` columns.
- No create, edit, or delete actions are available for `JobKillRequest` in the UI.
