from django_celery_results.backends import DatabaseBackend

from nautobot.core.celery import _dumps, _loads
from nautobot.extras.models import JobResult


class NautobotDatabaseBackend(DatabaseBackend):
    """
    Nautobot extensions to support database integration of Job machinery.
    """

    TaskModel = JobResult

    # overloaded to pass through actual args/kwargs to let the manager censor sensitive args before storing
    def _get_extended_properties(self, request, traceback):
        extended_props = {
            "periodic_task_name": None,
            "task_args": None,
            "task_kwargs": None,
            "task_name": None,
            "traceback": None,
            "worker": None,
        }
        if request and self.app.conf.find_value_for_key("extended", "result"):

            task_args = getattr(request, "args", None)
            task_kwargs = getattr(request, "kwargs", None)

            properties = getattr(request, "properties", {}) or {}
            periodic_task_name = properties.get("periodic_task_name", None)
            extended_props.update(
                {
                    "periodic_task_name": periodic_task_name,
                    "task_args": task_args,
                    "task_kwargs": task_kwargs,
                    "task_name": getattr(request, "task", None),
                    "traceback": traceback,
                    "worker": getattr(request, "hostname", None),
                }
            )

        return extended_props

    def encode_content(self, data):
        """Pass through encoding since we're storing as JSON explicitly."""
        return "application/x-nautobot-json", "utf-8", _dumps(data)

    def decode_content(self, obj, content):
        """Pass through decoding since we're storing as JSON explicitly."""
        return _loads(content)
