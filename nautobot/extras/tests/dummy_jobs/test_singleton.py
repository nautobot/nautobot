from nautobot.extras.jobs import Job, IntegerVar
import time


class SingletonJobNoArguments(Job):

    interval = IntegerVar(default=1, description="The time in seconds to sleep.")

    class Meta:
        name = "Singleton Job without argument hashing"
        description = "Singleton job, only runs one at a time. Excludes arguments for dupe detection."
        singleton = True

    def run(self, data, commit):
        interval = data["interval"]
        self.log_info(message=f"Sleeping for {interval} seconds")
        time.sleep(interval)
        self.log_success(obj=None)
        self.status = "complete"
        return "I just woke up."


class SingletonJobWithArguments(Job):

    interval = IntegerVar(default=1, description="The time in seconds to sleep.")

    class Meta:
        name = "Singleton Job with argument hashing"
        description = "Singleton job, only runs one at a time. Includes arguments for dupe detection."
        singleton = True
        singleton_keys = ["data"]

    def run(self, data, commit):
        interval = data["interval"]
        self.log_info(message=f"Sleeping for {interval} seconds")
        time.sleep(interval)
        self.log_success(obj=None)
        self.status = "complete"
        return "I just woke up."


jobs = (SingletonJobNoArguments, SingletonJobWithArguments)
