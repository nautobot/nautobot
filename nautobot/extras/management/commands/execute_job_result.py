from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from nautobot.core.celery import (
    app,
    setup_nautobot_job_logging,
)
from nautobot.extras.jobs import run_job
from nautobot.extras.management.utils import validate_job_and_job_data
from nautobot.extras.models import JobResult


class Command(BaseCommand):
    help = "Execute a job with console log capturing via JobConsoleLogExecutor"

    def add_arguments(self, parser):
        parser.add_argument(
            "job_result",
            help="Pass in an existing job result id from the database to continue executing the job on a local system",
        )

    def handle(self, *args, **options):
        """
        Directly execute a pending JobResult in the current process using Celery's
        eager (synchronous) execution mode.

        This method represents a *parallel execution path* to
        `JobResult.enqueue_job()` when running jobs synchronously.
        Both code paths ultimately execute the same job
        logic, but differ in how execution is orchestrated and how output
        are handled.

        HOW THIS DIFFERS FROM `runjob --local`:
        - `runjob --local` accepts a job class path and username as CLI arguments,
        constructs a new JobResult, and calls `JobResult.execute_job()`.
        - `execute_job_result` accepts an *existing* JobResult PK (already created
        and PENDING), and re-uses it directly via `run_job.apply()`. It does not
        create a new JobResult and does not accept a class path or username.

        HOW THIS DIFFERS FROM `runjob_with_job_result`:
        - `runjob_with_job_result` is an orchestrator: it inspects the JobResult and
        decides *how* to run it. Either by spawning `execute_job_result` as a
        subprocess (via `JobConsoleLogExecutor`) when console logging is enabled,
        or by calling `JobResult.execute_job()` directly otherwise.
        - `execute_job_result` is the *leaf* command it is never called by a human
        directly. It is always invoked as a subprocess by `JobConsoleLogExecutor`,
        which is responsible for capturing its stdout/stderr and storing them as
        `JobConsoleEntry` rows. It has no knowledge of how its output is consumed.

        EXECUTION CHAIN (console_log path):
            runjob_with_job_result
                |
                -- JobConsoleLogExecutor.execute()
                    |
                    -- subprocess: execute_job_result <job_result_pk>
                        |
                        -- run_job.apply() (Celery eager)

        IMPORTANT:
            Changes to job execution semantics (status handling, result persistence,
            exception behavior, logging, or profiling) should be reviewed in both
            this command and `JobResult.enqueue_job()`. These two paths must remain
            consistent to avoid divergent behavior between execution modes.
        """
        job_result = None
        job_result_id = options["job_result"]
        try:
            job_result = JobResult.objects.get(pk=job_result_id)
        except JobResult.DoesNotExist:
            raise CommandError(f"Job result with pk {job_result_id} not found.")
        job_user = job_result.user
        job_model = job_result.job_model
        job_class_path = job_model.class_path

        data = validate_job_and_job_data(self, job_user, job_class_path, job_result.task_kwargs)

        schedule = data.get("schedule", None)
        celery_kwargs = data.get("celery_kwargs", None)
        task_queue = data.get("task_queue", None)
        ignore_singleton_lock = data.get("ignore_singleton_lock", None)

        job_celery_kwargs = job_result.celery_kwargs
        if not job_celery_kwargs:
            # should be build in enqueue_job, but if not build it here
            job_celery_kwargs = JobResult._build_celery_kwargs(
                job_model=job_model,
                user=job_user,
                task_queue=task_queue,
                console_log=True,
                ignore_singleton_lock=ignore_singleton_lock,
                schedule=schedule,
                celery_kwargs=celery_kwargs,
            )

            job_result.celery_kwargs = job_celery_kwargs
        job_result.date_started = timezone.now()
        job_result.save()
        setup_nautobot_job_logging(None, None, app.conf)
        eager_result = run_job.apply(
            args=[job_model.class_path, *args],
            kwargs=data,
            task_id=str(job_result.id),
            **job_celery_kwargs,
        )
        job_result.refresh_from_db()
        JobResult._sync_eager_result_to_job_result(job_result, eager_result)
