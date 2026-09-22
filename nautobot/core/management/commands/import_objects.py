import argparse
from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from nautobot.core.management.utils import get_content_type, get_user, run_system_job_locally
from nautobot.extras.choices import JobResultStatusChoices
from nautobot.extras.management.utils import report_job_status
from nautobot.extras.models import FileProxy

JOB_CLASS_PATH = "nautobot.core.jobs.ImportObjects"


class Command(BaseCommand):
    help = (
        "Import objects from a CSV, JSON, or YAML file by running the ImportObjects system job locally. "
        "Intended for development and manual testing of the import pipeline."
    )

    def add_arguments(self, parser):
        parser.add_argument("file", help="Path of the CSV, JSON, or YAML file to import")
        parser.add_argument(
            # No short option: `-c` is nautobot-server's own `--config-path`
            "--content-type",
            help='Content type of the objects to import, in "app_label.model" form, e.g. "dcim.device". '
            "Defaults to the model the file declares for itself, as every file Nautobot exports does.",
        )
        parser.add_argument(
            "-u",
            "--username",
            required=True,
            help="User account to impersonate as the requester of this import",
        )
        parser.add_argument(
            "--match-fields",
            help='Field name(s) to match existing records on, separated by commas (e.g. "name,serial"), '
            "overriding any directive present in the file. NOT YET IMPLEMENTED: the value is passed to the "
            "Job but nothing acts on it, so every import currently creates new objects.",
        )
        parser.add_argument(
            "--format",
            default="auto",
            choices=["auto", "csv", "json", "yaml"],
            help="Format of the import file (default: auto-detect from extension/content)",
        )
        parser.add_argument(
            "--rollback",
            action=argparse.BooleanOptionalAction,
            default=True,
            help="Roll back the entire import if any row fails (default: enabled), "
            "matching the Job's own `roll_back_if_error` default",
        )

    def handle(self, *args, **options):
        user = get_user(options["username"])
        path = Path(options["file"])
        try:
            content = path.read_bytes()
        except OSError as exc:
            raise CommandError(str(exc)) from exc

        # Handed to the Job as a FileProxy rather than as inline text, so that a large import does not end
        # up stored in the JobResult's task_kwargs. The Job's own cleanup deletes the proxy afterwards
        # (`_cleanup_job`), which is also why it is created only once the Job is about to run.
        file_proxy = FileProxy.objects.create(name=path.name, file=ContentFile(content, name=path.name))
        data = {
            "csv_file": str(file_proxy.pk),
            "roll_back_if_error": options["rollback"],
            # "auto" leaves the detection to the Job, which sees the uploaded file's name
            "import_format": options["format"],
        }
        if options["content_type"]:
            # Otherwise the Job takes it from the model the data declares
            data["content_type"] = str(get_content_type(options["content_type"]).pk)
        if options["match_fields"]:
            data["match_fields"] = options["match_fields"]

        try:
            job_result = run_system_job_locally(self, user, JOB_CLASS_PATH, data)
        except Exception:
            # The Job never ran, so its cleanup never will either
            file_proxy.delete()
            raise

        report_job_status(self, job_result)
        if job_result.status != JobResultStatusChoices.STATUS_SUCCESS:
            raise CommandError("Import did not complete successfully; see logs above")
