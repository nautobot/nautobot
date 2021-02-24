from nautobot.extras.jobs import Job


class TestPass(Job):
    """
    Job with pass result.
    """

    description = "Validate job import"

    def test_pass(self):
        """
        Job function.
        """
        self.log_success(obj=None)
        self.status = "complete"
