from extras.custom_jobs import CustomJob


class TestFail(CustomJob):
    """
    Custom job with fail result.
    """
    description = "Validate custom job import"

    def test_fail(self):
        """
        Custom script function.
        """
        self.log_success(obj=None)
        raise Exception("Test failure")
