"""Celery implementation of the TaskBackend interface.

This is a thin wrapper around the existing Celery glue in ``nautobot.core.celery``.
It does NOT introduce new behavior; it relocates dispatch logic that previously
lived in ``JobResult.enqueue_job()`` into a backend-shaped surface.

The Celery app, NautobotTask base class, signal handlers, scheduler, custom
Kombu serializer, and worker control commands all remain in ``nautobot.core.celery``.
``CeleryBackend`` just calls into them.
"""
from __future__ import annotations

import contextlib
import signal
from typing import TYPE_CHECKING, Any, Iterable
from uuid import UUID

from celery.app.log import get_logger
from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import LoggingProxy

from .base import DispatchResult, EnqueueOptions, TaskBackend

if TYPE_CHECKING:
    pass


def _build_celery_kwargs_dict(options: EnqueueOptions) -> dict[str, Any]:
    """Reconstruct the legacy ``nautobot_job_*`` kwargs dict from EnqueueOptions.

    The legacy dict is the interchange format between Nautobot's job lifecycle
    code and the NautobotTask base class; the scheduler constructs the same
    shape. Kept here to preserve exact pre-existing dispatch behavior.
    """
    job_celery_kwargs: dict[str, Any] = {
        "nautobot_job_job_model_id": str(options.job_model_id) if options.job_model_id else None,
        "nautobot_job_profile": options.profile,
        "nautobot_job_user_id": str(options.user_id) if options.user_id else None,
        "nautobot_job_ignore_singleton_lock": options.ignore_singleton_lock,
        "nautobot_job_console_log": options.console_log,
        "queue": options.queue,
    }
    if options.schedule_id is not None:
        job_celery_kwargs["nautobot_job_schedule_id"] = options.schedule_id
    if options.soft_time_limit is not None:
        job_celery_kwargs["soft_time_limit"] = options.soft_time_limit
    if options.time_limit is not None:
        job_celery_kwargs["time_limit"] = options.time_limit
    # Caller-supplied overrides. Mirrors the existing celery_kwargs override behavior
    # in the old enqueue_job: keys in `extra` can shadow defaults like `queue`.
    if options.extra:
        job_celery_kwargs.update(options.extra)
    return job_celery_kwargs


class CeleryBackend(TaskBackend):
    """Celery-backed task dispatch."""

    name = "celery"

    # --- enqueue (async) ---

    def enqueue(
        self,
        *,
        job_result_id: UUID,
        job_class_path: str,
        args: Iterable[Any],
        kwargs: dict[str, Any],
        options: EnqueueOptions,
    ) -> DispatchResult:
        # Local import to dodge the circular import between
        # nautobot.core.celery and nautobot.extras.jobs.
        from nautobot.extras.jobs import run_console_log_job_and_return_job_result, run_job

        celery_kwargs = _build_celery_kwargs_dict(options)
        task = run_console_log_job_and_return_job_result if options.console_log else run_job

        task.apply_async(
            args=[job_class_path, *list(args)],
            kwargs=kwargs,
            task_id=str(job_result_id),
            **celery_kwargs,
        )
        return DispatchResult(task_id=job_result_id, backend=self.name)

    # --- enqueue_sync ---

    def enqueue_sync(
        self,
        *,
        job_result_id: UUID,
        job_class_path: str,
        args: Iterable[Any],
        kwargs: dict[str, Any],
        options: EnqueueOptions,
    ) -> DispatchResult:
        # Lazy imports preserve the circular-import dance the original code dealt with.
        from nautobot.core.celery import app, setup_nautobot_job_logging
        from nautobot.extras.choices import JobResultStatusChoices
        from nautobot.extras.jobs import run_job
        from nautobot.extras.models.jobs import JobResult
        from django.utils import timezone

        job_result = JobResult.objects.get(id=job_result_id)
        # Pre-execution: mark started. (Async path does this inside NautobotTask.before_start.)
        job_result.date_started = timezone.now()
        job_result.status = JobResultStatusChoices.STATUS_STARTED
        job_result.save()

        # Synchronous tasks bypass the worker, so the celery.task / celery.redirected
        # logger handlers normally installed by the worker boot signal aren't attached.
        # Install the NautobotDatabaseHandler explicitly so JobLogEntry rows are still created.
        setup_nautobot_job_logging(None, None, app.conf)

        celery_kwargs = _build_celery_kwargs_dict(options)

        def alarm_handler(*_args, **_kwargs):
            raise SoftTimeLimitExceeded()

        signal.signal(signal.SIGALRM, alarm_handler)
        soft_limit = celery_kwargs.get("soft_time_limit") or app.conf.task_soft_time_limit
        signal.alarm(int(soft_limit) if soft_limit else 0)

        try:
            redirect_logger = get_logger("celery.redirected")
            proxy = LoggingProxy(redirect_logger, app.conf.worker_redirect_stdouts_level)
            with contextlib.redirect_stdout(proxy), contextlib.redirect_stderr(proxy):
                eager_result = run_job.apply(
                    args=[job_class_path, *list(args)],
                    kwargs=kwargs,
                    task_id=str(job_result_id),
                    **celery_kwargs,
                )
        finally:
            signal.alarm(0)

        job_result.refresh_from_db()
        JobResult._sync_eager_result_to_job_result(job_result, eager_result)

        return DispatchResult(task_id=job_result_id, backend=self.name)

    # --- worker introspection ---

    def get_active_workers(self) -> int:
        from nautobot.core.celery import app

        try:
            active = app.control.inspect().active() or {}
        except Exception:  # broker unreachable, etc.
            return -1
        return len(active)

    # --- periodic (delegated to celery beat as a separate service) ---

    def get_periodic_runner(self):
        return None
