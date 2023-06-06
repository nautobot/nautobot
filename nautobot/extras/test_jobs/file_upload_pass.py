from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, FileVar, get_task_logger


logger = get_task_logger(__name__)


class TestFileUploadPass(Job):
    class Meta:
        name = "File Upload Success"
        description = "Upload a file successfully"

    file = FileVar(
        description="File to upload",
    )

    def run(self, file):
        contents = str(file.read())
        logger.warning("File contents: %s", contents)
        logger.info("Job didn't crash!")

        return "Great job!"


register_jobs(TestFileUploadPass)
