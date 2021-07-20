from nautobot.extras.jobs import FileVar, Job, StringVar


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"


jobs = (DummyJob,)
