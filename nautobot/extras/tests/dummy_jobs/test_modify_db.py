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
        Status.objects.create(
            name="Test Status",
            slug="test-status",
        )
