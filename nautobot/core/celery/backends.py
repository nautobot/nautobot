from django_celery_results.backends import DatabaseBackend

from nautobot.extras.models import JobResult


class NautobotDatabaseBackend(DatabaseBackend):
    """
    Nautobot extensions to support database integration of Job machinery.
    """

    TaskModel = JobResult
