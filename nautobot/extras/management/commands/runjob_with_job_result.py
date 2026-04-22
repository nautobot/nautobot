from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.jobs_console_log import JobConsoleLogExecutor
from nautobot.extras.management.utils import report_job_status
from nautobot.extras.models import JobResult


class Command(BaseCommand):
    help = (
        "Execute a pending JobResult by its UUID. Depending on the JobResult's celery_kwargs, "
        "either runs the job with console log streaming via a subprocess (capturing stdout/stderr "
        "into JobConsoleEntry records) or delegates to the 'execute_job_result' management command. "
        "Intended to be invoked as a Kubernetes Job command, not by humans directly."
    )

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

    def handle(self, *args, **options):
        """Execute a pending JobResult in the current process.

        Looks up the JobResult by the provided UUID and asserts it is in STATUS_PENDING.
        Then branches based on the 'nautobot_job_console_log' flag in celery_kwargs:

        - If True:  runs the job via JobConsoleLogExecutor, which spawns 'execute_job_result'
                    as a subprocess, captures its stdout and stderr into
                    JobConsoleEntry records via background StreamReader threads, and raises
                    JobConsoleLogSubprocessError on non-zero exit.
        - If False: delegates to the 'execute_job_result' management command directly
                    (optionally with cProfile enabled via --profile), then reports the
                    final job status.

        This command is the leaf entrypoint for Kubernetes-based job execution and is not
        intended to be called directly by humans.
        """
        job_result = None
        job_result_id = options["job_result"]
        try:
            job_result = JobResult.objects.get(pk=job_result_id)
        except JobResult.DoesNotExist:
            raise CommandError(f"Job result with pk {job_result_id} not found.")
        if job_result.status != JobResultStatusChoices.STATUS_PENDING:
            raise CommandError(
                f"Job result has an invalid status {job_result.status} for this command."
                f" You can only pass in a job result with status {JobResultStatusChoices.STATUS_PENDING}"
            )
        if job_result.celery_kwargs.get("nautobot_job_console_log", False):
            executor = JobConsoleLogExecutor(job_result_id)
            executor.execute()
        else:
            call_command("execute_job_result", f"{job_result_id}", profile=options["profile"], stdout=self.stdout)
            job_result.refresh_from_db()
        report_job_status(self, job_result)
