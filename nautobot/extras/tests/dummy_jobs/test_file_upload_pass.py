from nautobot.extras.jobs import Job, FileVar


class TestFileUploadPass(Job):
    class Meta:
        name = "File Upload"
        description = "Upload a file`"

    file = FileVar(
        description="File to upload",
    )

    def run(self, data, commit):
        blob = data["file"]

        contents = str(blob.read())
        self.log_warning(f"File contents: {contents}")
        self.log_success(message="Job didn't crash!")

        return "Great job!"
