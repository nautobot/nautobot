# Job Kill Switch — Manual QA Test Plan

## Prerequisites

- Run `nautobot-server create_kill_switch_demo_data` to populate demo data.
- Logged in as a superuser or user with `extras.change_jobresult` and `extras.view_jobkillrequest` permissions.

## 1. Terminate Job (UI — Detail View)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 1.1 | Terminate button visible for running job | Navigate to a Job Result in STARTED status. | Terminate Job button appears (red, leftmost action button). |
| 1.2 | Terminate button visible on all tabs | Click through Summary, Logs, Console Log tabs on a STARTED job. | Terminate Job button renders on every tab. |
| 1.3 | Terminate button hidden for completed job | Navigate to a Job Result in SUCCESS status. | No Terminate Job button. |
| 1.4 | Terminate button hidden for revoked job | Navigate to a Job Result in REVOKED status. | No Terminate Job button. |
| 1.5 | Confirm dialog appears | Click Terminate Job on a killable job. | Browser confirm() dialog appears warning about immediate termination. |
| 1.6 | Cancel confirm dialog | Click Terminate Job, then Cancel in the confirm dialog. | No action taken, job status unchanged. |
| 1.7 | Successful termination | Click Terminate Job, confirm. | Redirects to detail page. Success message shown. Status is now REVOKED. kill_type=terminate, killed_by=current user, killed_at populated. |
| 1.8 | Terminate already-terminal job (race condition) | Open detail page for a STARTED job in two tabs. Terminate in tab 1. Then terminate in tab 2. | Tab 2 shows info message "This job has already completed and cannot be terminated." Job is not modified again. |

## 2. Terminate Job (UI — List View)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 2.1 | Terminate in dropdown for killable job | Jobs > Job Results. Find a STARTED job. Open row dropdown. | "Terminate Job" option visible in dropdown. |
| 2.2 | Dropdown hidden for completed job | Find a SUCCESS job in the list. Open row dropdown. | No "Terminate Job" or "Reap Job" options. |
| 2.3 | Terminate from list view | Click "Terminate Job" from dropdown on a STARTED job, confirm. | Redirects back, success message, job now REVOKED. |

## 3. Reap Job (UI)

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 3.1 | Reap button visible for killable job | Jobs > Job Results. Find a STARTED job. Open row dropdown. | "Reap Job" option visible. |
| 3.2 | Reap dead job | Click "Reap Job" on a demo job whose worker is not running. Confirm. | Job moves to REVOKED. kill_type=reap. killed_by is null. Success message shown. |
| 3.3 | Reap active job (worker alive) | Start a real long-running job. While it's running, click "Reap Job" on it. | Job is NOT cancelled. Warning message: worker is still alive, job skipped. |
| 3.4 | Reap when Celery inspection fails | Stop all Celery workers. Click "Reap Job" on a STARTED job. | Job is NOT cancelled. Error message about inability to determine worker liveness. |

## 4. Active Jobs Button

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 4.1 | Click Active Jobs | Click the "Active Jobs" button. | Job Results list filters to only STARTED and PENDING jobs. URL shows `?status=STARTED&status=PENDING`. |
| 4.2 | Active Jobs button on Worker Status | Navigate to Worker Status page. | "Active Jobs" button visible, links to filtered Job Results. |

## 5. JobKillRequest Views

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 5.1 | List view loads | Navigate to Jobs > Job Kill Requests. | List view shows all kill request records with columns: Job Result, Requested By, Requested At, Acknowledged At, Status, Error Detail. |
| 5.2 | Detail view loads | Click on a kill request row. | Detail page shows all fields. Job Result links to the associated JobResult. |
| 5.3 | Read-only | Verify no Add, Edit, or Delete buttons on list or detail views. | No create/edit/delete actions available. |
| 5.4 | Navigation | Check Jobs section in sidebar. | "Job Kill Requests" menu item present. |

## 6. Model Validation

| # | Test | Steps | Expected |
|---|------|-------|----------|
| 6.1 | kill_type immutable | In shell: set kill_type on a terminated JobResult, try to change it via save(). | ValidationError: kill_type cannot be changed once set. |
| 6.2 | kill_type and killed_at consistency | In shell: set kill_type without killed_at (or vice versa). | ValidationError: must both be set or both be null. |
| 6.3 | killed_at before date_created | In shell: set killed_at to a time before job's date_created. | ValidationError: killed_at must not be before date_created. |
