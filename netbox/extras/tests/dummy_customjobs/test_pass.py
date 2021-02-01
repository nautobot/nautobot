from extras.custom_jobs import CustomJob


class TestPass(CustomJob):
    """
    Custom job with pass result.
    """
    description = "Validate custom job import"

    def test_pass(self):
        """
        Custom script function.
        """
        self.log_success(obj=None)
        self.status = "complete"
