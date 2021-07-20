from nautobot.extras.jobs import FileVar, Job, StringVar


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"


class FileUploadJob(Job):
    class Meta:
        name = "File Upload"
        description = "Upload a file`"

    file = FileVar(
        description="File to upload",
    )
    text = StringVar(
        description="Put some text here, any text at all",
        required=False,
    )

    def run(self, data, commit):
        blob = data["file"]
        text = data["text"]

        self.log_warning(f"Cursor position: {blob.tell()}")
        contents = str(blob.read())
        self.log_warning(f"File contents: {contents}")
        self.log_warning(f"Cursor position: {blob.tell()}")

        self.log_warning(f"Text is: {text}")
        self.log_success(message="Job didn't crash!")

        return "Great job!"


jobs = (DummyJob, FileUploadJob)
