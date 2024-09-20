from django_celery_results.backends import DatabaseBackend

from nautobot.core.utils.logging import sanitize
from nautobot.extras.constants import JOB_RESULT_CUSTOM_CELERY_KWARGS
from nautobot.extras.models import JobResult


class NautobotDatabaseBackend(DatabaseBackend):
    """
    Nautobot extensions to support database integration of Job machinery.
    """

    TaskModel = JobResult

    def encode_content(self, data):
        """Pass through encoding since we're storing as JSON explicitly."""
        return "application/x-nautobot-json", "utf-8", data

    def decode_content(self, obj, content):
        """Pass through decoding since we're storing as JSON explicitly."""
        return content

    def _get_extended_properties(self, request, traceback):
        """
        Overload default so that `argsrepr` and `kwargsrepr` aren't used to construct `args` and `kwargs`.
        Also adds custom kwargs passed in on `apply_async` calls to track user, job model, scheduled job, etc.
        """
        extended_props = {
            "task_args": None,
            "task_kwargs": None,
            "celery_kwargs": None,
            "job_model_id": None,
            "scheduled_job_id": None,
            "task_name": None,
            "traceback": None,
            "user_id": None,
            "worker": None,
        }
        if request and self.app.conf.find_value_for_key("extended", "result"):
            task_name = getattr(request, "task", None)
            # do not encode args/kwargs as we store these in a JSONField instead of TextField
            task_args = getattr(request, "args", None)
            task_kwargs = getattr(request, "kwargs", None)

            properties = getattr(request, "properties", {}) or {}

            # retrieve original "queue" kwarg from the request, celery stores it in delivery_info.routing_key
            celery_kwargs = {"queue": request.delivery_info.get("routing_key", None)}

            for kwarg_name in JOB_RESULT_CUSTOM_CELERY_KWARGS:
                if kwarg_name in properties:
                    celery_kwargs[kwarg_name] = properties[kwarg_name]

            # Explicitly sanitize the traceback output.
            if traceback is not None:
                traceback = sanitize(traceback)

            # Preserve the JobResult data behavior from Nautobot 2.0 through 2.2 (wherein the Job itself was the task)
            # by manipulating `task_name` and `task_args` to hide the fact that we are now calling
            # `run_job.apply(args=[JobClass.class_path, ...])` instead of `JobClass.apply(args=[...])`.
            if task_name == "nautobot.extras.jobs.run_job" and task_args:
                task_name = task_args[0]
                task_args = task_args[1:]

            extended_props.update(
                {
                    "task_args": task_args,
                    "task_kwargs": task_kwargs,
                    "celery_kwargs": celery_kwargs,
                    "job_model_id": properties.get("nautobot_job_job_model_id", None),
                    "scheduled_job_id": properties.get("nautobot_job_scheduled_job_id", None),
                    "task_name": task_name,
                    "traceback": traceback,
                    "user_id": properties.get("nautobot_job_user_id", None),
                    "worker": getattr(request, "hostname", None),
                }
            )

        return extended_props

    def prepare_exception(self, exc, serializer=None):
        """Overload default to explicitly sanitize the traceback message result."""
        exc_info = super().prepare_exception(exc, serializer=serializer)

        exc_message = exc_info["exc_message"]
        exc_info["exc_message"] = sanitize(exc_message)

        return exc_info
