from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import IntegerVar, Job


class FileOutputJob(Job):
    lines = IntegerVar()

    class Meta:
        name = "File Output job"
        description = "Creates a text file as output."

    def run(self, lines):  # pylint:disable=arguments-differ
        self.create_file("output.txt", "Hello World!\n" * lines)


register_jobs(FileOutputJob)
