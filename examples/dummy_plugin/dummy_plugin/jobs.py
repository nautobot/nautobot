from nautobot.extras.jobs import Job


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"
        description = """
        ### Markdown Formatting
        This demonstrates a multiline markdown-formatted job description.
        """


jobs = (DummyJob,)
