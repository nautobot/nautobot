from nautobot.extras.jobs import Job, FileVar


class TestFileUploadFail(Job):
    """Uploads and reads the file but then deliberately fails."""

    class Meta:
        name = "File Upload Failure"
        description = "Upload a file then throw an unrelated exception"

    file = FileVar(
        description="File to upload",
    )

    def run(self, data, commit):
        blob = data["file"]

        contents = str(blob.read())
        self.log_warning(message=f"File contents: {contents}")

        raise Exception("Test failure")
