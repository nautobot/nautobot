from celery import states
from django.utils import timezone
from django_celery_results.managers import TaskResultManager, transaction_retry

from nautobot.core.models.querysets import RestrictedQuerySet


# This subclass is a hack. We'll fix it in post.
class JobResultManager(RestrictedQuerySet.as_manager().__class__, TaskResultManager):
    @transaction_retry(max_retries=2)
    def store_result(self, *args, **kwargs):
        """
        Overload default to manage custom behaviors for Nautobot integration.
        """
        obj = super().store_result(*args, **kwargs)

        # Make sure `date_done` is allowed to stay null until the task reacheas
        # a ready state.
        if kwargs["status"] in states.READY_STATES:
            obj.date_done = timezone.now()
        else:
            obj.date_done = None

        # Always make sure the Job `name` is set.
        if not obj.name and obj.task_name:
            obj.name = obj.task_name

        obj.save()

        return obj
