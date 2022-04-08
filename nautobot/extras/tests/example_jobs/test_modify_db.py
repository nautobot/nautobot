from nautobot.extras.jobs import Job
from nautobot.extras.models import Status


class TestModifyDB(Job):
    """
    Job that modifies the database.
    """

    def test_modify_db(self):
        """
        Job function.
        """
        obj = Status(
            name="Test Status",
            slug="test-status",
        )
        obj.save()
        self.log_success(obj=obj, message="Status created successfully.")
