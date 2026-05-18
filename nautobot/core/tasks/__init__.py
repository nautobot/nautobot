"""Backend-agnostic task execution for Nautobot.

Public API::

    from nautobot.core.tasks import get_task_backend, EnqueueOptions

    backend = get_task_backend()
    backend.enqueue(...)

Backend selection is controlled by the Django ``TASK_BACKEND`` setting
(env var: ``NAUTOBOT_TASK_BACKEND``). Built-in values: ``"celery"``,
``"procrastinate"``. Any other string is treated as a dotted import path to a
``TaskBackend`` subclass.
"""
from __future__ import annotations

from functools import lru_cache

from django.conf import settings
from django.utils.module_loading import import_string

from .base import (
    DispatchResult,
    EnqueueOptions,
    PeriodicRunner,
    TaskBackend,
)

_BUILTIN_BACKENDS = {
    "celery": "nautobot.core.tasks.celery_backend.CeleryBackend",
    "procrastinate": "nautobot.core.tasks.procrastinate_backend.ProcrastinateBackend",
}


@lru_cache(maxsize=1)
def get_task_backend() -> TaskBackend:
    """Return the active TaskBackend instance.

    The result is cached for the lifetime of the process. Tests that switch
    backends mid-run should call ``get_task_backend.cache_clear()``.
    """
    name = getattr(settings, "TASK_BACKEND", "celery")
    dotted_path = _BUILTIN_BACKENDS.get(name, name)
    backend_cls = import_string(dotted_path)
    return backend_cls()


__all__ = [
    "DispatchResult",
    "EnqueueOptions",
    "PeriodicRunner",
    "TaskBackend",
    "get_task_backend",
]
