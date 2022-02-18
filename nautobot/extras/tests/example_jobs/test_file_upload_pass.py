from nautobot.extras.jobs import Job, FileVar


class TestFileUploadPass(Job):
    class Meta:
        name = "File Upload Success"
        description = "Upload a file successfully"

    file = FileVar(
        description="File to upload",
    )

    def run(self, data, commit):
        blob = data["file"]

        contents = str(blob.read())
        self.log_warning(message=f"File contents: {contents}")
        self.log_success(message="Job didn't crash!")

        return "Great job!"
