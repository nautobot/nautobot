"""Backend-agnostic task execution interface for Nautobot Jobs.

One built-in implementation lives under this package:
    - nautobot.core.task_backends.celery_backend.CeleryBackend

Additional backends can be plugged in by setting NAUTOBOT_TASK_BACKEND to a
dotted import path of a ``TaskBackend`` subclass. The active backend is
resolved via ``nautobot.core.task_backends.get_task_backend()``.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterable, Optional
from uuid import UUID

if TYPE_CHECKING:
    from nautobot.extras.models.jobs import JobResult


@dataclass(frozen=True)
class DispatchResult:
    """Return value of ``TaskBackend.enqueue()`` / ``TaskBackend.enqueue_sync()``.

    Carries identifiers and metadata about the dispatched task. The
    canonical authoritative state of the job lives on the ``JobResult`` model;
    this object is informational and primarily useful for logging / debugging.
    """

    task_id: UUID  # JobResult.task_id (same value used as Celery task_id under CeleryBackend)
    backend: str   # name of the backend that handled dispatch (e.g. "celery")


@dataclass
class EnqueueOptions:
    """All optional dispatch knobs for a single job execution.

    Backends consume the fields they understand and ignore the rest. Fields that
    map directly to Celery ``apply_async()`` kwargs (queue, soft_time_limit,
    time_limit) are reproduced verbatim. Fields prefixed with ``nautobot_job_``
    in the legacy Celery kwargs are exposed here as plain attributes.
    """

    queue: Optional[str] = None
    soft_time_limit: Optional[float] = None
    time_limit: Optional[float] = None
    profile: bool = False
    console_log: bool = False
    ignore_singleton_lock: bool = False
    user_id: Optional[UUID] = None
    job_model_id: Optional[UUID] = None
    schedule_id: Optional[UUID] = None
    # Branch name for the nautobot_version_control plugin. Backends install
    # this at task start; CeleryBackend does it via NautobotTask.
    branch_name: Optional[str] = None
    # Escape hatch for backend-specific knobs we don't know about yet.
    # CeleryBackend folds these into the apply_async() **kwargs; backends that
    # don't understand a key are free to ignore it.
    extra: dict = field(default_factory=dict)


class TaskBackend(abc.ABC):
    """Backend-agnostic interface for enqueueing and inspecting Nautobot Jobs.

    Implementations MUST guarantee:
        - Jobs run inside Django's normal context (DB connection, settings, etc.)
        - BaseJob lifecycle hooks fire in this order:
              before_start  ->  __call__ (which calls run)  ->  on_success/on_failure
              ->  after_return
        - JobResult.status transitions: PENDING -> STARTED -> SUCCESS|FAILURE|REVOKED
        - JobLogEntry records are populated via NautobotDatabaseHandler (or
          an equivalent that writes to the same model)
    """

    name: str  # subclass sets to e.g. "celery"

    @abc.abstractmethod
    def enqueue(
        self,
        *,
        job_result_id: UUID,
        job_class_path: str,
        args: Iterable[Any],
        kwargs: dict[str, Any],
        options: EnqueueOptions,
    ) -> DispatchResult:
        """Dispatch a job for asynchronous execution.

        The caller is responsible for wrapping this in
        ``transaction.on_commit(lambda: ...)`` if the JobResult was just created
        in the same transaction. Backends do not assume autocommit.
        """

    @abc.abstractmethod
    def enqueue_sync(
        self,
        *,
        job_result_id: UUID,
        job_class_path: str,
        args: Iterable[Any],
        kwargs: dict[str, Any],
        options: EnqueueOptions,
    ) -> DispatchResult:
        """Run a job synchronously in the calling process.

        Used by CELERY_TASK_ALWAYS_EAGER mode and by
        ``JobResult.enqueue_job(synchronous=True)``.

        Implementations MUST update the JobResult in place to its terminal state
        (status, date_done, result/traceback) before returning. The caller relies
        on this to render the synchronous-execution UI response.
        """

    @abc.abstractmethod
    def get_active_workers(self) -> int:
        """Return active worker count for the StatusView health check.

        Return -1 if the backend cannot determine this; the StatusView will
        surface that as "unknown".
        """

    def get_periodic_runner(self) -> "PeriodicRunner | None":
        """Return the periodic-task runner for this backend, or None if scheduling
        is handled out-of-band (e.g., ``celery beat`` as a separate process).

        CeleryBackend returns None — celery beat runs as a separate service.
        Backends without a separate scheduler process can return a runner that
        reads ``ScheduledJob`` rows and enqueues due jobs on each tick.
        """
        return None


class PeriodicRunner(abc.ABC):
    """Runs ScheduledJob rows on schedule.

    Separate from TaskBackend because backends that delegate scheduling to an
    external process (e.g., CeleryBackend → celery beat) don't need to
    implement this; only backends that include their own DB-row-driven
    scheduler do.
    """

    @abc.abstractmethod
    def tick(self) -> int:
        """Examine ScheduledJob rows whose next-run time has elapsed and enqueue them.

        Returns the number of jobs enqueued this tick.
        """
