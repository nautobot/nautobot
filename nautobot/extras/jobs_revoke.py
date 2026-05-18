from abc import ABC, abstractmethod
from datetime import datetime
import logging

from celery.exceptions import TaskRevokedError
from django.db import transaction
from django.utils import timezone

from nautobot.core.celery import app as celery_app
from nautobot.core.utils.logging import sanitize
from nautobot.extras.choices import JobQueueTypeChoices, JobResultStatusChoices, LogLevelChoices
from nautobot.extras.models import JobResult
from nautobot.users.models import User

logger = logging.getLogger(__name__)


class JobRevokeStrategy(ABC):
    """Abstract base class for job termination strategies across different queues.

    Defines the interface for various backends (Celery, Kubernetes, etc.).
    Subclasses implement the `is_alive`, `should_reap`, and
    `perform_termination` hooks; `revoke` orchestrates them.
    """

    @abstractmethod
    def is_alive(self, job_result: JobResult) -> bool | None:
        """Return True/False if the backend can confirm the job's liveness, None if unknown."""

    @abstractmethod
    def should_reap(self, job_result: JobResult) -> bool:
        """Return True if the job can be marked revoked without sending a kill signal."""

    @abstractmethod
    def perform_termination(self, job_result: JobResult, user: User) -> bool:
        """Send the backend-specific kill signal and mark the job revoked."""

    def _apply_termination_metadata(
        self, job_result: JobResult, user: User, now_timestamp: None | datetime = None
    ) -> set[str]:
        """Fill in termination metadata fields on a locked `JobResult`.

        Sets `date_done`, `revoked_by`, `revoked_by_user_name`, and
        only if they are not already set. Caller is responsible
        for the surrounding transaction/lock and for calling `save()`.

        Args:
            job_result: The locked `JobResult` to update (modified in place).
            user: The user requesting termination.
            now_timestamp: Optional timestamp to use for `date_done`. If not provided,
                the current time will be used.

        Returns:
            The set of field names that were modified, for `update_fields`.
        """
        if now_timestamp is None:
            now_timestamp = timezone.now()

        changed: set[str] = set()

        if job_result.date_done is None:
            job_result.date_done = now_timestamp
            changed.add("date_done")

        if job_result.revoked_by is None:
            job_result.revoked_by = user
            changed.add("revoked_by")

        if not job_result.revoked_by_user_name:
            job_result.revoked_by_user_name = user.username
            changed.add("revoked_by_user_name")

        return changed

    def _mark_revoked(self, job_result: JobResult, user: User) -> tuple[JobResult, bool]:
        """Mark a `JobResult` as revoked, filling in only fields that aren't already set."""
        with transaction.atomic():
            job_result = JobResult.objects.select_for_update().get(pk=job_result.pk)
            changed = self._apply_termination_metadata(job_result, user)

            exc = TaskRevokedError("revoked")
            job_result.status = JobResultStatusChoices.STATUS_REVOKED
            job_result.result = {
                "exc_type": type(exc).__name__,
                "exc_module": "celery.exceptions",
                "exc_message": [sanitize(str(exc))],
            }
            changed |= {"status", "result"}

            job_result.save(update_fields=list(changed))

        return job_result

    def revoke(self, job_result, user) -> dict:
        """Reap or kill a job and return the outcome.

        Reaps when `should_reap` is True (no signal sent). Otherwise sends
        the backend kill signal via `perform_termination`. Exceptions from
        the kill path are caught and reported in the result.

        Args:
            job_result: The `JobResult` to revoke.
            user: The user requesting termination.

        Returns:
            `{"job_result": JobResult, "error": str | None}`. `error` is
            set only when `perform_termination` raised.
        """
        # REAP
        if self.should_reap(job_result):
            logger.info("Reaped dead job %s by %s", job_result.pk, user)
            job_result.log(
                f"Reaped dead job {job_result.pk} by {user}",
                level_choice=LogLevelChoices.LOG_FAILURE,
                grouping="revoking",
            )
            return {"job_result": self._mark_revoked(job_result, user), "error": None, "revoked": True}

        # TERMINATE
        try:
            revoked = self.perform_termination(job_result, user)
        except Exception as e:
            logger.error("Termination failed for %s: %s", job_result.pk, e)
            job_result.log(
                f"Termination failed for {job_result.pk}: {e}",
                level_choice=LogLevelChoices.LOG_ERROR,
                grouping="revoking",
            )
            return {"job_result": job_result, "error": f"Termination failed: {e}", "revoked": False}

        return {"job_result": job_result, "error": None, "revoked": revoked}


class CeleryStrategy(JobRevokeStrategy):
    "Termination strategy for jobs running on Celery workers."

    def is_alive(self, job_result) -> bool:
        """
        Check whether a Celery worker is currently aware of (and likely processing)
        a given task.

        This method queries active Celery workers using `inspect().query_task`
        to determine if the task associated with the provided `job_result`
        is still present in any worker's task list.

        Args:
            job_result: An object representing the task result. It is expected
                to have a primary key attribute `pk` corresponding to the
                Celery task ID.

        Returns:
            bool:
                - True if at least one worker reports the task ID.
                - False if workers respond but none contain the task.
                - False if the worker state could not be determined (e.g., no
                replies or an exception occurred while querying workers).
        """
        try:
            task_id = str(job_result.pk)
            replies = celery_app.control.inspect().query_task([task_id])
        except Exception as e:
            logger.warning("Failed to query Celery workers: %s", e)
            job_result.log(
                "Failed to query Celery workers: {e}", level_choice=LogLevelChoices.LOG_WARNING, grouping="revoking"
            )
            return False
        if replies is None:
            return False
        # replies shape: {worker_hostname: {task_id: [state, info]}}
        return any(task_id in worker_tasks for worker_tasks in replies.values())

    def should_reap(self, job_result):
        """Return True if the job should be reaped (marked revoked without a kill signal).

        Reap when no worker will handle the job *and* the job isn't already done.
        `not self.is_alive(...)` covers both False (workers replied, none has the
        task) and None (couldn't reach workers at all) — both are treated as
        "no worker will handle this." The `_is_unready_state` guard prevents
        reaping a job that already finished normally.

        Args:
            job_result: The `JobResult` to evaluate.

        Returns:
            True if the job should be reaped, False otherwise.
        """
        return job_result.is_unready_state and not self.is_alive(job_result)

    def perform_termination(self, job_result: JobResult, user: User):
        """Send a SIGKILL revoke to the Celery worker and mark the job revoked.

        Fires a `revoke(terminate=True, signal="SIGKILL")` control message to
        whichever worker holds the task, then records the revocation on the
        `JobResult` via `_apply_termination_metadata`. Any exception from the revoke call
        propagates — the orchestrator in `revoke` catches it and reports
        the failure to the caller.

        Args:
            job_result: The `JobResult` to terminate. Its `pk` is used as the
                Celery task ID.
            user: The user requesting termination, recorded on `revoked_by`.
        """
        if not job_result.is_unready_state:
            logger.info(
                "Job %s is already in terminated state `%s` no action was taken.", job_result.pk, job_result.status
            )
            job_result.log(
                f"Job {job_result.pk} is already in terminated state `{job_result.status}` no action was taken",
                grouping="revoking",
            )
            return False

        task_id = str(job_result.pk)
        with transaction.atomic():
            now = timezone.now()
            job_result = JobResult.objects.select_for_update().get(pk=job_result.pk)
            changed = self._apply_termination_metadata(job_result, user, now)

            job_result.date_terminated = now
            changed.add("date_terminated")

            job_result.save(update_fields=list(changed))

            celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

        logger.info("Job %s terminated by %s", job_result.pk, user)
        job_result.log(
            f"Job {job_result.pk} terminated by {user}", level_choice=LogLevelChoices.LOG_FAILURE, grouping="revoking"
        )
        return True


class K8sStrategy(JobRevokeStrategy):
    """Placeholder for now"""


class UnknownStrategy(JobRevokeStrategy):
    """Fallback strategy for queue types without a registered backend.

    Has no way to reach a worker, so it always reports the job as not alive
    and reaps it. Marks the JobResult revoked without sending any kill signal.
    """

    def is_alive(self, job_result) -> bool:
        """Always return False. There is no backend to query for liveness."""
        return False

    def should_reap(self, job_result) -> bool:
        """Always reap when the job is still in an unready state.

        The is_unready_state check prevents a task that
        has already been completed from being overwritten.
        """
        # TBD: maybe this method shouldn't be abstract and should be defined in ABC class
        # Review after implementing K8sStrategy
        return job_result.is_unready_state and not self.is_alive(job_result)

    def perform_termination(self, job_result: JobResult, user: User) -> bool:
        """No-op; never reached in normal flow. See class docstring."""
        return False


class RevokeFactory:
    """Resolve the right revoke strategy for a given job queue type."""

    strategies = {JobQueueTypeChoices.TYPE_CELERY: CeleryStrategy, JobQueueTypeChoices.TYPE_KUBERNETES: K8sStrategy}

    @classmethod
    def get_strategy(cls, queue_type: str):
        """Return a strategy instance for `queue_type`.

        Unknown queue types fall back to `UnknownStrategy`, which reaps the
        job (marks it revoked) without attempting any backend-specific signal.
        """
        strategy_class = cls.strategies.get(queue_type, UnknownStrategy)
        return strategy_class()
