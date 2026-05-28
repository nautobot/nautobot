from abc import ABC, abstractmethod
from datetime import datetime
from enum import StrEnum
import logging
from typing import Callable

from celery.exceptions import TaskRevokedError
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import kubernetes.client

from nautobot.core.celery import app as celery_app
from nautobot.core.utils.logging import sanitize
from nautobot.extras.choices import (
    JobQueueTypeChoices,
    JobResultStatusChoices,
    JobRevocationTypeChoices,
    LogLevelChoices,
)
from nautobot.extras.models import JobResult
from nautobot.extras.utils import build_kubernetes_api_client
from nautobot.users.models import User

logger = logging.getLogger(__name__)


class JobLiveness(StrEnum):
    RUNNING = "running"
    NOT_RUNNING = "not_running"
    UNKNOWN = "unknown"

    @property
    def display(self) -> str:
        return self.value.replace("_", " ").upper()


class JobRevokeStrategy(ABC):
    """Abstract base class for job termination strategies across different queues.

    Defines the interface for various backends (Celery, Kubernetes, etc.).
    Subclasses implement the `is_alive`, 'perform_reap`, and
    `perform_termination` hooks; `revoke` orchestrates them.
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
        """Reap a job: mark it revoked without claiming we killed live work."""

    @abstractmethod
    def perform_termination(self, job_result: JobResult, user: User) -> bool:
        """Send the backend-specific kill signal and mark the job revoked."""

    def perform_abandon(self, job_result, user) -> bool:
        """Abandon a job whose backend is unreachable: mark revoked without
        confirming its actual state. No kill signal is sent — if the job is
        still executing somewhere, it will continue until it finishes on its own.
        """
        logger.info("Abandoned job %s by %s", job_result.pk, user)
        job_result.log(
            f"Abandoned job {job_result.pk} by {user}",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="revoking",
        )
        self._mark_revoked(job_result, user, JobRevocationTypeChoices.TYPE_ABANDONED)
        return True

    def _apply_termination_metadata(
        self, job_result: JobResult, user: User, revocation_type: str, now_timestamp: None | datetime = None
    ) -> set[str]:
        """Fill in termination metadata fields on a locked `JobResult`.

        Sets `date_done`, `revoked_by`, `revoked_by_user_name`, and
        only if they are not already set. Caller is responsible
        for the surrounding transaction/lock and for calling `save()`.

        Args:
            job_result: The locked `JobResult` to update (modified in place).
            user: The user requesting termination.
            revocation_type: revocation type based on `JobRevocationTypeChoices`.
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

        if not job_result.revocation_type:
            job_result.revocation_type = revocation_type
            changed.add("revocation_type")

        return changed

    def _mark_revoked(self, job_result: JobResult, user: User, revocation_type: str) -> tuple[JobResult, bool]:
        """Mark a `JobResult` as revoked, filling in only fields that aren't already set."""
        with transaction.atomic():
            job_result = JobResult.objects.select_for_update().get(pk=job_result.pk)
            changed = self._apply_termination_metadata(job_result, user, revocation_type)

            job_result.status = JobResultStatusChoices.STATUS_REVOKED
            changed |= {"status"}

            job_result.save(update_fields=list(changed))

        return job_result

    def _resolve_action(self, liveness: JobLiveness) -> tuple[Callable, str]:
        """Map liveness to the matching `perform_*` method and revocation type.

        Args:
            liveness: The result of `self.liveness(job_result)`.

        Returns:
            Tuple `(action, revocation_type)` where `action` is the bound
            `perform_*` method to invoke and `revocation_type` is the matching
            `JobRevocationTypeChoices` value to record.
        """
        return {
            JobLiveness.RUNNING: (self.perform_termination, JobRevocationTypeChoices.TYPE_TERMINATED),
            JobLiveness.NOT_RUNNING: (self.perform_reap, JobRevocationTypeChoices.TYPE_REAPED),
            JobLiveness.UNKNOWN: (self.perform_abandon, JobRevocationTypeChoices.TYPE_ABANDONED),
        }[liveness]

    def revoke(self, job_result, user) -> dict:
        """Terminate, reap, or abandon a job and return the outcome.

        Dispatches based on `self.liveness(job_result)`:
            - JobLiveness.RUNNING: perform_termination (send kill signal)
            - JobLiveness.NOT_RUNNING: perform_reap (worker is gone; mark revoked)
            - JobLiveness.UNKNOWN: perform_abandon (backend unreachable; mark revoked)

        Exceptions from the chosen action are caught and reported in `error`.

        Args:
            job_result: The job result object to revoke.
            user: The user requesting the revocation.

        Returns:
            dict: A dictionary containing:
                - job_result (JobResult): The updated job result.
                - error (str | None): Error message if an exception occurred.
                - revoked (bool): Whether the job was successfully marked as revoked.
        """
        base = {
            "job_result": job_result,
            "error": None,
            "revoked": False,
        }

        if not job_result.is_unready_state:
            logger.info(
                "Job %s is already in terminated state `%s` no action was taken.", job_result.pk, job_result.status
            )
            job_result.log(
                f"Job {job_result.pk} is already in terminated state `{job_result.status}` no action was taken",
                grouping="revoking",
            )
            return base

        job_liveness_state = self.liveness(job_result)
        action, revocation_type = self._resolve_action(job_liveness_state)

        try:
            revoked = action(job_result, user)
        except Exception as e:
            revocation_label = {"terminated": "Termination", "reaped": "Reap", "abandoned": "Abandon"}
            logger.error("%s failed for %s: %s", revocation_label[revocation_type], job_result.pk, e)
            job_result.log(
                f"{revocation_label[revocation_type]} failed for {job_result.pk}: {e}",
                level_choice=LogLevelChoices.LOG_ERROR,
                grouping="revoking",
            )
            return {**base, "error": f"{revocation_label[revocation_type]} failed: {e}"}

        return {
            **base,
            "revoked": revoked,
        }


class CeleryStrategy(JobRevokeStrategy):
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
                level_choice=LogLevelChoices.LOG_WARNING,
                grouping="revoking",
            )
            return JobLiveness.UNKNOWN

        if replies is None:
            return JobLiveness.NOT_RUNNING

        # replies shape: {worker_hostname: {task_id: [state, info]}}
        found = any(task_id in worker_tasks for worker_tasks in replies.values())
        return JobLiveness.RUNNING if found else JobLiveness.NOT_RUNNING

    def perform_reap(self, job_result, user) -> bool:
        """Reap a dead Celery job: mark revoked without sending a signal.

        Called when no worker is processing the task. Records revoke metadata
        and stamps a Celery-shaped `result` payload imitating what a worker
        would write on TaskRevokedError, so the JobResult looks the same as
        normally-revoked tasks for downstream consumers.
        """
        logger.info("Reaped dead job %s by %s", job_result.pk, user)
        job_result.log(
            f"Reaped dead job {job_result.pk} by {user}",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="revoking",
        )

        with transaction.atomic():
            job_result = self._mark_revoked(job_result, user, JobRevocationTypeChoices.TYPE_REAPED)

            exc = TaskRevokedError("revoked")
            job_result.result = {
                "exc_type": type(exc).__name__,
                "exc_module": "celery.exceptions",
                "exc_message": [sanitize(str(exc))],
            }
            job_result.save(update_fields=["result"])

        return True

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
            changed = self._apply_termination_metadata(job_result, user, JobRevocationTypeChoices.TYPE_TERMINATED, now)

            job_result.date_revoked = now
            changed.add("date_revoked")

            job_result.save(update_fields=list(changed))

            celery_app.control.revoke(task_id, terminate=True, signal="SIGKILL")

        logger.info("Job %s terminated by %s", job_result.pk, user)
        job_result.log(
            f"Job {job_result.pk} terminated by {user}", level_choice=LogLevelChoices.LOG_FAILURE, grouping="revoking"
        )
        return True


class K8sStrategy(JobRevokeStrategy):
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
                level_choice=LogLevelChoices.LOG_WARNING,
                grouping="revoking",
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
        """Reap a dead K8s job: clean up leftover resources, then mark JobResult revoked."""

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
                    grouping="revoking",
                )
                return False

        job_result.log(
            f"Reaped dead K8s job {job_name} by {user}",
            level_choice=LogLevelChoices.LOG_FAILURE,
            grouping="revoking",
        )
        self._mark_revoked(job_result, user, JobRevocationTypeChoices.TYPE_REAPED)
        return True

    def perform_termination(self, job_result: JobResult, user: User) -> bool:
        """Delete the K8s job and mark the JobResult revoked and set date_revoked."""

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
                    grouping="revoking",
                )
                return False

        with transaction.atomic():
            now = timezone.now()
            job_result = self._mark_revoked(job_result, user, JobRevocationTypeChoices.TYPE_TERMINATED)
            job_result.date_revoked = now
            job_result.save(update_fields=["date_revoked"])

        logger.info("Job %s terminated by %s", job_result.pk, user)
        job_result.log(
            f"Job {job_result.pk} terminated by {user}", level_choice=LogLevelChoices.LOG_FAILURE, grouping="revoking"
        )
        return True


class UnknownStrategy(JobRevokeStrategy):
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
