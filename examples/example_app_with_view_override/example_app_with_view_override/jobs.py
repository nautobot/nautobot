from nautobot.apps.jobs import Job, register_jobs

name = "Example App With View Override jobs"  # The "grouping" that will contain all Jobs defined in this file.


class ExampleHiddenJob(Job):
    class Meta:
        hidden = True
        name = "Example hidden job"
        description = "I should not show in the UI!"

    def run(self):  # pylint:disable=arguments-differ
        pass


jobs = (ExampleHiddenJob,)
register_jobs(*jobs)
