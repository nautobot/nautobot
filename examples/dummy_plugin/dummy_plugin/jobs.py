from nautobot.extras.jobs import Job, IntegerVar
import time


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"


class SingletonJob(Job):
    interval = IntegerVar(default=4, description="The time in seconds to sleep.")

    class Meta:
        name = "Singleton Job"
        description = "Singleton job, only runs one at a time. Try running several and see what happens."
        singleton = True

    def run(self, data, commit):
        interval = data["interval"]
        self.log_info(message=f"Sleeping for {interval} seconds")
        time.sleep(interval)
        self.log_success(obj=None)
        self.status = "complete"
        return "I just woke up."


jobs = (DummyJob, SingletonJob)
