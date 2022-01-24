import time
from nautobot.extras.jobs import Job


class TestSoftTimeLimitExceeded(Job):
    class Meta:
        name = "Soft Time Limit Exceeded"
        description = "Set a soft time limit of 1 second`"
        soft_time_limit = 1

    def run(self, data, commit):
        time.sleep(1.5)
        self.log_debug("This message should never be seen!")
        return "Soft time limit exceeded"
