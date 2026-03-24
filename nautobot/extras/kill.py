"""Kill switch logic for terminating and reaping Nautobot jobs."""

import logging

from django.utils import timezone

from nautobot.extras.choices import JobResultStatusChoices, KillRequestStatusChoices, KillTypeChoices
from nautobot.extras.models import JobKillRequest, JobResult

logger = logging.getLogger("nautobot.extras.kill")


def terminate_job(job_result, user=None, reason=KillTypeChoices.TERMINATE):
    """
    Terminate a running or pending job.

    For Celery-backed jobs, this calls control.revoke with terminate=True and SIGKILL.
    For Kubernetes-backed jobs, this is a placeholder.

    Args:
        job_result: The JobResult to terminate.
        user: The user requesting termination (None for reap workflow).
        reason: The kill type (default: terminate).

    Returns:
        dict with keys:
            - kill_request: The created JobKillRequest instance (on success)
            - error: Error message string (on failure)
            - kill_request_id: UUID of the kill request (on failure, if created)
    """
    now = timezone.now()

    # Reuse existing kill request if one exists (e.g. retry after failure), otherwise create
    try:
        kill_request = job_result.kill_request
        kill_request.requested_by = user
        kill_request.status = KillRequestStatusChoices.STATUS_PENDING
        kill_request.acknowledged_at = None
        kill_request.error_detail = ""
        kill_request.save()
    except JobKillRequest.DoesNotExist:
        kill_request = JobKillRequest.objects.create(
            job_result=job_result,
            requested_by=user,
            status=KillRequestStatusChoices.STATUS_PENDING,
        )

    # The Celery task_id is the string representation of the JobResult PK
    # (set in JobResult.enqueue_job via apply_async(task_id=str(job_result.id)))
    task_id = str(job_result.pk)

    try:
        from nautobot.core.celery import app

        app.control.revoke(task_id, terminate=True, signal="SIGKILL")
    except Exception as e:
        logger.error("Failed to revoke Celery task %s: %s", task_id, e)
        kill_request.status = KillRequestStatusChoices.STATUS_FAILED
        kill_request.acknowledged_at = timezone.now()
        kill_request.error_detail = str(e)
        kill_request.save()
        return {
            "error": f"Termination call failed: {e}",
            "kill_request_id": kill_request.pk,
        }

    # Revoke succeeded — update kill request and job result
    kill_request.status = KillRequestStatusChoices.STATUS_ACKNOWLEDGED
    kill_request.acknowledged_at = timezone.now()
    kill_request.save()

    job_result.status = JobResultStatusChoices.STATUS_REVOKED
    job_result.date_done = now
    job_result.kill_type = reason
    job_result.killed_by = user
    job_result.killed_at = now
    job_result.save()

    logger.info("Job %s terminated by %s (reason: %s)", job_result.pk, user, reason)

    return {"kill_request": kill_request}


def _get_active_celery_task_ids():
    """Query Celery workers for all currently active task IDs.

    Returns:
        set: Task IDs of all active tasks across all workers, or None if inspection failed.
    """
    try:
        from nautobot.core.celery import app

        inspect = app.control.inspect()
        active = inspect.active()
        if active is None:
            return None
        task_ids = set()
        for worker_tasks in active.values():
            for task in worker_tasks:
                task_ids.add(task["id"])
        return task_ids
    except Exception as e:
        logger.warning("Failed to inspect Celery workers: %s", e)
        return None


def reap_dead_jobs(queryset=None):
    """Find and cancel jobs whose underlying worker is confirmed absent.

    Args:
        queryset: Optional queryset of JobResult records to check. If None, all
                  non-terminal jobs are checked.

    Returns:
        dict with keys:
            - cancelled: number of jobs moved to REVOKED
            - skipped: number of jobs skipped (worker still alive or liveness unknown)
            - errors: list of error message strings
    """
    result = {"cancelled": 0, "skipped": 0, "errors": []}

    if queryset is None:
        queryset = JobResult.objects.filter(
            status__in=[JobResultStatusChoices.STATUS_PENDING, JobResultStatusChoices.STATUS_STARTED]
        )

    # Filter to only non-terminal jobs (in case caller passed a broader queryset)
    queryset = queryset.filter(
        status__in=[JobResultStatusChoices.STATUS_PENDING, JobResultStatusChoices.STATUS_STARTED]
    )

    if not queryset.exists():
        return result

    # Get active task IDs from Celery workers
    active_task_ids = _get_active_celery_task_ids()
    if active_task_ids is None:
        logger.warning("Cannot determine worker liveness — skipping all jobs")
        result["skipped"] = queryset.count()
        result["errors"].append("Cannot determine worker liveness: Celery inspection failed or timed out.")
        return result

    now = timezone.now()

    for job_result in queryset:
        task_id = str(job_result.pk)

        if task_id in active_task_ids:
            logger.info("Job %s is still active on a worker — skipping", job_result.pk)
            result["skipped"] += 1
            continue

        try:
            # Reuse existing kill request or create new one
            kill_request = JobKillRequest.objects.filter(job_result=job_result).first()
            if kill_request:
                kill_request.status = KillRequestStatusChoices.STATUS_ACKNOWLEDGED
                kill_request.acknowledged_at = now
                kill_request.error_detail = ""
                kill_request.save()
            else:
                JobKillRequest.objects.create(
                    job_result=job_result,
                    requested_by=None,
                    status=KillRequestStatusChoices.STATUS_ACKNOWLEDGED,
                    acknowledged_at=now,
                )

            job_result.status = JobResultStatusChoices.STATUS_REVOKED
            job_result.date_done = now
            job_result.kill_type = KillTypeChoices.REAP
            job_result.killed_at = now
            job_result.save()

            logger.info("Reaped dead job %s", job_result.pk)
            result["cancelled"] += 1
        except Exception as e:
            logger.error("Failed to reap job %s: %s", job_result.pk, e)
            result["errors"].append(f"Failed to reap job {job_result.pk}: {e}")

    return result
