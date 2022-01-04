from nautobot.extras.jobs import Job


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"
        description = """
            Markdown Formatting

            *This is italicized*
        """


class DummyHiddenJob(Job):
    class Meta:
        hidden = True
        name = "Dummy hidden job"
        description = "I should not show in the UI!"


jobs = (DummyJob, DummyHiddenJob)
