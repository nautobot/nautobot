from django_celery_results.managers import TaskResultManager

from nautobot.utilities.querysets import RestrictedQuerySet


# This subclass is a hack. We'll fix it in post.
class JobResultManager(RestrictedQuerySet.as_manager().__class__, TaskResultManager):
    pass
