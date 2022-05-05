from nautobot.extras.jobs import Job


class TestLogRedaction(Job):
    class Meta:
        description = "Test redaction of logs"

    def run(self, data, commit):
        self.log_debug("The secret is supersecret123")
        self.log_info(message="The secret is supersecret123")
        self.log_success(message="The secret is supersecret123")
        self.log_warning(message="The secret is supersecret123")
        # Disabled as we don't want the job to fail
        # self.log_failure(message="The secret is supersecret123")
