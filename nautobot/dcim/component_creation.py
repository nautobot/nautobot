"""Public extension point for suppressing automatic Device/Module component instantiation.

By default, when a new :class:`~nautobot.dcim.models.Device` or
:class:`~nautobot.dcim.models.Module` is first persisted, ``save()`` calls
``self.create_components()`` to instantiate one component (interface, console
port, power port, etc.) per template defined on the related ``DeviceType`` /
``ModuleType``. For apps that own the component inventory from an external
source-of-truth and intend to write the full component graph themselves
immediately after creating the parent object, this default is undesirable.

This module exposes :class:`SkipAutoComponentCreation`, a re-entrant,
exception-safe context manager. Code that runs inside the ``with`` block
creates Devices/Modules without their template-derived components::

    >>> from nautobot.apps.dcim import SkipAutoComponentCreation
    >>> from nautobot.dcim.models import Device
    >>> with SkipAutoComponentCreation():
    ...     device = Device.objects.create(...)  # no auto-instantiated components

The scope is limited to the *initial* save (the ``is_new`` branch of
``Device.save()`` / ``Module.save()``). It does not affect subsequent saves,
updates, or paths that bypass ``save()`` such as ``bulk_create()``.

Suppression is scoped per-asyncio-task and per-Celery-task via
:class:`contextvars.ContextVar`, so it cannot leak across concurrent task
boundaries.
"""

import contextvars
from typing import Optional

_skip_flag: contextvars.ContextVar[bool] = contextvars.ContextVar(
    "nautobot_dcim_skip_auto_component_creation",
    default=False,
)


class SkipAutoComponentCreation:
    """Context manager that suppresses Device/Module ``create_components()`` on save.

    Inside the ``with`` block, ``Device.save()`` and ``Module.save()`` skip
    their call to ``self.create_components()`` for newly created instances.
    Default behaviour (instantiate components from the related DeviceType /
    ModuleType templates) is restored automatically on exit, including when
    the block raises.

    The context manager is re-entrant: an outer ``with`` block continues to
    suppress after an inner block exits. It is exception-safe: state is
    restored even if the wrapped code raises.

    Implementation uses :class:`contextvars.ContextVar`, so the flag is
    correctly scoped per asyncio task / Celery worker invocation and does
    not leak across threads.

    Example:
        >>> from nautobot.apps.dcim import SkipAutoComponentCreation
        >>> from nautobot.dcim.models import Device
        >>> with SkipAutoComponentCreation():
        ...     device = Device.objects.create(...)  # no auto-components
    """

    def __init__(self):
        """Initialize without entering the context yet."""
        self._token: Optional[contextvars.Token] = None

    def __enter__(self):
        """Activate suppression for the calling context."""
        self._token = _skip_flag.set(True)
        return self

    def __exit__(self, exc_type, exc, tb):
        """Restore the previous suppression state."""
        if self._token is not None:
            _skip_flag.reset(self._token)
            self._token = None
        # Do not suppress exceptions raised inside the with block.
        return False


def is_auto_component_creation_suppressed() -> bool:
    """Return True if a :class:`SkipAutoComponentCreation` context is active.

    Intended primarily for introspection and tests. Production code should
    normally use the :class:`SkipAutoComponentCreation` context manager directly.
    """
    return _skip_flag.get()
