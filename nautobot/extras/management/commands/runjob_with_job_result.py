from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from nautobot.core.celery import (
    app,
    setup_nautobot_job_logging,
)
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs import run_job
from nautobot.extras.management.utils import report_job_status, validate_job_and_job_data
from nautobot.extras.models import JobResult


class Command(BaseCommand):
    help = "Run a job (script, report) to validate or update data in Nautobot"

    def add_arguments(self, parser):
        parser.add_argument(
            "job_result",
            help="Pass in an existing job result id from the database to continue executing the job on a local system",
        )
        parser.add_argument(
            "--profile",
            action="store_true",
            help="Run cProfile on the job execution and write the result to the disk under /tmp.",
        )
        parser.add_argument(
            "--console_log",
            action="store_true",
            help="Enable logging output to the console.",
        )

    def console_log_run(self, data: dict, job_result: JobResult, job_model, job_user, options, *args):
        """
        Execute a job in subprocess with console logging enabled.

        This method represents a *parallel execution path* to
        `JobResult.enqueue_job()` when running jobs synchronously.
        Both code paths ultimately execute the same job
        logic, but differ in how execution is orchestrated and how output
        are handled.

        Relationship to enqueue_job():
        - Both paths execute a job associated with a JobResult.
        - Both are responsible for updating job status, result, and
        error information.
        - enqueue_job() supports asynchronous, synchronous, and queue-based
        execution (Celery, Kubernetes, etc.).
        - console_log_run() is intentionally limited to subprocess, synchronous
        execution with stdout/stderr streamed directly to the console.

        IMPORTANT:
            Changes to job execution semantics (status handling, result
            persistence, exception behavior, logging, or profiling) should
            be reviewed in *both* this method and `enqueue_job()`.
            These implementations must remain reasonably synchronized to
            avoid inconsistent job behavior between execution modes.

        Args:
            data (dict): Validated job input data passed to the job execution.
            job_result (JobResult): The JobResult instance being executed.
            job_model (Job): The job definition associated with the JobResult.
            job_user (User): The user associated with the job execution.
            options (dict): Parsed command options provided to the management
                command (argparse output).
            *args: Positional arguments passed by the management command framework.
        """
        schedule = data.get("schedule", None)
        celery_kwargs = data.get("celery_kwargs", None)
        task_queue = data.get("task_queue", None)
        ignore_singleton_lock = data.get("ignore_singleton_lock", None)

        job_celery_kwargs = JobResult._build_celery_kwargs(
            job_model=job_model,
            user=job_user,
            task_queue=task_queue,
            profile=options["profile"],
            ignore_singleton_lock=ignore_singleton_lock,
            schedule=schedule,
            celery_kwargs=celery_kwargs,
        )

        job_result.celery_kwargs = job_celery_kwargs
        job_result.date_started = timezone.now()
        job_result.save()
        setup_nautobot_job_logging(None, None, app.conf)
        run_job.apply(
            args=[job_model.class_path, *args],
            kwargs=data,
            task_id=str(job_result.id),
            **job_celery_kwargs,
        )

    def handle(self, *args, **options):
        job_result = None
        job_result_id = options["job_result"]
        try:
            job_result = JobResult.objects.get(pk=job_result_id)
        except JobResult.DoesNotExist:
            raise CommandError(f"Job result with pk {job_result_id} not found.")
        if job_result.status != JobResultStatusChoices.STATUS_PENDING and not options["console_log"]:
            raise CommandError(
                f"Job result has an invalid status {job_result.status} for this command."
                f" You can only pass in a job result with status {JobResultStatusChoices.STATUS_PENDING}"
            )
        job_user = job_result.user
        job_model = job_result.job_model
        job_class_path = job_model.class_path

        data = validate_job_and_job_data(self, job_user, job_class_path, job_result.task_kwargs)
        # execute_job here implies "--local"
        if options["console_log"]:
            self.console_log_run(
                data=data, job_result=job_result, job_model=job_model, job_user=job_user, options=options, *args
            )
        else:
            job_result = JobResult.execute_job(
                job_model, job_user, profile=options["profile"], job_result=job_result, **data
            )
            report_job_status(self, job_result)
