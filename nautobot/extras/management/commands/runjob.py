import json
import time

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from nautobot.extras.choices import LogLevelChoices, JobResultStatusChoices
from nautobot.extras.models import Job, JobLogEntry, JobResult
from nautobot.extras.jobs import get_job


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
        job_class = get_job(options["job"])
        if not job_class:
            raise CommandError(f'Job "{options["job"]}" not found')

        User = get_user_model()
        try:
            user = User.objects.get(username=options["username"])
        except User.DoesNotExist as exc:
            raise CommandError("No such user") from exc

        data = {}
        try:
            if options.get("data"):
                data = json.loads(options["data"])
        except json.decoder.JSONDecodeError as error:
            raise CommandError(f"Invalid JSON data:\n{str(error)}")

        job_model = Job.objects.get_for_class_path(options["job"])

        # Run the job and create a new JobResult
        self.stdout.write(f"[{timezone.now():%H:%M:%S}] Running {options['job']}...")

        if options["local"]:
            job_result = JobResult.execute_job(job_model, user, profile=options["profile"], **data)
        else:
            job_result = JobResult.enqueue_job(job_model, user, profile=options["profile"], **data)

            # Wait on the job to finish
            while job_result.status not in JobResultStatusChoices.READY_STATES:
                time.sleep(1)
                job_result.refresh_from_db()

        # Report on success/failure
        groups = set(JobLogEntry.objects.filter(job_result=job_result).values_list("grouping", flat=True))
        for group in sorted(groups):
            logs = JobLogEntry.objects.filter(job_result__pk=job_result.pk, grouping=group)
            debug_count = logs.filter(log_level=LogLevelChoices.LOG_DEBUG).count()
            info_count = logs.filter(log_level=LogLevelChoices.LOG_INFO).count()
            warning_count = logs.filter(log_level=LogLevelChoices.LOG_WARNING).count()
            error_count = logs.filter(log_level=LogLevelChoices.LOG_ERROR).count()
            critical_count = logs.filter(log_level=LogLevelChoices.LOG_CRITICAL).count()

            self.stdout.write(
                f"\t{group}: {debug_count} debug, {info_count} info, {warning_count} warning, {error_count} error, {critical_count} critical"
            )

            for log_entry in logs:
                status = log_entry.log_level
                if status == "success":
                    status = self.style.SUCCESS(status)
                elif status == "info":
                    status = status
                elif status == "warning":
                    status = self.style.WARNING(status)
                elif status == "failure":
                    status = self.style.NOTICE(status)

                if log_entry.log_object:
                    self.stdout.write(f"\t\t{status}: {log_entry.log_object}: {log_entry.message}")
                else:
                    self.stdout.write(f"\t\t{status}: {log_entry.message}")

        if job_result.result:
            self.stdout.write(job_result.result)

        if job_result.status == JobResultStatusChoices.STATUS_FAILURE:
            status = self.style.ERROR("FAILURE")
        else:
            status = self.style.SUCCESS("SUCCESS")
        self.stdout.write(f"[{timezone.now():%H:%M:%S}] {options['job']}: {status}")

        # Wrap things up
        self.stdout.write(f"[{timezone.now():%H:%M:%S}] {options['job']}: Duration {job_result.duration}")
        self.stdout.write(f"[{timezone.now():%H:%M:%S}] Finished")
