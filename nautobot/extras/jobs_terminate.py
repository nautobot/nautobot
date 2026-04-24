from abc import ABC
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
    """

    NON_TERMINAL_STATUSES = (
        JobResultStatusChoices.STATUS_PENDING,
        JobResultStatusChoices.STATUS_STARTED,
    )

    def is_terminal(self, job_result: JobResult):
        return job_result.status not in self.NON_TERMINAL_STATUSES

    def is_alive(self, job_result: JobResult) -> bool | None:
        """Is the underlying strategy still aware of this job?"""
        raise NotImplementedError("Subclasses must implement `is_alive`.")

    def should_reap(self, job_result: JobResult) -> bool:
        """Backend-specific check: Can we safely mark dead w/o backend action?

        Returns:
            bool: True if no worker/Pod owns this job (safe to reap).
        """
        raise NotImplementedError("Subclasses must implement `should_reap`.")

    def _mark_revoked(self, job_result: JobResult, user: User):
        raise NotImplementedError("Subclasses must implement `_mark_revoked`.")

    def _perform_termination(self, job_result: JobResult):
        raise NotImplementedError("Subclasses must implement `_perform_termination`.")

    def terminate(self, job_result, user) -> dict:
        """Core termination algorithm (override hooks only).

        Returns:
            dict: {"job_result": JobResult, "error": str | None}
        """
        # REAP
        if self.should_reap(job_result):
            logger.info("Reaped dead job %s", job_result.pk)
            return {"job_result": self._mark_revoked(job_result, user), "error": None}

        # TERMINATE
        try:
            self._perform_termination(job_result)
        except Exception as e:
            logger.error("Termination failed for %s: %s", job_result.pk, e)
            return {"job_result": job_result, "error": f"Termination failed: {e}"}

        logger.info("Job %s terminated by %s", job_result.pk, user)
        return {"job_result": job_result, "error": None}


class CeleryStrategy(JobTerminatorStrategy):
    def get_celery_app(self):
        # TBD: move it to constructor?
        from nautobot.core.celery import app

        return app

    def is_alive(self, job_result) -> bool | None:
        """
        Check whether a Celery worker is currently aware of (and likely processing)
        a given task.

        This method queries active Celery workers using `inspect().query_task`
        to determine if the task associated with the provided ``job_result``
        is still present in any worker's task list.

        Args:
            job_result: An object representing the task result. It is expected
                to have a primary key attribute ``pk`` corresponding to the
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

    def _mark_revoked(self, job_result, user):
        """mark revoked"""
        now = timezone.now()
        with transaction.atomic():
            job_result = JobResult.objects.select_for_update().get(pk=job_result.pk)
            if self.is_terminal(job_result):
                return job_result
            job_result.terminated_by = user
            job_result.terminated_at = now
            job_result.save(update_fields=["terminated_by", "terminated_at"])

            celery_app = self.get_celery_app()

            def _revoke_on_backend():
                try:
                    celery_app.backend.mark_as_revoked(str(job_result.pk))
                except Exception:
                    # DB state is already committed; log loudly so this can
                    # be reconciled, but don't crash the caller.
                    logger.exception("Failed to mark job %s revoked on Celery backend", job_result.pk)

            transaction.on_commit(_revoke_on_backend)

        return job_result

    def _perform_termination(self, job_result: str) -> bool:
        task_id = str(job_result.pk)
        celery_app = self.get_celery_app()
        celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

        # The revoke control message is fire-and-forget: the worker
        # normally writes REVOKED to the backend as it tears the task
        # down, but if the worker is already gone the message goes
        # nowhere. Write the revoked state ourselves when the local
        # view of the job_result still looks non-terminal.

        # job_result.refresh_from_db() maybe will be needed
        if not self.is_terminal(job_result):
            celery_app.backend.mark_as_revoked(str(job_result.pk))

    def should_reap(self, job_result):
        # `not self.is_alive(...)` is True for both False (workers
        # replied, none has the task) and None (couldn't reach workers at
        # all). Both are treated as "no worker will handle this" here.
        # The `not is_terminal` guard prevents reaping a job that already
        # finished normally.
        return not self.is_alive(job_result) and not self.is_terminal(job_result)


class K8sStrategy(JobTerminatorStrategy):
    """Placeholder for now"""



class TerminatorFactory:
    strategies = {JobQueueTypeChoices.TYPE_CELERY: CeleryStrategy, JobQueueTypeChoices.TYPE_KUBERNETES: K8sStrategy}

    @classmethod
    def get_strategy(cls, queue_type: str, **kwargs):
        strategy_class = cls.strategies.get(queue_type)
        if not strategy_class:
            raise ValueError(f"Undefined queue type: {queue_type}")
        return strategy_class(**kwargs)
