from celery import states
from django.utils import timezone
from django_celery_beat.managers import ExtendedManager
from django_celery_results.managers import TaskResultManager, transaction_retry

from nautobot.core.models import BaseManager
from nautobot.core.models.querysets import RestrictedQuerySet


class JobResultManager(BaseManager.from_queryset(RestrictedQuerySet), TaskResultManager):
    @transaction_retry(max_retries=2)
    def store_result(
        self,
        task_id,
        result,
        status,
        traceback=None,
        meta=None,
        periodic_task_name=None,
        task_name=None,
        task_args=None,
        task_kwargs=None,
        celery_kwargs=None,
        job_model_id=None,
        scheduled_job_id=None,
        worker=None,
        user_id=None,
        using=None,
        content_type=None,
        content_encoding=None,
    ):
        """
        Store the result and status of a Celery task.

        This overloads default model options provided by `django-celery-results` to manage custom
        behaviors for integration with Nautobot. Specifically these changes are:

        - Ignore incoming `content_type` and `content_encoding` fields as Nautobot explicitly only uses
          JSON utf-8 encoding for Celery messages.
        - Ensure that `name` is set to `task_name` if not otherwise set.
        - Only set `date_done` if the task has reached a ready state (execution completed),
          otherwise keep it null.

        Args:
            task_id (uuid): UUID of task.
            periodic_task_name (str): Celery periodic task name. (not used by Nautobot)
            task_name (str): Celery task name.
            task_args (list): Task arguments.
            task_kwargs (dict): Task kwargs.
            celery_kwargs (dict): Celery kwargs (kwargs passed to apply_async).
            job_model_id (uuid): UUID of the Job model instance of the task being run.
            scheduled_job_id (uuid): UUID of the ScheduledJob model instance that initiated
                this task, or None if not scheduled.
            result (obj): Return value of the task, or an exception instance raised
                by the task.
            status (str): Task status. See `JobResultStatusChoices` for a list of possible status
                values.
            worker (str): Worker that executes the task.
            user_id (uuid): UUID of the user that initiated the task.
            using (str): Django database connection to use.
            traceback (str): Traceback string taken at the point of exception (only passed if the
                task failed).
            meta (json): JSON-serialized result meta data (this contains e.g. children).
            content_type: Ignored. Kept for interface compatibility.
            content_encoding: Ignored. Kept for interface compatibility.

        Returns:
            JobResult
        """

        # Prepare the fields for creating/updating a `JobResult`.
        fields = {
            "status": status,
            "result": result,
            "traceback": traceback,
            "meta": meta,
            "date_done": None,
            "task_name": task_name,
            "task_args": task_args,
            "task_kwargs": task_kwargs,
            "celery_kwargs": celery_kwargs,
            "job_model_id": job_model_id,
            "scheduled_job_id": scheduled_job_id,
            "user_id": user_id,
            "worker": worker,
        }
        from nautobot.extras.models.jobs import Job

        # Need to have a try/except block here
        # because sometimes job_model_id will be None.
        try:
            job = Job.objects.get(id=job_model_id)
            if job.has_sensitive_variables:
                del fields["task_args"]
                del fields["task_kwargs"]
        except Job.DoesNotExist:
            pass

        obj, created = self.using(using).get_or_create(id=task_id, defaults=fields)

        if not created:
            # Make sure `date_done` is allowed to stay null until the task reacheas a ready state.
            #
            # Default behavior in `django-celery-results` has this field as a
            # `DateField(auto_now=True)` which just automatically updates the `date_done` field on every
            # state transition. This is different than Celery's default behavior (and the current
            # behavior of Nautobot) to keep it null until there is a state transition to a ready state
            # (e.g. `SUCCESS`, `REVOKED`, `FAILURE`).
            if fields["status"] in states.READY_STATES:
                fields["date_done"] = timezone.now()

            # Always make sure the Job `name` is set.
            if not obj.name and fields["task_name"]:
                fields["name"] = fields["task_name"]

            # Set the field values on the model instance.
            for k, v in fields.items():
                setattr(obj, k, v)

            obj.save(using=using)

        return obj


class ScheduledJobsManager(BaseManager.from_queryset(RestrictedQuerySet), ExtendedManager):
    pass
