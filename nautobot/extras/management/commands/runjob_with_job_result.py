from django.core.management.base import BaseCommand, CommandError

from nautobot.extras.choices import JobResultStatusChoices
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

    def handle(self, *args, **options):
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

        job_user = job_result.user
        job_model = job_result.job_model
        job_class_path = job_model.class_path

        data = validate_job_and_job_data(self, job_user, job_class_path, job_result.task_kwargs)

        # execute_job here implies "--local"
        job_result = JobResult.execute_job(
            job_model, job_user, profile=options["profile"], job_result=job_result, **data
        )
        # Report on success/failure
        report_job_status(self, job_result)
