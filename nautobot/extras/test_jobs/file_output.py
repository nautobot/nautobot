import tempfile

from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import BooleanVar, IntegerVar, Job


class FileOutputJob(Job):
    lines = IntegerVar()
    use_file_object = BooleanVar(default=False, required=False)

    class Meta:
        name = "File Output job"
        description = "Creates a text file as output."

    def run(self, lines, use_file_object=False):  # pylint:disable=arguments-differ
        content = "Hello World!\n" * lines
        if not use_file_object:
            self.create_file("output.txt", content)
            return
        with tempfile.TemporaryFile() as output:
            output.write(content.encode("utf-8"))
            self.create_file("output.txt", output)


register_jobs(FileOutputJob)
