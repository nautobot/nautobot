"""Custom Task class for use with Nautobot background services."""

from hashlib import md5
import logging

from kombu import serialization


def nautobot_generate_lock(task_name, task_args=None, task_kwargs=None, key_prefix="SINGLETONLOCK_"):
    """
    Overload of `celery_singleton.util.generate_lock()` to use `kombu` serialization vs. `json`.

    This is required because the original function doesn't know how to serialize complex objects due
    to using the vanilla `json` encoder vs. the specialized Kombu encoder.
    """
    _, _, str_args = serialization.dumps(sorted(task_args) or [])
    _, _, str_kwargs = serialization.dumps({k: task_kwargs[k] for k in sorted(task_kwargs)} or {})
    task_hash = md5((task_name + str_args + str_kwargs).encode()).hexdigest()
    key_prefix = key_prefix
    return key_prefix + task_hash


# Monkey patch the `util` lib with our replacement.
from celery_singleton import util  # noqa

util.generate_lock = nautobot_generate_lock


# Now we can import Singleton
from celery_singleton import Singleton  # noqa


logger = logging.getLogger(__name__)


class NautobotTask(Singleton):
    """Base task for Nautobot Celery tasks.

    This is a subclass of `celery_singleton.Singleton` that's only singleton when we mean it by
    passing `really_singleton=True` to `apply_async()`.
    """

    def apply_async(
        self,
        args=None,
        kwargs=None,
        task_id=None,
        producer=None,
        link=None,
        link_error=None,
        shadow=None,
        really_singleton=False,
        **options,
    ):

        # Use the Singleton pattern
        if really_singleton:
            return super(NautobotTask, self).apply_async(
                args=args,
                kwargs=kwargs,
                task_id=task_id,
                producer=producer,
                link=link,
                link_error=link_error,
                shadow=shadow,
                **options,
            )
        # Call the base method (default behavior)
        else:
            return super(Singleton, self).apply_async(
                args=args,
                kwargs=kwargs,
                task_id=task_id,
                producer=producer,
                link=link,
                link_error=link_error,
                shadow=shadow,
                **options,
            )


Task = NautobotTask  # noqa: So that the class path resolves.
