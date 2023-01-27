from django_celery_results.backends import DatabaseBackend

from nautobot.extras.models import JobResult


class NautobotDatabaseBackend(DatabaseBackend):
    """
    Nautobot extensions to support database integration of Job machinery.
    """

    TaskModel = JobResult

    # TODO(jathan): Overloading these prevents the double encoding/decoding but
    # it's still not working to allow us to just have JSON fields on the
    # JobResult.
    def encode_content(self, data):
        return "application/x-nautobot-json", "utf-8", data

    def decode_content(self, obj, content):
        return content
