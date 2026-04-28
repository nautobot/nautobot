from abc import ABC, abstractmethod
import logging

from django.db import transaction
from django.utils import timezone

from nautobot.extras.choices import JobQueueTypeChoices, JobResultStatusChoices
from nautobot.extras.models import JobResult
from nautobot.users.models import User

logger = logging.getLogger(__name__)


class JobTerminatorStrategy(ABC):
    """Abstract base class for job termination strategies across different queues.

    Defines the interface for various backends (Celery, Kubernetes, etc.).
    Subclasses implement the `is_alive`, `should_reap`, `_mark_revoked`, and
    `_perform_termination` hooks; `terminate` orchestrates them.
    """

    NON_TERMINAL_STATUSES = (
        JobResultStatusChoices.STATUS_PENDING,
        JobResultStatusChoices.STATUS_STARTED,
    )

    def is_terminal(self, job_result: JobResult) -> bool:
        """Return True if job_result is in a finished state.

        Refreshes from the DB before checking, so callers get the live status
        rather than whatever the in-memory object happened to hold.
        """
        job_result.refresh_from_db()
        return job_result.status not in self.NON_TERMINAL_STATUSES

    def can_update_revocation_fields(self, job_result: JobResult) -> bool:
        """Return True if revocation fields can be written for this job's current status.

        Used inside `transaction.atomic` where `is_terminal` can't be called
        (it would re-fetch and bypass the row lock).
        """
        return (
            job_result.status
            in (
                JobResultStatusChoices.STATUS_PENDING,
                JobResultStatusChoices.STATUS_STARTED,
                JobResultStatusChoices.STATUS_REVOKED,  # Celery's own `revoke` has already populated status that's why it's here
            )
        )

    @abstractmethod
    def is_alive(self, job_result: JobResult) -> bool | None:
        """Return True/False if the backend can confirm the job's liveness, None if unknown."""

    @abstractmethod
    def should_reap(self, job_result: JobResult) -> bool:
        """Return True if the job can be marked revoked without sending a kill signal."""

    @abstractmethod
    def _perform_termination(self, job_result: JobResult, user: User):
        """Send the backend-specific kill signal and mark the job revoked."""

    def _mark_revoked(self, job_result: JobResult, user: User) -> tuple[JobResult, bool]:
        """Mark a `JobResult` as revoked, filling in only fields that aren't already set.

        Locks the row and writes whichever of `status`, `date_done`,
        `terminated_by`, and `terminated_at` are still unset.
        Returns early if the row's status doesn't allow revocation updates.

        Args:
            job_result: The `JobResult` to mark revoked.
            user: The user requesting termination, recorded on `terminated_by`
                when that field is unset.

        Returns:
            `(job_result, updated)` where `updated` is True
            if job_result was mark as revoked.
        """
        now = timezone.now()
        with transaction.atomic():
            job_result = JobResult.objects.select_for_update().get(pk=job_result.pk)
            if not self.can_update_revocation_fields(job_result):
                return job_result, False

            updates = {"status": JobResultStatusChoices.STATUS_REVOKED}

            if job_result.date_done is None:
                updates["date_done"] = now

            if job_result.terminated_by is None:
                updates["terminated_by"] = user

            if job_result.terminated_at is None:
                updates["terminated_at"] = now

            for k, v in updates.items():
                setattr(job_result, k, v)

            job_result.save(update_fields=list(updates.keys()))

        return job_result, True

    def terminate(self, job_result, user) -> dict:
        """Reap or kill a job and return the outcome.

        Reaps when `should_reap` is True (no signal sent). Otherwise sends
        the backend kill signal via `_perform_termination`. Exceptions from
        the kill path are caught and reported in the result.

        Args:
            job_result: The `JobResult` to terminate.
            user: The user requesting termination.

        Returns:
            `{"job_result": JobResult, "error": str | None}`. `error` is
            set only when `_perform_termination` raised.
        """
        # REAP
        if self.should_reap(job_result):
            job_result, revoked = self._mark_revoked(job_result, user)
            if revoked:
                logger.info("Reaped dead job %s", job_result.pk)
                return {"job_result": job_result, "error": None}
            else:
                logger.info(
                    "Reaped dead job %s not successed. Job in terminal state %s", job_result.pk, job_result.status
                )
                return {
                    "job_result": job_result,
                    "error": f"Reaped dead not successed. Job in terminal state {job_result.status}",
                }

        # TERMINATE
        try:
            self._perform_termination(job_result, user)
        except Exception as e:
            logger.error("Termination failed for %s: %s", job_result.pk, e)
            return {"job_result": job_result, "error": f"Termination failed: {e}"}

        logger.info("Job %s terminated by %s", job_result.pk, user)
        return {"job_result": job_result, "error": None}


class CeleryStrategy(JobTerminatorStrategy):
    "Termination strategy for jobs running on Celery workers."

    def get_celery_app(self):
        """Return the Nautobot Celery app."""

        # TBD: move it to constructor?
        from nautobot.core.celery import app

        return app

    def is_alive(self, job_result) -> bool | None:
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
            bool | None:
                - True if at least one worker reports the task ID.
                - False if workers respond but none contain the task.
                - None if the worker state could not be determined (e.g., no
                replies or an exception occurred while querying workers).
        """
        try:
            task_id = str(job_result.pk)
            celery_app = self.get_celery_app()
            replies = celery_app.control.inspect().query_task([task_id])
        except Exception as e:
            logger.warning("Failed to query Celery workers: %s", e)
            return None
        if replies is None:
            return None
        # replies shape: {worker_hostname: {task_id: [state, info]}}
        return any(task_id in worker_tasks for worker_tasks in replies.values())

    def should_reap(self, job_result):
        """Return True if the job should be reaped (marked revoked without a kill signal).

        Reap when no worker will handle the job *and* the job isn't already done.
        `not self.is_alive(...)` covers both False (workers replied, none has the
        task) and None (couldn't reach workers at all) — both are treated as
        "no worker will handle this." The `not is_terminal` guard prevents
        reaping a job that already finished normally.

        Args:
            job_result: The `JobResult` to evaluate.

        Returns:
            True if the job should be reaped, False otherwise.
        """
        return not self.is_terminal(job_result) and not self.is_alive(job_result)

    def _perform_termination(self, job_result: JobResult, user: User):
        """Send a SIGKILL revoke to the Celery worker and mark the job revoked.

        Fires a `revoke(terminate=True, signal="SIGKILL")` control message to
        whichever worker holds the task, then records the revocation on the
        `JobResult` via `_mark_revoked`. Any exception from the revoke call
        propagates — the orchestrator in `terminate` catches it and reports
        the failure to the caller.

        Args:
            job_result: The `JobResult` to terminate. Its `pk` is used as the
                Celery task ID.
            user: The user requesting termination, recorded on `terminated_by`.
        """
        if self.is_terminal(job_result):
            return
        task_id = str(job_result.pk)
        celery_app = self.get_celery_app()
        celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")
        self._mark_revoked(job_result, user)


class K8sStrategy(JobTerminatorStrategy):
    """Placeholder for now"""


class TerminatorFactory:
    """Resolve the right termination strategy for a given job queue type."""

    strategies = {JobQueueTypeChoices.TYPE_CELERY: CeleryStrategy, JobQueueTypeChoices.TYPE_KUBERNETES: K8sStrategy}

    @classmethod
    def get_strategy(cls, queue_type: str):
        """Return a strategy instance for `queue_type`.

        Args:
            queue_type: A `JobQueueTypeChoices` value identifying the backend.

        Returns:
            A `JobTerminatorStrategy` subclass instance for `queue_type`.

        Raises:
            ValueError: If `queue_type` is not registered in `strategies`.
        """
        strategy_class = cls.strategies.get(queue_type)
        if not strategy_class:
            raise ValueError(f"Undefined queue type: {queue_type}")
        return strategy_class()
