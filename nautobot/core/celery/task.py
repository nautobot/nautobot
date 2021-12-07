"""Custom Task class for use with Nautobot background services."""

import copy
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

    def get_key(self, args=None, kwargs=None):
        """
        Overload default to generate from the incoming `nautobot_kwargs` stored
        on the `request` object.

        The `job_name` is used instead of the internal Celery task's `name` attribute, and the
        runtime `once` values are merged in so that the key name will always be idempotent.
        """

        try:
            nautobot_kwargs = kwargs["request"]["nautobot_kwargs"]
        except (KeyError, TypeError):  # if dict or None
            nautobot_kwargs = dict(once={}, job_name=self.name)

        # Update `self.once` with any incoming `once` kwargs to assert runtime idempotence.
        original_once = copy.deepcopy(self.once)
        self.once.update(nautobot_kwargs["once"])

        # We're ignoring incoming `task_name` here and replacing it with `job_name`. We need to backup the
        # original `name` value and restore it before we return.
        original_name = self.name
        self.name = nautobot_kwargs["job_name"]

        # Generate the unique key using job_name + args + kwargs
        key = super().get_key(args, kwargs)

        # Restore original values
        self.name = original_name
        self.once = original_once

        return key


Task = NautobotTask  # noqa: So that the class path resolves.
