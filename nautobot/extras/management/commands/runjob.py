import time

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.models import JobResult
from nautobot.extras.jobs import get_job, run_job


class Command(BaseCommand):
    help = "Run a job (script, report) to validate or update data in Nautobot"

    def add_arguments(self, parser):
        parser.add_argument("job", help="Job to run")
        parser.add_argument(
            "--commit",
            action="store_true",
            help="Commit changes to DB (defaults to dry-run if unset)",
        )

    def handle(self, *args, **options):
        if "/" not in options["job"]:
            raise CommandError('Job must be specified in the form "grouping_name/module_name/JobClassName"')
        job_class = get_job(options["job"])
        if not job_class:
            raise CommandError('Job "%s" not found' % options["job"])

        job_content_type = ContentType.objects.get(app_label="extras", model="job")

        # Run the job and create a new JobResult
        self.stdout.write("[{:%H:%M:%S}] Running {}...".format(timezone.now(), job_class.class_path))

        job_result = JobResult.enqueue_job(
            run_job,
            job_class.class_path,
            job_content_type,
            None,
            data={},  # TODO: parsing CLI args into a data dictionary is not currently implemented
            request=None,
            commit=options["commit"],
        )

        # Wait on the job to finish
        while job_result.status not in JobResultStatusChoices.TERMINAL_STATE_CHOICES:
            time.sleep(1)
            job_result = JobResult.objects.get(pk=job_result.pk)

        # Report on success/failure
        for test_name, attrs in job_result.data.items():

            if test_name in ["total", "output"]:
                continue

            self.stdout.write(
                "\t{}: {} success, {} info, {} warning, {} failure".format(
                    test_name,
                    attrs["success"],
                    attrs["info"],
                    attrs["warning"],
                    attrs["failure"],
                )
            )

            for log_entry in attrs["log"]:
                status = log_entry[1]
                if status == "success":
                    status = self.style.SUCCESS(status)
                elif status == "info":
                    status = status
                elif status == "warning":
                    status = self.style.WARNING(status)
                elif status == "failure":
                    status = self.style.NOTICE(status)

                if log_entry[2]:  # object associated with log entry
                    self.stdout.write(f"\t\t{status}: {log_entry[2]}: {log_entry[-1]}")
                else:
                    self.stdout.write(f"\t\t{status}: {log_entry[-1]}")

        if job_result.data["output"]:
            self.stdout.write(job_result.data["output"])

        if job_result.status == JobResultStatusChoices.STATUS_FAILED:
            status = self.style.ERROR("FAILED")
        elif job_result.status == JobResultStatusChoices.STATUS_ERRORED:
            status = self.style.ERROR("ERRORED")
        else:
            status = self.style.SUCCESS("SUCCESS")
        self.stdout.write("[{:%H:%M:%S}] {}: {}".format(timezone.now(), job_class.class_path, status))

        # Wrap things up
        self.stdout.write(
            "[{:%H:%M:%S}] {}: Duration {}".format(timezone.now(), job_class.class_path, job_result.duration)
        )
        self.stdout.write("[{:%H:%M:%S}] Finished".format(timezone.now()))
