from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nautobot.core.management.utils import get_content_type, get_user, run_system_job_locally
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.management.utils import report_job_status

JOB_CLASS_PATH = "nautobot.core.jobs.ExportObjectList"


class Command(BaseCommand):
    help = (
        "Export objects to a file by running the ExportObjectList system job locally. "
        "Intended for development and manual testing of the export pipeline."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "content_type",
            help='Content type of the objects to export, in "app_label.model" form, e.g. "dcim.device"',
        )
        parser.add_argument(
            "-u",
            "--username",
            required=True,
            help="User account to impersonate as the requester of this export",
        )
        parser.add_argument(
            "--filter",
            default="",
            help='Filterset parameters to apply, in URL query format, e.g. "location=ams01&status=active"',
        )
        parser.add_argument(
            "--format",
            default="csv",
            choices=["csv", "json", "yaml"],
            help="Format to export to (default: csv)",
        )
        parser.add_argument(
            "--fields",
            default="",
            help="Comma-separated list of fields to export, including nested references "
            '(e.g. "name,status__name,device_type__manufacturer__name"); default is all fields',
        )
        parser.add_argument(
            "-o",
            "--output",
            help="Path to write the exported file to (default: write to standard output)",
        )

    def handle(self, *args, **options):
        user = get_user(options["username"])
        content_type = get_content_type(options["content_type"])

        data = {
            "content_type": str(content_type.pk),
            "query_string": options["filter"],
            "export_format": options["format"],
            "export_fields": options["fields"],
        }

        job_result = run_system_job_locally(self, user, JOB_CLASS_PATH, data)
        report_job_status(self, job_result)
        if job_result.status != JobResultStatusChoices.STATUS_SUCCESS:
            raise CommandError("Export did not complete successfully; see logs above")

        file_proxies = list(job_result.files.all())
        if not file_proxies:
            raise CommandError("The export job did not produce a file")
        for file_proxy in file_proxies:
            content = file_proxy.file.read()
            if options["output"]:
                Path(options["output"]).write_bytes(content)
                self.stdout.write(self.style.SUCCESS(f"Wrote {file_proxy.name} to {options['output']}"))
            else:
                self.stdout.write(content.decode("utf-8"))
