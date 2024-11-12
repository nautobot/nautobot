import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.management.utils import report_job_status, validate_job_and_job_data
from nautobot.extras.models import Job, JobResult


class Command(BaseCommand):
    help = "Run a job (script, report) to validate or update data in Nautobot"

    def add_arguments(self, parser):
        parser.add_argument("job", help="Job in the Python module form: `<module_name>.<JobClassName>`")
        parser.add_argument(
            "--profile",
            action="store_true",
            help="Run cProfile on the job execution and write the result to the disk under /tmp.",
        )
        parser.add_argument(
            "-u",
            "--username",
            help="User account to impersonate as the requester of this job",
            required=True,
        )
        parser.add_argument(
            "-l",
            "--local",
            action="store_true",
            help="Run the job on the local system and not on a worker.",
        )
        parser.add_argument("-d", "--data", type=str, help="JSON string that populates the `data` variable of the job.")

    def handle(self, *args, **options):
        if "." not in options["job"]:
            raise CommandError('Job must be specified in the Python module form: "<module_name>.<JobClassName>"')
        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError("No such user") from exc

        job_class_path = options["job"]
        data = validate_job_and_job_data(self, user, job_class_path, options.get("data"))
        job_model = Job.objects.get_for_class_path(job_class_path)

        if options["local"]:
            job_result = JobResult.execute_job(job_model, user, profile=options["profile"], **data)
        else:
            job_result = JobResult.enqueue_job(job_model, user, profile=options["profile"], **data)

            # Wait on the job to finish
            while job_result.status not in JobResultStatusChoices.READY_STATES:
                time.sleep(1)
                job_result.refresh_from_db()

        # Report on success/failure
        report_job_status(self, job_result)
