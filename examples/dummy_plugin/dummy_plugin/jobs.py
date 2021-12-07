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
        description = (
            "Singleton job, only runs one at a time. Arguments are ignored for uniqueness. "
            "Try running several and see what happens."
        )
        singleton = True
        singleton_keys = []  # Null singleton_keys

    def run(self, data, commit):
        interval = data["interval"]
        self.log_info(message=f"Sleeping for {interval} seconds")
        time.sleep(interval)
        self.log_success(obj=None)
        return "I just woke up."


class SingletonKeysJob(Job):
    interval = IntegerVar(default=4, description="The time in seconds to sleep.")

    class Meta:
        name = "Singleton Keys Job"
        description = (
            "Singleton job, only runs one at a time if the arguments match. Try running several and see what happens."
        )
        singleton = True
        singleton_keys = ["data"]

    def run(self, data, commit):
        interval = data["interval"]
        self.log_info(message=f"Sleeping for {interval} seconds")
        time.sleep(interval)
        self.log_success(obj=None)
        return "I just woke up."


jobs = (DummyJob, SingletonJob, SingletonKeysJob)
