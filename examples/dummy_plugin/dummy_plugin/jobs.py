import time

from nautobot.extras.jobs import IntegerVar, Job


name = "DummyPlugin jobs"


class DummyJob(Job):
    class Meta:
        name = "Dummy job, does nothing"


class DummyLoggingJob(Job):
    interval = IntegerVar(default=4, description="The time in seconds to sleep.")

    class Meta:
        name = "Dummy logging job."
        description = "I log stuff to demonstrate how UI logging works."

    def run(self, data, commit):
        interval = data["interval"]
        self.log_debug(message=f"Running for {interval} seconds.")
        for step in range(1, interval + 1):
            time.sleep(1)
            self.log_info(message=f"Step {step}")
        self.log_success(obj=None)
        return f"Ran for {interval} seconds"


jobs = (DummyJob, DummyLoggingJob)
