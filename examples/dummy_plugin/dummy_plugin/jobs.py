from nautobot.extras.jobs import Job


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"


jobs = (DummyJob,)
