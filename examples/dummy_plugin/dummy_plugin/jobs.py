from nautobot.extras.jobs import Job


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"
        description = """
            Markdown Formatting

            *This is italicized*
        """


jobs = (DummyJob,)
