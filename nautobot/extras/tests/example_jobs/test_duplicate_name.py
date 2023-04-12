from nautobot.core.celery import register_jobs
from nautobot.extras.jobs import Job


class TestDuplicateName1(Job):
    """
    Job with duplicate name.
    """

    class Meta:
        name = "This name is not unique."


class TestDuplicateName2(Job):
    """
    Job with duplicate name.
    """

    class Meta:
        name = "This name is not unique."


class TestDuplicateNameNoMeta(Job):
    pass


register_jobs(TestDuplicateName1, TestDuplicateName2, TestDuplicateNameNoMeta)
