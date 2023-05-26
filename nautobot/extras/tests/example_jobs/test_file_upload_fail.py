from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, FileVar, get_task_logger


logger = get_task_logger(__name__)


class FileUploadFailed(Exception):
    """Explicit exception for use with testing."""


class TestFileUploadFail(Job):
    """Uploads and reads the file but then deliberately fails."""

    exception = FileUploadFailed

    class Meta:
        name = "File Upload Failure"
        description = "Upload a file then throw an unrelated exception"

    file = FileVar(
        description="File to upload",
    )

    def run(self, file):
        contents = str(file.read())
        logger.warning("File contents: %s", contents)

        raise self.exception("Test failure")


register_jobs(TestFileUploadFail)
