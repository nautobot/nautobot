from rest_framework import status
from rest_framework.exceptions import APIException


class AbortTransaction(Exception):
    """
    An exception used to trigger a database transaction rollback.
    """

    pass


# TODO remove this in 2.0
class RQWorkerNotRunningException(APIException):
    """
    Indicates the temporary inability to enqueue a legacy RQ task  because no RQ worker processes are currently running.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Unable to process request: RQ worker process not running."
    default_code = "rq_worker_not_running"


class CeleryWorkerNotRunningException(APIException):
    """
    Indicates the temporary inability to enqueue a new Celery task (e.g. custom script execution) because
    no Celery worker processes are currently running.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Unable to process request: Celery worker process not running."
    default_code = "celery_worker_not_running"
