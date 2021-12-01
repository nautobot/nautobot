"""Custom Task class for use with Nautobot background services."""

import logging

from celery_once import QueueOnce


logger = logging.getLogger(__name__)


class NautobotTask(QueueOnce):
    """Base task for Nautobot Celery tasks.

    This is a subclass of `celery_once.QueueOnce` that's only singleton when we mean it by
    passing `singleton=True` to `apply_async()`.
    """

    def apply_async(self, args=None, kwargs=None, **options):

        is_singleton = options.pop("singleton", False)

        if is_singleton:
            return super(NautobotTask, self).apply_async(args=args, kwargs=kwargs, **options)
        else:
            return super(QueueOnce, self).apply_async(args=args, kwargs=kwargs, **options)
