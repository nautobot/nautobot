from nautobot.extras.jobs import Job, IntegerVar
import time


class SingletonJobNoSingletonKeys(Job):
    """Job that DOES NOT use `singleton_keys` to assert uniqueness. Job name only."""

    interval = IntegerVar(default=1, description="The time in seconds to sleep.")

    class Meta:
        name = "Singleton Job without argument hashing"
        description = "Singleton job, only runs one at a time. Uses only Job name for dupe detection."
        singleton = True
        singleton_keys = []  # Null singleton_keys

    def run(self, data, commit):
        interval = data["interval"]
        self.log_info(message=f"Sleeping for {interval} seconds")
        time.sleep(interval)
        self.log_success(obj=None)
        return "I just woke up."


class SingletonJobWithSingletonKeys(Job):
    """Job that uses Job name WITH `singleton_keys` to assert uniqueness."""

    interval = IntegerVar(default=1, description="The time in seconds to sleep.")

    class Meta:
        name = "Singleton Job with argument hashing"
        description = "Singleton job, only runs one at a time. Includes `singleton_keys` for dupe detection."
        singleton = True
        singleton_keys = ["data"]

    def run(self, data, commit):
        interval = data["interval"]
        self.log_info(message=f"Sleeping for {interval} seconds")
        time.sleep(interval)
        self.log_success(obj=None)
        return "I just woke up."


jobs = (SingletonJobNoSingletonKeys, SingletonJobWithSingletonKeys)
