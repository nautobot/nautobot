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
    help = (
        "Execute an existing pending JobResult synchronously in the current process using Celery's "
        "eager execution mode. Intended to be invoked as a subprocess by JobConsoleLogExecutor "
        "or via 'runjob --local', not called directly by humans."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "job_result",
            help="Pass in an existing job result id from the database to continue executing the job on a local system",
        )
        parser.add_argument("-d", "--data", type=str, help="JSON string that populates the `data` variable of the job.")
        parser.add_argument(
            "--profile",
            action="store_true",
            help="Run cProfile on the job execution and write the result to the disk under /tmp.",
        )

    def handle(self, *args, **options):
        """Execute a pending JobResult directly via Celery eager (synchronous) mode.

        Looks up the JobResult by UUID, resolves and validates the job data (from --data
        or from the existing task_kwargs on the JobResult), builds celery_kwargs if not
        already present, stamps date_started, then runs the job via run_job.apply().
        After execution, syncs the eager result back to the JobResult.

        This is the leaf command in two execution chains:

        Local execution (runjob --local):
            runjob --local
                |
                -- execute_job_result <job_result_pk>
                    |
                    -- run_job.apply() (Celery eager)

        Console log execution (runjob_with_job_result):
            runjob_with_job_result
                |
                -- JobConsoleLogExecutor.execute()
                    |
                    -- subprocess: execute_job_result <job_result_pk>
                        |
                        -- run_job.apply() (Celery eager)

        In the console log path, JobConsoleLogExecutor spawns this command as a subprocess
        and is responsible for capturing its stdout/stderr into JobConsoleEntry rows.
        This command has no knowledge of how its output is consumed.

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
        if job_data := options.get("data"):
            data = validate_job_and_job_data(self, job_user, job_class_path, job_data)
        else:
            data = validate_job_and_job_data(self, job_user, job_class_path, job_result.task_kwargs)

        job_celery_kwargs = job_result.celery_kwargs
        if not job_celery_kwargs:
            raise CommandError(f"Job result with pk {job_result_id} does not have `celery_kwargs` defined.")
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
