import logging

from celery_singleton import Singleton


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
