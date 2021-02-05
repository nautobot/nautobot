from extras.custom_jobs import CustomJob


name = "DummyPlugin jobs"


class DummyJob(CustomJob):
    class Meta:
        name = "Dummy job, does nothing"


jobs = (DummyJob, )
