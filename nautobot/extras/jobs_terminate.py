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
        """Return True if `job_result` is in a finished state."""
        return job_result.status not in self.NON_TERMINAL_STATUSES

    @abstractmethod
    def is_alive(self, job_result: JobResult) -> bool | None:
        """Return True/False if the backend can confirm the job's liveness, None if unknown."""

    @abstractmethod
    def should_reap(self, job_result: JobResult) -> bool:
        """Return True if the job can be marked revoked without sending a kill signal."""

    @abstractmethod
    def _perform_termination(self, job_result: JobResult, user: User):
        """Send the backend-specific kill signal and mark the job revoked."""

    @abstractmethod
    def _record_revoked_on_backend(self, job_result: JobResult):
        """Persist the revoked state to the backend's own state store, post-commit.

        Called via `transaction.on_commit` after the `JobResult` row is
        durably updated. Implementations should be idempotent and must
        handle their own exceptions - failures here cannot roll back
        the DB write.
        """

    def _mark_revoked(self, job_result: JobResult, user: User) -> JobResult:
        """Mark a `JobResult` as revoked and schedule the backend update post-commit.

        Locks the row and re-checks `is_terminal` to avoid racing a worker
        that just finished the job. After the DB write commits, calls
        `_record_revoked_on_backend` for backend-specific bookkeeping.

        Args:
            job_result: The `JobResult` to mark revoked.
            user: The user requesting termination, recorded on `terminated_by`.

        Returns:
            The locked `JobResult`, unchanged if it was already terminal.
        """
        now = timezone.now()
        with transaction.atomic():
            job_result = JobResult.objects.select_for_update().get(pk=job_result.pk)
            if self.is_terminal(job_result):
                return job_result
            job_result.terminated_by = user
            job_result.terminated_at = now
            job_result.save(update_fields=["terminated_by", "terminated_at"])

            transaction.on_commit(lambda: self._record_revoked_on_backend(job_result))

        return job_result

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
            logger.info("Reaped dead job %s", job_result.pk)
            return {"job_result": self._mark_revoked(job_result, user), "error": None}

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
        return not self.is_alive(job_result) and not self.is_terminal(job_result)

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
        task_id = str(job_result.pk)
        celery_app = self.get_celery_app()
        celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")
        self._mark_revoked(job_result, user)

    def _record_revoked_on_backend(self, job_result):
        """Update the Celery result backend.

        The revoke control message is fire-and-forget: the worker normally
        writes REVOKED to the backend as it tears the task down, but if the
        worker is already gone the message goes nowhere. Write the revoked
        state ourselves when the job still looks non-terminal. Backend
        failures are logged, not raised — the DB write is already durable.
        """
        if self.is_terminal(job_result):
            return
        try:
            self.get_celery_app().backend.mark_as_revoked(str(job_result.pk))
        except Exception:
            logger.exception("Failed to mark job %s revoked on Celery backend", job_result.pk)


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
