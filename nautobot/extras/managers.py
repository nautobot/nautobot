from celery import states
from django.utils import timezone
from django_celery_results.managers import TaskResultManager, transaction_retry

from nautobot.core.models.querysets import RestrictedQuerySet


# This subclass is a hack. We'll fix it in post.
class JobResultManager(RestrictedQuerySet.as_manager().__class__, TaskResultManager):
    @transaction_retry(max_retries=2)
    def store_result(self, *args, **kwargs):
        """
        Overload default to explicitly manage the `date_done` field so we can
        allow it to stay null until the task reaches a ready state.
        """
        obj = super().store_result(*args, **kwargs)

        if kwargs["status"] in states.READY_STATES:
            obj.date_done = timezone.now()
        else:
            obj.date_done = None
        obj.save()

        return obj
