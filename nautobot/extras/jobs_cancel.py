from abc import ABC, abstractmethod
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
import logging
from typing import Callable

from django.conf import settings
from django.db import transaction
from django.utils import timezone
import kubernetes.client

from nautobot.core.celery import app as celery_app
from nautobot.extras.choices import (
    JobCancelTypeChoices,
    JobQueueTypeChoices,
    JobResultStatusChoices,
    LogLevelChoices,
)
from nautobot.extras.models import Job, JobResult
from nautobot.extras.utils import build_kubernetes_api_client
from nautobot.users.models import User

logger = logging.getLogger(__name__)


def user_can_cancel_job_result(user, job_result):
    """Return whether `user` may cancel `job_result`.

    The submitter can always cancel their own job, without needing any
    permission. Anyone else needs the `extras.cancel_job` permission scoped
    to the specific Job.
    """
    if job_result.user == user:
        return True
    if job_result.job_model_id is None:
        # The associated Job is gone, so it can never run. Anyone with cancel_job
        # (even constrained) may clean it up, since there is no Job left to scope against.
        return user.has_perm("extras.cancel_job")
    return Job.objects.restrict(user, "cancel").filter(pk=job_result.job_model_id).exists()


class JobAlreadyTerminal(Exception):
    """Control-flow signal: the `JobResult` has already left the `unready`
    state, so there is nothing to cancel.

    Raised from `locked_unready_job_result` when the freshly-locked row is no longer
    in an unready state.
    """

    def __init__(self, job_result: JobResult):
        self.job_result = job_result
        super().__init__(f"Job {job_result.pk} already in terminal state {job_result.status}")


class JobLiveness(Enum):
    RUNNING = "running"
    NOT_RUNNING = "not_running"
    UNKNOWN = "unknown"

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").upper()


class JobCancelStrategy(ABC):
    """Abstract base class for job termination strategies across different queues.

    Defines the interface for various backends (Celery, Kubernetes, etc.).
    Subclasses implement the `is_alive`, 'perform_reap`, and
    `perform_termination` hooks; `cancel` orchestrates them.
    """

    @abstractmethod
    def liveness(self, job_result: JobResult) -> JobLiveness:
        """Report the job's liveness as observed by the backend.

        Args:
            job_result (JobResult): The job to check.

        Returns:
            JobLiveness: One of:
                - JobLiveness.RUNNING: Backend confirms the job is currently executing.
                - JobLiveness.NOT_RUNNING: Backend confirms the job is not executing
                (e.g., worker not aware of it, pod terminated).
                - JobLiveness.UNKNOWN: Backend could not be queried; liveness cannot be determined.
        """

    @abstractmethod
    def perform_reap(self, job_result: JobResult, user: User) -> bool:
        """Reap a job: mark it canceled without claiming we killed live work."""

    @abstractmethod
    def perform_termination(self, job_result: JobResult, user: User) -> bool:
        """Send the backend-specific kill signal and mark the job canceled."""

    def perform_abandon(self, job_result, user) -> bool:
        """Abandon a job whose backend is unreachable: mark canceled without
        confirming its actual state. No kill signal is sent — if the job is
        still executing somewhere, it will continue until it finishes on its own.
        """
        logger.info("Abandoned job %s by %s", job_result.pk, user)
        job_result.log(
            f"Abandoned job {job_result.pk} by {user}",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="canceling",
        )
        self._mark_canceled(job_result, user, JobCancelTypeChoices.TYPE_ABANDONED)
        return True

    @contextmanager
    def locked_unready_job_result(self, job_result: JobResult):
        """Yield the `JobResult` re-fetched and locked with SELECT FOR UPDATE,
        guaranteed to be in the `unready` state.

        If the row has already settled into a terminal state, this raises
        `JobAlreadyTerminal` instead of yielding, so callers never operate on
        a terminal job. The no-op is logged only after the lock is released,
        since `job_result.log()` writes via a separate connection and would
        deadlock against the held row lock. The lock is held until the
        surrounding transaction commits.

        Raises:
            JobAlreadyTerminal: The locked row is no longer in an unready state.
        """
        try:
            with transaction.atomic():
                locked = JobResult.objects.select_for_update().get(pk=job_result.pk)
                if not locked.is_unready_state:
                    raise JobAlreadyTerminal(locked)
                yield locked
        except JobAlreadyTerminal as e:
            self._log_already_terminal(e.job_result)
            raise

    def _log_already_terminal(self, job_result: JobResult) -> None:
        """Single place that phrases the 'already in a terminal state' no-op."""
        logger.info(
            "Job %s is already in terminal state `%s`, no action was taken.",
            job_result.pk,
            job_result.status,
        )
        job_result.log(
            f"Job {job_result.pk} is already in terminal state `{job_result.status}`, no action was taken",
            grouping="canceling",
        )

    def _apply_cancel_metadata(
        self, job_result: JobResult, user: User, cancel_type: str, now_timestamp: datetime | None = None
    ) -> set[str]:
        """Fill in termination metadata fields on a locked `JobResult`.

        Sets `date_done`, `date_canceled`, `canceled_by`, `canceled_by_user_name`, and
        only if they are not already set. Caller is responsible
        for the surrounding transaction/lock and for calling `save()`.

        Args:
            job_result: The locked `JobResult` to update (modified in place).
            user: The user requesting termination.
            cancel_type: cancel type based on `JobCancelTypeChoices`.
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

        if job_result.date_canceled is None:
            job_result.date_canceled = now_timestamp
            changed.add("date_canceled")

        if job_result.canceled_by is None:
            job_result.canceled_by = user
            changed.add("canceled_by")

        if not job_result.canceled_by_user_name:
            job_result.canceled_by_user_name = user.username
            changed.add("canceled_by_user_name")

        if not job_result.cancel_type:
            job_result.cancel_type = cancel_type
            changed.add("cancel_type")

        return changed

    def _mark_canceled(self, job_result: JobResult, user: User, cancel_type: str) -> JobResult:
        """Mark a `JobResult` as canceled, filling in only fields that aren't already set.

        Re-fetches and locks the row via `locked_unready_job_result`; if the job has
        already settled into a terminal state, `JobAlreadyTerminal` propagates
        """
        with self.locked_unready_job_result(job_result) as locked_job_result:
            changed = self._apply_cancel_metadata(locked_job_result, user, cancel_type)
            locked_job_result.status = JobResultStatusChoices.STATUS_REVOKED
            changed |= {"status"}
            locked_job_result.save(update_fields=list(changed))
            return locked_job_result

    def _resolve_action(self, liveness: JobLiveness) -> tuple[Callable, str]:
        """Map liveness to the matching `perform_*` method and cancel type.

        Args:
            liveness: The result of `self.liveness(job_result)`.

        Returns:
            Tuple `(action, cancel_type)` where `action` is the bound
            `perform_*` method to invoke and `cancel_type` is the matching
            `JobCancelTypeChoices` value to record.
        """
        return {
            JobLiveness.RUNNING: (self.perform_termination, JobCancelTypeChoices.TYPE_TERMINATED),
            JobLiveness.NOT_RUNNING: (self.perform_reap, JobCancelTypeChoices.TYPE_REAPED),
            JobLiveness.UNKNOWN: (self.perform_abandon, JobCancelTypeChoices.TYPE_ABANDONED),
        }[liveness]

    def cancel(self, job_result, user) -> dict:
        """Terminate, reap, or abandon a job and return the outcome.

        Dispatches based on `self.liveness(job_result)`:
            - JobLiveness.RUNNING: perform_termination (send kill signal)
            - JobLiveness.NOT_RUNNING: perform_reap (worker is gone; mark canceled)
            - JobLiveness.UNKNOWN: perform_abandon (backend unreachable; mark canceled)

        Exceptions from the chosen action are caught and reported in `error`.

        Args:
            job_result: The job result object to cancel.
            user: The user requesting the cancel.

        Returns:
            dict: A dictionary containing:
                - job_result (JobResult): The updated job result.
                - error (str | None): Error message if an exception occurred.
                - canceled (bool): Whether the job was successfully marked as canceled.
        """
        base = {
            "job_result": job_result,
            "error": None,
            "canceled": False,
        }

        if not job_result.is_unready_state:
            self._log_already_terminal(job_result)
            return base

        job_liveness_state = self.liveness(job_result)
        action, cancel_type = self._resolve_action(job_liveness_state)

        try:
            canceled = action(job_result, user)
        except JobAlreadyTerminal:
            return base
        except Exception as e:
            cancel_label = {"terminated": "Termination", "reaped": "Reap", "abandoned": "Abandon"}
            logger.error("%s failed for %s: %s", cancel_label[cancel_type], job_result.pk, e)
            job_result.log(
                f"{cancel_label[cancel_type]} failed for {job_result.pk}: {e}",
                level_choice=LogLevelChoices.LOG_ERROR,
                grouping="canceling",
            )
            return {**base, "error": f"{cancel_label[cancel_type]} failed: {e}"}

        return {
            **base,
            "canceled": canceled,
        }


class CeleryStrategy(JobCancelStrategy):
    "Termination strategy for jobs running on Celery workers."

    def liveness(self, job_result) -> JobLiveness:
        """
        Check whether a Celery worker is currently aware of (and likely processing)
        a given task.

        This method queries active Celery workers using `inspect().query_task`
        to determine if the task associated with the provided `job_result`
        is still present in any worker's task list.

        Args:
            job_result: The task result. Its `pk` is used as the Celery task ID.

        Returns:
            JobLiveness: One of:
                - JobLiveness.RUNNING: Backend confirms the job is currently executing.
                - JobLiveness.NOT_RUNNING: Backend confirms the job is not executing
                (e.g., worker not aware of it, pod terminated).
                - JobLiveness.UNKNOWN: Backend could not be queried; liveness cannot be determined.
        """
        try:
            task_id = str(job_result.pk)
            replies = celery_app.control.inspect().query_task([task_id])
        except Exception as e:
            logger.warning("Failed to query Celery workers: %s", e)
            job_result.log(
                f"Failed to query Celery workers: {e}",
                level_choice=LogLevelChoices.LOG_ERROR,
                grouping="canceling",
            )
            return JobLiveness.UNKNOWN

        if replies is None:
            return JobLiveness.NOT_RUNNING

        # replies shape: {worker_hostname: {task_id: [state, info]}}
        found = any(task_id in worker_tasks for worker_tasks in replies.values())
        return JobLiveness.RUNNING if found else JobLiveness.NOT_RUNNING

    def perform_reap(self, job_result, user) -> bool:
        """Reap a dead Celery job: mark canceled without sending a signal.

        Called when no worker is processing the task. Records cancel metadata
        and stamps a Celery-shaped `result` payload imitating what a worker
        would write on TaskCanceledError, so the JobResult looks the same as
        normally-canceled tasks for downstream consumers.
        """
        logger.info("Reaped dead job %s by %s", job_result.pk, user)
        job_result.log(
            f"Reaped dead job {job_result.pk} by {user}",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="canceling",
        )

        job_result = self._mark_canceled(job_result, user, JobCancelTypeChoices.TYPE_REAPED)

        return True

    def perform_termination(self, job_result: JobResult, user: User):
        """Send a SIGKILL cancel to the Celery worker and mark the job canceled.

        Fires a `cancel(terminate=True, signal="SIGKILL")` control message to
        whichever worker holds the task, then records the cancel on the
        `JobResult` via `_apply_cancel_metadata`. Any exception from the cancel call
        propagates — the orchestrator in `cancel` catches it and reports
        the failure to the caller.

        Args:
            job_result: The `JobResult` to terminate. Its `pk` is used as the
                Celery task ID.
            user: The user requesting termination, recorded on `canceled_by`.
        """
        task_id = str(job_result.pk)
        with self.locked_unready_job_result(job_result) as locked_job_result:
            changed = self._apply_cancel_metadata(locked_job_result, user, JobCancelTypeChoices.TYPE_TERMINATED)
            locked_job_result.save(update_fields=list(changed))
            celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

        logger.info("Job %s terminated by %s", job_result.pk, user)
        job_result.log(
            f"Job {job_result.pk} terminated by {user}", level_choice=LogLevelChoices.LOG_FAILURE, grouping="canceling"
        )
        return True


class K8sStrategy(JobCancelStrategy):
    def _job_name(self, job_result: JobResult) -> str:
        """Recreate the K8s Job name that was used at submission time."""
        return f"{settings.KUBERNETES_JOB_POD_NAME}-{job_result.pk}"

    def _delete_k8s_job(self, job_result: JobResult) -> bool:
        """Delete a K8s Job and its pods (Background propagation).

        Returns:
            bool:
                True: delete request was accepted by the API server.
                False: job was already gone (404).
        Other ApiExceptions (401/403/5xx) propagate.
        """
        job_name = self._job_name(job_result)
        namespace = settings.KUBERNETES_JOB_POD_NAMESPACE

        # Background - allow the garbage collector to delete the dependents in the background
        # grace_period_seconds - The duration in seconds before the object should be deleted.
        # Value must be non-negative integer. The value zero indicates delete immediately
        delete_options = kubernetes.client.V1DeleteOptions(
            propagation_policy="Background",
            grace_period_seconds=0,
        )
        try:
            with build_kubernetes_api_client() as api_client:
                api = kubernetes.client.BatchV1Api(api_client)
                api.delete_namespaced_job(
                    name=job_name,
                    namespace=namespace,
                    body=delete_options,
                )
            logger.info("Deleted K8s job %s", job_name)
            return True
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                logger.info("K8s job %s already gone", job_name)
                return False
            raise

    def _read_k8s_job(self, api_client, job_name, namespace):
        """Return the K8s Job object, or None if it doesn't exist (404)."""
        batch_api = kubernetes.client.BatchV1Api(api_client)
        try:
            return batch_api.read_namespaced_job(name=job_name, namespace=namespace)
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                return None
            raise

    def _read_first_pod_for_job(self, api_client, job_name, namespace):
        """Return the first pod for this job, or None if there isn't one yet."""
        core_api = kubernetes.client.CoreV1Api(api_client)
        pods = core_api.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"job-name={job_name}",
            limit=1,
        )
        return pods.items[0] if pods.items else None

    def liveness(self, job_result) -> JobLiveness:
        """Report whether the Kubernetes Job for this `job_result` is still progressing.

        Looks up the Kubernetes Job and its first pod by name, then inspects
        the container state to determine liveness.

        Args:
            job_result: The job result associated with the Kubernetes Job.

        Returns:
            JobLiveness: One of:
                - JobLiveness.RUNNING: Job exists, has a pod, and the container is in a running state.
                - JobLiveness.NOT_RUNNING: Job is missing (404), failed, has no pod yet,
                lacks container status, or the container is waiting or terminated.
                - JobLiveness.UNKNOWN: Kubernetes API returned a non-404 error; state cannot be determined.
        """
        job_name = self._job_name(job_result)
        namespace = settings.KUBERNETES_JOB_POD_NAMESPACE

        try:
            with build_kubernetes_api_client() as api_client:
                k8s_job = self._read_k8s_job(api_client, job_name, namespace)
                if k8s_job is None or k8s_job.status.failed:
                    return JobLiveness.NOT_RUNNING

                pod = self._read_first_pod_for_job(api_client, job_name, namespace)
                if pod is None:
                    return JobLiveness.NOT_RUNNING
        except kubernetes.client.exceptions.ApiException as e:
            if e.status == 404:
                return JobLiveness.NOT_RUNNING
            logger.warning("Kubernetes API error while checking job %s: %s", job_name, e)
            job_result.log(
                f"Kubernetes API error while checking job {job_name}: {e}",
                level_choice=LogLevelChoices.LOG_ERROR,
                grouping="canceling",
            )
            return JobLiveness.UNKNOWN

        # container_statuses can be None/[] while the pod is being scheduled.
        # We use [0] because our pod_manifest only defines one container under
        # spec.template.spec.containers.
        container_statuses = pod.status.container_statuses
        if not container_statuses:
            return JobLiveness.NOT_RUNNING

        # running, terminated, waiting
        is_running = bool(container_statuses[0].state.running)
        return JobLiveness.RUNNING if is_running else JobLiveness.NOT_RUNNING

    def perform_reap(self, job_result: JobResult, user: User) -> bool:
        """Reap a dead K8s job: clean up leftover resources, then mark JobResult canceled."""

        # Ideally, this operation has no effect
        # Functions in k8s, such as `ttlSecondsAfterFinished` or others
        # should already have deleted the job and its associated pods
        # but there are a few cases where this does not happen
        # That is why it is good to have this cleanup mechanism here as well
        deleted = self._delete_k8s_job(job_result)
        job_name = self._job_name(job_result)

        if not deleted:
            # 404 — JobResult may have already settled into a terminal state
            if not job_result.is_unready_state:
                logger.info(
                    "Job %s already in terminal state %s, no action taken.",
                    job_result.pk,
                    job_result.status,
                )
                job_result.log(
                    f"Job {job_result.pk} already in terminal state {job_result.status}, no action taken",
                    grouping="canceling",
                )
                return False

        job_result.log(
            f"Reaped dead K8s job {job_name} by {user}",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="canceling",
        )
        self._mark_canceled(job_result, user, JobCancelTypeChoices.TYPE_REAPED)
        return True

    def perform_termination(self, job_result: JobResult, user: User) -> bool:
        """Delete the K8s job and mark the JobResult canceled and set date_canceled."""

        deleted = self._delete_k8s_job(job_result)
        if not deleted:
            # 404 race — K8s job was deleted between is_alive and manual delete.
            # Success-path handler may have already updated JobResult.
            if not job_result.is_unready_state:
                logger.info(
                    "Job %s already in terminal state %s, no action taken.",
                    job_result.pk,
                    job_result.status,
                )
                job_result.log(
                    f"Job {job_result.pk} already in terminal state {job_result.status}, no action taken",
                    grouping="canceling",
                )
                return False

        self._mark_canceled(job_result, user, JobCancelTypeChoices.TYPE_TERMINATED)
        logger.info("Job %s terminated by %s", job_result.pk, user)
        job_result.log(
            f"Job {job_result.pk} terminated by {user}", level_choice=LogLevelChoices.LOG_FAILURE, grouping="canceling"
        )
        return True


class UnknownStrategy(JobCancelStrategy):
    """Fallback strategy for queue types without a registered backend.

    There is no backend to query for liveness, so liveness is always `UNKNOWN` and the orchestrator routes
    the request to `perform_abandon`.
    """

    def liveness(self, job_result) -> JobLiveness:
        """Always return False. There is no backend to query for liveness."""
        return JobLiveness.UNKNOWN

    def perform_reap(self, job_result, user) -> bool:
        """No-op; never reached. `liveness` is always `UNKNOWN`, so the
        orchestrator routes to `perform_abandon` instead."""
        return False

    def perform_termination(self, job_result: JobResult, user: User) -> bool:
        """No-op; never reached. `liveness` is always `UNKNOWN`, so the
        orchestrator routes to `perform_abandon` instead."""
        return False


class CancelFactory:
    """Resolve the right cancel strategy for a given job queue type."""

    strategies = {JobQueueTypeChoices.TYPE_CELERY: CeleryStrategy, JobQueueTypeChoices.TYPE_KUBERNETES: K8sStrategy}

    @classmethod
    def get_strategy(cls, queue_type: str):
        """Return a strategy instance for `queue_type`.

        Unknown queue types fall back to `UnknownStrategy`, which reaps the
        job (marks it canceled) without attempting any backend-specific signal.
        """
        strategy_class = cls.strategies.get(queue_type, UnknownStrategy)
        return strategy_class()
