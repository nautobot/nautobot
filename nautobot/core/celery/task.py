from celery.utils.log import get_task_logger
from celery import Task

from django.conf import settings


logger = get_task_logger(__name__)


class NautobotTask(Task):
    """Nautobot extensions to tasks for integrating with Job machinery."""


Task = NautobotTask  # noqa: So that the class path resolves.


class RunJobTaskFailed(Exception):
    """Celery task failed for some reason."""


class NautobotJobTask(Task):
    # TODO(jathan): Could be interesting for custom stuff when the Job is
    # enabled in the database and then therefore registered in Celery
    @classmethod
    def on_bound(cls, app):
        """Called when the task is bound to an app.

        Note:
            This class method can be defined to do additional actions when
            the task class is bound to an app.
        """

    # TODO(jathan): Could be interesting for showing the Job's class path as the
    # shadow name vs. the Celery task_name?
    def shadow_name(self, args, kwargs, options):
        """Override for custom task name in worker logs/monitoring.

        Example:
            .. code-block:: python

                from celery.utils.imports import qualname

                def shadow_name(task, args, kwargs, options):
                    return qualname(args[0])

                @app.task(shadow_name=shadow_name, serializer='pickle')
                def apply_function_async(fun, *args, **kwargs):
                    return fun(*args, **kwargs)

        Arguments:
            args (Tuple): Task positional arguments.
            kwargs (Dict): Task keyword arguments.
            options (Dict): Task execution options.
        """

    def get_job_result(self, task_id):
        from nautobot.extras.models.jobs import Job, JobResult  # avoid circular import
        from nautobot.extras.choices import LogLevelChoices
        return JobResult.objects.get(task_id=task_id)

    def before_start(self, task_id, args, kwargs):
        """Handler called before the task starts.

        .. versionadded:: 5.2

        Arguments:
            task_id (str): Unique id of the task to execute.
            args (Tuple): Original arguments for the task to execute.
            kwargs (Dict): Original keyword arguments for the task to execute.

        Returns:
            None: The return value of this handler is ignored.
        """
        # job_result = JobResult.objects.get(task_id=task_id)
        from nautobot.extras.choices import LogLevelChoices
        job_result = self.get_job_result(task_id)
        self.request.job_result = job_result
        job_model = job_result.job_model
        initialization_failure = None
        from nautobot.extras.models.jobs import Job # avoid circular import
        job_model = Job.objects.get_for_class_path(job_result.name)
        self.request.job_model = job_model

        if not job_model.enabled:
            initialization_failure = f"Job {job_model} is not enabled to be run!"
        else:
            job_class = job_model.job_class

            if not job_model.installed or not job_class:
                initialization_failure = f'Unable to locate job "{job_result.name}" to run it!'

        if initialization_failure:
            job_result.log(
                message=initialization_failure,
                obj=job_model,
                level_choice=LogLevelChoices.LOG_FAILURE,
                grouping="initialization",
                logger=logger,
            )
            raise RunJobTaskFailed(initialization_failure)

        job = job_class()
        self.request.job = job
        job.active_test = "initialization"
        job.job_result = job_result

        soft_time_limit = job_model.soft_time_limit or settings.CELERY_TASK_SOFT_TIME_LIMIT
        # soft_time_limit = settings.CELERY_TASK_SOFT_TIME_LIMIT
        time_limit = job_model.time_limit or settings.CELERY_TASK_TIME_LIMIT
        # time_limit = settings.CELERY_TASK_TIME_LIMIT
        if time_limit <= soft_time_limit:
            job_result.log(
                f"The hard time limit of {time_limit} seconds is less than "
                f"or equal to the soft time limit of {soft_time_limit} seconds. "
                f"This job will fail silently after {time_limit} seconds.",
                level_choice=LogLevelChoices.LOG_WARNING,
                grouping="initialization",
                logger=logger,
            )

        file_ids = None
        try:
            # Capture the file IDs for any FileProxy objects created so we can cleanup later.
            file_fields = list(job._get_file_vars())
            file_ids = [data[f] for f in file_fields]

            # Attempt to resolve serialized data back into original form by creating querysets or model instances
            # If we fail to find any objects, we consider this a job execution error, and fail.
            # This might happen when a job sits on the queue for a while (i.e. scheduled) and data has changed
            # or it might be bad input from an API request, or manual execution.

            data = job_class.deserialize_data(data)
        # TODO(jathan): Another place where because `log()` is called which mutates `.data`, we must
        # explicitly call `save()` again. We need to see if we can move more of this to `NauotbotTask`
        # and/or the DB backend as well.
        except Exception:
            stacktrace = traceback.format_exc()
            job_result.log(
                f"Error initializing job:\n```\n{stacktrace}\n```",
                level_choice=LogLevelChoices.LOG_FAILURE,
                grouping="initialization",
                logger=logger,
            )
            job_result.save()
            if file_ids:
                # Cleanup FileProxy objects
                job.delete_files(*file_ids)  # pylint: disable=not-an-iterable
            raise

        if job_model.read_only:
            # Force commit to false for read only jobs.
            commit = False

        # TODO(Glenn): validate that all args required by this job are set in the data or else log helpful errors?

        job.logger.info(f"Running job (commit={commit})")
        commit = True
        job_result.log(f"Running job (commit={commit})", logger=logger, level_choice=LogLevelChoices.LOG_INFO)

        # Add the current request as a property of the job
        job.request = request

    def on_success(self, retval, task_id, args, kwargs):
        """Success handler.

        Run by the worker if the task executes successfully.

        Arguments:
            retval (Any): The return value of the task.
            task_id (str): Unique id of the executed task.
            args (Tuple): Original arguments for the executed task.
            kwargs (Dict): Original keyword arguments for the executed task.

        Returns:
            None: The return value of this handler is ignored.
        """

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry handler.

        This is run by the worker when the task is to be retried.

        Arguments:
            exc (Exception): The exception sent to :meth:`retry`.
            task_id (str): Unique id of the retried task.
            args (Tuple): Original arguments for the retried task.
            kwargs (Dict): Original keyword arguments for the retried task.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Error handler.

        This is run by the worker when the task fails.

        Arguments:
            exc (Exception): The exception raised by the task.
            task_id (str): Unique id of the failed task.
            args (Tuple): Original arguments for the task that failed.
            kwargs (Dict): Original keyword arguments for the task that failed.
            einfo (~billiard.einfo.ExceptionInfo): Exception information.

        Returns:
            None: The return value of this handler is ignored.
        """

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Handler called after the task returns.

        Parameters
            status – Current task state.
            retval – Task return value/exception.
            task_id – Unique id of the task.
            args – Original arguments for the task that returned.
            kwargs – Original keyword arguments for the task that returned.

        Keyword Arguments
            einfo – ExceptionInfo instance, containing the traceback (if any).
        """
        from nautobot.extras.choices import LogLevelChoices
        job_result = self.request.job_result
        job_model = self.request.job_model
        job = self.request.job
        # job_result = self.get_job_result(task_id)
        # job_model = JobModel.objects.get_for_class_path(job_result.name)
        # job = job_model.job_class()

        # from nautobot.extras.models import JobResult  # avoid circular import
        # from nautobot.extras.choices import LogLevelChoices
        # TODO(jathan): Pretty sure this can also be handled by the backend, but
        # leaving it for now.
        # record data about this jobrun in the schedule
        if job_result.schedule:
            job_result.schedule.total_run_count += 1
            job_result.schedule.last_run_at = started
            job_result.schedule.save()

        # Perform any post-run tasks
        # 2.0 TODO Remove post_run() method entirely
        job.active_test = "post_run"
        output = job.post_run()
        # TODO(jathan): We need to call `save()` here too so that any appended output from
        # `post_run` gets stored on the `JobResult`. We need to move this out of here as well.
        if output:
            job.results["output"] += "\n" + str(output)
            job_result.save()

        job_result.refresh_from_db()
        # job.logger.info(f"Job completed in {job_result.duration}")
        job_result.log(f"Job completed in {job_result.duration}", logger=logger, level_choice=LogLevelChoices.LOG_INFO)


# TODO(jathan): Remove this once this body of work is done. This is just useful for debugging but it
# results int a lot of noise and slows things down.
# from celery import signals
# @signals.task_prerun.connect
def debug_task_prerun(sender, task_id, task, args, kwargs, **extra):
    logger.error(">>>    SENDER = %s", sender)
    logger.error(">>>      TASK = %s", task)
    logger.error(">>>   REQUEST = %s", task.request)
    logger.error(">>>   TASK_NAME = %s", task.request.task)
    logger.error(">>>   TASK_ID = %s", task_id)
    logger.error(">>>      ARGS = %s", args)
    logger.error(">>>    KWARGS = %s", kwargs)
    logger.error(">>>     EXTRA = %s", extra)
