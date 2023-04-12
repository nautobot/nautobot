from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job, FileVar


class TestFileUploadPass(Job):
    class Meta:
        name = "File Upload Success"
        description = "Upload a file successfully"

    file = FileVar(
        description="File to upload",
    )

    def run(self, file):
        contents = str(file.read())
        self.log_warning(message=f"File contents: {contents}")
        self.log_success(message="Job didn't crash!")

        return "Great job!"


register_jobs(TestFileUploadPass)
