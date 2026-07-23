from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from nautobot.core.jobs.import_utils import detect_import_format
from nautobot.core.management.utils import get_content_type, get_user, run_system_job_locally
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.management.utils import report_job_status

JOB_CLASS_PATH = "nautobot.core.jobs.ImportObjects"


class Command(BaseCommand):
    help = (
        "Import objects from a CSV file by running the ImportObjects system job locally. "
        "Intended for development and manual testing of the import pipeline."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "content_type",
            help='Content type of the objects to import, in "app_label.model" form, e.g. "dcim.device"',
        )
        parser.add_argument("file", help="Path of the CSV file to import")
        parser.add_argument(
            "-u",
            "--username",
            required=True,
            help="User account to impersonate as the requester of this import",
        )
        parser.add_argument(
            "--match-fields",
            help='Field name(s) to match existing records on, separated by commas (e.g. "name,serial"); '
            "matched records are updated in place. Overrides any directive present in the file.",
        )
        parser.add_argument(
            "--format",
            default="auto",
            choices=["auto", "csv", "json", "yaml"],
            help="Format of the import file (default: auto-detect from extension/content)",
        )
        parser.add_argument(
            "--no-rollback",
            action="store_true",
            help="Do not roll back the entire import if any row fails",
        )

    def handle(self, *args, **options):
        user = get_user(options["username"])
        content_type = get_content_type(options["content_type"])
        try:
            file_text = Path(options["file"]).read_text(encoding="utf-8-sig")
        except OSError as exc:
            raise CommandError(str(exc)) from exc

        data = {
            "content_type": str(content_type.pk),
            "csv_data": file_text,
            "roll_back_if_error": not options["no_rollback"],
            "import_format": options["format"]
            if options["format"] != "auto"
            else detect_import_format(options["file"], file_text),
        }
        if options["match_fields"]:
            data["match_fields"] = options["match_fields"]

        job_result = run_system_job_locally(self, user, JOB_CLASS_PATH, data)
        report_job_status(self, job_result)
        if job_result.status != JobResultStatusChoices.STATUS_SUCCESS:
            raise CommandError("Import did not complete successfully; see logs above")
