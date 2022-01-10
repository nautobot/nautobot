from nautobot.extras.jobs import Job


name = "ExamplePlugin jobs"


class ExampleJob(Job):
    class Meta:
        name = "Example job, does nothing"
        description = """
            Markdown Formatting

            *This is italicized*
        """


class ExampleHiddenJob(Job):
    class Meta:
        hidden = True
        name = "Example hidden job"
        description = "I should not show in the UI!"


jobs = (ExampleJob, ExampleHiddenJob)
