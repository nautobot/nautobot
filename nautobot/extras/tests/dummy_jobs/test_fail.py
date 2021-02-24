from nautobot.extras.jobs import Job


class TestFail(Job):
    """
    Job with fail result.
    """

    description = "Validate job import"

    def test_fail(self):
        """
        Job function.
        """
        self.log_success(obj=None)
        raise Exception("Test failure")
